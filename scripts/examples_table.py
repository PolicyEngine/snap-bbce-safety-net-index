"""SNAP for a single parent of two at five earnings levels, with rent, self-employment and smaller households (July 2024).

Output: out/examples_table.txt
"""
import numpy as np
from policyengine_us import Simulation

M = "2024-07"


def sim_for(state, earnings, kids=(5, 9), adults=1, rent=0.0, bbce=True, se=False):
    inc = "self_employment_income" if se else "employment_income"
    people = {"p1": {"age": {2024: 34}, inc: {2024: earnings / adults}, "rent": {2024: rent}}}
    if adults == 2:
        people["p2"] = {"age": {2024: 34}, inc: {2024: earnings / 2}}
    for i, a in enumerate(kids):
        people[f"c{i}"] = {"age": {2024: a}}
    mem = list(people)
    sit = {"people": people, "spm_units": {"s": {"members": mem}}, "families": {"f": {"members": mem}},
           "tax_units": {"t": {"members": mem}}, "households": {"h": {"members": mem, "state_code": {2024: state}}}}
    if adults == 2:
        sit["marital_units"] = {"m": {"members": ["p1", "p2"]}, **{f"mc{i}": {"members": [f"c{i}"]} for i in range(len(kids))}}
    s = Simulation(situation=sit)
    if not bbce:
        s.set_input("is_tanf_non_cash_eligible", M, np.array([False]))
    return float(s.calculate("snap_if_takes_up", M)[0])


print("single parent of two, no rent: earnings | federal rules (TX) | CA | TX | OH | AR")
for e in (32500, 35000, 37500, 40000, 42500):
    print(e, round(sim_for("TX", e, bbce=False)), round(sim_for("CA", e)), round(sim_for("TX", e)),
          round(sim_for("OH", e)), round(sim_for("AR", e)))
print("with $1,000/month rent at $32,500: CA", round(sim_for("CA", 32500, rent=12000)),
      "TX", round(sim_for("TX", 32500, rent=12000)), "| federal rules CA", round(sim_for("CA", 32500, rent=12000, bbce=False)),
      "TX", round(sim_for("TX", 32500, rent=12000, bbce=False)))
print("$32,500 of self-employment income instead of wages, no rent: CA", round(sim_for("CA", 32500, se=True)),
      "TX", round(sim_for("TX", 32500, se=True)), "| federal rules CA", round(sim_for("CA", 32500, se=True, bbce=False)),
      "TX", round(sim_for("TX", 32500, se=True, bbce=False)))
print("parent + 1 child at $38,000 (193% of the 2023 guideline): CA", round(sim_for("CA", 38000, kids=(5,))),
      "federal rules", round(sim_for("CA", 38000, kids=(5,), bbce=False)))
print("parent + 1 child at $36,000: NJ", round(sim_for("NJ", 36000, kids=(5,))), "federal rules NJ",
      round(sim_for("NJ", 36000, kids=(5,), bbce=False)))
