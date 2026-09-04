# MiR100 AGV: the 1880 flags per robot-hour that were the recorder

Platform: MiR100 warehouse AGV, `landmarks_demo_uncalibrated.bag`, Cartographer public data  
Duration: 359.938 s, measured with `loctriage inspect`  
Command: `.venv/bin/loctriage --config config/mir100.yaml detect landmarks_demo_uncalibrated.bag`  
Graded against: no labels exist for this recording  
Verdict: correction, 2026-09-04  

- `detections_receive_time.json`: the 188 `scan_gap` detections the published row was
  built on, produced at commit 1311e8b, where the reader collected header stamps for
  `/scan` only and this config names its lasers `/f_scan` and `/b_scan`, so the
  detector fell back to bag receive times.
- `detections_header_time.json`: the same command at commit c5e7ab1 and later, where
  every laser the gap detector reads gets its header stamps. Zero detections.

The thresholds are unchanged. What changed is which clock the gaps were measured on.
The full account is in [docs/transferability.md](../../docs/transferability.md) and
[docs/finding-recorder-artifacts.md](../../docs/finding-recorder-artifacts.md).
