"""Download the 2015-2019 CPS ASEC public-use files from the Census Bureau and check their SHA-256 hashes.

The 2015-2018 survey years come as fixed-width data with a data dictionary; 2019 comes as a CSV bundle. Files land in
ASEC_DIR (default data/asec), about 300 MB in all. A file already present with the right hash is kept.

Usage: download_asec.py
"""
import hashlib
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.environ.get("ASEC_DIR", os.path.join(ROOT, "data", "asec"))
BASE = "https://www2.census.gov/programs-surveys/cps/datasets/{year}/march/{name}"
FILES = [
    (2015, "asec2015_pubuse.dat.gz", "a770f968db6b294cde4ad4df07d8f2a4a19e62d637e09a8773186f73d21b322d"),
    (2015, "asec2015early_pubuse.dd.txt", "131535ff2206f1cbe6b7f1fe3e64c7f47051c1ed2e3db970dc3790905fd9a8fe"),
    (2016, "asec2016_pubuse_v3.dat.gz", "25cf5a6fd39c8eb4a10cf95d2adf6957775cf8c861fb01ffddf6478946cfa884"),
    (2016, "asec2016_pubuse.dd.txt", "0d4d8e4711b8157aee436cd068ccf0820a40b2abe583a38c21852d8f3767b3df"),
    (2017, "asec2017_pubuse.dat.gz", "9bd27168a8da621431a8e2b55556d0d8fc4c921167ed65f56683fbe07b258218"),
    (2017, "08ASEC2017_Data_Dict_Full.txt", "0e9ff2ee6bf50acbbe182d861f94d372afdd3c5d6c81ae8c03873cf7855c1ccc"),
    (2018, "asec2018_pubuse.dat.gz", "dbf453e91c32935651cb6bf71e45c947af2b8875f4af75efe218ad1943d1496c"),
    (2018, "08ASEC2018_Data_Dict_Full.txt", "eb6ad973a5a1da618d2e7d3938bcafc83ab95e44d0d791318360c1d612258838"),
    (2019, "asecpub19csv.zip", "88d8688ac5e5a1d4d4bd9daf72946d8fd34edda9360b3bbfde602d6ca55fb604"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, path, digest):
    if os.path.exists(path) and sha256(path) == digest:
        print(f"have {os.path.basename(path)}")
        return
    print(f"downloading {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research download)"})
    tmp = path + ".part"
    with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    got = sha256(tmp)
    if got != digest:
        os.remove(tmp)
        sys.exit(f"{os.path.basename(path)}: SHA-256 {got}, expected {digest}")
    os.replace(tmp, path)


if __name__ == "__main__":
    os.makedirs(DEST, exist_ok=True)
    for year, name, digest in FILES:
        fetch(BASE.format(year=year, name=name), os.path.join(DEST, name), digest)
    print(f"ASEC files in {DEST}")
