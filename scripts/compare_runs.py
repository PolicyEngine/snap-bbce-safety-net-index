"""Compare the PolicyEngine runs on the rebuilt Brookings sample with each other and with Brookings' published 2024 file.

Aggregates only. For each run (a summary from summarize.py plus its per-family files) it prints:
  - the BBCE gain over the 35 jurisdictions with a BBCE limit above 130% of poverty for working families (New York
    included, for its 150% limit for households with earnings), and the largest gain among the other 16;
  - the gain after reweighting the sample to Brookings' six family-type-by-disability cell shares;
  - the federal-rules index against Brookings' index: Wisconsin (Brookings' only jurisdiction with no TANF), the median
    ratio across the 49 jurisdictions other than Alaska and Hawaii, and each index regressed on Brookings' TANF index;
  - Wisconsin's federal-rules SNAP, SSI and BBCE gain by cell, against Brookings' cells.

Brookings' cell shares come from its files, not from its appendix: each state-year value in its main file equals a weighted
mean of its six cells, and least squares over SNAP, TANF, SSI and federal EITC recovers the weights.

Usage: compare_runs.py PERSONS BROOKINGS_DIR NAME=SUMMARY_CSV:RUN_DIR [NAME=...]
"""
import os
import sys

import numpy as np
import pandas as pd

persons_path, bdir = sys.argv[1:3]
runs = [(s.split("=", 1)[0], *s.split("=", 1)[1].split(":", 1)) for s in sys.argv[3:]]

bk = pd.read_stata(os.path.join(bdir, "1_noimmig v7.dta"))
cells = pd.read_stata(os.path.join(bdir, "13b_noimmig v7.dta"))
cells["cell"] = cells.family_type.astype(str) + "/" + cells.any_dis.astype(int).astype(str)
piv = cells.pivot_table(index=["year", "state"], columns="cell", values=["snap", "tanf", "ssi", "fedeitc"], observed=True)
X = np.vstack([piv[v].to_numpy(float) for v in ("snap", "tanf", "ssi", "fedeitc")])
y = np.concatenate([bk.set_index(["year", "state"])[v].reindex(piv.index).to_numpy(float) for v in ("snap", "tanf", "ssi", "fedeitc")])
ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
b, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
brookings_share = pd.Series(b, index=list(piv["snap"].columns))
fit_rms = np.sqrt(np.mean((X[ok] @ b - y[ok]) ** 2)) * 1000
print("Brookings cell shares recovered from its files (rms fit error $%.2f): %s; sum %.4f" % (
    fit_rms, brookings_share.round(4).to_dict(), brookings_share.sum()))

per = pd.read_csv(persons_path, usecols=["person_household_id", "household_weight", "role", "is_disabled"])
fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), dis=("is_disabled", "max"))
roles = per.groupby("person_household_id").role.apply(set)
fam["ftype"] = np.where(roles.apply(lambda s: "spouse" in s), "Ref person + spouse",
                        np.where(roles.apply(lambda s: "partner" in s), "Partner", "Single"))
fam["cell"] = fam.ftype + "/" + fam.dis.astype(int).astype(str)
W = fam.w.sum()
mine = fam.groupby("cell").w.sum() / W
fam["w_brookings"] = fam.w * fam.cell.map(brookings_share / mine)
print("sample cell shares: %s; summed absolute gap to Brookings' %.4f" % (mine.round(4).to_dict(), (mine - brookings_share).abs().sum()))

h24 = bk[bk.year == 2024].set_index("state")
NAME = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
        "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
        "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
        "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
        "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
        "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
        "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
        "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}


def q(s, f="%.2f"):
    return ("median " + f + ", IQR " + f + "-" + f + ", range " + f + " (%s) to " + f + " (%s)") % (
        s.median(), s.quantile(.25), s.quantile(.75), s.min(), s.idxmin(), s.max(), s.idxmax())


rows = []
for name, summary, rundir in runs:
    t = pd.read_csv(summary, index_col="state")
    assert len(t) == 51, (name, len(t))
    over = sorted(t.index[np.isfinite(t.bbce_gross_limit) & (t.bbce_gross_limit > 1.3)].tolist() + ["NY"])
    assert len(over) == 35
    other = sorted(set(t.index) - set(over))
    g = t.loc[over]
    print(f"\n=== {name} ({summary})")
    print("  35 jurisdictions, gain $/family/yr:", q(g.gain_fed))
    print("  35 jurisdictions, gain % of Brookings' index:", q(g.gain_fed_pct_brookings))
    print("  35 jurisdictions, gain % of PE federal-rules index:", q(g.gain_fed_pct_pe))
    print("  other 16, largest gain: $%.2f (%s); gains above $0.50: %s" % (
        t.loc[other].gain_fed.max(), t.loc[other].gain_fed.idxmax(),
        t.loc[other][t.loc[other].gain_fed > 0.5].gain_fed.round(2).to_dict()))
    print("  gainers receiving TANF (zero by construction; see tanf_cross_check.py): %d; receiving SSI (unweighted, all states): %d; families losing SNAP: %d" % (
        t.gainers_with_tanf.sum(), t.gainers_with_ssi.sum(), t.losers.sum()))
    print("  state minimums included: DC $%.2f, MD $%.2f, NJ $%.2f" % tuple(t.loc[s, "gain_state"] for s in ("DC", "MD", "NJ")))
    # Reweighted to Brookings' cell shares.
    rw = {}
    for st in t.index:
        f = pd.read_csv(os.path.join(rundir, f"families_{st}.csv.gz")).set_index("household_id")
        wh = fam.w_brookings.reindex(f.index)
        assert wh.notna().all()
        rw[st] = (wh * 12 * (f.snap_fed_bbce - f.snap_fed_nobbce)).sum() / fam.w_brookings.sum()
    rw = pd.Series(rw)
    print("  35 jurisdictions, gain reweighted to Brookings' cell shares:", q(rw.loc[over]),
          "| %% of Brookings' index: median %.2f" % (100 * rw.loc[over] / t.loc[over, "brookings_snap_index"]).median())
    # Levels.
    c = t.drop(index=["AK", "HI"])
    ratio = c.snap_index_fed_nobbce / c.brookings_snap_index
    hs, hi = np.polyfit(c.brookings_tanf_index, c.brookings_snap_index, 1)
    ps, pi = np.polyfit(c.brookings_tanf_index, c.snap_index_fed_nobbce, 1)
    print("  WI federal-rules index $%.2f vs Brookings $%.2f (%+.2f%%); SSI index $%.2f vs Brookings $%.2f; TANF index $%.2f vs Brookings $%.2f" % (
        t.loc["WI", "snap_index_fed_nobbce"], t.loc["WI", "brookings_snap_index"],
        100 * (t.loc["WI", "snap_index_fed_nobbce"] / t.loc["WI", "brookings_snap_index"] - 1),
        t.loc["WI", "ssi_index"], 1000 * h24.loc["Wisconsin", "ssi"], t.loc["WI", "tanf_index"], t.loc["WI", "brookings_tanf_index"]))
    print("  49 jurisdictions: PE/Brookings federal-rules ratio %s" % q(ratio, "%.3f"))
    print("  49 jurisdictions, regressed on Brookings' TANF index: Brookings %.1f %+.4f x TANF; PE %.1f %+.4f x TANF; corr(PE, Brookings) %.3f" % (
        hi, hs, pi, ps, np.corrcoef(c.snap_index_fed_nobbce, c.brookings_snap_index)[0, 1]))
    print("  PE SSI index across 51: $%.2f to $%.2f; Brookings $%.2f to $%.2f" % (
        t.ssi_index.min(), t.ssi_index.max(), 1000 * h24.ssi.min(), 1000 * h24.ssi.max()))
    rows.append({"run": name, "median_gain_35": g.gain_fed.median(), "median_pct_brookings_35": g.gain_fed_pct_brookings.median(),
                 "median_gain_35_brookings_cells": rw.loc[over].median(), "max_gain_other_16": t.loc[other].gain_fed.max(),
                 "wi_fed_rules": t.loc["WI", "snap_index_fed_nobbce"], "wi_brookings": t.loc["WI", "brookings_snap_index"],
                 "median_ratio_49": ratio.median(), "pe_intercept_on_brookings_tanf": pi, "pe_slope_on_brookings_tanf": ps,
                 "gainers_with_tanf": int(t.gainers_with_tanf.sum()), "losers": int(t.losers.sum())})
    # Wisconsin by cell.
    f = pd.read_csv(os.path.join(rundir, "families_WI.csv.gz")).set_index("household_id").join(fam[["cell"]])
    hw = cells[(cells.state == "Wisconsin") & (cells.year == 2024)].set_index("cell")
    out = []
    for cl, d in f.groupby("cell"):
        out.append({"cell": cl, "share": d.w.sum() / f.w.sum(), "brookings_share": brookings_share[cl],
                    "snap": np.average(12 * d.snap_fed_nobbce, weights=d.w), "brookings_snap": 1000 * hw.loc[cl, "snap"],
                    "ssi": np.average(12 * d.ssi_fed_nobbce, weights=d.w), "brookings_ssi": 1000 * hw.loc[cl, "ssi"],
                    "gain": np.average(12 * (d.snap_fed_bbce - d.snap_fed_nobbce), weights=d.w)})
    out = pd.DataFrame(out)
    out["snap_ratio"] = out.snap / out.brookings_snap
    print("  Wisconsin by cell:")
    print(out.round(3).to_string(index=False))

print()
pd.set_option("display.width", 250)
print(pd.DataFrame(rows).round(3).to_string(index=False))
