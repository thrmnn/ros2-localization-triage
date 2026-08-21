# How rows in the case log are scored

Fixed **before** the detectors were run against the real recording, and not
changed afterwards. The point of writing it first is that "was this a hit?" stops
being a judgement made with the answer already visible.

Two claims are made about every row, and they are graded separately because one
is mechanical and one is not. Conflating them is what makes a self-authored
demo read as marketing.

## Claim 1: "citations verified", mechanical

Every timestamp, topic and frame named in a finding must exist in the recording
at the stated time. This is checked by a script, reproducible by anyone with the
bag, and is either true or false. No judgement.

## Claim 2: "outcome", author-assessed and labelled as such

One of four verdicts. For synthetic rows the ground truth is the tag written
into the bag during recording. For the real recording there is no ground truth,
so the verdict is a reading of the signals and is marked as such, never as
verification.

**`correct`**: the finding names a real event, and the mechanism it proposes is
consistent with every other signal in the window. Nothing in the recording
contradicts it.

**`partial`**: the event is real but the account of it is incomplete or the
boundaries are wrong: right window, wrong cause; or one contributing signal
identified out of several; or the duration is materially off.

**`wrong`**: the finding names an event that did not occur, or proposes a
mechanism the other signals contradict.

**`low-confidence`**: the signals are genuinely ambiguous and a competent
engineer could read them either way. This is a verdict about the *evidence*, not
a hedge about the tool. A row may only be marked low-confidence if the specific
ambiguity is named: which signal is missing, or which two readings both fit.

## Rules that make the grading honest

1. **A declared negative counts.** An injected fault predicted in advance to sit
   below the detection floor, which is then not reported, is a `correct` row.
   the tool agreed with a prediction made before the run. It is not a miss.
2. **A missed fault that was expected to be caught is `wrong`.** It does not get
   downgraded to low-confidence after the fact.
3. **The real recording cannot produce a `correct` verdict on mechanism**. Only
   on whether the flagged event is present in the signals. Any causal claim about
   a recording whose ground truth nobody has is `low-confidence` at best.
4. **Rows are not dropped for being unflattering.** The case log's composition is
   fixed before the output is read: at least one `wrong` or `partial`, and at
   least one `low-confidence`. If the output does not contain them, that is
   reported, not corrected by re-running with different thresholds.
5. **Thresholds are frozen** at the values calibrated on the synthetic recording
   before the real recording is analysed. Re-tuning after seeing real output and
   then reporting the result as a finding is the failure this rule exists to
   prevent.
