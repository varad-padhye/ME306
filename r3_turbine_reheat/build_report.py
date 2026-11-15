import pandas as pd, numpy as np
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from dataclasses import replace
from r3_turbine_reheat import P, evaluate, compressor_stub

tit = pd.read_csv("results/tit_sweep.csv")
h2 = pd.read_csv("results/hydrogen_table.csv")
opt = pd.read_csv("results/r3_individual_optima.csv", index_col=0)
sens = pd.read_csv("results/sensitivity.csv")
pr = pd.read_csv("results/reheat_regen_vs_PR.csv")

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
for m in ("left_margin", "right_margin"): setattr(sec, m, Cm(2.2))
sec.top_margin = sec.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
for n, sz in (("Heading 1", 15), ("Heading 2", 12)):
    s = doc.styles[n]; s.font.name = "Calibri"; s.font.size = Pt(sz); s.font.bold = True
    s.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    s.paragraph_format.space_before = Pt(12); s.paragraph_format.space_after = Pt(4); s.paragraph_format.keep_with_next = True

def para(t="", bold=False, italic=False, size=None, align=None, after=4):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    if align: p.alignment = align
    p.paragraph_format.space_after = Pt(after); return p

def rich(parts, style=None):
    p = doc.add_paragraph(style=style)
    for t, b in parts:
        r = p.add_run(t); r.bold = b
    p.paragraph_format.space_after = Pt(3); return p

def bullet(t, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        p.add_run(bold_lead).bold = True
    p.add_run(t); p.paragraph_format.space_after = Pt(2); return p

def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcol); tcPr.append(sh)

def table(header, rows, widths, fs=9, first_left=True):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(fs)
        r.font.color.rgb = RGBColor(255, 255, 255); shade(c, "1F3A5F")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(fs)
            if i > 0 or not first_left: cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in t.rows:
        for i, w in enumerate(widths): row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

def fig(path, w=16.0, cap=None):
    doc.add_picture(path, width=Cm(w)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if cap: para(cap, italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)

def g(df, cfg, T): return df[(df.config == cfg) & (df.T3 == T)].iloc[0]
REF, SC, RN, RC = "Simple, no cooling (team reference)", "Simple, cooled", "Reheat, no cooling", "Reheat, cooled"

# ------------------------------------------------------------------ title
para("Problem 16 — Hydrogen-Fueled / Hydrogen-Blended Gas Turbine", bold=True, size=18, after=0)
para("R3 — Turbine & Reheat: report section", size=13, after=2)
para("Core design · Exergy analysis · Costing · Hand calculation · Code (r3_turbine_reheat.py)", italic=True, size=9.5, after=10)

# ------------------------------------------------------------------ 1 summary
doc.add_heading("1. Summary", 1)
b0, b1 = g(tit, REF, 1673), g(tit, REF, 1773)
r_n, r_c = g(tit, RN, 1673), g(tit, RC, 1673)
sc0, sc1 = g(tit, SC, 1673), g(tit, SC, 1773)
h0, h1 = h2[(h2.x_h2 == 0) & (~h2.cooling)].iloc[0], h2[(h2.x_h2 == 1) & (~h2.cooling)].iloc[0]
bullet(f" The turbine module reproduces the team's Week-2 reference (T4 {b0.T_exit:.0f} K, net work {b0.w_net:.0f} kJ/kg air, "
       f"η {b0.eta_th*100:.1f}%, LCOE Rs {b0.LCOE:.2f}/kWh) with the cooling model switched off.", "Validated.")
bullet(f" Raising TIT from 1,400 to 1,500 °C lifts uncooled efficiency {b0.eta_th*100:.1f}% → {b1.eta_th*100:.1f}% and net work "
       f"{b0.w_net:.0f} → {b1.w_net:.0f} kJ/kg (+{(b1.w_net/b0.w_net-1)*100:.0f}%). With the (assumed) cooling model the efficiency gain shrinks to "
       f"{sc0.eta_th*100:.1f}% → {sc1.eta_th*100:.1f}% because 12–14% of compressor air goes to cooling.", "Turbine-inlet temperature.")
bullet(f" Reheat (optimum split ≈ equal expansion) adds {(r_n.w_net/b0.w_net-1)*100:.0f}% specific work ({b0.w_net:.0f} → {r_n.w_net:.0f} kJ/kg) "
       f"but cuts simple-cycle efficiency by {(b0.eta_th-r_n.eta_th)*100:.1f} points and raises exhaust to {r_n.T_exit:.0f} K. "
       f"It only pays back efficiency when paired with regeneration (R4) at pressure ratios of roughly 12 and above. "
       f"Capex per extra kW is ≈ Rs {r_n.Rs_per_extra_kW:,.0f}, well below the Rs 40,000/kW of new baseline capacity, but LCOE rises "
       f"(Rs {r_n.LCOE:.2f} vs {b0.LCOE:.2f}/kWh).", "Reheat.")
bullet(f" At fixed TIT, going from 0 to 100% hydrogen changes the turbine side only slightly: hot-gas cp +{(h1.cp/h0.cp-1)*100:.1f}%, "
       f"exhaust H₂O {h0.y_h2o*100:.1f} → {h1.y_h2o*100:.1f} mol%, blade heat-transfer index +{(h1.h_index-1)*100:.1f}%, "
       f"efficiency +{(h1.eta_th-h0.eta_th)*100:.1f} points. The hydrogen problem is in the combustor (R2), not the turbine.", "Hydrogen.")
bullet(" TIT 1,400–1,500 °C, total coolant ≤ 25% of compressor air, reheat OFF unless regeneration is ON. R3's individually "
       "best design (max efficiency and min LCOE) is the cooled simple cycle at the 1,500 °C limit.", "Recommendation to R5.")
para("Items marked ASSUMPTION below (cooling-model calibration, hot-section cost slope, firing-temperature limit) are not from the problem "
     "statement and are not cited; the team should confirm or replace them before the report is frozen.", italic=True, size=9.5)

# ------------------------------------------------------------------ 2 scope & assumptions
doc.add_heading("2. Scope, interfaces and assumptions", 1)
para("R3 owns the turbine, the optional reheat combustor and LP turbine, the coolant demand, and the exergy and cost of those parts. "
     "The model is the constant-specific-heat cycle model agreed in the 4-week plan; per-kg quantities are per kg of compressor-inlet air.")
table(["Item", "Value", "Source / status"], [
    ["Compressor, ambient, PR, efficiencies, pressure losses, combustor efficiency, fuel LHV", "As in problem statement §5", "Given"],
    ["Hot-gas cp, γ (100% natural gas)", "1.15 kJ/kg K, 1.333", "Given; scaled with composition (see below)"],
    ["Hydrogen share definition", "By volume (mole fraction); energy share also reported", "Team to fix in Week 1 — one-line change in code"],
    ["Hot-gas property scaling vs H₂", "cp, R ratios from Cantera (GRI-Mech 3.0 thermo) at 1,300 K, complete combustion", "Stand-in for R2's cp table"],
    ["Turbine efficiency in split sections", "0.90 overall isentropic, converted to polytropic", "Method choice"],
    ["Reheat combustor pressure loss", "4% (same as main combustor)", "ASSUMPTION"],
    ["Reheat temperature", "Equal to TIT unless varied", "Design choice"],
    ["Cooling model", "Horlock-type film/convective: φ=(Tg−Tm)/(Tg−Tc), ε=φ/[η_c(1−φ)], m_c/m_air = B·(cp_g/cp_a)·ε·(h/h_base); Tm = 1,150 K, η_c = 0.70, B = 0.06 (≈12% coolant at 1,400 °C)", "ASSUMPTION — calibration, not cited"],
    ["Coolant treatment", "Taken at compressor exit, injected after half of each turbine's expansion (energy-balance mixing); bypasses the combustor", "Simplification"],
    ["Firing-temperature limit", "1,500 °C (1,773 K), H-class-type hot-section technology", "ASSUMPTION — confirm / cite"],
    ["Cooling limit", "Total coolant ≤ 25% of compressor air", "ASSUMPTION"],
    ["Blade heat transfer vs H₂O", "h ∝ k^0.6 · μ^−0.4 · cp^0.4 at fixed mass flux (Dittus–Boelter), properties from Cantera", "Standard correlation; radiation neglected"],
    ["Fuel chemical exergy / LHV", "CH₄ 1.04, H₂ 0.976", "Textbook values (Szargut/Kotas type)"],
    ["Cost basis", "Rs 4 crore/MW base (Rs 400 crore); reheat +12.5% (mid of 10–15%); CRF 0.102; O&M 3%", "Given (problem §6)"],
    ["Hot-section/cooling cost slope", "+4% of base plant cost per +100 K TIT above 1,673 K (negative below)", "ASSUMPTION — problem gives no figure"],
], [5.2, 7.2, 4.0], fs=8.5)

# ------------------------------------------------------------------ 3 equations
doc.add_heading("3. Equations", 1)
for t in [
    "Turbine exit (overall isentropic η_t):  T4 = T3 [1 − η_t (1 − r_t^−(γ−1)/γ)],  r_t = p3/p4 = PR(1−Δp_comb)(1−Δp_in)(1−Δp_exh)",
    "Work per kg air:  w_t = (1+f) cp_g (T3 − T4);  w_net = w_t − w_c;  η = w_net / (f · LHV)",
    "Fuel–air ratio (combustor energy balance):  f = (cp_g T3 − cp_a T2) / (η_b LHV − cp_g T3)",
    "Reheat fuel:  m_f2 = m_hp cp_g (T5 − T_hp) / (η_b LHV − cp_g T5);  pressure split by maximising w_net (≈ equal ratios, r_HP ≈ r_LP)",
    "Coolant mixing:  T_mix = (m_g cp_g T_a + m_c cp_a T2) / ((m_g + m_c) cp_g)",
    "Turbine exergy destruction:  X_d = T0 (S_out − S_in),  s = cp ln(T/T0) − R ln(p/p0); coolant enters at compressor-exit pressure, so throttling and mixing losses are included",
    "Reheat-combustor exergy destruction:  X_d = m_hp ψ(T_hp, p_mid) + m_f2 ex_f − m_5 ψ(T5, p5)",
    "LCOE:  [CAPEX·(CRF + 0.03) + annual fuel cost] / annual kWh, same 12-step recipe as the problem's worked example",
]:
    p = doc.add_paragraph(style="List Bullet"); r = p.add_run(t); r.font.size = Pt(9.5); p.paragraph_format.space_after = Pt(2)

# ------------------------------------------------------------------ 4 hand calc
doc.add_heading("4. Hand calculation (baseline turbine, PR 15, TIT 1,400 °C)", 1)
p = P(cooling=False); T2, p2, wc = compressor_stub(p)
rt = p2 * 0.96 / (p.p0 / 0.99); k = 0.333 / 1.333
T4 = 1673 * (1 - 0.9 * (1 - rt ** (-k))); f = (1.15 * 1673 - 1.005 * T2) / (0.99 * 48000 - 1.15 * 1673)
wt = (1 + f) * 1.15 * (1673 - T4)
table(["Step", "Calculation", "Result"], [
    ["Compressor exit", f"T2 = 308.15[1 + (15^0.2857 − 1)/0.87]", f"{T2:.1f} K"],
    ["Turbine expansion ratio", "r_t = 15 × 0.96 × 0.99 × 0.99  (p4 = 1.013/0.99 bar)", f"{rt:.2f}"],
    ["Turbine exit", f"T4 = 1673[1 − 0.90(1 − {rt:.2f}^−0.2498)]", f"{T4:.1f} K ({T4-273.15:.0f} °C)"],
    ["Fuel–air ratio", f"f = (1.15×1673 − 1.005×{T2:.1f}) / (0.99×48,000 − 1.15×1673)", f"{f:.4f}"],
    ["Turbine work", f"(1 + {f:.4f}) × 1.15 × (1673 − {T4:.1f})", f"{wt:.1f} kJ/kg"],
    ["Compressor work", f"1.005 × ({T2:.1f} − 308.15)", f"{wc:.1f} kJ/kg"],
    ["Net work, efficiency", f"{wt:.1f} − {wc:.1f};  η = w_net/(f·LHV)", f"{wt-wc:.1f} kJ/kg;  {(wt-wc)/(f*48000)*100:.1f}%"],
], [3.6, 9.4, 3.4], fs=8.5)
o = evaluate(P(cooling=False, reheat=True, hp_share=0.5))
rHP = (rt * 0.96) ** 0.5
THP = 1673 * (1 - 0.9 * (1 - rHP ** (-(o["gam"] - 1) / o["gam"])))
para(f"Reheat check (equal split). With the 4% reheat-combustor loss, r_HP = r_LP = √(14.11 × 0.96) = {rHP:.2f}. "
     f"The reheated-case gas is richer in products, so the property set is cp = {o['cp']:.3f}, γ = {o['gam']:.3f}; the HP exit is then "
     f"T = 1673[1 − 0.9(1 − {rHP:.2f}^−{(o['gam']-1)/o['gam']:.3f})] = {THP:.0f} K, matching the code ({o['T_hp_exit']:.0f} K). "
     f"The reheat combustor adds fuel f₂ = {o['mf2']:.4f} kg/kg air; net work {o['w_net']:.0f} kJ/kg, η {o['eta_th']*100:.1f}%.")

# ------------------------------------------------------------------ 5 validation
doc.add_heading("5. Validation against the team reference (no cooling, 100% natural gas)", 1)
b = evaluate(P(cooling=False))
table(["Quantity", "Reference", "R3 module"], [
    ["Compressor exit T2 (K)", "722", f"{b['T2']:.1f}"], ["Fuel–air ratio", "0.026", f"{b['f_tot']:.4f}"],
    ["Turbine exit (K / °C)", "944 / 671", f"{b['T_exit']:.1f} / {b['T_exit']-273.15:.0f}"],
    ["Net work (kJ/kg air)", "444", f"{b['w_net']:.1f}"],
    ["Efficiency, cycle / net of generator (%)", "35.2 / 34.7", f"{b['eta_th']*100:.2f} / {b['eta_net']*100:.2f}"],
    ["Heat rate (kJ/kWh)", "~10,380", f"{b['heat_rate']:.0f}"], ["Air / fuel flow (kg/s)", "~229 / ~6.0", f"{b['m_air']:.1f} / {b['m_fuel']:.2f}"],
    ["Direct CO₂ (kg/kWh)", "~0.58", f"{b['co2_kg_kwh']:.3f}"], ["LCOE (Rs/kWh)", "10.03", f"{b['LCOE']:.2f}"],
], [7, 4.2, 4.2])
para("The turbine exergy balance closes to numerical precision: (1+f)[ψ3 − ψ4] = w_t + X_d (892.3 kJ/kg both sides, uncooled baseline).", size=9.5)

# ------------------------------------------------------------------ 6 results TIT / reheat
doc.add_heading("6. Turbine-inlet temperature and reheat", 1)
rows = []
for cfg in (REF, SC, RN, RC):
    for T in (1673, 1773):
        d = g(tit, cfg, T)
        rows.append([cfg.replace(" (team reference)", " (ref.)"), f"{T-273.15:.0f}", f"{d.eta_th*100:.2f}", f"{d.w_net:.0f}", f"{d.T_exit:.0f}",
                     f"{d.coolant_total*100:.1f}", f"{d.capex_cr:.0f}", f"{d.LCOE:.2f}", "yes" if d.within_limits else "no"])
table(["Config.", "TIT °C", "η %", "w_net kJ/kg", "T_exit K", "Coolant %", "Capex Rs cr", "LCOE Rs/kWh", "In limits"], rows,
      [4.4, 1.2, 1.2, 1.7, 1.5, 1.5, 1.7, 1.9, 1.3], fs=8)
fig("figures/fig1_tit_sweep.png", 16.2, "Figure 1 — Efficiency and net work vs TIT. Dashed = uncooled (team reference basis); solid = with the assumed cooling model.")
para("Reading the curves. Without cooling, a higher TIT raises specific work almost linearly and efficiency with diminishing returns. "
     "Cooling air is charged against the cycle, so the cooled curves flatten; the efficiency benefit of the last 100 K is only about 0.3 points. "
     "Reheat shifts the work curve up strongly but the efficiency curve down, because the extra heat is added at a lower mean temperature than the main combustion.")
fig("figures/fig3_reheat_split.png", 16.2, "Figure 2 — Reheat pressure split at 1,400 °C. Net work peaks near an equal split; efficiency keeps rising slightly as less fuel is burned in the reheater.")
fig("figures/fig5_reheat_regen_PR.png", 10.5, "Figure 3 — Where reheat helps. A regenerator stub (ε = 0.75, no pressure loss) stands in for R4's module; uncooled model.")
pr15 = pr[(pr.PRv == 14) & pr.feasible]
a = pr15[(pr15.reheat) & (pr15.regen == .75)].eta_th.iloc[0] * 100; c_ = pr15[(~pr15.reheat) & (pr15.regen == .75)].eta_th.iloc[0] * 100
para(f"Interaction with R4. At PR 14 with ε = 0.75 the uncooled reheat + regeneration cycle reaches {a:.1f}% against {c_:.1f}% for simple + regeneration. "
     "Reheat becomes attractive when the regenerator can absorb the hotter exhaust (T_exit above 1,200 K). With the cooling model on, the extra "
     "cooling demand of the second hot stage removes this advantage, so the conclusion depends on the cooling assumption (see sensitivity, §11). "
     "R5 should therefore test reheat only in combination with regeneration.")

# ------------------------------------------------------------------ 7 hydrogen
doc.add_heading("7. Hydrogen: gas properties, water vapour and blade heat transfer", 1)
rows = []
for xv in (0, .3, .5, .8, 1.0):
    u = h2[(h2.x_h2 == xv) & (~h2.cooling)].iloc[0]; c = h2[(h2.x_h2 == xv) & (h2.cooling)].iloc[0]
    rows.append([f"{xv*100:.0f}", f"{u.e_share*100:.1f}", f"{u.cp:.3f}", f"{u.gam:.4f}", f"{u.y_h2o*100:.1f}", f"{(u.h_index-1)*100:+.1f}",
                 f"{c.coolant_total*100:.1f}", f"{u.eta_th*100:.2f}", f"{c.eta_th*100:.2f}", f"{u.co2_kg_kwh:.3f}"])
table(["H₂ % vol", "H₂ % energy", "cp", "γ", "H₂O mol %", "Heat-transfer index %", "Coolant % (cooled)", "η % uncooled", "η % cooled", "CO₂ kg/kWh"], rows,
      [1.3, 1.5, 1.3, 1.5, 1.5, 2.0, 1.9, 1.7, 1.6, 1.6], fs=8)
fig("figures/fig4_hydrogen.png", 15.0, "Figure 4 — Turbine-side effect of hydrogen at fixed TIT 1,400 °C (simple cycle).")
para("Because the plant stays strongly lean (overall equivalence ratio ≈ 0.45), even pure hydrogen raises exhaust H₂O only from about 9 to 14 mol%. "
     "The consequences for R3 are small: cp rises about 3%, the blade-side heat-transfer coefficient rises about 3%, and coolant demand rises by roughly 0.3 "
     "percentage points of compressor air. Efficiency at fixed TIT improves by under one point, consistent with the problem statement's expectation. "
     "Not captured: gas radiation (also increases with H₂O) and any change in the allowable metal temperature from steam-assisted oxidation; "
     "both would push in the direction of more cooling and should be mentioned as qualitative risks. Note that 30% hydrogen by volume is only "
     f"{h2[(h2.x_h2==.3)].e_share.iloc[0]*100:.1f}% of fuel energy.")

# ------------------------------------------------------------------ 8 material & cooling limit
doc.add_heading("8. Material and cooling limit (stated)", 1)
bullet(" TIT ≤ 1,500 °C (1,773 K), i.e. advanced-class hot-section technology (single-crystal nickel blades with thermal-barrier coating and film cooling) "
       "relative to the 1,400 °C baseline. ASSUMPTION — to be confirmed or replaced with a cited source.", "Firing limit.")
bullet(" Blade metal (TBC-surface) temperature ≤ 1,150 K; total coolant ≤ 25% of compressor air. Beyond that the model returns the design as infeasible "
       "(cooling effectiveness φ ≥ 0.98 or air budget exceeded). ASSUMPTION.", "Cooling limit.")
bullet(" 1,200–1,500 °C for sweeps; designs above 1,500 °C are shown but flagged and excluded from the feasible set.", "Search range handed to R5.")

# ------------------------------------------------------------------ 9 exergy
doc.add_heading("9. Exergy destruction in R3 components", 1)
rows = []
for cfg, T in ((REF, 1673), (SC, 1673), (SC, 1773), (RN, 1673), (RC, 1673)):
    d = g(tit, cfg, T)
    rows.append([cfg.replace(" (team reference)", " (ref.)"), f"{T-273.15:.0f}", f"{d.Xd_turb:.1f}", f"{d.Xd_reheat:.1f}", f"{d.Xd_turb_MW:.1f}",
                 f"{d.Xd_reheat_MW:.1f}", f"{(d.Xd_turb+d.Xd_reheat)/d.X_fuel*100:.1f}", f"{d.X_exit_MW:.0f}"])
table(["Configuration", "TIT °C", "Turbine kJ/kg", "Reheat comb. kJ/kg", "Turbine MW", "Reheat comb. MW", "% of fuel exergy", "Exit exergy MW"], rows,
      [4.6, 1.3, 1.9, 2.2, 1.8, 2.0, 1.9, 1.9], fs=8)
fig("figures/fig2_exergy_tit.png", 16.2, "Figure 5 — Exergy destroyed in the turbine and reheat combustor vs TIT.")
para("Turbine irreversibility is small in the uncooled baseline (about 2.5% of fuel exergy) and grows once coolant is throttled from compressor-exit pressure and mixed into the main stream. "
     "The reheat combustor is a much larger destroyer (about 25–28% of the fuel exergy burned in it), which is the second-law reason reheat lowers simple-cycle efficiency. "
     "Caveat: combustor exergy destruction ignores the chemical exergy of the product mixture, so it is slightly overstated; R2's combustor analysis should use the same convention. "
     "The large exit exergy of the reheat cases is the opportunity R4's regenerator recovers.")

# ------------------------------------------------------------------ 10 cost
doc.add_heading("10. Cost of hot-section, cooling and reheat vs work gained", 1)
rows = []
for cfg, T in ((REF, 1773), (SC, 1773), (RN, 1673), (RC, 1673)):
    d = g(tit, cfg, T)
    rows.append([cfg.replace(" (team reference)", " (ref.)"), f"{T-273.15:.0f}", f"{d.capex_hot_cr:.0f}", f"{d.capex_reheat_cr:.0f}", f"{d.capex_cr:.0f}",
                 f"{d.dW_MW_at_ref_flow:+.1f}", "n/a" if np.isnan(d.Rs_per_extra_kW) else f"{d.Rs_per_extra_kW:,.0f}", f"{d.LCOE:.2f}"])
table(["Configuration", "TIT °C", "Hot-section Rs cr", "Reheat Rs cr", "Total capex Rs cr", "ΔNet MW at same air flow", "Rs per extra kW", "LCOE Rs/kWh"], rows,
      [4.4, 1.3, 2.0, 1.7, 2.0, 2.2, 1.9, 1.8], fs=8)
fig("figures/fig6_cost.png", 16.2, "Figure 6 — LCOE of each configuration (left) and added capex per extra kW against the cost of new baseline capacity (right).")
para("Work gained is measured at the baseline air flow (228.6 kg/s): extra kW = Δw_net × flow × 0.985. A hardware item is worth buying for capacity if it adds a kW for less than the Rs 40,000/kW of new baseline plant. "
     "Higher TIT and uncooled reheat both pass this test (about Rs 12,000–15,000/kW). On LCOE, however, which includes fuel at a 50% load factor, only the higher-TIT simple cycle is neutral to slightly favourable; "
     "reheat adds roughly Rs 1/kWh because of its efficiency penalty. The cooled reheat case adds no net output at 1,400 °C under the assumed cooling model, so no capex-per-kW figure is meaningful.")

# ------------------------------------------------------------------ 11 optima and sensitivity
doc.add_heading("11. R3's individually-optimal designs and sensitivity", 1)
rows = []
for k, r in opt.iterrows():
    rows.append([k, r["config"], f"{r['T3']-273.15:.0f}", f"{float(r['eta_th'])*100:.2f}", f"{float(r['w_net']):.0f}", f"{float(r['LCOE']):.2f}", f"{float(r['coolant_total'])*100:.1f}"])
table(["Objective", "Configuration", "TIT °C", "η %", "w_net kJ/kg", "LCOE Rs/kWh", "Coolant %"], rows, [3.6, 3.4, 1.4, 1.4, 2.0, 2.2, 2.0], fs=8.5)
para("These are the R3-only best cases (feasible, cooled model, at the NG baseline). The team's chosen design will differ because R1, R2, R4 and the NOx, CO₂ and flashback objectives pull in other directions; "
     "in Week 4 compare it here: for each of the four rows above, state the TIT, reheat choice and efficiency / LCOE / exergy given up by the final design.", size=10)
rows = []
for _, r in sens.iterrows():
    rows.append([r["case"], r["parameter"], f"{r.eta_lo:.2f} / {r.eta_hi:.2f}", f"{r.LCOE_lo:.2f} / {r.LCOE_hi:.2f}"])
table(["Case", "Parameter (low / high)", "η % (low / high)", "LCOE Rs/kWh (low / high)"], rows, [3.6, 6.2, 3.0, 3.6], fs=8)
para("Turbine efficiency, cooling calibration and metal temperature matter most (each moves LCOE by about ±0.2–0.4 Rs/kWh). The hot-section cost slope and the reheat capex range barely move the result.")

# ------------------------------------------------------------------ 12 handover + limitations
doc.add_heading("12. Interface for R5 and limitations", 1)
for lead, t in [
    ("Inputs expected: ", "T2 and p2 from R1 (stub in code), hot-gas cp and γ vs hydrogen share from R2 (Cantera-scaled stand-in in code), regenerator preheat from R4 (stub, ε only)."),
    ("Outputs supplied: ", "w_t, w_net, f, η, T_exit and exhaust flow, exergy destruction (turbine, reheat), capex premiums, coolant fraction, feasibility flag."),
    ("Decision variables: ", "TIT (1,473–1,773 K), reheat on/off (reheat temperature = TIT, optimal pressure split computed internally)."),
    ("One property set per case: ", "cp and γ are evaluated once at the final gas composition, so the HP turbine in reheat cases is slightly overstated in cp."),
    ("Cooling model: ", "calibrated, uncited, and the LP turbine is assumed as demanding as the HP turbine; set cooling=False to recover the team reference basis."),
    ("Not modelled: ", "gas radiation, part-load behaviour of the 50% load-factor duty, hydrogen-specific O&M, and the NOx and flashback constraints (R2)."),
]:
    bullet(t, lead)
doc.add_heading("References and method sources", 2)
para("Brayton-cycle, reheat and exergy relations: course material. Cooling model form: Horlock-type convective/film cooling analysis for gas-turbine blading. "
     "Heat-transfer scaling: Dittus–Boelter correlation. Gas properties: Cantera 3.2 with GRI-Mech 3.0 thermodynamic and transport data. "
     "Fuel chemical exergy ratios: Szargut / Kotas-type standard exergy tables. Fuel properties, costs, CRF and baseline numbers: problem statement (Problem 16, §5–6). "
     "Items flagged ASSUMPTION have no external source.", size=9.5)

doc.save("R3_Turbine_Reheat_Report_Section.docx")
print("saved")
