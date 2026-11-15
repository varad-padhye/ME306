"""Generate LaTeX tables + number macros for the R5 report directly from the results files."""
import os, json
import numpy as np
import pandas as pd
from r5_model import evaluate, make_opts
import r5_params as P

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
TAB = os.path.join(HERE, "..", "report", "tables")
os.makedirs(TAB, exist_ok=True)
S = json.load(open(os.path.join(RES, "summary.json")))
sp = S["final_spec"]
FIN = evaluate(sp["PR"], sp["TIT"], sp["x"], sp["ic"], sp["rh"], sp["rg"], sp["eps"])
BC = evaluate(15, P.TIT_BASE, 0.0)
BU = evaluate(15, P.TIT_BASE, 0.0, o=make_opts(COOLING=False))
NGc = evaluate(sp["PR"], sp["TIT"], 0.0, sp["ic"], sp["rh"], sp["rg"], sp["eps"])
RU = S["runner_up"]


def w(name, body):
    open(os.path.join(TAB, name), "w").write(body)


def esc(s):
    return str(s).replace("%", r"\%").replace("&", r"\&").replace("_", r"\_").replace("CO2", r"CO$_2$").replace("H2", r"H$_2$")


# ---------------------------------------------------------- macros
M = {}
def m(k, v): M[k] = v
m("finPR", f"{FIN['PR']:.0f}"); m("finTITC", f"{FIN['TIT']-273.15:.0f}"); m("finTITK", f"{FIN['TIT']:.0f}")
m("finX", f"{FIN['x']:.2f}"); m("finE", f"{100*FIN['e_share']:.1f}"); m("finEps", f"{FIN['eps']:.2f}")
m("finEta", f"{100*FIN['eta_net']:.1f}"); m("finEtaTh", f"{100*FIN['eta_th']:.1f}"); m("finHR", f"{FIN['heat_rate']:,.0f}")
m("finLCOE", f"{FIN['lcoe']:.2f}"); m("finCO", f"{FIN['co2']:.3f}"); m("finNOx", f"{FIN['nox']:.1f}")
m("finFI", f"{FIN['FI']:.2f}"); m("finXd", f"{FIN['Xd_MJ_kWh']:.2f}"); m("finPsi", f"{100*FIN['psi2nd']:.1f}")
m("finMair", f"{FIN['m_air']:.1f}"); m("finMfuel", f"{FIN['m_fuel']:.2f}"); m("finMh", f"{FIN['m_h2']:.3f}")
m("finCapex", f"{FIN['capex']:.0f}"); m("finWnet", f"{FIN['w_net']:.0f}"); m("finCool", f"{100*FIN['psi_cool']:.1f}")
m("finTfive", f"{FIN['T5']:.0f}"); m("finTsix", f"{FIN['T6']:.0f}"); m("finTfour", f"{FIN['T4']:.0f}"); m("finTtwo", f"{FIN['T2']:.0f}")
m("finArea", f"{FIN['A_rg']:,.0f}"); m("finQrg", f"{FIN['Q_rg_MW']:.1f}")
m("finStore", f"{FIN['m_h2']*3600*8/1000:.1f}")
m("bcEta", f"{100*BC['eta_net']:.1f}"); m("bcLCOE", f"{BC['lcoe']:.2f}"); m("bcCO", f"{BC['co2']:.3f}"); m("bcNOx", f"{BC['nox']:.1f}")
m("bcCool", f"{100*BC['psi_cool']:.1f}"); m("bcXd", f"{BC['Xd_MJ_kWh']:.2f}")
m("buEta", f"{100*BU['eta_net']:.2f}"); m("buLCOE", f"{BU['lcoe']:.2f}"); m("buCO", f"{BU['co2']:.3f}")
m("ngLCOE", f"{NGc['lcoe']:.2f}"); m("ngCO", f"{NGc['co2']:.3f}")
dL, dC = FIN["lcoe"] - BC["lcoe"], BC["co2"] - FIN["co2"]
m("dCOpct", f"{100*dC/BC['co2']:.0f}"); m("dLpct", f"{100*dL/BC['lcoe']:.1f}")
m("abateTot", f"{1000*dL/dC:,.0f}")
m("abateHtwo", f"{1000*(FIN['lcoe']-NGc['lcoe'])/(NGc['co2']-FIN['co2']):,.0f}")
m("abateCycle", f"{1000*(NGc['lcoe']-BC['lcoe'])/(BC['co2']-NGc['co2']):,.0f}")
m("dCOcyclepct", f"{100*(BC['co2']-NGc['co2'])/BC['co2']:.0f}")
m("ruEta", f"{100*RU['eta_net']:.1f}"); m("ruLCOE", f"{RU['lcoe']:.2f}"); m("ruCO", f"{RU['co2']:.3f}"); m("ruNOx", f"{RU['nox']:.1f}")
m("ruXd", f"{RU['Xd_MJ_kWh']:.2f}"); m("ruPR", f"{RU['PR']:.0f}"); m("ruTITC", f"{RU['TIT']-273.15:.0f}"); m("ruX", f"{RU['x']:.2f}")
m("nScan", f"{S['scan']['n']:,}"); m("nScanFeas", f"{S['scan']['n_feasible']:,}")
m("nFeas", f"{S['n_feasible_total']:,}"); m("nPareto", f"{S['n_pareto']:,}")
m("nDom", str(S["final_dominated_by"]))
m("noxK", f"{1000*__import__('r5_model').NOX_K_TIN:.2f}"); m("noxN", f"{__import__('r5_model').NOX_N_SHARE:.2f}")
h = pd.read_csv(os.path.join(RES, "h2_price_sweep.csv"))
f_ = h[h.case == "final design"].set_index("h2_price").lcoe
m("lcoeLo", f"{f_[280]:.2f}"); m("lcoeHi", f"{f_[400]:.2f}")
be = h[h.case == "cooled NG baseline"].set_index("h2_price").lcoe
diff = (f_ - be)
cross = np.interp(0, diff.values, diff.index.values) if (diff.min() < 0 < diff.max()) else np.nan
m("parityPrice", f"{cross:.0f}")
lp = S["lcoe_parts"]["R5 final design"]
m("fuelShare", f"{100*lp['fuel']/sum(lp.values()):.0f}")
with open(os.path.join(TAB, "macros.tex"), "w") as fh:
    for k, v in M.items():
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

# ---------------------------------------------------------- validation table
v = pd.read_csv(os.path.join(RES, "validation.csv"))
body = ["\\begin{tabular}{llrr}\\toprule Check & Quantity & Reference & R5 model\\\\\\midrule"]
prev = None
for r in v.itertuples():
    if r.check == "R2 config table" and "NOx" in r.quantity:
        continue
    lab = r.check if r.check != prev else ""
    if r.check != prev and prev is not None:
        body.append("\\addlinespace")
    body.append(f"{esc(lab)} & {esc(r.quantity)} & {r.reference} & {r.r5_model}\\\\")
    prev = r.check
body.append("\\bottomrule\\end{tabular}")
w("validation.tex", "\n".join(body))

# ---------------------------------------------------------- candidate configs table
c = pd.read_csv(os.path.join(RES, "candidate_configs_PR15_TIT1400C.csv"))
c = c[c.x == 0.3]
order = ["Simple", "Reheat", "Regen", "Regen+Reheat", "IC", "IC+Reheat", "IC+Regen", "IC+Regen+Reheat"]
body = ["\\begin{tabular}{lrrrrrrrrl}\\toprule",
        " & \\multicolumn{2}{c}{$\\eta_{net}$ (\\%)} & \\multicolumn{2}{c}{LCOE (Rs/kWh)} & \\multicolumn{5}{c}{With cooling}\\\\",
        "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-10}",
        "Configuration & uncooled & cooled & uncooled & cooled & CO$_2$ & NOx & $\\psi_{cool}$ & $\\Psi$ (\\%) & Feasible?\\\\\\midrule"]
for n in order:
    a = c[(c.config == n) & (~c.cooling)].iloc[0]; b = c[(c.config == n) & (c.cooling)].iloc[0]
    viol = [k[3:] for k in c.columns if k.startswith("g: ") and b[k] > 0]
    body.append(f"{n} & {100*a.eta_net:.1f} & {100*b.eta_net:.1f} & {a.lcoe:.2f} & {b.lcoe:.2f} & {b.co2:.3f} & {b.nox:.1f} & {b.psi_cool:.3f} & {100*b.psi2nd:.1f} & {'yes' if b.feasible else esc('no: ' + ', '.join(viol))}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("candidates.tex", "\n".join(body))

# ---------------------------------------------------------- TOPSIS table
t = pd.read_csv(os.path.join(RES, "topsis_selection.csv"))
body = ["\\begin{tabular}{llllrrrrrrrr}\\toprule Normalisation & Weights & Configuration & PR & TIT (\\textdegree C) & $x$ & $\\varepsilon$ & $C^*$ & $\\eta_{net}$ (\\%) & LCOE & CO$_2$ & NOx\\\\\\midrule"]
for r in t.itertuples():
    body.append(f"{r.normalisation} & {r.weights} & {r.config} & {r.PR:.1f} & {r.TIT_C:.0f} & {r.x:.2f} & {r.eps:.2f} & {r.closeness:.3f} & {100*r.eta_net:.1f} & {r.lcoe:.2f} & {r.co2:.3f} & {r.nox:.1f}\\\\")
    if r.Index == 4:
        body.append("\\addlinespace")
body.append("\\bottomrule\\end{tabular}")
w("topsis.tex", "\n".join(body))

# ---------------------------------------------------------- head-to-head
hh = S["head_to_head"]; A, B = hh["vector"], hh["minmax"]
rows = [("Configuration", A["config"], B["config"], ""), ("Pressure ratio", f"{A['PR']:.0f}", f"{B['PR']:.0f}", ""),
        ("TIT (\\textdegree C)", f"{A['TIT']-273.15:.0f}", f"{B['TIT']-273.15:.0f}", ""),
        ("H$_2$ share $x$ (vol.)", f"{A['x']:.2f}", f"{B['x']:.2f}", ""), ("Regenerator $\\varepsilon$", f"{A['eps']:.2f}", f"{B['eps']:.2f}", "")]
for k, lab, sc, fmt, hib in [("eta_net", "Net efficiency (\\%)", 100, "{:.1f}", True), ("Xd_MJ_kWh", "Exergy destruction (MJ/kWh)", 1, "{:.2f}", False),
                             ("lcoe", "LCOE (Rs/kWh)", 1, "{:.2f}", False), ("co2", "Direct CO$_2$ (kg/kWh)", 1, "{:.3f}", False),
                             ("nox", "NOx index (ppm)", 1, "{:.1f}", False)]:
    bw = (B[k] > A[k]) if hib else (B[k] < A[k])
    rows.append((lab, fmt.format(A[k] * sc), fmt.format(B[k] * sc), "B" if bw else "A"))
body = ["\\begin{tabular}{lccc}\\toprule & A: vector-TOPSIS winner & B: min-max-TOPSIS winner & Better\\\\\\midrule"]
body += [f"{a} & {b} & {c_} & {d}\\\\" for a, b, c_, d in rows]
body.append("\\bottomrule\\end{tabular}")
w("headtohead.tex", "\n".join(body))

# ---------------------------------------------------------- final design state table
F = FIN
o = P
rs = np.sqrt(F["PR"] / (1 - P.DP_IC))
p1 = P.P0 * 0.99
states = [("0", "Ambient", P.T0, P.P0, "--"), ("1", "Compressor inlet (after 1\\% loss)", F["T1"], F["p1"], f"{F['m_air']:.1f}"),
          ("1a", "LP compressor exit", F["T1a"], rs * p1, f"{F['m_air']:.1f}"),
          ("1b", "Intercooler exit", F["T1b"], rs * p1 * (1 - P.DP_IC), f"{F['m_air']:.1f}"),
          ("2", "HP compressor exit / coolant bleed", F["T2"], F["p2"], f"{F['m_air']:.1f}"),
          ("5", "Regenerator air out = combustor inlet", F["T5"], F["p5"], f"{F['m_air']*(1-F['psi_cool']):.1f}"),
          ("3", "Combustor exit = turbine inlet", F["T3"], F["p3"], f"{F['m_air']*(1-F['psi_cool'])+F['m_fuel']:.1f}"),
          ("4", "Turbine exit (after coolant mixing)", F["T4"], F["p4"], f"{F['m_air']+F['m_fuel']:.1f}"),
          ("6", "Regenerator gas out", F["T6"], F["p6"], f"{F['m_air']+F['m_fuel']:.1f}"),
          ("7", "Stack", F["T6"], P.P0, f"{F['m_air']+F['m_fuel']:.1f}")]
body = ["\\begin{tabular}{cllll}\\toprule State & Location & $T$ (K) & $p$ (bar) & $\\dot m$ (kg/s)\\\\\\midrule"]
body += [f"{a} & {b} & {c_:.1f} & {d:.3f} & {e}\\\\" for a, b, c_, d, e in states]
body.append("\\bottomrule\\end{tabular}")
w("final_states.tex", "\n".join(body))

# ---------------------------------------------------------- final performance comparison
def col(r):
    return [f"{r['config']}", f"{r['PR']:.0f}", f"{r['TIT']-273.15:.0f}", f"{r['x']:.2f} ({100*r['e_share']:.1f}\\%)",
            f"{r['eps']:.2f}" if r["rg"] else "--", f"{100*r['psi_cool']:.1f}", f"{r['w_net']:.0f}", f"{100*r['eta_th']:.1f}",
            f"{100*r['eta_net']:.1f}", f"{r['heat_rate']:,.0f}", f"{r['m_air']:.1f}", f"{r['m_fuel']:.2f}", f"{r['m_h2']:.3f}",
            f"{r['T5']:.0f}", f"{r['T6']:.0f}", f"{r['Xd_MJ_kWh']:.2f}", f"{100*r['psi2nd']:.1f}", f"{r['capex']:.0f}",
            f"{r['lcoe']:.2f}", f"{r['co2']:.3f}", f"{r['nox']:.1f}", f"{r['FI']:.2f}"]
labels = ["Configuration", "Pressure ratio", "TIT (\\textdegree C)", "H$_2$ share $x$ (energy share)", "Regenerator $\\varepsilon$",
          "Blade coolant (\\% of air)", "Net work (kJ/kg air)", "Cycle efficiency (\\%)", "Net efficiency (\\%)", "Heat rate (kJ/kWh)",
          "Air flow (kg/s)", "Fuel flow (kg/s)", "of which H$_2$ (kg/s)", "Combustor inlet $T_5$ (K)", "Stack $T$ (K)",
          "Exergy destruction (MJ/kWh)", "Second-law efficiency $\\Psi$ (\\%)", "Capital cost (Rs crore)", "LCOE (Rs/kWh)",
          "Direct CO$_2$ (kg/kWh)", "NOx index (ppm @15\\% O$_2$)", "Flashback index (--)"]
cols = [col(BU), col(BC), col(NGc), col(FIN)]
body = ["\\begin{tabular}{lrrrr}\\toprule & NG baseline & NG baseline & Final cycle & \\textbf{R5 final}\\\\ & (plan, uncooled) & (cooled) & on NG only & \\textbf{design}\\\\\\midrule"]
for i, lab in enumerate(labels):
    body.append(f"{lab} & " + " & ".join(cc[i] for cc in cols[:3]) + f" & \\textbf{{{cols[3][i]}}}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("final_perf.tex", "\n".join(body))

# ---------------------------------------------------------- capex + LCOE build-up
body = ["\\begin{tabular}{lrl}\\toprule Capital item & Rs crore & Basis\\\\\\midrule"]
basis = {"base plant": "Rs 4 cr/MW [PS]", "hot section (TIT)": "+4\\%/100 K above 1400\\textdegree C [R3]",
         "intercooler": "6.5\\% of base [R1]", "regenerator": "$\\propto UA$, Rs 40 cr at $UA$ = 576 kW/K [R4]",
         "reheat": "12.5\\% of base [R3]", "H2 combustor premium": "0--4--15\\% of base vs $x$ [R2]",
         "H2 storage": "8 h full-load H$_2$ at Rs 55,000/kg [R2]"}
for k, b in basis.items():
    body.append(f"{esc(k)} & {FIN['cap: ' + k]:.1f} & {b}\\\\")
body.append(f"\\midrule Total & {FIN['capex']:.1f} & \\\\\\bottomrule\\end{{tabular}}")
w("capex.tex", "\n".join(body))
body = ["\\begin{tabular}{lrrr}\\toprule Rs/kWh & NG baseline (plan) & NG baseline (cooled) & R5 final design\\\\\\midrule"]
parts = S["lcoe_parts"]
for k in ["capital recovery", "O&M", "H2 storage", "fuel"]:
    body.append(f"{esc(k)} & " + " & ".join(f"{parts[c][k]:.2f}" for c in ["NG baseline (uncooled)", "NG baseline (cooled)", "R5 final design"]) + "\\\\")
body.append("\\midrule LCOE & " + " & ".join(f"{sum(parts[c].values()):.2f}" for c in ["NG baseline (uncooled)", "NG baseline (cooled)", "R5 final design"]) + "\\\\")
body.append(f"Direct CO$_2$ (kg/kWh) & {BU['co2']:.3f} & {BC['co2']:.3f} & {FIN['co2']:.3f}\\\\\\bottomrule\\end{{tabular}}")
w("lcoe_parts.tex", "\n".join(body))

# ---------------------------------------------------------- exergy balance table
e = pd.read_csv(os.path.join(RES, "exergy_balance.csv"))
cases = list(dict.fromkeys(e.case))
items = ["fuel exergy in", "net electricity", "combustor", "reheat combustor", "turbine (incl. cooling)", "compressor", "intercooler",
         "regenerator", "inlet duct", "exhaust duct", "generator", "stack (thermal exergy lost)", "closure"]
body = ["\\begin{tabular}{l" + "rr" * len(cases) + "}\\toprule",
        " & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{c_}}}" for c_ in cases) + "\\\\",
        "".join(f"\\cmidrule(lr){{{2+2*i}-{3+2*i}}}" for i in range(len(cases))),
        "Item" + " & MW & \\%" * len(cases) + "\\\\\\midrule"]
for it in items:
    vals = []
    for c_ in cases:
        r = e[(e.case == c_) & (e.item == it)].iloc[0]
        vals += [f"{r.MW:.2f}" if it != "closure" else f"{r.kJ_per_kg_air:.0e}", f"{r.pct:.1f}" if it != "closure" else "--"]
    body.append(f"{esc(it)} & " + " & ".join(vals) + "\\\\")
    if it in ("net electricity",):
        body.append("\\midrule")
body.append("\\bottomrule\\end{tabular}")
w("exergy.tex", "\n".join(body))

# ---------------------------------------------------------- role tables
r_ = pd.read_csv(os.path.join(RES, "role_tradeoffs.csv"))
body = ["\\begin{tabular}{p{2.6cm}p{3.6cm}rp{5.2cm}r}\\toprule Role & Metric & Role-best & Design achieving it & Final design\\\\\\midrule"]
for r in r_.itertuples():
    sc = 100 if r.metric == "Net efficiency" else 1
    fm = "{:.3f}" if r.unit == "kg/kWh" else "{:.1f}" if sc == 100 or "%" in r.unit or r.unit in ("ppm",) else "{:.2f}"
    if r.unit in ("kJ/kg air", "K"):
        fm = "{:.0f}"
    unit = "\\%" if sc == 100 else esc(r.unit)
    body.append(f"{esc(r.role)} & {esc(r.metric)} ({unit}) & {fm.format(r.best_value*sc)} & {esc(r.best_design)} & {fm.format(r.selected*sc)}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("roles.tex", "\n".join(body))
rc = pd.read_csv(os.path.join(RES, "role_candidates_integrated.csv"))
body = ["\\begin{tabular}{p{5.0cm}rrrrrp{3.2cm}}\\toprule Case (run through the cooled integrated model) & $\\eta_{net}$ (\\%) & LCOE & CO$_2$ & NOx & FI & Constraint violations\\\\\\midrule"]
for r in rc.itertuples():
    body.append(f"{esc(r.case)} & {100*r.eta_net:.1f} & {r.lcoe:.2f} & {r.co2:.3f} & {r.nox:.1f} & {r.FI:.2f} & {esc(r.violations)}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("role_cands.tex", "\n".join(body))

# ---------------------------------------------------------- sensitivity + robustness
sdf = pd.read_csv(os.path.join(RES, "sensitivity_final.csv"))
sdf["span"] = (sdf.lcoe_hi - sdf.lcoe_lo).abs(); sdf = sdf.sort_values("span", ascending=False)
body = ["\\begin{tabular}{lrrrrrr}\\toprule Parameter (low / high) & \\multicolumn{2}{c}{LCOE (Rs/kWh)} & \\multicolumn{2}{c}{$\\eta_{net}$ (\\%)} & \\multicolumn{2}{c}{CO$_2$ (kg/kWh)}\\\\ & low & high & low & high & low & high\\\\\\midrule"]
for r in sdf.itertuples():
    body.append(f"{esc(r.parameter)} & {r.lcoe_lo:.2f} & {r.lcoe_hi:.2f} & {100*r.eta_lo:.1f} & {100*r.eta_hi:.1f} & {r.co2_lo:.3f} & {r.co2_hi:.3f}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("sensitivity.tex", "\n".join(body))
rb = pd.read_csv(os.path.join(RES, "selection_robustness.csv"))
body = ["\\begin{tabular}{rllrrrrr}\\toprule H$_2$ price (Rs/kg) & Normalisation & Configuration & PR & TIT (\\textdegree C) & $x$ & $\\varepsilon$ & LCOE\\\\\\midrule"]
for r in rb.itertuples():
    body.append(f"{r.h2_price:.0f} & {r.normalisation} & {r.config} & {r.PR:.0f} & {r.TIT_C:.0f} & {r.x:.2f} & {r.eps:.2f} & {r.lcoe:.2f}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("robustness.tex", "\n".join(body))

# ---------------------------------------------------------- feasibility table
sc_ = S["scan"]
body = ["\\begin{tabular}{lrr}\\toprule Constraint & Designs violating & Violating only this one\\\\\\midrule"]
for k in sc_["violations"]:
    body.append(f"{esc(k)} & {sc_['violations'][k]:,} & {sc_['sole_violation'][k]:,}\\\\")
body.append(f"\\midrule Feasible / total & \\multicolumn{{2}}{{r}}{{{sc_['n_feasible']:,} / {sc_['n']:,}}}\\\\")
fb = sc_["feasible_by_config"]
body.append("\\bottomrule\\end{tabular}")
w("feasibility.tex", "\n".join(body))
body = ["\\begin{tabular}{lrrr}\\toprule Configuration & Feasible & Scanned & Pareto members\\\\\\midrule"]
for n in order:
    body.append(f"{n} & {fb['sum'][n]:,} & {fb['count'][n]:,} & {S['pareto_by_config'].get(n, 0):,}\\\\")
body.append("\\bottomrule\\end{tabular}")
w("feas_config.tex", "\n".join(body))
print("tables written:", sorted(os.listdir(TAB)))
print(M)
