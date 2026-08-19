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


def main() -> None:
    bag = Path(sys.argv[1])
    rows = intervals(bag)
    print(json.dumps(rows, indent=2, sort_keys=True))
    print(f"\n{len(rows)} tagged incidents", file=sys.stderr)


if __name__ == "__main__":
    main()
