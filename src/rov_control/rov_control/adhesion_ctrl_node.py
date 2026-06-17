import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32
from std_srvs.srv import Trigger
from mavros_msgs.msg import ManualControl


class RovAdhesionCtrlNode(Node):
    def __init__(self):
        super().__init__('adhesion_ctrl', namespace='rov')

        self._vertical_cmd = 0.0
        self._cb_group = MutuallyExclusiveCallbackGroup()

        self._sub = self.create_subscription(
            Float32, '/rov/depth_ctrl/vertical_cmd',
            self._vertical_cmd_callback, 10)

        self._pub = self.create_publisher(
            ManualControl, '/mavros/manual_control/send', 10)

        self._srv_toggle = self.create_service(
            Trigger, 'adhesion_ctrl/toggle_depth',
            self._toggle_depth_cb, callback_group=self._cb_group)

        self._depth_hold_client = self.create_client(
            Trigger, 'depth_ctrl/hold', callback_group=self._cb_group)

        self.get_logger().info('rov_adhesion_ctrl started')

    def _vertical_cmd_callback(self, msg):
        self._vertical_cmd = msg.data
        manual = ManualControl()
        manual.x = 0
        manual.y = 0
        manual.z = float(self._vertical_cmd)
        manual.r = 0
        self._pub.publish(manual)

    def _toggle_depth_cb(self, request, response):
        if not self._depth_hold_client.wait_for_service(timeout_sec=0.5):
            response.success = False
            response.message = 'rov_depth_ctrl hold service not available'
            return response

        future = self._depth_hold_client.call_async(request)
        future.add_done_callback(self._toggle_done_cb)

        response.success = True
        response.message = 'Toggle request forwarded'
        return response

    def _toggle_done_cb(self, future):
        try:
            response = future.result()
            self.get_logger().info(
                f'Toggle depth result: success={response.success}, '
                f'message="{response.message}"')
        except Exception as e:
            self.get_logger().error(f'Toggle depth call failed: {e}')

    def _wait_for_toggle(self, request, timeout_sec=1.0):
        future = self._depth_hold_client.call_async(request)
        import time
        start = time.time()
        while rclpy.ok() and not future.done():
            if time.time() - start > timeout_sec:
                return None
            time.sleep(0.05)
        if future.done():
            return future.result()
        return None


def main(args=None):
    rclpy.init(args=args)
    node = RovAdhesionCtrlNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
