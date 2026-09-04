# The AMCL recovery series behind docs/finding-amcl-recovery.md

Platform: TurtleBot3 Waffle, simulated  
Duration: 457.986 s (`sim/out/20260819T190412Z`, stated in the finding as 457.986 s)  
Command: `.venv/bin/python scripts/recovery_extract.py`  
Graded against: `docs/finding-amcl-recovery.md`, checked by `recovery_numbers()` in `scripts/check_numbers.py`  
Verdict: every window's median, max and n in the finding's table, plus the last
return to the quiet baseline, the final value and the ratio, recompute from this CSV

`yaw_sigma.csv` is `/amcl_pose` yaw uncertainty (1 sigma, rad), one row per message,
read with `localization_triage.bagread.read_signals` and the topics in
`config/detectors.yaml`, so it is the same reader every detector uses. 453 rows, one
per `/amcl_pose` message in the bag.

The bag is `sim/out/20260819T190412Z`, not `sim/out/20260819T170915Z`: the latter is
337 s with a three-incident schedule (`scan_dropout`, one `wheel_slip`, `kidnap`) used
elsewhere for the scan-gap sweep (`plots/day3/`). This one carries the five-fault
schedule the finding describes. Windows below are bag-relative, from
`sim/out/20260819T190412Z.session.log`'s own epoch timestamps minus the bag's start
time in `sim/out/20260819T190412Z/metadata.yaml`, not from the log's `t_rel` field,
which runs 3.2 to 5.2 s earlier and is not the CSV's clock:

- scan dropout, 63.2 to 88.5 s
- 100 mm odometry jump, 148.8 to 179.1 s
- 12 mm odometry jump, 209.3 to 239.5 s
- 5 mm odometry jump, 269.7 to 300.0 s
- 0.9 m instantaneous kidnap displacement, 360.2 to 363.3 s

## Reproducing it

    .venv/bin/python scripts/recovery_extract.py
    .venv/bin/python scripts/check_numbers.py

`incidents.json` is the bag-relative fault schedule, written from the session log by
the same script, so the number gate rebuilds every window from committed files alone.
