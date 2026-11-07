"""Test sample, earnings scale and the standard deduction jointly against Brookings' published Wisconsin cells.

Wisconsin carries zero TANF in every Brookings year, so SNAP there reflects earnings and rules alone. Three anchors
answer different questions:
  credits    the 2024 federal EITC depends on earnings and tax rules, not on SNAP's rules. It bounds the earnings scale.
  July 2020  emergency allotments gave every eligible family the maximum allotment, so the benefit formula drops out.
             Only eligibility and family size remain, and with the standard deduction the net test doesn't bind.
  benefit    2016-2019, 2023 and 2024, when the regular benefit formula applied. Given the scale, these test the rule.

The script computes SNAP (federal_snap.py) and the EITC (EITC below) by hand. Its fit chooses the 7% earnings raise
the main runs use (README, Earnings). Cells: Wisconsin's family types with no disabled member.

Usage: joint_anchor.py BROOKINGS_DIR NAME=PERSONS [NAME=PERSONS ...]
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import federal_snap  # noqa: E402
from federal_snap import PE, at, params  # noqa: E402,F401  (rent_test.py and wage_index_test.py read these here)

SCALES = (1.00, 1.03, 1.05, 1.07, 1.10)
CELLS = ("Single/0", "Ref person + spouse/0", "Partner/0")
BENEFIT_YEARS = (2016, 2017, 2018, 2019, 2023, 2024)


cpi = yaml.safe_load(open(os.path.join(PE, "gov/bls/cpi/cpi_u.yaml")))["values"]
s = pd.Series({str(k): float(v) for k, v in cpi.items()})
ann = s.groupby(s.index.str[:4]).mean()


def snap_value(n, em, y, use_std=True, max_for_all=False):
    """Monthly federal SNAP by hand (federal_snap.py); use_std=False drops the standard deduction."""
    return federal_snap.benefit(n, em, y, standard_deduction=use_std, max_for_all=max_for_all)


EITC = {0: (0.0765, 632, 10330, 17250, 0.0765), 1: (0.34, 4213, 22720, 29640, 0.1598),
        2: (0.40, 6960, 22720, 29640, 0.2106), 3: (0.45, 7830, 22720, 29640, 0.2106)}


def eitc(earn, kids, joint):
    out = np.zeros(len(earn))
    for k, (pi, mx, a, j, po) in EITC.items():
        m = np.minimum(kids, 3) == k
        start = np.where(joint, j, a)
        out[m] = np.maximum(np.minimum(pi * earn[m], mx) - po * np.maximum(earn[m] - start[m], 0), 0)
    return out


def load_cells(bdir):
    c = pd.read_stata(os.path.join(bdir, "13b_noimmig v7.dta"))
    c["cell"] = c.family_type.astype(str) + "/" + c.any_dis.astype(int).astype(str)
    return c[c.state == "Wisconsin"].set_index(["year", "cell"])


def evaluate(name, per, wi, scales=SCALES, earn_col="earnings"):
    """Return one row per scale and standard-deduction choice. per holds person rows of one sample."""
    per = per.assign(earnings=per[earn_col])
    rows = []
    kid = per[per.role == "other"]
    q = (kid.age < 19) | ((kid.age < 24) & (kid.is_full_time_college_student == 1)) | (kid.is_disabled == 1)
    fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), n=("role", "size"), dis=("is_disabled", "max"))
    fam["kids"] = q.groupby(kid.person_household_id).sum()
    fam["kids"] = fam.kids.fillna(0).astype(int)
    r = per.pivot_table(index="person_household_id", columns="role", values="earnings", aggfunc="sum").reindex(columns=["head", "spouse", "partner"]).fillna(0)
    fam["tax_earn"] = r["head"] + r["spouse"]
    fam["all_earn"] = r["head"] + r["spouse"] + r["partner"]
    has = per.groupby("person_household_id").role.apply(set)
    fam["ft"] = np.where(has.apply(lambda v: "spouse" in v), "Ref person + spouse", np.where(has.apply(lambda v: "partner" in v), "Partner", "Single"))
    fam["cell"] = fam.ft + "/" + fam.dis.astype(int).astype(str)
    fam = fam[fam.dis == 0]
    joint = (fam.ft == "Ref person + spouse").to_numpy()
    n = fam.n.to_numpy()
    w = fam.w.to_numpy()

    def cellmean(v):
        return {cl: float(np.average(v[(fam.cell == cl).to_numpy()], weights=w[(fam.cell == cl).to_numpy()])) for cl in CELLS}

    for sc in scales:
        et = cellmean(eitc(fam.tax_earn.to_numpy() * sc, fam.kids.to_numpy(), joint))
        k20 = ann["2020"] / ann["2024"]
        em = fam.all_earn.to_numpy() / 12 * sc
        ea_std = cellmean(12 * snap_value(n, em * k20, 2020, True, True) / k20)
        ea_no = cellmean(12 * snap_value(n, em * k20, 2020, False, True) / k20)
        for use_std in (True, False):
            logs = {cl: [] for cl in CELLS}
            for y in BENEFIT_YEARS:
                k = ann[str(y)] / ann["2024"]
                v = cellmean(12 * snap_value(n, em * k, y, use_std) / k)
                for cl in CELLS:
                    logs[cl].append(np.log(v[cl] / (1000 * float(wi.loc[(y, cl), "snap"]))))
            row = {"sample": name, "scale": sc, "std": use_std}
            errs = []
            for cl in CELLS:
                tag = cl[:3]
                row[f"eitc_{tag}"] = et[cl] / (1000 * float(wi.loc[(2024, cl), "fedeitc"]))
                row[f"ea20_{tag}"] = (ea_std if use_std else ea_no)[cl] / (1000 * float(wi.loc[(2020, cl), "snap"]))
                row[f"ben_{tag}"] = float(np.exp(np.mean(logs[cl])))
                errs += logs[cl]
            row["rms_benefit"] = float(np.sqrt(np.mean(np.square(errs))))
            row["rms_ea20"] = float(np.sqrt(np.mean([np.log(row[f"ea20_{cl[:3]}"]) ** 2 for cl in CELLS])))
            row["rms_eitc"] = float(np.sqrt(np.mean([np.log(row[f"eitc_{cl[:3]}"]) ** 2 for cl in CELLS])))
            rows.append(row)
    return rows


def table(rows):
    res = pd.DataFrame(rows)
    res["rms_all"] = np.sqrt((res.rms_benefit ** 2 + res.rms_ea20 ** 2 + res.rms_eitc ** 2) / 3)
    return res


COLS = ["sample", "scale", "std", "rms_all", "rms_benefit", "rms_ea20", "rms_eitc", "ben_Sin", "ben_Ref", "ben_Par", "ea20_Sin", "ea20_Ref", "ea20_Par", "eitc_Sin", "eitc_Ref", "eitc_Par"]

if __name__ == "__main__":
    wi = load_cells(sys.argv[1])
    rows = []
    for spec in sys.argv[2:]:
        name, path = spec.split("=", 1)
        rows += evaluate(name, pd.read_csv(path, usecols=["person_household_id", "household_weight", "role", "age", "is_disabled", "earnings", "is_full_time_college_student"]), wi)
    res = table(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(res[COLS].round(3).to_string(index=False))
    print("\nbest ten by rms_all:")
    print(res.sort_values("rms_all")[COLS].head(10).round(3).to_string(index=False))
