"""
R5 master run: candidate configurations, feasible-set scan, NSGA-II (5 objectives), TOPSIS,
final design, role trade-offs, exergy balance, LCOE/CO2, sensitivity.  Writes ../results/*.csv
and ../results/summary.json (read by r5_figures.py and the report).
"""
import os, json, itertools
import numpy as np
import pandas as pd
from r5_model import evaluate, make_opts, CONFIGS, config_name, BASE_OPTS
from r5_nsga2 import nsga2, fast_nondominated_sort
import r5_params as P

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)
OBJ = ["eta_net", "Xd_MJ_kWh", "lcoe", "co2", "nox"]
GKEYS = None
G_SCALE = {"NOx > CPCB 75 ppm": 75.0, "flashback index > 2.0": 2.0, "combustor inlet > 1050 K": 1050.0,
           "reheat-combustor H2 autoignition": 1.0, "regenerator approach < 20 K": 20.0,
           "TIT > firing limit": 100.0}
summary = {}


def objvec(r):
    return np.array([-r["eta_net"], r["Xd_MJ_kWh"], r["lcoe"], r["co2"], r["nox"]])


def cv(r):
    if "g: NOx > CPCB 75 ppm" not in r:
        return 1e3
    return sum(max(r["g: " + k], 0.0) / s for k, s in G_SCALE.items())


def short(r):
    keep = ["config", "PR", "TIT", "x", "e_share", "eps", "feasible", "eta_th", "eta_net", "heat_rate",
            "w_net", "m_air", "m_fuel", "m_h2", "T2", "T5", "T4", "T6", "psi_cool", "Tpz", "FI", "nox",
            "co2", "lcoe", "capex", "fuel_cr", "Xd_total", "Xd_MJ_kWh", "psi2nd", "X_stack", "X_fuel",
            "UA", "A_rg", "approach", "ic", "rh", "rg"]
    d = {k: r.get(k, np.nan) for k in keep}
    d.update({k: v for k, v in r.items() if k.startswith(("Xd: ", "cap: ", "g: "))})
    return d


# ======================================================== 1. baselines + candidate configurations
nouc = make_opts(COOLING=False)
b_unc = evaluate(15, P.TIT_BASE, 0.0, o=nouc)
b_cool = evaluate(15, P.TIT_BASE, 0.0)
summary["baseline_uncooled"] = short(b_unc)
summary["baseline_cooled"] = short(b_cool)
rows = []
for x in (0.0, 0.3):
    for ic, rh, rg in CONFIGS:
        for cool in (True, False):
            o = BASE_OPTS if cool else nouc
            r = evaluate(15, P.TIT_BASE, x, ic, rh, rg, 0.75, o=o)
            d = short(r); d["cooling"] = cool
            rows.append(d)
cand = pd.DataFrame(rows)
cand.to_csv(os.path.join(RES, "candidate_configs_PR15_TIT1400C.csv"), index=False)

# PR sweep per configuration (cooled, x = 0.3, TIT 1400 C, eps 0.75) for the integration plot
rows = []
for ic, rh, rg in CONFIGS:
    for PR in np.arange(6, 40.5, 1.0):
        r = evaluate(PR, P.TIT_BASE, 0.3, ic, rh, rg, 0.75)
        if "eta_net" in r:
            rows.append(dict(config=r["config"], PR=PR, eta_net=r["eta_net"], lcoe=r["lcoe"],
                             feasible=r["feasible"], T4_minus_T2=r["T4"] - r["T2"]))
pd.DataFrame(rows).to_csv(os.path.join(RES, "pr_sweep.csv"), index=False)

# TIT sweep (cooled vs uncooled) on IC+Regen, PR 15, x 0.3
rows = []
for TIT in np.arange(1573.15, 1773.2, 10):
    for cool in (True, False):
        r = evaluate(15, TIT, 0.3, 1, 0, 1, 0.8, o=BASE_OPTS if cool else nouc)
        rows.append(dict(TIT=TIT, cooling=cool, eta_net=r["eta_net"], psi_cool=r["psi_cool"],
                         nox=r["nox"], lcoe=r["lcoe"]))
pd.DataFrame(rows).to_csv(os.path.join(RES, "tit_sweep_integrated.csv"), index=False)

# ======================================================== 2. structured scan -> feasible set
grid = []
PRs = np.arange(8, 31, 2.0)
TITs = np.array([1573.15, 1623.15, 1673.15, 1723.15, 1773.15])
Xs = np.round(np.linspace(0, 1, 11), 2)
EPSs = [0.5, 0.65, 0.75, 0.85]
for ic, rh, rg in CONFIGS:
    for PR, TIT, x in itertools.product(PRs, TITs, Xs):
        for eps in (EPSs if rg else [0.0]):
            r = evaluate(PR, TIT, x, ic, rh, rg, eps)
            if "eta_net" not in r:
                continue
            grid.append(short(r))
grid = pd.DataFrame(grid)
grid.to_csv(os.path.join(RES, "grid_scan_all.csv"), index=False)
gcols = [c for c in grid.columns if c.startswith("g: ")]
viol = {c[3:]: int((grid[c] > 0).sum()) for c in gcols}
only = {}
for c in gcols:
    others = [k for k in gcols if k != c]
    only[c[3:]] = int(((grid[c] > 0) & (grid[others] <= 0).all(axis=1)).sum())
summary["scan"] = dict(n=len(grid), n_feasible=int(grid.feasible.sum()), violations=viol, sole_violation=only,
                       feasible_by_config=grid.groupby("config").feasible.agg(["sum", "count"]).astype(int).to_dict())

# ======================================================== 3. NSGA-II per configuration
nsga_rows, arch_rows = [], []
for ic, rh, rg in CONFIGS:
    lo = [8.0, P.TIT_MIN, 0.0] + ([P.EPS_RG_MIN] if rg else [])
    hi = [30.0, P.TIT_MAX, 1.0] + ([P.EPS_RG_MAX] if rg else [])

    def f(v, ic=ic, rh=rh, rg=rg):
        r = evaluate(v[0], v[1], v[2], ic, rh, rg, v[3] if rg else 0.0)
        if "eta_net" not in r:
            return np.full(5, 1e6), 1e3, None
        return objvec(r), cv(r), r

    final, archive = nsga2(f, lo, hi, pop=100, gens=150, seed=11 + 4 * ic + 2 * rg + rh)
    for e in final:
        if e[2] is not None:
            nsga_rows.append(short(e[2]))
    for e in archive:
        if e[2] is not None and e[2]["feasible"]:
            arch_rows.append(short(e[2]))
    print("NSGA-II done:", config_name(ic, rh, rg), sum(e[1] == 0 for e in final), "feasible in final pop")
nsga = pd.DataFrame(nsga_rows)
nsga.to_csv(os.path.join(RES, "nsga2_final_populations.csv"), index=False)
arch = pd.DataFrame(arch_rows)

# ======================================================== 4. global feasible set + 5-D Pareto front
feas = pd.concat([grid[grid.feasible], arch, nsga[nsga.feasible]], ignore_index=True)
feas = feas.drop_duplicates(subset=["config", "PR", "TIT", "x", "eps"]).reset_index(drop=True)
F = np.column_stack([-feas.eta_net, feas.Xd_MJ_kWh, feas.lcoe, feas.co2, feas.nox]).astype(float)
# non-dominated filter (vectorised in chunks)
nd = np.ones(len(F), bool)
for i in range(len(F)):
    if not nd[i]:
        continue
    dom = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
    if dom.any():
        nd[i] = False
pareto = feas[nd].reset_index(drop=True)
feas_s = feas.sample(min(len(feas), 20000), random_state=0) if len(feas) > 20000 else feas
feas_s.to_csv(os.path.join(RES, "feasible_set.csv"), index=False)
pareto.to_csv(os.path.join(RES, "pareto_front_5obj.csv"), index=False)
summary["n_feasible_total"] = int(len(feas))
summary["n_pareto"] = int(len(pareto))
summary["pareto_by_config"] = pareto.config.value_counts().to_dict()

with open(os.path.join(RES, "summary.json"), "w") as fh:
    json.dump(summary, fh, indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))
print("stage 1 done: feasible", len(feas), "pareto", len(pareto))
