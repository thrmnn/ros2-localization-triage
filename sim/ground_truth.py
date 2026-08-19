"""Pull the tagged incidents back out of a recorded bag.

The tags were published live on /incident_marker during the session, so this is
a read of what was recorded -- not a reconstruction. Emits the intervals that
day-3 threshold calibration scores detector output against.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

TOPIC = "/incident_marker"

# How long a fault's effect may outlast its trigger. Declared per fault kind,
# not read off the recorded signal -- deriving the truth window from the trace
# the detector is scored against would make the scoring circular.
#
#   scan_dropout  AMCL reconverges within a few updates once scans return.
#   odom_jump     the discontinuity is instantaneous; nothing persists once
#                 the displacements stop.
#   kidnap        the particle filter needs roughly a minute to recover.
#
# These are day-3 calibration inputs and worth a second look against the sweep.
RECOVERY_S = {"scan_dropout": 30.0, "odom_jump": 0.0, "kidnap": 60.0}


def intervals(bag: Path) -> list[dict]:
    store = get_typestore(Stores.ROS2_HUMBLE)
    open_by_id: dict[str, dict] = {}
    out: list[dict] = []
    with AnyReader([bag], default_typestore=store) as reader:
        start = reader.start_time
        conns = [c for c in reader.connections if c.topic == TOPIC]
        if not conns:
            raise SystemExit(f"{bag}: no {TOPIC} -- this bag carries no ground truth")
        for conn, ts, raw in reader.messages(connections=conns):
            tag = json.loads(reader.deserialize(raw, conn.msgtype).data)
            t = (ts - start) / 1e9
            if tag["phase"] == "begin":
                open_by_id[tag["id"]] = {**tag, "t_begin": round(t, 3)}
            else:
                rec = open_by_id.pop(tag["id"], None)
                if rec is None:
                    continue
                rec.pop("phase", None)
                rec.pop("t_rel", None)
                out.append({**rec, "t_end": round(t, 3)})
    return sorted(out, key=lambda r: r["t_begin"])


def as_labels(rows: list[dict]) -> dict:
    """Effect windows in the shape `loctriage sweep --labels` expects."""
    return {"incidents": [{
        "start_s": r["t_begin"],
        "end_s": round(r["t_end"] + RECOVERY_S.get(r["kind"], 0.0), 3),
        "label": r["kind"],
    } for r in rows]}


def main() -> None:
    bag = Path(sys.argv[1])
    rows = intervals(bag)
    if "--yaml" in sys.argv:
        import yaml
        print(yaml.safe_dump(as_labels(rows), default_flow_style=False, sort_keys=False))
    else:
        print(json.dumps(rows, indent=2, sort_keys=True))
    print(f"\n{len(rows)} tagged incidents", file=sys.stderr)


if __name__ == "__main__":
    main()
