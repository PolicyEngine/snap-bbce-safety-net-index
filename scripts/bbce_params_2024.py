"""Print PolicyEngine-US's BBCE parameters in effect on 2024-07-01, by state.

Usage: bbce_params_2024.py STATES   (comma-separated state codes, such as AL,AK,AZ)
"""
import sys
import pandas as pd
from policyengine_us.system import system

p = system.parameters("2024-07-01").gov.hhs.tanf.non_cash
STATES = sys.argv[1].split(",")
rows = []
for st in STATES:
    def g(node):
        try:
            return node[st]
        except Exception as e:  # noqa: BLE001
            return f"ERR:{type(e).__name__}"
    rows.append(dict(state=st, gross=g(p.income_limit.gross), gross_hheod=g(p.income_limit.gross_hheod),
                     net_non_hheod=g(p.income_limit.net_applies.non_hheod), net_hheod=g(p.income_limit.net_applies.hheod),
                     requires_all_hheod=g(p.requires_all_for_hheod), asset_limit=g(p.asset_limit),
                     fpg_start_month=g(p.income_limit.fpg_year_start_month)))
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).to_string(index=False))
print("NY earned_income", p.income_limit.ny.earned_income, "NY dependent_care", p.income_limit.ny.dependent_care)
