# DMC staged receiver decision and exact handoff

Decision: proceed with staged receiver implementation using existing evidence only. Register this as a distinct numerical/workflow variant of the frozen physical method, not an undeclared replacement of old records. No new calculation authorization is issued here; acceptance remains unchanged until protocol comparability, receiver QC, dedup and coverage are complete.

## Verified input evidence

Owned allocation 3894976_0 completed 0:0, 4 cores, ElapsedRaw1368, actual cost1.52CH. Codex settled the repaired package's active attempts ledger and released14.48CH from its16CH reservation using current sacct and per-element mapping. Scientific labels were not changed.

Reverified all13 files in `work/dmc_mplus_evidence_20261030/RECOVERY.json` against disk hashes. Applied existing `validate_hessian_geometry_invariant` to the actual freq Hessian `$atoms` and final XYZ with existing5e-6 Angstrom tolerance: passed. Stage XYZ byte identity alone is NOT proof that the Hessian belongs to that geometry.

Existing `parse_thermo` returns36 total frequencies (30 nonzero vibrations), zero imaginary modes, lowest positive76.38cm^-1, qRRHOTrue, temperature298.15K, pressure1atm, electronic E=-343.54458661Eh, G=-343.48565115Eh. Preserve full precision raw energies in additional evidence fields. Do not mislabel30 as a3N-incomplete result; do not count only positive modes to prove completeness.

Opt/Freq same-geometry electronic energy difference about7.86e-7Eh is a measured numerical discrepancy, not the optimization's successive-step DeltaE. Record both energies and the difference. Do not overwrite either, call it zero, apply TolE as an unregistered cross-stage tolerance, or infer electronic-state equality from electron count alone.

## Protocol representation

Keep separate metadata fields for physical method (wB97X-D4/def2-TZVPD/SMD acetonitrile), numerical settings (VeryTightSCF), geometry-stop policy (EnforceStrictConvergence), and layout (staged Opt->AnFreq). Physical method and all five acceptance thresholds remain frozen. A versioned QC-passed candidate can be stored before global comparability is decided; it must not become accepted solely because a receiver succeeds.

Do not assert that this run isolates the SCF effect: stricter stopping and SCF precision changed together. State that this declared combination succeeded in the measured attempt.

## Receiver implementation contract for the execution owner

1. Implement a receiver that reads the two original input/log pairs plus start/final XYZ, actual Hessian and scheduler evidence; verify trusted source hashes before parsing. Never concatenate logs or relabel a frequency-only file as joint Opt+AnFreq.
2. Recompute five convergence criteria from raw Opt text, including strict echo, absolute DeltaE and exact frozen tolerances. Recompute normal/error status, runtime charge/multiplicity/electrons, atom order/species/connectivity in each appropriate stage. `opt_qc.json`/`workflow_result.json` are corroboration, not authoritative QC.
3. Verify exact Opt-final->Freq-start bytes and actual Hessian-to-geometry invariant linkage. Parse complete36-frequency data and full thermochemistry with the existing parser. Derive E and G consistently from the frequency stage; do not combine Opt E with Freq thermal correction.
4. Emit separate opt_input/log hashes, freq_input/log hashes, final geometry and Hessian hashes, stage energies and DeltaE, numerical-protocol version, and explicit `protocol_comparability=pending` until reviewed. Preserve absence as absent.
5. Add negative tests: missing stage, mutated input/log, wrong Hessian geometry, failed/negative DeltaE exceeding threshold, truncated modes, malformed thermochemistry, wrong runtime identity and fake workflow success all refuse QC. Idempotent repeated import must not double-count a member or cost. Test a genuinely rotated Hessian frame remains accepted by the existing invariant validator.
6. First emit a sidecar/staging record only; then review schema/consumer changes before registering this new numerical variant in the formal candidate/structure tables. Separate axes: numerical QC pass, protocol comparability, coverage acceptance. Run dedup and coverage only through generators, retaining historical limited reasons and attempts.

## Comparability review scope

Use existing same-geometry TightSCF/VeryTightSCF diagnostics and printed occupation/spin comparisons first. Identify which claims apply to Rk/Rk1 and which still lack endpoint-specific evidence. Judge whether current evidence supports the project's formal comparison accuracy; do not demand an entire cohort rerun automatically or invent a tolerance after seeing results. If a final-geometry paired calculation is required, present it as a separate bounded proposal rather than spending the released14.48CH automatically.

Single writer: execution owner builds the receiver; Codex independently verifies the output evidence. Current scientific acceptance stays45/48 until the above consumer path is complete.
