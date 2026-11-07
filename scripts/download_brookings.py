"""Download the State Safety Net Database v3 (July 2026) from Brookings and extract the files these scripts read.

Brookings publishes the database with its State Safety Net Interactive at
https://www.brookings.edu/articles/state-safety-net-interactive-2026/. Cite it as: Curtis Broker, Janina, Gabriela
Goodman, Lucie Schmidt, Lara Shore-Sheppard, Sasha Snyder, and Tara Watson, 2026. State Safety Net Database version v3
[dataset]. Brookings Institution, Washington, D.C.

Files land in BROOKINGS_DIR (default data/brookings). The script checks the archive's SHA-256 hash, so a later
release fails loudly rather than changing the results.

Usage: download_brookings.py
"""
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download_asec import ROOT, fetch  # noqa: E402

DEST = os.environ.get("BROOKINGS_DIR", os.path.join(ROOT, "data", "brookings"))
URL = "https://www.brookings.edu/wp-content/uploads/2026/07/sna_styr_v3_0da9f2.zip"
DIGEST = "d5aa7f00101449905c6125f5939fe07d1b1f99062318249172ee76898b1350e1"
MEMBERS = ["1_noimmig v7.dta", "2_noimmig v7.dta", "13_noimmig v7.dta", "13b_noimmig v7.dta",
           "safety_net_codebook.xlsx", "Data Appendix Summer26 release_final.pdf"]

if __name__ == "__main__":
    os.makedirs(DEST, exist_ok=True)
    archive = os.path.join(DEST, os.path.basename(URL))
    fetch(URL, archive, DIGEST)
    with zipfile.ZipFile(archive) as z:
        for name in MEMBERS:
            with z.open(f"sna_styr_v3/{name}") as src, open(os.path.join(DEST, name), "wb") as dst:
                shutil.copyfileobj(src, dst)
    print(f"Brookings files in {DEST}")
