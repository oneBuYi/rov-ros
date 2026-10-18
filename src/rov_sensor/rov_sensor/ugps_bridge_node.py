
"""
UGPS 桥接节点：通过 UDP 接收 NMEA 语句，
按设备 ID 过滤、过滤零坐标、转换专有前缀为通用 NMEA 前缀，
重新计算校验和后通过 UART 转发给 Pixhawk 飞控。

设计要点：
- 非阻塞 UDP 读取（select + setblocking(False)），不阻塞 ROS spin
- 所有关键参数（端口、波特率、设备 ID）均可通过 ROS params 配置
- 周期性状态日志，记录收发/过滤/转发计数
"""

import select
import socket

import serial

import rclpy
from rclpy.node import Node


# ── NMEA 工具函数 ──────────────────────────────────────────────────────────────

def _calculate_nmea_checksum(nmea_data: str) -> str:
    """计算 NMEA 语句的校验和（$ 后到 * 前的所有字符异或）。"""
    checksum = 0
    for c in nmea_data[1:]:
        if c == '*':
            break
        checksum ^= ord(c)
    return f"{checksum:02X}"


def _is_valid_coordinate(coord_str: str) -> bool:
    """判断坐标是否有效（非零，非空）。"""
    if not coord_str or coord_str.strip() == "":
        return False
    try:
        coord = float(coord_str)
        return abs(coord) > 0.000001
    except (ValueError, TypeError):
        return False


def _modify_nmea_for_pixhawk(nmea_data: str) -> str:
    """替换专有 NMEA 前缀为标准 GPS 前缀，并重新计算校验和。

    UGPS 设备发出的 NMEA 语句使用 $PBPxxx 前缀（P = Proprietary），
    Pixhawk 只识别标准 $GPxxx 前缀。
    """
    if not nmea_data.startswith('$') or '*' not in nmea_data:
        return nmea_data

    original_data, _old_checksum = nmea_data.split('*', 1)

    prefix_map = {
        '$PBPRMC': '$GPRMC',
        '$PBPGGA': '$GPGGA',
        '$PBPGLL': '$GPGLL',
        '$PBPHDT': '$GPHDT',
        '$PBPTHS': '$GPTHS',
        '$PBPDBS': '$GPDBS',
    }

    modified_data = original_data
    for old_prefix, new_prefix in prefix_map.items():
        if original_data.startswith(old_prefix):
            modified_data = original_data.replace(old_prefix, new_prefix, 1)
            break

    new_checksum = _calculate_nmea_checksum(modified_data)
    return f"{modified_data}*{new_checksum}"


# ── ROS 2 节点 ────────────────────────────────────────────────────────────────

class UgpsBridgeNode(Node):
    """UGPS UDP → UART 桥接节点。

    从 UDP 端口接收 NMEA 语句，过滤非目标设备 ID 和零坐标数据，
    转换前缀后通过串口转发给 Pixhawk。
    """

    def __init__(self):
        super().__init__('ugps_bridge', namespace='rov')

        # ── 参数声明 ──
        self.declare_parameters(
            namespace='',
            parameters=[
                ('udp_port', 52120),
                ('uart_port', '/dev/ttyS1'),
                ('baudrate', 38400),
                ('target_device_id', '019496'),
                ('poll_rate', 100.0),
                ('status_interval_sec', 10.0),
            ],
        )

        self._udp_port = self.get_parameter('udp_port').value
        self._uart_port = self.get_parameter('uart_port').value
        self._baudrate = self.get_parameter('baudrate').value
        # 规范化设备 ID：ROS 2 Foxy 的 launch 参数序列化（YAML）可能
        # 将字符串 '019496' 转换为整数 19496（或浮点数 19496.0），
        # 因此需要鲁棒地处理两种类型，始终归一化为零填充字符串。
        raw_device_id = self.get_parameter('target_device_id').value
        try:
            self._target_device_id = f"{int(float(raw_device_id)):06d}"
        except (ValueError, TypeError):
            self._target_device_id = str(raw_device_id).strip()
        poll_rate = self.get_parameter('poll_rate').value
        status_interval = self.get_parameter('status_interval_sec').value

        # ── 统计计数 ──
        self._total_received = 0
        self._total_filtered_device = 0
        self._total_filtered_coord = 0
        self._total_forwarded = 0

        # ── 初始化串口 ──
        self._ser = None
        try:
            self._ser = serial.Serial(
                port=self._uart_port,
                baudrate=self._baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0,  # 非阻塞
            )
            self.get_logger().info(
                f'UART 初始化成功: {self._uart_port} (波特率: {self._baudrate})')
        except serial.SerialException as e:
            self.get_logger().error(f'UART 初始化失败: {e}')
            raise

        # ── 初始化 UDP ──
        self._sock = None
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(('', self._udp_port))
            self._sock.setblocking(False)
            self.get_logger().info(
                f'监听 UDP 端口 {self._udp_port}，等待数据...')
        except Exception as e:
            self.get_logger().error(f'UDP 初始化失败: {e}')
            if self._ser:
                self._ser.close()
            raise

        self._data_buffer = b""

        # ── 定时器 ──
        poll_period = 1.0 / poll_rate
        self._poll_timer = self.create_timer(poll_period, self._poll)
        self._status_timer = self.create_timer(
            status_interval, self._dump_status)

        self.get_logger().info(
            f'ugps_bridge 启动 '
            f'(udp:{self._udp_port} → uart:{self._uart_port}@{self._baudrate}, '
            f'device_id={self._target_device_id}, poll@{poll_rate:.0f}Hz)')

    # ── UDP 轮询 ──────────────────────────────────────────────────────────

    def _poll(self):
        """定时回调：非阻塞读取 UDP 数据，逐行处理并转发。"""
        while True:
            ready = select.select([self._sock], [], [], 0)
            if not ready[0]:
                break

            try:
                data, _client_addr = self._sock.recvfrom(4096)
            except OSError:
                continue

            if not data:
                continue

            self._total_received += 1
            self._data_buffer += data

            self.get_logger().info(
                f'UDP 收到 {len(data)} 字节: {data!r}')

            # 按行分割处理
            while b'\n' in self._data_buffer:
                line, self._data_buffer = self._data_buffer.split(b'\n', 1)
                line = line.strip(b'\r')

                try:
                    nmea_str = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    continue

                if not nmea_str.startswith('$'):
                    continue

                self.get_logger().info(f'原始 NMEA: {nmea_str}')

                # ── 1. 提取设备 ID ──
                device_id = ""
                if '*' in nmea_str:
                    main_part = nmea_str.split('*')[0]
                    fields = main_part.split(',')
                    if fields:
                        device_id = fields[-1].strip()

                # ── 2. 过滤非目标设备 ──
                # 对提取的 ID 和目标 ID 均进行归一化处理（零填充），
                # 以解决 ROS 2 YAML 参数序列化过程中潜在的的类型强制转换问题。
                try:
                    extracted_id = f"{int(float(device_id)):06d}" if device_id else ""
                except (ValueError, TypeError):
                    extracted_id = device_id
                target_id = self._target_device_id

                if extracted_id != target_id:
                    self._total_filtered_device += 1
                    self.get_logger().info(f'过滤设备 ID [{extracted_id}], 期望 [{target_id}]')
                    continue

                # ── 3. 过滤零坐标 ──
                fields = nmea_str.split(',')
                is_valid = True
                if nmea_str.startswith('$PBPRMC'):
                    lat = fields[3] if len(fields) >= 4 else ""
                    lon = fields[5] if len(fields) >= 6 else ""
                    is_valid = _is_valid_coordinate(lat) and _is_valid_coordinate(lon)
                elif nmea_str.startswith('$PBPGGA'):
                    lat = fields[2] if len(fields) >= 3 else ""
                    lon = fields[4] if len(fields) >= 5 else ""
                    is_valid = _is_valid_coordinate(lat) and _is_valid_coordinate(lon)
                elif nmea_str.startswith('$PBPGLL'):
                    lat = fields[1] if len(fields) >= 2 else ""
                    lon = fields[3] if len(fields) >= 4 else ""
                    is_valid = _is_valid_coordinate(lat) and _is_valid_coordinate(lon)

                if not is_valid and nmea_str.startswith(('$PBPRMC', '$PBPGGA', '$PBPGLL')):
                    self._total_filtered_coord += 1
                    self.get_logger().info(f'过滤 0 坐标: {nmea_str}')
                    continue

                # ── 4. 转换并转发 ──
                try:
                    fixed_nmea = _modify_nmea_for_pixhawk(nmea_str)
                    self._ser.write((fixed_nmea + '\r\n').encode('utf-8'))
                    self._total_forwarded += 1
                    self.get_logger().info(f'转发 → UART: {fixed_nmea}')
                except serial.SerialException as e:
                    self.get_logger().error(
                        f'串口写入失败: {e}', throttle_duration_sec=5.0)
                except Exception as e:
                    self.get_logger().error(
                        f'转发错误: {e}', throttle_duration_sec=5.0)

    # ── 状态日志 ──────────────────────────────────────────────────────────

    def _dump_status(self):
        """周期性状态报告。"""
        self.get_logger().info(
            f'[STATUS] '
            f'recv={self._total_received} '
            f'filtered_dev={self._total_filtered_device} '
            f'filtered_coord={self._total_filtered_coord} '
            f'forwarded={self._total_forwarded}')

    # ── 清理 ──────────────────────────────────────────────────────────────

    def destroy_node(self):
        self.get_logger().info(
            f'Destroying node — final stats: '
            f'recv={self._total_received} forwarded={self._total_forwarded}')
        if self._sock:
            self._sock.close()
        if self._ser:
            self._ser.close()
        super().destroy_node()


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = UgpsBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
