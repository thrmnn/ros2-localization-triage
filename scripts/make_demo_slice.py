"""Cut the committed demo slice out of the Cartographer backpack recording.

The full b2-2015-05-12-12-46-34.bag is a 576 MB download, so a fresh clone could
not see a detection without it. This writes a 20 s, lasers-only, bz2-compressed
excerpt around two of the laser gaps the dataset's own authors annotated, small
enough to commit, and a NOTICE next to it carrying the Apache 2.0 attribution the
data licence requires. Deterministic: same input, same bytes.

    .venv/bin/python scripts/make_demo_slice.py /path/to/b2-2015-05-12-12-46-34.bag
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rosbags.rosbag1 import Reader, Writer

SOURCE = "b2-2015-05-12-12-46-34.bag"
SOURCE_URL = "https://storage.googleapis.com/cartographer-public-data/bags/backpack_2d/" + SOURCE
TOPICS = ("horizontal_laser_2d", "vertical_laser_2d")
WINDOW_S = (2130.0, 2150.0)
OUT = Path(__file__).resolve().parents[1] / "demo" / "backpack-gaps-20s.bag"

NOTICE = """# Demo slice

`backpack-gaps-20s.bag` is a {n} s excerpt, seconds {t0:.0f} to {t1:.0f}, of the
laser topics `horizontal_laser_2d` and `vertical_laser_2d` from
`{source}` in the Cartographer public data set,
cut and recompressed with `scripts/make_demo_slice.py`. Every other topic was dropped
and nothing else was changed.

Original: {url}
Copyright 2016 The Cartographer Authors. Licensed under the Apache License,
Version 2.0: http://www.apache.org/licenses/LICENSE-2.0. This file is a modified
excerpt of that work.

The full recording is annotated by its authors with 14 gaps in laser data. This
window contains two of the events the frozen detector reports on the full
recording, so a fresh clone can see a detection without the 576 MB download.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bag", help="path to the full " + SOURCE)
    args = ap.parse_args()
    src = Path(args.bag)
    if src.name != SOURCE:
        raise SystemExit(f"expected {SOURCE}, got {src.name}")
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    t0, t1 = WINDOW_S
    writer = Writer(OUT)
    writer.set_compression(Writer.CompressionFormat.BZ2)
    writer.open()
    n = 0
    with Reader(src) as reader:
        start = reader.start_time
        conns = {
            c.id: writer.add_connection(c.topic, c.msgtype, msgdef=c.msgdef.data, md5sum=c.digest,
                                        callerid=c.ext.callerid, latching=c.ext.latching)
            for c in reader.connections if c.topic in TOPICS
        }
        for conn, ts, raw in reader.messages():
            if conn.id not in conns:
                continue
            rel = (ts - start) / 1e9
            if rel < t0:
                continue
            if rel > t1:
                break
            writer.write(conns[conn.id], ts, raw)
            n += 1
    writer.close()
    (OUT.parent / "NOTICE.md").write_text(NOTICE.format(n=int(t1 - t0), t0=t0, t1=t1, source=SOURCE, url=SOURCE_URL))
    print(f"{OUT}: {n} messages, {OUT.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
