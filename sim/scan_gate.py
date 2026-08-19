"""Relay /scan -> /scan_amcl, dropping every message inside a dropout window.

AMCL is pointed at /scan_amcl (see params/nav2_localization.yaml) while the bag
records the untouched /scan, so the recording keeps both what the sensor really
saw and what the localiser was actually given.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool


class ScanGate(Node):
    def __init__(self) -> None:
        super().__init__("scan_gate")
        self.open = True
        self.pub = self.create_publisher(LaserScan, "/scan_amcl", qos_profile_sensor_data)
        self.create_subscription(LaserScan, "/scan", self.on_scan, qos_profile_sensor_data)
        self.create_subscription(Bool, "/chaos/scan_gate", self.on_cmd, 10)

    def on_cmd(self, msg: Bool) -> None:
        self.open = msg.data
        self.get_logger().info(f"scan gate {'open' if self.open else 'CLOSED'}")

    def on_scan(self, msg: LaserScan) -> None:
        if self.open:
            self.pub.publish(msg)


def main() -> None:
    rclpy.init()
    rclpy.spin(ScanGate())


if __name__ == "__main__":
    main()
