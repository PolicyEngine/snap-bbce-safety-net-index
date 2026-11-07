"""Test sample variants against Brookings' published values. Aggregates only.

Each variant rebuilds the sample from the raw ASEC tables with a different unit, screen or disability definition
(see build_sample.py), then prints its family-type-by-disability cell shares against the shares recovered from
Brookings' files, its 2024 EITC by cell against Brookings' Wisconsin values, and joint_anchor.evaluate's fit.

Usage: variant_anchor.py
"""
import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw_cache import BROOKINGS, load_module, raw_tables  # noqa: E402

ex = load_module("ex", "scripts/build_sample.py")
ja = load_module("ja", "scripts/fit/joint_anchor.py")
raw = raw_tables(ex)
cpi = ex.annual_cpi()
wi = ja.load_cells(BROOKINGS)
cells = pd.read_stata(os.path.join(BROOKINGS, "13b_noimmig v7.dta"))
cells["cell"] = cells.family_type.astype(str) + "/" + cells.any_dis.astype(int).astype(str)
one = pd.read_stata(os.path.join(BROOKINGS, "1_noimmig v7.dta"))
piv = cells.pivot_table(index=["year", "state"], columns="cell", values=["snap", "tanf", "ssi", "fedeitc"], observed=True)
X = np.vstack([piv[v].to_numpy(float) for v in ("snap", "tanf", "ssi", "fedeitc")])
y = np.concatenate([one.set_index(["year", "state"])[v].reindex(piv.index).to_numpy(float) for v in ("snap", "tanf", "ssi", "fedeitc")])
ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
b, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
bk_share = pd.Series(b, index=list(piv["snap"].columns))
h24 = cells[(cells.year == 2024) & (cells.state == "Wisconsin")].set_index("cell")
ORDER = ["Single/0", "Ref person + spouse/0", "Partner/0", "Single/1", "Ref person + spouse/1", "Partner/1"]


def build(**kw):
    parts = []
    for y_, (p, h) in raw.items():
        parts.append(ex.build_year(p, h, y_, cpi["2024"] / cpi[str(y_ - 1)], kw.get("parents", "biological"),
                                   kw.get("disability", "notw"), kw.get("units", "families"), kw.get("screen", "unit")))
    return pd.concat(parts, ignore_index=True)


allrows = []
for name, kw in [
    ("fam notw unit", dict()),
    ("fam notw hhscreen", dict(screen="household")),
    ("fam hp_sga unit", dict(disability="hp_sga")),
    ("fam hp_sga hhscreen", dict(disability="hp_sga", screen="household")),
    ("hh notw", dict(units="households")),
    ("hh hp_sga", dict(units="households", disability="hp_sga")),
    ("hh appendix", dict(units="households", disability="appendix")),
    ("fam nilf hhscreen", dict(disability="nilf", screen="household")),
    ("fam appendix hhscreen", dict(disability="appendix", screen="household")),
]:
    with contextlib.redirect_stderr(io.StringIO()):
        per = build(**kw)
    fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), dis=("is_disabled", "max"))
    r = per.groupby("person_household_id").role.apply(set)
    fam["ft"] = np.where(r.apply(lambda s: "spouse" in s), "Ref person + spouse", np.where(r.apply(lambda s: "partner" in s), "Partner", "Single"))
    fam["cell"] = fam.ft + "/" + fam.dis.astype(int).astype(str)
    W = fam.w.sum()
    sh = fam.groupby("cell").w.sum() / W
    print(f"\n=== {name}: families {len(fam)}, weight/yr {W / 5 / 1e6:.2f}m, any disabled {fam.w[fam.dis == 1].sum() / W:.4f} "
          f"(Brookings {bk_share[[c for c in bk_share.index if c.endswith('/1')]].sum():.4f})")
    print("  shares sample/Brookings: " + "  ".join(f"{c[:3]}{c[-1]} {sh[c]:.4f}/{bk_share[c]:.4f}" for c in ORDER)
          + f"  | abs err sum {sum(abs(sh[c] - bk_share[c]) for c in ORDER):.4f}")
    # Federal EITC by all six cells, from the hand-written 2024 rules in joint_anchor.py.
    kid = per[per.role == "other"]
    q = (kid.age < 19) | ((kid.age < 24) & (kid.is_full_time_college_student == 1)) | (kid.is_disabled == 1)
    fam["kids"] = q.groupby(kid.person_household_id).sum()
    fam["kids"] = fam.kids.fillna(0).astype(int)
    rr = per.pivot_table(index="person_household_id", columns="role", values="earnings", aggfunc="sum").reindex(columns=["head", "spouse", "partner"]).fillna(0)
    joint = (fam.ft == "Ref person + spouse").to_numpy()
    e = (rr["head"] + rr["spouse"]).reindex(fam.index).to_numpy()
    for sc in (1.0, 1.05):
        et = ja.eitc(e * sc, fam.kids.to_numpy(), joint)
        print(f"  EITC ratio x{sc:.2f}: " + "  ".join(
            f"{c[:3]}{c[-1]} {np.average(et[(fam.cell == c).to_numpy()], weights=fam.w[fam.cell == c]) / (1000 * float(h24.loc[c, 'fedeitc'])):.3f}"
            for c in ORDER))
    allrows += ja.evaluate(name, per, wi)
res = ja.table(allrows)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)
print("\nbest fifteen by rms_all:")
print(res.sort_values("rms_all")[ja.COLS].head(15).round(3).to_string(index=False))
print("\nwith the standard deduction, scale 1.00, 1.03 and 1.05 for each variant:")
print(res[(res["std"]) & res.scale.isin([1.0, 1.03, 1.05])][ja.COLS].round(3).to_string(index=False))
