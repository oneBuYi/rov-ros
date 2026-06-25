import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float64, Float32, Bool
from std_srvs.srv import Trigger
from rov_msgs.srv import SetTarget
from rov_control.pid import PID


class RovHeadingCtrlNode(Node):
    """航向（偏航角）定航控制节点。

    订阅 MAVROS compass_hdg 获取当前航向角（0-360°），通过 PID 计算偏航推力，
    发布到 heading_ctrl/pid_output。误差计算处理了角度环绕问题（最短路径）。
    """

    def __init__(self):
        super().__init__('heading_ctrl', namespace='rov')

        self.declare_parameters(
            namespace='',
            parameters=[
                ('kp', 80.0),
                ('ki', 20.0),
                ('kd', 40.0),
                ('out_min', -100.0),
                ('out_max', 100.0),
                ('control_rate', 10.0),
            ]
        )

        self._pid = PID(
            kp=self.get_parameter('kp').value,
            ki=self.get_parameter('ki').value,
            kd=self.get_parameter('kd').value,
            out_min=self.get_parameter('out_min').value,
            out_max=self.get_parameter('out_max').value,
        )

        self._target = 0.0
        self._enabled = False
        self._current_heading = 0.0

        self._cb_group = MutuallyExclusiveCallbackGroup()

        self._sub = self.create_subscription(
            Float64, '/mavros/global_position/compass_hdg',
            self._heading_callback, 10)

        self._pub = self.create_publisher(
            Float32, 'heading_ctrl/pid_output', 10)

        self._srv_set_target = self.create_service(
            SetTarget, 'heading_ctrl/set_target',
            self._set_target_cb, callback_group=self._cb_group)

        self._srv_hold = self.create_service(
            Trigger, 'heading_ctrl/toggle_hold',
            self._hold_cb, callback_group=self._cb_group)

        self._status_pub = self.create_publisher(
            Bool, 'heading_ctrl/status_hold', 10)

        rate = self.get_parameter('control_rate').value
        self._timer = self.create_timer(1.0 / rate, self._control_loop)

        self.get_logger().info('rov_heading_ctrl started')

    @staticmethod
    def _heading_error(target: float, current: float) -> float:
        """计算最短角度误差，处理 0°/360° 环绕。

        Args:
            target: 目标航向角 (degrees, 0-360).
            current: 当前航向角 (degrees, 0-360).

        Returns:
            最短角度误差 (degrees, -180..180)，正值表示需要右转（顺时针）。
        """
        return ((target - current + 180.0) % 360.0) - 180.0

    def _heading_callback(self, msg):
        self._current_heading = msg.data

    def _control_loop(self):
        if not self._enabled:
            return

        error = self._heading_error(self._target, self._current_heading)
        # 构造一个假的 measurement 使得 PID 内部
        # setpoint - measurement == error
        fake_measurement = self._target - error
        output = self._pid.update(self._target, fake_measurement)

        cmd = Float32()
        cmd.data = float(output)
        self._pub.publish(cmd)

    def _set_target_cb(self, request, response):
        target = request.target
        # 将目标角度归一化到 [0, 360)
        self._target = target % 360.0
        # Only reset PID if hold was previously disabled — avoids a
        # gratuitous 0-output cycle when simply changing the target.
        if not self._enabled:
            self._pid.reset()
        self._enabled = True
        msg = Bool()
        msg.data = self._enabled
        self._status_pub.publish(msg)
        response.success = True
        response.message = (
            f'Target heading set to {self._target:.1f}°, hold enabled'
        )
        self.get_logger().info(response.message)
        return response

    def _hold_cb(self, request, response):
        self._enabled = not self._enabled
        msg = Bool()
        msg.data = self._enabled
        self._status_pub.publish(msg)
        self._pid.reset()
        if self._enabled:
            self._target = self._current_heading
            response.message = (
                f'Heading hold enabled at {self._current_heading:.1f}°'
            )
        else:
            response.message = 'Heading hold disabled'
        response.success = True
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RovHeadingCtrlNode()
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
