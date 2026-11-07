"""Does a wage index explain the earnings scale? Inflate each source year's earnings with SSA's national average wage
index (NAWI, from PolicyEngine-US's gov.ssa.nawi) instead of CPI-U, then test against Brookings' Wisconsin cells with
joint_anchor.evaluate. Aggregates only.

Usage: wage_index_test.py PERSONS BROOKINGS_DIR
"""
import os
import sys

import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw_cache import load_module  # noqa: E402

ja = load_module("ja", "scripts/fit/joint_anchor.py")
persons, bdir = sys.argv[1:3]
nawi = yaml.safe_load(open(os.path.join(ja.PE, "gov/ssa/nawi.yaml")))["values"]
nawi = {k.year: float(v) for k, v in nawi.items()}
cpi = ja.ann
per = pd.read_csv(persons, usecols=["person_household_id", "household_weight", "role", "age", "is_disabled", "earnings",
                                    "is_full_time_college_student", "source_year"])
ratio = {int(y): float((nawi[2024] / nawi[y]) / (cpi["2024"] / cpi[str(y)])) for y in sorted(per.source_year.unique())}
print("NAWI factor over CPI-U factor, by income year:", {y: round(r, 4) for y, r in ratio.items()})
fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), y=("source_year", "first"))
print("weighted mean over families: %.4f" % ((fam.y.map(ratio) * fam.w).sum() / fam.w.sum()))
per["earnings_nawi"] = per.earnings * per.source_year.map(ratio)
wi = ja.load_cells(bdir)
rows = ja.evaluate("CPI-U", per, wi, scales=(1.00, 1.07, 1.10)) + ja.evaluate("NAWI", per, wi, scales=(0.97, 1.00), earn_col="earnings_nawi")
res = ja.table(rows)
pd.set_option("display.width", 250)
print(res[res["std"]][ja.COLS].round(3).to_string(index=False))
