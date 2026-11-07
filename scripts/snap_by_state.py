"""Estimate what BBCE would add to a Brookings-style SNAP index, by state, July 2024.

Simulates every sample family from build_sample.py, in every state, with its own
members' ages, disability flags (is_disabled, meets_ssi_disability_criteria), full-time
college status, earnings, usual weekly hours and weeks worked, and tax roles (see
pe_frame.py). Each adult's wages plus self-employment income enter as that adult's wages.
Children's earnings enter as zero, or as their own earnings with --child-earnings; every
member's hours and weeks enter as reported. PolicyEngine-US computes SSI, TANF and SNAP for
each family.

Every family is simulated. PolicyEngine-US leaves a full-time college student who meets no
SNAP student exception out of the SNAP unit, along with that student's earnings, so an
earnings cutoff cannot rule a family out of SNAP.

Scenarios, July 2024:
  fed_bbce      PolicyEngine-US current law with federal minimum allotments in DC, MD and NJ
                and no DC temporary local benefit, so SNAP follows federal benefit rules
                apart from each state's BBCE choice
  fed_nobbce    fed_bbce with is_tanf_non_cash_eligible forced False (no BBCE)
  state_bbce    current law, state minimums and DC local benefit included (DC, MD, NJ only;
                elsewhere identical to fed_bbce)
  state_nobbce  state_bbce with is_tanf_non_cash_eligible forced False (DC, MD, NJ only)

Rule switches, for reconciling levels with the Brookings index (each applies to every scenario):
  --no-sua           snap_utility_allowance set to zero, as the appendix mentions no shelter costs
  --no-student-rule  nobody counts as a full-time college student for SNAP's student rule, as the
                     appendix keeps full-time students 19-23 in the benefit unit
  --no-tanf          tanf set to zero, which leaves SNAP's benefit formula free of any TANF model
  --no-standard-deduction
                     snap_standard_deduction set to zero, to test whether Brookings' published SNAP
                     cells fit better without it
  --earnings-scale X multiply every member's earnings by X, to test how far an earnings scale moves the result

Index = sum(w * 12 * July SNAP) / sum(w over all sample families).
Usage: snap_by_state.py persons.csv outdir STATE[,STATE...] [--child-earnings] [--no-sua]
           [--no-student-rule] [--no-tanf] [--no-standard-deduction] [--earnings-scale X]
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe_frame import FIPS, MONTH, build_base, simulate  # noqa: E402

STATE_SUPPLEMENT_STATES = {"DC", "MD", "NJ"}

persons_path, outdir, states = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
CHILD_EARNINGS = "--child-earnings" in sys.argv[4:]
NO_SUA = "--no-sua" in sys.argv[4:]
NO_STUDENT_RULE = "--no-student-rule" in sys.argv[4:]
NO_TANF = "--no-tanf" in sys.argv[4:]
NO_STANDARD = "--no-standard-deduction" in sys.argv[4:]
EARNINGS_SCALE = float(sys.argv[sys.argv.index("--earnings-scale") + 1]) if "--earnings-scale" in sys.argv[4:] else 1.0
os.makedirs(outdir, exist_ok=True)
log = lambda *a: print(*a, file=sys.stderr, flush=True)

per = pd.read_csv(persons_path)
fam = per.groupby("person_household_id").agg(
    w=("household_weight", "first"), size=("role", "size"), earnings=("earnings", "sum"))
W = fam.w.sum()
sim_ids = fam.index
log(f"families {len(fam)}; weighted {W/1e6:.3f}m; simulated {len(sim_ids)} "
    f"({fam.loc[sim_ids, 'w'].sum()/W:.3f} of weight)")

# Person rows for the simulated families, in a fixed order: head, spouse, partner, children.
base, fam_index = build_base(per, sim_ids, child_earnings=CHILD_EARNINGS)
if NO_STUDENT_RULE:
    base["is_full_time_college_student"] = False
base["employment_income"] = base.employment_income * EARNINGS_SCALE
n_f = len(fam_index)
log(f"child earnings {'included' if CHILD_EARNINGS else 'zero'}; members {len(base)}; "
    f"no_sua={NO_SUA} no_student_rule={NO_STUDENT_RULE} no_tanf={NO_TANF} no_standard={NO_STANDARD} earnings_scale={EARNINGS_SCALE}")
w_sim = fam.loc[fam_index, "w"].to_numpy()
fam_type = per.drop_duplicates("person_household_id").set_index("person_household_id")
roles = per.groupby("person_household_id").role.apply(set)
ftype = np.where(roles.loc[fam_index].apply(lambda s: "spouse" in s), "married",
                 np.where(roles.loc[fam_index].apply(lambda s: "partner" in s), "partner", "single"))


def run(st, scen):
    t = time.time()
    sim = simulate(base, FIPS[st], scen, no_sua=NO_SUA, no_tanf=NO_TANF, no_standard=NO_STANDARD)
    out = {
        "snap": np.asarray(sim.calculate("snap_if_takes_up", MONTH)),
        "elig": np.asarray(sim.calculate("is_snap_eligible", MONTH)),
        "tanf": np.asarray(sim.calculate("tanf", MONTH)),
        "bbce_flag": np.asarray(sim.calculate("is_tanf_non_cash_eligible", MONTH)),
        "eldis": np.asarray(sim.calculate("has_snap_elderly_disabled_member", MONTH)),
    }
    ssi_p = np.asarray(sim.calculate("ssi", 2024))
    out["ssi"] = np.bincount(base.fi.to_numpy(), weights=ssi_p, minlength=n_f) / 12
    sc = np.asarray(sim.calculate("state_code_str", 2024))
    assert len(sc) == n_f and (sc == st).all(), (st, sc[:3])
    log(f"  {st} {scen}: {time.time()-t:.1f}s")
    return out


for st in states:
    scens = ["fed_bbce", "fed_nobbce"] + (["state_bbce", "state_nobbce"] if st in STATE_SUPPLEMENT_STATES else [])
    res = {s: run(st, s) for s in scens}
    if st not in STATE_SUPPLEMENT_STATES:
        res["state_bbce"], res["state_nobbce"] = res["fed_bbce"], res["fed_nobbce"]
    fam_out = pd.DataFrame({"household_id": fam_index, "w": w_sim, "family_type": ftype})
    for s, r in res.items():
        for k in ("snap", "elig", "tanf", "ssi"):
            fam_out[f"{k}_{s}"] = r[k]
    fam_out["bbce_flag"] = res["fed_bbce"]["bbce_flag"]
    fam_out["eldis"] = res["fed_bbce"]["eldis"]
    fam_out.to_csv(os.path.join(outdir, f"families_{st}.csv.gz"), index=False, compression="gzip")
    row = {"state": st}
    for s in ("fed_bbce", "fed_nobbce", "state_bbce", "state_nobbce"):
        row[f"snap_index_{s}"] = (w_sim * 12 * fam_out[f"snap_{s}"]).sum() / W
        row[f"share_eligible_{s}"] = (w_sim * fam_out[f"elig_{s}"]).sum() / W
    row["tanf_index"] = (w_sim * 12 * fam_out["tanf_fed_bbce"]).sum() / W
    row["ssi_index"] = (w_sim * 12 * fam_out["ssi_fed_bbce"]).sum() / W
    gain = fam_out.snap_fed_bbce - fam_out.snap_fed_nobbce
    # Zero by construction, never a test: TANF makes a family categorically eligible in both scenarios
    # (meets_snap_categorical_eligibility), so a family with TANF can't gain, and --no-tanf zeroes TANF.
    # scripts/tanf_cross_check.py joins this run's gains to another run's TANF instead.
    row["gainers_with_tanf"] = int(((gain > 0) & (fam_out.tanf_fed_bbce > 0)).sum())
    row["gainers_with_ssi"] = int(((gain > 0) & (fam_out.ssi_fed_bbce > 0)).sum())
    row["losers"] = int((gain < -0.005).sum())
    for t_ in ("married", "partner", "single"):
        m = fam_out.family_type == t_
        row[f"gain_{t_}"] = (w_sim[m] * 12 * gain[m]).sum() / W
    m = fam_out.eldis.astype(bool)
    row["gain_eldis"] = (w_sim[m] * 12 * gain[m]).sum() / W
    pd.DataFrame([row]).to_csv(os.path.join(outdir, f"index_{st}.csv"), index=False)
    log(f"{st}: fed {row['snap_index_fed_nobbce']:.1f} -> {row['snap_index_fed_bbce']:.1f}; "
        f"state {row['snap_index_state_nobbce']:.1f} -> {row['snap_index_state_bbce']:.1f}")
