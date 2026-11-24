# EC p4 authorized submission — 2026-10-29

User request: “能不能请你来写一个包现在提交计算”. Execution was bounded to the existing EC p4→conditional-p7 design. DMC's existing stop ruling remains in force; no DMC, WP6 or pool expansion was submitted.

## Actual scheduler evidence

- Submitted at 2026-10-29 12:58 Beijing (04:58 UTC).
- Job **3853042**, array element **3853042_0** = **EC|LiM_2plus|ec_v2_p4**.
- Live `squeue`/`sacct`: RUNNING, node n0348, AllocCPUS=4, TimeLimit=04:00:00.
- Initial stdout confirms OpenMPI/5.0 loaded, `geom.xyz: OK`, `job.inp: OK`.
- Remote workdir: `/home/pengqihang/project/electrolyte_wp2/hpc_ec_recovery_v2_p4_authorized_20261029`.
- No automatic retry. Unknown submission response must occupy the campaign slot until reconciled.

## Resource and input boundaries

- Profile `orca_production_4h_v1`, 4 cores × 4 hours = **16 CH reserved**; authorized EC campaign cap **32 CH**, at most two submitted elements.
- p7 is isolated reserve, not submitted/registered. Only after p4 reaches a scheduler terminal state, complete scientific QC explicitly fails, and actual costs are settled may p7 be considered. If p4 passes, stop.
- Frozen input unchanged: wB97X-D4/def2-TZVPD, SMD(acetonitrile), Opt VeryTightOpt, AnFreq, TightSCF/SlowConv. No numerical gradients/frequencies.
- Input geometry SHA256: `1c04e3b80f7d5030466964e9ce6f0e426d37225ba6cad4409527676391d597af`.
- Parent optimized `job.xyz` SHA256: `a0a8d53b1e6083c4212d98d844350ce3248c38d201b82f9f3f40936341cd969b`.
- Manifest submission-time SHA256: `6a35fc04f86f31df54780fd89cdd8df08af8cb927aae61fdbb4772e49ba56014`.
- Historical costs retained in original ledgers, not reset. New reservation lives in `work/ec_recovery_v2_campaign/campaign_ledger.json` and the package submission journal.

## Independent preflight and changes

- Read-only reviewer found two original HOLD-package blockers: missing activated candidate and missing manifest members/importer discoverability. Both repaired in a **new** package; original HOLD package unchanged.
- Candidate registration: 121→122; only EC/p4 added; every pre-existing row unchanged. Scientific label bytes unchanged during activation.
- Package remote hashes **17/17 OK**. Importer discovers package and resolves `recovery_v1_start` with original provenance.
- 48 targeted tests passed, covering registration, path escape refusal, real submit-entry contract and campaign contract. Old exact-two registration assertion first failed (RED), then explicitly versioned to the three authorized entries (GREEN).
- Activation loader now permits an explicit package-contained `task_relpath`; historical default remains unchanged. New entry notes cite current authorization, not the old two-leg authorization.
- Bridge directory upload was unsupported; archive extraction was policy-refused. No policy was bypassed: payload was sent using supported per-file `hpc put`, then SHA-verified. Unused upload archive is retained, not deleted.

## Handoff: one writer, actual results before claims

Codex owns this submitted EC attempt. Harness must not submit another p4 or modify its live campaign/journal. Original 12-hour code-hardening task and this new calculation are distinct scopes.

On terminal state: query sacct → fetch immutable artifacts via `ensemble_hpc_io` and verify receipts/hashes → importer QC (absolute TolE and all five frozen criteria, normal termination, SCF, analytical Hessian linkage, imaginary modes, identity) → dedup/coverage → aggregator → actual-cost settlement → downstream rebuild. Successful Slurm termination alone is not scientific acceptance.

Scientific baseline remains 45 accepted / 3 limited until this result is independently accepted. EC acceptance could raise it to 46/48, not 48/48. Current labels are a pre-result snapshot; do not claim all derived outputs are refreshed while the new member is in flight.

No commit or push was performed by Codex in this submission turn; preserve parallel dirty work.
