"""Compute the programs in Brookings' 2024 State Safety Net Interactive file with PolicyEngine-US, on the rebuilt sample.

Every family in the rebuilt 2015-2019 ASEC sample (build_sample.py) is placed in each state, and
PolicyEngine-US 2.100.0 computes, for 2024, under the setting Brookings' data appendix describes:
  snap      July 2024 SNAP x 12 under federal rules: is_tanf_non_cash_eligible forced False (no BBCE), the DC, Maryland
            and New Jersey minimum benefits and DC's temporary local benefit turned off, no utility allowance, and
            nobody counted as a full-time college student (Brookings' units keep full-time students 19-23).
            PolicyEngine-US's own TANF counts as SNAP income, as Brookings' TANF does in its SNAP.
  tanf      PolicyEngine-US's 2024 TANF. The Brookings team takes TANF rules from the Welfare Rules Database instead.
  ssi       2024 federal SSI.
  ssp       2024 state SSI supplements: the variables SNAP's unearned-income list names for the state, except Colorado's
            Old Age Pension (co_oap).
  eitc, ctc, refundable_ctc, non_refundable_ctc, income_tax_capped_non_refundable_credits,
  income_tax_before_credits, income_tax_refundable_credits, state_eitc, state_refundable_credits,
  state_non_refundable_credits
            2024 tax-unit amounts, summed over the family's tax units. pe_frame.py files the head with the spouse and
            the children, and a cohabiting partner alone.
  medicaid_adult, medicaid_child, medicaid_or_chip_child
            each family's share of adults (head, spouse, partner) and of children (the unit's children) whom
            is_medicaid_eligible (or is_chip_eligible) marks eligible for 2024.

Dollar amounts are per family per year. index_ST.csv holds weighted means over all families ("all") and over each of
Brookings' six cells (family type x any disabled member); medicaid columns are weighted means of the family shares.
families_ST.csv.gz holds per-family results, which .gitignore keeps out of the repository.

Usage: replicate_2024.py PERSONS OUTDIR STATE[,STATE...] [--earnings-scale X] [--limit N]
  --earnings-scale X  multiply every member's earnings by X
  --limit N           simulate only the first N families (smoke tests)
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import policyengine_us
import yaml
from policyengine_core.data import Dataset
from policyengine_us import Simulation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe_frame import FED_RULES, FIPS, MONTH, build_base, frame as pe_frame  # noqa: E402

YEAR = 2024
TAX_VARS = ["eitc", "ctc", "refundable_ctc", "non_refundable_ctc", "income_tax_capped_non_refundable_credits",
            "income_tax_before_credits", "income_tax_refundable_credits", "state_eitc", "state_refundable_credits",
            "state_non_refundable_credits"]
CELL_TYPES = {"married": "Ref person + spouse", "single": "Single", "partner": "Partner"}

# State supplements: the entries between general_assistance and pension_income in SNAP's unearned-income list.
_src = yaml.safe_load(open(os.path.join(os.path.dirname(policyengine_us.__file__),
                                        "parameters/gov/usda/snap/income/sources/unearned.yaml")))["values"]
_unearned = _src[max(_src)]
SSP_VARS = [v for v in _unearned[_unearned.index("general_assistance") + 1:_unearned.index("pension_income")]
            if v != "co_oap"]

persons_path, outdir, states = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
opts = sys.argv[4:]
SCALE = float(opts[opts.index("--earnings-scale") + 1]) if "--earnings-scale" in opts else 1.0
LIMIT = int(opts[opts.index("--limit") + 1]) if "--limit" in opts else None
os.makedirs(outdir, exist_ok=True)
log = lambda *a: print(*a, file=sys.stderr, flush=True)

per = pd.read_csv(persons_path)
fam = per.groupby("person_household_id").agg(w=("household_weight", "first"), dis=("is_disabled", "max"))
ids = fam.index if LIMIT is None else fam.index[:LIMIT]
base, fam_index = build_base(per, ids)
base["is_full_time_college_student"] = False
base["employment_income"] = base.employment_income * SCALE
n_f = len(fam_index)
w = fam.loc[fam_index, "w"].to_numpy()
W = w.sum()
roles = per[per.person_household_id.isin(fam_index)].groupby("person_household_id").role.apply(set).loc[fam_index]
ftype = np.where(roles.apply(lambda s: "spouse" in s), "married",
                 np.where(roles.apply(lambda s: "partner" in s), "partner", "single"))
anydis = (fam.loc[fam_index, "dis"].to_numpy() == 1).astype(int)
fi = base.fi.to_numpy()
adult = base.role.isin(["head", "spouse", "partner"]).to_numpy()
# Group-entity amounts reach families through one member each: the family head for the SPM unit (one per family) and
# each tax unit's head (the head, and a cohabiting partner who files alone). PolicyEngine-core renumbers group
# entities, so the script never maps them by id.
is_head = (base.role == "head").to_numpy()
is_tu_head = (base.tax_unit_role_input == "HEAD").to_numpy()
log(f"families {n_f} ({w.sum() / fam.w.sum():.3f} of weight); members {len(base)}; earnings x {SCALE}")


def fam_sum(a):
    return np.bincount(fi, weights=np.asarray(a, dtype=float), minlength=n_f)


n_adults, n_children = fam_sum(adult), fam_sum(~adult)
assert (n_adults >= 1).all() and (n_children >= 1).all()


def run(st):
    t = time.time()
    sim = Simulation(dataset=Dataset.from_dataframe(pe_frame(base, FIPS[st]), YEAR), reform=FED_RULES)
    sim.set_input("dc_snap_temporary_local_benefit", MONTH, np.zeros(n_f))
    sim.set_input("is_tanf_non_cash_eligible", MONTH, np.zeros(n_f, dtype=bool))
    sim.set_input("snap_utility_allowance", MONTH, np.zeros(n_f))
    sc = np.asarray(sim.calculate("state_code_str", YEAR))
    assert len(sc) == n_f and (sc == st).all(), (st, sc[:3])
    def group(values, entity, holder):
        return fam_sum(sim.map_result(np.asarray(values, dtype=float), entity, "person") * holder)

    out = {
        "snap": 12 * group(sim.calculate("snap_if_takes_up", MONTH), "spm_unit", is_head),
        "tanf": group(sim.calculate("tanf", YEAR), "spm_unit", is_head),
        "ssi": fam_sum(sim.calculate_add("ssi", YEAR)),
    }
    ssp = np.zeros(n_f)
    for v in (v for v in SSP_VARS if v.startswith(st.lower() + "_")):
        val = np.asarray(sim.calculate_add(v, YEAR), dtype=float)
        entity = sim.tax_benefit_system.variables[v].entity.key
        assert entity in ("person", "spm_unit"), (v, entity)
        ssp += fam_sum(val) if entity == "person" else group(val, "spm_unit", is_head)
    out["ssp"] = ssp
    for v in TAX_VARS:
        out[v] = group(sim.calculate(v, YEAR), "tax_unit", is_tu_head)
    med = np.asarray(sim.calculate("is_medicaid_eligible", YEAR), dtype=bool)
    chip = np.asarray(sim.calculate("is_chip_eligible", YEAR), dtype=bool)
    out["medicaid_adult"] = fam_sum(med & adult) / n_adults
    out["medicaid_child"] = fam_sum(med & ~adult) / n_children
    out["medicaid_or_chip_child"] = fam_sum((med | chip) & ~adult) / n_children
    log(f"  {st}: {time.time() - t:.1f}s")
    return out


for st in states:
    res = run(st)
    f = pd.DataFrame({"household_id": fam_index, "w": w, "family_type": ftype, "any_dis": anydis, **res})
    f.to_csv(os.path.join(outdir, f"families_{st}.csv.gz"), index=False, compression="gzip")
    cols = list(res)
    rows = [{"state": st, "cell": "all", "weight_share": 1.0,
             **{c: (f.w * f[c]).sum() / f.w.sum() for c in cols}}]
    for (ft, d), g in f.groupby(["family_type", "any_dis"]):
        rows.append({"state": st, "cell": f"{CELL_TYPES[ft]}/{d}", "weight_share": g.w.sum() / f.w.sum(),
                     **{c: (g.w * g[c]).sum() / g.w.sum() for c in cols}})
    pd.DataFrame(rows).to_csv(os.path.join(outdir, f"index_{st}.csv"), index=False)
    a = rows[0]
    log(f"{st}: snap {a['snap']:.0f} tanf {a['tanf']:.0f} ssi {a['ssi']:.0f} ssp {a['ssp']:.0f} eitc {a['eitc']:.0f} "
        f"ctc {a['ctc']:.0f} actc {a['refundable_ctc']:.0f} state_eitc {a['state_eitc']:.0f} "
        f"medicaid adult {a['medicaid_adult']:.3f} child {a['medicaid_child']:.3f}")
