"""
从 USB 摄像头采集 MJPEG 帧并发布为 sensor_msgs/CompressedImage 话题。

使用 GStreamer appsink 直接从 v4l2src 获取 JPEG 帧，
不做 MJPEG→BGR→JPEG 的徒劳往返，保持原始压缩数据。
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage


def _gst_pipeline(device: str, width: int, height: int,
                  framerate: int) -> str:
    """Build GStreamer pipeline that captures raw JPEG frames directly."""
    return (
        f'v4l2src device={device} io-mode=2 ! '
        f'image/jpeg, width={width}, height={height}, framerate={framerate}/1 ! '
        f'appsink name=sink max-buffers=2 drop=true'
    )


class CameraPubNode(Node):
    """相机发布节点：MJPEG 直通 → /rov/camera/image_raw/compressed。"""

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

        pipeline_str = _gst_pipeline(device, width, height, framerate)
        self.get_logger().info(f'Pipeline: {pipeline_str}')

        Gst.init(None)
        self._pipeline = Gst.parse_launch(pipeline_str)
        self._sink = self._pipeline.get_by_name('sink')

        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.get_logger().error('Failed to start GStreamer pipeline')
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            self._sink = None
            return

        self._pub = self.create_publisher(
            CompressedImage, 'camera/image_raw/compressed', 10)
        self._timer = self.create_timer(1.0 / publish_rate, self._capture)

        self.get_logger().info(
            f'rov_camera_pub started ({width}x{height}@{framerate}fps, '
            f'publish@{publish_rate:.0f}Hz, MJPEG passthrough)')

    def _capture(self):
        if self._pipeline is None:
            return

        # emit('pull-sample') is compatible with older GStreamer Python
        # bindings that lack try_pull_sample / pull_sample wrappers.
        sample = self._sink.emit('pull-sample')
        if sample is None:
            self.get_logger().warn(
                'No camera frame available', throttle_duration_sec=5.0)
            return

        buf = sample.get_buffer()
        ok, map_info = buf.map(Gst.MapFlags.READ)
        if not ok:
            return

        try:
            msg = CompressedImage()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'camera_link'
            msg.format = 'jpeg'
            msg.data = map_info.data
            self._pub.publish(msg)
        finally:
            buf.unmap(map_info)

    def destroy_node(self):
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
