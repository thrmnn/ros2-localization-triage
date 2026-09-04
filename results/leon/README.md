# León attack-pair artifacts

Platform: Tiago-family robot  
Command: `python3 scripts/leon_scan_timing.py E1-1 E1-2`  
Graded against: the dataset's own attack label  
Verdict: correct (L1), wrong (L2)

Detector output on the Universidad de León "Simulated attacks Rosbags against
mobile robot in ROS 2" dataset (CC BY 4.0, Zenodo 17649537). The
`*_receive_time.json` files are the tool's output before the scan_gap timestamp
fix and exist as evidence of the defect; `*_header_time.json` are the current
tool. `timing_summary.json` is written by `scripts/leon_scan_timing.py` from the
bags. Writeup: `docs/finding-recorder-artifacts.md`.
