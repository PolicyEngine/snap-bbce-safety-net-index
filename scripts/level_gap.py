"""Level comparisons between PolicyEngine's federal-rules SNAP index and Brookings' published 2024 index.

Usage: level_gap.py SUMMARY_CSV

Prints each statistic with the set of jurisdictions it covers: all 51 (50 states and DC), and the 49
jurisdictions other than Alaska and Hawaii (48 states and DC), whose SNAP rules differ from the rest.
"""
import sys

import numpy as np
import pandas as pd

t = pd.read_csv(sys.argv[1], index_col="state")
assert len(t) == 51
SUA = ["CA", "CT", "DC", "MA", "ME", "MI", "MT", "NY", "OR", "PA", "RI", "VT", "WA"]
gap = 100 * (t.snap_index_fed_nobbce / t.brookings_snap_index - 1)
c = t.drop(index=["AK", "HI"])
gap49 = gap.drop(index=["AK", "HI"])


def q(s):
    return f"median {s.median():.3f}%, IQR {s.quantile(.25):.3f}-{s.quantile(.75):.3f}%, range {s.min():.2f}% ({s.idxmin()}) to {s.max():.2f}% ({s.idxmax()})"


print("PE federal-rules index over Brookings', all 51:", q(gap))
print("PE federal-rules index over Brookings', 49 (48 states and DC):", q(gap49))
print(f"  CA {gap['CA']:.2f}%, VT {gap['VT']:.2f}%")
print(f"  13 jurisdictions where PE's own rules give every household the SUA: median {gap.loc[SUA].median():.2f}%; "
      f"other 38: median {gap.drop(index=SUA).median():.2f}%")
print(f"corr(PE federal-rules SNAP, Brookings SNAP), 49: {np.corrcoef(c.snap_index_fed_nobbce, c.brookings_snap_index)[0, 1]:.3f}")
print(f"corr(PE TANF, Brookings TANF), 49: {np.corrcoef(c.tanf_index, c.brookings_tanf_index)[0, 1]:.3f}")
slope, intercept = np.polyfit(c.brookings_tanf_index, c.brookings_snap_index, 1)
r = np.corrcoef(c.brookings_tanf_index, c.brookings_snap_index)[0, 1]
print(f"Brookings SNAP on Brookings TANF, 49: slope {slope:.4f}, correlation {r:.4f}, R^2 {r * r:.4f}")
print(f"PE SSI index: min ${t.ssi_index.min():.2f}, max ${t.ssi_index.max():.2f}")
print(f"gainers receiving TANF (zero by construction; see tanf_cross_check.py): {int(t.gainers_with_tanf.sum())}; receiving SSI: "
      f"{int(t.gainers_with_ssi.sum())}; families losing SNAP under BBCE: {int(t.losers.sum())}")
