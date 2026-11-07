"""Federal SNAP rules written out by hand, for households whose only income is earnings and whose members are neither
elderly nor disabled, in the 48 contiguous states and DC.

joint_anchor.py, rent_test.py and variant_gain.py compute SNAP with these rules instead of running PolicyEngine-US, so
they can try many earnings scales, years and rents against Brookings' published values in seconds. The parameters come
from PolicyEngine-US 2.100.0's YAML files, and the rules follow its SNAP variables:

  income standards  130% (gross) and 100% (net) of the monthly poverty guideline SNAP adopted the previous October 1,
                    rounded up to the next dollar; above eight people, the eight-person standard plus a rounded-up
                    increment for each additional person (snap_monthly_income_standard)
  net income        earnings less the 20% earned income deduction, the standard deduction and, with rent, the excess
                    shelter deduction, rounded to the nearest dollar (snap_net_income). The shelter deduction is rent
                    above half of income after the other deductions, up to the cap for households with no elderly or
                    disabled member (snap_excess_shelter_expense_deduction)
  benefit           the maximum allotment less 30% of net income, rounded up to the next dollar
                    (snap_expected_contribution), and at least the minimum benefit, 8% of the one-person maximum
                    rounded to the dollar, for households of one or two (snap_min_allotment)
  BBCE              with bbce_limit, gross income at or below that multiple of the monthly guideline also makes a
                    household eligible (is_tanf_non_cash_eligible). The guideline is the one SNAP adopted the previous
                    October, or with bbce_current_guideline the current calendar year's (tanf_non_cash_fpg), and
                    bbce_net_test keeps the federal net income test for these households

tests/test_rules.py checks that these rules give the same July 2024 SNAP as PolicyEngine-US, to the cent, for families
with children placed in each of the 48 contiguous states and DC, with and without BBCE and with and without rent.
"""
import datetime as dt
import os

import numpy as np
import policyengine_us
import yaml

PE = os.path.join(os.path.dirname(policyengine_us.__file__), "parameters")
SNAP = os.path.join(PE, "gov/usda/snap")


def _load(path):
    with open(path) as f:
        return yaml.safe_load(f)


MAX_ALLOTMENT = _load(os.path.join(SNAP, "max_allotment.yaml"))
STANDARD_DEDUCTION = _load(os.path.join(SNAP, "income/deductions/standard.yaml"))
SHELTER_CAP = _load(os.path.join(SNAP, "income/deductions/excess_shelter_expense/cap.yaml"))["CONTIGUOUS_US"]
FPG = _load(os.path.join(PE, "gov/hhs/fpg.yaml"))
MIN_ALLOTMENT = {k: _load(os.path.join(SNAP, "min_allotment", f"{k}.yaml"))
                 for k in ("rate", "maximum_household_size", "relevant_max_allotment_household_size", "published_adjustment")}
# Rates PolicyEngine-US has held constant since 2005; the fit's years start in 2016.
GROSS_RATE = _load(os.path.join(SNAP, "income/limit/gross.yaml"))["values"]
NET_RATE = _load(os.path.join(SNAP, "income/limit/net.yaml"))["values"]
INCREMENT_SIZE = _load(os.path.join(SNAP, "income/limit/increment_household_size_threshold.yaml"))["values"]
EARNED_INCOME_DEDUCTION = _load(os.path.join(SNAP, "income/deductions/earned_income.yaml"))["values"]
CONTRIBUTION_RATE = _load(os.path.join(SNAP, "expected_contribution.yaml"))["values"]
# Half of income after the other deductions (7 USC 2014(e)(6)(A)). PolicyEngine-US's parameter for it starts in 2018,
# after two of the fit's years, so the share is written here.
SHELTER_INCOME_SHARE = 0.5


def at(node, date):
    """Value of a dated YAML parameter node on date."""
    return next(v for k, v in sorted(node.items(), key=lambda kv: kv[0], reverse=True) if k <= date)


def params(y):
    """Maximum allotments by size (1-8), the allotment for each person above 8, standard deductions by size (1-6), and
    the monthly poverty guideline for the first and each additional person, for July of year y."""
    d = dt.date(y, 7, 1)
    al = {k: at(MAX_ALLOTMENT["main"]["CONTIGUOUS_US"][k], d) for k in range(1, 9)}
    add = at(MAX_ALLOTMENT["additional"]["CONTIGUOUS_US"], d)
    sd = {k: at(STANDARD_DEDUCTION["CONTIGUOUS_US"][k], d) for k in range(1, 7)}
    d2 = dt.date(y - 1, 10, 1)
    return (al, add, sd, at(FPG["first_person"]["CONTIGUOUS_US"], d2) / 12,
            at(FPG["additional_person"]["CONTIGUOUS_US"], d2) / 12)


def income_standard(rate, n, first, additional, threshold):
    """Monthly income standard at rate times the guideline, for households of n people."""
    above = np.maximum(n - threshold, 0)
    base = np.ceil(np.round(rate * (first + additional * (np.minimum(n, threshold) - 1)), 2))
    return base + above * np.ceil(np.round(rate * additional, 2))


def benefit(n, em, y, standard_deduction=True, max_for_all=False, rent=0.0, bbce_limit=None, bbce_net_test=False,
            bbce_current_guideline=False):
    """Monthly SNAP in July of year y for households of n people with monthly earnings em and monthly rent.

    max_for_all gives every eligible household the maximum allotment, as the emergency allotments of 2020 did."""
    al, add, sd, first, additional = params(y)
    d = dt.date(y, 7, 1)
    n = np.asarray(n, dtype=int)
    em = np.asarray(em, dtype=float)
    mx = np.array([al[min(int(x), 8)] for x in n]) + np.maximum(n - 8, 0) * add
    sdv = np.array([sd[min(int(x), 6)] for x in n]) * (1 if standard_deduction else 0)
    # Income after the earned income and standard deductions, before the shelter deduction.
    adjusted = np.maximum((1 - at(EARNED_INCOME_DEDUCTION, d)) * em - sdv, 0)
    shelter = np.minimum(np.maximum(rent - SHELTER_INCOME_SHARE * adjusted, 0), at(SHELTER_CAP, d))
    net = np.floor(np.round(np.maximum(adjusted - shelter, 0), 2) + 0.5)
    threshold = at(INCREMENT_SIZE, d)
    eligible = ((em <= income_standard(at(GROSS_RATE, d), n, first, additional, threshold))
                & (net <= income_standard(at(NET_RATE, d), n, first, additional, threshold)))
    if bbce_limit is not None:
        g1, ga = first, additional
        if bbce_current_guideline:
            g1, ga = (at(FPG[k]["CONTIGUOUS_US"], dt.date(y, 1, 1)) / 12 for k in ("first_person", "additional_person"))
        bbce = em <= bbce_limit * (g1 + ga * (n - 1))
        if bbce_net_test:
            bbce = bbce & (net <= income_standard(at(NET_RATE, d), n, first, additional, threshold))
        eligible = eligible | bbce
    if max_for_all:
        return np.where(eligible, mx, 0.0)
    mn = {k: at(v["CONTIGUOUS_US"] if k == "published_adjustment" else v["values"], d) for k, v in MIN_ALLOTMENT.items()}
    minimum = np.where(n <= mn["maximum_household_size"],
                       np.round(mn["rate"] * al[mn["relevant_max_allotment_household_size"]]) + mn["published_adjustment"], 0.0)
    contribution = np.ceil(np.round(at(CONTRIBUTION_RATE, d) * net, 2))
    return np.where(eligible, np.maximum(mx - contribution, minimum), 0.0)
