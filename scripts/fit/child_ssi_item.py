"""Share of children under 18 that each ASEC year's SSIKIDYN item marks as receiving SSI. Aggregates only.

The 2015-2018 files carry the item, which names the children in a household who receive SSI; the 2019 file
doesn't. build_sample.py assigns SSI that a parent reports for a child to the family's youngest child.

Usage: child_ssi_item.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw_cache import load_module, raw_tables  # noqa: E402

ex = load_module("ex", "scripts/build_sample.py")
raw = raw_tables(ex)
print("ASEC year: weighted share of children under 18 with SSIKIDYN == 1 (the item that names children receiving SSI)")
for y, (p, h) in sorted(raw.items()):
    k = p[p.A_AGE < 18]
    print(y, f"{(k.MARSUPWT * (k.SSIKIDYN == 1)).sum() / k.MARSUPWT.sum():.4f}",
          "item present" if (p.SSIKIDYN != 0).any() else "item absent (all zero)")
