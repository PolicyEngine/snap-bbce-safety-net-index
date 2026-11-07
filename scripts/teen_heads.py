"""How much families headed by someone under 18 contribute to a run's federal-rules index and BBCE gain. Aggregates only.

PolicyEngine-US's is_in_k12_school formula treats everyone aged 5-17 as a K-12 student, and snap_excluded_child_earner
leaves such a member's earnings out of SNAP income (7 USC 2014(d)(7)), including a teenager who heads a family.
Brookings' appendix doesn't say whether its team excludes them. This prints the share of families with a head under 18 and their
contribution to the index and the gain, per state.

Usage: teen_heads.py PERSONS RUN_DIR STATE [STATE ...]
"""
import os
import sys

import numpy as np
import pandas as pd

persons, run_dir, *states = sys.argv[1:]
per = pd.read_csv(persons, usecols=["person_household_id", "role", "age", "earnings"])
heads = per[per.role == "head"].set_index("person_household_id")
teen = heads.age < 18
print(f"families with a head under 18: {int(teen.sum())} records")
for st in states:
    f = pd.read_csv(os.path.join(run_dir, f"families_{st}.csv.gz")).set_index("household_id")
    t = teen.reindex(f.index).fillna(False).astype(bool)
    W = f.w.sum()
    idx = 12 * f.snap_fed_nobbce
    gain = 12 * (f.snap_fed_bbce - f.snap_fed_nobbce)
    print(f"{st}: weight share {f.w[t].sum() / W:.4f}; index ${(f.w * idx).sum() / W:.2f}, of which teen-headed families "
          f"${(f.w[t] * idx[t]).sum() / W:.2f}; gain ${(f.w * gain).sum() / W:.2f}, of which ${(f.w[t] * gain[t]).sum() / W:.2f}; "
          f"teen-headed families with earnings and SNAP: {int(((heads.earnings.reindex(f.index[t]) > 0) & (f.snap_fed_nobbce[t] > 0)).sum())}")
