"""Compare 2024 federal credits on a rebuilt sample with Brookings' published cells, at several earnings scales.

Written out by hand for speed; a differential check by hand, and no number here feeds a published figure. Credits test the earnings distribution without SNAP's rules, so they
separate an earnings-scale explanation of the SNAP gap from a SNAP-rule explanation.

Tax rules for 2024, from IRS Rev. Proc. 2023-34 and the Internal Revenue Code:
  EITC: phase-in rate, maximum, phase-out start (single/joint) and rate by qualifying children.
  Tax before credits: standard deduction and brackets by filing status.
  CTC: $2,000 per child under 17; $500 for other dependents; phase-out at $200,000/$400,000, $50 per $1,000.
  ACTC: min(unused child credit, $1,700 per child under 17, 15% of earnings above $2,500).

Filing, as in pe_frame.py: a married head files jointly with spouse and children; an unmarried head files as head of
household with the children; a cohabiting partner files alone with no dependents. A dependent counts as an EITC
qualifying child under 19, or under 24 as a full-time student, or at any age if disabled.

Usage: plain_tax_anchor.py PERSONS BROOKINGS_DIR [SCALE ...]
"""
import os
import sys

import numpy as np
import pandas as pd

persons, bdir = sys.argv[1:3]
scales = [float(x) for x in sys.argv[3:]] or [1.0, 1.05, 1.10, 1.15, 1.20]

EITC = {0: (0.0765, 632, 10330, 17250, 0.0765), 1: (0.34, 4213, 22720, 29640, 0.1598),
        2: (0.40, 6960, 22720, 29640, 0.2106), 3: (0.45, 7830, 22720, 29640, 0.2106)}
STD = {"joint": 29200, "hoh": 21900, "single": 14600}
BR = {
    "joint": [(23200, .10), (94300, .12), (201050, .22), (383900, .24), (487450, .32), (731200, .35), (np.inf, .37)],
    "hoh": [(16550, .10), (63100, .12), (100500, .22), (191950, .24), (243700, .32), (609350, .35), (np.inf, .37)],
    "single": [(11600, .10), (47150, .12), (100525, .22), (191950, .24), (243725, .32), (609350, .35), (np.inf, .37)],
}


def eitc(earn, kids, joint, heads_age_ok=None):
    out = np.zeros(len(earn))
    for k, (pi, mx, s, j, po) in EITC.items():
        m = np.minimum(kids, 3) == k
        start = np.where(joint, j, s)
        out[m] = np.maximum(np.minimum(pi * earn[m], mx) - po * np.maximum(earn[m] - start[m], 0), 0)
    return out


def tax_before_credits(earn, status):
    t = np.zeros(len(earn))
    for st, br in BR.items():
        m = status == st
        ti = np.maximum(earn[m] - STD[st], 0)
        lo, acc = 0.0, np.zeros(m.sum())
        for hi, r in br:
            acc += r * np.clip(ti - lo, 0, hi - lo)
            lo = hi
        t[m] = acc
    return t


per = pd.read_csv(persons, usecols=["person_household_id", "household_weight", "role", "age", "is_disabled", "earnings",
                                    "is_full_time_college_student"])
per["adult"] = per.role.isin(["head", "spouse", "partner"])
kid = per[per.role == "other"].copy()
kid["eitc_kid"] = (kid.age < 19) | ((kid.age < 24) & (kid.is_full_time_college_student == 1)) | (kid.is_disabled == 1)
kid["ctc_kid"] = kid.age < 17
kid["dep"] = True
g = kid.groupby("person_household_id")
fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), dis=("is_disabled", "max"))
fam["eitc_kids"] = g.eitc_kid.sum()
fam["ctc_kids"] = g.ctc_kid.sum()
fam["deps"] = g.dep.sum()
fam = fam.fillna(0)
roles = per.pivot_table(index="person_household_id", columns="role", values="earnings", aggfunc="sum").reindex(columns=["head", "spouse", "partner"]).fillna(0)
ages = per[per.role.isin(["head", "partner", "spouse"])].pivot_table(index="person_household_id", columns="role", values="age", aggfunc="first").reindex(columns=["head", "spouse", "partner"])
fam = fam.join(roles).join(ages.add_prefix("age_"))
has = per.groupby("person_household_id").role.apply(set)
fam["ftype"] = np.where(has.apply(lambda s: "spouse" in s), "Ref person + spouse", np.where(has.apply(lambda s: "partner" in s), "Partner", "Single"))
fam["cell"] = fam.ftype + "/" + fam.dis.astype(int).astype(str)
cells = pd.read_stata(os.path.join(bdir, "13b_noimmig v7.dta"))
cells["cell"] = cells.family_type.astype(str) + "/" + cells.any_dis.astype(int).astype(str)
h = cells[(cells.year == 2024) & (cells.state == "Wisconsin")].set_index("cell")
order = ["Single/0", "Ref person + spouse/0", "Partner/0", "Single/1", "Ref person + spouse/1", "Partner/1"]
print(f"{persons}: {len(fam)} families; weighted shares {(fam.groupby('cell').w.sum() / fam.w.sum()).round(4).to_dict()}")
print("Brookings WI 2024 (federal credits don't vary by state):", {c: (round(1000 * float(h.loc[c, 'fedeitc'])), round(1000 * float(h.loc[c, 'actc'])), round(1000 * float(h.loc[c, 'ctc']))) for c in order})
rows = []
for sc in scales:
    head = fam["head"].to_numpy() * sc
    sp = fam["spouse"].to_numpy() * sc
    pa = fam["partner"].to_numpy() * sc
    joint = (fam.ftype == "Ref person + spouse").to_numpy()
    e = head + sp
    status = np.where(joint, "joint", "hoh")
    status = np.where((~joint) & (fam.deps.to_numpy() == 0), "single", status)
    et = eitc(e, fam.eitc_kids.to_numpy().astype(int), joint)
    tax = tax_before_credits(e, status)
    credit = 2000 * fam.ctc_kids.to_numpy() + 500 * (fam.deps.to_numpy() - fam.ctc_kids.to_numpy())
    po = np.where(joint, 400000, 200000)
    credit = np.maximum(credit - 50 * np.ceil(np.maximum(e - po, 0) / 1000), 0)
    # The EITC doesn't reduce the tax that the nonrefundable child credit offsets.
    used = np.minimum(credit, tax)
    unused = credit - used
    actc = np.minimum(np.minimum(unused, 1700 * fam.ctc_kids.to_numpy()), 0.15 * np.maximum(e - 2500, 0))
    is_partner = (fam.ftype == "Partner").to_numpy()
    # A cohabiting partner files alone. Childless EITC for ages 25-64.
    et_p = eitc(pa, np.zeros(len(pa), dtype=int), np.zeros(len(pa), dtype=bool))
    et_p = np.where(is_partner & (fam.age_partner.fillna(0).to_numpy() >= 25) & (fam.age_partner.fillna(0).to_numpy() < 65), et_p, 0)
    t = pd.DataFrame({"w": fam.w, "cell": fam.cell, "eitc": et + et_p, "actc": actc, "ctc_used": used})
    for c in order:
        m = t.cell == c
        wm = t.w[m]
        rows.append({"scale": sc, "cell": c, "eitc": np.average(t.eitc[m], weights=wm), "actc": np.average(t.actc[m], weights=wm), "ctc_used": np.average(t.ctc_used[m], weights=wm),
                     "eitc_ratio": np.average(t.eitc[m], weights=wm) / (1000 * float(h.loc[c, "fedeitc"])), "actc_ratio": np.average(t.actc[m], weights=wm) / (1000 * float(h.loc[c, "actc"])),
                     "ctc_ratio": np.average(t.ctc_used[m], weights=wm) / (1000 * float(h.loc[c, "ctc"]))})
res = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(res[res.scale == scales[0]].drop(columns="scale").round(3).to_string(index=False))
print("\nratios to Brookings by scale (eitc / actc / ctc used):")
for c in order:
    r = res[res.cell == c]
    print(f"  {c:24s} " + "  ".join(f"x{s:.2f}: {a:.3f}/{b:.3f}/{d:.3f}" for s, a, b, d in zip(r.scale, r.eitc_ratio, r.actc_ratio, r.ctc_ratio)))
