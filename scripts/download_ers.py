"""Download ERS's SNAP Policy Database and write its July rows for the BBCE variables to sources/.

The database (https://www.ers.usda.gov/data-products/snap-policy-data-sets) records each state's SNAP policies by
month from January 1996 to December 2020. This keeps July of each year, the month Brookings' appendix uses for SNAP
rules, and the columns bbce (1 if the state uses BBCE), bbce_inclmt (its gross income limit, % of poverty),
bbce_asset and bbce_child. ERS codes -9 where a column doesn't apply.

Usage: download_ers.py [--xlsx PATH] [OUT_CSV]
  --xlsx reads a workbook already on disk instead of downloading it. OUT_CSV defaults to
  sources/ers_snap_policy_database_july.csv.
"""
import argparse
import os
import tempfile
import urllib.request
import zipfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://www.ers.usda.gov/media/6472/snap-policy-database.xlsx"


def download(path):
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (research download)"})
    with urllib.request.urlopen(req) as r, open(path, "wb") as f:
        size = int(r.headers.get("Content-Length", 0))
        while chunk := r.read(1 << 20):
            f.write(chunk)
    if (size and os.path.getsize(path) != size) or not zipfile.is_zipfile(path):
        raise SystemExit(f"incomplete download: {os.path.getsize(path)} of {size} bytes; run it again")


def july_rows(xlsx):
    db = pd.read_excel(xlsx, sheet_name="SNAP Policy Database")
    july = db[db.yearmonth % 100 == 7].copy()
    july["year"] = july.yearmonth // 100
    cols = ["bbce", "bbce_inclmt", "bbce_asset", "bbce_child"]
    july = july[["state_pc", "year"] + cols].astype({c: float for c in cols})
    assert july.state_pc.nunique() == 51, july.state_pc.nunique()
    return july


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=os.path.join(ROOT, "sources", "ers_snap_policy_database_july.csv"))
    ap.add_argument("--xlsx")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        xlsx = a.xlsx or os.path.join(tmp, "snap-policy-database.xlsx")
        if not a.xlsx:
            download(xlsx)
        july = july_rows(xlsx)
    july.to_csv(a.out, index=False)
    print(f"wrote {a.out}: {len(july)} rows, {july.year.min()}-{july.year.max()}")
