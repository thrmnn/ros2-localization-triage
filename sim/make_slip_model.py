"""Emit the stock TurtleBot3 waffle with a real wheel-slip plugin attached.

Every fault this rig injected before today was a teleport: `set_entity_state` moved the
body and the odometry followed it. That is more physical than writing to a topic, but a
hostile reader can still say the fault was placed where the detector was looking.

Wheel slip is different in kind. The plugin changes the tyre's slip compliance in the
physics solver, so the wheel really turns while the body does not follow. Nothing writes
to /odom, /tf, /scan or /amcl_pose. The divergence between wheel odometry and the
localiser is then a consequence the estimator has to discover, not a value we authored.

    make_slip_model.py <out.sdf> <slip_compliance>

Slip compliance is in (m/s)/N: 0.0 is the stock no-slip tyre, larger slips more.
"""
from __future__ import annotations

import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path("/opt/ros/humble/share/turtlebot3_gazebo/models/turtlebot3_waffle/model.sdf")
WHEELS = ("wheel_left_link", "wheel_right_link")
WHEEL_RADIUS = 0.033
# Waffle is about 1.8 kg on two driven wheels plus a caster; half the weight per wheel is
# the right order and the plugin only uses this to scale compliance.
NORMAL_FORCE = 9.0


def build(dst: Path, compliance: float) -> None:
    tree = ET.parse(SRC)
    model = tree.getroot().find("model")
    if model is None:
        raise SystemExit("make_slip_model: no <model> in the stock SDF")

    plugin = ET.SubElement(model, "plugin", {
        "name": "wheel_slip", "filename": "libgazebo_ros_wheel_slip.so"})
    ros = ET.SubElement(plugin, "ros")
    ET.SubElement(ros, "namespace").text = "/"
    for link in WHEELS:
        w = ET.SubElement(plugin, "wheel", {"link_name": link})
        # Longitudinal only. Lateral slip would make the robot slide sideways, which is a
        # different failure and would confound the measurement.
        ET.SubElement(w, "slip_compliance_lateral").text = "0.0"
        ET.SubElement(w, "slip_compliance_longitudinal").text = f"{compliance:.6f}"
        ET.SubElement(w, "wheel_normal_force").text = str(NORMAL_FORCE)
        ET.SubElement(w, "wheel_radius").text = str(WHEEL_RADIUS)

    dst.parent.mkdir(parents=True, exist_ok=True)
    # spawn_entity.py reads this file as TEXT and hands it to lxml, which refuses a
    # declaration carrying an encoding: "Unicode strings with encoding declaration are not
    # supported". The stock model declares `<?xml version="1.0" ?>` with no encoding, so
    # match it exactly rather than letting ElementTree write its own.
    body = ET.tostring(tree.getroot(), encoding="unicode")
    dst.write_text('<?xml version="1.0" ?>\n' + body + "\n")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    dst = Path(sys.argv[1])
    compliance = float(sys.argv[2])
    if compliance == 0.0:
        # The control arm has to be the stock model byte for byte, not a rebuilt one, or a
        # difference in the writer becomes a difference in the result.
        shutil.copyfile(SRC, dst)
        print(f"{dst}: stock model, no slip plugin (control)")
        return
    build(dst, compliance)
    print(f"{dst}: slip_compliance_longitudinal={compliance} on {len(WHEELS)} wheels")


if __name__ == "__main__":
    main()
