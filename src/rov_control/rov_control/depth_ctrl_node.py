import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float64, Float32, Bool
from std_srvs.srv import Trigger
from rov_msgs.srv import SetTarget
from rov_control.pid import PID


class RovDepthCtrlNode(Node):
    def __init__(self):
        super().__init__('depth_ctrl', namespace='rov')

        self.declare_parameters(
            namespace='',
            parameters=[
                ('kp', 100.0),
                ('ki', 40.0),
                ('kd', 80.0),
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
        self._current_depth = 0.0

        self._cb_group = MutuallyExclusiveCallbackGroup()

        self._sub = self.create_subscription(
            Float64, '/mavros/global_position/rel_alt',
            self._depth_callback, qos_profile_sensor_data)

        self._pub = self.create_publisher(
            Float32, 'depth_ctrl/pid_output', 10)

        self._srv_set_target = self.create_service(
            SetTarget, 'depth_ctrl/set_target',
            self._set_target_cb, callback_group=self._cb_group)

        self._srv_hold = self.create_service(
            Trigger, 'depth_ctrl/toggle_hold',
            self._hold_cb, callback_group=self._cb_group)

        self._status_pub = self.create_publisher(
            Bool, 'depth_ctrl/status_hold', 10)

        rate = self.get_parameter('control_rate').value
        self._timer = self.create_timer(1.0 / rate, self._control_loop)

        self.get_logger().info('rov_depth_ctrl started')

    def _depth_callback(self, msg):
        self._current_depth = msg.data * -1.0

    def _control_loop(self):
        if not self._enabled:
            return
        output = self._pid.update(self._target, self._current_depth)
        # PID error = target - current. When current > target (too deep),
        # error is negative. ArduSub ManualControl z maps 0=down, 500=neutral,
        # 1000=up. Negate so that too-deep → positive cmd → z > 500 → ascend.
        cmd = Float32()
        cmd.data = float(-output)
        self._pub.publish(cmd)

    def _set_target_cb(self, request, response):
        self._target = request.target
        # Only reset PID if hold was previously disabled — avoids a
        # gratuitous 0-output cycle when simply changing the target.
        if not self._enabled:
            self._pid.reset()
        self._enabled = True
        msg = Bool()
        msg.data = self._enabled
        self._status_pub.publish(msg)
        response.success = True
        response.message = f'Target depth set to {request.target:.2f}m, hold enabled'
        self.get_logger().info(response.message)
        return response

    def _hold_cb(self, request, response):
        self._enabled = not self._enabled
        msg = Bool()
        msg.data = self._enabled
        self._status_pub.publish(msg)
        self._pid.reset()
        if self._enabled:
            self._target = self._current_depth
            response.message = f'Hold enabled at {self._current_depth:.2f}m'
        else:
            response.message = 'Hold disabled'
        response.success = True
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RovDepthCtrlNode()
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
