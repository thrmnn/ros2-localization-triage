# Kidnap replay artifacts, outdoor sequence

`outdoor_kidnap` from the same dataset (Livox MID360, two consecutive bags
merged), through the identical pipeline as `results/kidnap/` (see that README
for the file roles). Reported as an observation, not a graded prediction: no
case-log row was frozen before this replay ran. `detectors_kidnap.yaml` here
differs from the frozen indoor copy in exactly one value, the tf edge name,
because hdl_localization publishes `map->livox_frame` for this sensor.
Writeup: the outdoor section of `docs/finding-kidnap.md`.
