"""R5 validation: reproduce the plan's baseline and each teammate's hand-off numbers."""
import csv, os
from r5_model import evaluate, make_opts

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(OUT, exist_ok=True)
rows = []


def add(check, qty, ref, val, fmt="{:.2f}"):
    rows.append(dict(check=check, quantity=qty, reference=ref, r5_model=fmt.format(val)))


# 1. Plan Week-2 reference (uncooled, no extra losses)
o = make_opts(COOLING=False)
b = evaluate(15, 1673.15, 0.0, o=o)
for q, ref, v, f in [("Compressor exit T2 (K)", "722", b["T2"], "{:.1f}"),
                     ("Fuel-air ratio", "0.026", b["f_tot"], "{:.4f}"),
                     ("Turbine exit T4 (K)", "944", b["T4"], "{:.1f}"),
                     ("Net work (kJ/kg air)", "444", b["w_net"], "{:.1f}"),
                     ("Cycle efficiency (%)", "35.2", 100 * b["eta_th"], "{:.2f}"),
                     ("Net efficiency (%)", "34.7", 100 * b["eta_net"], "{:.2f}"),
                     ("Heat rate (kJ/kWh)", "10,380", b["heat_rate"], "{:.0f}"),
                     ("Air flow (kg/s)", "229", b["m_air"], "{:.1f}"),
                     ("Fuel flow (kg/s)", "6.0", b["m_fuel"], "{:.2f}"),
                     ("Direct CO2 (kg/kWh)", "0.58", b["co2"], "{:.3f}"),
                     ("LCOE (Rs/kWh)", "10.03", b["lcoe"], "{:.2f}"),
                     ("Exergy closure (kJ/kg air)", "0", b["closure"], "{:.1e}")]:
    add("Plan baseline", q, ref, v, f)

# 2. R1 two-stage handoff (eps 0.85, no IC loss, uncooled)
o = make_opts(COOLING=False, DP_IC=0.0)
r1 = evaluate(15, 1673.15, 0.0, ic=True, o=o)
add("R1 handoff", "LPC exit T (K)", "475.46", r1["T1a"])
add("R1 handoff", "Intercooler exit T (K)", "333.25", r1["T1b"])
add("R1 handoff", "Compressor exit T (K)", "514.18", r1["T2"])
add("R1 handoff", "Compressor work (kJ/kg)", "349.98", r1["w_c"])

# 3. R4 regenerator (eps 0.75, zero added dp, uncooled)
o = make_opts(COOLING=False, DP_RG=0.0)
r4 = evaluate(15, 1673.0, 0.0, rg=True, eps=0.75, o=o)
add("R4 handoff", "Air after regenerator T5 (K)", "888.84", r4["T5"])
add("R4 handoff", "Exhaust after regenerator T6 (K)", "801.76", r4["T6"])
add("R4 handoff", "Heat recovered (MW)", "38.65", r4["Q_rg_MW"])
add("R4 handoff", "Net efficiency (%)", "40.03", 100 * r4["eta_net"])
add("R4 handoff", "Fuel flow (kg/s)", "5.204", r4["m_fuel"], "{:.3f}")
add("R4 handoff", "UA (kW/K)", "576.05", r4["UA"], "{:.1f}")
add("R4 handoff", "Regenerator exergy destruction (MW)", "1.172",
    r4["Xd: regenerator"] * r4["m_air"] / 1000, "{:.3f}")
add("R4 handoff", "LCOE (Rs/kWh)", "8.968", r4["lcoe"], "{:.3f}")

# 4. R3 cooled simple cycle (R3's calibration B = 0.06)
o = make_opts(B_COOL=0.06, T_METAL=1150.0)
r3 = evaluate(15, 1673.0, 0.0, o=o)
add("R3 handoff", "Coolant fraction (-)", "0.1187", r3["psi_cool"], "{:.4f}")
add("R3 handoff", "Turbine exit T (K)", "887.4", r3["T4"], "{:.1f}")
add("R3 handoff", "Net efficiency (%)", "32.35", 100 * r3["eta_net"])

# 5. R2 configuration table (x=0, PR 15, eps_rg 0.7, eps_ic 0.9, no extra losses, uncooled)
o = make_opts(COOLING=False, DP_IC=0.0, DP_RG=0.0, EPS_IC=0.9)
nox2 = {"Simple": 25.0, "Regen": 30.8, "Reheat": 16.9, "Regen+Reheat": 24.8, "IC": 19.1,
        "IC+Regen": 28.1, "IC+Reheat": 13.5, "IC+Regen+Reheat": 23.1}
ref2 = {"Simple": 34.7, "Regen": 39.6, "Reheat": 31.9, "Regen+Reheat": 40.5, "IC": 34.2,
        "IC+Regen": 43.3, "IC+Reheat": 31.8, "IC+Regen+Reheat": 43.4}
for ic, rh, rg in [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)]:
    r = evaluate(15, 1673.15, 0.0, ic, rh, rg, 0.7, o=o)
    add("R2 config table", r["config"] + " net efficiency (%)", f"{ref2[r['config']]}", 100 * r["eta_net"], "{:.1f}")
    add("R2 config table", r["config"] + " NOx (ppm)", f"{nox2[r['config']]}", r["nox"], "{:.1f}")

with open(os.path.join(OUT, "validation.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(f"{r['check']:18s} {r['quantity']:42s} ref {r['reference']:>8s}  R5 {r['r5_model']:>10s}")
