"""Compare replicate_2024.py's program values with Brookings' published 2024 values, by state and by cell. Aggregates only.

Brookings' files give each program in thousands of 2024 dollars per family per year (Medicaid as shares of adults and of
children). This converts them to dollars and pairs them with PolicyEngine-US's values:
  snap -> snap            tanf -> tanf             ssi -> ssi + ssp (federal SSI plus state supplements)
  fedeitc -> eitc         steitc -> state_eitc     actc -> refundable_ctc
  ctc -> ctc (total) and income_tax_capped_non_refundable_credits (the non-refundable credits used against tax)
  fii_credit -> income_tax_refundable_credits      sii_credit -> state_refundable_credits
  medicaid_adult -> medicaid_adult                 medicaid_child -> medicaid_child and medicaid_or_chip_child
For each pair it prints, across the 51 jurisdictions: PolicyEngine's national value (the median state), the median ratio of
PolicyEngine's value to Brookings', the correlation across states, and Wisconsin; then, by cell, the median ratio across states.

Usage: compare_replication.py RUN_DIR BROOKINGS_DIR OUT_CSV
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

run_dir, bdir, out_csv = sys.argv[1:4]
NAMES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
         "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
         "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
         "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
         "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
         "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
         "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
         "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
         "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
         "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
ABBR = {v: k for k, v in NAMES.items()}
PAIRS = [("snap", "snap"), ("tanf", "tanf"), ("ssi", "ssi_total"), ("ssi", "ssi"), ("fedeitc", "eitc"),
         ("steitc", "state_eitc"), ("actc", "refundable_ctc"), ("ctc", "ctc"),
         ("ctc", "income_tax_capped_non_refundable_credits"), ("fii_credit", "income_tax_refundable_credits"),
         ("sii_credit", "state_refundable_credits"), ("medicaid_adult", "medicaid_adult"),
         ("medicaid_child", "medicaid_child"), ("medicaid_child", "medicaid_or_chip_child")]
SHARES = {"medicaid_adult", "medicaid_child"}

pe = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(run_dir, "index_*.csv")))])
assert pe.state.nunique() == 51, pe.state.nunique()
pe["ssi_total"] = pe.ssi + pe.ssp


def brookings_frame(name, cell_cols):
    d = pd.read_stata(os.path.join(bdir, name))
    d = d[d.year == 2024].copy()
    d["state"] = d.state.astype(str).map(ABBR)
    assert d.state.notna().all()
    if cell_cols:
        d["cell"] = d.family_type.astype(str) + "/" + d.any_dis.astype(int).astype(str)
    else:
        d["cell"] = "all"
    for h in {p[0] for p in PAIRS} - SHARES:
        d[h] = 1000 * d[h]
    return d.set_index(["state", "cell"])


bk = pd.concat([brookings_frame("1_noimmig v7.dta", False), brookings_frame("13b_noimmig v7.dta", True)])
o = pe.set_index(["state", "cell"])
rows = []
for h, p in PAIRS:
    j = pd.DataFrame({"brookings": bk[h], "policyengine": o[p]}).dropna()
    j["ratio"] = j.policyengine / j.brookings.where(j.brookings > 0)
    for (st, cell), r in j.iterrows():
        rows.append({"program": h, "pe_variable": p, "state": st, "cell": cell, "brookings": r.brookings, "policyengine": r.policyengine,
                     "ratio": r.ratio})
res = pd.DataFrame(rows)
res.to_csv(out_csv, index=False)

fmt = lambda h, x: f"{x:.3f}" if h in SHARES else f"${x:,.0f}"
print(f"run {run_dir}: PolicyEngine-US against Brookings 2024, 51 jurisdictions\n")
print(f"{'Brookings':15s} {'PolicyEngine-US':42s} {'median BK':>12s} {'median PE':>12s} {'median ratio':>12s} "
      f"{'IQR':>13s} {'corr':>6s}   Wisconsin BK / PE")
for (h, p), g in res[res.cell == "all"].groupby(["program", "pe_variable"], sort=False):
    q = g.ratio.quantile([.25, .5, .75])
    corr = np.corrcoef(g.brookings, g.policyengine)[0, 1] if g.brookings.std() > 0 and g.policyengine.std() > 0 else np.nan
    wi = g[g.state == "WI"].iloc[0]
    print(f"{h:15s} {p:42s} {fmt(h, g.brookings.median()):>12s} {fmt(h, g.policyengine.median()):>12s} {q[.5]:12.3f} "
          f"{q[.25]:6.3f}-{q[.75]:6.3f} {corr:6.3f}   {fmt(h, wi.brookings)} / {fmt(h, wi.policyengine)}")
print("\nby cell, median ratio of PolicyEngine-US to Brookings across states (cells where Brookings' value is positive):")
piv = (res[res.cell != "all"].groupby(["program", "pe_variable", "cell"], sort=False).ratio.median()
       .unstack("cell").round(3))
pd.set_option("display.width", 250)
print(piv.to_string())
share = pe[pe.cell != "all"].groupby("cell").weight_share.mean().round(4)
print("\nsample cell shares (mean over states):", share.to_dict())
