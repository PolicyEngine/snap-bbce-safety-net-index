"""Across states, does the gap between PolicyEngine-US's SNAP and Brookings' follow the gap in TANF? Aggregates only.

Reads compare_replication.py's output (all families, cell "all") and prints, for SNAP and TANF, PolicyEngine-US minus Brookings in
dollars per family per year, their correlation and least-squares slope across jurisdictions, and the jurisdictions
where PolicyEngine-US's SNAP falls furthest below or rises furthest above Brookings', with both TANF values.

Usage: replication_snap_tanf.py COMPARE_CSV
"""
import sys

import numpy as np
import pandas as pd

c = pd.read_csv(sys.argv[1])
c = c[c.cell == "all"]
snap = c[(c.program == "snap") & (c.pe_variable == "snap")].set_index("state")
tanf = c[(c.program == "tanf") & (c.pe_variable == "tanf")].set_index("state")
d = pd.DataFrame({"snap_bk": snap.brookings, "snap_pe": snap.policyengine, "snap_ratio": snap.ratio,
                  "tanf_bk": tanf.brookings, "tanf_pe": tanf.policyengine})
d["snap_gap"] = d.snap_pe - d.snap_bk
d["tanf_gap"] = d.tanf_pe - d.tanf_bk
for label, x in (("51 jurisdictions", d), ("49 (without AK, HI)", d.drop(index=["AK", "HI"]))):
    slope = np.polyfit(x.tanf_gap, x.snap_gap, 1)[0]
    print(f"{label}: SNAP gap on TANF gap, correlation {np.corrcoef(x.tanf_gap, x.snap_gap)[0, 1]:.3f}, "
          f"slope {slope:.3f}")
pd.set_option("display.width", 200)
cols = ["snap_bk", "snap_pe", "snap_ratio", "tanf_bk", "tanf_pe"]
print("\nPolicyEngine-US SNAP furthest below Brookings':")
print(d.sort_values("snap_ratio")[cols].head(5).round(2).to_string())
print("\nPolicyEngine-US SNAP furthest above Brookings':")
print(d.sort_values("snap_ratio")[cols].tail(5).round(2).to_string())
lo = d.sort_values("snap_ratio")
print(f"\nPolicyEngine-US TANF above Brookings' in the 5 lowest SNAP ratios: {int((lo.head(5).tanf_pe > lo.head(5).tanf_bk).sum())}/5; "
      f"below Brookings' in the 5 highest: {int((lo.tail(5).tanf_pe < lo.tail(5).tanf_bk).sum())}/5")
