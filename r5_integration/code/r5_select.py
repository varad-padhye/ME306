"""
R5 selection stage: TOPSIS (two normalisations x five weight sets) on the 5-objective Pareto set,
reasoned final choice, role trade-offs, exergy balance, LCOE build-up, hydrogen-price and
one-at-a-time sensitivity.  Reads the outputs of r5_run_all.py.
"""
import os, json
import numpy as np
import pandas as pd
from r5_model import evaluate, make_opts, BASE_OPTS
import r5_params as P

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
summary = json.load(open(os.path.join(RES, "summary.json")))
pareto = pd.read_csv(os.path.join(RES, "pareto_front_5obj.csv"))
grid = pd.read_csv(os.path.join(RES, "grid_scan_all.csv"))
feas = pd.concat([grid[grid.feasible], pd.read_csv(os.path.join(RES, "feasible_set.csv")), pareto],
                 ignore_index=True).drop_duplicates(subset=["config", "PR", "TIT", "x", "eps"]).reset_index(drop=True)
F = np.column_stack([-feas.eta_net, feas.Xd_MJ_kWh, feas.lcoe, feas.co2, feas.nox]).astype(float)
nouc = make_opts(COOLING=False)
b_unc = evaluate(15, P.TIT_BASE, 0.0, o=nouc)
b_cool = evaluate(15, P.TIT_BASE, 0.0)


def objvec(r):
    return np.array([-r["eta_net"], r["Xd_MJ_kWh"], r["lcoe"], r["co2"], r["nox"]])


def short(r):
    keep = ["config", "PR", "TIT", "x", "e_share", "eps", "feasible", "eta_th", "eta_net", "heat_rate",
            "w_net", "w_c", "m_air", "m_fuel", "m_h2", "T2", "T5", "T4", "T6", "psi_cool", "Tpz", "FI", "nox",
            "co2", "lcoe", "capex", "fuel_cr", "Xd_total", "Xd_MJ_kWh", "psi2nd", "X_stack", "X_fuel",
            "UA", "A_rg", "approach", "ic", "rh", "rg"]
    d = {k: r.get(k, np.nan) for k in keep}
    d.update({k: v for k, v in r.items() if k.startswith(("Xd: ", "cap: ", "g: "))})
    return d


# ======================================================== 5. TOPSIS
WEIGHTS = {"Equal weights": [0.2, 0.2, 0.2, 0.2, 0.2],
           "Cost-led": [0.15, 0.15, 0.40, 0.15, 0.15],
           "Climate-led": [0.15, 0.15, 0.15, 0.40, 0.15],
           "Efficiency-led": [0.40, 0.15, 0.15, 0.15, 0.15],
           "Safety/NOx-led": [0.15, 0.15, 0.15, 0.15, 0.40]}


def topsis(df, w, norm="vector"):
    M = np.column_stack([df.eta_net, df.Xd_MJ_kWh, df.lcoe, df.co2, df.nox]).astype(float)
    benefit = np.array([True, False, False, False, False])
    if norm == "vector":
        N = M / np.sqrt((M ** 2).sum(axis=0))
    else:                                   # min-max (range) normalisation
        N = (M - M.min(0)) / (M.max(0) - M.min(0))
    V = N * np.asarray(w)
    best = np.where(benefit, V.max(0), V.min(0))
    worst = np.where(benefit, V.min(0), V.max(0))
    dp = np.sqrt(((V - best) ** 2).sum(1)); dn = np.sqrt(((V - worst) ** 2).sum(1))
    return dn / (dp + dn)


tops = []
for norm in ("vector", "min-max"):
    for name, w in WEIGHTS.items():
        c = topsis(pareto, w, norm)
        pareto[f"C_{norm}_{name}"] = c
        i = int(np.argmax(c))
        d = pareto.iloc[i]
        tops.append(dict(normalisation=norm, weights=name, config=d.config, PR=d.PR, TIT_C=d.TIT - 273.15,
                         x=d.x, e_share=d.e_share, eps=d.eps, closeness=c[i], eta_net=d.eta_net, lcoe=d.lcoe,
                         co2=d.co2, nox=d.nox, Xd=d.Xd_MJ_kWh))
tops = pd.DataFrame(tops)
tops.to_csv(os.path.join(RES, "topsis_selection.csv"), index=False)
pareto.to_csv(os.path.join(RES, "pareto_front_5obj.csv"), index=False)

# ======================================================== 6. reasoned final choice between the two
# equal-weight TOPSIS winners, then a rounded engineering specification
A = pareto.loc[pareto["C_vector_Equal weights"].idxmax()]
B = pareto.loc[pareto["C_min-max_Equal weights"].idxmax()]
fa, fb = objvec(A), objvec(B)
better_B = int((fb < fa).sum())
# rule: prefer the candidate that is better on the majority of the five objectives, provided its NOx
# index keeps at least a 1/3 margin to the CPCB limit (<= 50 ppm, the stricter 400 MW band)
s = B if (better_B >= 3 and B.nox <= 50.0) else A
summary["head_to_head"] = dict(vector=dict(A[["config", "PR", "TIT", "x", "eps", "eta_net", "Xd_MJ_kWh", "lcoe", "co2", "nox"]]),
                               minmax=dict(B[["config", "PR", "TIT", "x", "eps", "eta_net", "Xd_MJ_kWh", "lcoe", "co2", "nox"]]),
                               minmax_better_on=better_B, chosen="min-max" if s is B else "vector")
spec = dict(PR=float(np.round(s.PR)), TIT=float(np.round((s.TIT - 273.15) / 5) * 5 + 273.15),
            x=float(np.round(s.x / 0.05) * 0.05), ic=int(s.ic), rh=int(s.rh), rg=int(s.rg),
            eps=float(np.round(s.eps / 0.05) * 0.05) if s.rg else 0.0)
final = evaluate(spec["PR"], spec["TIT"], spec["x"], spec["ic"], spec["rh"], spec["rg"], spec["eps"])
if not final["feasible"]:      # fall back to the exact optimum if rounding breaks a constraint
    spec = dict(PR=s.PR, TIT=s.TIT, x=s.x, ic=int(s.ic), rh=int(s.rh), rg=int(s.rg), eps=s.eps)
    final = evaluate(**{k: spec[k] for k in ("PR", "TIT", "x", "ic", "rh", "rg", "eps")})
alt = evaluate(A.PR, A.TIT, A.x, int(A.ic), int(A.rh), int(A.rg), A.eps)
summary["runner_up"] = short(alt)
summary["topsis_exact"] = short(evaluate(s.PR, s.TIT, s.x, int(s.ic), int(s.rh), int(s.rg), s.eps))
summary["final_spec"] = spec
summary["final"] = {k: (float(v) if isinstance(v, (np.floating, float, int, np.integer, bool)) else v)
                    for k, v in final.items()}
# is the rounded design dominated by anything in the feasible set?
fv = objvec(final)
summary["final_dominated_by"] = int((np.all(F <= fv, axis=1) & np.any(F < fv, axis=1)).sum())
fin_opts = dict(PR=spec["PR"], TIT=spec["TIT"], x=spec["x"], ic=spec["ic"], rh=spec["rh"], rg=spec["rg"],
                eps=spec["eps"])

# ======================================================== 7. what is sacrificed vs each role's best
def best(col, fn):
    i = feas[col].idxmin() if fn == "min" else feas[col].idxmax()
    return feas.loc[i]


role_rows = []
pct = lambda d, cols: sum(d[c] for c in cols) / d["X_fuel"] * 100
C_COMP, C_COMB = ["Xd: compressor", "Xd: intercooler"], ["Xd: combustor", "Xd: reheat combustor"]
C_TURB = ["Xd: turbine (incl. cooling)"]
feas["comp_frac"] = pct(feas, C_COMP); feas["comb_frac"] = pct(feas, C_COMB)
feas["turb_frac"] = pct(feas, C_TURB); feas["stack_frac"] = feas.X_stack / feas.X_fuel * 100
for role, metric, col, fn, fval, unit in [
    ("R1 Compressor & IC", "Compressor + intercooler exergy destruction", "comp_frac", "min", pct(final, C_COMP), "% fuel exergy"),
    ("R2 Combustor & blend", "NOx index", "nox", "min", final["nox"], "ppm"),
    ("R2 Combustor & blend", "Combustion exergy destruction (all combustors)", "comb_frac", "min", pct(final, C_COMB), "% fuel exergy"),
    ("R3 Turbine & reheat", "Specific net work (machine size)", "w_net", "max", final["w_net"], "kJ/kg air"),
    ("R3 Turbine & reheat", "Turbine exergy destruction incl. cooling", "turb_frac", "min", pct(final, C_TURB), "% fuel exergy"),
    ("R4 Regenerator", "Stack exergy loss", "stack_frac", "min", final["X_stack"] / final["X_fuel"] * 100, "% fuel exergy"),
    ("R5 Integration", "Net efficiency", "eta_net", "max", final["eta_net"], "-"),
    ("R5 Integration", "Total exergy destruction", "Xd_MJ_kWh", "min", final["Xd_MJ_kWh"], "MJ/kWh"),
    ("R5 Integration", "LCOE", "lcoe", "min", final["lcoe"], "Rs/kWh"),
    ("R5 Integration", "Direct CO2", "co2", "min", final["co2"], "kg/kWh")]:
    b = best(col, fn)
    role_rows.append(dict(role=role, metric=metric, unit=unit, best_value=b[col], best_design=
                          f"{b.config}, PR {b.PR:.1f}, TIT {b.TIT-273.15:.0f} C, x {b.x:.2f}" +
                          (f", eps {b.eps:.2f}" if b.rg else ""), selected=fval))
pd.DataFrame(role_rows).to_csv(os.path.join(RES, "role_tradeoffs.csv"), index=False)

# each role's own submitted candidate, run through the integrated (cooled) model
cands = [("R1 candidate: IC, PR 15, NG", (15, P.TIT_BASE, 0.0, 1, 0, 0, 0.0)),
         ("R2 stand-in: IC+Regen+Reheat, PR 15, x 0.40", (15, P.TIT_BASE, 0.40, 1, 1, 1, 0.70)),
         ("R3 best: simple, TIT 1500 C, NG", (15, 1773.15, 0.0, 0, 0, 0, 0.0)),
         ("R4 candidate: Regen eps 0.75, PR 15, NG", (15, P.TIT_BASE, 0.0, 0, 0, 1, 0.75)),
         ("Cooled NG baseline", (15, P.TIT_BASE, 0.0, 0, 0, 0, 0.0)),
         ("R5 final design", tuple(fin_opts[k] for k in ("PR", "TIT", "x", "ic", "rh", "rg", "eps")))]
rows = []
for name, a in cands:
    r = evaluate(*a)
    d = short(r); d["case"] = name
    d["violations"] = "; ".join(k[3:] for k, v in r.items() if k.startswith("g: ") and v > 0) or "none"
    rows.append(d)
pd.DataFrame(rows).to_csv(os.path.join(RES, "role_candidates_integrated.csv"), index=False)

# ======================================================== 8. exergy balances
rows = []
for name, r in [("NG baseline (uncooled, reference)", b_unc), ("NG baseline (cooled)", b_cool), ("R5 final design", final)]:
    for k, v in r.items():
        if k.startswith("Xd: "):
            rows.append(dict(case=name, item=k[4:], kJ_per_kg_air=v, MW=v * r["m_air"] / 1000, pct=100 * v / r["X_fuel"]))
    rows.append(dict(case=name, item="stack (thermal exergy lost)", kJ_per_kg_air=r["X_stack"], MW=r["X_stack"] * r["m_air"] / 1000, pct=100 * r["X_stack"] / r["X_fuel"]))
    rows.append(dict(case=name, item="net electricity", kJ_per_kg_air=r["W_el"], MW=r["W_el"] * r["m_air"] / 1000, pct=100 * r["W_el"] / r["X_fuel"]))
    rows.append(dict(case=name, item="fuel exergy in", kJ_per_kg_air=r["X_fuel"], MW=r["X_fuel"] * r["m_air"] / 1000, pct=100.0))
    rows.append(dict(case=name, item="closure", kJ_per_kg_air=r["closure"], MW=0, pct=0))
pd.DataFrame(rows).to_csv(os.path.join(RES, "exergy_balance.csv"), index=False)

# ======================================================== 9. LCOE build-up + H2 price + sensitivity
def lcoe_parts(r):
    E = P.P_NET * 8760 * P.LOAD_FACTOR
    crf = P.crf()
    capex_noS = r["capex"] - r["cap: H2 storage"]
    return {"capital recovery": capex_noS * crf * 1e7 / E, "O&M": capex_noS * P.OM_FRAC * 1e7 / E,
            "H2 storage": r["cap: H2 storage"] * (crf + P.OM_FRAC) * 1e7 / E,
            "fuel": r["fuel_cr"] * 1e7 / E}


summary["lcoe_parts"] = {"NG baseline (uncooled)": lcoe_parts(b_unc), "NG baseline (cooled)": lcoe_parts(b_cool),
                         "R5 final design": lcoe_parts(final)}
rows = []
for price in np.arange(250, 451, 10):
    o = make_opts(H2_PRICE_KG=float(price))
    for lab, xx in (("final design", fin_opts["x"]), ("same cycle, NG only", 0.0), ("same cycle, x = 1 (if feasible)", 1.0)):
        r = evaluate(fin_opts["PR"], fin_opts["TIT"], xx, fin_opts["ic"], fin_opts["rh"], fin_opts["rg"], fin_opts["eps"], o=o)
        rows.append(dict(h2_price=price, case=lab, lcoe=r["lcoe"], co2=r["co2"], feasible=r["feasible"]))
    r = evaluate(15, P.TIT_BASE, 0.0, o=o)
    rows.append(dict(h2_price=price, case="cooled NG baseline", lcoe=r["lcoe"], co2=r["co2"], feasible=True))
pd.DataFrame(rows).to_csv(os.path.join(RES, "h2_price_sweep.csv"), index=False)

# hydrogen-share sweep on the final cycle
rows = []
for xx in np.round(np.linspace(0, 1, 21), 2):
    r = evaluate(fin_opts["PR"], fin_opts["TIT"], xx, fin_opts["ic"], fin_opts["rh"], fin_opts["rg"], fin_opts["eps"])
    d = short(r); rows.append(d)
pd.DataFrame(rows).to_csv(os.path.join(RES, "h2_share_sweep_final_cycle.csv"), index=False)

# tornado (one at a time) on LCOE / CO2 / efficiency of the final design
SENS = [("H2 price Rs 280 / 400 per kg", dict(H2_PRICE_KG=280.0), dict(H2_PRICE_KG=400.0)),
        ("NG price -20 % / +20 %", dict(NG_PRICE=680.0), dict(NG_PRICE=1020.0)),
        ("Load factor 60 % / 40 %", dict(LOAD_FACTOR=0.60), dict(LOAD_FACTOR=0.40)),
        ("Plant cost Rs 3.5 / 5 cr per MW", dict(BASE_CAPEX=350.0, C_IC=0.065 * 350, C_RH=0.125 * 350),
         dict(BASE_CAPEX=500.0, C_IC=0.065 * 500, C_RH=0.125 * 500)),
        ("Discount rate 8 % / 10 %", dict(DISC=0.08), dict(DISC=0.10)),
        ("O&M 3 % / 4 % of capital", dict(OM_FRAC=0.03), dict(OM_FRAC=0.04)),
        ("H2 storage Rs 38k / 85k per kg", dict(H2_STORE_RS_KG=38000.0), dict(H2_STORE_RS_KG=85000.0)),
        ("Cooling air 10 % / 20 % at 1400 C", dict(B_COOL=0.05), dict(B_COOL=0.10)),
        ("Regenerator dP 1 % / 3 % per side", dict(DP_RG=0.01), dict(DP_RG=0.03)),
        ("Intercooler dP 1 % / 3 %", dict(DP_IC=0.01), dict(DP_IC=0.03)),
        ("Turbine efficiency 0.92 / 0.88", dict(ETA_T=0.92), dict(ETA_T=0.88)),
        ("Compressor efficiency 0.89 / 0.85", dict(ETA_C=0.89), dict(ETA_C=0.85))]
rows = []
for lab, lo_, hi_ in SENS:
    rl = evaluate(**fin_opts, o=make_opts(**lo_)); rh_ = evaluate(**fin_opts, o=make_opts(**hi_))
    rows.append(dict(parameter=lab, lcoe_lo=rl["lcoe"], lcoe_hi=rh_["lcoe"], eta_lo=rl["eta_net"],
                     eta_hi=rh_["eta_net"], co2_lo=rl["co2"], co2_hi=rh_["co2"], feas_lo=rl["feasible"],
                     feas_hi=rh_["feasible"]))
pd.DataFrame(rows).to_csv(os.path.join(RES, "sensitivity_final.csv"), index=False)

# robustness of the SELECTION: re-run TOPSIS on the Pareto set with H2 price and storage changed
rows = []
for price in (280.0, 350.0, 400.0):
    o = make_opts(H2_PRICE_KG=price)
    pp = pareto.copy()
    pp["lcoe"] = [evaluate(r.PR, r.TIT, r.x, int(r.ic), int(r.rh), int(r.rg), r.eps, o=o)["lcoe"] for r in pp.itertuples()]
    for norm in ("vector", "min-max"):
        c = topsis(pp, WEIGHTS["Equal weights"], norm); i = int(np.argmax(c)); d = pp.iloc[i]
        rows.append(dict(h2_price=price, normalisation=norm, config=d.config, PR=d.PR, TIT_C=d.TIT - 273.15,
                         x=d.x, eps=d.eps, lcoe=d.lcoe, co2=d.co2))
pd.DataFrame(rows).to_csv(os.path.join(RES, "selection_robustness.csv"), index=False)

with open(os.path.join(RES, "summary.json"), "w") as fh:
    json.dump(summary, fh, indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))
print(json.dumps({k: summary[k] for k in ("final_spec", "final_dominated_by", "head_to_head")}, default=str, indent=1))
print(tops.to_string())
