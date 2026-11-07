"""Group results, poverty bands and family-type shares for one run. Aggregates only.

Usage: detail.py PERSONS RUN_DIR SUMMARY_CSV [--earnings-scale X]

--earnings-scale gives the factor the run applied to earnings, so the poverty bands use the earnings the run saw.
"""
import sys

import numpy as np
import pandas as pd
from policyengine_us.system import system

persons_path, rundir, summary_path = sys.argv[1:4]
SCALE = float(sys.argv[sys.argv.index("--earnings-scale") + 1]) if "--earnings-scale" in sys.argv else 1.0
per = pd.read_csv(persons_path)
fam = per.groupby("person_household_id").agg(
    w=("household_weight", "first"), size=("role", "size"), earnings=("earnings", "sum"))
W = fam.w.sum()
t = pd.read_csv(summary_path, index_col="state")

# Jurisdiction groups (PE-US parameters on 2024-07-01; see bbce_params_2024.py).
above130 = t.index[np.isfinite(t.bbce_gross_limit) & (t.bbce_gross_limit > 1.3)].tolist()
bbce_over_130_for_earners = sorted(above130 + ["NY"])
other = sorted(set(t.index) - set(bbce_over_130_for_earners))
print(f"jurisdictions with a BBCE limit above 130% for working families: {len(bbce_over_130_for_earners)}"
      f" (incl. DC and NY): {bbce_over_130_for_earners}")
print(f"other {len(other)}: {other}")
g = t.loc[bbce_over_130_for_earners]
q = lambda s: f"median {s.median():.3f}, IQR {s.quantile(.25):.3f}-{s.quantile(.75):.3f}, range {s.min():.3f}-{s.max():.3f}"
print("  gain $/family/yr:", q(g.gain_fed))
print("  gain % of Brookings' index:", q(g.gain_fed_pct_brookings))
print("  gain % of PE fed-rules index:", q(g.gain_fed_pct_pe))
print("  other jurisdictions: max gain", t.loc[other].gain_fed.round(2).to_dict())
net = ["HI", "LA", "ND", "RI"]
print("  net-test states:", t.loc[net].gain_fed.round(1).to_dict())
nonet = g.drop(index=[s for s in net if s in g.index])
print(f"  without the net test ({len(nonet)}): ", q(nonet.gain_fed), "| % Brookings:", q(nonet.gain_fed_pct_brookings))
# New York's limit for households with earnings. Families with no earnings have no gross income in these runs, so
# any limit admits them.
ny_earned = float(system.parameters("2024-07-01").gov.hhs.tanf.non_cash.income_limit.ny.earned_income)
for lim, s in nonet.groupby(nonet.bbce_gross_limit.where(nonet.index != "NY", ny_earned)):
    print(f"    limit for working families {lim}: {sorted(s.index)} median gain {s.gain_fed.median():.1f}, median % Brookings {s.gain_fed_pct_brookings.median():.1f}")

ratio = t.snap_index_fed_nobbce / t.brookings_snap_index
print("PE fed-rules / Brookings SNAP, all 51: median %.3f, IQR %.3f-%.3f; excl AK/HI median %.3f" % (
    ratio.median(), ratio.quantile(.25), ratio.quantile(.75), ratio.drop(index=["AK", "HI"]).median()))
print("corr(PE SNAP fed rules, PE TANF) all 51 %.3f; corr(Brookings SNAP, Brookings TANF) all 51 %.3f" % (
    np.corrcoef(t.snap_index_fed_nobbce, t.tanf_index)[0, 1], np.corrcoef(t.brookings_snap_index, t.brookings_tanf_index)[0, 1]))
sua = ["CA", "CT", "DC", "ME", "MA", "MI", "MT", "NY", "OR", "PA", "RI", "VT", "WA"]
print("median PE/Brookings ratio, 13 jurisdictions where PE's own rules give every household the SUA %.3f, "
      "other 38 %.3f" % (
    ratio.loc[sua].median(), ratio.drop(index=sua).median()))

# Pooled detail over the jurisdictions with a BBCE limit above 130% for working families.
fpg23 = system.parameters("2023-01-01").gov.hhs.fpg
rows, pos = [], []
for st in t.index:
    f = pd.read_csv(f"{rundir}/families_{st}.csv.gz").set_index("household_id")
    f = f.join(fam[["size", "earnings"]])
    grp = "AK" if st == "AK" else ("HI" if st == "HI" else "CONTIGUOUS_US")
    fpg = fpg23.first_person[grp] + fpg23.additional_person[grp] * (f["size"] - 1)
    f["pct_fpg"] = 100 * f.earnings * SCALE / fpg
    f["gain"] = 12 * (f.snap_fed_bbce - f.snap_fed_nobbce)
    pos.append({"state": st,
                "share_positive_fed_nobbce": (f.w * (f.snap_fed_nobbce > 0)).sum() / W,
                "share_positive_fed_bbce": (f.w * (f.snap_fed_bbce > 0)).sum() / W,
                "share_gaining": (f.w * (f.gain > 0.005)).sum() / W})
    if st in bbce_over_130_for_earners:
        f["state"] = st
        rows.append(f[f.gain > 0.005][["w", "gain", "pct_fpg", "family_type", "eldis", "ssi_fed_bbce", "size", "state"]])
pos = pd.DataFrame(pos).set_index("state")
pos.to_csv(summary_path.replace(".csv", "_positive_shares.csv"))
print("\nshare of all sample families with SNAP > 0 (fed rules -> with BBCE), and share gaining:")
print(pos.loc[bbce_over_130_for_earners].round(4).describe().loc[["min", "50%", "max"]].to_string())
print(pos.loc[["CA", "FL", "TX", "NY", "LA", "HI", "MA"]].round(4).to_string())

G = pd.concat(rows)
tot = (G.w * G.gain).sum()
bands = pd.cut(G.pct_fpg, [-1, 100, 130, 150, 165, 185, 200, 1e9],
               labels=["<=100", "100-130", "130-150", "150-165", "165-185", "185-200", ">200"])
print("\npooled over those jurisdictions: share of the BBCE gain by family earnings (% of the 2023 guideline):")
print((G.w * G.gain).groupby(bands, observed=False).sum().div(tot).round(4).to_string())
print("share of gain by family type:", (G.w * G.gain).groupby(G.family_type).sum().div(tot).round(4).to_dict())
print("share of gain to families with an elderly/disabled SNAP member: %.4f" % ((G.w * G.gain)[G.eldis.astype(bool)].sum() / tot))
print("share of gain to families with SSI: %.4f" % ((G.w * G.gain)[G.ssi_fed_bbce > 0].sum() / tot))
avg = G.groupby("state").apply(lambda d: (d.w * d.gain).sum() / d.w.sum() / 12)
print("average monthly gain per gaining family across those jurisdictions: median $%.2f (range %.2f-%.2f)" % (
    avg.median(), avg.min(), avg.max()))
print("  Hawaii $%.2f; the other %d: $%.2f (%s) to $%.2f (%s)" % (
    avg["HI"], len(avg) - 1, avg.drop(index="HI").min(), avg.drop(index="HI").idxmin(),
    avg.drop(index="HI").max(), avg.drop(index="HI").idxmax()))
