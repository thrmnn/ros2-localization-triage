# Stata Center replay artifacts

Everything the finding doc cites, recomputable without the 7.1 GB bag:
`gt_part*_floor2.csv` are the dataset's AprilTag ground truth (CC BY 3.0,
MIT Stata Center dataset), `amcl_poses.csv` is the replayed AMCL output,
`walls.csv` is the GT-projected endpoint cloud behind the figure,
`detections.json` is the tool's output on the merged bag, and
`gt_comparison.json` is written by `scripts/stata_grade.py` from the CSVs.
Writeup: `docs/finding-confidently-wrong.md`. Replay recipe:
`scripts/stata_replay.sh` plus `scripts/stata_build_map.py`.
