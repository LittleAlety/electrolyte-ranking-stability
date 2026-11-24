# Original EC p7 submission

- Submitted via the protected `submit_hpc_batch.py` entry, 2026-10-29 23:43 Beijing (15:43 UTC).
- Array job: **3885000**. Unique element: **3885000_0 = EC|LiM_2plus|ec_v2_p7**.
- Live check: RUNNING on n0349, started 2026-10-29 23:43:34 Beijing.
- Local package: `work/hpc_ec_recovery_v2_p7_authorized_20261029`.
- Remote package: `/home/pengqihang/project/electrolyte_wp2/hpc_ec_recovery_v2_p7_authorized_20261029`.
- Journal: package `submission_journal.json`; campaign history: `work/ec_recovery_v2_campaign/campaign_ledger.json`.

## Authorization and budget

This activates the conditional original p7 in the existing user-authorized 32 CH EC campaign. The prior p4 was verified terminal with failed frozen QC and settled at 3.7266666667 CH. The original p7 geometry was preserved, not replaced by a mode perturbation. Exactly one p7 submission was made.

Profile `orca_production_4h_v1`: 4 cores, 4 hours, 16 CH reservation. Campaign remaining after reservation = 32 - 3.7266666667 - 16 = **12.2733333333 CH**. The package-local journal's `remaining_after_core_hours=16` is its local-envelope figure; the shared campaign contract separately includes the prior p4 cost. Do not report the local figure as campaign balance.

## Identity and integrity

- Input geometry SHA256: `4cf903d4ff3afa2165cb696044c862ca1cd7d9e1a59660b3b842b2a7be183133`.
- Input file SHA256: `72608d6b4b2f3be658906c2cf22787cdadcdff4b07f24f6ba2b58391078b48d0`.
- Manifest SHA256: `369601145c64241bb6285af7dc07061b68b34cfa101b6eadda202198c88ffb8e`.
- Batch script SHA256: `f1f8a5b9ecbb21199a3b796a864f7927a2d824006f8b8b0823bf5a095c18c7aa`.
- Input: wB97X-D4/def2-TZVPD, SMD(acetonitrile), VeryTightOpt, TightSCF, SlowConv, Opt AnFreq; charge +2, multiplicity 2.
- Ten payload files passed remote SHA256 verification (plus the checksum file itself uploaded).
- 58 targeted tests passed: candidate activation, EC submit entry, EC contract, generic submission gate.
- Candidate registration rebuilt to include exactly one ec_v2_p7 row; importer resolves the task as pending.

## Ownership and next actions

Codex owns this submitted attempt. Other sessions must not submit another p7, alter its input package, or replace its campaign/journal history.

After Slurm terminal evidence, fetch with:

```powershell
.\.venv\Scripts\python.exe scripts/wp_production/ensemble_hpc_io.py --package work/hpc_ec_recovery_v2_p7_authorized_20261029 --job-id 3885000
```

Verify snapshot hashes, run frozen importer QC, retain all failure flags, settle actual allocated core-hours from terminal accounting, then rebuild scientific consumers when complete. The p4-specific settlement helper must not be used blindly for p7; its current reviewed scope is the failed p4 snapshot.

The campaign contract forbids a third leg. p7 is another preregistered start; whether it avoids p4's failure remains unknown until calculation and QC. Scientific acceptance remains 45/48 at submission time. This submission adds no DMC computation authorization.
