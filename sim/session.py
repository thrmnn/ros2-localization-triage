"""Drive the robot, inject faults on a fixed schedule, and tag every incident live.

Tags go out on /incident_marker and are recorded into the same bag as the signals
they describe, so ground truth is in-band and timestamped by the same clock --
not reconstructed afterwards from memory.

Schedule is deliberately front-loaded with clean driving: days 3-5 calibrate
thresholds against this recording's real noise floor, and a recording with no
quiet stretches has no noise floor to measure.
"""
import json
import math
import sys
import time

import rclpy
from gazebo_msgs.srv import GetEntityState, GetModelList, SetEntityState
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String

DRIVE_LINEAR = 0.12
DRIVE_ANGULAR = 0.35   # ~0.35 m radius circle: continuous motion, clear of the world's pillars

# (t_seconds, action, payload). Everything between entries is clean driving.
SCHEDULE = [
    (60.0,  "begin", {"id": "inc-01", "kind": "scan_dropout",
                      "note": "laser starved for 25 s; AMCL runs open-loop on odometry"}),
    (85.0,  "end",   {"id": "inc-01"}),
    (145.0, "begin", {"id": "inc-02", "kind": "wheel_slip",
                      "note": "body displaced against travel while wheels keep turning"}),
    (175.0, "end",   {"id": "inc-02"}),
    (235.0, "begin", {"id": "inc-03", "kind": "kidnap",
                      "note": "instantaneous 0.9 m displacement; particle filter must recover"}),
    (238.0, "end",   {"id": "inc-03"}),
    (330.0, "stop",  {}),
]


class Session(Node):
    def __init__(self) -> None:
        super().__init__("chaos_session")
        self.cmd = self.create_publisher(Twist, "/cmd_vel", 10)
        self.gate = self.create_publisher(Bool, "/chaos/scan_gate", 10)
        self.marker = self.create_publisher(String, "/incident_marker", 10)
        self.get_state = self.create_client(GetEntityState, "/gazebo/get_entity_state")
        self.set_state = self.create_client(SetEntityState, "/gazebo/set_entity_state")
        self.model_list = self.create_client(GetModelList, "/get_model_list")
        self.entity: str | None = None
        self.active: dict[str, dict] = {}
        self.t = 0.0
        self.next = 0
        self.done = False

    # --- helpers -----------------------------------------------------------
    def call(self, client, req):
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        return future.result()

    def find_entity(self) -> str:
        self.model_list.wait_for_service(timeout_sec=30.0)
        res = self.call(self.model_list, GetModelList.Request())
        for name in res.model_names:
            if name not in ("ground_plane", "turtlebot3_world", "sun"):
                return name
        raise RuntimeError(f"no robot model among {res.model_names}")

    def tag(self, phase: str, payload: dict) -> None:
        body = {"phase": phase, "source": "synthetic", "t_rel": round(self.t, 2), **payload}
        self.marker.publish(String(data=json.dumps(body, sort_keys=True)))
        self.get_logger().info(f"INCIDENT {phase}: {body}")

    def displace(self, forward: float, lateral: float = 0.0) -> None:
        """Shift the robot in its OWN frame -- a world-frame nudge would mean
        something different at every point on a circular route."""
        req = GetEntityState.Request()
        req.name = self.entity
        cur = self.call(self.get_state, req)
        if cur is None:
            self.get_logger().warn("get_entity_state timed out; displacement skipped")
            return
        q = cur.state.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        s = SetEntityState.Request()
        s.state.name = self.entity
        s.state.pose = cur.state.pose
        s.state.pose.position.x += forward * math.cos(yaw) - lateral * math.sin(yaw)
        s.state.pose.position.y += forward * math.sin(yaw) + lateral * math.cos(yaw)
        self.call(self.set_state, s)

    def teleport_inward(self, dist: float) -> None:
        """Kidnap toward the middle of the arena. Along the robot's own heading a
        0.9 m jump can land it inside a wall, where the laser sees nothing and the
        incident stops being a localization failure and starts being a broken bag."""
        req = GetEntityState.Request()
        req.name = self.entity
        cur = self.call(self.get_state, req)
        if cur is None:
            self.get_logger().warn("get_entity_state timed out; kidnap skipped")
            return
        px, py = cur.state.pose.position.x, cur.state.pose.position.y
        norm = math.hypot(px, py) or 1.0
        s = SetEntityState.Request()
        s.state.name = self.entity
        s.state.pose = cur.state.pose
        s.state.pose.position.x = px - dist * px / norm
        s.state.pose.position.y = py - dist * py / norm
        self.call(self.set_state, s)

    # --- fault actions -----------------------------------------------------
    def begin(self, spec: dict) -> None:
        kind = spec["kind"]
        if kind == "scan_dropout":
            self.gate.publish(Bool(data=False))
        elif kind == "kidnap":
            self.teleport_inward(0.9)
        elif kind == "wheel_slip":
            self.active["wheel_slip"] = spec
        self.tag("begin", spec)

    def end(self, spec: dict) -> None:
        for kind, live in list(self.active.items()):
            if live["id"] == spec["id"]:
                del self.active[kind]
        self.gate.publish(Bool(data=True))
        self.tag("end", spec)

    # --- main tick ---------------------------------------------------------
    def tick(self) -> None:
        self.t += 0.1
        self.cmd.publish(_twist(DRIVE_LINEAR, DRIVE_ANGULAR))

        # Slip is continuous while live: drag the body backwards along its own
        # heading so wheel odometry over-reports distance travelled.
        if "wheel_slip" in self.active and round(self.t * 10) % 5 == 0:
            self.displace(-0.02)   # dragged backwards while the wheels claim forward progress

        while self.next < len(SCHEDULE) and self.t >= SCHEDULE[self.next][0]:
            _, action, payload = SCHEDULE[self.next]
            self.next += 1
            if action == "begin":
                self.begin(payload)
            elif action == "end":
                self.end(payload)
            elif action == "stop":
                self.cmd.publish(_twist(0.0, 0.0))
                self.done = True


def _twist(lin: float, ang: float) -> Twist:
    t = Twist()
    t.linear.x = lin
    t.angular.z = ang
    return t


def main() -> None:
    rclpy.init()
    node = Session()
    node.entity = node.find_entity()
    node.get_logger().info(f"robot entity: {node.entity}")
    node.gate.publish(Bool(data=True))
    while rclpy.ok() and not node.done:
        node.tick()
        rclpy.spin_once(node, timeout_sec=0.0)
        time.sleep(0.1)
    node.get_logger().info("session complete")
    rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
