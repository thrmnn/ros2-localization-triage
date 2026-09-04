# The Cartographer backpack rows, re-run on header stamps

Platform: Cartographer backpack, four public recordings  
Duration: 344 s, 787 s, 942.1 s and 2281.0 s  
Command: `.venv/bin/loctriage --config config/cartographer-backpack.yaml detect <bag> --json <out>`  
Graded against: the receive-time runs, committed for the two annotated bags under results/labelled/ and stated as counts in docs/transferability.md for the other two  
Verdict: unchanged, 2026-09-04

`config/cartographer-backpack.yaml` renames the lasers, so until commit c5e7ab1 these
rows, like the MiR100 row, were measured on bag receive times. Re-run the same night
with header stamps collected for both lasers, the two annotated bags produced the same
events at the same times, 4 and 28 raw, which the number gate checks against the
committed receive-time lists. The other two rows kept their counts, 1 on b0 and 2 on
b2-2016-02-02, matching the flags stated for them in docs/transferability.md; their
receive-time event lists were never committed, so for those two the comparison is a
count. The backpack recorder kept up with its lasers; the MiR100
recorder did not, and only the header stamps tell those two cases apart.
