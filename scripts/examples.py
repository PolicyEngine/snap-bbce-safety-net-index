"""SNAP for example households in July 2024, under PolicyEngine-US current law and with BBCE turned off."""
import numpy as np
from policyengine_us import Simulation

M = "2024-07"


def fam(state, earnings, adults=1, kids=(5, 9)):
    people = {"p1": {"age": {2024: 34}, "employment_income": {2024: earnings if adults == 1 else earnings / 2}}}
    if adults == 2:
        people["p2"] = {"age": {2024: 34}, "employment_income": {2024: earnings / 2}}
    for i, a in enumerate(kids):
        people[f"c{i}"] = {"age": {2024: a}}
    members = list(people)
    sit = {"people": people,
           "spm_units": {"s": {"members": members}},
           "families": {"f": {"members": members}},
           "tax_units": {"t": {"members": members}},
           "households": {"h": {"members": members, "state_code": {2024: state}}}}
    if adults == 2:
        sit["marital_units"] = {"m": {"members": ["p1", "p2"]}, **{f"mc{i}": {"members": [f"c{i}"]} for i in range(len(kids))}}
    return sit


def run(state, earnings, adults=1, kids=(5, 9)):
    out = {}
    for scen in ("bbce", "nobbce"):
        sim = Simulation(situation=fam(state, earnings, adults, kids))
        if scen == "nobbce":
            sim.set_input("is_tanf_non_cash_eligible", M, np.array([False]))
        out[scen] = {v: float(sim.calculate(v, M)[0]) for v in
                     ("snap_if_takes_up", "snap_gross_income", "snap_net_income", "is_snap_eligible",
                      "meets_snap_gross_income_test", "meets_snap_net_income_test")}
    return out


for label, args in [("single parent of 2, $35,000, CA", ("CA", 35000)),
                    ("single parent of 2, $35,000, TX", ("TX", 35000)),
                    ("single parent of 2, $35,000, MO (no BBCE)", ("MO", 35000)),
                    ("married couple + 2, $39,000, MO", ("MO", 39000, 2)),
                    ("married couple + 2, $39,001, MO", ("MO", 39001, 2)),
                    ("married couple + 2, $39,001, TX", ("TX", 39001, 2)),
                    ("married couple + 2, $45,000, TX", ("TX", 45000, 2))]:
    r = run(*args)
    b, n = r["bbce"], r["nobbce"]
    print(f"{label}: SNAP with BBCE ${b['snap_if_takes_up']:.0f}/mo, federal rules ${n['snap_if_takes_up']:.0f}/mo; "
          f"gross ${n['snap_gross_income']:.0f}, net ${n['snap_net_income']:.0f}; fed gross test {bool(n['meets_snap_gross_income_test'])}, "
          f"net test {bool(n['meets_snap_net_income_test'])}")
