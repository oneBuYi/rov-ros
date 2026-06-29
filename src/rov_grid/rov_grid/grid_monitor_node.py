import math
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float64, Bool, Int32
from sensor_msgs.msg import NavSatFix
from rov_msgs.srv import SetGridTarget


def haversine_distance(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
    """Calculate horizontal distance (m) between two WGS84 coordinates.

    Uses the Haversine formula with Earth mean radius 6371000 m.
    Accurate to sub-meter for the short distances used in grid checking.
    """
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2.0) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2)
    a = min(a, 1.0)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class GridMonitorNode(Node):
    """Monitor whether the ROV is inside the target pool-wall grid cell.

    Subscribes to MAVROS global position (lat/lon) and relative altitude
    (negated to get depth).  At ``control_rate`` Hz, computes horizontal
    distance via Haversine and checks against the depth window.  Publishes
    ``in_target`` (Bool) continuously; ``target_row`` / ``target_col``
    only when the target changes.
    """

    def __init__(self):
        super().__init__('grid_monitor', namespace='rov')

        self.declare_parameters(
            namespace='',
            parameters=[
                ('grids', []),
                ('distance_threshold', 0.5),
                ('depth_threshold', 0.2),
                ('control_rate', 10.0),
            ],
        )

        self._distance_threshold = self.get_parameter('distance_threshold').value
        self._depth_threshold = self.get_parameter('depth_threshold').value

        self._grids = {}          # {(row, col): (lat, lon, depth)}
        self._target_key = None    # (row, col) or None
        self._current_lat = 0.0
        self._current_lon = 0.0
        self._current_depth = 0.0
        self._lat_lon_ready = False
        self._depth_ready = False

        self._load_grids()

        self._cb_group = MutuallyExclusiveCallbackGroup()

        # --- Subscriptions ---
        self._sub_navsat = self.create_subscription(
            NavSatFix,
            '/mavros/global_position/global',
            self._navsat_callback,
            10,
        )

        self._sub_rel_alt = self.create_subscription(
            Float64,
            '/mavros/global_position/rel_alt',
            self._rel_alt_callback,
            10,
        )

        # --- Publishers ---
        self._pub_in_target = self.create_publisher(
            Bool, 'grid/in_target', 10,
        )
        self._pub_target_row = self.create_publisher(
            Int32, 'grid/target_row', 10,
        )
        self._pub_target_col = self.create_publisher(
            Int32, 'grid/target_col', 10,
        )

        # --- Service ---
        self._srv_set_target = self.create_service(
            SetGridTarget,
            'grid/set_grid_target',
            self._set_target_cb,
            callback_group=self._cb_group,
        )

        # --- Timer ---
        rate = self.get_parameter('control_rate').value
        self._timer = self.create_timer(1.0 / rate, self._control_loop)

        self.get_logger().info(
            f'grid_monitor started with {len(self._grids)} grid cells loaded'
        )

    # ------------------------------------------------------------------
    # Grid loading
    # ------------------------------------------------------------------

    def _load_grids(self):
        """Load grid points from the ROS parameter into ``self._grids``."""
        raw = self.get_parameter('grids').value
        if not raw:
            self.get_logger().error(
                'No grids configured — pool_wall_grid.yaml may be missing '
                'or empty. in_target will always be False.'
            )
            return

        for item in raw:
            try:
                row = int(item['row'])
                col = int(item['col'])
                lat = float(item['lat'])
                lon = float(item['lon'])
                depth_val = float(item['depth'])
            except (KeyError, TypeError, ValueError) as e:
                self.get_logger().error(
                    f'Skipping malformed grid entry {item}: {e}'
                )
                continue

            key = (row, col)
            if key in self._grids:
                self.get_logger().warning(
                    f'Duplicate grid ({row}, {col}) — overwriting'
                )
            self._grids[key] = (lat, lon, depth_val)

        if not self._grids:
            self.get_logger().error(
                'No valid grids loaded after parsing — all entries were malformed'
            )

    # ------------------------------------------------------------------
    # MAVROS callbacks
    # ------------------------------------------------------------------

    def _navsat_callback(self, msg: NavSatFix):
        self._current_lat = msg.latitude
        self._current_lon = msg.longitude
        self._lat_lon_ready = True

    def _rel_alt_callback(self, msg: Float64):
        # rel_alt: positive = above water surface.  We want depth
        # (positive = below surface), so negate.
        self._current_depth = -msg.data
        self._depth_ready = True

    # ------------------------------------------------------------------
    # Control loop (timer)
    # ------------------------------------------------------------------

    def _control_loop(self):
        msg = Bool()

        if self._target_key is None:
            msg.data = False
            self._pub_in_target.publish(msg)
            return

        if not (self._lat_lon_ready and self._depth_ready):
            msg.data = False
            self._pub_in_target.publish(msg)
            return

        grid_lat, grid_lon, grid_depth = self._grids[self._target_key]

        dist = haversine_distance(
            self._current_lat, self._current_lon,
            grid_lat, grid_lon,
        )
        depth_ok = abs(self._current_depth - grid_depth) < self._depth_threshold
        dist_ok = dist < self._distance_threshold

        msg.data = dist_ok and depth_ok
        self._pub_in_target.publish(msg)

    # ------------------------------------------------------------------
    # Service callback
    # ------------------------------------------------------------------

    def _set_target_cb(self, request, response):
        row = request.row
        col = request.col
        key = (row, col)

        if key not in self._grids:
            response.success = False
            response.message = (
                f'Grid ({row}, {col}) not found in configured grid list'
            )
            self.get_logger().warning(response.message)
            return response

        self._target_key = key

        # Publish the new target row/col
        row_msg = Int32()
        row_msg.data = row
        self._pub_target_row.publish(row_msg)

        col_msg = Int32()
        col_msg.data = col
        self._pub_target_col.publish(col_msg)

        response.success = True
        response.message = (
            f'Target grid set to ({row}, {col}) '
            f'at lat={self._grids[key][0]:.6f}, '
            f'lon={self._grids[key][1]:.6f}, '
            f'depth={self._grids[key][2]:.2f}m'
        )
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = GridMonitorNode()
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
