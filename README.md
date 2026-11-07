# BBCE and the SNAP index in Brookings' State Safety Net Interactive

In its [State Safety Net Interactive](https://www.brookings.edu/articles/state-safety-net-interactive-2026/), Brookings shows what SNAP, TANF, SSI, tax credits and Medicaid would provide one fixed sample of families with children if they lived in each state, in each year from 2001 to 2024. Brookings' team computes SNAP under federal rules, without the state option of broad-based categorical eligibility (BBCE).

Through BBCE, a state makes households categorically eligible for SNAP when they qualify for a non-cash benefit that the state funds with TANF or maintenance-of-effort money, often a brochure or a referral. The state then applies that benefit's income and asset limits in place of SNAP's federal tests, among them a gross income limit of 130% of the poverty guidelines. In 2024, [34 states and DC](https://web.archive.org/web/20240906193040/https://www.fns.usda.gov/sites/default/files/resource-files/BBCE-States-Chart-Aug-2024.pdf) set limits that let working families qualify above 130%.

We rebuilt the interactive's sample from the Census Bureau's Current Population Survey and computed each family's July 2024 SNAP in every state with [PolicyEngine-US](https://github.com/PolicyEngine/policyengine-us), under federal rules and under the state's BBCE rules. In those 34 states and DC, we estimate that BBCE would raise the 2024 SNAP index by a median of $91.44 per family per year, or a median of 7.04% of Brookings' published values. We list every state's estimate in [`out/bbce_snap_index_2024_by_state.csv`](out/bbce_snap_index_2024_by_state.csv), after rows that describe the method.

## Results

As a share of Brookings' index, the gain grows with a state's limit, and it shrinks where the state also requires net income at or below the poverty line, as SNAP's federal net income test does.

| BBCE rule for working families, 2024 | Jurisdictions | Median gain, $ per family per year | Gain, % of Brookings' index |
|---|---|---:|---:|
| 200% of poverty, no net income test | CA, CO, CT, DC, DE, FL, KY, MA, MD, ME, MI, MN, MT, NC, NH, NV, OR, PA, VA, WA, WI, WV | 91.4 | 7.4 |
| 185%, no net income test | AZ, NJ, VT | 90.5 | 7.0 |
| 165%, no net income test | IL, NE, NM, TX | 84.1 | 6.4 |
| 160%, no net income test | IA | 80.1 | 6.0 |
| 150% for households with earnings | NY | 65.7 | 5.3 |
| 200%, net income test kept | HI | 103.0 | 3.1 |
| 185% or 200%, net income test kept | LA, ND, RI | 18.1 | 1.4 to 1.6 |
| 130% | AL, GA, ID, IN, OH, OK, SC | 0 to 10.2 | 0 to 0.9 |
| No BBCE | AK, AR, KS, MO, MS, SD, TN, UT, WY | 0 | 0 |

USDA counts a SNAP household member as elderly or disabled at 60 or older, or when they receive SSI or another disability benefit. Under federal law, households with such a member skip the gross income test but must pass the net income test, and states set separate BBCE rules for these households. USDA's Food and Nutrition Service (FNS) lists each state's gross income and asset limits in its August 2024 chart. For each state's net income test and its rules for these households, we use PolicyEngine-US's parameters ([`out/bbce_params_2024.txt`](out/bbce_params_2024.txt)).

For example, Minnesota and Nebraska keep the net income test for these households, so families with an elderly or disabled member gain nothing there. Minnesota's gain of $81.20 therefore trails the $91.44 median of the 22 jurisdictions with a 200% limit and no net income test. In Ohio, families with an elderly or disabled member skip the net income test up to 200% of poverty, and they receive all of the state's $10.24 gain. Alabama, Georgia and South Carolina apply their rules for these households only when every member qualifies as elderly or disabled. Families with children and an SSI recipient fall under the general rule there, a 130% limit with no net income test, and those whose net income exceeds the poverty line add $1.33 to each state's index ([`out/elderly_disabled_split_appendix_x107.txt`](out/elderly_disabled_split_appendix_x107.txt)).

Across the 35 jurisdictions, families whose earnings fall between 130% and 150% of the 2023 poverty guideline receive two thirds of the gain, and families between 150% and 165% receive another 19%. Married parents receive 55% of it, single parents 31% and cohabiting parents 14%, and families with an elderly or disabled member receive 10%. For example, in Florida, which has the median gain of the 35, 7.6% of the sample's families get more SNAP with BBCE, and the share with any SNAP rises from 20.6% to 28.2%. Families that gain receive an average of $739 a month in Hawaii, and from $98 in Massachusetts to $161 in Louisiana elsewhere ([`out/detail_appendix_x107.txt`](out/detail_appendix_x107.txt)).

## How BBCE changes one family's SNAP

A single parent with children aged 5 and 9 who earns $32,500 a year in wages has gross income of $2,708 a month, just over SNAP's federal limit of $2,694 for a family of three. For October 2023 through September 2024, USDA sets that limit at 130% of the 2023 poverty guideline and rounds it up to the next dollar. We compute the family's monthly SNAP for July 2024 under PolicyEngine-US's rules, with no rent:

| Annual wages | Federal rules | California (200%) | Texas (165%) | Ohio (130%) | Arkansas (no BBCE) |
|---:|---:|---:|---:|---:|---:|
| $32,500 | $0 | $175 | $175 | $0 | $0 |
| $35,000 | $0 | $125 | $125 | $0 | $0 |
| $37,500 | $0 | $75 | $75 | $0 | $0 |
| $40,000 | $0 | $25 | $25 | $0 | $0 |
| $42,500 | $0 | $0 | $0 | $0 | $0 |

At $42,500, the family stays under California's limit, but 30% of its net income exceeds the $766 maximum benefit for three, so it gets nothing. Texas sets its limit at 165% of poverty, or $41,019 a year for a family of three. With $1,000 a month in rent at $32,500, the family gets $180 a month in Texas and $358 in California, where PolicyEngine-US adds SNAP's standard utility allowance to every household's shelter costs. Under federal rules, it gets nothing in either state ([`out/examples_table.txt`](out/examples_table.txt)).

## How Brookings' SNAP index varies across states

Brookings' team computes SNAP under federal rules, "using earnings and family structure", and counts TANF as income ([data appendix](https://www.brookings.edu/wp-content/uploads/2026/07/Data-Appendix-Summer26-release_final-copy.pdf), p. 3). States set some SNAP deductions themselves: the standard utility allowance, the standard medical deduction for elderly and disabled members, and whether legally obligated child support counts as an income exclusion or a deduction. Each of these deductions depends on a household's utility, medical or child support costs, and the appendix lists none of those costs among SNAP's inputs.

Across the 48 states other than Alaska and Hawaii, plus DC, Brookings' 2024 SNAP index falls 27 cents for each dollar of its TANF index. Under federal law, each dollar of net income cuts a household's benefit by 30 cents. The line fits the 49 jurisdictions with an R² of 0.974, and every jurisdiction but California comes within $34 of it, while California sits $108 above it ([`out/fit/snap_tanf_residuals.txt`](out/fit/snap_tanf_residuals.txt)). USDA sets higher SNAP maximum benefits, standard deductions and shelter deduction caps for Alaska and Hawaii, and HHS sets higher poverty guidelines there. Brookings' index for the two states sits $903 and $2,158 above the line.

Brookings' index doesn't move with the BBCE gain we estimate. When we add that gain to the regression, it gets a coefficient of −0.02, with a standard error of 0.07, where an index that included BBCE would give it about 1. We estimate a median gain of $91.44 in the 34 of the 49 with a BBCE limit above 130%. Brookings' index sits a median $0.06 above the line in these 34 and $3.37 above it in the other 15.

In 13 jurisdictions (CA, CT, DC, MA, ME, MI, MT, NY, OR, PA, RI, VT and WA), PolicyEngine-US gives every household SNAP's standard utility allowance, whatever its utility costs. With that allowance and no rent, we estimate that the federal-rules index there would rise by a median of $105.57, or 7.7%, from $12.58 in DC to $202.83 in Maine. If Brookings' index included the allowance, these 13 would sit well above the TANF line. Instead, Brookings' index sits a median $5.24 below the line in these 13 and $3.28 above it in the other 36. California sits $107.52 above it, more than twice the $49.09 the allowance would add there. With the allowance, the median BBCE gain in the 13 rises from $91.44 to $91.92 ([`out/sua_test.txt`](out/sua_test.txt)).

In Wisconsin, where Brookings shows no TANF, rent moves our SNAP away from Brookings'. We compute it with hand-coded federal rules and the 7% earnings raise at which the federal EITC alone fits Brookings' values best ([Earnings](#earnings)). Our 2024 SNAP for the state's three family types with no disabled member then exceeds Brookings' by 0.3% to 4.7% with no rent. Rent of $500 a month widens the gap to 1.4% to 6.7%, and rent of $1,000 to 7.9% to 16.7% ([`out/fit/rent_test_x107.txt`](out/fit/rent_test_x107.txt)).

## Method

### Sample

We pool the 2015–2019 CPS ASEC public-use files, as the appendix does, and form a family around each family reference person, with any spouse or cohabiting partner. Two reference persons who cohabit form one family. We include each family's children under 19, its children aged 19–23 in school full time and its disabled children under 24, as long as a biological parent lives in the family, and we disregard other household members. We keep the 90,127 families with a child under 18 whose households have nobody 65 or older and no foreign-born members, and weight each family by its reference person's ASEC weight. If we apply the age and immigrant screens to the family alone, instead of the whole household, the sample fits Brookings' published EITC and Wisconsin SNAP values less well ([`out/fit/joint_anchor.txt`](out/fit/joint_anchor.txt)).

We count a member as disabled if they:

- receive SSI in their own right;
- at 15 or older, say a disability keeps them out of the labor force, or that illness or disability kept them from working the prior year;
- at 15–18, report difficulty on any of the CPS's six disability questions;
- under 18, appear in the ASEC's record of children who receive SSI, which the 2015–2018 files carry.

When a parent reports SSI received on behalf of a child, we count the family's youngest child under 18.

The appendix also names the CPS's work-limiting disability item. If we counted it in place of the prior-year reason for not working, 12.3% of families would have a disabled member, against the 8.7% we recover from Brookings' files and 8.5% in our sample ([`out/fit/variant_anchor.txt`](out/fit/variant_anchor.txt)). We get the next best fit to Brookings' published EITC and Wisconsin SNAP values when we swap the labor-force and prior-year items for the work-limiting item ([`out/fit/joint_anchor.txt`](out/fit/joint_anchor.txt)). We then count that item only for members who earn less than $18,600 a year, the 2024 substantial gainful activity level. With that definition, 8.9% of families have a disabled member, and we estimate that BBCE adds $92.40 in Wisconsin, against $91.97 in the main sample ([`out/disability_runner_up_WI.txt`](out/disability_runner_up_WI.txt)).

Brookings publishes each state-year value along with its values for six cells of family type and disability. Since Brookings places the same sample in every state and year, each state-year value averages its six cells with the same weights, and we recover those weights by least squares over SNAP, TANF, SSI and the federal EITC. Our shares come within a percentage point of Brookings':

| Family type | Disabled member | Brookings | Our sample |
|---|---|---:|---:|
| Married parents | No | 57.60% | 58.47% |
| Married parents | Yes | 3.93% | 3.96% |
| Single parent | No | 26.17% | 25.35% |
| Single parent | Yes | 3.55% | 3.45% |
| Cohabiting parents | No | 7.52% | 7.70% |
| Cohabiting parents | Yes | 1.22% | 1.07% |

### Earnings

For the reference person and any spouse or partner, we sum prior-year wages, self-employment and farm income, floor each person's sum at zero, bring it to 2024 dollars with annual average CPI-U, and enter it as wages. We enter children's earnings as zero. Brookings' team keeps each family's real earnings constant across years, and the appendix doesn't name the price index. At CPI-U, our federal EITC and Wisconsin SNAP exceed Brookings' published values, so we raise earnings a further 7%.

We fit that raise to Brookings' values for Wisconsin families with no disabled member, since Brookings shows no TANF in Wisconsin and its SNAP there depends on earnings and SNAP's rules alone. We compute three sets of values with hand-coded rules, SNAP's parameters from PolicyEngine-US and the 2024 EITC schedule:

- the 2024 federal EITC, which depends on earnings and tax rules alone;
- SNAP in July 2020, when states paid emergency allotments that brought every eligible household to the maximum benefit, so only eligibility matters;
- SNAP in 2016–2019, 2023 and 2024, under the regular benefit formula.

We test the hand-coded rules against PolicyEngine-US in the 48 contiguous states and DC, with no utility allowance ([`tests/test_rules.py`](tests/test_rules.py)). For families with no elderly or disabled member and no income but earnings, with or without rent, they give the same July 2024 SNAP as PolicyEngine-US, to the cent.

Across those values, the root-mean-square log gap between ours and Brookings' falls from 0.112 at CPI-U to 0.025 with a 7% raise and 0.024 with 8%. We use 7%, where the EITC alone fits best, with a gap of 0.015. Without SNAP's standard deduction, the gap rises to 0.070 at a 7% raise, and its lowest value across the five raises we try without it (0%, 3%, 5%, 7% and 10%) comes to 0.052, at 3% ([`out/fit/joint_anchor.txt`](out/fit/joint_anchor.txt), [`out/fit/fine_scale.txt`](out/fit/fine_scale.txt)).

If we inflated earnings with SSA's national average wage index instead of CPI-U, the sample's 2024 earnings would rise by 9.8% on average, and the gap would come to 0.034 with no further raise ([`out/fit/wage_index_test.txt`](out/fit/wage_index_test.txt)).

### SNAP

We place each family in every state and compute its July 2024 SNAP with PolicyEngine-US 2.100.0 twice: under federal rules, with BBCE off, and under the state's BBCE rules. PolicyEngine-US's 2024 BBCE gross income and asset limits match FNS's August 2024 chart in all 42 jurisdictions that use BBCE ([`out/fns_chart_check.txt`](out/fns_chart_check.txt)). We enter each member's age, disability flags, earnings, usual weekly hours, weeks worked and tax role, and no other income, assets, housing costs or child care costs. We set every family's utility allowance to zero. As the appendix's benefit unit does, we keep full-time students aged 19–23 in the family, and we count nobody as a full-time college student under SNAP's student rule. We leave out the state minimum benefits in DC, Maryland and New Jersey, and DC's local supplement, in both scenarios.

We mark every member we count as disabled as meeting SSI's disability criteria. PolicyEngine-US gives no SSI to members who earn over $1,550 a month, the 2024 limit on substantial gainful activity, and counts federal SSI and the state supplements it models as SNAP income. As federal law requires, it exempts families with an SSI recipient or a member 60 or older from SNAP's gross income test. It also leaves K-12 students' earnings out of SNAP income and treats everyone aged 5–17 as a K-12 student, so it leaves out the earnings of the heads under 18 in 87 sample families. In Wisconsin, those families add $6.35 to the index and $0.03 to the gain ([`out/teen_heads_appendix_x107.txt`](out/teen_heads_appendix_x107.txt)).

We set TANF to zero, so it counts neither as SNAP income nor as a route to categorical eligibility. Brookings counts TANF as SNAP income, and under federal law TANF families qualify for SNAP categorically, so they gain nothing from BBCE. Under PolicyEngine-US's TANF rules, 0.8% of the families that gain from BBCE in the 35 jurisdictions receive TANF. If we leave out their gains, the median gain falls from $91.44 to $90.57, with the largest drops in Wisconsin ($5.78) and California ($5.58) ([`out/tanf_cross_check.txt`](out/tanf_cross_check.txt)).

We multiply each family's July benefit by 12 and average it over every family in the sample, including families with no SNAP, using the families' weights.

### What moves the estimate

We change one choice at a time ([`out/compare_runs.txt`](out/compare_runs.txt), [`out/tanf_cross_check.txt`](out/tanf_cross_check.txt)):

| Change from the main estimate | Median gain over the 35 jurisdictions | % of Brookings' index |
|---|---:|---:|
| None | $91.44 | 7.04% |
| Earnings at CPI-U, without the 7% raise | $100.40 | 7.73% |
| Sample reweighted to Brookings' six cell shares | $91.69 | 7.06% |
| PolicyEngine-US's own SNAP rules, with utility allowances, the student rule and TANF | $89.29 | 6.88% |
| Without families that receive TANF under PolicyEngine-US's rules | $90.57 | 7.01% |

With the state minimum benefits and DC's local supplement, we estimate that BBCE adds $228.17 in DC, $91.56 in Maryland and $137.80 in New Jersey. We also build nine variants of the sample, which change the family unit, the screens, the disability definition and whose earnings count. With hand-coded federal rules and the 7% raise, we estimate that a 200% limit with no net income test adds $88.12 to $90.45 across them, and $90.10 in the main sample ([`out/fit/variant_gain.txt`](out/fit/variant_gain.txt)). The hand-coded rules treat no member as elderly or disabled and count no SSI.

### Our federal-rules index against Brookings'

In Wisconsin, our federal-rules index of $1,350.27 trails Brookings' $1,400.44 by 3.6%, and at CPI-U earnings it exceeds Brookings' by 2.1%. For Wisconsin's three family types with no disabled member, ours comes within 5% of Brookings'. For the three with a disabled member, ours trails Brookings' by 15% to 19%, while our federal SSI exceeds Brookings' federal and state SSI by 10% to 56% ([`out/disability_runner_up_WI.txt`](out/disability_runner_up_WI.txt)).

Across the 48 states other than Alaska and Hawaii, plus DC, our index exceeds Brookings' by a median 6.0% (interquartile range 2.3% to 14.3%), and the gap runs from −3.6% in Wisconsin to +57.3% in Minnesota ([`out/level_gap_appendix_x107.txt`](out/level_gap_appendix_x107.txt)). Since we set TANF to zero, ours falls 1 cent for each dollar of Brookings' TANF index, against Brookings' 27 cents. With PolicyEngine-US's own SNAP rules and TANF, ours trails Brookings' by a median 4.0%. PolicyEngine-US's federal SSI comes to $831.89 per family in every state, while Brookings' federal and state SSI runs from $633.60 to $876.10 ([`out/compare_runs.txt`](out/compare_runs.txt)).

### Other programs

With the 7% raise, we also compute TANF, SSI, tax credits and Medicaid eligibility for the same sample under PolicyEngine-US's own rules. We compute SNAP as in our federal-rules index, but count PolicyEngine-US's TANF as income and as a route to categorical eligibility. We compare each program with Brookings' 2024 values across the 50 states and DC ([`out/replicate_x107_compare.txt`](out/replicate_x107_compare.txt)):

| Brookings | PolicyEngine-US | Brookings median | PolicyEngine-US median | Median ratio | Correlation across states |
|---|---|---:|---:|---:|---:|
| SNAP | `snap` | $1,295 | $1,232 | 0.962 | 0.949 |
| TANF | `tanf` | $559 | $581 | 1.020 | 0.659 |
| SSI, federal and state | `ssi` plus state supplements | $634 | $832 | 1.313 | 0.922 |
| Federal EITC | `eitc` | $1,034 | $992 | 0.959 | |
| State EITC | `state_eitc` | $102 | $98 | 0.959 | 0.837 |
| Refundable CTC | `refundable_ctc` | $552 | $535 | 0.969 | |
| Nonrefundable CTC | `income_tax_capped_non_refundable_credits` | $2,346 | $2,386 | 1.017 | |
| Medicaid, share of adults | `medicaid_adult` | 0.249 | 0.249 | 1.002 | 0.937 |
| Medicaid, share of children | `medicaid_child` | 0.381 | 0.356 | 0.969 | 0.325 |
| Medicaid, share of children | `medicaid_or_chip_child` | 0.381 | 0.457 | 1.184 | 0.990 |

Federal credits don't vary across states, so we report no correlation for them. Our SNAP falls below Brookings' where our TANF exceeds Brookings', by 27.5 cents for each dollar of the TANF gap across states, with a correlation of −0.97 ([`out/replicate_x107_snap_tanf.txt`](out/replicate_x107_snap_tanf.txt)).

### BBCE from 2001 to 2020

States adopted BBCE limits above 130% of poverty over the years the interactive covers. We count the states and DC that used BBCE each July in ERS's [SNAP Policy Database](https://www.ers.usda.gov/data-products/snap-policy-data-sets), which covers 1996 through 2020 ([`out/ers_bbce_counts.txt`](out/ers_bbce_counts.txt)):

| July | Using BBCE | With a BBCE limit above 130% |
|---:|---:|---:|
| 2001 | 7 | 7 |
| 2005 | 11 | 10 |
| 2009 | 27 | 17 |
| 2011 | 40 | 26 |
| 2015 | 40 | 27 |
| 2020 | 41 | 31 |

## Reproduce

The scripts need Python 3.12 and [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/PolicyEngine/snap-bbce-safety-net-index
cd snap-bbce-safety-net-index
uv sync
uv run ./run_all.sh
```

`run_all.sh` runs six stages in order. `download` fetches the 2015–2019 ASEC files from the Census Bureau (about 300 MB) and Brookings' database (about 6 MB), and checks their SHA-256 hashes. `samples` builds the main sample and the three variants the fit compares it with, and `fit` runs the earnings and sample tests. `runs` computes each family's SNAP in every state, and for the replication it computes every program. `summaries` and `checks` then write the rest of `out/`. To run some stages, name them: `uv run ./run_all.sh summaries checks`. On four cores, the runs stage takes about two hours. `WORKERS` sets how many states run at once, and rerunning a stopped run picks it up where it left off. `scripts/download_ers.py` rebuilds `sources/ers_snap_policy_database_july.csv` from ERS's workbook.

The samples and the per-family run files hold record-level survey data, so `.gitignore` keeps them out of the repository. Every committed file in `out/` holds aggregates.

## Tests

`uv run pytest` runs two sets of tests. [`tests/test_outputs.py`](tests/test_outputs.py) checks that, in every state of every SNAP run, BBCE lowers no family's SNAP, the gains of the three family types sum to the whole gain, families with TANF gain nothing, and states with no BBCE gain nothing. It also checks the per-state table and this README's headline figures against the run summaries. [`tests/test_rules.py`](tests/test_rules.py) draws families at random with [Hypothesis](https://hypothesis.readthedocs.io/) and checks that the fit's hand-coded SNAP rules match PolicyEngine-US in July 2024 in the 48 contiguous states and DC, with and without BBCE and with and without rent.

## Files

| Path | Contents |
|---|---|
| `out/bbce_snap_index_2024_by_state.csv` | Each state's federal-rules index, index with BBCE, gain, Brookings' index and notes, after the method rows |
| `out/runs/<run>/index_<state>.csv` | Each run's aggregates for one state |
| `out/summary_<run>.txt`, `out/detail_<run>.txt` | Each run against Brookings' 2024 index, and its gains by rule, earnings band and family type |
| `out/fit/` | The earnings fit, sample variants, and the BBCE, rent, SSI and TANF tests |
| `out/sua_test.txt` | The utility allowance test |
| `out/replicate_<run>_compare.txt` | Every program in Brookings' 2024 file, against PolicyEngine-US |
| `sources/` | FNS's August 2024 BBCE chart, its transcription, and ERS's July rows |
| `scripts/` | The code; each script's docstring describes its inputs and outputs |
| `tests/` | Invariants of the outputs, and the hand-coded SNAP rules against PolicyEngine-US |

`appendix_x107` holds the main estimate, with no utility allowance, full-time students in the SNAP unit, TANF at zero and the 7% raise. `appendix_x100` keeps CPI-U earnings, `pe_rules_x107` uses PolicyEngine-US's own SNAP rules, `appendix_sua_x107` gives the utility allowance in its 13 jurisdictions, `appendix_x107_hp_sga` runs Wisconsin on the disability variant, and `replicate_x107` and `replicate_x100` compute every program.

## Sources

- Curtis Broker, Janina, Gabriela Goodman, Lucie Schmidt, Lara Shore-Sheppard, Sasha Snyder, and Tara Watson, 2026. State Safety Net Database version v3 [dataset]. Brookings Institution, Washington, D.C. [Data appendix](https://www.brookings.edu/wp-content/uploads/2026/07/Data-Appendix-Summer26-release_final-copy.pdf).
- U.S. Census Bureau, [Current Population Survey Annual Social and Economic Supplement](https://www2.census.gov/programs-surveys/cps/datasets/), 2015–2019 public-use files.
- USDA Food and Nutrition Service, [Broad-Based Categorical Eligibility chart](https://web.archive.org/web/20240906193040/https://www.fns.usda.gov/sites/default/files/resource-files/BBCE-States-Chart-Aug-2024.pdf), August 2024.
- USDA Economic Research Service, [SNAP Policy Database](https://www.ers.usda.gov/data-products/snap-policy-data-sets).
- [PolicyEngine-US](https://github.com/PolicyEngine/policyengine-us) 2.100.0.

## License

The code carries the MIT license ([LICENSE](LICENSE)). The download scripts fetch the Census and Brookings files from their publishers.
