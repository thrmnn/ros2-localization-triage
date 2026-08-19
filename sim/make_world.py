"""Emit the stock TurtleBot3 world with the state plugin enabled.

Generated, never a hand-edited copy: libgazebo_ros_state.so is what exposes
/gazebo/{get,set}_entity_state, and the kidnap and slip injections are both
just calls to it. Stock gzserver does not load it.
"""
import sys
import xml.etree.ElementTree as ET

SRC = "/opt/ros/humble/share/turtlebot3_gazebo/worlds/turtlebot3_world.world"
DST = sys.argv[1] if len(sys.argv) > 1 else "/session/params/world.sdf"

tree = ET.parse(SRC)
world = tree.getroot().find("world")
plugin = ET.SubElement(world, "plugin", {"name": "gazebo_ros_state",
                                         "filename": "libgazebo_ros_state.so"})
ros = ET.SubElement(plugin, "ros")
ET.SubElement(ros, "namespace").text = "/gazebo"
ET.SubElement(plugin, "update_rate").text = "50.0"
tree.write(DST, encoding="unicode", xml_declaration=True)
print(f"world written: {DST}")
