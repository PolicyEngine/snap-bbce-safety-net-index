"""Differential test: the hand-coded federal SNAP rules of the earnings fit (scripts/fit/federal_snap.py) against
PolicyEngine-US, run through the main runs' own code (build_base and simulate in scripts/pe_frame.py).

Hypothesis draws families with children whose members are under 60 and not disabled and whose only income is wages,
gives each a monthly rent or none, and places each in one of the 48 contiguous states or DC. Under Brookings' appendix
setting (no utility allowance, no TANF, nobody counted as a full-time college student), the two must give the same
July 2024 SNAP to the cent, under the state's BBCE rules and with BBCE off. Annual wages end in 50 cents, so no family
sits exactly on an income limit, where PolicyEngine-US's single-precision arithmetic could round either way.

RULES_EXAMPLES (default 6) sets how many batches of up to 150 families Hypothesis tries. Each batch runs two
simulations, and building each one takes several seconds, so the batches are large and few.
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "scripts"), os.path.join(ROOT, "scripts", "fit")]
import federal_snap  # noqa: E402
from pe_frame import FIPS, MONTH, build_base, simulate  # noqa: E402
from policyengine_us.system import system  # noqa: E402

DATE = "2024-07-01"
LIMITS = system.parameters.gov.hhs.tanf.non_cash.income_limit
# federal_snap.py uses the contiguous states' allotments, deductions and guidelines.
STATES = sorted(set(FIPS) - {"AK", "HI"})


def bbce_rule(state):
    """federal_snap.benefit's BBCE arguments for a family with no elderly or disabled member in state, July 2024."""
    gross = float(LIMITS.gross(DATE)[state])
    if not np.isfinite(gross):
        return {}
    # New York's limit for households with earnings. Any limit admits a household with no gross income.
    limit = float(LIMITS.ny.earned_income(DATE)) if state == "NY" else gross
    return {"bbce_limit": limit,
            "bbce_net_test": bool(LIMITS.net_applies.non_hheod(DATE)[state]),
            "bbce_current_guideline": int(LIMITS.fpg_year_start_month(DATE)[state]) <= 7}


@st.composite
def family(draw):
    kind = draw(st.sampled_from(("single", "married", "partner")))
    wage = st.one_of(st.just(0.0), st.integers(0, 89_999).map(lambda k: k + 0.5))
    adults = [("head", draw(st.integers(18, 59)), draw(wage))]
    if kind != "single":
        adults.append(("spouse" if kind == "married" else "partner", draw(st.integers(18, 59)), draw(wage)))
    kids = draw(st.lists(st.integers(0, 17), min_size=1, max_size=9))
    rent = draw(st.one_of(st.just(0.0), st.integers(1, 2_500).map(float)))  # monthly, in whole dollars
    return draw(st.sampled_from(STATES)), adults, kids, rent


def persons(fams):
    """Member rows in build_sample.py's layout for (state, [(role, age, wages)], [child ages], rent) families."""
    rows = []
    for i, (_, adults, kids, _) in enumerate(fams):
        rows += [dict(person_household_id=i, role=r, age=a, earnings=e) for r, a, e in adults]
        rows += [dict(person_household_id=i, role="other", age=a, earnings=0.0) for a in kids]
    per = pd.DataFrame(rows)
    worked = (per.earnings > 0).to_numpy()
    return per.assign(own_earnings=per.earnings, household_weight=1.0, is_disabled=0, meets_ssi_disability_criteria=0,
                      is_full_time_college_student=0, weekly_hours=np.where(worked, 40.0, 0.0),
                      weeks_worked=np.where(worked, 52.0, 0.0))


def policyengine(fams, variable, scen):
    """variable for July 2024 for each family, from simulate() with the appendix setting, in the order of fams. Each
    family's rent enters as its only housing cost."""
    base, fam_index = build_base(persons(fams))
    fips = np.array([FIPS[fams[fam_index[c]][0]] for c in base.fi])
    sim = simulate(base, fips, scen, no_sua=True, no_tanf=True)
    # Each family forms one SPM unit and one household, both identified by its family code.
    ids = np.asarray(fam_index)[np.asarray(sim.populations["spm_unit"].ids).astype(int)]
    states = np.asarray(sim.calculate("state_code_str", 2024))
    assert (np.asarray(fam_index)[np.asarray(sim.populations["household"].ids).astype(int)] == ids).all()
    assert [fams[i][0] for i in ids] == states.tolist()
    sim.set_input("housing_cost", 2024, 12 * np.array([fams[i][3] for i in ids]))
    values = pd.Series(np.asarray(sim.calculate(variable, MONTH)), index=ids)
    return values.reindex(range(len(fams))).to_numpy()


def by_hand(fams, bbce):
    return np.array([float(federal_snap.benefit([len(adults) + len(kids)], [sum(e for _, _, e in adults) / 12], 2024,
                                                rent=rent, **(bbce_rule(state) if bbce else {}))[0])
                     for state, adults, kids, rent in fams])


def mismatches(fams, scen, bbce):
    pe, hand = policyengine(fams, "snap_if_takes_up", scen), by_hand(fams, bbce)
    bad = np.flatnonzero(~np.isclose(pe, hand, rtol=0, atol=0.005))
    return hand, (len(bad), [(scen, fams[i], float(pe[i]), float(hand[i])) for i in bad[:5]])


@settings(max_examples=int(os.environ.get("RULES_EXAMPLES", 6)), deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large, HealthCheck.large_base_example])
@given(st.lists(family(), min_size=1, max_size=150))
def test_hand_coded_rules_match_policyengine(fams):
    for scen, bbce in (("fed_nobbce", False), ("fed_bbce", True)):
        _, bad = mismatches(fams, scen, bbce)
        assert not bad[0], bad


def test_federal_gross_limit_for_three():
    """The README's federal gross income limit for a family of three in July 2024: $2,694 a month."""
    _, _, _, first, additional = federal_snap.params(2024)
    assert federal_snap.income_standard(1.3, 3, first, additional, 8) == 2694
    fams = [("WI", [("head", 30, 12 * 2694 - 0.5)], [5, 9], 0.0), ("WI", [("head", 30, 12 * 2694 + 0.5)], [5, 9], 0.0)]
    assert policyengine(fams, "meets_snap_gross_income_test", "fed_nobbce").tolist() == [True, False]


def threshold_grid():
    """Families of 2 to 11 in each state, with no rent and wages a twelfth of a dollar a month below and above every
    limit that can change their SNAP: the gross and net income standards, the state's BBCE limit, the point where net
    income rounds up past the net standard, and the point where the benefit reaches zero."""
    al, add, sd, first, additional = federal_snap.params(2024)
    fams = []
    for state in STATES:
        rule = bbce_rule(state)
        for n in range(2, 12):
            fp = first + additional * (n - 1)
            if rule:
                g1, ga = first, additional
                if rule["bbce_current_guideline"]:
                    g1, ga = (federal_snap.at(federal_snap.FPG[k]["CONTIGUOUS_US"], federal_snap.dt.date(2024, 1, 1)) / 12
                              for k in ("first_person", "additional_person"))
                bbce = [rule["bbce_limit"] * (g1 + ga * (n - 1))]
            else:
                bbce = []
            s = sd[min(n, 6)]
            net_standard = federal_snap.income_standard(1.0, n, first, additional, 8)
            mx = al[min(n, 8)] + max(n - 8, 0) * add
            limits = [federal_snap.income_standard(1.3, n, first, additional, 8),
                      (net_standard + 0.5 + s) / 0.8, (mx / 0.3 + s) / 0.8, 1.3 * fp, fp] + bbce
            wages = sorted({12 * m + d for m in limits for d in (-0.5, 0.5)} | {k * 5000 + 0.5 for k in range(13)})
            for w in wages:
                fams.append((state, [("head", 35, float(w))], [6] * (n - 1), 0.0))
            # Every third wage split between two parents, for families of three or more.
            if n >= 3:
                for w in wages[::3]:
                    fams.append((state, [("head", 35, float(w) / 2), ("spouse", 34, float(w) / 2)], [6] * (n - 2), 0.0))
    return fams


def test_rules_on_threshold_grid():
    fams = threshold_grid()
    for scen, bbce in (("fed_nobbce", False), ("fed_bbce", True)):
        hand, bad = mismatches(fams, scen, bbce)
        assert not bad[0], bad
        # The grid reaches every rule: families with and without SNAP, at the minimum benefit, and above eight people.
        assert (hand > 0).sum() > 1000 and (hand == 0).sum() > 1000
    gains = by_hand(fams, True) - by_hand(fams, False)
    assert (gains > 0).sum() > 500 and (gains >= 0).all()


def rent_grid():
    """Single parents of 1 to 8 children with wages every $2,500 from $0.50 to $70,000.50 and monthly rents from $0
    to $2,400, in Mississippi (no BBCE), Wisconsin (200%, no net income test), Ohio (130%, no net income test) and
    Louisiana (200%, net income test kept)."""
    return [(state, [("head", 35, k * 2500 + 0.5)], [6] * kids, float(rent))
            for state in ("MS", "WI", "OH", "LA") for kids in range(1, 9) for k in range(29)
            for rent in (0, 300, 600, 900, 1200, 1800, 2400)]


def test_rules_with_rent():
    """The shelter deduction: rent above half of income after the other deductions, up to the cap."""
    fams = rent_grid()
    no_rent = [(state, adults, kids, 0.0) for state, adults, kids, _ in fams]
    d = dt.date(2024, 7, 1)
    _, _, sd, _, _ = federal_snap.params(2024)
    share = 1 - federal_snap.at(federal_snap.EARNED_INCOME_DEDUCTION, d)
    adjusted = np.array([max(share * adults[0][2] / 12 - sd[min(1 + len(kids), 6)], 0) for _, adults, kids, _ in fams])
    rent = np.array([r for *_, r in fams])
    # The grid reaches the cap: some families' rent exceeds half their adjusted income by more than it.
    assert ((rent - federal_snap.SHELTER_INCOME_SHARE * adjusted) > federal_snap.at(federal_snap.SHELTER_CAP, d)).sum() > 500
    for scen, bbce in (("fed_nobbce", False), ("fed_bbce", True)):
        hand, bad = mismatches(fams, scen, bbce)
        assert not bad[0], bad
        # Rent never lowers SNAP, and it raises SNAP for many families.
        gain = hand - by_hand(no_rent, bbce)
        assert (gain > 0).sum() > 500 and (gain >= 0).all()
