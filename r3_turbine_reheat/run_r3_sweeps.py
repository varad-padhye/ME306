"""R3 sweeps: TIT, reheat split, hydrogen share, cost, regen interaction, sensitivity.
Run:  python3 run_r3_sweeps.py     (writes CSVs to ./results and PNGs to ./figures)"""
import os, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dataclasses import replace
from r3_turbine_reheat import P, evaluate, fuel_blend, x_from_energy_share

os.makedirs("results", exist_ok=True); os.makedirs("figures", exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "figure.dpi": 130})
C = {"ref": "#6b7280", "simple": "#1f6feb", "reheat": "#d9480f", "regen": "#2b8a3e", "gold": "#b8860b"}
T3_LIM_K = 1773.0       # R3 firing-temperature limit (H-class assumption, 1,500 C)
COOL_LIM = 0.25         # R3 limit: total coolant <= 25 % of compressor air (assumption)
base = P()

def row(tag, p):
    o = evaluate(p)
    if not o["feasible"]:
        return dict(case=tag, feasible=False)
    keep = ["T3", "T5", "T_exit", "x1", "x2", "s_hp", "w_net", "eta_th", "eta_net", "f_tot",
            "m_air", "m_fuel", "Xd_turb", "Xd_reheat", "X_exit", "X_fuel", "Xd_turb_MW",
            "Xd_reheat_MW", "X_exit_MW", "capex_cr", "capex_hot_cr", "capex_reheat_cr",
            "LCOE", "co2_kg_kwh", "cp", "gam", "y_h2o", "h_index", "e_share", "heat_rate"]
    d = {k: float(o[k]) for k in keep}
    d.update(case=tag, feasible=True, x_h2=p.x_h2, reheat=p.reheat, cooling=p.cooling,
             regen=p.regen_eff, PR=p.PR)
    d["coolant_total"] = d["x1"] + d["x2"]
    d["within_limits"] = (d["T3"] <= T3_LIM_K + 1e-6) and (d["coolant_total"] <= COOL_LIM)
    return d

# ---------------------------------------------------------------- 1. TIT sweep (NG)
cfgs = {"Simple, no cooling (team reference)": dict(cooling=False),
        "Simple, cooled": dict(),
        "Reheat, no cooling": dict(cooling=False, reheat=True),
        "Reheat, cooled": dict(reheat=True)}
T_grid = np.arange(1473, 1874, 25.0)
rows = []
for name, kw in cfgs.items():
    for T in T_grid:
        r = row(name, replace(base, T3=T, **kw)); r["config"] = name; rows.append(r)
tit = pd.DataFrame(rows); tit.to_csv("results/tit_sweep.csv", index=False)

# cost-vs-work gained (at the SAME air flow as baseline plant, 228.6 kg/s)
ref = tit[(tit.config.str.startswith("Simple, no")) & (tit.T3 == 1673)].iloc[0]
m_ref = ref.m_air
tit["dW_MW_at_ref_flow"] = (tit.w_net - ref.w_net) * m_ref * 0.985 / 1000.0
tit["dCapex_cr"] = tit.capex_cr - ref.capex_cr
tit["Rs_per_extra_kW"] = np.where(tit.dW_MW_at_ref_flow > 0.5,
                                  tit.dCapex_cr * 1e7 / (tit.dW_MW_at_ref_flow * 1000), np.nan)
tit.to_csv("results/tit_sweep.csv", index=False)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
sty = {"Simple, no cooling (team reference)": (C["ref"], "--"), "Simple, cooled": (C["simple"], "-"),
       "Reheat, no cooling": (C["reheat"], "--"), "Reheat, cooled": (C["reheat"], "-")}
for name, (c, ls) in sty.items():
    d = tit[tit.config == name]
    ax[0].plot(d.T3 - 273.15, d.eta_th * 100, color=c, ls=ls, lw=2, label=name)
    ax[1].plot(d.T3 - 273.15, d.w_net, color=c, ls=ls, lw=2, label=name)
for a in ax:
    a.axvline(1400, color="k", lw=.8, ls=":"); a.axvline(T3_LIM_K - 273.15, color="crimson", lw=1.2)
    a.set_xlabel("Turbine-inlet temperature (°C)")
ax[0].text(T3_LIM_K - 273.15 - 5, ax[0].get_ylim()[0] + .3, "R3 limit\n1,500 °C", color="crimson", ha="right", fontsize=8)
ax[0].text(1403, ax[0].get_ylim()[0] + .3, "baseline", fontsize=8)
ax[0].set_ylabel("Cycle thermal efficiency (%)"); ax[1].set_ylabel("Net work (kJ/kg air)")
ax[0].legend(fontsize=8, frameon=False)
fig.suptitle("Turbine-inlet temperature: efficiency and specific work (natural gas, PR 15, no regeneration)", fontsize=10)
fig.tight_layout(); fig.savefig("figures/fig1_tit_sweep.png"); plt.close(fig)

# exergy vs TIT
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for name in ["Simple, cooled", "Reheat, cooled"]:
    d = tit[tit.config == name]; c, ls = sty[name]
    ax[0].plot(d.T3 - 273.15, d.Xd_turb, color=c, lw=2, label=f"Turbine – {name.split(',')[0].lower()}")
    if "Reheat" in name:
        ax[0].plot(d.T3 - 273.15, d.Xd_reheat, color=C["gold"], lw=2, label="Reheat combustor")
ax[0].set_ylabel("Exergy destroyed (kJ/kg air)"); ax[0].legend(fontsize=8, frameon=False)
for name in ["Simple, no cooling (team reference)", "Simple, cooled", "Reheat, cooled"]:
    d = tit[tit.config == name]; c, ls = sty[name]
    ax[1].plot(d.T3 - 273.15, (d.Xd_turb + d.Xd_reheat) / d.X_fuel * 100, color=c, ls=ls, lw=2, label=name)
ax[1].set_ylabel("R3 exergy destruction (% of fuel exergy)"); ax[1].legend(fontsize=8, frameon=False)
for a in ax: a.set_xlabel("Turbine-inlet temperature (°C)")
fig.suptitle("Exergy destroyed in R3 components vs turbine-inlet temperature", fontsize=10)
fig.tight_layout(); fig.savefig("figures/fig2_exergy_tit.png"); plt.close(fig)

# ---------------------------------------------------------------- 2. Reheat split
rows = []
for cool in (False, True):
    for s in np.arange(0.20, 0.801, 0.02):
        r = row("split", replace(base, reheat=True, cooling=cool, hp_share=s)); r["hp_share"] = s; r["cooled"] = cool; rows.append(r)
spl = pd.DataFrame(rows); spl.to_csv("results/reheat_split_sweep.csv", index=False)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for cool, c, lab in [(False, C["ref"], "no cooling"), (True, C["reheat"], "cooled")]:
    d = spl[spl.cooled == cool]
    ax[0].plot(d.hp_share, d.w_net, color=c, lw=2, label=lab)
    ax[1].plot(d.hp_share, d.eta_th * 100, color=c, lw=2, label=lab)
    i = d.w_net.idxmax(); ax[0].plot(d.loc[i, "hp_share"], d.loc[i, "w_net"], "o", color=c)
ax[0].set_ylabel("Net work (kJ/kg air)"); ax[1].set_ylabel("Thermal efficiency (%)")
for a in ax: a.set_xlabel("HP-turbine share of total expansion (log-pressure)"); a.legend(frameon=False, fontsize=8)
fig.suptitle("Reheat pressure split at 1,400 °C (reheat to 1,400 °C): the optimum is near an equal split", fontsize=10)
fig.tight_layout(); fig.savefig("figures/fig3_reheat_split.png"); plt.close(fig)

# reheat temperature sweep (HP at 1,400 C)
rows = []
for T5 in np.arange(1273, 1774, 50):
    for cool in (False, True):
        r = row("T5", replace(base, reheat=True, T5=float(T5), cooling=cool)); r["cooled"] = cool; rows.append(r)
pd.DataFrame(rows).to_csv("results/reheat_temperature_sweep.csv", index=False)

# ---------------------------------------------------------------- 3. Hydrogen sweep
rows = []
for x in np.linspace(0, 1, 21):
    for rh in (False, True):
        for cool in (False, True):
            r = row("h2", replace(base, x_h2=x, reheat=rh, cooling=cool)); r["x_vol"] = x; rows.append(r)
h2 = pd.DataFrame(rows); h2.to_csv("results/hydrogen_sweep.csv", index=False)
d = h2[(~h2.reheat) & (h2.cooling)]; d0 = h2[(~h2.reheat) & (~h2.cooling)]
fig, ax = plt.subplots(2, 2, figsize=(11, 7))
ax[0, 0].plot(d0.x_vol * 100, d0.cp, color=C["simple"], lw=2); ax[0, 0].set_ylabel("Hot-gas cp (kJ/kg K)")
a2 = ax[0, 0].twinx(); a2.plot(d0.x_vol * 100, d0.y_h2o * 100, color=C["reheat"], lw=2, ls="--"); a2.set_ylabel("H₂O in exhaust (mol %)", color=C["reheat"])
a2.grid(False); a2.spines["right"].set_visible(True)
ax[0, 1].plot(d0.x_vol * 100, (d0.h_index - 1) * 100, color=C["reheat"], lw=2)
ax[0, 1].set_ylabel("Blade heat-transfer index vs 100 % NG (%)")
ax[1, 0].plot(d.x_vol * 100, d.coolant_total * 100, color=C["simple"], lw=2); ax[1, 0].set_ylabel("Coolant (% of compressor air)")
ax[1, 1].plot(d0.x_vol * 100, d0.eta_th * 100, color=C["ref"], ls="--", lw=2, label="no cooling")
ax[1, 1].plot(d.x_vol * 100, d.eta_th * 100, color=C["simple"], lw=2, label="cooled"); ax[1, 1].set_ylabel("Thermal efficiency (%)")
ax[1, 1].legend(frameon=False)
for a in ax.flat: a.set_xlabel("Hydrogen share, % by volume")
fig.suptitle("Hydrogen share at fixed TIT 1,400 °C: effect on the turbine side (simple cycle)", fontsize=10)
fig.tight_layout(); fig.savefig("figures/fig4_hydrogen.png"); plt.close(fig)

# ---------------------------------------------------------------- 4. Reheat + regeneration vs PR (interaction)
rows = []
for PRv in np.arange(4, 31, 2.0):
    for rh in (False, True):
        for rg in (0.0, 0.75):
            r = row("PR", replace(base, PR=PRv, reheat=rh, regen_eff=rg, cooling=False)); r["PRv"] = PRv; rows.append(r)
pr = pd.DataFrame(rows); pr.to_csv("results/reheat_regen_vs_PR.csv", index=False)
fig, ax = plt.subplots(figsize=(6.2, 4.2))
for rh, rg, c, ls, lab in [(False, 0.0, C["ref"], "--", "simple"), (True, 0.0, C["reheat"], "--", "reheat"),
                           (False, 0.75, C["simple"], "-", "simple + regen (ε 0.75)"),
                           (True, 0.75, C["regen"], "-", "reheat + regen (ε 0.75)")]:
    d = pr[(pr.reheat == rh) & (pr.regen == rg) & pr.feasible]
    ax.plot(d.PRv, d.eta_th * 100, color=c, ls=ls, lw=2, label=lab)
ax.set_xlabel("Pressure ratio"); ax.set_ylabel("Thermal efficiency (%)"); ax.legend(frameon=False, fontsize=8)
ax.set_title("Where does reheat help? (TIT 1,400 °C, uncooled model)", fontsize=10)
fig.tight_layout(); fig.savefig("figures/fig5_reheat_regen_PR.png"); plt.close(fig)

# ---------------------------------------------------------------- 5. LCOE / cost figure
sel = ["Simple, no cooling (team reference)", "Simple, cooled", "Reheat, no cooling", "Reheat, cooled"]
d = tit[(tit.T3 == 1673) & tit.config.isin(sel)].set_index("config").loc[sel]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
cols = [C["ref"], C["simple"], C["ref"], C["reheat"]]
ax[0].bar(range(4), d.LCOE, color=[C["ref"], C["simple"], "#c9ccd1", C["reheat"]])
for i, v in enumerate(d.LCOE): ax[0].text(i, v + .1, f"{v:.2f}", ha="center", fontsize=9)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(["Simple\n(no cool)", "Simple\ncooled", "Reheat\n(no cool)", "Reheat\ncooled"])
ax[0].set_ylabel("LCOE (Rs/kWh), NG, 50 % load"); ax[0].set_ylim(0, 14)
t = tit[(tit.config == "Reheat, no cooling") & (tit.T3 >= 1473)]
ax[1].plot(t.T3 - 273.15, t.Rs_per_extra_kW, color=C["reheat"], lw=2, label="Reheat (uncooled)")
t2 = tit[(tit.config == "Simple, no cooling (team reference)") & (tit.T3 > 1673)]
ax[1].plot(t2.T3 - 273.15, t2.Rs_per_extra_kW, color=C["ref"], lw=2, ls="--", label="Higher TIT only (uncooled)")
ax[1].axhline(40000, color="crimson", lw=1.2); ax[1].text(1215, 40800, "cost of new baseline capacity: Rs 40,000/kW", color="crimson", fontsize=8)
ax[1].set_xlabel("Turbine-inlet temperature (°C)"); ax[1].set_ylabel("Added capex per extra kW (Rs/kW)")
ax[1].legend(frameon=False, fontsize=8)
fig.suptitle("Cost of the work gained (R3 hardware) vs the LCOE it ends up with", fontsize=10)
fig.tight_layout(); fig.savefig("figures/fig6_cost.png"); plt.close(fig)

# ---------------------------------------------------------------- 6. R3 individually-optimal designs
feas = tit[(tit.feasible) & (tit.within_limits) & (tit.config != sel[0]) & (tit.config != sel[2])].copy()
best = {"Max efficiency": feas.loc[feas.eta_th.idxmax()],
        "Max specific work": feas.loc[feas.w_net.idxmax()],
        "Min LCOE": feas.loc[feas.LCOE.idxmin()],
        "Min R3 exergy destruction": feas.loc[((feas.Xd_turb + feas.Xd_reheat) / feas.X_fuel).idxmin()]}
bt = pd.DataFrame({k: v[["config", "T3", "eta_th", "w_net", "Xd_turb", "Xd_reheat", "capex_cr", "LCOE", "coolant_total", "T_exit"]] for k, v in best.items()}).T
bt.to_csv("results/r3_individual_optima.csv")

# ---------------------------------------------------------------- 7. Sensitivity (reheat OFF, cooled, 1,500 C vs 1,400 C)
def sens(cfg_kw, T):
    out = []
    p0 = replace(base, T3=T, **cfg_kw); r0 = row("b", p0)
    for name, field, lo, hi in [("Turbine isentropic efficiency 0.88 / 0.92", "eta_t", .88, .92),
                                ("Cooling calibration B 0.045 / 0.075", "B_cool", .045, .075),
                                ("Metal temperature 1,100 / 1,200 K", "T_metal", 1100., 1200.),
                                ("Hot-section cost 2 / 8 % per 100 K", "hot_sec_frac_per_100K", .02, .08),
                                ("Reheat capex 10 / 15 % of base", "reheat_capex_frac", .10, .15)]:
        a = row("lo", replace(p0, **{field: lo})); b = row("hi", replace(p0, **{field: hi}))
        out.append(dict(parameter=name, eta_lo=a["eta_th"] * 100, eta_hi=b["eta_th"] * 100,
                        LCOE_lo=a["LCOE"], LCOE_hi=b["LCOE"], eta_base=r0["eta_th"] * 100, LCOE_base=r0["LCOE"]))
    return pd.DataFrame(out)
s1 = sens(dict(), 1773.0); s1["case"] = "Simple cooled, 1,500 C"
s2 = sens(dict(reheat=True), 1673.0); s2["case"] = "Reheat cooled, 1,400 C"
pd.concat([s1, s2]).to_csv("results/sensitivity.csv", index=False)

# H2 summary table for the report
tab = []
for e_share in (0.0, 0.119, 0.3, 0.5, 1.0):
    pass
for xv in (0.0, 0.3, 0.5, 0.8, 1.0):
    for cool in (False, True):
        tab.append(row("h2tab", replace(base, x_h2=xv, cooling=cool)))
pd.DataFrame(tab).to_csv("results/hydrogen_table.csv", index=False)
print("done")
