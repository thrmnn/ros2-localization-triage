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

**Cartographer Public Data** (Google, Apache-2.0, anonymous download). Five
platforms: 2D and 3D backpacks, a PR2, a MiR100 AGV, a Magazino warehouse robot.
13.1 hours in the 2D set alone.

Its value is not volume. It ships a **"Known Issues" column** annotating specific
bags with laser dropouts, written by its authors years before this tool existed.
That is independently labelled ground truth for a gap detector, and it produced
the only non-circular true positive in this work. See `transferability.md`.

**fmrico/mh_amcl test bag** (Apache-2.0). A real Tiago with `/scan` and `/tf`,
published alongside the map it was recorded in, specifically so it can be replayed
through a localiser. Used for the localisation figures.

## Best next targets, in order

**UT-SARA-GQ** (Clearpath Warthog, **CC0**, roughly 7.5 hours across 42 bags,
ROS 2 Humble, open directory). CC0 means no licence friction at all, and the
Warthog is a large outdoor platform, far from a TurtleBot3. Best volume-to-effort
ratio available.

**LILocBench** (University of Bonn). Purpose-built for long-term localisation
failure and **it ships an AMCL baseline**. Licence is NC-SA, so usable for
analysis but check before redistributing anything derived from it. This is the
most directly relevant dataset found for the covariance detector, which currently
has no confirmed true positive.

**Hard Point Cloud Localization.** Contains literal `indoor_kidnap` and
`outdoor_kidnap` sequences with ground truth. A kidnap is exactly what the
transform-jump detector claims to catch, and here it is labelled by someone else.

**León attack bags.** Paired clean and attacked runs of the same route. Paired
data is the ideal evaluation structure, because the clean run is the control.

**MIT Stata Center** (PR2, 38 hours, CC BY 3.0). Scans, wheel odometry and
transforms already present, 2 cm ground truth on 17 sequences. Note the download
page is `downloads.html`, not `downloads.php`, which is a dead link still cited in
places.

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
