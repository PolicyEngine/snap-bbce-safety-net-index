"""Write the per-state table of results (aggregates only), from the runs on the rebuilt Brookings sample.

Usage: state_table.py MAIN_SUMMARY MAIN_POSITIVE_SHARES CPI_SUMMARY OUT_CSV

MAIN is the run with Brookings' SNAP setting and earnings x 1.07 (appendix_x107); CPI is the same at CPI-U earnings
(appendix_x100). The file opens with the method, one sentence per row in the first column, so it stands alone. A blank row and the header follow, then one row per jurisdiction. Read the table with
skiprows=len(METHOD) + 1.

The file stays ASCII so that Excel reads it correctly without a byte order mark.
"""
import csv
import math
import sys

import pandas as pd

t = pd.read_csv(sys.argv[1], index_col="state")
pos = pd.read_csv(sys.argv[2], index_col="state")
cpi = pd.read_csv(sys.argv[3], index_col="state")
assert len(t) == len(cpi) == 51 and (t.index.sort_values() == cpi.index.sort_values()).all()

METHOD = [
    "We estimate what broad-based categorical eligibility (BBCE) would add to the 2024 SNAP index in Brookings' "
    "State Safety Net Interactive.",
    "We rebuilt the interactive's sample from the 2015-2019 CPS ASEC public-use files, following its July 2026 data "
    "appendix (v3).",
    "We formed one family around each CPS family reference person, with any spouse or cohabiting partner, and "
    "merged two reference persons who cohabit into one family.",
    "We included children under 19, children 19-23 in school full time and disabled children under 24, as long as a "
    "biological parent lived in the family.",
    "We disregarded other household members.",
    "We kept families with a child under 18 in households with nobody 65 or older and no foreign-born members, and "
    "weighted each by the reference person's ASEC weight.",
    "We counted a member as disabled who received SSI in their own right.",
    "We also counted members 15 or older who said a disability kept them out of the labor force, or that illness or "
    "disability kept them from working the prior year.",
    "We also counted members 15-18 who reported difficulty on any of the CPS's six disability questions, and children "
    "under 18 who received SSI.",
    "When a parent reported receiving SSI on behalf of a child, we counted the family's youngest child under 18 as "
    "disabled.",
    "For the reference person and any spouse or partner, we summed prior-year wages, self-employment and farm income "
    "and floored each person's sum at zero.",
    "We brought those earnings to 2024 dollars with annual average CPI-U and entered them as wages.",
    "We then raised them 7%, where our federal EITC best fits Brookings' published values for the family types with "
    "no disabled member.",
    "At that scale, our federal-rules SNAP index for Wisconsin comes within 5% of Brookings' for each family type with "
    "no disabled member.",
    "For each Wisconsin family type with a disabled member, ours trails Brookings' by 15-19%, and our federal SSI "
    "alone exceeds Brookings' federal and state SSI by 10-56%.",
    "We entered no children's earnings, other income, assets, housing costs or child care costs.",
    "We placed each family in every state and computed its July 2024 SNAP with PolicyEngine-US 2.100.0 under federal "
    "rules and under the state's BBCE rules.",
    "We gave no family a utility allowance and kept full-time students in the SNAP unit.",
    "We also set TANF to zero, so that it counted neither as SNAP income nor as a route to categorical eligibility.",
    "Under PolicyEngine-US's own TANF rules, we estimate that 0.8% of the families that gain from BBCE in the 35 "
    "jurisdictions receive TANF, which would make them categorically eligible without BBCE.",
    "If we leave out their gains, the median gain across the 35 jurisdictions falls from $91.44 to $90.57, and the "
    "gains in California and Wisconsin fall by about 6%.",
    "Across the 48 states other than Alaska and Hawaii, plus DC, Brookings' SNAP index falls 27 cents for each dollar "
    "of its TANF index.",
    "Because we set TANF to zero, our federal-rules index falls 1 cent for each dollar of Brookings' TANF index.",
    "PolicyEngine-US treated every member we counted as disabled as meeting SSI's disability criteria.",
    "It then applied SSI's 2024 limit on substantial gainful activity, so members earning over $1,550 a month "
    "received no SSI.",
    "It computed federal SSI and the state supplements it models, and counted both as SNAP income.",
    "As federal rules require, PolicyEngine-US exempted families with an SSI recipient or a member 60 or older from "
    "SNAP's gross income test.",
    "We left the state minimum benefits in DC, Maryland and New Jersey, and DC's local supplement, out of both "
    "scenarios.",
    "We multiplied each July benefit by 12 and averaged it over every family, including families with no SNAP.",
    "We repeat the estimate without the 7% raise in the column bbce_adds_usd_at_cpi_u_earnings.",
    "We converted Brookings' 2024 index (file 1_noimmig v7) from thousands of dollars to dollars.",
    "The gross income limits in the second column match FNS's August 2024 BBCE chart.",
    "We took the net income tests, and the rules for households with an elderly or disabled member, from "
    "PolicyEngine-US parameters.",
    "The Internet Archive keeps FNS's August 2024 chart at https://web.archive.org/web/20240906193040/"
    "https://www.fns.usda.gov/sites/default/files/resource-files/BBCE-States-Chart-Aug-2024.pdf",
]

# Gross limits match FNS's August 2024 BBCE chart in every BBCE state. The summary carries New York's general 130%
# limit; the column shows the 150% that FNS's chart lists for households with earned income, which PolicyEngine-US
# applies to every New York family here with earnings and no dependent care or elderly or disabled member
# (gov.hhs.tanf.non_cash.income_limit.ny.earned_income; tanf_non_cash_gross_income_limit).
# The net-test flag and the limits for households with an elderly or disabled member come from
# PolicyEngine-US parameters (sources: SNAP Screener table, ERS SNAP Policy Database), which the FNS chart does not
# cover, so the net-test column carries the pe_ prefix and those notes name PolicyEngine.
# Notes on the 130% states say where a gain comes from, or why none comes, and the IL, MN and NE notes give the rules
# for households with an elderly or disabled member that move those states' gains. For 2024, PolicyEngine-US sets
# net_applies.non_hheod false in AL, GA, SC, ID, OH and OK, so households under the 130% limit skip the net test. A
# family with an SSI recipient can pass 130% gross yet fail the federal net test, since SSI gets no earned income
# deduction; under BBCE it gains. In AL, GA and SC, requires_all_for_hheod is true, so these families, whose members
# are not all elderly or disabled, fall under the general 130% rule (AL keeps the net test, under 200%, only when every
# member is elderly or disabled). In ID and OK, any elderly or disabled member puts a household under gross_hheod
# (no limit) with net_applies.hheod true, so these families keep the net test and gain nothing; MN (200%) and NE (165%)
# apply the same rule, so their families with an elderly or disabled member gain nothing either
# (out/elderly_disabled_split_appendix_x107.txt). In OH and IL, any such member puts the household under a 200% limit
# with no net test. RI also sets 200% for these households but keeps the net test, so its tier changes no gain, and IN
# keeps the net test for every household (its column reads yes); neither gets a note.
EARNED_INCOME_LIMIT = {"NY": 1.5}
NET_TEST_DROPPED = ("PolicyEngine drops SNAP's net income test for households under {}'s 130% BBCE limit, so families "
                    "with an SSI recipient gain when their net income exceeds the poverty line.")
NET_TEST_KEPT = "PolicyEngine keeps SNAP's net income test for households with an elderly or disabled member."
HHEOD_200 = "PolicyEngine applies a 200% BBCE limit to households with an elderly or disabled member."
NOTES = {
    "NY": "FNS lists New York's BBCE limit as 150% of poverty for households with earned income and 200% for "
          "households with dependent care expenses. PolicyEngine also applies 130% to other households and 200% to "
          "households with an elderly or disabled member.",
    "OH": HHEOD_200,
    "IL": HHEOD_200,
    "AL": NET_TEST_DROPPED.format("Alabama") + " It keeps the test, under a 200% limit, when every household member "
          "is elderly or disabled.",
    "GA": NET_TEST_DROPPED.format("Georgia"),
    "SC": NET_TEST_DROPPED.format("South Carolina"),
    "ID": NET_TEST_KEPT,
    "OK": NET_TEST_KEPT,
    "MN": NET_TEST_KEPT,
    "NE": NET_TEST_KEPT,
}
# Parameter values for July 2024, read from policyengine-us 2.100.0: gov.states.dc.dhs.snap.min_allotment ($30),
# gov.states.dc.tax.income.snap.temporary_local_benefit.rate (10%), gov.states.md.usda.snap.min_allotment ($40,
# age_threshold 62) and gov.states.nj.snap ($95).
STATE_BENEFITS = {
    "DC": "DC's $30 minimum benefit and its local supplement of 10% of the maximum benefit",
    "MD": "Maryland's $40 minimum benefit for households with a member 62 or older",
    "NJ": "New Jersey's $95 minimum benefit",
}
rows = []
for st, r in t.sort_index().iterrows():
    lim = EARNED_INCOME_LIMIT.get(st, r.bbce_gross_limit)
    has = math.isfinite(lim)
    note = NOTES.get(st, "")
    if st in STATE_BENEFITS:
        note = f"Including {STATE_BENEFITS[st]}, we estimate BBCE adds ${r.gain_state:,.0f} per family per year."
    rows.append({
        "state": st,
        "bbce_gross_income_limit_pct_poverty": f"{round(lim * 100)}" if has else "no BBCE",
        "pe_bbce_keeps_net_income_test": ("yes" if r.net_test_applies else "no") if has else "",
        "pe_snap_federal_rules_usd_per_family_per_year": round(r.snap_index_fed_nobbce, 1),
        "pe_snap_with_bbce_usd_per_family_per_year": round(r.snap_index_fed_bbce, 1),
        "bbce_adds_usd_per_family_per_year": round(r.gain_fed, 1),
        "brookings_2024_snap_usd_per_family_per_year": round(r.brookings_snap_index),
        "bbce_adds_pct_of_brookings_2024": round(r.gain_fed_pct_brookings, 1),
        "bbce_adds_usd_at_cpi_u_earnings": round(cpi.loc[st, "gain_fed"], 1),
        "pe_pct_families_with_snap_federal_rules": round(100 * pos.loc[st, "share_positive_fed_nobbce"], 1),
        "pe_pct_families_with_snap_with_bbce": round(100 * pos.loc[st, "share_positive_fed_bbce"], 1),
        "note": note,
    })
out = pd.DataFrame(rows)
assert len(out) == 51, len(out)
n = len(out.columns)
with open(sys.argv[4], "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    for line in METHOD:
        w.writerow([line] + [""] * (n - 1))
    w.writerow([""] * n)
    out.to_csv(f, index=False, lineterminator="\n")

raw = open(sys.argv[4], "rb").read()
raw.decode("ascii")  # raises on any non-ASCII byte
back = pd.read_csv(sys.argv[4], skiprows=len(METHOD) + 1, keep_default_na=False)
assert list(back.columns) == list(out.columns) and len(back) == 51 and back.state.is_unique

for line in METHOD:
    print(line)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 60)
print(out.to_string(index=False))
