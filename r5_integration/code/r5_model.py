"""
Problem 16 - R5 integrated cycle model (R1 + R2 + R3 + R4 -> complete plant).

Constant-specific-heat model of the four-week plan, h = cp*T, all specific quantities per kg of
COMPRESSOR-INLET air.  Hydrogen share x is the VOLUME (mole) fraction of H2 in the fuel.

State numbering (team master):
  0  ambient                     1  compressor inlet (after 1 % inlet loss)
  1a LP-compressor exit (IC)      1b intercooler exit (IC)
  2  compressor exit / coolant bleed point
  5  regenerator air outlet = combustor inlet (= 2 if no regenerator)
  3  combustor exit = turbine inlet (TIT)
  m  HP-turbine exit (reheat)     r  reheat-combustor exit (reheat to TIT)
  4  turbine exit                 6  regenerator gas outlet (= 4 if none)   7 stack (p0)
Blade coolant (fraction psi of compressor air, bled at 2) is mixed in at the middle of each
turbine's expansion (R3 approach); turbines use the polytropic efficiency equivalent to 0.90.
"""
from types import SimpleNamespace
import numpy as np
import r5_params as P

DEFAULTS = {k: getattr(P, k) for k in dir(P) if k.isupper()}


def make_opts(**over):
    d = dict(DEFAULTS)
    for k, v in over.items():
        if k not in d:
            raise KeyError(k)
        d[k] = v
    return SimpleNamespace(**d)


BASE_OPTS = make_opts()


# ------------------------------------------------------------------ fuel (R2)
def fuel(x, o):
    M = (1 - x) * o.M_CH4 + x * o.M_H2
    y = x * o.M_H2 / M                                 # H2 mass share
    LHV = (1 - y) * o.LHV_NG + y * o.LHV_H2
    e = y * o.LHV_H2 / LHV                             # H2 energy share
    ex = (1 - y) * o.LHV_NG * o.EXR_NG + y * o.LHV_H2 * o.EXR_H2
    return dict(y=y, LHV=LHV, e=e, ex=ex)


def gas_props(x, o):
    cp = float(np.interp(x, o.X_TAB, o.CPG_TAB))
    g = float(np.interp(x, o.X_TAB, o.GAMG_TAB))
    return cp, g, cp * (g - 1) / g


# ------------------------------------------------------------------ exergy helpers
def psi(T, p, cp, R, o):
    return cp * (T - o.T0) - o.T0 * (cp * np.log(T / o.T0) - R * np.log(p / o.P0))


def poly_eta(rt, eta, g):
    k = (g - 1) / g
    return np.log(1 - eta * (1 - rt ** (-k))) / (-k * np.log(rt))


def expand(T, rt, g, ep):
    return T * rt ** (-ep * (g - 1) / g)


# ------------------------------------------------------------------ R3 cooling
def coolant(TIT, Tc, x, o):
    if not o.COOLING or TIT <= o.T_METAL:
        return 0.0
    phi = (TIT - o.T_METAL) / (TIT - Tc)
    if phi >= 0.98:
        return np.nan
    eps = phi / (o.ETA_COOL * (1 - phi))
    return o.B_COOL * (o.CPG_TAB[0] / o.CP_A) * eps * float(np.interp(x, o.HIDX_X, o.HIDX))


# ------------------------------------------------------------------ turbine train (R3)
def turbine(m_in, T_in, p_in, p_out, psi_c, T2, p2, cp, g, R, o):
    """One turbine with coolant psi_c injected at mid log-pressure. Returns work, exit T,
    exit mass and exergy destruction (balance)."""
    rt = p_in / p_out
    ep = poly_eta(rt, o.ETA_T, g)
    p_half = np.sqrt(p_in * p_out)
    Ta = expand(T_in, p_in / p_half, g, ep)
    w = m_in * cp * (T_in - Ta)
    m2 = m_in + psi_c
    Tm = (m_in * cp * Ta + psi_c * o.CP_A * T2) / (m2 * cp)
    Tb = expand(Tm, p_half / p_out, g, ep)
    w += m2 * cp * (Tm - Tb)
    Xin = m_in * psi(T_in, p_in, cp, R, o) + psi_c * psi(T2, p2, o.CP_A, o.R_A, o)
    Xout = m2 * psi(Tb, p_out, cp, R, o)
    return w, Tb, m2, Xin - Xout - w


# ------------------------------------------------------------------ constraint indicators (R2)
def _fit_nox():
    A = np.array([[t - 722.0, np.log(s)] for t, s, _ in P.NOX_FIT_DATA])
    b = np.array([np.log(n / 25.0) for _, _, n in P.NOX_FIT_DATA])
    k, n = np.linalg.lstsq(A, b, rcond=None)[0]
    return k, n


NOX_K_TIN, NOX_N_SHARE = _fit_nox()


def nox_index(x, TIT, T_in, share_main, o):
    Tpz = o.TPZ_BASE + max(0.0, TIT - o.TIT_BASE)       # keep R2's dilution margin above TIT
    base = float(np.exp(np.interp(Tpz, o.NOX_TPZ_T, np.log(o.NOX_TPZ_PPM),
                                  right=np.log(o.NOX_TPZ_PPM[-1]))))
    h2 = float(np.interp(x, o.NOX_H2_X, o.NOX_H2_F))
    return base * h2 * np.exp(NOX_K_TIN * (T_in - 722.0)) * share_main ** NOX_N_SHARE, Tpz


def flashback_index(x, T_in, o):
    f722 = np.log(np.interp(x, o.FI_X_722, o.FI_722))
    f877 = np.log(np.interp(x, o.FI_X_877, o.FI_877))
    w = (max(T_in, 722.0) - 722.0) / (877.0 - 722.0)       # linear in T_in, extrapolated above 877 K
    return float(np.exp(f722 + w * (f877 - f722)))


def rh_xmax(PR, o):
    return float(np.interp(PR, o.RH_X_PR, o.RH_X_MAX))


# ------------------------------------------------------------------ main evaluation
def evaluate(PR, TIT, x, ic=False, rh=False, rg=False, eps=0.75, o=BASE_OPTS):
    r = dict(PR=PR, TIT=TIT, x=x, ic=int(ic), rh=int(rh), rg=int(rg), eps=eps if rg else 0.0,
             config=config_name(ic, rh, rg))
    fb = fuel(x, o)
    cp, g, R = gas_props(x, o)
    LHV = fb["LHV"]
    # ---- R1: compression
    T1, p1 = o.T0, o.P0 * (1 - o.DP_INLET)
    p2 = PR * p1
    k_a = (o.GAM_A - 1) / o.GAM_A
    Xd = {}
    Xd["inlet duct"] = o.T0 * o.R_A * np.log(o.P0 / p1)
    if ic:
        rs = np.sqrt(PR / (1 - o.DP_IC))
        T1a = T1 * (1 + (rs ** k_a - 1) / o.ETA_C)
        p1a = rs * p1
        T1b = T1a - o.EPS_IC * (T1a - o.T_COOLANT_IC)
        p1b = p1a * (1 - o.DP_IC)
        T2 = T1b * (1 + (rs ** k_a - 1) / o.ETA_C)
        w_c = o.CP_A * ((T1a - T1) + (T2 - T1b))
        Xd["compressor"] = (o.CP_A * (T1a - T1) - psi(T1a, p1a, o.CP_A, o.R_A, o) + psi(T1, p1, o.CP_A, o.R_A, o)
                            + o.CP_A * (T2 - T1b) - psi(T2, p2, o.CP_A, o.R_A, o) + psi(T1b, p1b, o.CP_A, o.R_A, o))
        Xd["intercooler"] = psi(T1a, p1a, o.CP_A, o.R_A, o) - psi(T1b, p1b, o.CP_A, o.R_A, o)
        r.update(T1a=T1a, T1b=T1b, q_ic=o.CP_A * (T1a - T1b))
    else:
        T2 = T1 * (1 + (PR ** k_a - 1) / o.ETA_C)
        w_c = o.CP_A * (T2 - T1)
        Xd["compressor"] = w_c - psi(T2, p2, o.CP_A, o.R_A, o) + psi(T1, p1, o.CP_A, o.R_A, o)
        Xd["intercooler"] = 0.0
        r.update(q_ic=0.0)
    # ---- R3: coolant demand (bled at state 2)
    psi1 = coolant(TIT, T2, x, o)
    psi2 = coolant(TIT, T2, x, o) if rh else 0.0
    if np.isnan(psi1):
        r.update(feasible=False, reason="cooling")
        return r
    a = 1.0 - psi1 - psi2                               # combustor air per kg compressor air
    # ---- pressures
    p5 = p2 * (1 - o.DP_RG) if rg else p2
    p3 = p5 * (1 - o.DP_COMB)
    p6 = o.P0 / (1 - o.DP_EXH)
    p4 = p6 / (1 - o.DP_RG) if rg else p6
    # ---- iterate regenerator <-> combustor <-> turbine
    T4 = 900.0
    for _ in range(100):
        if rg:
            Cc = a * o.CP_A
            T5_guess = None
        T5 = T2
        Q_rg = 0.0
        if rg and T4 > T2:
            # hot-side capacity uses current mass estimate
            m_ex_est = r.get("_m_ex", 1.03)
            Cc, Ch = a * o.CP_A, m_ex_est * cp
            Cmin = min(Cc, Ch)
            Q_rg = eps * Cmin * (T4 - T2)
            T5 = T2 + Q_rg / Cc
        # main combustor (R2 hand balance)
        f1 = (cp * TIT - o.CP_A * T5) / (o.ETA_B * LHV - cp * TIT)
        mf1 = a * f1
        m_g = a + mf1
        if rh:
            p_mid = np.exp(np.log(p3) + o.RH_HP_SHARE * (np.log(p4 / (1 - o.DP_COMB)) - np.log(p3)))
            w1, Tm, m_hp, xd1 = turbine(m_g, TIT, p3, p_mid, psi1, T2, p2, cp, g, R, o)
            pr_ = p_mid * (1 - o.DP_COMB)
            mf2 = m_hp * cp * (TIT - Tm) / (o.ETA_B * LHV - cp * TIT)
            m_r = m_hp + mf2
            w2, T4n, m_ex, xd2 = turbine(m_r, TIT, pr_, p4, psi2, T2, p2, cp, g, R, o)
            w_t = w1 + w2
            Xd_rh = m_hp * psi(Tm, p_mid, cp, R, o) + mf2 * fb["ex"] - m_r * psi(TIT, pr_, cp, R, o)
            Xd_t = xd1 + xd2
        else:
            mf2, Tm, p_mid = 0.0, np.nan, np.nan
            w_t, T4n, m_ex, Xd_t = turbine(m_g, TIT, p3, p4, psi1, T2, p2, cp, g, R, o)
            Xd_rh = 0.0
        r["_m_ex"] = m_ex
        if abs(T4n - T4) < 1e-7:
            T4 = T4n
            break
        T4 = T4n
    r.pop("_m_ex", None)
    # regenerator final (consistent capacities)
    if rg and T4 > T2:
        Cc, Ch = a * o.CP_A, m_ex * cp
        Cmin, Cmax = min(Cc, Ch), max(Cc, Ch)
        Q_rg = eps * Cmin * (T4 - T2)
        T5 = T2 + Q_rg / Cc
        T6 = T4 - Q_rg / Ch
        Cr = Cmin / Cmax
        NTU = np.log((1 - eps * Cr) / (1 - eps)) / (1 - Cr) if Cr < 0.999 else eps / (1 - eps)
        ua_kg = NTU * Cmin                                 # kW/K per (kg/s) of compressor air
        appr = min(T4 - T5, T6 - T2)
        Xd["regenerator"] = (a * psi(T2, p2, o.CP_A, o.R_A, o) + m_ex * psi(T4, p4, cp, R, o)
                             - a * psi(T5, p5, o.CP_A, o.R_A, o) - m_ex * psi(T6, p6, cp, R, o))
    else:
        # regenerator selected but exhaust not hotter than compressor delivery -> infeasible
        T6, ua_kg, NTU = T4, 0.0, 0.0
        appr = (T4 - T2) if rg else np.inf
        Xd["regenerator"] = 0.0
    f_tot = mf1 + mf2
    Xd["combustor"] = a * psi(T5, p5, o.CP_A, o.R_A, o) + mf1 * fb["ex"] - m_g * psi(TIT, p3, cp, R, o)
    Xd["reheat combustor"] = Xd_rh
    Xd["turbine (incl. cooling)"] = Xd_t
    Xd["exhaust duct"] = m_ex * (psi(T6, p6, cp, R, o) - psi(T6, o.P0, cp, R, o))
    w_net = w_t - w_c
    if w_net <= 0:
        r.update(feasible=False, reason="no net work")
        return r
    Xd["generator"] = w_net * (1 - o.ETA_GEN)
    X_stack = m_ex * psi(T6, o.P0, cp, R, o)
    X_fuel = f_tot * fb["ex"]
    W_el = w_net * o.ETA_GEN
    eta_th = w_net / (f_tot * LHV)
    eta_net = eta_th * o.ETA_GEN
    m_air = o.P_NET / W_el
    m_fuel = m_air * f_tot
    Xd_tot = sum(Xd.values())
    closure = X_fuel - W_el - Xd_tot - X_stack
    # ---- constraint indicators
    nox, Tpz = nox_index(x, TIT, T5, mf1 / f_tot, o)
    fi = flashback_index(x, T5, o)
    # ---- emissions (direct; green H2 has zero upstream by assumption)
    fuel_MJ_kWh = 3.6 / eta_net
    co2 = fuel_MJ_kWh * (1 - fb["e"]) * o.CO2_NG / 1000.0
    # ---- cost (R5): capital + O&M + fuel (+ H2 hardware + storage)
    cap = {"base plant": o.BASE_CAPEX,
           "hot section (TIT)": o.BASE_CAPEX * o.HOT_SEC_PER_100K * max(0.0, TIT - o.TIT_BASE) / 100.0,
           "intercooler": o.C_IC if ic else 0.0,
           "regenerator": o.C_RG_REF * (ua_kg * m_air) / o.UA_REF if rg else 0.0,
           "reheat": o.C_RH if rh else 0.0,
           "H2 combustor premium": o.BASE_CAPEX * float(np.interp(x, o.H2HW_X, o.H2HW_P)),
           }
    m_h2 = m_fuel * fb["y"]                            # kg/s
    cap["H2 storage"] = m_h2 * 3600 * o.H2_STORE_HOURS * o.H2_STORE_RS_KG / 1e7
    capex = sum(cap.values())
    E = o.P_NET * 8760 * o.LOAD_FACTOR                 # kWh/yr
    fuel_GJ = E * fuel_MJ_kWh / 1000.0
    price = (1 - fb["e"]) * o.NG_PRICE + fb["e"] * o.H2_PRICE_KG / 0.120
    fuel_cr = fuel_GJ * price / 1e7
    crf = P.crf(o.DISC, o.LIFE)
    ann = capex * (crf + o.OM_FRAC) + fuel_cr
    lcoe = ann * 1e7 / E
    # ---- constraints (g <= 0 feasible)
    cons = {
        "NOx > CPCB 75 ppm": nox - o.NOX_LIMIT,
        "flashback index > 2.0": fi - o.FI_LIMIT,
        "combustor inlet > 1050 K": T5 - o.T_IN_CC_MAX,
        "reheat-combustor H2 autoignition": (x - rh_xmax(PR, o)) if rh else -1.0,
        "regenerator approach < 20 K": (o.DT_APPROACH_MIN - appr) if rg else -1.0,
        "TIT > firing limit": TIT - o.TIT_MAX - 1e-6,
    }
    r.update(feasible=all(v <= 0 for v in cons.values()), reason="",
             T1=T1, p1=p1, T2=T2, p2=p2, T5=T5, p5=p5, T3=TIT, p3=p3, T_hp=Tm, p_mid=p_mid,
             T4=T4, p4=p4, T6=T6, p6=p6, psi_cool=psi1 + psi2, f1=f1, f_tot=f_tot,
             w_c=w_c, w_t=w_t, w_net=w_net, eta_th=eta_th, eta_net=eta_net,
             heat_rate=3600.0 / eta_net, m_air=m_air, m_fuel=m_fuel, m_h2=m_h2,
             Q_rg_MW=Q_rg * m_air / 1000.0, UA=ua_kg * m_air, A_rg=ua_kg * m_air / o.U_RG,
             NTU=NTU, approach=appr, e_share=fb["e"], LHV=LHV, cp_g=cp, gam_g=g,
             X_fuel=X_fuel, W_el=W_el, X_stack=X_stack, Xd_total=Xd_tot, closure=closure,
             psi2nd=W_el / X_fuel, Xd_MJ_kWh=3.6 * Xd_tot / W_el,
             nox=nox, Tpz=Tpz, FI=fi, co2=co2, capex=capex, fuel_cr=fuel_cr,
             fuel_price=price, lcoe=lcoe, fuel_MJ_kWh=fuel_MJ_kWh)
    for k, v in Xd.items():
        r["Xd: " + k] = v
    for k, v in cap.items():
        r["cap: " + k] = v
    for k, v in cons.items():
        r["g: " + k] = v
    return r


def config_name(ic, rh, rg):
    parts = [n for n, b in (("IC", ic), ("Regen", rg), ("Reheat", rh)) if b]
    return "+".join(parts) if parts else "Simple"


CONFIGS = [(ic, rh, rg) for ic in (0, 1) for rg in (0, 1) for rh in (0, 1)]
