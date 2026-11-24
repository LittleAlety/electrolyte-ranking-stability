# DMC M_plus bounded optimization submission — 2026-10-30

## Actual result of submission

- Unique array **3894976**, element **3894976_0 = DMC|M_plus|Rk1**.
- Started **2026-10-30 12:42:26 Beijing**; independently observed RUNNING, 4 cores, node **n0358**.
- Profile `orca_dmc_vtscf_4h_v1`: one allocation, 4 cores x 4 hours, **16 CH maximum**, paid from the existing 600 CH rescue pool under the explicit DMC-only user ruling.
- New immutable submission package: `work/hpc_dmc_mplus_opt_repaired_v1_20261030`.
- Remote path: `/home/pengqihang/project/electrolyte_wp2/hpc_dmc_mplus_opt_repaired_v1_20261030`.
- Real protected-entry submission journal and mutable attempts ledger are inside that package. Ledger records 16 CH occupancy; no automatic restart or second scientific submission.
- Three-hour checkpoint: **15:42:26 Beijing**. Four-hour Slurm limit: **16:42:26 Beijing**, subject to scheduler enforcement precision. These are execution checkpoints, not a completion guarantee or a claim that an automation was created.

## Bridge environment

PowerShell 7 already exists locally:

`C:\Users\Little Alety\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe`

Version **7.6.5**. Bridge: `E:\软件\超算连接\hpc\hpc.ps1`. Doctor passed. No PowerShell installation, service changes or raw ssh/scp were needed.

## Why the original package was preserved

`work/hpc_dmc_mplus_opt_v1` had no real submission journal or remote job, despite manifest `submitted=true` and a pending planning entry. Independent review found missing manifest batches, wrong `%scf` placement of EnforceStrictConvergence, missing VeryTightOpt, nonexistent ORCA module, unsafe Slurm task/core combination, missing task working directory, YES/NO parsed as numbers, and frequency tied to the original start geometry. The original files and planning records were retained unchanged. This repair is the same authorized single experiment, not an extra scientific attempt.

## Reviewed repair

Reviewer `dmc_staged_review` reported no remaining Critical/Important blockers for this bounded computation. Test-first driver implementation: initial 8 failing cases before implementation; final **11 targeted tests pass**, including protected-submit mock, persisted16CH, duplicate refusal, absolute negative delta energy, missing/frozen tolerance checks, electronic identity, failed-opt and timeout blocking frequency, new-final-geometry linkage and a shared decreasing wallclock. Bash syntax check passed. Thirteen payload files passed remote SHA256 checks.

Wider existing submitter tests have eight failures caused by old fixtures lacking generic gate fields or reusing already-submitted machine-local packages; those unrelated files were not changed. This is not a repository-wide ALL GREEN statement.

New driver: `work/dmc_staged_opt_driver_v2.py`; builder: `work/build_dmc_mplus_repaired_20261030.py`; tests: `tests/test_dmc_staged_opt_driver.py`.

## Actual startup evidence

Read back the running `opt/job_opt.log` through the bridge. It echoes:

- `VeryTightSCF`, `VeryTightOpt`, wB97X-D4/def2-TZVPD, SMD(acetonitrile).
- **Strict Convergence .... True**.
- TolE2e-7, TolMAXG3e-5, TolRMSG8e-6, TolMAXD2e-4, TolRMSD1e-4.
- Charge **1**, multiplicity **2**, electron count **47**.
- Starting XYZ SHA256 `a2e5c861ef0afb503a923ea57b41e176686acaecc6cc38eb09e32f156981d3a0`.

Manifest SHA256 at submit: `8f58c873ae8b28aa7203139e969dc4d6b1e3f372211a44e98848560069a9497c`.
Batch script SHA256: `c492450dc3a58a5e9e07bf798deb6fc660399c6d3de10c01db38235e6fc482ad`.

## Two-stage evidence and scientific boundary

Attempt path: `tasks/DMC/M_plus__opt_Rk1/attempts/3894976_0_0/`.

- `opt/job_opt.inp`, `opt/job_opt.log`, `opt/job_opt.stderr`, `opt/job_opt.xyz`.
- `opt_qc.json` only after frozen five criteria and species checks pass.
- Then `freq/geom.xyz` is a byte copy of that attempt's optimized endpoint; `freq/job_freq.inp`, log, stderr and new Hessian remain separate.
- `workflow_result.json` records status/reason and both-stage hashes. Frequency can use only the remaining time in the same allocation. No geometry exporter or fake concatenated joint log is used.
- `scientific_import_gate=HOLD_until_staged_receiver_and_final_QC`: successful process execution alone cannot promote acceptance. Retain each stage; build/verify the staged receiver and Hessian linkage before downstream rebuild.

At terminal state, recover these staged artifacts with remote hashes, classify failures as explicit outcomes, settle using sacct AllocCPUS x ElapsedRaw, retain all old costs and release only the measured unused reservation. Do not apply the old joint-log importer blindly.

Submission ownership is Codex. Parallel sessions must not submit the original package, duplicate the repair, change live inputs, or reset its budget/journal. No EC strict experiment was submitted by this action. Scientific acceptance remains **45/48** pending real results.

The generic submitter currently tags persisted entries `diagnostic_only=true`; this is inaccurate for Opt+AnFreq. The new package's own mutable ledger has been corrected to `false` with explicit production-rescue experiment identity, without changing its16CH occupancy. The shared helper was left untouched to avoid overlapping another writer.
