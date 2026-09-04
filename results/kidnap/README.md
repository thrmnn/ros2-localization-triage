# Kidnap replay artifacts

Platform: handheld Azure Kinect  
Duration: 147 s  
Graded against: gt_traj.txt, the dataset's own ground truth  
Verdict: partial (K1)

Everything the finding doc cites, recomputable without the 2.35 GB bag:
`gt_traj.txt` is the dataset's own ground truth (TUM format, CC BY 4.0, Hard
Point Cloud Localization Dataset, Zenodo 10122133), `hdl_poses.csv` is the
generated localiser output (`scripts/kidnap_extract.py`),
`occlusion_windows.json` is derived from the point clouds themselves
(`scripts/kidnap_occlusion.py`), `detections.json` is the tool's output on the
replay bag with `detectors_kidnap.yaml` (thresholds byte-frozen, only topics
and the tf edge changed), and `gt_comparison.json` is written by
`scripts/kidnap_grade.py` from these files. Writeup:
`docs/finding-kidnap.md`. Replay recipe: `scripts/kidnap_replay.sh` inside the
image built from `scripts/kidnap_docker/Dockerfile`, inputs prepared by
`scripts/kidnap_prepare.py`.
