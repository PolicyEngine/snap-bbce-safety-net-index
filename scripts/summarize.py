"""Join a run's state indexes with Brookings' published 2024 file and PolicyEngine-US's BBCE parameters.

Usage: summarize.py RUN_DIR "data/brookings/1_noimmig v7.dta" SUMMARY_CSV
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
from policyengine_us.system import system

rundir, brookings_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
idx = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(rundir, "index_*.csv")))]).set_index("state")
assert len(idx) == 51, len(idx)
bk = pd.read_stata(brookings_path)
bk = bk[bk.year == 2024].set_index("state")
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
p = system.parameters("2024-07-01").gov.hhs.tanf.non_cash
rows = []
for st in idx.index:
    gross = float(p.income_limit.gross[st])
    net = bool(p.income_limit.net_applies.non_hheod[st]) if np.isfinite(gross) else None
    rows.append((st, gross, net, float(p.asset_limit[st])))
par = pd.DataFrame(rows, columns=["state", "bbce_gross_limit", "net_test_applies", "bbce_asset_limit"]).set_index("state")
t = idx.join(par)
t["brookings_snap_index"] = [1000 * bk.loc[NAMES[s], "snap"] for s in t.index]
t["brookings_tanf_index"] = [1000 * bk.loc[NAMES[s], "tanf"] for s in t.index]
t["gain_fed"] = t.snap_index_fed_bbce - t.snap_index_fed_nobbce
t["gain_state"] = t.snap_index_state_bbce - t.snap_index_state_nobbce
t["gain_fed_pct_pe"] = 100 * t.gain_fed / t.snap_index_fed_nobbce
t["gain_fed_pct_brookings"] = 100 * t.gain_fed / t.brookings_snap_index
t.to_csv(out)

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 100)
cols = ["bbce_gross_limit", "net_test_applies", "brookings_snap_index", "snap_index_fed_nobbce", "snap_index_fed_bbce",
        "gain_fed", "gain_state", "gain_fed_pct_pe", "gain_fed_pct_brookings", "share_eligible_fed_nobbce",
        "share_eligible_fed_bbce", "tanf_index", "brookings_tanf_index", "ssi_index", "gainers_with_tanf", "gainers_with_ssi", "losers"]
print(t[cols].sort_values(["gain_fed", "bbce_gross_limit"], ascending=False).round(3).to_string())
q = lambda s: f"median {s.median():.2f}, IQR {s.quantile(.25):.2f}-{s.quantile(.75):.2f}, range {s.min():.2f}-{s.max():.2f}"
# The headline set: the 34 states and DC with a BBCE limit above 130% for working families
# (New York's general limit is 130%, its limit for households with earnings 150%), as detail.py does.
over130 = sorted(t.index[np.isfinite(t.bbce_gross_limit) & (t.bbce_gross_limit > 1.3)].tolist() + ["NY"])
assert len(over130) == 35, len(over130)
w = t.loc[over130]
print(f"\nthe {len(w)} jurisdictions with a BBCE limit above 130% for working families:")
print("  gain $ (federal benefit rules):", q(w.gain_fed))
print("  gain % of PE federal-rules index:", q(w.gain_fed_pct_pe))
print("  gain % of Brookings' published index:", q(w.gain_fed_pct_brookings))
print("  the other 16: largest gain %.2f (%s)" % (t.drop(over130).gain_fed.max(), t.drop(over130).gain_fed.idxmax()))
g = t[t.gain_fed > 0.5]
print(f"\nall {len(g)} jurisdictions with any gain above $0.50 (adds Ohio, through its limit for households with an"
      " elderly or disabled member); zero-gain:", sorted(t.index[t.gain_fed <= 0.5]))
print("  gain $ (federal benefit rules):", q(g.gain_fed))
print("  gain % of PE federal-rules index:", q(g.gain_fed_pct_pe))
print("  gain % of Brookings' published index:", q(g.gain_fed_pct_brookings))
for lim in sorted(g.bbce_gross_limit.unique()):
    s = g[g.bbce_gross_limit == lim]
    print(f"  limit {lim}: n={len(s)} median gain {s.gain_fed.median():.1f} states {sorted(s.index)}")
print("gainers receiving TANF (zero by construction; see tanf_cross_check.py):", int(t.gainers_with_tanf.sum()), "; receiving SSI:", int(t.gainers_with_ssi.sum()), "; losers:", int(t.losers.sum()))
c = t[~t.index.isin(["AK", "HI"])]
print("49 jurisdictions excl AK/HI: corr(Brookings SNAP, PE fed-rules no BBCE) %.3f; corr(Brookings SNAP, Brookings TANF) %.3f; corr(Brookings TANF, PE TANF) %.3f"
      % (np.corrcoef(c.brookings_snap_index, c.snap_index_fed_nobbce)[0, 1], np.corrcoef(c.brookings_snap_index, c.brookings_tanf_index)[0, 1],
         np.corrcoef(c.brookings_tanf_index, c.tanf_index)[0, 1]))
print("49 jurisdictions excl AK/HI: ratio PE fed-rules no-BBCE / Brookings SNAP: median %.3f (range %.3f-%.3f)" % (
    (c.snap_index_fed_nobbce / c.brookings_snap_index).median(), (c.snap_index_fed_nobbce / c.brookings_snap_index).min(),
    (c.snap_index_fed_nobbce / c.brookings_snap_index).max()))
print("gain by family type, median over the jurisdictions with any gain: married %.1f partner %.1f single %.1f eldis %.1f" % (
    g.gain_married.median(), g.gain_partner.median(), g.gain_single.median(), g.gain_eldis.median()))
print("state-rule gains where they differ:", t[(t.gain_state - t.gain_fed).abs() > 0.5][["gain_fed", "gain_state"]].round(2).to_dict("index"))
