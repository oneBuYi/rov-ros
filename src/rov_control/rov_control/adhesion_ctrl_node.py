import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32, Bool
from std_srvs.srv import Trigger
from mavros_msgs.msg import ManualControl


class RovAdhesionCtrlNode(Node):
    """合并节点：将 PID 控制输出与手柄指令合并后发送给飞控。

    输入源：
    - depth_ctrl 的垂直 PWM 和定深状态 → z 通道
    - heading_ctrl 的偏航 PWM 和定航状态 → r 通道
    - 手柄指令 → x, y 通道（以及 z/r 在未启用 hold 时）

    合并逻辑：
    - x, y: 始终来自手柄
    - z: 定深 hold 启用时使用 PID 输出，否则使用手柄 z 轴值
    - r: 定航 hold 启用时使用 PID 输出，否则使用手柄 r 轴值
    """

    def __init__(self):
        super().__init__('adhesion_ctrl', namespace='rov')

        self._vertical_pwm = 0.0
        self._yaw_pwm = 0.0
        self._joystick_x = 0.0
        self._joystick_y = 0.0
        self._joystick_z = 0.0
        self._joystick_r = 0.0
        self._joystick_buttons = 0
        self._depth_hold_enabled = False
        self._heading_hold_enabled = False
        self._cb_group = MutuallyExclusiveCallbackGroup()

        # --- depth hold inputs ---
        self._sub_vertical = self.create_subscription(
            Float32, '/rov/depth_ctrl/pid_output',
            self._on_vertical_pwm, 10)

        self._sub_depth_hold = self.create_subscription(
            Bool, '/rov/depth_ctrl/status_hold',
            self._on_depth_hold_status, 10)

        # --- heading hold inputs ---
        self._sub_yaw = self.create_subscription(
            Float32, '/rov/heading_ctrl/pid_output',
            self._on_yaw_pwm, 10)

        self._sub_heading_hold = self.create_subscription(
            Bool, '/rov/heading_ctrl/status_hold',
            self._on_heading_hold_status, 10)

        # --- joystick input ---
        self._sub_joystick = self.create_subscription(
            ManualControl, '/rov/joystick_ctrl/cmd',
            self._on_joystick_cmd, 10)

        # --- merged output ---
        self._pub = self.create_publisher(
            ManualControl, '/mavros/manual_control/send', 10)

        # --- toggle depth forwarding ---
        self._srv_toggle_depth = self.create_service(
            Trigger, 'adhesion_ctrl/toggle_depth',
            self._toggle_depth_cb, callback_group=self._cb_group)

        self._depth_hold_client = self.create_client(
            Trigger, 'depth_ctrl/toggle_hold', callback_group=self._cb_group)

        # --- toggle heading forwarding ---
        self._srv_toggle_heading = self.create_service(
            Trigger, 'adhesion_ctrl/toggle_heading',
            self._toggle_heading_cb, callback_group=self._cb_group)

        self._heading_hold_client = self.create_client(
            Trigger, 'heading_ctrl/toggle_hold', callback_group=self._cb_group)

        self.get_logger().info('rov_adhesion_ctrl started')

    def _on_vertical_pwm(self, msg):
        self._vertical_pwm = msg.data
        self._publish_merged()

    def _on_yaw_pwm(self, msg):
        self._yaw_pwm = msg.data
        self._publish_merged()

    def _on_joystick_cmd(self, msg):
        self._joystick_x = float(msg.x)
        self._joystick_y = float(msg.y)
        self._joystick_z = float(msg.z)
        self._joystick_r = float(msg.r)
        self._joystick_buttons = int(msg.buttons)
        self._publish_merged()

    def _on_depth_hold_status(self, msg):
        self._depth_hold_enabled = msg.data
        self._publish_merged()

    def _on_heading_hold_status(self, msg):
        self._heading_hold_enabled = msg.data
        self._publish_merged()

    # Scale factor: internal range ±100 → MAVLink range ±1000
    SCALE = 10.0

    def _publish_merged(self):
        manual = ManualControl()
        manual.x = self._joystick_x * self.SCALE
        manual.y = self._joystick_y * self.SCALE
        manual.z = (
            float(self._vertical_pwm)
            if self._depth_hold_enabled
            else float(self._joystick_z)
        ) * self.SCALE
        manual.r = (
            float(self._yaw_pwm)
            if self._heading_hold_enabled
            else float(self._joystick_r)
        ) * self.SCALE
        manual.buttons = self._joystick_buttons
        self._pub.publish(manual)

    # ----- toggle depth (existing) -----

    def _toggle_depth_cb(self, request, response):
        if not self._depth_hold_client.wait_for_service(timeout_sec=0.5):
            response.success = False
            response.message = 'depth_ctrl hold service not available'
            return response

        future = self._depth_hold_client.call_async(request)
        future.add_done_callback(self._toggle_depth_done_cb)

        response.success = True
        response.message = 'Toggle depth request forwarded'
        return response

    def _toggle_depth_done_cb(self, future):
        try:
            response = future.result()
            self.get_logger().info(
                f'Toggle depth result: success={response.success}, '
                f'message="{response.message}"')
        except Exception as e:
            self.get_logger().error(f'Toggle depth call failed: {e}')

    # ----- toggle heading (new) -----

    def _toggle_heading_cb(self, request, response):
        if not self._heading_hold_client.wait_for_service(timeout_sec=0.5):
            response.success = False
            response.message = 'heading_ctrl hold service not available'
            return response

        future = self._heading_hold_client.call_async(request)
        future.add_done_callback(self._toggle_heading_done_cb)

        response.success = True
        response.message = 'Toggle heading request forwarded'
        return response

    def _toggle_heading_done_cb(self, future):
        try:
            response = future.result()
            self.get_logger().info(
                f'Toggle heading result: success={response.success}, '
                f'message="{response.message}"')
        except Exception as e:
            self.get_logger().error(f'Toggle heading call failed: {e}')


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
