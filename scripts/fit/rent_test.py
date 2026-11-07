"""Would a rent deduction fit Brookings' published Wisconsin SNAP? A differential check by hand; aggregates only.

Brookings' appendix imputes SNAP "using earnings and family structure" and mentions no rent, shelter costs or utility
allowances. Wisconsin carries zero TANF in every Brookings year, so its SNAP depends only on earnings, family size and
SNAP's rules. Its 2024 EITC pins the earnings scale near 1.07 without touching SNAP (scripts/fit/joint_anchor.py). At that
scale this script adds SNAP's excess shelter deduction for a range of monthly rents (2024 dollars, deflated by CPI-U
in earlier years) and reports our SNAP over Brookings' for its three family types with no disabled member.

Rules (federal_snap.py, 7 USC 2014(e)): income after the 20% earned income and standard deductions, less the excess of
shelter costs over half that income, capped for households with no elderly or disabled member (all families here).
Parameters come from PolicyEngine-US 2.100.0's YAML: max allotments, standard deduction, FPG, shelter cap, CPI-U.

Usage: rent_test.py PERSONS BROOKINGS_DIR [SCALE]
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ja", os.path.join(HERE, "joint_anchor.py"))
ja = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ja)

persons, bdir = sys.argv[1:3]
SCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 1.07
RENTS = (0, 250, 500, 750, 1000, 1250, 1500)


def snap_rent(n, em, y, rent):
    return ja.federal_snap.benefit(n, em, y, rent=rent)


per = pd.read_csv(persons, usecols=["person_household_id", "household_weight", "role", "is_disabled", "earnings"])
fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), n=("role", "size"), dis=("is_disabled", "max"),
                                             earn=("earnings", "sum"))
has = per.groupby("person_household_id").role.apply(set)
fam["ft"] = np.where(has.apply(lambda v: "spouse" in v), "Ref person + spouse", np.where(has.apply(lambda v: "partner" in v), "Partner", "Single"))
fam["cell"] = fam.ft + "/" + fam.dis.astype(int).astype(str)
fam = fam[fam.dis == 0]
wi = ja.load_cells(bdir)
n, w = fam.n.to_numpy(), fam.w.to_numpy()
em = fam.earn.to_numpy() / 12 * SCALE

print(f"Wisconsin, families with no disabled member, earnings x {SCALE}; our plain-rules SNAP over Brookings' published SNAP")
print("rent is monthly, in 2024 dollars; 'all years' is the geometric mean over 2016-2019, 2023 and 2024\n")
rows = []
for rent in RENTS:
    row = {"rent": rent}
    logs = {cl: [] for cl in ja.CELLS}
    for y in ja.BENEFIT_YEARS:
        k = ja.ann[str(y)] / ja.ann["2024"]
        v = 12 * snap_rent(n, em * k, y, rent * k) / k
        for cl in ja.CELLS:
            m = (fam.cell == cl).to_numpy()
            ratio = np.average(v[m], weights=w[m]) / (1000 * float(wi.loc[(y, cl), "snap"]))
            logs[cl].append(np.log(ratio))
            if y == 2024:
                row[f"2024 {cl.split('/')[0]}"] = ratio
    for cl in ja.CELLS:
        row[f"all years {cl.split('/')[0]}"] = float(np.exp(np.mean(logs[cl])))
    rows.append(row)
pd.set_option("display.width", 250)
print(pd.DataFrame(rows).round(3).to_string(index=False))
