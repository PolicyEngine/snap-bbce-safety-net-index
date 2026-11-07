"""Compare PE-US BBCE gross and asset limits on 2024-07-01 with FNS's August 2024 BBCE states chart.

Source: https://www.fns.usda.gov/sites/default/files/resource-files/BBCE-States-Chart-Aug-2024.pdf
(archived copy in sources/; values transcribed to sources/fns_bbce_states_chart_aug2024.csv).
"""
import math
import os
import pandas as pd
from policyengine_us.system import system

p = system.parameters("2024-07-01").gov.hhs.tanf.non_cash
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fns = pd.read_csv(os.path.join(ROOT, "sources", "fns_bbce_states_chart_aug2024.csv")).set_index("state")
STATES = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
bad = []
for st in STATES:
    g = float(p.income_limit.gross[st])
    pe_lim = round(100 * float(p.income_limit.ny.earned_income)) if st == "NY" else (round(100 * g) if math.isfinite(g) else None)
    pe_asset = float(p.asset_limit[st])
    pe_asset = "none" if pe_asset == math.inf else (None if not math.isfinite(pe_asset) else str(int(pe_asset)))
    if st in fns.index:
        f = fns.loc[st]
        if pe_lim != f.gross_limit_pct or (pe_asset != str(f.asset_limit)):
            bad.append((st, pe_lim, pe_asset, f.gross_limit_pct, f.asset_limit))
    elif pe_lim is not None:
        bad.append((st, pe_lim, pe_asset, "not in FNS chart", ""))
print(f"BBCE jurisdictions in PE (of 50 states and DC): {sum(math.isfinite(float(p.income_limit.gross[s])) for s in STATES)}; "
      f"in FNS chart (incl. GU, VI): {len(fns)}")
print("NY dependent care limit in PE:", float(p.income_limit.ny.dependent_care))
print("mismatches (state, PE limit, PE asset, FNS limit, FNS asset):", bad if bad else "none")
