import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32, Bool
from std_srvs.srv import Trigger
from mavros_msgs.msg import ManualControl


class RovAdhesionCtrlNode(Node):
    def __init__(self):
        super().__init__('adhesion_ctrl', namespace='rov')

        self._vertical_cmd = 0.0
        self._joystick_x = 0
        self._joystick_y = 0
        self._joystick_z = 0
        self._joystick_r = 0
        self._hold_enabled = False
        self._cb_group = MutuallyExclusiveCallbackGroup()

        self._sub_vertical = self.create_subscription(
            Float32, '/rov/depth_ctrl/vertical_cmd',
            self._on_vertical_cmd, 10)

        self._sub_joystick = self.create_subscription(
            ManualControl, '/rov/joystick/cmd',
            self._on_joystick_cmd, 10)

        self._sub_hold_status = self.create_subscription(
            Bool, '/rov/depth_ctrl/status',
            self._on_hold_status, 10)

        self._pub = self.create_publisher(
            ManualControl, '/mavros/manual_control/send', 10)

        self._srv_toggle = self.create_service(
            Trigger, 'adhesion_ctrl/toggle_depth',
            self._toggle_depth_cb, callback_group=self._cb_group)

        self._depth_hold_client = self.create_client(
            Trigger, 'depth_ctrl/hold', callback_group=self._cb_group)

        self.get_logger().info('rov_adhesion_ctrl started')

    def _on_vertical_cmd(self, msg):
        self._vertical_cmd = msg.data
        self._publish_merged()

    def _on_joystick_cmd(self, msg):
        self._joystick_x = int(msg.x)
        self._joystick_y = int(msg.y)
        self._joystick_z = int(msg.z)
        self._joystick_r = int(msg.r)
        self._publish_merged()

    def _on_hold_status(self, msg):
        self._hold_enabled = msg.data
        self._publish_merged()

    def _publish_merged(self):
        manual = ManualControl()
        manual.x = self._joystick_x
        manual.y = self._joystick_y
        manual.r = self._joystick_r
        manual.z = (
            float(self._vertical_cmd)
            if self._hold_enabled
            else float(self._joystick_z)
        )
        self._pub.publish(manual)

    def _toggle_depth_cb(self, request, response):
        if not self._depth_hold_client.wait_for_service(timeout_sec=0.5):
            response.success = False
            response.message = 'depth_ctrl hold service not available'
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
