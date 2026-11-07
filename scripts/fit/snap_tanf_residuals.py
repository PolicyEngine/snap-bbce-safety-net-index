"""Regress Brookings' 2024 SNAP index on its TANF index across the 48 states other than Alaska and Hawaii, plus DC,
and print each jurisdiction's residual, then how far Alaska and Hawaii sit from the same line. Then add the BBCE gain
we estimate for each state to the regression, and compare the residuals of the jurisdictions with a BBCE limit above
130% with the rest. Aggregates only (Brookings' published state values and our state estimates).

A rent deduction at local levels would lift high-rent states above this line, and BBCE would lift the states that use
it by about the gain we estimate. SNAP's federal amounts (maximum allotments, the standard deduction, the shelter cap
and the poverty guidelines) differ only for Alaska and Hawaii, which is why the fit leaves them out.

Usage: snap_tanf_residuals.py SUMMARY_CSV   (a run summary from summarize.py; the BBCE test reads its gain_fed column,
       so pass the main run's summary, out/summary_appendix_x107.csv)
"""
import sys

import numpy as np
import pandas as pd

full = pd.read_csv(sys.argv[1], index_col="state")
t = full.drop(index=["AK", "HI"])
assert len(t) == 49
x, y = t.brookings_tanf_index.to_numpy(float), t.brookings_snap_index.to_numpy(float)
slope, intercept = np.polyfit(x, y, 1)
res = pd.Series(y - (intercept + slope * x), index=t.index)
sd = np.sqrt((res ** 2).sum() / (len(res) - 2))
r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
rms = np.sqrt((res ** 2).mean())
print(f"49 jurisdictions: Brookings SNAP = {intercept:.1f} {slope:+.4f} x Brookings TANF; R2 {r2:.3f}; "
      f"residual standard deviation ${sd:.1f} (n-2 degrees of freedom), root mean square ${rms:.1f}")
print(f"correlation {np.corrcoef(x, y)[0, 1]:.3f}")
print("residuals, $ per family per year:")
for st in ["CA", "MA", "CT", "NY", "NJ", "WA", "MD", "DC"]:
    print(f"  {st} {res[st]:+.1f}")
print("largest 5:", res.sort_values().tail(5).round(1).to_dict())
print("smallest 5:", res.sort_values().head(5).round(1).to_dict())
for st in ["AK", "HI"]:
    tanf, snap = full.loc[st, "brookings_tanf_index"], full.loc[st, "brookings_snap_index"]
    print(f"{st} off the line: SNAP ${snap:,.1f}, TANF ${tanf:,.1f}, predicted ${intercept + slope * tanf:,.1f}, "
          f"residual {snap - (intercept + slope * tanf):+,.1f}")

# Does BBCE show up in Brookings' index? If it did, each dollar of the BBCE gain we estimate (gain_fed, from the run
# behind SUMMARY_CSV) would add about a dollar to Brookings' index, so its coefficient here would sit near 1.
gain = t.gain_fed.to_numpy(float)
X = np.column_stack([np.ones_like(x), x, gain])
b, *_ = np.linalg.lstsq(X, y, rcond=None)
e = y - X @ b
se = np.sqrt(np.diag((e ** 2).sum() / (len(y) - 3) * np.linalg.inv(X.T @ X)))
print(f"adding our BBCE gain: Brookings SNAP = {b[0]:.1f} {b[1]:+.4f} x TANF {b[2]:+.3f} x gain "
      f"(standard error of the gain's coefficient {se[2]:.3f}, {len(y) - 3} degrees of freedom)")
# The headline set: a BBCE limit above 130% for working families, which New York sets for households with earnings.
above = (np.isfinite(t.bbce_gross_limit) & (t.bbce_gross_limit > 1.3)) | (t.index == "NY")
print(f"residual median ${res[above].median():+.2f} in the {above.sum()} of the 49 with a BBCE limit above 130% "
      f"(median gain ${t.gain_fed[above].median():.2f}), ${res[~above].median():+.2f} in the other {(~above).sum()} "
      f"(median gain ${t.gain_fed[~above].median():.2f})")
