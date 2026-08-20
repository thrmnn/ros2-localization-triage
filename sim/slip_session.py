"""Drive a fixed route with NO injected faults, so the only variable is the tyre.

This is the control-and-treatment rig for the one authorised synthetic figure. Nothing
here teleports the robot or writes to any topic the detectors read. The robot drives the
same route every run; between runs the only difference is the wheel's slip compliance in
the physics solver.

That matters because it is the difference between a fault we authored and a fault the
estimator has to discover. When the tyre slips, wheel odometry over-reports distance while
the laser keeps telling AMCL where the robot really is, and the divergence between them is
a consequence, not a value we set.

The route is a closed loop so the robot stays inside the mapped area at every slip level.
A run that leaves the map would confound slip with being lost.
"""
from __future__ import annotations

import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool

DURATION_S = 120.0
# Straight, turn, straight, turn: a rectangle. Longitudinal slip shows on the straights,
# where wheel odometry accumulates the error it cannot see.
LEG_S = 6.0
LINEAR = 0.16
ANGULAR = 0.5


def _twist(lin: float, ang: float) -> Twist:
    t = Twist()
    t.linear.x = lin
    t.angular.z = ang
    return t


class SlipRun(Node):
    def __init__(self) -> None:
        super().__init__("slip_session")
        self.cmd = self.create_publisher(Twist, "/cmd_vel", 10)
        self.gate = self.create_publisher(Bool, "/scan_gate", 10)
        self.t0 = time.time()

    @property
    def t(self) -> float:
        return time.time() - self.t0

    def tick(self) -> bool:
        if self.t >= DURATION_S:
            self.cmd.publish(_twist(0.0, 0.0))
            return False
        phase = int(self.t // LEG_S) % 2
        self.cmd.publish(_twist(LINEAR, 0.0) if phase == 0 else _twist(0.0, ANGULAR))
        return True


def main() -> int:
    rclpy.init()
    node = SlipRun()
    node.gate.publish(Bool(data=True))
    node.get_logger().info(f"slip run: {DURATION_S:.0f} s, no injected faults")
    while rclpy.ok() and node.tick():
        rclpy.spin_once(node, timeout_sec=0.0)
        time.sleep(0.1)
    node.get_logger().info("slip run complete")
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
