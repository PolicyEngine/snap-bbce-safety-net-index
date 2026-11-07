"""Count the jurisdictions using BBCE each July, and those with a BBCE income limit above 130% of poverty, from ERS's
SNAP Policy Database (sources/ers_snap_policy_database_july.csv, written by download_ers.py).

Usage: ers_bbce_counts.py [CSV]
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "sources", "ers_snap_policy_database_july.csv")
d = pd.read_csv(path)
uses = d.bbce == 1
counts = pd.DataFrame({
    "bbce": uses.groupby(d.year).sum(),
    "bbce_limit_above_130": (uses & (d.bbce_inclmt > 130)).groupby(d.year).sum(),
})
print("July of each year, of 50 states and DC:")
print(counts.to_string())
