"""Would a standard utility allowance show up in Brookings' published SNAP index? Aggregates only.

PolicyEngine-US gives every household the standard utility allowance (SUA) in the states that set
gov.usda.snap.income.deductions.utility.always_standard, whatever utility costs it reports. SUA_RUN_DIR holds a
snap_by_state.py run over those states with Brookings' appendix setting except --no-sua: no TANF, students kept,
earnings x 1.07, and no rent or other shelter costs, so the SUA makes up a family's whole shelter cost. BASE_RUN_DIR
holds the main run (the SUA set to zero). For each state this prints how much the SUA adds to the federal-rules index
and to the BBCE gain, and how far Brookings' index sits from the line that fits it to its TANF index across the 49
jurisdictions other than Alaska and Hawaii. If Brookings' index included the SUA in these states, they would sit above
the line by about what the SUA adds.

Usage: sua_test.py SUMMARY_CSV BASE_RUN_DIR SUA_RUN_DIR
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from policyengine_us.system import system

summary_csv, base_dir, sua_dir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])

node = system.parameters.gov.usda.snap.income.deductions.utility.always_standard("2024-07-01")
always = sorted(st for st in system.variables["state_code"].possible_values._member_names_
                if st in node._children and bool(node[st]))
ran = sorted(p.stem.removeprefix("index_") for p in sua_dir.glob("index_*.csv"))
assert ran == always, f"SUA run covers {ran}; PolicyEngine-US's always-SUA states on 2024-07-01 are {always}"

summary = pd.read_csv(summary_csv, index_col="state")
fit = summary.drop(index=["AK", "HI"])
assert len(fit) == 49
slope, intercept = np.polyfit(fit.brookings_tanf_index, fit.brookings_snap_index, 1)
residual = summary.brookings_snap_index - (intercept + slope * summary.brookings_tanf_index)

rows = []
for st in always:
    base = pd.read_csv(base_dir / f"index_{st}.csv").iloc[0]
    sua = pd.read_csv(sua_dir / f"index_{st}.csv").iloc[0]
    rows.append({
        "state": st,
        "fed_rules_no_sua": base.snap_index_fed_nobbce,
        "fed_rules_with_sua": sua.snap_index_fed_nobbce,
        "sua_adds": sua.snap_index_fed_nobbce - base.snap_index_fed_nobbce,
        "sua_adds_pct": 100 * (sua.snap_index_fed_nobbce / base.snap_index_fed_nobbce - 1),
        "bbce_gain_no_sua": base.snap_index_fed_bbce - base.snap_index_fed_nobbce,
        "bbce_gain_with_sua": sua.snap_index_fed_bbce - sua.snap_index_fed_nobbce,
        "brookings_residual": residual[st],
    })
t = pd.DataFrame(rows).set_index("state")
pd.set_option("display.width", 200)
print(f"PolicyEngine-US always-SUA jurisdictions on 2024-07-01 ({len(always)}): {' '.join(always)}")
print("$ per family per year, July 2024 x 12; Brookings' residual from SNAP = "
      f"{intercept:.1f} {slope:+.4f} x TANF (49 jurisdictions)")
print(t.round(2).to_string())
others = residual.drop(index=always + ["AK", "HI"])
print(f"SUA adds to the federal-rules index: median ${t.sua_adds.median():.2f} ({t.sua_adds_pct.median():.2f}%), "
      f"range ${t.sua_adds.min():.2f} ({t.sua_adds.idxmin()}) to ${t.sua_adds.max():.2f} ({t.sua_adds.idxmax()})")
print(f"BBCE gain with the SUA: median ${t.bbce_gain_with_sua.median():.2f}, against ${t.bbce_gain_no_sua.median():.2f} "
      "without it")
print(f"Brookings' residual: median ${t.brookings_residual.median():+.2f} in these {len(always)}, "
      f"${others.median():+.2f} in the other {len(others)} of the 49")
