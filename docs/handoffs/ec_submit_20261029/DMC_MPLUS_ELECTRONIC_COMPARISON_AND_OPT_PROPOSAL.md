# DMC M_plus electronic comparison and bounded optimization proposal

Date: 2026-10-30 Beijing. Design and existing-evidence analysis only. No optimization package activation or new submission.

Reproducer: `.venv/Scripts/python.exe work/compare_dmc_mplus_electronic_solutions.py`.
Inputs: SHA-verified logs and receipts under `work/independent_dmc_adjacent_results_20261030/`, jobs 3886404_0, 3886404_1, 3886408_0, 3886408_1.

## Printed electronic evidence

All four runs have charge +1, doublet, 47 electrons, 24 occupied alpha and 23 occupied beta orbitals. All printed occupation numbers match exactly. The printed table contains 35 alpha and 34 beta orbitals; it is not the complete virtual spectrum or an orbital-coefficient matrix.

| Comparison, same geometry | Max occupation difference | Alpha HOMO/LUMO delta (Eh) | Beta HOMO/LUMO delta (Eh) | Max Mulliken spin delta (e) | Max Loewdin spin delta (e) |
|---|---:|---|---|---:|---:|
| Rk, VeryTightSCF minus TightSCF | 0 | -1e-6 / +1e-6 | +2e-6 / +1e-6 | 5.2e-5 | 3.0e-5 |
| Rk1, VeryTightSCF minus TightSCF | 0 | 0 / -2e-6 | +1e-6 / 0 | 4.2e-5 | 1.5e-5 |

Maximum printed orbital energy changes are 9e-6 Eh for Rk and 6e-6 Eh for Rk1. Occupied frontier indices remain alpha 23, beta 22 (zero-based). VeryTightSCF Rk1: alpha HOMO -0.472383, LUMO +0.045271 Eh; beta HOMO -0.468133, LUMO -0.184298 Eh. Alpha and beta channels must not be combined into a single HOMO/LUMO ordering.

Spin expectations are 0.755384, 0.755385, 0.755386, 0.755386. This combined evidence supports “no appreciable electronic-solution change detected in printed occupations, spectrum and population diagnostics.” It is not proof of identical wavefunctions: integer occupation agreement alone is weak, and orbital character/order identity requires coefficient overlaps with the AO metric (or validated orbital-character evidence). A 1e-3 occupation cutoff is a diagnostic, not a sufficient state-identity acceptance rule.

## Proposed experiment: one M_plus attempt

Hypothesis: with all other declared settings fixed, VeryTightSCF may reduce the SCF-setting contribution to adjacent-step energy differences enough for an optimization to satisfy the existing five thresholds. The diagnostic's ~1694-fold ratio reduction concerns this pair only; it is not a guaranteed optimization speedup or a measured universal noise reduction. Endpoint Cartesian gradients did not improve with SCF tightening.

- Target: DMC|M_plus, +1/doublet, expected 47 electrons.
- Start: the exact registered Rk1 geometry from the completed diagnostic, `work/hpc_dmc_adjacent_step_v2/tasks/production/DMC/M_plus__adj_Rk1/geom.xyz`.
- Geometry SHA256: `a2e5c861ef0afb503a923ea57b41e176686acaecc6cc38eb09e32f156981d3a0`. Do not select another start based on a new energy comparison. Rk1 is the later historical endpoint and the predesignated continuation choice, not a newly discovered basin.
- Precision limitation: this geometry came from a six-decimal printed log, even though the generated XYZ displays extra zeros. It is not a full-precision trajectory checkpoint. Preserve provenance; never claim its historical energy is reproduced by cold-start EnGrad.
- Single physical setting change: TightSCF to VeryTightSCF. Preserve functional, basis, SMD solvent, grid, optimizer, coordinate system, SCF algorithm modifiers, core count and all five thresholds. No trust-radius change or mode perturbation in the same experiment.
- Preserve the original SCF initialization policy. Do not silently introduce MORead from the diagnostic or a different GBW at the same time. Record actual initialization and runtime electronic identity.
- Workflow: analytic-gradient Opt first; parse the final complete geometry convergence table, absolute energy change, identity and normal termination. Only when all five frozen criteria pass, run a fresh AnFreq on that exact final job.xyz under the same numerical settings. This gating change is explicitly versioned and is not hidden inside the single-variable scientific comparison.
- One 4-core allocation with total wallclock at most 4 hours for both stages, maximum reservation **16 CH**. Frequency does not receive another 4-hour allocation. If the time budget is insufficient, record incomplete and stop.
- Resource profile must be a versioned DMC profile; do not reuse the EC-exclusive `orca_production_4h_v1`. Proposed name `orca_dmc_vtscf_4h_v1`, kept HOLD until approved and implemented.
- Funding: propose an explicit production/rescue allocation after terminal accounting is reconciled. Do not charge an Opt+AnFreq run to a screening-only remainder merely because sufficient numbers remain there. 16 CH is the worst-case reservation, not a runtime estimate.

## Result branches and stopping rule

1. Opt passes all five: fresh AnFreq, complete thermochemistry, no imaginary modes, unchanged species/connectivity, correct runtime electronic identity, Hessian-to-final-geometry linkage and file hashes. A candidate passing these checks still needs the project's version/comparability review before its label replaces a frozen-protocol scientific result.
2. Opt stops close-enough or misses any criterion: keep the exact failure vector and ratios, no AnFreq, no automatic restart. Do not interpret the stopped optimizer as proof that no minimum exists.
3. SCF/electronic identity changes: stop and report the comparison as confounded; do not promote it using matching electron count alone.
4. Timeout or technical failure: preserve logs and measured allocated cost. No automatic additional budget or second scientific attempt.

No LiM_2plus optimization is included. That pair's cold-start energy changes were already below TolE for both settings and did not reproduce the historical optimizer jump. Its mechanism needs a separate hypothesis.

## Required implementation before any submission

- A new builder with immutable geometry/input hashes, explicit version/funding/authorization and HOLD gate; a real total-16-CH submission contract.
- Stage driver and tests: a failed energy criterion blocks frequency, negative energy change is checked by absolute value, missing criteria block, first-stage failure/timeout blocks frequency, and frequency references only that attempt's final geometry.
- Electronic checks compare all four existing logs without converting integer occupations into proof of wavefunction identity; absent coefficient evidence remains explicit.
- Terminal cost reconciliation retains prior diagnostics and failed attempts; no resetting historical costs.

Current scientific status remains 45/48. This proposal authorizes no computation and does not relax TolE.
