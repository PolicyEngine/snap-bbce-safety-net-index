"""Fit the earnings scale finely: joint_anchor.evaluate at scales 1.00-1.10 on the main sample and on the runner-up
sample, which counts an adult's work-limiting disability only below 2024's substantial gainful activity level.
Aggregates only.

Usage: fine_scale.py [MAIN_PERSONS] [RUNNER_UP_PERSONS]
  (defaults data/sample/persons.csv and data/sample_hp_sga/persons.csv)
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw_cache import BROOKINGS, ROOT, load_module  # noqa: E402

ja = load_module("ja", "scripts/fit/joint_anchor.py")
main = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/sample/persons.csv")
runner_up = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data/sample_hp_sga/persons.csv")
wi = ja.load_cells(BROOKINGS)
cols = ["person_household_id", "household_weight", "role", "age", "is_disabled", "earnings", "own_earnings",
        "is_full_time_college_student"]
rows = []
for name, path in (("main", main), ("hp_sga", runner_up)):
    per = pd.read_csv(path, usecols=cols)
    rows += ja.evaluate(name, per, wi, scales=(1.00, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.09, 1.10))
res = ja.table(rows)
res = res[res["std"]]
pd.set_option("display.width", 230)
pd.set_option("display.max_columns", 40)
print(res[ja.COLS].round(3).to_string(index=False))
