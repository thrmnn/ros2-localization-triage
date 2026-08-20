#!/usr/bin/env bash
# The one authorised synthetic figure: detection against slip magnitude.
#
# Output is a CURVE over an independent variable, never a count of events. A curve
# answers how small a fault the frozen thresholds can still see. A count would only say
# how many hits we authored ourselves, and a self-authored true positive is worth nothing.
#
# Each arm is the same route on the same robot; the only difference is the tyre. The rig
# is flaky: gzserver sometimes starts slowly, AMCL's lifecycle transition times out, and
# the run completes with an empty /amcl_pose. That failure is SILENT and would look like a
# measurement, so every arm is verified and retried rather than trusted.
set -uo pipefail
cd "$(dirname "$0")/.."

LEVELS="${*:-0.0 0.05 0.15 0.4 1.0}"
ATTEMPTS=3

for slip in $LEVELS; do
  tag="slip$(echo "$slip" | tr -d '.')"
  ok=0
  for attempt in $(seq 1 $ATTEMPTS); do
    stamp="${tag}-a${attempt}"
    echo "== slip=$slip attempt $attempt =="
    timeout 900 docker run --rm --hostname loctriage -v "$PWD/sim":/session \
      loctriage-sim:humble bash -lc "/session/record_slip.sh $stamp $slip" \
      > "sim/out/${stamp}.run.log" 2>&1
    n=$(grep -oE "/amcl_pose \| Type: [^|]+ \| Count: [0-9]+" "sim/out/${stamp}.baginfo.txt" 2>/dev/null | grep -oE "[0-9]+$")
    n=${n:-0}
    if [ "$n" -gt 100 ]; then
      echo "   ok: $n amcl_pose messages -> sim/out/slip-${stamp}"
      echo "$slip sim/out/slip-${stamp} $n" >> sim/out/slip_sweep.index
      ok=1
      break
    fi
    # Retrying without saying WHY turns a systematic bug into apparent flakiness. The
    # first version of this sweep retried a broken SDF three times per arm and reported
    # "empty localiser" each time, while the real error sat in the bringup log.
    echo "   EMPTY LOCALISER ($n amcl_pose messages). Cause, from the bringup log:"
    grep -iE "error|ValueError|died|exit code" "sim/out/${stamp}.bringup.log" 2>/dev/null \
      | grep -viE "ALSA|snd_|pcm|lifecycle node launched" | head -3 | sed 's/^/     /'
    echo "   Discarding and retrying."
    rm -rf "sim/out/slip-${stamp}"
  done
  [ "$ok" -eq 1 ] || echo "   FAILED after $ATTEMPTS attempts at slip=$slip"
done

echo
echo "index:"
cat sim/out/slip_sweep.index 2>/dev/null || echo "  nothing recorded"
