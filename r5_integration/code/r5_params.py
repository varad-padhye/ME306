"""
Problem 16 - R5 shared parameter file (single source of truth for the integrated model).

Every number used by the integrated cycle, exergy, cost and constraint models lives here,
with its owner and source. Change a value here and every module picks it up.

Sources:  [PS] Detailed problem statement 16   [PLAN] four-week plan
          [R1] [R2] [R3] [R4] teammate reports   [WEB] cited web sources (see report)
"""
import numpy as np

# ---------------------------------------------------------------- ambient / dead state  [PS]
T0 = 308.15          # K   (35 C) - also exergy dead state
P0 = 1.013           # bar
DP_INLET = 0.01      # inlet duct loss                                       [PS]
DP_COMB = 0.04       # combustor loss (main and reheat)                      [PS]; reheat = main [R3]
DP_EXH = 0.01        # exhaust duct loss                                     [PS]

# ---------------------------------------------------------------- air side  [PS]
CP_A = 1.005         # kJ/kg K
GAM_A = 1.4
R_A = CP_A * (GAM_A - 1) / GAM_A
ETA_C = 0.87

# ---------------------------------------------------------------- R1 intercooler
EPS_IC = 0.85        # intercooler effectiveness (R1 candidate)               [R1]
DP_IC = 0.02         # intercooler pressure loss (R5 fixed value; R1 neglected it)
T_COOLANT_IC = T0    # cooling-medium inlet = ambient                         [R1]

# ---------------------------------------------------------------- R2 combustor / fuel
ETA_B = 0.99                         # combustor efficiency                  [PS]
LHV_NG, LHV_H2 = 48.0e3, 120.0e3     # kJ/kg, project basis                  [PS][R2]
M_CH4, M_H2 = 16.043, 2.016          # kg/kmol                              [R2]
EXR_NG, EXR_H2 = 1.0366, 0.9764      # chemical exergy / LHV (Szargut)      [R2]
CO2_NG = 56.1                        # kg CO2 per GJ natural gas             [PS]
CO2_H2_UPSTREAM = 0.0                # green hydrogen, zero upstream (team assumption)

# Hot-gas properties vs hydrogen share by VOLUME (R2 table, plan basis: NG -> 1.15 / 1.333)  [R2 s3.3]
X_TAB = np.linspace(0.0, 1.0, 11)
CPG_TAB = np.array([1.150, 1.151, 1.153, 1.155, 1.157, 1.159, 1.162, 1.167, 1.172, 1.180, 1.191])
GAMG_TAB = np.array([1.3330, 1.3331, 1.3333, 1.3335, 1.3337, 1.3340, 1.3344, 1.3348, 1.3354, 1.3362, 1.3374])

# NOx indicator (R2 s4.1): calibrated Zeldovich, 25 ppm @ 1790 K primary zone on NG
NOX_TPZ_T = np.array([1600, 1650, 1700, 1750, 1790, 1850, 1900, 1950.0])
NOX_TPZ_PPM = np.array([0.40, 1.32, 4.01, 11.37, 25.00, 75.90, 180.24, 406.60])
TPZ_BASE = 1790.0                    # K at TIT 1673 K (R2 strategy S2, re-tuned burner)
# relative NOx increase with hydrogen at fixed primary-zone temperature (R2 S2 column / 25)
NOX_H2_X = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0])
NOX_H2_F = np.array([25.0, 25.2, 25.5, 25.8, 26.2, 26.8, 27.8, 29.5, 34.6]) / 25.0
# R2 configuration table (x = 0, PR 15): used to fit the inlet-temperature and reheat-dilution
# terms of the NOx surrogate.  (T_in,cc [K], main-combustor fuel share [-], NOx [ppm])
NOX_FIT_DATA = [(722, 1.000, 25.0), (878, 1.000, 30.8), (722, 0.709, 16.9), (1095, 0.627, 24.8),
                (501, 1.000, 19.1), (812, 1.000, 28.1), (501, 0.742, 13.5), (1029, 0.644, 23.1)]
NOX_LIMIT = 75.0                     # ppm @15% O2, CPCB 100-400 MW band      [R2, to verify]

# Flashback index (R2 s4.2) = g_c(x)/g_c(NG) at the same inlet temperature
FI_X_722 = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0])
FI_722 = np.array([1.00, 1.07, 1.15, 1.26, 1.38, 1.55, 1.94, 2.69, 6.97])
FI_X_877 = np.array([0.0, 0.3, 0.5, 0.65, 1.0])
FI_877 = np.array([1.00, 1.31, 1.67, 2.13, 10.59])
FI_LIMIT = 2.0                       # tier-B advanced premixer (R2 tier-B top FI = 1.94)

T_IN_CC_MAX = 1050.0                 # premixer autoignition limit, K          [R2 s4.3]
# hydrogen share allowed in an autoignition-stabilised reheat combustor vs PR  [R2 s4.3]
RH_X_PR = np.array([10.0, 15.0, 20.0])
RH_X_MAX = np.array([0.27, 0.41, 0.47])

# H2-capable combustor premium (fraction of base plant cost), piecewise linear   [R2 s4.5]
H2HW_X = np.array([0.0, 0.30, 1.0])
H2HW_P = np.array([0.0, 0.04, 0.15])

# ---------------------------------------------------------------- R3 turbine / cooling
ETA_T = 0.90                                                               # [PS]
TIT_BASE = 1673.15                                                         # [PS]
TIT_MIN, TIT_MAX = 1573.15, 1773.15  # firing-temperature limit 1500 C (G/H-class air-cooled tech) [WEB]
COOLING = True
T_METAL = 1150.0     # K allowable blade-metal temperature (R3; WEB: ~1200 K metal at 1400 C entry)
ETA_COOL = 0.70      # internal cooling effectiveness                       [R3]
B_COOL = 0.075       # calibration -> 15 % of compressor air at 1400 C (R3: 12 %; WEB: ~20 % incl. sealing)
# blade heat-transfer index h/h_NG vs hydrogen share (R3 Cantera/Dittus-Boelter)  [R3 hydrogen_table]
HIDX_X = np.array([0.0, 0.3, 0.5, 0.8, 1.0])
HIDX = np.array([1.000, 1.004, 1.008, 1.019, 1.034])
RH_HP_SHARE = 0.5    # reheat: equal log-pressure split, reheat to TIT          [R2]

# ---------------------------------------------------------------- R4 regenerator
EPS_RG_MIN, EPS_RG_MAX = 0.50, 0.85                                       # [R4]
DP_RG = 0.02         # pressure loss each side (R4 sensitivity range 1-3 %; R5 fixed value)
DT_APPROACH_MIN = 20.0                                                     # [R4]
U_RG = 0.050         # kW/m2K                                              [R4]
UA_REF, C_RG_REF = 576.05, 40.0      # R4: UA [kW/K] and Rs 40 cr at eps 0.75 -> cost ~ UA

# ---------------------------------------------------------------- plant / economics  [PS]
P_NET = 100.0e3      # kW
ETA_GEN = 0.985
LOAD_FACTOR = 0.50
DISC, LIFE = 0.09, 25
OM_FRAC = 0.03
BASE_CAPEX = 4.0 * 100   # Rs crore
C_IC = 0.065 * BASE_CAPEX        # 6.5 % -> Rs 26 cr                         [R1]
C_RH = 0.125 * BASE_CAPEX        # 12.5 % -> Rs 50 cr                        [R3]
HOT_SEC_PER_100K = 0.04          # +4 % of base per +100 K above 1673 K      [R3 assumption]
NG_PRICE = 850.0                 # Rs/GJ
H2_PRICE_KG = 350.0              # Rs/kg                                      [PS]
H2_STORE_RS_KG = 55000.0         # Rs per kg of storage capacity              [R2, US DOE]
H2_STORE_HOURS = 8.0             # hours of full-load hydrogen                [R2]


def crf(r=None, n=None):
    r = DISC if r is None else r
    n = LIFE if n is None else n
    return r * (1 + r) ** n / ((1 + r) ** n - 1)
