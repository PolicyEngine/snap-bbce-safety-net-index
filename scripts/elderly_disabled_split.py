"""Split each state's BBCE gain between families with and without an elderly or disabled member. Aggregates only.

has_snap_elderly_disabled_member (column eldis, from the BBCE scenario) marks families with an elderly or disabled
member. In most states these families face PolicyEngine-US's BBCE rules for such households. In AL, GA and SC those
rules require every member to qualify, so these families fall under the general 130% rule there. Gains are $ per
family per year, averaged over every family in the sample, so the two parts add up to the state's gain.

Usage: elderly_disabled_split.py RUN_DIR STATE[,STATE...]
"""
import os
import sys

import pandas as pd

run_dir, states = sys.argv[1], sys.argv[2].split(",")
rows = []
for st in states:
    f = pd.read_csv(os.path.join(run_dir, f"families_{st}.csv.gz"), usecols=["w", "snap_fed_bbce", "snap_fed_nobbce", "eldis"])
    W = f.w.sum()
    gain = 12 * (f.snap_fed_bbce - f.snap_fed_nobbce)
    e = f.eldis.astype(bool)
    rows.append({"state": st, "gain": (f.w * gain).sum() / W,
                 "from_eldis_families": (f.w * gain * e).sum() / W,
                 "from_other_families": (f.w * gain * ~e).sum() / W,
                 "eldis_share_of_families": f.w[e].sum() / W})
print(pd.DataFrame(rows).set_index("state").round(3).to_string())
