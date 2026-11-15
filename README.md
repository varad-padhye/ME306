# Hydrogen-Blended Gas Turbine for Decarbonised Grid Power
### ME 306 Course Project, Problem 16: team repository

**Team:** Vedika Kone (R1, 24B2115), Tanvi Gattani (R2, 24B2246), Shravanee Kulkarni (R3, 24B2206), Dhanvin A. S. (R4, 24B2261), Varad Padhye (R5, 24B2179) · **Repository:** https://github.com/varad-padhye/ME306

This is the design and multi-objective optimisation of a **100 MW Brayton-cycle gas-turbine plant burning hydrogen–natural-gas blends**. Five team members each owned one subsystem, worked at three levels (thermodynamic design, exergy, cost), and the subsystems were combined into one validated cycle model. That model was optimised with **NSGA-II** over **5 objectives** and **6 constraints**, and **one final configuration** was selected using TOPSIS followed by a reasoned trade-off.

📄 **Team report (IEEE format):** [`report/Problem16_Group_Report.pdf`](report/Problem16_Group_Report.pdf)

---

## Contents
1. [Result in one table](#1-result-in-one-table)
2. [Team and roles](#2-team-and-roles)
3. [Repository structure](#3-repository-structure)
4. [Quick start](#4-quick-start)
5. [What the pipeline does, step by step](#5-what-the-pipeline-does-step-by-step)
6. [The integrated model](#6-the-integrated-model)
7. [Optimisation and selection](#7-optimisation-and-selection)
8. [Changing an assumption](#8-changing-an-assumption)
9. [Output files](#9-output-files)
10. [Assumptions beyond the problem statement](#10-assumptions-beyond-the-problem-statement)
11. [Validation](#11-validation)
12. [R3 turbine and reheat package](#12-r3-turbine-and-reheat-package)
13. [Compiling the reports](#13-compiling-the-reports)
14. [Troubleshooting](#14-troubleshooting)
15. [Limitations](#15-limitations)
16. [References](#16-references)

---

## 1. Result in one table

**Selected design:** intercooled + regenerative Brayton cycle, *no reheat*. Pressure ratio **16**, turbine-inlet temperature **1400 °C**, hydrogen **30 % by volume** (11.9 % of fuel energy), regenerator effectiveness **0.85**.

| Metric | NG baseline (plan, uncooled) | NG baseline (with blade cooling) | **Final design** |
|---|---|---|---|
| Net efficiency | 34.67 % | 31.4 % | **40.5 %** |
| Heat rate (kJ/kWh) | 10 384 | 11 454 | **8 885** |
| Second-law efficiency Ψ | 33.4 % | 30.3 % | **39.4 %** |
| LCOE (Rs/kWh) | 10.03 | 10.94 | **11.34** |
| Direct CO₂ (kg/kWh) | 0.583 | 0.643 | **0.439** (−32 %) |
| NOx index (ppm @15 % O₂) | 25.0 | 25.0 | **29.6** (CPCB limit 75) |
| Air / fuel / H₂ flow (kg/s) | 228.6 / 6.01 / 0 | 296.5 / 6.63 / 0 | **237.6 / 4.78 / 0.244** |
| Capital cost (Rs crore) | 400 | 400 | **534** |

**Why this design:**
- **Blade cooling changes the ranking.** Reheat needs a second cooled turbine (about 30 % of the air as coolant in total), so it loses efficiency once cooling is counted.
- **Intercooling pays twice.** Colder compressor delivery (516 K instead of 722 K) cuts the coolant needed from 15 % to 10 %, and leaves more room for regeneration.
- **It beats the runner-up on 4 of 5 objectives.** Against IC+Regen+Reheat it wins on efficiency, exergy destruction, LCOE and CO₂. It loses only on the NOx index, which stays far under the limit.
- **Efficiency is the cheap decarbonisation lever; hydrogen is the expensive one.** The cycle upgrade alone cuts CO₂ by 22 % *and saves money*. The 30 % H₂ blend costs about Rs 39 000 per tonne of CO₂ avoided.
- **Hydrogen share is capped by safety, not thermodynamics.** Efficiency changes by less than 1 point from 0 to 100 % H₂. Flashback (premixer), autoignition and NOx are what limit the blend.

---

## 2. Team and roles

| Role | Member | Subsystem | Core | Exergy | Cost |
|---|---|---|---|---|---|
| **R1** | Vedika Kone (24B2115) | Compressor & intercooling | pressure ratio, intercooler, compressor work | compressor + intercooler | intercooler vs work saved |
| **R2** | Tanvi Gattani (24B2246) | Combustor & fuel blend | H₂ share, excess air, f/a, flame T, NOx index, flashback index | combustion | H₂ combustor premium, fuel, H₂ storage |
| **R3** | Shravanee Kulkarni (24B2206) | Turbine & reheat | TIT, reheat, H₂O-rich gas, material & cooling limits | turbine + reheat combustor | hot section, cooling, reheat hardware |
| **R4** | Dhanvin A. S. (24B2261) | Regenerator & heat recovery | effectiveness, air preheat, T₄ > T₂ rule | regenerator + stack loss | exchanger area vs fuel saved |
| **R5** | Varad Padhye (24B2179) | Integration & fuel supply | full cycle, flows for 100 MW | plant exergy balance, Ψ | LCOE incl. H₂ supply & storage, CO₂/kWh, NSGA-II, TOPSIS |

Each member's subsystem report is in [`team_reports/`](team_reports/).

---

## 3. Repository structure

```
ME306/
├── README.md                     ← this file
├── run_pipeline.py               ← one command regenerates every result, table and figure
├── requirements.txt
├── report/
│   ├── Problem16_Group_Report.tex   ← team report (IEEE two-column style)
│   ├── Problem16_Group_Report.pdf
│   └── meta.tex                     ← author list and repository URL (edit here)
├── r5_integration/               ← integrated model, optimisation, selection (R5)
│   ├── code/
│   │   ├── r5_params.py          ← SHARED PARAMETER FILE: every number, its owner and source
│   │   ├── r5_model.py           ← integrated cycle (R1+R2+R3+R4), cooling, constraints, exergy, LCOE, CO₂
│   │   ├── r5_validate.py        ← reproduces the plan baseline and every R1–R4 hand-off
│   │   ├── r5_nsga2.py           ← NSGA-II (constrained domination, SBX, polynomial mutation)
│   │   ├── r5_run_all.py         ← candidate layouts, sweeps, grid scan, NSGA-II, Pareto set
│   │   ├── r5_select.py          ← TOPSIS (2 normalisations × 5 weight sets), final design, trade-offs, sensitivity
│   │   ├── r5_figures.py         ← main result figures
│   │   ├── r5_group_extras.py    ← subsystem figures, T–s diagram, "why not" and H₂-share tables
│   │   └── r5_make_tables.py     ← LaTeX tables + number macros used by both reports
│   ├── results/                  ← all CSV outputs + summary.json
│   ├── figures/                  ← all PNG figures
│   └── report/                   ← R5 individual report source + generated tables/
├── r3_turbine_reheat/            ← R3's turbine/reheat code, sweeps, figures, data (uses Cantera)
└── team_reports/                 ← R1, R2, R3, R4, R5 subsystem reports (PDF)
```

---

## 4. Quick start

**Requirements:** Python ≥ 3.9 with NumPy, pandas and matplotlib. A LaTeX distribution (TeX Live or MiKTeX) is optional, for compiling the reports.

```bash
git clone https://github.com/varad-padhye/ME306.git
cd ME306
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux/macOS:  source .venv/bin/activate
pip install numpy pandas matplotlib

python run_pipeline.py --quick     # ~15 s: reuses the stored optimisation, regenerates everything else
python run_pipeline.py             # ~10–12 min: full run including the NSGA-II search
python run_pipeline.py --report    # also compiles both PDFs (needs pdflatex)
```

To run a single step, go into `r5_integration/code` and run the script, for example `python r5_validate.py`.

**Evaluate one design interactively:**
```python
# from r5_integration/code
from r5_model import evaluate
r = evaluate(PR=16, TIT=1673.15, x=0.30, ic=1, rh=0, rg=1, eps=0.85)
print(r["eta_net"], r["lcoe"], r["co2"], r["nox"], r["feasible"])
# every state temperature/pressure, flow, exergy item ("Xd: ..."), cost item ("cap: ...")
# and constraint margin ("g: ...", feasible when <= 0) is in the returned dict
```
Arguments: `PR` pressure ratio, `TIT` in K, `x` H₂ volume fraction, `ic`/`rh`/`rg` intercooling/reheat/regeneration on (1) or off (0), `eps` regenerator effectiveness. Pass `o=make_opts(NAME=value)` to override any parameter from `r5_params.py`.

---

## 5. What the pipeline does, step by step

| # | Script | Runtime | What it does | Main outputs |
|---|---|---|---|---|
| 1 | `r5_validate.py` | < 1 s | Runs the integrated code with each teammate's own settings and compares it with the plan baseline, R1's two-stage compressor, R4's regenerator, R3's cooled turbine and R2's 8-configuration table | `results/validation.csv` |
| 2 | `r5_run_all.py` | ~10 min | (a) all 8 layouts at PR 15 / 1400 °C, cooled and uncooled; (b) pressure-ratio and TIT sweeps; (c) a 13 200-point grid scan for constraint statistics; (d) **NSGA-II** for each of the 8 layouts (pop 100 × 150 generations); (e) merges feasible designs and filters the global 5-objective Pareto set | `candidate_configs_*.csv`, `pr_sweep.csv`, `tit_sweep_integrated.csv`, `grid_scan_all.csv`, `nsga2_final_populations.csv`, `feasible_set.csv`, `pareto_front_5obj.csv` |
| 3 | `r5_select.py` | ~5 s | TOPSIS with vector and min-max normalisation × 5 weight sets; pre-stated head-to-head rule between the two equal-weight winners; rounds to an engineering specification and checks feasibility and non-dominance; role trade-offs; exergy balance; LCOE build-up; H₂ price and share sweeps; one-at-a-time sensitivity; selection robustness vs H₂ price | `topsis_selection.csv`, `role_tradeoffs.csv`, `role_candidates_integrated.csv`, `exergy_balance.csv`, `h2_price_sweep.csv`, `h2_share_sweep_final_cycle.csv`, `sensitivity_final.csv`, `selection_robustness.csv`, `summary.json` |
| 4 | `r5_figures.py` | ~3 s | Result figures: candidate layouts, PR sweep, TIT trade-off, exergy balance, 4 Pareto plots, feasibility filter, tornado, H₂ price/share | `figures/fig_*.png` |
| 5 | `r5_make_tables.py` | < 1 s | Writes every LaTeX table and `macros.tex` (named numbers such as `\finEta`) from the results. **No number in the reports is typed by hand.** | `r5_integration/report/tables/*.tex` |
| 6 | `r5_group_extras.py` | ~3 s | Subsystem figures (R1–R4), T–s diagram, "why the other layouts were rejected" table, H₂-share table | `figures/fig_sub_R*.png`, `fig_ts_diagram.png`, `tables/why_not.tex`, `tables/h2share.tex` |

NSGA-II is seeded, so results are reproducible run to run.

---

## 6. The integrated model

### 6.1 State numbering (team master)
```
 air → 1 →[LP comp]→ 1a →[intercooler]→ 1b →[HP comp]→ 2 →[regenerator, cold side]→ 5 →[combustor]→ 3
                                                     │ coolant ψ bled at 2                              │
                                                     └──────────────► mixed into each turbine ◄──────────┘
 3 →[HP turbine]→ m →[reheat combustor]→ r →[LP turbine]→ 4 →[regenerator, hot side]→ 6 → stack 7
```
Optional blocks (intercooler, regenerator, reheat combustor + LP turbine) are on/off: 2³ = 8 layouts, each run as its own case. With no regenerator, 5 ≡ 2 and 6 ≡ 4. With no reheat, the HP turbine expands directly to 4.

### 6.2 Equations (constant cp, h = cp·T, per kg of compressor-inlet air)
- **Compressor (R1):** `T2 = T1[1 + (rp^((γ−1)/γ) − 1)/ηc]`. Intercooled: two equal stages `rs = √(rp/(1−ΔpIC))`, `T1b = T1a − εIC (T1a − T0)`.
- **Combustor (R2):** `f = (cp,g·T3 − cp,a·T5) / (ηb·LHV_blend − cp,g·T3)`, with `LHV_blend = (1−y)·48 + y·120 MJ/kg`, where y is the H₂ mass share. Hot-gas `cp,g(x)` and `γg(x)` come from R2's Cantera table (1.150 → 1.191 kJ/kg K).
- **Turbine (R3):** the polytropic efficiency equivalent to ηt = 0.90. Blade coolant ψ is bled at state 2 and mixed in at mid log-pressure of each turbine. Reheat uses an equal pressure split and reheats to TIT.
- **Blade cooling (R3 relation, web-sourced data):** `φ = (TIT − Tmetal)/(TIT − T2)`, `ψ = B·(cp,g/cp,a)·φ/[ηcool(1−φ)]·h_x`, with Tmetal = 1150 K, ηcool = 0.7, B = 0.075 (15 % at 1400 °C), and h_x the H₂O heat-transfer index (+3.4 % at x = 1).
- **Regenerator (R4):** `Q = ε·Cmin·(T4 − T2)`, `T5 = T2 + Q/Cc`, `T6 = T4 − Q/Ch`, with `UA = NTU(ε, Cr)·Cmin` for counterflow. The regenerator–combustor–turbine coupling is solved by fixed-point iteration on T4 to 10⁻⁷ K.
- **Plant:** `η_net = ηgen·w_net/(f_tot·LHV)`, `ṁ_air = 100 MW/(ηgen·w_net)`.
- **Exergy:** `ψ = cp(T−T0) − T0[cp ln(T/T0) − R ln(p/p0)]`. Fuel exergy uses Szargut ratios (CH₄ 1.0366, H₂ 0.9764). Each component's destruction comes from its own balance, so the plant balance closes to ~10⁻¹³ kJ/kg.
- **LCOE:** `[Capital·(CRF + 0.03) + Fuel]/E` with CRF = 0.1018 (9 %, 25 y) and E = 438 GWh/y. Capital = base Rs 400 cr + intercooler 6.5 % + regenerator ∝ UA + reheat 12.5 % + H₂ combustor premium (0 → 4 → 15 %) + hot-section premium + **H₂ storage** (8 h at Rs 55 000/kg). Fuel is priced at the energy-weighted blend price, so H₂ **supply** is carried in the delivered price.
- **CO₂:** `3.6/η_net × (1−e) × 56.1 g/MJ`, where e is the H₂ energy share. Green H₂ is taken as zero upstream.

### 6.3 Constraint indicators (from R2)
| Constraint | Model |
|---|---|
| NOx ≤ 75 ppm (CPCB, 100–400 MW) | R2's calibrated Zeldovich index (25 ppm at 1790 K primary zone, re-tuned burner). Primary zone `Tpz = 1790 + (TIT − 1673)` K above 1400 °C. Inlet-temperature and reheat-dilution factors fitted to R2's 8-configuration table |
| Flashback index FI ≤ 2.0 | `FI = g_c(x)/g_c(NG)`, critical velocity gradient ∝ S_L²/α (Cantera flame speeds), interpolated between 722 K and 877 K air |
| Premixer autoignition | combustor-inlet air T5 ≤ 1050 K |
| Reheat-combustor autoignition | x ≤ 0.27 / 0.41 / 0.47 at PR 10 / 15 / 20 |
| Regenerator | only if T4 > T2, both terminal approaches ≥ 20 K |
| Firing limit | TIT ≤ 1500 °C |

---

## 7. Optimisation and selection

- **Decision variables:** pressure ratio 8–30, TIT 1300–1500 °C, H₂ share x 0–1 (by volume), regenerator ε 0.50–0.85, with intercooling, reheat and regeneration on/off.
- **Objectives:** max η_net · min exergy destruction (MJ/kWh) · min LCOE · min direct CO₂ · min NOx index.
- **NSGA-II:** written in NumPy (`r5_nsga2.py`) because pymoo was not available in the build environment. It follows Deb et al. (2002) with constrained domination, SBX (η = 15, pc = 0.9), polynomial mutation (η = 20, pm = 1/n), population 100, 150 generations, run once per layout.
- **Result:** 106 539 feasible designs and 9 653 designs in the 5-objective Pareto set. Only intercooled layouts reach the Pareto set.
- **TOPSIS** was run with two normalisations × five weight sets. Vector normalisation favours the low-NOx IC+Regen+Reheat design; min-max normalisation favours IC+Regen in 4 of 5 weight sets.
- **Decision rule (fixed before the comparison):** prefer the candidate that is better on the majority of objectives, provided its NOx stays ≤ 50 ppm. IC+Regen wins on 4 of 5. The rounded design (PR 16, 1400 °C, x 0.30, ε 0.85) is feasible, is dominated by none of the feasible designs, and is selected at every H₂ price from Rs 280 to 400/kg.

---

## 8. Changing an assumption

All inputs live in **`r5_integration/code/r5_params.py`**, each with its owner and source. Examples:

```python
H2_PRICE_KG = 350.0     # Rs/kg green hydrogen
B_COOL = 0.075          # blade-cooling calibration (15 % coolant at 1400 C)
TIT_MAX = 1773.15       # firing-temperature limit (K)
NOX_LIMIT = 75.0        # ppm
DP_RG = 0.02            # regenerator pressure loss per side
```
Edit the value, run `python run_pipeline.py` (full run, because the optimum may move), and recompile the report. Both reports pick up the new numbers automatically through `tables/macros.tex`.

For a quick what-if without re-optimising: `evaluate(..., o=make_opts(H2_PRICE_KG=280))`.

---

## 9. Output files

| File (`r5_integration/results/`) | Content |
|---|---|
| `validation.csv` | integrated model against plan / R1 / R2 / R3 / R4 reference values |
| `candidate_configs_PR15_TIT1400C.csv` | 8 layouts × (x = 0, 0.3) × (cooled, uncooled), with all states, flows, exergy items, costs and constraint margins |
| `pr_sweep.csv`, `tit_sweep_integrated.csv` | sweeps used in the figures |
| `grid_scan_all.csv` | 13 200-point structured scan (feasible and infeasible) |
| `nsga2_final_populations.csv` | final NSGA-II population of each layout |
| `feasible_set.csv` | 20 000-point sample of the feasible designs |
| `pareto_front_5obj.csv` | 5-objective Pareto set with TOPSIS closeness columns |
| `topsis_selection.csv`, `topsis_top_equal.csv` | TOPSIS winners / top designs |
| `role_tradeoffs.csv` | each role's best value vs the final design |
| `role_candidates_integrated.csv` | each teammate's own candidate re-run in the integrated model |
| `exergy_balance.csv` | plant exergy balance (MW, %) for baseline and final |
| `h2_price_sweep.csv`, `h2_share_sweep_final_cycle.csv` | H₂ economics |
| `sensitivity_final.csv`, `selection_robustness.csv` | sensitivity and robustness |
| `summary.json` | key numbers (final design, baselines, counts) |

Column naming: `Xd: <component>` is exergy destruction (kJ/kg air), `cap: <item>` is capital (Rs crore), and `g: <constraint>` is the constraint margin (feasible when ≤ 0).

---

## 10. Assumptions beyond the problem statement

| Item | Value | Basis |
|---|---|---|
| Firing-temperature limit | 1500 °C | G/H-class air-cooled technology (MHI Technical Review) |
| Blade-metal limit; cooling effectiveness | 1150 K; 0.70 | R3; consistent with ~930 °C metal at 1400 °C entry (Cambridge) and CMSX-4 limits |
| Coolant at 1400 °C | 15 % of compressor air | between R3 (12 %) and ~20 % incl. sealing quoted for industrial GTs |
| Intercooler ε; ΔP intercooler / regenerator | 0.85; 2 % / 2 % per side | R1; R4's 1–3 % range |
| NOx limit | 75 ppm @15 % O₂ | CPCB band 100–400 MW (secondary source, to verify against the Gazette) |
| Flashback limit | FI ≤ 2.0 | top of R2's tier-B advanced premixer |
| H₂ storage | Rs 55 000/kg, 8 h | R2 (US DOE Record 13010) |
| Regenerator cost | ∝ UA, Rs 40 cr at 576 kW/K | R4 calibration |
| Hot-section cost | +4 % of base per 100 K above 1400 °C | R3 |
| Upstream CO₂ of hydrogen | 0 (green) | team assumption |

---

## 11. Validation

`python r5_validate.py` checks the integrated code against:
- the plan's Week-2 reference: T2 721.8 K, f 0.0263, T4 944.6 K, w_net 444.1 kJ/kg, η 35.20 % / 34.67 %, heat rate 10 384, LCOE Rs 10.03, exergy closure ~10⁻¹³;
- R1's two-stage compressor: 475.46 / 333.25 / 514.18 K, 349.98 kJ/kg;
- R4's regenerator: 888.84 / 801.76 K, 38.65 MW, 40.03 %, UA 576, 1.172 MW destroyed, LCOE 8.968;
- R2's 8-configuration efficiency and NOx table (all within 0.1 pt / 0.4 ppm);
- R3's cooled turbine (32.17 % vs 32.35 %; R3 additionally rescales gas properties with f through Cantera).

---

## 12. R3 turbine and reheat package

`r3_turbine_reheat/` holds R3's own model (`r3_turbine_reheat.py`), sweeps (`run_r3_sweeps.py`), results and figures. It uses **Cantera** for hot-gas property ratios:
```bash
pip install scipy cantera
cd r3_turbine_reheat && python run_r3_sweeps.py
```
The integrated model does not need Cantera. It uses R2's and R3's tabulated property and heat-transfer ratios directly.

R1's, R2's and R4's code was not part of the shared project folder. Their methods and results are documented in their reports in `team_reports/` and reproduced by `r5_validate.py`.

---

## 13. Compiling the reports

```bash
cd report && pdflatex Problem16_Group_Report.tex && pdflatex Problem16_Group_Report.tex
```
- The team report reads its tables from `../r5_integration/report/tables/` and its figures from `../r5_integration/figures/`.
- Authors and the repository URL are set in `report/meta.tex`.
- The layout imitates IEEE journal style using standard packages (`article`, two-column, `mathptmx`, `titlesec`). The official `IEEEtran.cls` was not available in the build environment. To use it, swap the document class and remove the custom title/section formatting.

Required LaTeX packages: amsmath, booktabs, graphicx, adjustbox, stfloats, enumitem, cite, url, hyperref, titlesec, caption, tikz, lm (for typewriter text).

---

## 14. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: pandas` | `pip install numpy pandas matplotlib` inside your virtual environment |
| `--quick needs stored results` | run `python run_pipeline.py` once without `--quick` |
| Full run is slow | normal: about 120 000 cycle evaluations; use `--quick` after the first run |
| LaTeX `File ... not found` | compile from inside `report/`, so the relative paths resolve |
| Numbers in the PDF did not change after editing parameters | rerun the pipeline (it regenerates `macros.tex`), then compile LaTeX twice |

---

## 15. Limitations
- **Model:** constant-cp (required by the plan); it overstates fuel use by about 2.4 % against Cantera.
- **Cooling:** semi-empirical and calibrated by assumption. Real reheat machines use lower-pressure bleed for the LP turbine, which would soften the reheat penalty.
- **NOx index:** calibrated and relative. The CPCB limit still needs checking against the Gazette.
- **Capital costs:** percentage allowances, with no scale credit for smaller machines.
- **CO₂:** direct emissions only, assuming green H₂. Grey H₂ would remove the benefit of blending.

---

## 16. References
Problem 16 statement and four-week plan (ME 306, 2026); team subsystem reports R1–R4; Heywood (1988); Lefebvre & Ballal (2010); Lewis & von Elbe (1987); Szargut et al. (1988); GRI-Mech 3.0 / Cantera; US DOE storage record 13010; MHI Technical Review (2019); Cambridge Phase-Transformations "Coatings for turbine blades"; Cannon-Muskegon CMSX-4; J. Eng. Gas Turbines Power 10.1115/1.4048452; CEAS Aeronaut. J. 10.1007/s13272-024-00776-0; Horlock et al. (2001); Lienhard (2024); Deb et al., IEEE TEC 6(2), 2002 (NSGA-II); Hwang & Yoon (1981, TOPSIS). The full list is in the report.
