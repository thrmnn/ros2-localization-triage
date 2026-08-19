# How this was graded, and by whom

**I recorded the faults, I ran the tool, and I graded the results.** There is no
independent evaluator here. That is worth knowing before you read anything else,
because it changes what the numbers below are worth.

Two different claims are made about every row in the case log, and they are not
equally strong. Presenting them as one number would be the easiest way to
mislead you, so they are kept apart.

## Claim 1 — "citations verified" · mechanical

Every timestamp, topic and frame named in a finding exists in the recording at
the stated time. A script checks this. You can re-run it against the same
recordings and get the same answer. Nothing about it depends on trusting me.

## Claim 2 — "outcome" · assessed by the author

Whether a finding was *right* is my judgement.

For the controlled recording this is nearly mechanical, because the expected
result was written down **before each run**, in the script that injects the
faults. A displacement of 5 mm was declared "expected to go unreported" before
the recording existed; it then went unreported. That is a prediction that held,
not a result selected afterwards.

For the public recording it is weaker and is labelled as such. There is no
ground truth. A genuine relocalisation and ordinary filter behaviour on a
featureless stretch look the same in the signals available, so no causal claim
about that recording is graded better than low-confidence.

## What stops this from being self-congratulation

- The scoring rubric (`case-log-rubric.md`) was written and committed **before**
  the detectors were run against the public recording. It fixes what counts as
  correct, partial, wrong and low-confidence, and it forbids re-tuning
  thresholds after seeing real output and then reporting the result as a finding.
- The case log's composition was fixed in advance: it must contain at least one
  row the tool got wrong or only partly right, and at least one it could not
  resolve. Those rows are not optional and were not chosen for being flattering.
- **The tool's worst result is the headline finding.** Thresholds calibrated on
  a simulated TurtleBot3 produce continuous false positives on a real Tiago —
  five reported incidents where the signal never left its own baseline. That is
  reported as `wrong`, not smoothed over, and the thresholds were left frozen
  rather than adjusted until the number improved.
- One of four detectors, `pose_divergence`, has no demonstrated true positive on
  the public recording at all. It is listed as such.

## What this is not

It is not a benchmark. A single simulated session and one public recording
cannot support statistical claims, which is why the public-facing word is *case
log* and why there is no headline accuracy figure. The failures here are also
isolated — each injected one at a time — while real fleet incidents compound.
That limitation is stated rather than solved.

External technical readthrough: **PLACEHOLDER — pending / name to be filled**.
