"""Shared paths and a cache of the raw 2015-2019 ASEC tables, for the sample-variant scripts in this folder.

RAW_CACHE names a local pickle of record-level survey data (default data/raw_2015_2019.pkl, which .gitignore keeps
out of the repository). The scripts rebuild it from the Census files in ASEC_DIR when it's missing.
"""
import importlib.util
import os
import pickle
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.environ.get("RAW_CACHE", os.path.join(ROOT, "data", "raw_2015_2019.pkl"))
BROOKINGS = os.environ.get("BROOKINGS_DIR", os.path.join(ROOT, "data", "brookings"))


def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def raw_tables(ex):
    if os.path.exists(CACHE):
        with open(CACHE, "rb") as f:
            return pickle.load(f)
    raw = {y: (ex.read_fixed(y) if y in ex.FIXED else ex.read_csv_year(y)) for y in range(2015, 2020)}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "wb") as f:
        pickle.dump(raw, f)
    return raw
