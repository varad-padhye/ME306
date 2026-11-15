"""
Extra figures and tables for the IEEE-format GROUP report:
  - subsystem figures for R1 (compression/intercooling), R2 (blend, NOx, flashback), R3 (cooling),
    R4 (regenerator effectiveness, area, pressure loss)
  - 'why not the alternatives' table (best design of every configuration)
  - hydrogen-share choice table on the final cycle
Run after r5_select.py.
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, NullFormatter
from r5_model import evaluate, make_opts, fuel, coolant
import r5_params as P

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
TAB = os.path.join(HERE, "..", "report", "tables")
S = json.load(open(os.path.join(RES, "summary.json")))
sp = S["final_spec"]
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK2, GRID = "#52514e", "#e6e5e1"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                     "savefig.dpi": 220, "savefig.bbox": "tight", "font.family": "DejaVu Sans"})
W1 = 3.45  # IEEE single-column width (in)


def save(fig, n):
    fig.subplots_adjust(wspace=0.42)
    fig.savefig(os.path.join(FIG, n)); plt.close(fig)


# ------------------------------------------------ R1: compressor work vs PR, single vs intercooled
o = make_opts(COOLING=False, DP_IC=0.0)
PR = np.arange(6, 31, 1.0)
fig, ax = plt.subplots(1, 2, figsize=(2 * W1, 2.3))
wc1 = [evaluate(p, P.TIT_BASE, 0, o=o)["w_c"] for p in PR]
ax[0].plot(PR, wc1, color=INK2, lw=2, label="single stage")
for i, e in enumerate([0.5, 0.7, 0.85]):
    oo = make_opts(COOLING=False, DP_IC=0.0, EPS_IC=e)
    ax[0].plot(PR, [evaluate(p, P.TIT_BASE, 0, ic=True, o=oo)["w_c"] for p in PR], color=CAT[i], lw=2, label=f"intercooled, ε = {e}")
ax[0].set_xlabel("Overall pressure ratio"); ax[0].set_ylabel("Compressor work (kJ/kg air)"); ax[0].legend(fontsize=6.5)
T2a = [evaluate(p, P.TIT_BASE, 0, o=o)["T2"] for p in PR]
T2b = [evaluate(p, P.TIT_BASE, 0, ic=True, o=o)["T2"] for p in PR]
ax[1].plot(PR, [coolant(P.TIT_BASE, t, 0, P) * 100 for t in T2a], color=INK2, lw=2, label="single stage")
ax[1].plot(PR, [coolant(P.TIT_BASE, t, 0, P) * 100 for t in T2b], color=CAT[2], lw=2, label="intercooled, ε = 0.85")
ax[1].set_xlabel("Overall pressure ratio"); ax[1].set_ylabel("Blade coolant at 1400 °C (% of air)"); ax[1].legend(fontsize=6.5)
save(fig, "fig_sub_R1.png")

# ------------------------------------------------ R2: blend energy share, NOx and flashback vs x
x = np.linspace(0, 1, 101)
fig, ax = plt.subplots(1, 3, figsize=(2 * W1, 2.2))
ax[0].plot(x, [100 * fuel(v, P)["e"] for v in x], color=CAT[0], lw=2)
ax[0].plot([0, 1], [0, 100], color=INK2, lw=0.8, ls=":")
ax[0].set_xlabel("H$_2$ share by volume, x"); ax[0].set_ylabel("H$_2$ share of fuel energy (%)")
xs1 = np.array([0, .1, .2, .3, .4, .5, .65, .8, 1.0])
s1 = np.array([25.0, 27.3, 30.1, 34.0, 39.2, 46.6, 66.1, 111.5, 410.7])
ax[1].semilogy(xs1, s1, color=CAT[1], lw=2, marker="o", ms=3, label="S1 hardware unchanged")
ax[1].semilogy(P.NOX_H2_X, P.NOX_H2_F * 25, color=CAT[0], lw=2, marker="o", ms=3, label="S2 re-tuned (adopted)")
ax[1].axhline(75, color=INK2, ls="--", lw=0.8); ax[1].text(0.02, 80, "CPCB 75 ppm", fontsize=6, color=INK2)
ax[1].set_xlabel("H$_2$ share by volume, x"); ax[1].set_ylabel("NOx index (ppm @15% O$_2$)"); ax[1].legend(fontsize=6)
ax[2].semilogy(P.FI_X_722, P.FI_722, color=CAT[0], lw=2, marker="o", ms=3, label="air at 722 K")
ax[2].semilogy(P.FI_X_877, P.FI_877, color=CAT[1], lw=2, marker="o", ms=3, label="air at 877 K (regen.)")
ax[2].axhline(2.0, color=INK2, ls="--", lw=0.8); ax[2].text(0.02, 2.15, "tier-B limit 2.0", fontsize=6, color=INK2)
ax[2].set_xlabel("H$_2$ share by volume, x"); ax[2].set_ylabel("Flashback index (–)"); ax[2].legend(fontsize=6)
for a_ in ax[1:]:
    a_.yaxis.set_major_formatter(ScalarFormatter()); a_.yaxis.set_minor_formatter(NullFormatter())
ax[1].set_yticks([25, 50, 75, 100, 200, 400]); ax[2].set_yticks([1, 2, 5, 10])
save(fig, "fig_sub_R2.png")

# ------------------------------------------------ R3: coolant + efficiency vs TIT, simple vs reheat
T = np.arange(1573.15, 1773.2, 10)
fig, ax = plt.subplots(1, 2, figsize=(2 * W1, 2.3))
for i, (lab, kw) in enumerate([("Simple", {}), ("Reheat", dict(rh=1)), ("IC+Regen", dict(ic=1, rg=1, eps=0.85))]):
    r = [evaluate(15, t, 0.0, **kw) for t in T]
    ax[0].plot(T - 273.15, [100 * q["psi_cool"] for q in r], color=CAT[i], lw=2, label=lab)
    ax[1].plot(T - 273.15, [100 * q["eta_net"] for q in r], color=CAT[i], lw=2, label=lab + " (cooled)")
    ru = [evaluate(15, t, 0.0, o=make_opts(COOLING=False), **kw) for t in T]
    ax[1].plot(T - 273.15, [100 * q["eta_net"] for q in ru], color=CAT[i], lw=1, ls="--")
ax[0].set_xlabel("Turbine-inlet temperature (°C)"); ax[0].set_ylabel("Total blade coolant (% of air)"); ax[0].legend(fontsize=6.5)
ax[1].set_xlabel("Turbine-inlet temperature (°C)"); ax[1].set_ylabel("Net efficiency (%)"); ax[1].legend(fontsize=6, title="dashed = uncooled", title_fontsize=6)
save(fig, "fig_sub_R3.png")

# ------------------------------------------------ R4: effectiveness sweep (cooled, IC+Regen PR16 x0.3) + dp
E = np.linspace(0.5, 0.9, 41)
fig, ax = plt.subplots(1, 3, figsize=(2 * W1, 2.2))
for i, dp in enumerate([0.0, 0.02, 0.03]):
    r = [evaluate(sp["PR"], sp["TIT"], sp["x"], 1, 0, 1, e, o=make_opts(DP_RG=dp)) for e in E]
    ax[0].plot(E, [100 * q["eta_net"] for q in r], color=CAT[i], lw=2, label=f"ΔP = {100*dp:.0f} % per side")
    ax[2].plot(E, [q["lcoe"] for q in r], color=CAT[i], lw=2)
    if dp == 0.02:
        ax[1].plot(E, [q["A_rg"] / 1000 for q in r], color=CAT[1], lw=2)
for a_ in ax:
    a_.axvline(0.85, color=INK2, lw=0.8, ls=":"); a_.set_xlabel("Regenerator effectiveness ε")
ax[0].set_ylabel("Net efficiency (%)"); ax[0].legend(fontsize=6)
ax[1].set_ylabel("Surface area (10$^3$ m$^2$, U = 50 W/m$^2$K)"); ax[2].set_ylabel("LCOE (Rs/kWh)")
save(fig, "fig_sub_R4.png")

# ------------------------------------------------ table: best design of every configuration (why not chosen)
grid = pd.read_csv(os.path.join(RES, "grid_scan_all.csv"))
feas = pd.concat([grid[grid.feasible], pd.read_csv(os.path.join(RES, "feasible_set.csv")),
                  pd.read_csv(os.path.join(RES, "pareto_front_5obj.csv"))], ignore_index=True)
M = np.column_stack([feas.eta_net, feas.Xd_MJ_kWh, feas.lcoe, feas.co2, feas.nox]).astype(float)
N = (M - M.min(0)) / (M.max(0) - M.min(0))
V = N * 0.2
best = np.where([1, 0, 0, 0, 0], V.max(0), V.min(0)); worst = np.where([1, 0, 0, 0, 0], V.min(0), V.max(0))
feas["C"] = np.sqrt(((V - worst) ** 2).sum(1)) / (np.sqrt(((V - best) ** 2).sum(1)) + np.sqrt(((V - worst) ** 2).sum(1)))
REASON = {"Simple": "lowest efficiency; 26\\% of fuel exergy lost in stack",
          "Reheat": "two cooled turbines (30\\% coolant); worst efficiency",
          "Regen": "regeneration limited by hot compressor delivery and 15\\% coolant",
          "Regen+Reheat": "combustor inlet near 1050 K autoignition limit; cooling penalty",
          "IC": "no exhaust-heat recovery; stack loss stays high",
          "IC+Reheat": "lowest NOx, but cooled LP turbine and no heat recovery: $\\eta$ 9 points below selected",
          "IC+Regen+Reheat": "runner-up: lower NOx, but worse $\\eta$, LCOE, CO$_2$, exergy; reheat H$_2$ autoignition risk",
          "IC+Regen": "\\textbf{selected} (best on 4 of 5 objectives)"}
order = ["Simple", "Reheat", "Regen", "Regen+Reheat", "IC", "IC+Reheat", "IC+Regen+Reheat", "IC+Regen"]
body = ["\\begin{tabular}{@{}lrrrrrrp{2.9cm}@{}}\\toprule Config. & PR & TIT & $\\eta$ (\\%) & LCOE & CO$_2$ & NOx & Verdict\\\\\\midrule"]
for n in order:
    sub = feas[(feas.config == n) & ((feas.x - 0.30).abs() < 0.005)]
    d = sub.sort_values("C", ascending=False).iloc[0]
    if n == "IC+Regen":                       # show the selected (rounded) design itself
        d = pd.Series(evaluate(sp["PR"], sp["TIT"], sp["x"], 1, 0, 1, sp["eps"]))
    body.append(f"{n} & {d.PR:.0f} & {d.TIT-273.15:.0f} & {100*d.eta_net:.1f} & {d.lcoe:.2f} & {d.co2:.3f} & {d.nox:.0f} & {REASON[n]}\\\\")
body.append("\\bottomrule\\end{tabular}")
open(os.path.join(TAB, "why_not.tex"), "w").write("\n".join(body))

# ------------------------------------------------ table: hydrogen share on the final cycle
body = ["\\begin{tabular}{@{}rrrrrrl@{}}\\toprule $x$ & $e$ (\\%) & $\\eta$ (\\%) & LCOE & CO$_2$ & NOx & FI \\\\\\midrule"]
for xv in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]:
    r = evaluate(sp["PR"], sp["TIT"], xv, 1, 0, 1, sp["eps"])
    fi = f"{r['FI']:.2f}" + ("" if r["feasible"] else " (fails)")
    bold = (lambda s: f"\\textbf{{{s}}}") if abs(xv - sp["x"]) < 1e-9 else (lambda s: s)
    body.append(" & ".join(bold(v) for v in [f"{xv:.1f}", f"{100*r['e_share']:.1f}", f"{100*r['eta_net']:.2f}",
                                             f"{r['lcoe']:.2f}", f"{r['co2']:.3f}", f"{r['nox']:.1f}", fi]) + "\\\\")
body.append("\\bottomrule\\end{tabular}")
open(os.path.join(TAB, "h2share.tex"), "w").write("\n".join(body))
print("group extras done")

# ------------------------------------------------ T-s diagram: NG baseline vs final design (constant cp)
def s_air(T, p): return P.CP_A * np.log(T / P.T0) - P.R_A * np.log(p / P.P0)
def s_gas(T, p, cp, R): return cp * np.log(T / P.T0) - R * np.log(p / P.P0)
def isobar(ax, Ta, sa, Tb, sb, cp, **kw):
    s = np.linspace(sa, sb, 40); ax.plot(s, Ta * np.exp((s - sa) / cp), **kw)
fig, ax = plt.subplots(figsize=(W1, 2.8))
from r5_model import gas_props
for lab, r, col in [("NG baseline (cooled)", evaluate(15, P.TIT_BASE, 0.0), CAT[1]),
                    ("Final design", evaluate(sp["PR"], sp["TIT"], sp["x"], 1, 0, 1, sp["eps"]), CAT[0])]:
    cp, g, R = gas_props(r["x"], P)
    pts = []
    s1 = s_air(r["T1"], r["p1"])
    if r["ic"]:
        rs = np.sqrt(r["PR"] / (1 - P.DP_IC)); p1a = rs * r["p1"]; p1b = p1a * (1 - P.DP_IC)
        s1a, s1b = s_air(r["T1a"], p1a), s_air(r["T1b"], p1b)
        ax.plot([s1, s1a], [r["T1"], r["T1a"]], color=col, lw=1.6)
        isobar(ax, r["T1a"], s1a, r["T1b"], s1b, P.CP_A, color=col, lw=1.6)
        ax.plot([s1b, s_air(r["T2"], r["p2"])], [r["T1b"], r["T2"]], color=col, lw=1.6)
        for T_, s_, n_ in [(r["T1a"], s1a, "1a"), (r["T1b"], s1b, "1b")]:
            ax.annotate(n_, (s_, T_), fontsize=6, color=col, xytext=(3, -6), textcoords="offset points")
    else:
        ax.plot([s1, s_air(r["T2"], r["p2"])], [r["T1"], r["T2"]], color=col, lw=1.6)
    s2 = s_air(r["T2"], r["p2"]); s5 = s_air(r["T5"], r["p5"])
    s3 = s_gas(r["T3"], r["p3"], cp, R) - s_gas(r["T5"], r["p5"], cp, R) + s5
    s4 = s3 + (s_gas(r["T4"], r["p4"], cp, R) - s_gas(r["T3"], r["p3"], cp, R))
    s6 = s4 + (s_gas(r["T6"], r["p6"], cp, R) - s_gas(r["T4"], r["p4"], cp, R))
    if r["rg"]:
        isobar(ax, r["T2"], s2, r["T5"], s5, P.CP_A, color=col, lw=1.6)
    isobar(ax, r["T5"], s5, r["T3"], s3, cp, color=col, lw=1.6, label=lab)
    ax.plot([s3, s4], [r["T3"], r["T4"]], color=col, lw=1.6)
    isobar(ax, r["T4"], s4, r["T6"], s6, cp, color=col, lw=1.6, ls="-" if r["rg"] else ":")
    isobar(ax, r["T6"], s6, r["T1"], s1, cp, color=col, lw=0.8, ls=":")
    for T_, s_, n_ in [(r["T1"], s1, "1"), (r["T2"], s2, "2"), (r["T3"], s3, "3"), (r["T4"], s4, "4")] + \
                      ([(r["T5"], s5, "5"), (r["T6"], s6, "6")] if r["rg"] else []):
        ax.plot(s_, T_, "o", ms=3, color=col)
        ax.annotate(n_, (s_, T_), fontsize=6.5, color=col, xytext=(3, 3) if r["ic"] else (-9, -9), textcoords="offset points")
ax.set_xlabel("Specific entropy relative to dead state, s (kJ/kg K)"); ax.set_ylabel("Temperature (K)")
ax.legend(fontsize=6.5, loc="upper left")
save(fig, "fig_ts_diagram.png")
print("T-s done")
