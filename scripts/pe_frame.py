"""PolicyEngine-US input frame shared by snap_by_state.py and replicate_2024.py: one row per sample member.

Entities. Each family forms one household, SPM unit and family. The head files taxes with the
spouse and the children, and a cohabiting partner files alone. Marital units pair the head
with the spouse; the partner and each child form their own.

Tax roles. tax_unit_role_input names every member's role: the head and a cohabiting partner
head their own tax units, the spouse is the head's spouse, and children are dependents. With
every role supplied, PolicyEngine-US uses these roles instead of inferring head and spouse
from age order, which would otherwise make an adult child the spouse of a single parent.

Earnings. child_earnings=False enters children's earnings as zero (the main design), and
True enters every member's own earnings (the variant). Hours and weeks worked always enter as
reported for every member, since SNAP's student work exception reads them.

Scenarios. simulate() builds the PolicyEngine-US simulation that snap_by_state.py runs for each state and scenario, so
tests/test_rules.py checks the same code path.
"""
import numpy as np
import pandas as pd
from policyengine_core.data import Dataset
from policyengine_core.reforms import Reform
from policyengine_us import Simulation

FIPS = dict(AL=1, AK=2, AZ=4, AR=5, CA=6, CO=8, CT=9, DE=10, DC=11, FL=12, GA=13, HI=15, ID=16, IL=17,
            IN=18, IA=19, KS=20, KY=21, LA=22, ME=23, MD=24, MA=25, MI=26, MN=27, MS=28, MO=29, MT=30,
            NE=31, NV=32, NH=33, NJ=34, NM=35, NY=36, NC=37, ND=38, OH=39, OK=40, OR=41, PA=42, RI=44,
            SC=45, SD=46, TN=47, TX=48, UT=49, VT=50, VA=51, WA=53, WV=54, WI=55, WY=56)
MONTH = "2024-07"
# Federal minimum allotments in DC, MD and NJ, in place of their state minimums.
FED_RULES = Reform.from_dict({
    "gov.states.dc.dhs.snap.min_allotment.in_effect": {"2024-01-01.2024-12-31": False},
    "gov.states.md.usda.snap.min_allotment.in_effect": {"2024-01-01.2024-12-31": False},
    "gov.states.nj.snap.in_effect": {"2024-01-01.2024-12-31": False},
}, country_id="us")
ORDER = {"head": 0, "spouse": 1, "partner": 2, "other": 3}
TAX_ROLE = {"head": "HEAD", "spouse": "SPOUSE", "partner": "HEAD", "other": "DEPENDENT"}


def build_base(per, ids=None, child_earnings=False):
    """Return (base, fam_index): member rows in a fixed order and the family ids they map to."""
    ps = per if ids is None else per[per.person_household_id.isin(ids)]
    ps = ps.copy()
    ps["o"] = ps.role.map(ORDER)
    ps = ps.sort_values(["person_household_id", "o", "age"], ascending=[True, True, False]).reset_index(drop=True)
    fam_codes, fam_index = pd.factorize(ps.person_household_id, sort=True)
    k = ps.groupby(fam_codes).cumcount().to_numpy()
    # IDs stay unique across families (fi * 100 + k, k < 100).
    assert k.max() < 98
    mu_k = np.where(ps.role.isin(["head", "spouse"]), 0, k + 1)
    tu_k = np.where(ps.role == "partner", 1, 0)
    earnings = ps.own_earnings if child_earnings else ps.earnings
    base = pd.DataFrame({
        "fi": fam_codes,
        "mu": fam_codes * 100 + mu_k,
        "tu": fam_codes * 100 + tu_k,
        "role": ps.role.to_numpy(),
        "age": ps.age.astype(float).to_numpy(),
        "is_disabled": (ps.is_disabled == 1).to_numpy(),
        "meets_ssi_disability_criteria": (ps.meets_ssi_disability_criteria == 1).to_numpy(),
        "is_full_time_college_student": (ps.is_full_time_college_student == 1).to_numpy(),
        "is_household_head": (ps.role == "head").to_numpy(),
        "tax_unit_role_input": ps.role.map(TAX_ROLE).to_numpy(),
        "employment_income": earnings.astype(float).to_numpy(),
        "weekly_hours_worked_before_lsr": ps.weekly_hours.astype(float).to_numpy(),
        "weeks_worked": ps.weeks_worked.astype(float).to_numpy(),
    })
    tu_roles = base.groupby("tu").tax_unit_role_input
    assert (tu_roles.apply(lambda r: (r == "HEAD").sum()) == 1).all(), "each tax unit needs one head"
    assert (tu_roles.apply(lambda r: (r == "SPOUSE").sum()) <= 1).all(), "at most one spouse per tax unit"
    return base, fam_index


def frame(base, fips):
    """Flat PolicyEngine-core dataset frame for one state, period 2024."""
    n = len(base)
    return pd.DataFrame({
        "person_id__2024": np.arange(n),
        "person_household_id__2024": base.fi,
        "person_spm_unit_id__2024": base.fi,
        "person_family_id__2024": base.fi,
        "person_tax_unit_id__2024": base.tu,
        "person_marital_unit_id__2024": base.mu,
        "age__2024": base.age,
        "is_disabled__2024": base.is_disabled,
        "meets_ssi_disability_criteria__2024": base.meets_ssi_disability_criteria,
        "is_full_time_college_student__2024": base.is_full_time_college_student,
        "is_household_head__2024": base.is_household_head,
        "tax_unit_role_input__2024": base.tax_unit_role_input,
        "employment_income__2024": base.employment_income,
        "weekly_hours_worked_before_lsr__2024": base.weekly_hours_worked_before_lsr,
        "weeks_worked__2024": base.weeks_worked,
        "state_fips__2024": np.full(n, fips),
    })


def simulate(base, fips, scen, no_sua=False, no_tanf=False, no_standard=False):
    """PolicyEngine-US simulation of base's families placed in the state with FIPS code fips (one code, or one per
    member), under scenario scen: fed_bbce, fed_nobbce, state_bbce or state_nobbce (see snap_by_state.py)."""
    n_f = int(base.fi.max()) + 1
    assert base.fi.nunique() == n_f, "family codes must run from 0 to the number of families"
    reform = FED_RULES if scen.startswith("fed_") else None
    sim = Simulation(dataset=Dataset.from_dataframe(frame(base, fips), 2024), reform=reform)
    if scen.startswith("fed_"):
        sim.set_input("dc_snap_temporary_local_benefit", MONTH, np.zeros(n_f))
    if scen.endswith("_nobbce"):
        sim.set_input("is_tanf_non_cash_eligible", MONTH, np.zeros(n_f, dtype=bool))
    if no_sua:
        sim.set_input("snap_utility_allowance", MONTH, np.zeros(n_f))
    if no_tanf:
        # tanf has a yearly definition period in PolicyEngine-US 2.100.0.
        sim.set_input("tanf", 2024, np.zeros(n_f))
    if no_standard:
        sim.set_input("snap_standard_deduction", MONTH, np.zeros(n_f))
    return sim
