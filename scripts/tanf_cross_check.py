"""How much of the BBCE gain goes to families that PolicyEngine-US's TANF rules would pay TANF. Aggregates only.

The main runs set tanf to zero, which takes TANF out of SNAP income and out of SNAP's categorical eligibility
(gov.usda.snap.categorical_eligibility lists tanf; meets_snap_categorical_eligibility). A run with PolicyEngine-US's
TANF can't show a family that receives TANF gaining from BBCE: TANF makes it categorically eligible with and without
BBCE, so its gain is zero by construction. This script joins the runs by family instead. It takes each family's BBCE
gain from MAIN_RUN and its TANF from TANF_RUN (same family, state and earnings scale), and reports, over the 35
jurisdictions with a BBCE limit above 130% of poverty for working families:
  - the weight share of gaining families that receive TANF in TANF_RUN, pooled and by state, and their share
    of the gain;
  - the median gain and its share of Brookings' index, with and without those families' gains. Without them, the
    gain matches a run in which PolicyEngine-US's TANF makes its recipients categorically eligible, since a family
    with no TANF has the same SNAP either way.

Usage: tanf_cross_check.py MAIN_SUMMARY_CSV MAIN_RUN_DIR TANF_RUN_DIR
"""
import os
import sys

import numpy as np
import pandas as pd

summary_path, main_dir, tanf_dir = sys.argv[1:4]
t = pd.read_csv(summary_path, index_col="state")
above = t.index[np.isfinite(t.bbce_gross_limit) & (t.bbce_gross_limit > 1.3)].tolist() + ["NY"]
assert len(above) == 35, len(above)
rows = []
for st in sorted(t.index):
    m = pd.read_csv(os.path.join(main_dir, f"families_{st}.csv.gz"),
                    usecols=["household_id", "w", "snap_fed_bbce", "snap_fed_nobbce"]).set_index("household_id")
    d = pd.read_csv(os.path.join(tanf_dir, f"families_{st}.csv.gz"),
                    usecols=["household_id", "tanf_fed_bbce"]).set_index("household_id")
    assert m.index.equals(d.index), st
    W = m.w.sum()
    gain = 12 * (m.snap_fed_bbce - m.snap_fed_nobbce)
    tanf = d.tanf_fed_bbce > 0
    gainer = gain > 0.005
    rows.append({
        "state": st,
        "gain": (m.w * gain).sum() / W,
        "gain_without_tanf_families": (m.w * gain * ~tanf).sum() / W,
        "gainer_weight_share_with_tanf": (m.w[gainer & tanf]).sum() / max(m.w[gainer].sum(), 1e-9),
        "gain_share_to_tanf_families": (m.w * gain * tanf).sum() / max((m.w * gain).sum(), 1e-9),
        "gainer_weight_with_tanf": m.w[gainer & tanf].sum(),
        "gainer_weight": m.w[gainer].sum(),
        "gainer_records_with_tanf": int((gainer & tanf).sum()),
        "gainer_records": int(gainer.sum()),
        "brookings_snap_index": t.loc[st, "brookings_snap_index"],
    })
r = pd.DataFrame(rows).set_index("state")
r["pct_brookings"] = 100 * r.gain / r.brookings_snap_index
r["pct_brookings_without"] = 100 * r.gain_without_tanf_families / r.brookings_snap_index
g = r.loc[above]
print(f"35 jurisdictions: median gain ${g.gain.median():.2f} ({g.pct_brookings.median():.2f}% of Brookings' index); without the "
      f"families PolicyEngine-US pays TANF, ${g.gain_without_tanf_families.median():.2f} "
      f"({g.pct_brookings_without.median():.2f}%)")
print(f"gaining records with TANF: {int(g.gainer_records_with_tanf.sum())} of {int(g.gainer_records.sum())} "
      f"in {int((g.gainer_records_with_tanf > 0).sum())} of the 35 jurisdictions")
pooled = g.gainer_weight_with_tanf.sum() / g.gainer_weight.sum()
print(f"weight share of gaining families with TANF, pooled over the 35: {pooled:.4f}; unweighted: "
      f"{g.gainer_records_with_tanf.sum() / g.gainer_records.sum():.4f}")
print(f"weight share of gaining families with TANF, median over the 35: {g.gainer_weight_share_with_tanf.median():.4f}; "
      f"largest: {g.gainer_weight_share_with_tanf.sort_values().tail(5).round(4).to_dict()}")
print(f"share of the gain to those families, largest: {g.gain_share_to_tanf_families.sort_values().tail(5).round(4).to_dict()}")
print(f"largest drops in the gain: {(g.gain - g.gain_without_tanf_families).sort_values().tail(5).round(2).to_dict()}")
other = r.drop(index=above)
print(f"other 16: largest gain without TANF families ${other.gain_without_tanf_families.max():.2f} "
      f"({other.gain_without_tanf_families.idxmax()})")
