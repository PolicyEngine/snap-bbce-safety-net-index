"""Compare Wisconsin's 2024 SNAP, SSI and BBCE gain by cell between samples that define disability differently.
Aggregates only.

Each NAME=PERSONS:RUN_DIR pairs a sample with a snap_by_state.py run that includes Wisconsin. For each it prints
Wisconsin's federal-rules SNAP and SSI indexes and BBCE gain, then each family-type-by-disability cell beside
Brookings' published Wisconsin values (13b_noimmig v7.dta).

Usage: disability_runner_up.py BROOKINGS_DIR NAME=PERSONS:RUN_DIR [NAME=PERSONS:RUN_DIR ...]
"""
import os
import sys

import numpy as np
import pandas as pd

bdir, specs = sys.argv[1], sys.argv[2:]
c = pd.read_stata(os.path.join(bdir, "13b_noimmig v7.dta"))
c["cell"] = c.family_type.astype(str) + "/" + c.any_dis.astype(int).astype(str)
wi = c[(c.state == "Wisconsin") & (c.year == 2024)].set_index("cell")
one = pd.read_stata(os.path.join(bdir, "1_noimmig v7.dta"))
wi_all = one[(one.state == "Wisconsin") & (one.year == 2024)].iloc[0]
T = {"single": "Single", "married": "Ref person + spouse", "partner": "Partner"}
print("Wisconsin, July 2024, Brookings' appendix SNAP setting (no utility allowance, students kept, no TANF)")
print(f"Brookings Wisconsin 2024: SNAP ${1000 * wi_all.snap:,.2f}, SSI ${1000 * wi_all.ssi:,.2f}")
for spec in specs:
    name, paths = spec.split("=", 1)
    persons, run_dir = paths.split(":", 1)
    per = pd.read_csv(persons, usecols=["person_household_id", "is_disabled", "household_weight"])
    fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), dis=("is_disabled", "max"))
    r = pd.read_csv(os.path.join(run_dir, "families_WI.csv.gz")).set_index("household_id").reindex(fam.index)
    W = fam.w.sum()
    fam["cell"] = r.family_type.map(T) + "/" + fam.dis.astype(int).astype(str)
    print(f"\n{name}: SNAP index ${(fam.w * 12 * r.snap_fed_nobbce).sum() / W:.2f}, "
          f"SSI index ${(fam.w * 12 * r.ssi_fed_nobbce).sum() / W:.2f}, "
          f"gain ${(fam.w * 12 * (r.snap_fed_bbce - r.snap_fed_nobbce)).sum() / W:.2f}, "
          f"any disabled {fam.w[fam.dis == 1].sum() / W:.4f}")
    rows = []
    for cl, g in fam.groupby("cell"):
        rr = r.loc[g.index]
        w = rr.w
        rows.append(dict(cell=cl, share=w.sum() / W,
                         snap=np.average(12 * rr.snap_fed_nobbce, weights=w), brookings_snap=1000 * float(wi.loc[cl, "snap"]),
                         ssi=np.average(12 * rr.ssi_fed_nobbce, weights=w), brookings_ssi=1000 * float(wi.loc[cl, "ssi"]),
                         gain=np.average(12 * (rr.snap_fed_bbce - rr.snap_fed_nobbce), weights=w),
                         with_ssi=np.average(rr.ssi_fed_nobbce > 0, weights=w)))
    d = pd.DataFrame(rows)
    d["snap_ratio"] = d.snap / d.brookings_snap
    d["ssi_ratio"] = d.ssi / d.brookings_ssi
    print(d.round(3).to_string(index=False))
