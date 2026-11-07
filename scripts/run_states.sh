#!/usr/bin/env bash
# Run a per-state PolicyEngine-US script over the 50 states and DC, WORKERS states at a time (default 4).
# Each state gets a fresh process: a long-lived process's memory grows with every state it simulates. A state that
# already has its index file is skipped, so rerunning the same command resumes a stopped run.
# Usage: run_states.sh SCRIPT PERSONS OUTDIR [script options]
#   STATES (default all 51, as a space-separated list) limits the run to some jurisdictions.
#   PYTHON (default python) names the interpreter; run inside the project environment, e.g. `uv run`.
set -uo pipefail
SCRIPT=$1; PERSONS=$2; OUT=$3; shift 3
export SCRIPT PERSONS OUT PYTHON=${PYTHON:-python}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
STATES=${STATES:-"DC MD NJ AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MA MI MN MS MO MT NE NV NH NM NY NC ND OH
OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"}
mkdir -p "$OUT/logs"
rc=0
printf '%s\n' $STATES | xargs -P "${WORKERS:-4}" -I{} bash -c '
  [ -s "$OUT/index_{}.csv" ] && exit 0
  "$PYTHON" -I "$SCRIPT" "$PERSONS" "$OUT" {} "$@" > "$OUT/logs/{}.log" 2>&1
' _ "$@" || rc=$?
for st in $STATES; do
  [ -s "$OUT/index_$st.csv" ] || { echo "missing $st (see $OUT/logs/$st.log)" >&2; rc=1; }
done
exit $rc
