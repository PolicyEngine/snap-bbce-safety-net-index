"""Across states, does Brookings' SNAP index fall with its SSI index, holding its TANF index fixed? Aggregates only.

For each year, regress Brookings' SNAP index on a polynomial in its TANF index plus its SSI index, across the 49
jurisdictions other than Alaska and Hawaii, and print the SSI slope with its standard error; then repeat over the
states with a TANF index under $700. A slope near -0.3 to -0.5 fits SSI counted as SNAP income.

Usage: ssi_slope.py [BROOKINGS_DIR]
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw_cache import BROOKINGS  # noqa: E402

bdir = sys.argv[1] if len(sys.argv) > 1 else BROOKINGS
bk = pd.read_stata(os.path.join(bdir, "1_noimmig v7.dta"))


def fit(c, deg):
    t = 1000 * c.tanf.to_numpy(float)
    s = 1000 * c.ssi.to_numpy(float)
    y = 1000 * c.snap.to_numpy(float)
    X = np.column_stack([t ** k for k in range(deg + 1)] + [s - 633.6])
    b, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    dof = len(y) - X.shape[1]
    se = np.sqrt(res @ res / dof * np.linalg.inv(X.T @ X)[-1, -1])
    return b, se, np.abs(res).max(), X


for y in (2024, 2023, 2019, 2018):
    h = bk[bk.year == y].set_index("state").drop(index=["Alaska", "Hawaii"])
    print(y, "states", len(h), "SSI sd", round(1000 * h.ssi.std(), 1))
    for deg in (1, 2, 3, 4):
        b, se, mx, X = fit(h, deg)
        print(f"  TANF poly deg {deg}: SSI slope {b[-1]:+.3f} (se {se:.3f}); intercept at TANF 0, base SSI {b[0]:.0f}; max abs resid {mx:.1f}")
    low = h[1000 * h.tanf < 700]
    for deg in (1, 2):
        b, se, mx, X = fit(low, deg)
        print(f"  TANF<$700 only ({len(low)} states) deg {deg}: SSI slope {b[-1]:+.3f} (se {se:.3f}); intercept {b[0]:.0f}; max abs resid {mx:.1f}")
h = bk[bk.year == 2024].set_index("state").drop(index=["Alaska", "Hawaii"])
print((1000 * h[["snap", "tanf", "ssi"]]).round(1).sort_values("tanf").to_string())
