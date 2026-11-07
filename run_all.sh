#!/usr/bin/env bash
# Reproduce every result in this repository, stage by stage.
# Usage: ./run_all.sh [STAGE ...]   stages: download samples fit runs summaries checks (default: all of them, in order)
#   Run it inside the project environment: `uv sync`, then `uv run ./run_all.sh`.
#   WORKERS (default 4) sets how many states run at once in the runs stage.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python} -I"
STAGES=${*:-download samples fit runs summaries checks}
OUT=out; RUNS=out/runs; FIT=out/fit; BK=data/brookings
MAIN=data/sample/persons.csv
mkdir -p "$OUT" "$FIT"

for stage in $STAGES; do
  echo "== $stage"
  case $stage in
  download)
    $PY scripts/download_asec.py
    $PY scripts/download_brookings.py
    ;;
  samples)
    # The main sample, then the three runners-up the fit stage compares it with (see README).
    $PY scripts/build_sample.py data/sample/persons.csv --disability notw --screen household
    $PY scripts/build_sample.py data/sample_hp_sga/persons.csv --disability hp_sga --screen household
    $PY scripts/build_sample.py data/sample_family_notw/persons.csv --disability notw
    $PY scripts/build_sample.py data/sample_household_appendix/persons.csv --screen household
    ;;
  fit)
    $PY scripts/fit/joint_anchor.py $BK main=$MAIN hp_sga=data/sample_hp_sga/persons.csv \
      family_notw=data/sample_family_notw/persons.csv household_appendix=data/sample_household_appendix/persons.csv \
      > $FIT/joint_anchor.txt
    $PY scripts/fit/fine_scale.py > $FIT/fine_scale.txt
    $PY scripts/fit/variant_anchor.py > $FIT/variant_anchor.txt
    $PY scripts/fit/variant_gain.py > $FIT/variant_gain.txt
    $PY scripts/fit/ssi_slope.py > $FIT/ssi_slope.txt
    $PY scripts/fit/plain_tax_anchor.py $MAIN $BK 1.00 1.07 > $FIT/plain_tax_anchor.txt
    $PY scripts/fit/wage_index_test.py $MAIN $BK > $FIT/wage_index_test.txt
    $PY scripts/fit/rent_test.py $MAIN $BK 1.07 > $FIT/rent_test_x107.txt
    $PY scripts/fit/rent_test.py $MAIN $BK 1.10 > $FIT/rent_test_x110.txt
    $PY scripts/fit/child_ssi_item.py > $FIT/child_ssi_item.txt
    ;;
  runs)
    # Brookings' appendix SNAP setting at earnings x 1.07 (the main estimate) and at CPI-U earnings; PolicyEngine-US's
    # own SNAP rules; then the replication of Brookings' 2024 programs at both earnings scales.
    A="--no-sua --no-student-rule --no-tanf"
    scripts/run_states.sh scripts/snap_by_state.py $MAIN $RUNS/appendix_x107 $A --earnings-scale 1.07
    scripts/run_states.sh scripts/snap_by_state.py $MAIN $RUNS/appendix_x100 $A
    scripts/run_states.sh scripts/snap_by_state.py $MAIN $RUNS/pe_rules_x107 --earnings-scale 1.07
    # Wisconsin alone on the runner-up sample, for the disability comparison.
    [ -s $RUNS/appendix_x107_hp_sga/index_WI.csv ] || OMP_NUM_THREADS=1 $PY scripts/snap_by_state.py \
      data/sample_hp_sga/persons.csv $RUNS/appendix_x107_hp_sga WI $A --earnings-scale 1.07
    scripts/run_states.sh scripts/replicate_2024.py $MAIN $RUNS/replicate_x107 --earnings-scale 1.07
    scripts/run_states.sh scripts/replicate_2024.py $MAIN $RUNS/replicate_x100
    # The appendix setting with the standard utility allowance left on, over the 13 jurisdictions where PolicyEngine-US
    # gives every household the SUA (scripts/sua_test.py checks this list against its parameters).
    STATES="CA CT DC MA ME MI MT NY OR PA RI VT WA" scripts/run_states.sh scripts/snap_by_state.py $MAIN \
      $RUNS/appendix_sua_x107 --no-student-rule --no-tanf --earnings-scale 1.07
    ;;
  summaries)
    for r in appendix_x107:1.07 appendix_x100:1.00 pe_rules_x107:1.07; do
      run=${r%%:*}; scale=${r##*:}
      $PY scripts/summarize.py $RUNS/$run "$BK/1_noimmig v7.dta" $OUT/summary_$run.csv > $OUT/summary_$run.txt
      $PY scripts/detail.py $MAIN $RUNS/$run $OUT/summary_$run.csv --earnings-scale $scale > $OUT/detail_$run.txt
    done
    $PY scripts/compare_runs.py $MAIN $BK appendix_x107=$OUT/summary_appendix_x107.csv:$RUNS/appendix_x107 \
      appendix_x100=$OUT/summary_appendix_x100.csv:$RUNS/appendix_x100 \
      pe_rules_x107=$OUT/summary_pe_rules_x107.csv:$RUNS/pe_rules_x107 > $OUT/compare_runs.txt
    $PY scripts/level_gap.py $OUT/summary_appendix_x107.csv > $OUT/level_gap_appendix_x107.txt
    $PY scripts/tanf_cross_check.py $OUT/summary_appendix_x107.csv $RUNS/appendix_x107 $RUNS/pe_rules_x107 \
      > $OUT/tanf_cross_check.txt
    $PY scripts/elderly_disabled_split.py $RUNS/appendix_x107 MN,NE,FL,CA,IL,NM,TX,RI,LA,ND,OH,ID,OK,AL \
      > $OUT/elderly_disabled_split_appendix_x107.txt
    $PY scripts/teen_heads.py $MAIN $RUNS/appendix_x107 WI > $OUT/teen_heads_appendix_x107.txt
    $PY scripts/disability_runner_up.py $BK main_x107=$MAIN:$RUNS/appendix_x107 \
      hp_sga_x107=data/sample_hp_sga/persons.csv:$RUNS/appendix_x107_hp_sga > $OUT/disability_runner_up_WI.txt
    $PY scripts/fit/snap_tanf_residuals.py $OUT/summary_appendix_x107.csv > $FIT/snap_tanf_residuals.txt
    $PY scripts/sua_test.py $OUT/summary_appendix_x107.csv $RUNS/appendix_x107 $RUNS/appendix_sua_x107 > $OUT/sua_test.txt
    for run in replicate_x107 replicate_x100; do
      $PY scripts/compare_replication.py $RUNS/$run $BK $OUT/${run}_compare.csv > $OUT/${run}_compare.txt
    done
    $PY scripts/replication_snap_tanf.py $OUT/replicate_x107_compare.csv > $OUT/replicate_x107_snap_tanf.txt
    $PY scripts/state_table.py $OUT/summary_appendix_x107.csv $OUT/summary_appendix_x107_positive_shares.csv \
      $OUT/summary_appendix_x100.csv $OUT/bbce_snap_index_2024_by_state.csv > $OUT/state_table_checks.txt
    ;;
  checks)
    ALL=AL,AK,AZ,AR,CA,CO,CT,DE,DC,FL,GA,HI,ID,IL,IN,IA,KS,KY,LA,ME,MD,MA,MI,MN,MS,MO,MT,NE,NV,NH,NJ,NM,NY,NC,ND,OH,OK,OR,PA,RI,SC,SD,TN,TX,UT,VT,VA,WA,WV,WI,WY
    $PY scripts/bbce_params_2024.py $ALL > $OUT/bbce_params_2024.txt
    $PY scripts/check_fns_chart.py > $OUT/fns_chart_check.txt
    $PY scripts/ers_bbce_counts.py > $OUT/ers_bbce_counts.txt
    $PY scripts/examples.py > $OUT/examples.txt
    $PY scripts/examples_table.py > $OUT/examples_table.txt
    ;;
  *) echo "unknown stage: $stage" >&2; exit 2 ;;
  esac
done
