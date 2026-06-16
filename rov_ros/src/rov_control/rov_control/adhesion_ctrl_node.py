"""rov_adhesion_ctrl — ROS2 仲裁节点。

订阅 /rov/depth/vertical_cmd，转发为 /mavros/manual_control/control。
manual_control 唯一发布者，预留为手柄 + PID 仲裁汇合点。

服务:
  /rov/adhesion/toggle_depth  — 转发到 /rov/depth/hold
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

from std_msgs.msg import Float32
from std_srvs.srv import Trigger
from mavros_msgs.msg import ManualControl


class AdhesionCtrlNode(Node):
    def __init__(self):
        super().__init__('rov_adhesion_ctrl')

        # manual_control 发布者（唯一出口）
        self._mc_pub = self.create_publisher(ManualControl, '/mavros/manual_control/control', 10)

        # 订阅 depth vertical_cmd
        self._cmd_sub = self.create_subscription(
            Float32,
            '/rov/depth/vertical_cmd',
            self._vertical_cmd_callback,
            10,
        )

        # 服务：toggle_depth
        self._hold_client = self.create_client(Trigger, '/rov/depth/hold')

        cb_group = MutuallyExclusiveCallbackGroup()
        self._toggle_srv = self.create_service(
            Trigger, '/rov/adhesion/toggle_depth', self._toggle_cb, callback_group=cb_group
        )

        self.get_logger().info('Adhesion controller started')

    def _vertical_cmd_callback(self, msg):
        """转发 vertical_cmd → manual_control.z"""
        mc = ManualControl()
        mc.x = 0.0
        mc.y = 0.0
        mc.z = float(msg.data)
        mc.r = 0.0
        self._mc_pub.publish(mc)

    def _toggle_cb(self, request, response):
        """转发 toggle 到 /rov/depth/hold"""
        if not self._hold_client.wait_for_service(timeout_sec=2.0):
            response.success = False
            response.message = '/rov/depth/hold service not available'
            return response

        future = self._hold_client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

        if future.done() and future.result() is not None:
            response = future.result()
        else:
            response.success = False
            response.message = 'Call to /rov/depth/hold failed'

        return response


def main(args=None):
    rclpy.init(args=args)
    node = AdhesionCtrlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
