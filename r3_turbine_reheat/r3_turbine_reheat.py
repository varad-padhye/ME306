"""
Problem 16 - R3 module: Turbine & Reheat
=========================================
Hydrogen-fuelled / hydrogen-blended gas turbine (Brayton cycle).

Scope of R3 (from the problem statement)
  Core    : turbine-inlet temperature (TIT), reheat (second combustor + LP turbine),
            expansion work, effect of the higher H2O content of hydrogen exhaust on gas
            properties and on blade heat transfer, material / cooling limits.
  Exergy  : exergy destroyed in the turbine (incl. coolant throttling + mixing) and in
            the reheat combustor.
  Cost    : hot-section materials, cooling and reheat hardware vs. work gained.

Model = constant-specific-heat cycle model (as agreed in the 4-week plan).  Cantera is
used ONLY to get the hot-gas property ratios (cp, R, heat-transfer index) vs hydrogen
share once; those ratios scale the baseline hot-gas cp = 1.15 kJ/kg K, gamma = 1.333.

Interfaces (so R1/R2/R4/R5 can plug in)
  IN  from R1 : T2, p2 (compressor exit)  -> here a stub `compressor_stub` is used.
  IN  from R2 : hydrogen share (vol) -> `hot_gas_props` stands in for R2's cp table.
  OUT to  R4  : turbine exit temperature T_exit, exhaust flow, p_exit.
  OUT to  R5  : net work per kg air, thermal efficiency, fuel per kg air,
                exergy destruction (turbine, reheat), cost premiums.

All specific quantities are per kg of COMPRESSOR-INLET air unless stated.
Temperatures K, pressures bar, energies kJ.
"""
from dataclasses import dataclass, replace
import numpy as np
from scipy.optimize import minimize_scalar

# ----------------------------------------------------------------------------------
# 1. Baseline parameters (problem statement, section 5)
# ----------------------------------------------------------------------------------
@dataclass
class P:
    # ambient / compressor side (R1 owns these; stub only)
    T0: float = 308.15          # K (35 C)
    p0: float = 1.013           # bar
    PR: float = 15.0
    eta_c: float = 0.87
    cp_a: float = 1.005
    gam_a: float = 1.4
    # turbine side (R3 owns these)
    eta_t: float = 0.90
    cp_g0: float = 1.15         # baseline hot-gas cp
    gam_g0: float = 1.333       # baseline hot-gas gamma
    T3: float = 1673.0          # turbine-inlet temperature (K)
    reheat: bool = False
    T5: float = None            # reheat temperature (K); None -> same as T3
    hp_share: float = None      # HP share of log expansion; None -> numerical optimum
    # losses
    dp_in: float = 0.01
    dp_comb: float = 0.04
    dp_reheat: float = 0.04     # ASSUMPTION: same as main combustor
    dp_exh: float = 0.01
    eta_b: float = 0.99
    loss_mode: str = "explicit"    # 'explicit': p1 = 0.99 p0, p4 = p0/0.99 -> rt = 14.11 (reproduces team reference)
                                    # 'reference': inlet/exhaust dp ignored in rt (rt = 14.4) - for sensitivity only
    eta_gen: float = 0.985
    # fuel
    x_h2: float = 0.0           # hydrogen share BY VOLUME (mole fraction)  <-- team definition
    LHV_ch4: float = 48.0e3     # kJ/kg (problem statement)
    LHV_h2: float = 120.0e3     # kJ/kg
    # regenerator stub (R4 owns the real one). 0 = none.
    regen_eff: float = 0.0
    # cooling model (ASSUMPTIONS - see report section 4)
    cooling: bool = True
    T_metal: float = 1150.0     # K  allowable blade-metal (TBC surface) temperature
    eta_cool: float = 0.70      # internal-cooling effectiveness
    B_cool: float = 0.06        # calibration: ~12% of compressor air at 1,400 C
    # cost (problem statement, section 6 + assumptions)
    plant_capex_cr_per_MW: float = 4.0
    P_net_MW: float = 100.0
    reheat_capex_frac: float = 0.125   # 10-15 % of base plant cost -> midpoint (assumption)
    hot_sec_frac_per_100K: float = 0.04  # ASSUMPTION: +4 % of base per +100 K above 1,673 K
    T3_cost_ref: float = 1673.0


M_CH4, M_H2 = 16.043, 2.016
EX_RATIO_CH4, EX_RATIO_H2 = 1.04, 0.976   # chemical exergy / LHV  (Szargut/Kotas-type values)


# ----------------------------------------------------------------------------------
# 2. Fuel + hot-gas properties (stand-in for R2's table)
# ----------------------------------------------------------------------------------
def fuel_blend(x_h2, p: P):
    """Mass-basis LHV, molar mass, exergy-LHV ratio and energy share of a blend (vol basis)."""
    M = x_h2 * M_H2 + (1 - x_h2) * M_CH4
    m_h2 = x_h2 * M_H2 / M
    LHV = m_h2 * p.LHV_h2 + (1 - m_h2) * p.LHV_ch4
    e_share = m_h2 * p.LHV_h2 / LHV
    ex_ratio = (m_h2 * p.LHV_h2 * EX_RATIO_H2 + (1 - m_h2) * p.LHV_ch4 * EX_RATIO_CH4) / LHV
    return dict(M=M, LHV=LHV, e_share=e_share, ex_ratio=ex_ratio, ex=LHV * ex_ratio)


def x_from_energy_share(e, p: P):
    """Inverse of fuel_blend: volume fraction giving a requested energy share."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if fuel_blend(mid, p)["e_share"] < e:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


_ct = {}
def _gas_state(x_h2, f_air, p: P, T=1300.0):
    """Cantera: cp, R, k, mu, y_H2O of the combustion gas (complete combustion, excess O2)."""
    import cantera as ct
    if "g" not in _ct:
        _ct["g"] = ct.Solution("gri30.yaml")
    g = _ct["g"]
    fb = fuel_blend(x_h2, p)
    n_air = 1.0 / 28.85                              # kmol air per kg air
    n_f = f_air / fb["M"]                            # kmol fuel per kg air
    n_ch4, n_h2 = (1 - x_h2) * n_f, x_h2 * n_f
    o2_req = 2 * n_ch4 + 0.5 * n_h2
    n_o2 = 0.21 * n_air - o2_req
    if n_o2 < 0:
        raise ValueError("fuel-air ratio exceeds stoichiometric - infeasible")
    n = {"N2": 0.79 * n_air, "O2": n_o2, "CO2": n_ch4, "H2O": 2 * n_ch4 + n_h2}
    g.TPX = T, ct.one_atm, n
    y_h2o = g["H2O"].X[0]
    return dict(cp=g.cp_mass / 1000.0, R=8.314462 / g.mean_molecular_weight,
                k=g.thermal_conductivity, mu=g.viscosity, y_h2o=y_h2o)


def hot_gas_props(x_h2, f_air, p: P):
    """Scale baseline cp/R so that x_h2=0 at the baseline f reproduces cp=1.15, gamma=1.333.
    Also returns the blade heat-transfer index h/h_baseline at fixed mass flux:
        h  ~  k^0.6 * mu^-0.4 * cp^0.4   (Dittus-Boelter, Re^0.8 Pr^0.4)"""
    ref = _gas_state(0.0, 0.0263, p)
    cur = _gas_state(x_h2, f_air, p)
    R0 = p.cp_g0 * (p.gam_g0 - 1) / p.gam_g0
    cp = p.cp_g0 * cur["cp"] / ref["cp"]
    R = R0 * cur["R"] / ref["R"]
    gam = cp / (cp - R)
    hfun = lambda s: s["k"] ** 0.6 * s["mu"] ** -0.4 * s["cp"] ** 0.4
    return dict(cp=cp, R=R, gam=gam, h_index=hfun(cur) / hfun(ref), y_h2o=cur["y_h2o"])


# ----------------------------------------------------------------------------------
# 3. Compressor stub (R1 replaces this)
# ----------------------------------------------------------------------------------
def compressor_stub(p: P):
    p1 = p.p0 * (1 - (p.dp_in if p.loss_mode == "explicit" else 0.0))
    p2 = p.PR * p1
    T2 = p.T0 * (1 + (p.PR ** ((p.gam_a - 1) / p.gam_a) - 1) / p.eta_c)
    w_c = p.cp_a * (T2 - p.T0)
    return T2, p2, w_c


# ----------------------------------------------------------------------------------
# 4. R3 core: cooling, turbine sections, reheat
# ----------------------------------------------------------------------------------
def coolant_fraction(T_in, T_c, cp_g, p: P, h_index=1.0):
    """Convective-film cooling (Horlock-type):  phi=(Tg-Tm)/(Tg-Tc),  eps=phi/(eta_c(1-phi)),
       m_c/m_air = B * (cp_g/cp_a) * eps * (h/h_base)."""
    if not p.cooling:
        return 0.0
    phi = (T_in - p.T_metal) / (T_in - T_c)
    if phi <= 0:
        return 0.0
    if phi >= 0.98:
        return np.nan          # cooling cannot hold metal limit -> infeasible
    eps = phi / (p.eta_cool * (1 - phi))
    return p.B_cool * (p.cp_g0 / p.cp_a) * eps * h_index * (cp_g_scale_ref(p))


def cp_g_scale_ref(p):  # kept for transparency: coolant model is calibrated with cp_g0
    return 1.0


def _poly_eta(rt, eta, gam):
    """Polytropic efficiency equivalent to overall isentropic efficiency `eta` over ratio rt."""
    k = (gam - 1) / gam
    return np.log(1 - eta * (1 - rt ** (-k))) / (-k * np.log(rt))


def _turb_section(T_in, rt, cp, gam, eta_p):
    """Expansion over ratio rt with POLYTROPIC efficiency eta_p (so that splitting one
    turbine into sections for coolant injection does not change its overall efficiency)."""
    return T_in * rt ** (-eta_p * (gam - 1) / gam)


def _s(T, pr, cp, R, p: P):   # entropy rel. to (T0,p0), constant cp
    return cp * np.log(T / p.T0) - R * np.log(pr / p.p0)


def _psi(T, pr, cp, R, p: P):  # flow (thermo-mechanical) exergy per kg
    return cp * (T - p.T0) - p.T0 * _s(T, pr, cp, R, p)


def cycle(p: P):
    """Full cycle evaluation for one configuration. Returns a dict (per kg compressor air)."""
    T2, p2, w_c = compressor_stub(p)
    R_a = p.cp_a * (p.gam_a - 1) / p.gam_a
    T5 = p.T3 if p.T5 is None else p.T5
    p3 = p2 * (1 - p.dp_comb)
    p4 = p.p0 / (1 - (p.dp_exh if p.loss_mode == "explicit" else 0.0))
    fb = fuel_blend(p.x_h2, p)
    LHV = fb["LHV"]

    # regenerator stub (air preheat uses turbine exit temperature -> iterate)
    T_exit_guess = 900.0
    f_tot_guess = 0.026
    for _ in range(40):
        gp = hot_gas_props(p.x_h2, min(f_tot_guess, 0.055), p)
        cp, R, gam = gp["cp"], gp["R"], gp["gam"]
        Tair = T2 + p.regen_eff * max(T_exit_guess - T2, 0.0) if p.regen_eff > 0 else T2

        # ---- coolant demand
        x1 = coolant_fraction(p.T3, T2, cp, p, gp["h_index"])
        x2 = coolant_fraction(T5, T2, cp, p, gp["h_index"]) if p.reheat else 0.0
        if np.isnan(x1) or np.isnan(x2):
            return dict(feasible=False, reason="cooling cannot hold metal limit")
        a = 1 - x1 - x2                       # combustor air per kg compressor air
        if a <= 0:
            return dict(feasible=False, reason="coolant > air")

        # ---- main combustor
        f1 = (cp * p.T3 - p.cp_a * Tair) / (p.eta_b * LHV - cp * p.T3)
        mf1 = a * f1
        m_g = a + mf1                         # gas mass into HP turbine

        # ---- pressure split
        if p.reheat:
            def total_work(s):
                return _train(p, T2, p3, p4, T5, s, m_g, x1, x2, cp, R, gam, LHV, mf1)["w_t"]
            if p.hp_share is None:
                res = minimize_scalar(lambda s: -total_work(s), bounds=(0.2, 0.8), method="bounded")
                s_opt = res.x
            else:
                s_opt = p.hp_share
            tr = _train(p, T2, p3, p4, T5, s_opt, m_g, x1, x2, cp, R, gam, LHV, mf1)
        else:
            s_opt = 1.0
            tr = _train(p, T2, p3, p4, T5, 1.0, m_g, x1, 0.0, cp, R, gam, LHV, mf1)

        f_tot = tr["mf_tot"]
        if abs(f_tot - f_tot_guess) < 1e-9 and abs(tr["T_exit"] - T_exit_guess) < 1e-6:
            break
        f_tot_guess, T_exit_guess = f_tot, tr["T_exit"]
    else:
        pass
    if f_tot > 0.055:
        return dict(feasible=False, reason="over-rich")

    w_net = tr["w_t"] - w_c
    Q = tr["mf_tot"] * LHV
    eta_th = w_net / Q
    eta_net = eta_th * p.eta_gen
    m_air = p.P_net_MW * 1000.0 / (w_net * p.eta_gen)           # kg/s
    # ---- exergy (per kg air; then MW)
    ex_f = fb["ex"]
    out = dict(feasible=True, T2=T2, p2=p2, T3=p.T3, T5=T5, T_exit=tr["T_exit"], p_exit=p4,
               x1=x1, x2=x2, s_hp=s_opt, w_c=w_c, w_t=tr["w_t"], w_net=w_net, f_tot=f_tot,
               f1=f1, mf1=mf1, mf2=tr["mf2"], eta_th=eta_th, eta_net=eta_net,
               heat_rate=3600.0 / eta_net, m_air=m_air, m_fuel=m_air * f_tot,
               Tair=Tair, cp=cp, gam=gam, R=R, h_index=gp["h_index"], y_h2o=gp["y_h2o"],
               e_share=fb["e_share"], LHV=LHV,
               co2_kg_kwh=_co2(p, fb, eta_net),
               p_mid=tr["p_mid"], T_hp_exit=tr["T_hp_exit"])
    # exergy destruction (kJ/kg air)
    out["Xd_turb"] = tr["Xd_turb"]
    out["Xd_reheat"] = tr["Xd_reheat"]
    out["X_fuel"] = tr["mf_tot"] * ex_f
    out["X_exit"] = tr["X_exit"]
    for k in ("Xd_turb", "Xd_reheat", "X_exit", "X_fuel"):
        out[k + "_MW"] = out[k] * m_air / 1000.0
    # cost
    out.update(cost_block(p, out))
    return out


def _train(p, T2, p3, p4, T5, s, m_g, x1, x2, cp, R, gam, LHV, mf1):
    """HP turbine [+ reheat + LP turbine].  Coolant injected after half of each turbine's
    expansion; coolant enters at (T2) after throttling from p2.  Returns work + exergy."""
    cpa, Ra = p.cp_a, p.cp_a * (p.gam_a - 1) / p.gam_a
    T3 = p.T3
    p2 = p3 / (1 - p.dp_comb)
    lnp3, lnp4 = np.log(p3), np.log(p4)
    # ---------------- HP turbine
    if p.reheat:
        lnp_mid = lnp3 + s * (np.log(p4 / (1 - p.dp_reheat)) - lnp3)
    else:
        lnp_mid = lnp4
    p_mid = np.exp(lnp_mid)
    p_half = np.exp(0.5 * (lnp3 + lnp_mid))
    ep1 = _poly_eta(p3 / p_mid, p.eta_t, gam)
    Ta = _turb_section(T3, p3 / p_half, cp, gam, ep1)
    w1a = m_g * cp * (T3 - Ta)
    Tmix = (m_g * cp * Ta + x1 * cpa * T2) / ((m_g + x1) * cp)
    Tb = _turb_section(Tmix, p_half / p_mid, cp, gam, ep1)
    w1b = (m_g + x1) * cp * (Tmix - Tb)
    m_hp = m_g + x1
    # entropy generation (HP): out - in
    S_in = m_g * _s(T3, p3, cp, R, p) + x1 * _s(T2, p2, cpa, Ra, p)
    S_out = m_hp * _s(Tb, p_mid, cp, R, p)
    Xd_turb = p.T0 * (S_out - S_in)
    w_t = w1a + w1b
    Xd_reheat, mf2 = 0.0, 0.0
    if not p.reheat:
        T_exit = Tb
        m_exit = m_hp
        p_exit = p_mid
    else:
        # ---------------- reheat combustor
        p5 = p_mid * (1 - p.dp_reheat)
        mf2 = m_hp * cp * (T5 - Tb) / (p.eta_b * LHV - cp * T5)
        m5 = m_hp + mf2
        # exergy balance of reheat combustor (thermo-mechanical + fuel chemical exergy)
        fb = fuel_blend(p.x_h2, p)
        Xin = m_hp * _psi(Tb, p_mid, cp, R, p) + mf2 * fb["ex"]
        Xout = m5 * _psi(T5, p5, cp, R, p)
        Xd_reheat = Xin - Xout
        # ---------------- LP turbine
        lnp5 = np.log(p5)
        p_half2 = np.exp(0.5 * (lnp5 + lnp4))
        ep2 = _poly_eta(p5 / p4, p.eta_t, gam)
        Tc = _turb_section(T5, p5 / p_half2, cp, gam, ep2)
        w2a = m5 * cp * (T5 - Tc)
        Tmix2 = (m5 * cp * Tc + x2 * cpa * T2) / ((m5 + x2) * cp)
        Td = _turb_section(Tmix2, p_half2 / p4, cp, gam, ep2)
        w2b = (m5 + x2) * cp * (Tmix2 - Td)
        S_in2 = m5 * _s(T5, p5, cp, R, p) + x2 * _s(T2, p2, cpa, Ra, p)
        S_out2 = (m5 + x2) * _s(Td, p4, cp, R, p)
        Xd_turb += p.T0 * (S_out2 - S_in2)
        w_t += w2a + w2b
        T_exit = Td
        m_exit = m5 + x2
        p_exit = p4
    X_exit = m_exit * _psi(T_exit, p_exit, cp, R, p)
    return dict(w_t=w_t, T_exit=T_exit, mf_tot=mf1 + mf2, mf2=mf2, Xd_turb=Xd_turb,
                Xd_reheat=Xd_reheat, X_exit=X_exit, p_mid=p_mid,
                T_hp_exit=(Tb if p.reheat else Tb))


def _co2(p, fb, eta_net):
    """Direct CO2 kg/kWh = fuel energy (MJ/kWh) x methane-energy share x 0.0561 kg/MJ
    (problem-statement factor 56.1 kg/GJ; hydrogen burns carbon-free)."""
    return (3.6 / eta_net) * (1 - fb["e_share"]) * 0.0561


# ----------------------------------------------------------------------------------
# 5. Cost (R3 share) and LCOE (same 12-step recipe as the worked example)
# ----------------------------------------------------------------------------------
CRF = lambda r=0.09, n=25: r * (1 + r) ** n / ((1 + r) ** n - 1)


def cost_block(p: P, o: dict):
    base = p.plant_capex_cr_per_MW * p.P_net_MW                        # Rs crore
    hot = base * p.hot_sec_frac_per_100K * (p.T3 - p.T3_cost_ref) / 100.0
    if p.reheat:   # LP turbine also sees hot gas
        hot += base * p.hot_sec_frac_per_100K * max((o["T5"] - p.T3_cost_ref), 0) / 100.0 * 0.5
    rh = base * p.reheat_capex_frac if p.reheat else 0.0
    capex = base + hot + rh
    return dict(capex_base_cr=base, capex_hot_cr=hot, capex_reheat_cr=rh, capex_cr=capex)


def lcoe(capex_cr, eta_net, p: P, fuel_Rs_per_GJ=850.0, LF=0.50, om=0.03):
    kwh = p.P_net_MW * 1000 * 8760 * LF
    fuel_GJ = kwh * (3.6 / eta_net) / 1000.0
    fuel_cr = fuel_GJ * fuel_Rs_per_GJ / 1e7
    cap = capex_cr * CRF()
    omc = capex_cr * om
    return (cap + omc + fuel_cr) * 1e7 / kwh, dict(cap=cap, om=omc, fuel=fuel_cr)


def fuel_price_per_GJ(e_share, ng=850.0, h2=2917.0):
    return (1 - e_share) * ng + e_share * h2


def evaluate(p: P):
    o = cycle(p)
    if not o["feasible"]:
        return o
    fp = fuel_price_per_GJ(o["e_share"])
    o["LCOE"], parts = lcoe(o["capex_cr"], o["eta_net"], p, fp)
    o["LCOE_parts"] = parts
    return o


if __name__ == "__main__":
    # ---- validation against the "reference check for end of Week 2" (no cooling, NG)
    b = evaluate(P(cooling=False))
    print("BASELINE (no cooling, 100% NG)  - reference in brackets")
    print(f" T2         = {b['T2']:.1f} K        [722]")
    print(f" f          = {b['f_tot']:.4f}        [0.026]")
    print(f" T_exit     = {b['T_exit']:.1f} K ({b['T_exit']-273.15:.0f} C) [944 K / 671 C]")
    print(f" w_net      = {b['w_net']:.1f} kJ/kg  [444]")
    print(f" eta_th     = {b['eta_th']*100:.2f} %   [35.2]   eta_net = {b['eta_net']*100:.2f} % [34.7]")
    print(f" heat rate  = {b['heat_rate']:.0f} kJ/kWh [~10,380]")
    print(f" air / fuel = {b['m_air']:.1f} / {b['m_fuel']:.2f} kg/s [~229 / ~6.0]")
    print(f" CO2        = {b['co2_kg_kwh']:.3f} kg/kWh [~0.58]  (LHV-based)")
    print(f" LCOE       = {b['LCOE']:.2f} Rs/kWh  [10.03]")
