R3 COMPLETE DELIVERABLES
========================

This package is organized in the style of the supplied R3_code_results.zip.

MAIN COMPUTATIONAL FILES
- r3_turbine_reheat.py: turbine/reheat subsystem model.
- run_r3_sweeps.py: parameter sweeps and plot generation.
- build_report.py: report-generation script.

COMPUTATIONAL OUTPUTS
- results/: CSV outputs from the supplied computational reference package.
- figures/: six sweep/result figures from the supplied computational reference package.

REPORT
- R3_Turbine_and_Reheat_Report.pdf: technical report prepared from the two Problem 16 source documents.

SUPPORTING SOURCE-GROUNDED ASSETS
- supporting_data/: CSVs containing problem-statement inputs, baseline hand calculation,
  reheat hardware cost calculation, and unspecified design inputs.
- supporting_diagrams/: original conceptual cycle and blade-cooling illustrations.

IMPORTANT MODEL / ASSUMPTION NOTE
The supplied reference computational model contains explicitly marked modelling assumptions,
including cooling-model calibration, blade-metal temperature, cooling effectiveness,
coolant calibration, hot-section cost slope, reheat pressure-loss treatment, and a
1,500 deg C firing-temperature limit. These are assumptions in the computational
reference package, not values stated in the two Problem 16 source documents.
Review and obtain team/instructor agreement before treating those assumptions as
the team's final design limits.

The source documents specify the natural-gas baseline TIT as 1,400 deg C (1,673 K),
turbine efficiency 0.90, hot-gas cp 1.15 kJ/kg K, gamma 1.333, and the other
baseline values listed in the report. The supporting_data folder preserves those
source-grounded values separately.

The computational reference package uses Cantera in its hot-gas property routine.
Install the dependencies listed in the Python files / your environment before running.
