"""Invariants of the committed outputs, which hold aggregates only, and the README's headline figures against them.

For every state in every run of scripts/snap_by_state.py in out/runs:
  - BBCE lowers no family's SNAP (losers == 0), so the index and the share of families eligible with BBCE are at least
    those without it, under federal benefit rules and with state benefits.
  - The gains of married, cohabiting and single-parent families sum to the whole gain, and the gain of families with an
    elderly or disabled member lies between zero and the whole gain.
  - No family that receives TANF gains, since TANF makes a family categorically eligible for SNAP in both scenarios.
  - Outside DC, Maryland and New Jersey, the scenarios with state benefits equal those with federal benefit rules.
  - In the states with no BBCE in PolicyEngine-US's July 2024 parameters, BBCE adds nothing.
The per-state table matches the main run's summaries, and the README's headline figures match those summaries.
"""
import glob
import os

import numpy as np
import pandas as pd
import pytest
from policyengine_us.system import system

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
GROSS = system.parameters.gov.hhs.tanf.non_cash.income_limit.gross("2024-07-01")
STATE_BENEFIT_STATES = {"DC", "MD", "NJ"}
INDEXES = sorted(p for p in glob.glob(os.path.join(OUT, "runs", "*", "index_*.csv"))
                 if "snap_index_fed_bbce" in open(p).readline())


def summary(run):
    return pd.read_csv(os.path.join(OUT, f"summary_{run}.csv"), index_col="state")


def above_130(t):
    """The jurisdictions whose BBCE limit for working families exceeds 130% of poverty; New York's is 150%."""
    return t[(np.isfinite(t.bbce_gross_limit) & (t.bbce_gross_limit > 1.3)) | (t.index == "NY")]


def test_runs_cover_every_state():
    runs = {os.path.basename(os.path.dirname(p)) for p in INDEXES}
    assert {"appendix_x107", "appendix_x100", "pe_rules_x107"} <= runs
    for run in ("appendix_x107", "appendix_x100", "pe_rules_x107"):
        assert len(glob.glob(os.path.join(OUT, "runs", run, "index_*.csv"))) == 51


@pytest.mark.parametrize("path", INDEXES, ids=lambda p: os.path.relpath(p, OUT))
def test_index_invariants(path):
    r = pd.read_csv(path).iloc[0]
    gain = r.snap_index_fed_bbce - r.snap_index_fed_nobbce
    assert r.losers == 0
    assert gain >= -1e-9
    assert r.snap_index_state_bbce >= r.snap_index_state_nobbce - 1e-9
    assert r.share_eligible_fed_bbce >= r.share_eligible_fed_nobbce - 1e-12
    assert r.share_eligible_state_bbce >= r.share_eligible_state_nobbce - 1e-12
    assert r.gain_married + r.gain_partner + r.gain_single == pytest.approx(gain, abs=1e-6)
    assert -1e-9 <= r.gain_eldis <= gain + 1e-9
    assert r.gainers_with_tanf == 0
    if r.state not in STATE_BENEFIT_STATES:
        for k in ("bbce", "nobbce"):
            assert r[f"snap_index_state_{k}"] == r[f"snap_index_fed_{k}"]
    if not np.isfinite(GROSS[r.state]):
        assert gain == 0 and r.share_eligible_fed_bbce == r.share_eligible_fed_nobbce


@pytest.mark.parametrize("run", ["appendix_x107", "appendix_x100", "pe_rules_x107"])
def test_summary_matches_indexes(run):
    t = summary(run)
    assert len(t) == 51
    for st, r in t.iterrows():
        i = pd.read_csv(os.path.join(OUT, "runs", run, f"index_{st}.csv")).iloc[0]
        assert r.gain_fed == pytest.approx(i.snap_index_fed_bbce - i.snap_index_fed_nobbce, abs=1e-9)
        assert r.gain_state == pytest.approx(i.snap_index_state_bbce - i.snap_index_state_nobbce, abs=1e-9)
        # Brookings' file stores its index in single precision, and the summary writes it with single-precision
        # digits, so the percentage, computed before writing, agrees to about 1e-7.
        assert r.gain_fed_pct_brookings == pytest.approx(100 * r.gain_fed / r.brookings_snap_index, rel=1e-6)
    assert len(above_130(t)) == 35 and "DC" in above_130(t).index


def test_state_table_matches_summaries():
    path = os.path.join(OUT, "bbce_snap_index_2024_by_state.csv")
    lines = open(path, encoding="ascii").read().splitlines()
    table = pd.read_csv(path, skiprows=next(i for i, line in enumerate(lines) if line.startswith("state,")),
                        keep_default_na=False).set_index("state")
    main, cpi = summary("appendix_x107"), summary("appendix_x100")
    assert sorted(table.index) == sorted(main.index)
    for st, row in table.iterrows():
        m = main.loc[st]
        assert row.pe_snap_federal_rules_usd_per_family_per_year == round(m.snap_index_fed_nobbce, 1)
        assert row.pe_snap_with_bbce_usd_per_family_per_year == round(m.snap_index_fed_bbce, 1)
        assert row.bbce_adds_usd_per_family_per_year == round(m.gain_fed, 1)
        assert row.brookings_2024_snap_usd_per_family_per_year == round(m.brookings_snap_index)
        assert row.bbce_adds_pct_of_brookings_2024 == round(m.gain_fed_pct_brookings, 1)
        assert row.bbce_adds_usd_at_cpi_u_earnings == round(cpi.loc[st, "gain_fed"], 1)
        limit = 1.5 if st == "NY" else m.bbce_gross_limit
        assert row.bbce_gross_income_limit_pct_poverty == (str(round(100 * limit)) if np.isfinite(limit) else "no BBCE")


def test_readme_headline_figures():
    readme = open(os.path.join(ROOT, "README.md")).read()
    for run, gain, pct in (("appendix_x107", "$91.44", "7.04%"), ("appendix_x100", "$100.40", "7.73%")):
        t = above_130(summary(run))
        assert f"${t.gain_fed.median():.2f}" == gain and f"{t.gain_fed_pct_brookings.median():.2f}%" == pct
        assert gain in readme and pct in readme
