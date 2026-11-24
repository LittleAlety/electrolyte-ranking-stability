# P7 and DMC diagnostic result check — 2026-10-30 Beijing

Independent read-only scientific check. No new jobs, acceptance changes, or cost-ledger settlement in this check. Scheduler and fetched artifacts were verified through the protected WHU bridge.

## Scheduler results

| Element/group | Terminal status | Allocated seconds, 4 cores | Allocated CH |
|---|---|---:|---:|
| EC 3885000_0 | COMPLETED 0:0 | 4191 | 4.6566667 |
| DMC batch 1, 3886404_0–3 | All COMPLETED 0:0 | 142+156+180+167=645 | 0.7166667 |
| DMC batch 2, 3886408_0–3 | All COMPLETED 0:0 | 182+182+200+199=763 | 0.8477778 |
| DMC total | 8/8 terminal success | 1408 | 1.5644444 |

P7 ran 2026-10-29 23:43:34 to 2026-10-30 00:53:25. DMC's last element finished 2026-10-30 00:49:23. Live user queue was empty at inspection. These are calculated costs from terminal sacct, not a claim that production budget ledgers were updated.

## EC p7 frozen QC

Eight fetched artifacts verified using ensemble_hpc_io. Importer `qc_task` was run in memory against the registered ec_v2_p7 candidate.

| Criterion | Value | Frozen threshold | Result |
|---|---:|---:|---|
| Energy change (Eh) | +8.380e-7 | 2e-7 | FAIL, 4.19x |
| RMS gradient | 4.5732e-6 | 8e-6 | PASS |
| MAX gradient | 9.6635e-6 | 3e-5 | PASS |
| RMS step | 7.27354e-5 | 1e-4 | PASS |
| MAX step | 1.71340e-4 | 2e-4 | PASS |

33 frequencies, **0 imaginary modes**, lowest positive frequency **32.30 cm^-1**. Thermochemistry complete at 298.15 K; connectivity, candidate species and bond graph pass; Li denticity 1, single fragment. Final QC: `technical_complete_qc_failed`, `qc_flags=strict_reopt_required`. Do not accept on normal termination or zero imaginary modes alone. Electronic energy -349.77634014 Eh and single-structure G -349.73727849 Eh remain nonaccepted results.

Final geometry SHA256: `17830a4c4cdb6479ff03be07b409c44414025d98da20fdc99ebe80c7a556432d`.
Log SHA256: `80f094abe6aa72f5aa2e2e9369b04b851650be0c256abbf8b716f24beab6c890`.

Snapshot: `work/hpc_ec_recovery_v2_p7_authorized_20261029/tasks/EC/LiM_2plus__ec_v2_p7/snapshots/3885000_0/`.

The EC campaign has exhausted its two permitted real submissions. Any later strict optimization is a new bounded, versioned experiment requiring its own authorization; remaining money does not grant a third attempt.

## DMC adjacent-step diagnostic

Reproducer: `.venv/Scripts/python.exe work/check_dmc_adjacent_results_20261030.py`.
Eight independent receipts and summary: `work/independent_dmc_adjacent_results_20261030/`.

All 8 logs normally terminated, contain complete `.engrad`, and input/start-geometry hashes match the uploaded local package. Runtime charge, multiplicity and electron counts match targets: M_plus +1/doublet/47, LiM_2plus +2/doublet/49. Cartesian gradients are reported here directly, not treated as equivalent to the optimizer's internal-coordinate convergence table. No numerical gradients or optimization were run.

Define delta E = E(Rk1)-E(Rk); delta-delta E = delta E(VeryTightSCF)-delta E(TightSCF).

| State | TightSCF delta E (Eh) | abs(delta E)/TolE | VeryTightSCF delta E (Eh) | abs(delta E)/TolE | delta-delta E (Eh) |
|---|---:|---:|---:|---:|---:|
| DMC M_plus | +1.25068e-6 | 6.2534 | +7.3800e-10 | 0.003690 | -1.249942e-6 |
| DMC LiM_2plus | -4.67304e-9 | 0.023365 | -1.81390e-8 | 0.090695 | -1.34660e-8 |

M_plus max absolute Cartesian gradient: TightSCF 3.45e-5 / 3.35e-5; VeryTightSCF 4.47e-5 / 4.31e-5 Eh/bohr (Rk/Rk1). LiM_2plus: TightSCF 7.44e-5 / 7.76e-5; VeryTightSCF 7.13e-5 / 7.38e-5. All exceed 3e-5 when compared descriptively to the frozen maximum-gradient number; this is not a replacement geometry-QC test.

Spin expectation values: M_plus approximately 0.755384–0.755386, LiM_2plus 0.755094. Similar spin and correct electron counts do not establish identical orbital solutions; occupations/spin densities/orbitals remain a comparison task.

Interpretation: SCF tightening changes the measured M_plus adjacent-step energy difference below TolE for this pair. It does not demonstrate convergence of an optimization, gradient improvement, a valid minimum, or universal noise reduction. LiM_2plus does not reproduce the historical optimizer energy jump in either cold single-point setting; distinguish warm-start history, electronic solution, orientation and coordinate precision before assigning a cause. Six-decimal extracted coordinates remain a limitation. Do not infer TolE impossibility or relax thresholds.

## Next decisions

1. Execution owners settle DMC attempts from terminal sacct and release unused reservation; retain v1 technical failures.
2. Settle p7 with its actual failure and cost while preserving both EC attempts. Existing p4-specific settlement helper is not applicable unchanged.
3. For DMC, prioritize a versioned single-variable VeryTightSCF optimization proposal for M_plus, after electronic-solution comparison and with original thresholds. Do not automatically launch either DMC state.
4. For EC, report p7 as a zero-imaginary-mode candidate with a remaining strict energy-convergence gap; no automatic third campaign leg.

Scientific acceptance remains **45/48**, with EC LiM_2plus and the two DMC states limited. This audit did not rebuild or overwrite scientific delivery tables.
