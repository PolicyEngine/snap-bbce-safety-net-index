"""BBCE gain under hand-written federal rules across sample variants and earnings scales. Aggregates only.

For each variant and scale it prints the federal-rules SNAP index and the gain from a BBCE gross income limit of
160%, 165%, 185% or 200% of poverty with no net income test, using parents' earnings ("earn") or every member's own
earnings ("own").

Usage: variant_gain.py
"""
import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw_cache import load_module, raw_tables  # noqa: E402

ex = load_module("ex", "scripts/build_sample.py")
ja = load_module("ja", "scripts/fit/joint_anchor.py")
raw = raw_tables(ex)
cpi = ex.annual_cpi()


def build(**kw):
    parts = []
    with contextlib.redirect_stderr(io.StringIO()):
        for y_, (p, h) in raw.items():
            parts.append(ex.build_year(p, h, y_, cpi["2024"] / cpi[str(y_ - 1)], kw.get("parents", "biological"),
                                       kw.get("disability", "notw"), kw.get("units", "families"), kw.get("screen", "unit")))
    return pd.concat(parts, ignore_index=True)


def ben(n, em, use_std=True, limit=None):
    """Monthly July 2024 SNAP by hand (federal_snap.py), with a BBCE limit of limit times the guideline if given."""
    return ja.federal_snap.benefit(n, em, 2024, standard_deduction=use_std, bbce_limit=limit)


rows = []
for name, kw in [("fam notw unit", dict()), ("fam notw hhscreen", dict(screen="household")),
                 ("fam hp_sga hhscreen", dict(disability="hp_sga", screen="household")), ("hh notw", dict(units="households")),
                 ("hh appendix", dict(units="households", disability="appendix"))]:
    per = build(**kw)
    f = per.groupby("person_household_id").agg(w=("household_weight", "first"), n=("role", "size"), earn=("earnings", "sum"),
                                               own=("own_earnings", "sum"))
    n, w = f.n.to_numpy(), f.w.to_numpy()
    for col in ("earn", "own"):
        for sc in (1.0, 1.03, 1.05, 1.07, 1.10):
            em = f[col].to_numpy() / 12 * sc
            s0 = ben(n, em)
            row = {"sample": name, "earn": col, "scale": sc, "index": (w * 12 * s0).sum() / w.sum()}
            for L in (1.6, 1.65, 1.85, 2.0):
                row[f"gain{int(L * 100)}"] = (w * 12 * (ben(n, em, limit=L) - s0)).sum() / w.sum()
            rows.append(row)
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).round(2).to_string(index=False))
