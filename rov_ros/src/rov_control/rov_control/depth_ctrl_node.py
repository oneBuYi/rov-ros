"""rov_depth_ctrl — ROS2 定深控制节点。

订阅 /mavros/global_position/rel_alt 获取深度（relative_alt），
PID 计算后发布 /rov/depth/vertical_cmd。

服务:
  /rov/depth/set_target   — 设置目标深度
  /rov/depth/hold         — 切换定深保持启用/禁用
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

from std_msgs.msg import Float32, Float64
from std_srvs.srv import Trigger
from rov_msgs.srv import SetTarget

from rov_control.pid import PID


class DepthCtrlNode(Node):
    def __init__(self):
        super().__init__('rov_depth_ctrl')

        # 参数
        self.declare_parameter('kp', 100.0)
        self.declare_parameter('ki', 40.0)
        self.declare_parameter('kd', 80.0)
        self.declare_parameter('out_min', -100.0)
        self.declare_parameter('out_max', 100.0)
        self.declare_parameter('control_rate', 10.0)

        # PID 控制器
        self._pid = PID(
            kp=self.get_parameter('kp').value,
            ki=self.get_parameter('ki').value,
            kd=self.get_parameter('kd').value,
            out_min=self.get_parameter('out_min').value,
            out_max=self.get_parameter('out_max').value,
        )

        self._target = None
        self._hold_enabled = False
        self._current_depth = None

        # 发布者
        self._cmd_pub = self.create_publisher(Float32, '/rov/depth/vertical_cmd', 10)

        # 订阅者：mavros/global_position/rel_alt（Float64 多少米）
        self._sub = self.create_subscription(
            Float64,
            '/mavros/global_position/rel_alt',
            self._depth_callback,
            10,
        )

        # 服务
        svc_cb = MutuallyExclusiveCallbackGroup()
        self._set_target_srv = self.create_service(
            SetTarget, '/rov/depth/set_target', self._set_target_cb, callback_group=svc_cb
        )
        self._hold_srv = self.create_service(
            Trigger, '/rov/depth/hold', self._hold_cb, callback_group=svc_cb
        )

        # 控制 Timer
        rate = self.get_parameter('control_rate').value
        self._timer = self.create_timer(1.0 / rate, self._control_step)

        self.get_logger().info('Depth controller started')

    def _depth_callback(self, msg):
        """mavros global_position/rel_alt: depth = -relative_alt"""
        self._current_depth = msg.data * -1.0

    def _control_step(self):
        """10 Hz PID 控制循环"""
        if not self._hold_enabled:
            return
        if self._current_depth is None:
            self.get_logger().warn('No depth data yet', throttle_duration_sec=5.0)
            return
        if self._target is None:
            return

        output = self._pid.update(self._target, self._current_depth)

        msg = Float32()
        msg.data = output
        self._cmd_pub.publish(msg)

    def _set_target_cb(self, request, response):
        self._target = request.target
        self._pid.reset()
        response.success = True
        response.message = f'Target depth set to {self._target:.2f}m'
        self.get_logger().info(response.message)
        return response

    def _hold_cb(self, request, response):
        self._hold_enabled = not self._hold_enabled

        if self._hold_enabled:
            if self._current_depth is not None:
                self._target = self._current_depth
            self._pid.reset()
            msg = f'Hold enabled, target={self._target}'
        else:
            self._pid.reset()
            msg = 'Hold disabled'

        response.success = True
        response.message = msg
        self.get_logger().info(msg)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = DepthCtrlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
