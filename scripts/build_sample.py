"""Rebuild the State Safety Net Database's simulated sample from the CPS ASEC public-use files.

Follows the database's July 2026 data appendix (v3), at
https://www.brookings.edu/wp-content/uploads/2026/07/Data-Appendix-Summer26-release_final-copy.pdf:

- Pool: the 2015-2019 ASEC, weighted with the reference person's ASEC weight (MARSUPWT), which equals
  HSUP_WGT within 0.1% for household reference persons. --units households uses HSUP_WGT.
- Family units (--units families, the default): every family reference person (A_FAMREL == 1), so a
  parent who heads a related or unrelated subfamily inside someone else's household forms a family of
  their own, and the script disregards the rest of the household. --units households keeps only the
  household reference person.
- Family types: an unmarried reference person with no cohabiting partner; a married reference
  person and spouse; an unmarried reference person with a cohabiting partner (PECOHAB). Two cohabiting
  reference persons form one family, headed by the one in the lower-numbered family.
- Children in the benefit unit: under 19; 19-23 and a full-time student; under 24 and disabled.
  Only children with at least one biological parent in the family (PEPAR1TYP/PEPAR2TYP == 1).
  The script disregards every other household member.
- Keep families with a child under 18, no member 65 or older and no immigrant member
  (PRCITSHP 4 or 5).
- Earnings: prior-year wages plus self-employment plus farm income, inflated to 2024 dollars
  with annual average CPI-U (read from PolicyEngine-US's gov.bls.cpi.cpi_u, monthly values).
- Disability (--disability appendix): reported SSI receipt at any age the file records it;
  work-limiting disability at 15 and older (DIS_HP or PEMLR "not in labor force, disabled");
  the six difficulty items for children 15-18; and, for a child under 18, the ASEC's "which
  children receive SSI" item or an adult's SSI reported on behalf of a child, which marks the
  youngest child under 18 in the unit. The ASEC asks no disability items under age 15.
  meets_ssi_disability_criteria follows is_disabled, as the appendix imputes SSI for this group.

The main sample uses --disability notw --screen household. The other options rebuild the comparison samples that
scripts/fit/ tests:
  --asec Y,Y,...          the ASEC survey years to pool (default 2015-2019)
  --dollars 2023|nominal  bring earnings to 2023 dollars, or leave them in source-year dollars
  --parents any           count step and adoptive parent pointers too
  --disability items      any of the six difficulty items, or SSI under age 65
  --disability hp         as appendix, without PEMLR "not in labor force, disabled"
  --disability nilf       as appendix, with PEMLR but without DIS_HP
  --disability notw       as nilf, adding RSNNOTW "ill or disabled" as the reason for not working last year
  --disability hp_sga     as hp, counting an adult's DIS_HP only below 2024 substantial gainful activity ($18,600)
  --screen household      apply "no member 65 or older, no immigrant member" to the whole household, not the unit

Writes person rows for the kept families to OUT and family rows to OUT with _families.csv, and prints aggregate
diagnostics. Both files hold record-level survey data, so .gitignore keeps them out of the repository.

ASEC_DIR names the folder that holds the Census files (default data/asec, which scripts/download_asec.py fills).

Usage: build_sample.py OUT [--asec Y,Y,...] [--dollars 2024|2023|nominal]
           [--parents biological|any] [--disability appendix|items|hp|nilf|notw|hp_sga] [--units families|households]
           [--screen unit|household]
Invariants checked before writing: one reference person per household; one head per family; at
most one spouse or partner; a child under 18 in every family; nobody 65 or older; nobody foreign
born; every child has a qualifying parent pointer into the family; earnings nonnegative.
"""
import argparse
import gzip
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd
import yaml

SRC = os.environ.get("ASEC_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "asec"))
FIXED = {
    2015: ("asec2015_pubuse.dat.gz", "asec2015early_pubuse.dd.txt"),
    2016: ("asec2016_pubuse_v3.dat.gz", "asec2016_pubuse.dd.txt"),
    2017: ("asec2017_pubuse.dat.gz", "08ASEC2017_Data_Dict_Full.txt"),
    2018: ("asec2018_pubuse.dat.gz", "08ASEC2018_Data_Dict_Full.txt"),
}
PERSON_VARS = [
    "PH_SEQ", "A_LINENO", "A_EXPRRP", "A_AGE", "A_SPOUSE", "PECOHAB", "PEPAR1", "PEPAR2", "PEPAR1TYP",
    "PEPAR2TYP", "PRCITSHP", "A_HSCOL", "A_FTPT", "WSAL_VAL", "SEMP_VAL", "FRSE_VAL", "PEARNVAL", "HRSWK",
    "WKSWORK", "MARSUPWT", "SSI_VAL", "SSIKIDYN", "RESNSSI1", "RESNSSI2", "DIS_HP", "PEMLR",
    "PEDISDRS", "PEDISEAR", "PEDISEYE", "PEDISOUT", "PEDISPHY", "PEDISREM", "A_FAMREL", "A_FAMNUM", "A_MARITL", "RSNNOTW",
]
HH_VARS = ["H_SEQ", "HSUP_WGT"]
# The 2015-2018 files name the parent pointers by mother and father; the 2019 file onward uses PEPAR1/2.
# The value codes match: a line number, and 1 biological, 2 step, 3 adopted.
FIXED_NAMES = {"PEPAR1": "PELNMOM", "PEPAR2": "PELNDAD", "PEPAR1TYP": "PEMOMTYP", "PEPAR2TYP": "PEDADTYP"}
DIFFICULTY = ["PEDISDRS", "PEDISEAR", "PEDISEYE", "PEDISOUT", "PEDISPHY", "PEDISREM"]
SGA_2024_ANNUAL = 12 * 1550  # SSA's 2024 non-blind substantial gainful activity level.
log = lambda *a: print(*a, file=sys.stderr, flush=True)


def parse_dictionary(path):
    """Return {record: {name: (start0, end0)}} from a Census data dictionary's 'D NAME SIZE BEGIN' lines."""
    layout, record = {"H": {}, "F": {}, "P": {}}, None
    pat = re.compile(rb"^D\s+(\S+)\s+(\d+)\s+(\d+)\s")
    with open(path, "rb") as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            name, size, begin = m.group(1).decode(), int(m.group(2)), int(m.group(3))
            if name in ("HRECORD", "FRECORD", "PRECORD"):
                record = name[0]
            if record:
                layout[record][name] = (begin - 1, begin - 1 + size)
    return layout


def read_fixed(year):
    dat, dd = FIXED[year]
    layout = parse_dictionary(os.path.join(SRC, dd))
    names = {v: FIXED_NAMES.get(v, v) for v in PERSON_VARS}
    missing = [n for n in names.values() if n not in layout["P"]] + [v for v in HH_VARS if v not in layout["H"]]
    assert not missing, (year, missing)
    with gzip.open(os.path.join(SRC, dat), "rb") as f:
        lines = f.read().split(b"\n")
    persons = [ln for ln in lines if ln[:1] == b"3"]
    hh = [ln for ln in lines if ln[:1] == b"1"]
    del lines

    def col(rows, span):
        s, e = span
        return np.array([int(r[s:e] or 0) for r in rows], dtype=np.int64)

    p = pd.DataFrame({v: col(persons, layout["P"][names[v]]) for v in PERSON_VARS})
    h = pd.DataFrame({v: col(hh, layout["H"][v]) for v in HH_VARS})
    return p, h


def read_csv_year(year):
    yy = f"{year % 100:02d}"
    with zipfile.ZipFile(os.path.join(SRC, f"asecpub{yy}csv.zip")) as z:
        def member(stem):
            return next(n for n in z.namelist() if n.lower().endswith(f"{stem}{yy}.csv"))
        with z.open(member("pppub")) as f:
            p = pd.read_csv(f, usecols=lambda c: c in PERSON_VARS)
        missing = [v for v in PERSON_VARS if v not in p.columns]
        if missing:
            log(f"ASEC {year}: columns absent from the CSV, entered as zero: {missing}")
            p = p.assign(**{v: 0 for v in missing})
        with z.open(member("hhpub")) as f:
            h = pd.read_csv(f, usecols=HH_VARS)
    return p[PERSON_VARS].astype("int64"), h[HH_VARS].astype("int64")


def annual_cpi():
    """Annual average CPI-U by year, from PolicyEngine-US's monthly parameter."""
    import policyengine_us
    path = os.path.join(os.path.dirname(policyengine_us.__file__), "parameters/gov/bls/cpi/cpi_u.yaml")
    with open(path) as f:
        values = yaml.safe_load(f)["values"]
    s = pd.Series({str(k): float(v) for k, v in values.items()})
    return s.groupby(s.index.str[:4]).mean()


def assign_households(p, year, parents):
    """Return p with hh, role and has_parent, where each household's reference person heads one family."""
    p = p.copy()
    p["hh"] = year * 100000 + p.PH_SEQ
    head_rows = p[p.A_EXPRRP.isin([1, 2])]
    assert head_rows.hh.is_unique, "more than one reference person in a household"
    h_cols = head_rows.set_index("hh")[["A_LINENO", "A_SPOUSE", "PECOHAB"]].rename(columns=lambda c: "h_" + c)
    p = p.join(h_cols, on="hh")
    p = p[p.h_A_LINENO.notna()].copy()
    is_head = p.A_LINENO == p.h_A_LINENO
    is_spouse = (p.h_A_SPOUSE > 0) & (p.A_LINENO == p.h_A_SPOUSE) & ~is_head
    has_spouse = is_spouse.groupby(p.hh).transform("any")
    is_partner = (p.h_PECOHAB > 0) & (p.A_LINENO == p.h_PECOHAB) & ~is_head & ~is_spouse & ~has_spouse
    p["role"] = np.select([is_head, is_spouse, is_partner], ["head", "spouse", "partner"], "other")
    in_couple = p.role.isin(["head", "spouse", "partner"])

    # A parent pointer counts when it points at the head, spouse or partner.
    second = p[p.role.isin(["spouse", "partner"])].set_index("hh").A_LINENO.rename("second_line")
    assert second.index.is_unique, "more than one spouse or partner"
    p = p.join(second, on="hh")

    def to_couple(ptr):
        return (p[ptr] > 0) & ((p[ptr] == p.h_A_LINENO) | (p[ptr] == p.second_line))
    if parents == "biological":
        p["has_parent"] = (to_couple("PEPAR1") & (p.PEPAR1TYP == 1)) | (to_couple("PEPAR2") & (p.PEPAR2TYP == 1))
    else:
        p["has_parent"] = to_couple("PEPAR1") | to_couple("PEPAR2")
    p["in_couple"] = in_couple
    return p


def assign_families(p, year, parents):
    """Return p with hh (a family id), role and has_parent, with one family per family reference person.

    A person who heads a subfamily stays in that family, even when also the qualifying child of the household's
    reference person. Two cohabiting reference persons form one family under the lower-numbered one.
    """
    owner = {}
    refs = p[p.A_FAMREL == 1].sort_values(["PH_SEQ", "A_FAMNUM", "A_LINENO"])
    for ph, line, num, spouse, partner in zip(refs.PH_SEQ, refs.A_LINENO, refs.A_FAMNUM, refs.A_SPOUSE, refs.PECOHAB):
        k = ph * 100 + line
        if k in owner:
            continue
        fam = year * 1000000 + ph * 10 + num
        owner[k] = (fam, "head")
        if spouse > 0:
            owner.setdefault(ph * 100 + spouse, (fam, "spouse"))
        elif partner > 0:
            owner.setdefault(ph * 100 + partner, (fam, "partner"))
    fam_of = pd.Series({k: v[0] for k, v in owner.items()}, dtype="float64")
    role_of = pd.Series({k: v[1] for k, v in owner.items()}, dtype="object")
    p = p.copy()
    key = p.PH_SEQ * 100 + p.A_LINENO
    p["role"] = key.map(role_of).fillna("other")
    own_fam = key.map(fam_of)

    def parent_fam(ptr, typ):
        f = (p.PH_SEQ * 100 + p[ptr]).map(fam_of).where(p[ptr] > 0)
        return f.where(p[typ] == 1) if parents == "biological" else f
    via = parent_fam("PEPAR1", "PEPAR1TYP").fillna(parent_fam("PEPAR2", "PEPAR2TYP"))
    p["in_couple"] = p.role != "other"
    p["has_parent"] = ~p.in_couple & via.notna()
    p["hh"] = own_fam.fillna(via)
    p = p[p.hh.notna()].copy()
    p["hh"] = p.hh.astype("int64")
    return p


def build_year(p, h, year, factor, parents, disability, units="families", screen="unit"):
    """Return person rows of the kept families for one ASEC year."""
    assert p.A_AGE.between(0, 85).all() and p.A_LINENO.between(1, 39).all() and p.PRCITSHP.between(1, 5).all(), year
    assert p.A_EXPRRP.between(1, 14).all(), (year, p.A_EXPRRP.min(), p.A_EXPRRP.max())
    assert h.H_SEQ.is_unique, year
    all_persons = p
    p = assign_families(p, year, parents) if units == "families" else assign_households(p, year, parents)
    in_couple, has_parent = p.in_couple, p.has_parent

    typ = pd.concat([p.PEPAR1TYP[p.PEPAR1 > 0], p.PEPAR2TYP[p.PEPAR2 > 0]]).value_counts(normalize=True).round(3)
    log(f"ASEC {year}: parent pointer types {typ.sort_index().to_dict()}")
    any_item = (p[DIFFICULTY] == 1).any(axis=1)
    ssi = p.SSI_VAL > 0
    limit_items = {"appendix": (p.DIS_HP == 1) | (p.PEMLR == 6), "hp": p.DIS_HP == 1, "nilf": p.PEMLR == 6,
                   "notw": (p.PEMLR == 6) | (p.RSNNOTW == 1),
                   "hp_sga": (p.DIS_HP == 1) & ((p.WSAL_VAL + p.SEMP_VAL + p.FRSE_VAL).clip(lower=0) * factor < SGA_2024_ANNUAL)}
    if disability in limit_items:
        adult_limit = (p.A_AGE >= 15) & limit_items[disability]
        teen_items = p.A_AGE.between(15, 18) & any_item
        child_ssi = (p.A_AGE < 18) & (p.SSIKIDYN == 1)
        p["disabled"] = ssi | adult_limit | teen_items | child_ssi
    else:
        p["disabled"] = any_item | (ssi & (p.A_AGE < 65))
    full_time = p.A_FTPT == 1
    age_ok = (p.A_AGE < 19) | (p.A_AGE.between(19, 23) & full_time) | ((p.A_AGE < 24) & p.disabled)
    p["brookings_child"] = ~in_couple & has_parent & age_ok

    if disability in limit_items:
        # An adult's SSI reported on behalf of a child marks the unit's youngest child under 18,
        # and leaves the adult's own disability status to the adult's other items.
        behalf = (p.RESNSSI1.isin([3, 4]) | p.RESNSSI2.isin([3, 4])) & in_couple
        if behalf.any():
            own_reason = p.RESNSSI1.isin([1, 2, 5]) | p.RESNSSI2.isin([1, 2, 5])
            p.loc[behalf & ~own_reason & ~limit_items[disability], "disabled"] = False
            kids = p[p.brookings_child & (p.A_AGE < 18) & p.hh.isin(p.loc[behalf, "hh"])]
            youngest = kids.sort_values(["hh", "A_AGE"]).groupby("hh").head(1).index
            p.loc[youngest, "disabled"] = True

    unit = p[in_couple | p.brookings_child].copy()
    grp = unit.groupby("hh")
    fam = pd.DataFrame({
        "kids_u18": (unit.brookings_child & (unit.A_AGE < 18)).groupby(unit.hh).sum(),
        "max_age": grp.A_AGE.max(),
        "any_foreign": unit.PRCITSHP.isin([4, 5]).groupby(unit.hh).any(),
    })
    if screen == "household":
        by_ph = all_persons.groupby("PH_SEQ")
        hh_old = by_ph.A_AGE.max() >= 65
        hh_foreign = all_persons.PRCITSHP.isin([4, 5]).groupby(all_persons.PH_SEQ).any()
        fam_ph = grp.PH_SEQ.first()
        fam["max_age"] = np.where(fam_ph.map(hh_old), 99, fam.max_age)
        fam["any_foreign"] = fam.any_foreign | fam_ph.map(hh_foreign)
    keep = fam.index[(fam.kids_u18 >= 1) & (fam.max_age < 65) & ~fam.any_foreign]
    unit = unit[unit.hh.isin(keep)].copy()

    raw = unit.WSAL_VAL + unit.SEMP_VAL + unit.FRSE_VAL
    own = raw.clip(lower=0) * factor
    unit["own_earnings"] = own
    unit["earnings"] = np.where(unit.role != "other", own, 0.0)
    # Diagnostic only: earnings of everyone who shares the head's CPS family number, relatives included.
    member_earn = (all_persons.WSAL_VAL + all_persons.SEMP_VAL + all_persons.FRSE_VAL).clip(lower=0) * factor
    by_cps_family = member_earn.groupby(all_persons.PH_SEQ * 100 + all_persons.A_FAMNUM).sum()
    heads = unit[unit.role == "head"].set_index("hh")
    unit["all_member_earnings"] = unit.hh.map((heads.PH_SEQ * 100 + heads.A_FAMNUM).map(by_cps_family))
    head_w = unit[unit.role == "head"].set_index("hh").MARSUPWT / 100
    hsup = h.assign(hh=year * 100000 + h.H_SEQ).set_index("hh").HSUP_WGT / 100
    if units == "families":
        unit["household_weight"] = unit.hh.map(head_w)
        gap = (head_w / ((head_w.index // 1000000 * 100000 + (head_w.index % 1000000) // 10)).map(hsup).to_series(index=head_w.index) - 1).abs()
        gap = gap[head_w.index % 10 == 1]
    else:
        unit["household_weight"] = unit.hh.map(hsup)
        gap = (head_w / unit[unit.role == "head"].set_index("hh").household_weight - 1).abs()
    assert unit.household_weight.notna().all(), year
    n_units = len(fam)
    log(f"ASEC {year}: persons {len(all_persons)}, weighted pop {all_persons.MARSUPWT.sum() / 100 / 1e6:.1f}m, households "
        f"{(h.HSUP_WGT > 0).sum()} ({h.HSUP_WGT.sum() / 100 / 1e6:.1f}m), candidate units {n_units}, kept {len(keep)} "
        f"({unit.groupby('hh').household_weight.first().sum() / 1e6:.2f}m), factor {factor:.4f}, "
        f"PEARNVAL equals the sum for {(all_persons.PEARNVAL == all_persons.WSAL_VAL + all_persons.SEMP_VAL + all_persons.FRSE_VAL).mean():.4f}; "
        f"head MARSUPWT within 0.1% of HSUP_WGT for {(gap < 0.001).mean():.3f}")
    return pd.DataFrame({
        "person_household_id": unit.hh,
        "household_weight": unit.household_weight,
        "role": unit.role,
        "age": unit.A_AGE,
        "is_disabled": unit.disabled.astype(int),
        "meets_ssi_disability_criteria": unit.disabled.astype(int),
        "is_full_time_college_student": ((unit.A_HSCOL == 2) & (unit.A_FTPT == 1)).astype(int),
        "earnings": unit.earnings,
        "source_year": year - 1,
        "weekly_hours": unit.HRSWK.astype(float),
        "weeks_worked": unit.WKSWORK.clip(0, 52).astype(float),
        "own_earnings": unit.own_earnings,
        "reported_earnings_nominal": raw.clip(lower=0),
        "all_member_earnings": unit.all_member_earnings,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--asec", default="2015,2016,2017,2018,2019")
    ap.add_argument("--dollars", default="2024", choices=["2024", "2023", "nominal"])
    ap.add_argument("--parents", default="biological", choices=["biological", "any"])
    ap.add_argument("--disability", default="appendix", choices=["appendix", "items", "hp", "nilf", "notw", "hp_sga"])
    ap.add_argument("--screen", default="unit", choices=["unit", "household"])
    ap.add_argument("--units", default="families", choices=["families", "households"])
    a = ap.parse_args()
    years = [int(y) for y in a.asec.split(",")]
    cpi = annual_cpi()
    log("annual CPI-U:", {y: round(cpi[str(y)], 3) for y in list(range(2014, 2019)) + [2022, 2023, 2024]})
    parts = []
    for y in years:
        p, h = read_fixed(y) if y in FIXED else read_csv_year(y)
        factor = 1.0 if a.dollars == "nominal" else cpi[a.dollars] / cpi[str(y - 1)]
        parts.append(build_year(p, h, y, factor, a.parents, a.disability, a.units, a.screen))
    per = pd.concat(parts, ignore_index=True)

    # Invariants of the sample.
    assert per.earnings.ge(0).all() and per.own_earnings.ge(0).all()
    assert per.age.lt(65).all(), "a member 65 or older"
    roles = per.groupby("person_household_id").role
    assert (roles.apply(lambda r: (r == "head").sum()) == 1).all(), "one head per family"
    assert (roles.apply(lambda r: r.isin(["spouse", "partner"]).sum()) <= 1).all(), "one spouse or partner at most"
    kids = per[per.role == "other"]
    assert kids.groupby("person_household_id").age.min().lt(18).all(), "a family without a child under 18"
    assert kids.person_household_id.nunique() == per.person_household_id.nunique(), "a family with no child"

    fam = per.groupby("person_household_id").agg(
        household_weight=("household_weight", "first"), earnings=("earnings", "sum"),
        source_year=("source_year", "first"), size=("role", "size"), any_disabled=("is_disabled", "max"))
    role_sets = per.groupby("person_household_id").role.apply(set)
    fam["family_type"] = np.where(role_sets.apply(lambda s: "spouse" in s), "married",
                                  np.where(role_sets.apply(lambda s: "partner" in s), "partner", "single"))
    W = fam.household_weight.sum()
    log(f"families {len(fam)}; weighted {W / 1e6:.3f}m; annual average {W / len(years) / 1e6:.3f}m")
    log("family type shares:", fam.groupby("family_type").household_weight.sum().div(W).round(4).to_dict())
    log("families by source year:", fam.groupby("source_year").size().to_dict())
    log("share with a disabled member:", round(fam.household_weight[fam.any_disabled == 1].sum() / W, 4))
    log("mean family earnings:", round(np.average(fam.earnings, weights=fam.household_weight)),
        " median:", round(fam.earnings.sort_values().iloc[(fam.household_weight[fam.earnings.sort_values().index].cumsum() >= W / 2).argmax()]))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    per.to_csv(a.out, index=False)
    fam.to_csv(a.out.replace(".csv", "_families.csv"))
    log("wrote", a.out)


if __name__ == "__main__":
    main()
