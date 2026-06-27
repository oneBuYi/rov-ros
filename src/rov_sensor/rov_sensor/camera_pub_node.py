"""
从 USB 摄像头采集图像并发布为 ROS2 sensor_msgs/Image 话题。

使用 Jetson NVV4L2 硬件加速解码 MJPEG，通过 GStreamer pipeline
将解码后的 BGR 帧输出给 OpenCV，通过 cv_bridge 构造 Image 消息。
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import cv2


def _gst_pipeline(device: str, width: int, height: int,
                  framerate: int) -> str:
    """构建 GStreamer pipeline（NVV4L2 硬件解码 MJPEG → BGR）。"""
    return (
        f'v4l2src device={device} io-mode=2 ! '
        f'image/jpeg, width={width}, height={height}, framerate={framerate}/1 ! '
        'nvv4l2decoder mjpeg=1 ! '
        'nvvidconv ! '
        'video/x-raw, format=I420 ! '
        'videoconvert ! '
        'video/x-raw, format=BGR ! '
        'appsink drop=true max-buffers=2'
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
            ],
        )

        device = self.get_parameter('device').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        framerate = self.get_parameter('framerate').value
        publish_rate = self.get_parameter('publish_rate').value

        pipeline = _gst_pipeline(device, width, height, framerate)
        self.get_logger().info(f'Opening camera: {pipeline}')

        self._cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._cap.isOpened():
            self.get_logger().error(f'Failed to open camera: {device}')
            self._cap = None

        self._bridge = CvBridge()
        self._pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self._timer = self.create_timer(1.0 / publish_rate, self._capture)

        self.get_logger().info(
            f'rov_camera_pub started ({width}x{height}@{framerate}fps, '
            f'publish@{publish_rate:.0f}Hz)')

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
