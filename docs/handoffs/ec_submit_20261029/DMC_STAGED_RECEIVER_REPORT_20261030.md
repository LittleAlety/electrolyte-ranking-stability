# DMC staged receiver — implementation, audit fixes and comparability scope (2026-10-30, rev 2)

Sidecar receiver only. No production file was modified, no calculation submitted, no
acceptance label changed. Formal scientific status remains **45/48**.

## Revision 2: the four audit holes, each now a failing test

The independent audit of rev 1 found four admission-gate holes. Each was reproduced, fixed,
and is now covered by a **negative test that refuses**. Test count: **25/25 passing**.

| # | Hole in rev 1 | Fix in rev 2 | Refusal code | Test |
|---|---|---|---|---|
| 1 | empty/partial `expected_hashes` was accepted, so unverified stages slipped through | the trusted set must cover **all seven** stage files; empty or partial set refuses before any parsing | `HASHES_INCOMPLETE` | `test_empty_hash_set_refuses`, `test_partial_hash_set_refuses` |
| 2 | method/job shape was hard-coded in the record; an input saying `HF`, or a freq input with `AnFreq` deleted, still produced "wB97X-D4 / AnFreq" | `parse_input_contract()` reads the `!` line of **both** inputs and records what is actually declared; any mismatch with the frozen contract refuses | `INPUT_CONTRACT_MISMATCH` | `test_swapped_functional_in_input_refuses`, `test_missing_anfreq_flag_in_freq_input_refuses`, `test_numfreq_in_freq_input_refuses` |
| 3 | thermochemistry was only checked for non-emptiness (350 K, 2 atm, `qRRHO False` passed) | frozen settings enforced: **298.15 K, 1.00 atm, qRRHO True** | `THERMO_SETTINGS_MISMATCH` | `test_wrong_temperature_refuses`, `test_wrong_pressure_refuses`, `test_qrrho_false_refuses` |
| 4 | Opt log was bound to `job_opt.xyz` by element order only, so a 0.05 Å shift of the log's last coordinate block passed | the last `CARTESIAN COORDINATES (ANGSTROEM)` block is compared **numerically** component-wise against `job_opt.xyz`, must agree within **1e-5 Å** (measured 4.812e-7 Å on the accepted attempt) | `FINAL_GEOMETRY_DISAGREES` | `test_log_last_coordinate_moved_but_same_symbols_refuses` |

Rev 1's other gates are unchanged and still covered: five criteria from raw text with
printed-tolerance equality, strict echo, absolute ΔE, species/bond graph, 3N mode
completeness, stage byte linkage, Hessian geometry invariant, rotated-frame acceptance,
identity, fake-`workflow_result` refusal and idempotent import.

The record now carries the **parsed** contract (`protocol.parsed_inputs.opt/freq`,
`protocol.physical_method`, `protocol.numerical_settings` derived from those tokens) plus
`stages.opt.log_geometry_max_delta_a`, so the declared method can never be asserted
independently of the bytes.

**These were admission-gate holes; they do not negate the measured DMC result.** The real
evidence still passes every gate under rev 2 and the staging record was regenerated.

## Artifacts

| Artifact | Path |
|---|---|
| Receiver | `work/dmc_staged_receiver.py` |
| Tests (25) | `work/test_dmc_staged_receiver.py` |
| Staging record | `work/dmc_mplus_evidence_20261030/STAGING_RECORD.json` |
| Staging ledger (append-once) | `work/dmc_staged_staging_ledger.json` |

Staging record: `status = qc_passed_candidate_staged`,
labels `numerical_qc=passed / protocol_comparability=pending / coverage_acceptance=pending`,
`protocol_version = dmc_vtscf_strict_v1`.

Measured content (unchanged by the fixes): five criteria 1.133e-7 / 7.0307e-6 / 2.8069e-6 /
1.915971e-4 / 6.09166e-5; 36 modes = 3N, 30 positive, **0 imaginary**, lowest **76.38 cm⁻¹**;
E −343.54458661 Eh, G −343.48565115 Eh (both from the frequency stage); cross-stage
same-geometry FSPE difference **7.86322e-7 Eh** recorded as a measured discrepancy.

## Comparability yardstick — corrected

Rev 1 quoted the wrong repository figure. Current facts, with sources:

| Quantity | Value | Where | Scope |
|---|---|---|---|
| Active-learning **stop endpoint** | **O₃ ≥ 2/3 and R₃ ≤ 0.10 eV** | `scripts/build_physics_completion_batch.py:3888`, `NEW_ENDPOINT_R3_EV="0.10"`; `docs/63_week42_wp5_delta_learning_active_query.md:11`; `docs/PROJECT_GUIDE.md:139` | the project's current stopping rule |
| 3→6 sampling-stability tolerance | 0.10 kcal/mol, frozen 2026-10-21 (basis B) | `scripts/wp_production/build_tolerance_preregistration.py:103–111,217` | a *different* frozen tolerance for sampling stability |

Neither is a protocol-comparability tolerance, and neither may be reused as one. 0.10 eV
= 3.6749e-3 Eh; 0.10 kcal/mol = 1.5929e-4 Eh.

For scale only (not as a pass/fail rule), the measured SCF-setting single-point shifts at
the two existing endpoints are:

| Endpoint | shift (VeryTight − Tight) | shift / 0.10 eV | shift / 0.10 kcal mol⁻¹ |
|---|---:|---:|---:|
| Rk | +1.326035e-6 Eh | 3.6e-4 | 8.3e-3 |
| Rk1 | +7.6093e-8 Eh | 2.1e-5 | 4.8e-4 |

These ratios describe magnitude only. **A small energy difference does not by itself
approve protocol comparability, does not establish that vibrational/thermal corrections are
equivalent, and cannot promote the candidate to accepted.**

## Endpoint single point — design retained, still unauthorised

- Geometry: the new optimized endpoint `5b0fc24d033b5f8a80f4609739fb7534089a8920d0daaeecf522b0839282c367`.
- Content: **one** single point under the frozen method with `TightSCF` (frozen-protocol SCF),
  identical basis/SMD/grid; then compare energy, printed occupations, spin and frontier
  orbitals against the existing same-geometry VeryTightSCF run.
- Shape: 4 cores × 5 min ⇒ worst case **1/3 CH** (0.3333), and the reservation must not be
  rounded down below that.
- Stopping: timeout or incomplete evidence stops it; no automatic continuation.
- Reporting: measured differences only; no comparability verdict is derived from the gap.
- Budget: a **new, explicitly approved** calculation; the released 14.48 CH must not be used.

## Order of execution (agreed)

receiver fixes + negative tests → **independent re-audit** → freeze the comparability
criterion → obtain approval → endpoint single point → dedup/coverage → aggregation and
downstream rebuild. Only after those gates does 45 → 46 become discussable; no label is
edited directly.

## Still open

1. Independent re-audit of rev 2 (the audit agent that found the four holes).
2. Promotion into `scripts/wp_production/` **only after** that re-audit, with the four-place
   registration duty.
3. Comparability criterion freeze + approval of the 1/3 CH endpoint single point.
4. Dedup and coverage review through the generators, then aggregation.

## Revision 3: second-round audit blockers, each now a failing test

The second audit reproduced four further blockers. All four are fixed; **34/34 tests pass**;
the record schema is now `dmc_staged_receiver/v3` and the staging record was regenerated.
The real evidence still passes every gate.

| # | Blocker reproduced in rev 2 | Fix in rev 3 | Refusal code | Test |
|---|---|---|---|---|
| 1 | the optimized endpoint could be substituted for the registered Rk1 start and still be labelled Rk1 | `expected_start_sha256` is **mandatory** and checked against the start bytes before parsing | `START_GEOMETRY_UNTRUSTED` | `test_swapped_start_geometry_refuses`, `test_missing_declared_start_hash_refuses` |
| 2 | identity parameters were optional, so two logs changed to a wrong electron count still "verified" each other | `expected_identity` is **mandatory** (missing field refuses) and is cross-checked against **both logs** and **both inputs'** `* xyzfile <charge> <mult>` line | `IDENTITY_NOT_DECLARED`, `IDENTITY_MISMATCH` | `test_identity_not_declared_refuses`, `test_both_logs_wrong_electron_count_refuses`, `test_input_declared_charge_mult_must_match` |
| 3 | the input kept the frozen method while the log ran another method | the `\|  n> ! …` line ORCA echoes is parsed and must state the same functional/basis/solvent/SCF/job type as the input contract | `LOG_METHOD_MISMATCH`, `LOG_INPUT_ECHO_MISSING` | `test_log_method_must_match_input_method`, `test_log_echo_missing_refuses` |
| 4 | `NumGrad` was not forbidden | `NumGrad`/`NumFreq` refused in both inputs; the Opt stage must actually request the frozen preset (`VeryTightOpt` **or** explicit `%geom` tolerances equal to the five frozen values) | `INPUT_CONTRACT_MISMATCH` | `test_numgrad_in_opt_input_refuses`, `test_missing_verytightopt_or_geometry_tolerances_refuses` |

The preset requirement directly encodes the EC-class packaging bug (Opt without the frozen
preset while the log still echoes `Strict Convergence .... True`): a package that drops
`VeryTightOpt` cannot reach a passing record.

### Updated status

| Item | State |
|---|---|
| `work/dmc_staged_receiver.py` | rev 3, sidecar |
| `work/test_dmc_staged_receiver.py` | **34/34 passing** |
| Staging record | regenerated, `qc_passed_candidate_staged`, three axes still pending/pending |
| `scripts/wp_production/` | **not** promoted |
| Formal tables / acceptance | unchanged, **45/48** |