# STAGE 1 — Ground truth (independent recomputation)

Auditor: crosscheck agent (`audit_partial_crosscheck_20261026`).
Date of work: 2026-10-26 (session). Read-only w.r.t. all existing files.
Purpose: independently establish the CURRENT state of the 16 sampling-audit items
directly from the repo's own products/sources, so the other member's report can be
cross-checked against ground truth — not against the task's background hypothesis.

## Environment note (write path)
The `pwsh` tool runs this session at **Low mandatory integrity** (token group
`Mandatory Label\Low Mandatory Level Label`, S-1-16-4096). The target folder
`docs/handoffs/four_state_recovery_20261023/` is default Medium IL with DACL
`NT AUTHORITY\Authenticated Users:(I)(M)` but mandatory-integrity "no-write-up"
blocks a Low-IL process from creating files there. Evidence:

```
New-Item ... audit_partial_crosscheck_20261026  -> Access to the path ... is denied  [exit code: 1]
[System.IO.File]::WriteAllText(...) -> Access to the path ... is denied.            (WRITE FAIL)
```
Consequence: `pwsh` is used READ-ONLY (analysis only). All file creation uses the
`write`/`edit` tools (harness at Medium IL), which succeed and auto-create the dir:

```
write docs/.../audit_partial_crosscheck_20261026/_scratch_probe.md  -> Created file
```

## The generator and its products
Script (334 lines): `scripts/wp_production/build_sampling_audit_3to6.py`.
Inputs it reads:
- `outputs/physics_completion/sampling/sampling_conformer_set.csv` (free conformers)
- `outputs/physics_completion/li_motif_sampling/li_motif_screen.json` (round-1 Li screen)
- `outputs/physics_completion/li_motif_sampling/li_motif_round2_exec_index.json` (round-2 Li exec)
- `outputs/physics_completion/ensembles/production_ensemble_structures.csv` (primaries)
Outputs it writes:
- `outputs/physics_completion/sampling/sampling_audit_3to6.csv`
- `outputs/physics_completion/sampling/sampling_audit_3to6.md`
- `outputs/physics_completion/sampling/sampling_audit_index.json`
Constants: window 6.0 kcal/mol, round1 cap 3, round2 ceiling 6, molecules EMC/DEC/DME/TMP,
states M / M_plus / LiM_plus / LiM_2plus.

## Commands actually run (with actual exit codes)

### C1 — confirm generator exists
```
Test-Path "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\scripts\wp_production\build_sampling_audit_3to6.py"
-> True        (exit 0)
```

### C2 — directory create via pwsh (expected to fail under Low IL) 
```
New-Item -ItemType Directory -Force -Path ".../audit_partial_crosscheck_20261026"
-> Access to the path ... is denied.   [exit code: 1]
```

### C3 — independent recomputation from sources (my own csv.DictReader logic, no import of repo script)
```
& .venv\Scripts\python.exe -B docs/handoffs/four_state_recovery_20261023/audit_partial_crosscheck_20261026/stage1_recompute.py
-> EXITCODE=0
```
Actual output (abridged to the decisive lines):
```
SECTION A: exec_csv exists = True ; hash check = ('MATCH', 'e587000bfb93580f75723a93528b5b8708f6e2f37f696b862cb65f37a5b47c4f')
SECTION B: (my 16 rows)
EMC | M      | free_conformer           | round1=2 | pool=2 | ceil=2 | sampling_limited
EMC | M_plus | free_conformer           | round1=2 | pool=2 | ceil=2 | sampling_limited
EMC | LiM_plus     | li_motif_round2_measured | round1=2 | pool=4 | ceil=4 | executable_partial
EMC | LiM_2plus    | li_motif_round2_measured | round1=1 | pool=2 | ceil=2 | executable_partial
DEC | M      | free_conformer           | round1=3 | pool=3 | ceil=3 | sampling_limited
DEC | M_plus | free_conformer           | round1=3 | pool=4 | ceil=4 | executable_partial
DEC | LiM_plus     | li_motif_round2_measured | round1=2 | pool=4 | ceil=4 | executable_partial
DEC | LiM_2plus    | li_motif_round2_measured | round1=1 | pool=2 | ceil=2 | executable_partial
DME | M      | free_conformer           | round1=3 | pool=6 | ceil=6 | executable
DME | M_plus | free_conformer           | round1=3 | pool=4 | ceil=4 | executable_partial
DME | LiM_plus     | li_motif_round2_measured | round1=1 | pool=1 | ceil=1 | sampling_limited
DME | LiM_2plus    | li_motif_round2_measured | round1=1 | pool=3 | ceil=3 | executable_partial
TMP | M      | free_conformer           | round1=2 | pool=2 | ceil=2 | sampling_limited
TMP | M_plus | free_conformer           | round1=3 | pool=3 | ceil=3 | sampling_limited
TMP | LiM_plus     | li_motif_round2_measured | round1=2 | pool=5 | ceil=5 | executable_partial
TMP | LiM_2plus    | li_motif_round2_measured | round1=2 | pool=3 | ceil=3 | executable_partial
SECTION C: my by_status tally = {'sampling_limited': 6, 'executable_partial': 9, 'executable': 1}  total=16
SECTION E: non-executed legs: NONE (all 8 executed)
SECTION F: product by_status = {'sampling_limited': 6, 'executable_partial': 9, 'executable': 1}  total=16
           total field diffs (mine vs product) = 0
SECTION G: index states = 16  index by_status = {'sampling_limited': 6, 'executable_partial': 9, 'executable': 1}
           index generated_at_utc = 2026-10-25T04:31:38Z
```

### C4 — repo's own read-only self-check (recompute-in-memory, never writes)
```
& .venv\Scripts\python.exe -B scripts/wp_production/build_sampling_audit_3to6.py --check
-> CHECK OK -- sampling audit outputs match recomputation
-> EXITCODE=0
```

### C5 — Li pool wiring: pool = max(LI_SCREEN in-window, round-2 measured_ceiling)
```
& .venv\Scripts\python.exe -B docs/handoffs/four_state_recovery_20261023/audit_partial_crosscheck_20261026/stage1_liscreen.py
-> EXITCODE=0
leg | screen_in_window | measured_ceiling | max()=pool | driven_by       | meas==round1_kept+new?
DEC|LiM_2plus | 1 | 2 | 2 | measured_ceiling | 2==1+1 -> True
DEC|LiM_plus  | 2 | 4 | 4 | measured_ceiling | 4==2+2 -> True
DME|LiM_2plus | 1 | 3 | 3 | measured_ceiling | 3==1+2 -> True
DME|LiM_plus  | 1 | 1 | 1 | measured_ceiling | 1==1+0 -> True
EMC|LiM_2plus | 1 | 2 | 2 | measured_ceiling | 2==1+1 -> True
EMC|LiM_plus  | 2 | 4 | 4 | measured_ceiling | 4==2+2 -> True
TMP|LiM_2plus | 2 | 3 | 3 | measured_ceiling | 3==2+1 -> True
TMP|LiM_plus  | 2 | 5 | 5 | measured_ceiling | 5==2+3 -> True
```

## GROUND TRUTH (established this session, three independent ways agree)
- **16 states.** `by_status`: **executable = 1, executable_partial = 9, sampling_limited = 6.**
- The single `executable` is **DME / M** (pool 6 = ceiling 6).
- **Li pools** (`pool_independent_minima`): EMC|LiM_plus **4**, EMC|LiM_2plus **2**,
  DEC|LiM_plus **4**, DEC|LiM_2plus **2**, DME|LiM_plus **1**, DME|LiM_2plus **3**,
  TMP|LiM_plus **5**, TMP|LiM_2plus **3**.
- **All 8 Li legs are `status=executed`** with parents verified (2/2, 3/3, 6/6, 2/2 …).
  **No leg failed the parent-hash check; none is "held at round-1".**
- Li pool is driven by the **round-2 measured ceiling** for every leg, and
  `measured_ceiling == round1_kept + new_independent_basins` holds for all 8.
- Round-1 Li counts use the leg's real `round1_kept_motifs` (e.g. DME|LiM_2plus round1=1).
- `li_motif_round2_exec.csv` sha256 MATCHES `exec_csv_sha256` in the index
  (`e587000b…`), so `build_sampling_audit_3to6.py` would NOT raise the stale-CSV SystemExit.
- Products are NOT stale: repo `--check` = CHECK OK (exit 0); my recompute = 0 diffs.
- `sampling_audit_index.json` `generated_at_utc = 2026-10-25T04:31:38Z`.

## The task's background HYPOTHESIS vs this ground truth (for Stage-2 priming)
| # | Hypothesis claim | Ground truth | Verdict |
|--c--|--c--|--c--|--c--|
| H1 | 1 executable (DME/M) | 1 executable = DME/M | AGREE |
| H2 | 7 executable_partial | 9 executable_partial | **DISAGREE** (actual 9) |
| H3 | 8 sampling_limited | 6 sampling_limited | **DISAGREE** (actual 6) |
| H4 | DEC|LiM_plus 4 | 4 | AGREE |
| H5 | DEC|LiM_2plus 2 | 2 | AGREE |
| H6 | DME|LiM_plus 1 | 1 | AGREE |
| H7 | DME|LiM_2plus 3 | 3 | AGREE |
| H8 | TMP|LiM_plus 5 | 5 | AGREE |
| H9 | TMP|LiM_2plus 3 | 3 | AGREE |
| H10 | EMC legs held at 2/1 (stale parent hash) | EMC|LiM_plus=4, EMC|LiM_2plus=2, both executed, 2/2 parents verified; NO stale parent hash anywhere | **DISAGREE** |
| H11 | (code logic) Li pool from measured ceiling = round1 retained + genuinely new basins | confirmed for all 8 legs | AGREE (logic) |
| H12 | (code logic) round-1 counts use leg's real retained number | confirmed | AGREE (logic) |
| H13 | (code logic) hash-fail legs keep round-1 pool + annotated | code path exists (build…py L199-204) but is NOT triggered by current data (all executed) | code AGREE / current-data: not triggered |

This hypothesis is therefore partly wrong on the current products (H2, H3, H10). Any
statement in the other member's report that repeats 7/8 or "EMC held 2/1" would be a
DISAGREE. Statements matching the 1/9/6 and the per-leg numbers above would AGREE.

## Stage-1 enrichment — cost/count numbers & hashes (for Stage-2 assertions)
Command: `& .venv\Scripts\python.exe -B .../stage1_extra.py` -> EXITCODE=0

**(a) Input SHA256 — all four MATCH `sampling_audit_index.json`:**
- sampling_conformer_set.csv = `b4665e14dc3f2cc337e2229190115f52f98725be09bec1f49d0b7099b91b4f4c`
- li_motif_screen.json = `0a886c1469f771ec0f7ba2a48cf854e11b7c3c0056f68170a568dd414b58d595`
- li_motif_round2_exec_index.json = `93d34fbfaf11abe854d5d2ea66a6c3d652b42dabae68b2e83e562564f7e5dfa6`
- production_ensemble_structures.csv = `51f671a6d6385c53e0695dcdb8270e5078053b17dfb4b430bccff949b316d5ec`

**(b) round-2 exec CSV** `li_motif_round2_exec.csv`: 214 rows; status tally
`{ok: 213, execution_failed: 1}`; sha256 = `e587000bfb93580f75723a93528b5b8708f6e2f37f696b862cb65f37a5b47c4f`
(matches `exec_csv_sha256`). The single `execution_failed` is consistent with the
DME|LiM_2plus leg `n_ok=35 / n_candidates=36` in the round-2 index.

**(c) round-2 index `totals` block:** `{legs: 8, candidates: 214, ok: 213,
kept_motifs: 19, new_independent_basins: 12, collapsed_onto_round1: 7,
rejected_parents: 0, legs_above_registered_bound: 1}`; `n_checks=9, n_failed=0`.

**(d) free-conformer window counts / round1-selected (from `sampling_conformer_set.csv`,
columns incl. rel_kcal, selected_round1):**
- EMC|M 2/2 ; EMC|M_plus 2/2 ; DEC|M 3/3 ; DEC|M_plus 4/3 ; DME|M 6/3 ; DME|M_plus 4/3 ; TMP|M 2/2 ; TMP|M_plus 3/3
  (format = window_count / round1_selected). All match the product's pool/round1 columns.

## Independent stale-statement already located (Stage-2 class ii candidate)
`outputs/physics_completion/compliance/plan_compliance.csv`, item `wp2_sampling_extension`
(row 14), note currently states (Chinese) "3->6 升级对全部态仍是 registered_pending …
要等第 1 轮生产自由能才能判定 sampling_limited". That contradicts the CURRENT
`sampling_audit_3to6.csv`, where all 16 states already carry a concrete status
(1 executable / 9 executable_partial / 6 sampling_limited) and no state is
`registered_pending`. So this compliance note is STALE w.r.t. the sampling-audit product.
(Whether the other member's report cites this exact line is unknown until the report lands.)
