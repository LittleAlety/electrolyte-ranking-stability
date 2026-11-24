# EC p4 mode 6 independent recheck

Source: task EC/LiM_2plus__ec_v2_p4, snapshot 3853042_0.
Reproducer: `.venv/Scripts/python.exe work/ec_mode6_independent_check.py`.
This audit does not submit jobs or change scientific acceptance or campaign accounting.

## Corrections to the pasted analysis

- `$atoms` exists at line 537 of job.hess. `$act_coord=0` does not mean coordinates are absent.
- Block parsing with explicit column headers and exactly 33 indexed rows recovers mode 6. The first six columns are zero. The previous all-columns-unit-norm claim is false.
- Independent comparison with the NORMAL MODES table in job.log agrees within 4.55e-7 (printed precision).
- These are Cartesian displacement directions, already mass-unweighted. After projecting rigid translations/rotations, the mass-weighted Hessian eigenproblem residual is 1.78e-8 for this interpretation, versus 0.98 if treated as a mass-weighted vector. Do not divide by sqrt(m) again.
- Hessian atoms converted from bohr and properly aligned to job.xyz match within 2.0e-8 Angstrom. Rotate vectors together with geometry.

## Correct mode 6

Raw normalized Cartesian vector norms (dimensionless, not participation probabilities):

| Atom, zero based | Norm |
|---|---:|
| Li10 | 0.797029 |
| O4 | 0.308184 |
| H6 | 0.237352 |
| H9 | 0.235761 |
| H8 | 0.200105 |

The previous H8=0.857, H9=0.509, Li=0.0004 values are not this mode and must not guide rescue construction.

Amplitude is explicitly defined as maximum atomic Cartesian displacement. At 0.1 Angstrom, C1-H8 changes by -0.0000507 / +0.0001472 Angstrom for positive/negative displacement, not 0.087 Angstrom. Li-O4 changes by +0.00585 / +0.00422 Angstrom; C3-O4-Li angle changes by -2.623 / -3.357 degrees. This supports substantial Li-relative angular motion rather than the previous CH-stretch interpretation; it does not prove the physical cause of the negative curvature. Positive/negative angle changes need not be antisymmetric at finite amplitude near a linear arrangement.

Checks at maximum displacement 0.01, 0.02, 0.05 and 0.1 Angstrom agree between Hessian and properly transformed XYZ frames to below 1e-8 for all reported internal coordinates (observed ~7e-14). H6-C0-H7=87.18372777 degrees is reproduced from both original geometries; it is not a frame-reading artifact. Its chemical significance is not established by this audit.

## Original p7: preliminary read-only checks

- Geometry SHA256 matches candidate.json.
- Topology mapping search is exhaustive with 2 mappings for both comparisons.
- Minimum mapped heavy-atom RMSD: p7 versus parent 0.05436091 Angstrom; p7 versus p4 input 0.09345728 Angstrom.
- Non-rigid differences exist. These do not establish independent optimized basins or pass the complete candidate admission contract. Full torsion/donor/close-contact and submission checks remain required.

## Outstanding execution state

The fetched receipt reports COMPLETED, 0:0, 4 cores and 00:55:54; derived allocated-core cost is 3.7266667 CH. The repository lacked a terminal campaign settlement entry point. `scripts/wp_production/settle_ec_campaign.py` now verifies the receipt, all artifact hashes and importer QC before atomically settling the campaign ledger. The entry records `terminal=true`, `accepted=false`, `evidence_complete=true`, `settled_core_hours=3.7266666667`, `qc_flags=strict_reopt_required;imaginary_modes`, energy change 1.0506e-6 Eh and the observed -39.43 cm^-1 frequency. The contract's `next_candidate` now returns `ec_v2_p7`. Three settlement tests pass, including repeat invocation and corrupted-evidence refusal. No new computation was submitted in this audit.

The further p7 geometry check preserves the registered input SHA256 and covalent bond graph. Both p7 and its parent and p4 input have one Li donor site, O4. Maximum absolute differences among the five ring torsions are 13.49 degrees versus the parent and 19.51 degrees versus p4. The nearest *nonbonded* pair is H6-H7 at 1.5800 Angstrom (two hydrogens on the same carbon), followed by H8-H9 at 1.7887 Angstrom. This check finds no evident interfragment close contact but is not a production-level geometry or electronic-identity validation. Different starts remain distinct from distinct optimized minima.
