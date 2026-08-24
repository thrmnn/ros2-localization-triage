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
the only non-circular true positive in this work. See `transferability.md`.

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

**MIT Stata Center Dataset** (PR2, CC BY 3.0, commercially clean). Checked
2026-08-24 and the most promising real lead for the two detectors with no
confirmed catch. `/base_scan`, `/base_odometry/odom` and `/tf` at 557 Hz are
real recorded topics, verified against a bag's own `.info` output, not
inferred from the project page. 17 of its sequences carry independent ground
truth: (x, y, yaw) at roughly 20 Hz from a ceiling AprilTag system, entirely
separate from AMCL, so replaying a bag through AMCL and comparing its output
against this ground truth would be a genuine, non-circular test for
`covariance_spike` and `pose_divergence`, both of which need `/amcl_pose`.

Verified for the smallest candidate, `2012-01-27-07-37-01.bag` (6:48, floors
2 then 3 then 2): 200 seconds of real ground truth downloaded and inspected,
CSV of `timestamp_us,x,y,yaw`, same epoch as the bag. ROS1 Noetic's own `amcl`
and `map_server` packages are installed locally, so this needs no bridging.

**Blocked, not abandoned.** The file itself and a second, larger candidate
both returned Google Drive's "quota exceeded" page within minutes of each
other, a shared, traffic-dependent limit stated to clear within 24 hours,
confirmed by Drive's own error text rather than inferred. Retry either bag
once the quota clears; the ground truth for the first is already on disk. No
new dataset or tooling has to be found, only time.

**Hard Point Cloud Localization.** Contains literal `indoor_kidnap` and
`outdoor_kidnap` sequences with ground truth. A kidnap is exactly what the
transform-jump detector claims to catch, and here it is labelled by someone else.

**León attack bags.** Paired clean and attacked runs of the same route. Paired
data is the ideal evaluation structure, because the clean run is the control.

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
