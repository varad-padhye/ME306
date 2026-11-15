"""R5 figures (static PNG for the LaTeX report). Palette: validated reference categorical slots;
hydrogen share uses a single-hue sequential blue ramp."""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)
S = json.load(open(os.path.join(RES, "summary.json")))

CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
BLUES = LinearSegmentedColormap.from_list("seq", ["#cfe1f7", "#2a78d6", "#0d2f5c"])
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                     "savefig.dpi": 200, "savefig.bbox": "tight", "font.family": "DejaVu Sans"})
ORDER = ["Simple", "Reheat", "Regen", "Regen+Reheat", "IC", "IC+Reheat", "IC+Regen", "IC+Regen+Reheat"]


def save(fig, name):
    fig.savefig(os.path.join(FIG, name)); plt.close(fig)


# ---- 1. candidate configurations, cooled vs uncooled (x = 0.3, PR 15, TIT 1400 C)
c = pd.read_csv(os.path.join(RES, "candidate_configs_PR15_TIT1400C.csv"))
c = c[c.x == 0.3]
fig, ax = plt.subplots(1, 4, figsize=(11, 3.1))
for k, (col, lab, sc) in enumerate([("eta_net", "Net efficiency (%)", 100), ("lcoe", "LCOE (Rs/kWh)", 1),
                                    ("co2", "Direct CO$_2$ (kg/kWh)", 1), ("nox", "NOx index (ppm @15% O$_2$)", 1)]):
    y = np.arange(len(ORDER))
    for j, (cool, lab2, colr) in enumerate([(False, "Uncooled (plan model)", CAT[1]), (True, "With blade cooling", CAT[0])]):
        v = [c[(c.config == n) & (c.cooling == cool)][col].values[0] * sc for n in ORDER]
        ax[k].barh(y + (j - 0.5) * 0.38, v, height=0.34, color=colr, label=lab2)
    ax[k].set_yticks(y); ax[k].set_yticklabels(ORDER if k == 0 else [])
    ax[k].invert_yaxis(); ax[k].set_xlabel(lab); ax[k].grid(axis="y", visible=False)
    if col == "nox":
        ax[k].axvline(75, color=INK2, lw=1, ls="--"); ax[k].text(75, -0.9, "CPCB 75", fontsize=7, color=INK2, ha="center")
ax[0].legend(loc="lower center", bbox_to_anchor=(2.3, 1.02), ncol=2)
save(fig, "fig_candidate_configs.png")

# ---- 2. PR sweep (cooled, x 0.3)
p = pd.read_csv(os.path.join(RES, "pr_sweep.csv"))
fig, ax = plt.subplots(figsize=(6.4, 3.6))
for i, n in enumerate(ORDER):
    d = p[p.config == n]
    if "Regen" in n:
        d = d[d.T4_minus_T2 > 20]
    ax.plot(d.PR, 100 * d.eta_net, color=CAT[i], lw=2, label=n)
ax.set_xlabel("Overall pressure ratio"); ax.set_ylabel("Net efficiency (%)")
ax.legend(ncol=2, fontsize=7.5, loc="lower left")
ax.set_title("Cooled cycle, TIT 1400 °C, x = 0.30, ε$_{regen}$ = 0.75 (regenerator only where T$_4$ > T$_2$ + 20 K)", fontsize=8, color=INK2)
save(fig, "fig_pr_sweep.png")

# ---- 3. TIT sweep: cooled vs uncooled + NOx
t = pd.read_csv(os.path.join(RES, "tit_sweep_integrated.csv"))
fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
for cool, colr, lab in ((False, CAT[1], "Uncooled"), (True, CAT[0], "With blade cooling")):
    d = t[t.cooling == cool]
    ax[0].plot(d.TIT - 273.15, 100 * d.eta_net, color=colr, lw=2, label=lab)
d = t[t.cooling]
ax[1].plot(d.TIT - 273.15, d.nox, color=CAT[0], lw=2)
ax[1].axhline(75, color=INK2, ls="--", lw=1); ax[1].text(1500, 78, "CPCB 75 ppm", ha="right", fontsize=7, color=INK2)
ax[0].set_xlabel("Turbine-inlet temperature (°C)"); ax[0].set_ylabel("Net efficiency (%)"); ax[0].legend()
ax[1].set_xlabel("Turbine-inlet temperature (°C)"); ax[1].set_ylabel("NOx index (ppm)")
fig.suptitle("IC + Regen, PR 15, x = 0.30, ε = 0.80", fontsize=8, color=INK2)
save(fig, "fig_tit_tradeoff.png")

# ---- 4. exergy balance stacked bars
e = pd.read_csv(os.path.join(RES, "exergy_balance.csv"))
groups = {"Net electricity": ["net electricity"], "Combustion (main + reheat)": ["combustor", "reheat combustor"],
          "Turbine incl. cooling": ["turbine (incl. cooling)"], "Compressor + intercooler": ["compressor", "intercooler"],
          "Regenerator": ["regenerator"], "Ducts + generator": ["inlet duct", "exhaust duct", "generator"],
          "Stack loss": ["stack (thermal exergy lost)"]}
cases = list(dict.fromkeys(e.case))
fig, ax = plt.subplots(figsize=(8.5, 2.6))
for ci, case in enumerate(cases):
    left = 0
    for gi, (g, items) in enumerate(groups.items()):
        v = e[(e.case == case) & (e.item.isin(items))].pct.sum()
        ax.barh(ci, v, left=left, color=CAT[gi], height=0.6, edgecolor="white", linewidth=1.5,
                label=g if ci == 0 else None)
        if v > 4:
            ax.text(left + v / 2, ci, f"{v:.1f}", ha="center", va="center", fontsize=7, color="white")
        left += v
ax.set_yticks(range(len(cases))); ax.set_yticklabels(cases); ax.invert_yaxis()
ax.set_xlim(0, 100); ax.set_xlabel("% of fuel exergy"); ax.grid(axis="y", visible=False)
ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.45, -0.28))
save(fig, "fig_exergy_balance.png")

# ---- 5. Pareto plots
fs = pd.read_csv(os.path.join(RES, "feasible_set.csv"))
pf = pd.read_csv(os.path.join(RES, "pareto_front_5obj.csv"))
fin = S["final"]; base = S["baseline_cooled"]
pairs = [("eta_net", 100, "Net efficiency (%)", "lcoe", 1, "LCOE (Rs/kWh)"),
         ("lcoe", 1, "LCOE (Rs/kWh)", "co2", 1, "Direct CO$_2$ (kg/kWh)"),
         ("eta_net", 100, "Net efficiency (%)", "nox", 1, "NOx index (ppm @15% O$_2$)"),
         ("Xd_MJ_kWh", 1, "Total exergy destruction (MJ/kWh)", "lcoe", 1, "LCOE (Rs/kWh)")]
fig, axs = plt.subplots(2, 2, figsize=(10, 7.4))
for ax, (xc, xs, xl, yc, ys, yl) in zip(axs.flat, pairs):
    ax.scatter(fs[xc] * xs, fs[yc] * ys, s=4, color="#c9c8c2", alpha=0.5, lw=0, label="Feasible designs", rasterized=True)
    sc = ax.scatter(pf[xc] * xs, pf[yc] * ys, c=pf.x, cmap=BLUES, vmin=0, vmax=1, s=14, edgecolor="white",
                    linewidth=0.4, label="5-objective Pareto set")
    ax.scatter(base[xc] * xs, base[yc] * ys, marker="s", s=60, color=CAT[1], edgecolor="white", lw=1.5, label="Cooled NG baseline", zorder=5)
    ax.scatter(fin[xc] * xs, fin[yc] * ys, marker="*", s=260, color=CAT[7], edgecolor="white", lw=1.5, label="R5 final design", zorder=6)
    ax.set_xlabel(xl); ax.set_ylabel(yl)
axs[0, 0].legend(fontsize=7, loc="upper left")
cb = fig.colorbar(sc, ax=axs, shrink=0.6, pad=0.02); cb.set_label("Hydrogen share by volume, x")
save(fig, "fig_pareto_fronts.png")

# ---- 6. feasibility filter
sc_ = S["scan"]
labs = [k for k in sc_["violations"] if sc_["violations"][k] > 0]
v_all = [sc_["violations"][k] for k in labs]; v_only = [sc_["sole_violation"][k] for k in labs]
idx = np.argsort(v_all)
fig, ax = plt.subplots(figsize=(7, 2.8))
y = np.arange(len(labs))
ax.barh(y + 0.19, np.array(v_all)[idx], height=0.36, color=CAT[0], label="Designs violating")
ax.barh(y - 0.19, np.array(v_only)[idx], height=0.36, color=CAT[1], label="Violating only this constraint")
ax.set_yticks(y); ax.set_yticklabels(np.array(labs)[idx]); ax.grid(axis="y", visible=False)
ax.set_xlabel(f"Number of grid designs (of {sc_['n']}; {sc_['n_feasible']} feasible)"); ax.legend(loc="lower right", fontsize=7)
save(fig, "fig_feasibility.png")

# ---- 7. tornado
t = pd.read_csv(os.path.join(RES, "sensitivity_final.csv"))
b0 = fin["lcoe"]
t["span"] = (t.lcoe_hi - t.lcoe_lo).abs()
t = t.sort_values("span")
fig, ax = plt.subplots(figsize=(7, 3.6))
y = np.arange(len(t))
lo_ = t.lcoe_lo - b0; hi_ = t.lcoe_hi - b0
ax.barh(y, lo_, color=CAT[0], height=0.6, label="Low value of parameter")
ax.barh(y, hi_, color=CAT[1], height=0.6, label="High value of parameter")
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(y); ax.set_yticklabels(t.parameter); ax.grid(axis="y", visible=False)
ax.set_xlabel(f"Change in LCOE from Rs {b0:.2f}/kWh (Rs/kWh)"); ax.legend(fontsize=7, loc="lower right")
save(fig, "fig_tornado.png")

# ---- 8. hydrogen price + share
h = pd.read_csv(os.path.join(RES, "h2_price_sweep.csv"))
xs_ = pd.read_csv(os.path.join(RES, "h2_share_sweep_final_cycle.csv"))
fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
for i, case in enumerate(["cooled NG baseline", "same cycle, NG only", "final design", "same cycle, x = 1 (if feasible)"]):
    d = h[h.case == case]
    ax[0].plot(d.h2_price, d.lcoe, color=[INK2, CAT[2], CAT[0], CAT[6]][i], lw=2, ls=["--", "-", "-", ":"][i], label=case)
ax[0].axvspan(280, 400, color="#efeee9", zorder=0); ax[0].legend(fontsize=7, loc="upper left")
ax[0].set_xlabel("Green hydrogen price (Rs/kg)  [shaded: PS range]"); ax[0].set_ylabel("LCOE (Rs/kWh)")
ok = xs_.feasible.astype(bool)
for k, (col, lab) in enumerate([("lcoe", "LCOE (Rs/kWh)"), ("co2", "Direct CO$_2$ (kg/kWh)")]):
    a_ = ax[k + 1]
    a_.plot(xs_.x, xs_[col], color=CAT[0], lw=2, label="final cycle")
    a_.plot(xs_.x[~ok], xs_[col][~ok], "o", ms=4, color=CAT[7], label="blend infeasible")
    a_.axvline(fin["x"], color=INK2, lw=1, ls=":"); a_.set_xlabel("Hydrogen share by volume, x"); a_.set_ylabel(lab)
ax[1].legend(fontsize=7, loc="upper left")
save(fig, "fig_h2_price_share.png")
print("figures written")
