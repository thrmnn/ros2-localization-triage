# Where the evidence comes from

A map of public robot navigation data that this work can actually use, with what
each source is good for. Four parallel research passes produced the long version;
this is the curated result. Every entry was checked for whether it downloads
anonymously and what licence it carries.

## The rule that saved the most time

**A topic list is not evidence that a topic has data.** Three datasets in the
survey declare `/tf` or `/tf_static` and publish zero messages on them. Audit
message counts before downloading gigabytes.

## Already used here

**Cartographer Public Data** ([index](https://raw.githubusercontent.com/cartographer-project/cartographer_ros/master/docs/source/data.rst),
[licence](https://github.com/cartographer-project/cartographer_ros/blob/master/LICENSE);
Google, Apache-2.0, anonymous download). Five
platforms: 2D and 3D backpacks, a PR2, a MiR100 AGV, a Magazino warehouse robot.
13.1 hours in the 2D set alone.

Its value is not volume. It ships a **"Known Issues" column** annotating specific
bags with laser dropouts, written by its authors years before this tool existed.
That is independently labelled ground truth for a gap detector, and it produced
the first non-circular true positive in this work. See `transferability.md`.

**fmrico/mh_amcl test bag** ([repo](https://github.com/fmrico/mh_amcl), Apache-2.0). A real Tiago with `/scan` and `/tf`,
published alongside the map it was recorded in, specifically so it can be replayed
through a localiser. Used for the localisation figures.

## Best next targets, in order

**UT-SARA-GQ** (Clearpath Warthog, **CC0**, roughly 7.5 hours across 42 bags,
ROS 2 Humble, open directory). CC0 means no licence friction at all, and the
Warthog is a large outdoor platform, far from a TurtleBot3. Best volume-to-effort
ratio available.

**LILocBench** (University of Bonn). Purpose-built for long-term localisation
failure. Checked 2026-08-24: it does **not** ship an AMCL baseline as earlier
notes claimed; it ships raw ROS bags (Dingo robot, 2x SICK TIM781S, ceiling
AprilTag ground truth) that would need the same self-replay this repo already
does for Tiago. Licence is **CC BY-NC-SA, which forbids commercial use**. This
practice is commercial, so findings built on this data cannot honestly support
a paid service. Not pursued for that reason, not a technical one.

**MIT Stata Center Dataset** (PR2, CC BY 3.0, commercially clean). **Used, 2026-08-24,
and it delivered.** The smallest floor-2 candidate, `2012-01-27-07-37-01.bag` (7.1 GB,
6:48), downloaded after the Drive quota cleared, replayed through ROS 1 AMCL against a
map rasterised from the dataset's own AprilTag ground truth, and graded against that
same independent ground truth. Result: the first non-circular true positives for
`pose_divergence` and `covariance_spike`, and a demonstrated structural miss. Full
writeup in `finding-confidently-wrong.md`; every number recomputes from
`results/stata/` without the bag. 16 more ground-truthed sequences remain if more
windows are ever needed.

**Universidad de León attack bags, the current generation.** The old paired
clean-vs-attack lead resolved to something better: [Simulated attacks Rosbags against
mobile robot in ROS 2](https://zenodo.org/records/17649537) (published 2025-11,
**CC BY 4.0, commercially clean, anonymous download**). ROS 2 bags from a Tiago-family
robot: paired clean and cmd_vel-flood runs of the same route, `/scan`, `/tf`,
`/mobile_base_controller/odom`, and a live `map->odom` edge, so a localiser was
running during the attacks. Used 2026-08-24: exposed a real defect in `scan_gap`
(receive time vs header stamps) and then gave the fixed detector a labelled catch.
See `finding-recorder-artifacts.md` and `results/leon/`. Experiment 2 (3.1 GB, more
runs) is downloaded and unexamined.

**Hard Point Cloud Localization** ([Zenodo](https://zenodo.org/records/10122133),
Koide et al., AIST). Checked 2026-08-24: **CC BY 4.0, commercially clean, anonymous
download**, with literal `indoor_kidnap` and `outdoor_kidnap` sequences introduced by
the MegaParticles paper (arXiv:2404.16370). The catch: it is a **3D LiDAR** dataset
with `.ply` point-cloud maps, no 2D scan and no AMCL-shaped pipeline, so using it
means projecting 3D to 2D or running a different localiser. Kidnaps labelled by
someone else remain exactly what `tf_jump` needs; the format is why this is future
work rather than done.

**CARMEN logs** mirrored at Bonn and Freiburg (CC BY). Thirteen different legacy
robots, 2D laser and wheel odometry, under 200 MB in total. The cheapest platform
diversity available, at the cost of one format adapter.

## Dead ends, so nobody spends a day on them

- **Radish** is gone. Its host no longer resolves in DNS.
- **Rawseeds** is unobtainable. BitTorrent only, no surviving seeds.
- **UTIAS MRCLAM** FTP times out.
- **AWS RoboMaker** publishes no bags.
- **foxglove.dev/data** returns 404 and the sample MCAP URLs are dead.
- **ros2/rosbag2 and Nav2 fixtures** are synthetic, not robot recordings.
- IEEE DataPort is not usefully searchable; Kaggle is login-walled.
- **EuRoC's classic ASL URL moved silently and still returns 200**, which is worse
  than a 404 because it looks fine.

## On localisation topics specifically

`/amcl_pose` is essentially unpublished. Three sources exist in the whole survey
and only one is a real robot, at 86 seconds with no declared licence. This is
structural rather than an oversight: localisation output is an algorithm's product,
not a measurement, so nobody records it.

**Replaying real sensor data through a localiser yourself is the only scalable
route**, and it must be stated as such wherever those signals are used. The scans
and transforms are recorded; the pose and its uncertainty are generated.

## Licence traps worth reading twice

CC BY-ND forbids derivative datasets, which includes a converted or re-cut version.
NC-SA blocks commercial use, which matters for anything client-facing. Several
otherwise attractive sources declare no licence at all, and no licence means no
permission, not free rein.
