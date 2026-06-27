"""
通过 UDP 转发 /dev/video1 的 H.264 视频流。

使用 GStreamer pipeline 从输出 H.264 编码的摄像头采集视频，
经 h264parse 解析、RTP 封装后通过 UDP 发送到目标地址。
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

import rclpy
from rclpy.node import Node


# GStreamer 总线消息类型（非阻塞轮询时关注的类型）
_BUS_MSG_TYPES = (
    Gst.MessageType.ERROR
    | Gst.MessageType.EOS
    | Gst.MessageType.WARNING
    | Gst.MessageType.INFO
    | Gst.MessageType.STATE_CHANGED
    | Gst.MessageType.STREAM_STATUS
    | Gst.MessageType.ELEMENT
)


def _gst_pipeline_str(device: str, width: int, height: int,
                      framerate: int, host: str, port: int) -> str:
    """构建 H.264 UDP 转发 GStreamer pipeline 字符串。

    /dev/video1 输出已编码的 H.264 帧（byte-stream 格式），
    通过 h264parse 解析后以 RTP 封装，经 UDP 发送至目标地址。

    config-interval=-1 确保每个 IDR 帧前插入 SPS/PPS，
    使接收端可在任意时刻加入流。
    """
    return (
        f'v4l2src device={device} io-mode=2 ! '
        f'video/x-h264, width={width}, height={height}, framerate={framerate}/1 ! '
        f'h264parse config-interval=-1 ! '
        f'rtph264pay ! '
        f'udpsink host={host} port={port} sync=false'
    )


class H264UdpNode(Node):
    """H.264 UDP 转发节点：/dev/video1 → H.264 RTP → UDP。

    启动 GStreamer pipeline 将 H.264 摄像头的视频流以 RTP 封装后
    通过 UDP 发送到目标地址。接收端可用 VLC、ffplay 或 GStreamer
    播放 rtpH264 流。
    """

    def __init__(self):
        super().__init__('h264_udp', namespace='rov')

        self.declare_parameters(
            namespace='',
            parameters=[
                ('device', '/dev/video1'),
                ('width', 640),
                ('height', 480),
                ('framerate', 15),
                ('host', '192.168.3.11'),
                ('port', 5600),
            ],
        )

        device = self.get_parameter('device').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        framerate = self.get_parameter('framerate').value
        host = self.get_parameter('host').value
        port = self.get_parameter('port').value

        pipeline_str = _gst_pipeline_str(
            device, width, height, framerate, host, port)
        self.get_logger().info(f'Pipeline: {pipeline_str}')

        # 初始化 GStreamer
        Gst.init(None)

        # 解析并创建 pipeline（失败时抛出 GLib.Error，由调用者处理）
        try:
            self._pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            self.get_logger().error(f'Failed to parse GStreamer pipeline: {e}')
            self._pipeline = None
            return

        self._bus = self._pipeline.get_bus()

        # 启动 pipeline
        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.get_logger().error('Failed to start GStreamer pipeline')
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            return

        self.get_logger().info(
            f'rov_h264_udp started ({width}x{height}@{framerate}fps'
            f' → {host}:{port})')

        # 定时轮询 GStreamer 总线（非阻塞，0.5 Hz 足够）
        self._poll_timer = self.create_timer(2.0, self._poll_bus)

    def _poll_bus(self):
        """轮询 GStreamer 总线消息（非阻塞）。"""
        if self._pipeline is None:
            self._poll_timer.cancel()
            return

        # 非阻塞取消息：timeout=0 立即返回
        msg = self._bus.timed_pop_filtered(0, _BUS_MSG_TYPES)
        while msg is not None:
            t = msg.type

            if t == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                self.get_logger().error(
                    f'GStreamer error: {err.message} '
                    f'(source: {msg.src.name}, debug: {debug[:200]})')
                self._stop_pipeline()

            elif t == Gst.MessageType.WARNING:
                err, debug = msg.parse_warning()
                self.get_logger().warn(
                    f'GStreamer warning: {err.message}',
                    throttle_duration_sec=10.0)

            elif t == Gst.MessageType.EOS:
                self.get_logger().warn('GStreamer EOS, stopping pipeline')
                self._stop_pipeline()

            elif t == Gst.MessageType.INFO:
                err, debug = msg.parse_info()
                self.get_logger().debug(f'GStreamer info: {err.message}')

            elif t == Gst.MessageType.STATE_CHANGED:
                if msg.src == self._pipeline:
                    old, new, pending = msg.parse_state_changed()
                    self.get_logger().debug(
                        f'Pipeline state: {old.value_nick} → {new.value_nick}')

            msg = self._bus.timed_pop_filtered(0, _BUS_MSG_TYPES)

    def _stop_pipeline(self):
        """停止 GStreamer pipeline 并释放资源。"""
        if self._pipeline is not None:
            self.get_logger().info('Stopping H.264 UDP pipeline')
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None

    def destroy_node(self):
        self._stop_pipeline()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = H264UdpNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
