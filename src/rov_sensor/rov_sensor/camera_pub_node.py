"""
从 USB 摄像头采集 MJPEG 帧并发布为 sensor_msgs/CompressedImage 话题。

使用 GStreamer appsink 直接从 v4l2src 获取 JPEG 帧，
不做 MJPEG→BGR→JPEG 的徒劳往返，保持原始压缩数据。

设备路径支持：
- 显式路径: /dev/video0, /dev/v4l/by-id/usb-...-video-index0
- Glob 通配符: /dev/v4l/by-id/usb-*-video-index0 (自动选择第一个匹配项)
- 回退机制: 如果指定路径不可用，自动尝试 /dev/video{0-9}

关键设计：
- try-pull-sample + 超时 防止 timer 回调被无限阻塞（卡死的根源）
- GStreamer bus 轮询捕获底层 pipeline 错误
- pipeline 错误/EOS 后自动重启
- 帧计数器 + 周期性状态日志 用于诊断断流/卡死问题
"""

import glob
import os
import time
from collections import deque

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

# ── helpers ────────────────────────────────────────────────────────────────

def _resolve_device(device_spec: str):
    """
    Resolve a camera device specification to an existing path.

    解析策略：
    1. 如果路径存在（精确匹配或 glob 匹配），直接返回
    2. 否则按 /dev/video0 → /dev/video9 回退
    3. 都找不到则返回原始 spec（让 GStreamer 报错）

    Returns:
        (resolved_path: str, description: str)
    """
    if os.path.exists(device_spec):
        return device_spec, device_spec

    if '*' in device_spec or '?' in device_spec:
        matches = sorted(glob.glob(device_spec))
        if matches:
            resolved = matches[0]
            real = os.path.realpath(resolved) if os.path.islink(resolved) else resolved
            return resolved, f'{resolved} -> {real}'

    for i in range(10):
        candidate = f'/dev/video{i}'
        if os.path.exists(candidate):
            return candidate, f'{candidate} (fallback — {device_spec} not found)'

    return device_spec, f'{device_spec} (not found, no fallback available)'


def _gst_pipeline(device: str, width: int, height: int,
                  framerate: int) -> str:
    """Build GStreamer pipeline string."""
    return (
        f'v4l2src device={device} io-mode=2 ! '
        f'image/jpeg, width={width}, height={height}, framerate={framerate}/1 ! '
        f'appsink name=sink max-buffers=2 drop=true'
    )


def _format_size(nbytes: int) -> str:
    """Human-readable byte size."""
    if nbytes >= 1024 * 1024:
        return f'{nbytes / (1024 * 1024):.1f} MB'
    if nbytes >= 1024:
        return f'{nbytes / 1024:.1f} KB'
    return f'{nbytes} B'

# ── node ───────────────────────────────────────────────────────────────────

class CameraPubNode(Node):
    """相机发布节点：MJPEG 直通 → /rov/camera/image_raw/compressed。

    Pipeline 错误（USB 断连、V4L2 报错等）后自动重启。
    """

    def __init__(self):
        super().__init__('camera_pub', namespace='rov')

        self.declare_parameters(
            namespace='',
            parameters=[
                ('device', '/dev/v4l/by-id/usb-H264_USB_Camera_H264_USB_Camera_2020032801-video-index0'),
                ('width', 640),
                ('height', 480),
                ('framerate', 15),
                ('publish_rate', 15.0),
                ('capture_timeout_ms', 200),
                ('status_interval_sec', 10.0),
                ('stall_warn_sec', 2.0),
                ('restart_cooldown_sec', 1.0),
                ('stall_restart_sec', 5.0),
            ],
        )

        # cache pipeline params for restart
        self._device_spec = self.get_parameter('device').value
        self._width = self.get_parameter('width').value
        self._height = self.get_parameter('height').value
        self._framerate = self.get_parameter('framerate').value
        publish_rate = self.get_parameter('publish_rate').value
        self._capture_timeout_ns = int(self.get_parameter('capture_timeout_ms').value * 1e6)
        self._status_interval_sec = self.get_parameter('status_interval_sec').value
        self._stall_warn_sec = self.get_parameter('stall_warn_sec').value
        self._restart_cooldown_sec = self.get_parameter('restart_cooldown_sec').value
        self._stall_restart_sec = self.get_parameter('stall_restart_sec').value

        # ── frame stats ──
        self._frame_total = 0
        self._frame_miss = 0
        self._frame_consecutive_miss = 0
        self._last_frame_time = time.monotonic()
        self._stall_reported = False
        self._frame_sizes = deque(maxlen=50)

        # ── pipeline state ──
        self._pipeline = None
        self._sink = None
        self._bus = None
        self._pipeline_error = False        # set by _poll_bus on ERROR/EOS
        self._restart_count = 0
        self._restart_fail_count = 0        # consecutive failures for backoff
        self._last_restart_time = 0.0

        Gst.init(None)

        # initial pipeline start
        if not self._start_pipeline():
            self.get_logger().error('Initial pipeline start failed — node idle')

        self._pub = self.create_publisher(
            CompressedImage, 'camera/image_raw/compressed', 10)
        period = 1.0 / publish_rate
        self._timer = self.create_timer(period, self._capture)

        self._status_timer = self.create_timer(
            self._status_interval_sec, self._dump_status)

        self.get_logger().info(
            f'rov_camera_pub started ({self._width}x{self._height}@{self._framerate}fps, '
            f'publish@{publish_rate:.0f}Hz, MJPEG passthrough, '
            f'capture_timeout={self._capture_timeout_ns // 1_000_000}ms)')

    # ── pipeline lifecycle ──────────────────────────────────────────────

    def _start_pipeline(self) -> bool:
        """Create and start a new GStreamer pipeline. Returns True on success.

        Always updates _last_restart_time so cooldown applies to failures too.
        """
        now = time.monotonic()
        self._last_restart_time = now

        # tear down old pipeline if any
        if self._pipeline is not None:
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            self._sink = None
            self._bus = None

        device, desc = _resolve_device(self._device_spec)
        pipeline_str = _gst_pipeline(device, self._width, self._height,
                                     self._framerate)
        self.get_logger().info(
            f'Starting pipeline [{self._restart_count + 1}]: {pipeline_str}')

        try:
            self._pipeline = Gst.parse_launch(pipeline_str)
        except Exception as exc:
            self.get_logger().error(f'Failed to parse pipeline: {exc}')
            self._pipeline = None
            self._restart_fail_count += 1
            return False

        self._sink = self._pipeline.get_by_name('sink')
        self._bus = self._pipeline.get_bus()
        self._bus.set_flushing(False)

        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.get_logger().error('Failed to set pipeline to PLAYING')
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            self._sink = None
            self._bus = None
            self._restart_fail_count += 1
            return False

        self._pipeline_error = False
        self._restart_count += 1
        self._restart_fail_count = 0
        self._stall_reported = False
        self.get_logger().info(
            f'Pipeline started successfully (attempt #{self._restart_count})')
        return True

    # ── GStreamer bus polling ──────────────────────────────────────────

    def _poll_bus(self):
        """Non-blocking drain of GStreamer bus messages (timeout=0, no GLib)."""
        if self._bus is None:
            return

        msg_types = (Gst.MessageType.ERROR | Gst.MessageType.WARNING |
                     Gst.MessageType.EOS | Gst.MessageType.STATE_CHANGED)
        while True:
            msg = self._bus.timed_pop_filtered(0, msg_types)
            if msg is None:
                break

            t = msg.type
            if t == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                self.get_logger().error(
                    f'GStreamer ERROR: {err.message} | debug: {debug}')
                self.get_logger().error(
                    f'GStreamer source: {msg.src.get_name() if msg.src else "unknown"}')
                self._pipeline_error = True
            elif t == Gst.MessageType.WARNING:
                err, debug = msg.parse_warning()
                self.get_logger().warn(
                    f'GStreamer WARNING: {err.message} | debug: {debug}')
            elif t == Gst.MessageType.EOS:
                self.get_logger().error('GStreamer EOS — pipeline ended unexpectedly')
                self._pipeline_error = True
            elif t == Gst.MessageType.STATE_CHANGED:
                old, new, pending = msg.parse_state_changed()
                if old is not None and new is not None:
                    src_name = msg.src.get_name() if msg.src else '?'
                    self.get_logger().debug(
                        f'GStreamer state: {src_name} {old.value_nick} → {new.value_nick}')

    # ── capture ─────────────────────────────────────────────────────────

    def _capture(self):
        """Timer callback: pull one frame (with timeout) and publish."""
        now = time.monotonic()

        # ── restart needed? ─────────────────────────────────────────
        need_restart = False
        restart_reason = ''

        if self._pipeline_error:
            need_restart = True
            restart_reason = 'pipeline error'
        elif (self._pipeline is not None and self._sink is not None
              and self._last_frame_time > 0):
            # silent stall detection: no error, but no frames for too long
            stall_duration = now - self._last_frame_time
            if stall_duration >= self._stall_restart_sec:
                need_restart = True
                restart_reason = f'silent stall ({stall_duration:.1f}s)'

        if need_restart:
            # exponential backoff: 1s, 2s, 4s, 8s... max 30s
            backoff = min(self._restart_cooldown_sec * (2 ** self._restart_fail_count), 30.0)
            if (now - self._last_restart_time) < backoff:
                return  # still cooling down

            self.get_logger().info(
                f'Attempting pipeline restart (#{self._restart_count + 1}) '
                f'due to {restart_reason} '
                f'(fail_count={self._restart_fail_count}, backoff={backoff:.1f}s)...')
            if self._start_pipeline():
                self.get_logger().info(
                    f'Pipeline restarted successfully (attempt #{self._restart_count})')
                # reset stall timer — pipeline is fresh
                self._last_frame_time = time.monotonic()
            else:
                self.get_logger().error(
                    f'Pipeline restart failed (fail_count={self._restart_fail_count}) '
                    f'— will retry after {backoff:.1f}s cooldown')
            return

        if self._pipeline is None or self._sink is None:
            return

        # drain GStreamer bus messages (non-blocking, timeout=0)
        self._poll_bus()
        # re-check: _poll_bus may have set _pipeline_error
        if self._pipeline_error:
            return

        # 使用 try-pull-sample + 超时，避免无限阻塞
        # 超时后返回 None，timer 回调正常结束，Ctrl+C 可响应
        try:
            sample = self._sink.emit('try-pull-sample', self._capture_timeout_ns)
        except Exception as exc:
            self.get_logger().error(
                f'try-pull-sample exception: {exc}', throttle_duration_sec=5.0)
            self._pipeline_error = True
            return

        if sample is None:
            self._frame_miss += 1
            self._frame_consecutive_miss += 1
            elapsed_since_last = now - self._last_frame_time

            if not self._stall_reported and elapsed_since_last >= self._stall_warn_sec:
                self.get_logger().warn(
                    f'Camera stalled — no frame for {elapsed_since_last:.1f}s '
                    f'({self._frame_consecutive_miss} consecutive misses)',
                    throttle_duration_sec=2.0)
                self._stall_reported = True
            return

        # got a frame
        self._stall_reported = False
        if self._frame_consecutive_miss > 0:
            self.get_logger().info(
                f'Camera recovered after {self._frame_consecutive_miss} misses '
                f'({now - self._last_frame_time:.1f}s gap)')
            self._frame_consecutive_miss = 0

        self._frame_total += 1
        self._last_frame_time = now

        buf = sample.get_buffer()
        ok, map_info = buf.map(Gst.MapFlags.READ)
        if not ok:
            return

        try:
            data = map_info.data
            self._frame_sizes.append(len(data))

            msg = CompressedImage()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'camera_link'
            msg.format = 'jpeg'
            msg.data = data
            self._pub.publish(msg)
        finally:
            buf.unmap(map_info)

    # ── 周期性状态日志 ──────────────────────────────────────────────────

    def _dump_status(self):
        """Periodic status report — runs on independent timer."""
        now = time.monotonic()
        elapsed = now - self._last_frame_time
        if self._frame_sizes:
            avg_size = sum(self._frame_sizes) / len(self._frame_sizes)
        else:
            avg_size = 0.0

        self.get_logger().info(
            f'[STATUS] '
            f'frames: total={self._frame_total} miss={self._frame_miss} '
            f'consec_miss={self._frame_consecutive_miss} '
            f'last_frame={elapsed:.1f}s ago '
            f'avg_size={_format_size(int(avg_size))} '
            f'restarts={self._restart_count} '
            f'fail={self._restart_fail_count} '
            f'error={self._pipeline_error}')

    # ── cleanup ─────────────────────────────────────────────────────────

    def destroy_node(self):
        self.get_logger().info(
            f'Destroying node — final stats: '
            f'total={self._frame_total} miss={self._frame_miss} '
            f'restarts={self._restart_count}')
        if self._pipeline is not None:
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraPubNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
