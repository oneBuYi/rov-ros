import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float64, Float32, Bool
from std_srvs.srv import Trigger
from rov_msgs.srv import SetTarget, SetPIDGains
from rov_control.pid import PID


class RovDepthCtrlNode(Node):
    def __init__(self):
        super().__init__('depth_ctrl', namespace='rov')

        # Store default PID gains for reset
        self._default_gains = {
            'kp': 100.0,
            'ki': 40.0,
            'kd': 80.0,
        }

        self.declare_parameters(
            namespace='',
            parameters=[
                ('kp', self._default_gains['kp']),
                ('ki', self._default_gains['ki']),
                ('kd', self._default_gains['kd']),
                ('out_min', -100.0),
                ('out_max', 100.0),
                ('control_rate', 20.0),
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

        self._srv_set_gains = self.create_service(
            SetPIDGains, 'depth_ctrl/set_pid_gains',
            self._set_gains_cb, callback_group=self._cb_group)

        self._srv_reset_gains = self.create_service(
            Trigger, 'depth_ctrl/reset_pid_gains',
            self._reset_gains_cb, callback_group=self._cb_group)

        self._status_pub = self.create_publisher(
            Bool, 'depth_ctrl/status_hold', 10)

        self._gains_pub = self.create_publisher(
            Float32, 'depth_ctrl/pid_kp', 10)
        self._gains_pub_ki = self.create_publisher(
            Float32, 'depth_ctrl/pid_ki', 10)
        self._gains_pub_kd = self.create_publisher(
            Float32, 'depth_ctrl/pid_kd', 10)

        rate = self.get_parameter('control_rate').value
        self._timer = self.create_timer(1.0 / rate, self._control_loop)
        self._gains_timer = self.create_timer(1.0, self._publish_gains)

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

    def _set_gains_cb(self, request, response):
        """Set PID gains at runtime without resetting internal state,
        so the ROV does not momentarily lose control during hold."""
        self._pid.kp = request.kp
        self._pid.ki = request.ki
        self._pid.kd = request.kd
        response.success = True
        response.message = (
            f'Depth PID gains set: kp={request.kp:.1f}, '
            f'ki={request.ki:.1f}, kd={request.kd:.1f}'
        )
        self.get_logger().info(response.message)
        return response

    def _reset_gains_cb(self, request, response):
        """Reset PID gains to default values."""
        self._pid.kp = self._default_gains['kp']
        self._pid.ki = self._default_gains['ki']
        self._pid.kd = self._default_gains['kd']
        self._pid.reset()
        response.success = True
        response.message = (
            f'Depth PID gains reset to defaults: '
            f'kp={self._default_gains["kp"]:.1f}, '
            f'ki={self._default_gains["ki"]:.1f}, '
            f'kd={self._default_gains["kd"]:.1f}'
        )
        self.get_logger().info(response.message)
        return response

    def _publish_gains(self):
        """Periodically publish current PID gains for GCS display."""
        kp_msg = Float32()
        kp_msg.data = float(self._pid.kp)
        self._gains_pub.publish(kp_msg)
        ki_msg = Float32()
        ki_msg.data = float(self._pid.ki)
        self._gains_pub_ki.publish(ki_msg)
        kd_msg = Float32()
        kd_msg.data = float(self._pid.kd)
        self._gains_pub_kd.publish(kd_msg)


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
