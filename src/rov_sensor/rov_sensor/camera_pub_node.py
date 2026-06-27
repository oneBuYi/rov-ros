"""
从 USB 摄像头采集图像并发布为 ROS2 sensor_msgs/Image 话题。

使用 Jetson NVV4L2 硬件加速解码 MJPEG，通过 GStreamer pipeline
将解码后的 BGR 帧输出给 OpenCV，通过 cv_bridge 构造 Image 消息。
"""

import re

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import cv2


def _parse_gcs_url(url: str):
    """Parse MAVROS-style gcs_url for GStreamer udpsink.

    Formats:
      udp-b://@host:port  → broadcast (host=255.255.255.255)
      udp-b://@:port      → broadcast (host=255.255.255.255)
      udp://host:port     → unicast to host

    Returns (host, port, is_broadcast).
    """
    m = re.match(r'(udp(?:-b)?)://(?:@)?([^:]*):(\d+)$', url)
    if not m:
        raise ValueError(f'Invalid gcs_url: {url}')

    scheme = m.group(1)      # 'udp-b' or 'udp'
    bind_addr = m.group(2)   # host part (may be empty, e.g. '@:5600')
    port = int(m.group(3))

    is_broadcast = scheme == 'udp-b'
    host = '255.255.255.255' if is_broadcast else (bind_addr or '127.0.0.1')

    return host, port, is_broadcast


def _gst_pipeline(device: str, width: int, height: int,
                  framerate: int, gcs_url: str = '',
                  bitrate: int = 3000000) -> str:
    """Build GStreamer pipeline with optional H.264 UDP video stream.

    When gcs_url is non-empty, inserts a tee after the hardware decoder
    and sends H.264-encoded video over RTP/UDP via a second branch.
    """
    base = (
        f'v4l2src device={device} io-mode=2 ! '
        f'image/jpeg, width={width}, height={height}, framerate={framerate}/1 ! '
        f'nvv4l2decoder mjpeg=1 ! '
    )

    # BGR → ROS topic branch (always present)
    bgr_branch = (
        'nvvidconv ! '
        'video/x-raw, format=I420 ! '
        'videoconvert ! '
        'video/x-raw, format=BGR ! '
        'appsink drop=true max-buffers=2'
    )

    if not gcs_url:
        return base + bgr_branch

    # Parse gcs_url for UDP branch
    host, port, is_broadcast = _parse_gcs_url(gcs_url)

    h264_branch = (
        f'queue ! '
        f'nvvidconv ! '
        f'video/x-raw(memory:NVMM), width={width}, height={height}, format=NV12 ! '
        f'nvv4l2h264enc bitrate={bitrate} iframeinterval=7 insert-sps-pps=true ! '
        f'h264parse ! '
        f'rtph264pay config-interval=1 pt=96 mtu=1400 ! '
        f'udpsink host={host} port={port} sync=false'
    )

    return (
        f'{base}'
        f'tee name=t ! '
        f'queue ! {bgr_branch} '
        f't. ! {h264_branch}'
    )


class CameraPubNode(Node):
    """相机发布节点：采集 USB 摄像头图像 → /rov/camera/image_raw。"""

    def __init__(self):
        super().__init__('camera_pub', namespace='rov')

        self.declare_parameters(
            namespace='',
            parameters=[
                ('device', '/dev/video0'),
                ('width', 640),
                ('height', 480),
                ('framerate', 15),
                ('publish_rate', 15.0),
                ('gcs_url', ''),
                ('bitrate', 3000000),
            ],
        )

        device = self.get_parameter('device').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        framerate = self.get_parameter('framerate').value
        publish_rate = self.get_parameter('publish_rate').value
        gcs_url = self.get_parameter('gcs_url').value
        bitrate = self.get_parameter('bitrate').value

        if gcs_url:
            try:
                _parse_gcs_url(gcs_url)
            except ValueError as e:
                self.get_logger().warn(
                    f'Invalid gcs_url "{gcs_url}": {e}. UDP stream disabled.'
                )
                gcs_url = ''

        pipeline = _gst_pipeline(device, width, height, framerate, gcs_url, bitrate)
        self.get_logger().info(f'Opening camera: {pipeline}')

        self._cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._cap.isOpened():
            self.get_logger().error(f'Failed to open camera: {device}')
            self._cap = None

        self._bridge = CvBridge()
        self._pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self._timer = self.create_timer(1.0 / publish_rate, self._capture)

        udp_info = f', H.264 UDP→{gcs_url}@{bitrate//1000}kbps' if gcs_url else ''
        self.get_logger().info(
            f'rov_camera_pub started ({width}x{height}@{framerate}fps, '
            f'publish@{publish_rate:.0f}Hz{udp_info})')

    def _capture(self):
        if self._cap is None:
            return

        ret, frame = self._cap.read()
        if not ret or frame is None:
            self.get_logger().warn(
                'Failed to read camera frame', throttle_duration_sec=5.0)
            return

        msg = self._bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_link'
        self._pub.publish(msg)

    def destroy_node(self):
        if self._cap is not None:
            self._cap.release()
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
