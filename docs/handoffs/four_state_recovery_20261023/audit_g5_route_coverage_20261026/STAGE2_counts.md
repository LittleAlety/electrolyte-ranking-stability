# STAGE 2 — Real row counts per route + test-reference census

All commands below were run in this session. The CSV was opened **read-only**
(`open(path)` + `csv.DictReader`, no write mode) and was **not** rewritten.

**CSV under measurement:**
`E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\outputs\physics_completion\recovery\coverage_reviews.csv`
— 4828 bytes, mtime 2026/10/25 12:31:31 (unchanged before/after this stage),
sha256 `6CD5E92EDE14B910ED4555DCC5B1A187618245276B1231B55255B5192F3A0F80`.

---

## 2.1 Column-name check (question 2, "if the file has a different column name for the route, say so")

**The column is named exactly `route`.** `csv.DictReader.fieldnames` returned:

```
['review_id', 'batch_id', 'name', 'state', 'historical_limitation',
 'historical_n_limited', 'resolution_path', 'route', 'kept_pool_evidence',
 'registered_starts', 'computed_new_members', 'n_unique_after', 'verdict',
 'review_version', 'evidence_note']
```

So no column-name divergence: `route` and `verdict` are separate columns, and the
script's `FIELDS` (build_coverage_reviews.py:63-69) matches the header exactly.
The script writes `route` = `verdict_route` (line 399) and `verdict` = `verdict`
(line 404), i.e. the two are emitted independently, which is what makes a
route/verdict mismatch observable in this file.

---

## 2.2 The exact counting command and its ACTUAL output

Command (run via the `pwsh` tool; venv python, `-B`, read-only):

```
& "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\.venv\Scripts\python.exe" -B -c "<python one-liner>"
```

with the python one-liner being:

```python
import csv,collections,sys
p=r'E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\outputs\physics_completion\recovery\coverage_reviews.csv'
f=open(p,encoding='utf-8')
r=csv.DictReader(f)
print('FIELDS:', r.fieldnames)
rows=list(r)
print('N_ROWS:', len(rows))
print('--- route counts ---')
[print('%-28s %d' % (k,v)) for k,v in sorted(collections.Counter(x.get('route','<MISSING>') for x in rows).items())]
print('--- verdict counts ---')
[print('%-28s %d' % (k,v)) for k,v in sorted(collections.Counter(x.get('verdict','<MISSING>') for x in rows).items())]
print('--- route x verdict ---')
[print('%-28s %-16s %d' % (a,b,c)) for (a,b),c in sorted(collections.Counter((x.get('route','<MISSING>'),x.get('verdict','<MISSING>')) for x in rows).items())]
```

**ACTUAL OUTPUT (verbatim):**

```
FIELDS: ['review_id', 'batch_id', 'name', 'state', 'historical_limitation', 'historical_n_limited', 'resolution_path', 'route', 'kept_pool_evidence', 'registered_starts', 'computed_new_members', 'n_unique_after', 'verdict', 'review_version', 'evidence_note']
N_ROWS: 14
--- route counts ---
multi_basin_coverage         8
search_exhausted             2
single_basin_verified        2
unresolved_qc                2
--- verdict counts ---
resolved                     10
search_exhausted             2
unresolved                   2
--- route x verdict ---
multi_basin_coverage         resolved         8
search_exhausted             search_exhausted 2
single_basin_verified        resolved         2
unresolved_qc                unresolved      2
```

Exit code: **0**.

---

## 2.3 Measured per-route row counts (question 2)

| route | measured rows | prior independent count | agree? |
|---|---|---|---|
| `multi_basin_coverage` | **8** | 8 | ✅ |
| `single_basin_verified` | **2** | 2 | ✅ |
| `unresolved_qc` | **2** | 2 | ✅ |
| `search_exhausted` | **2** | 2 | ✅ |
| `known_basin_reproduction` | **0** | 0 | ✅ |
| `pending` | **0** | 0 | ✅ |
| `dedup_evidence_required` | **0** | 0 | ✅ |
| **total** | **14** | 14 | ✅ |

**The prior independent count is fully re-verified.** Every number matches,
including the three "zero data" routes.

### Route → verdict consistency in the real data
Every one of the 14 rows is internally consistent with the mapping at
build_coverage_reviews.py:357-375:

| route | verdict emitted | mapping line that produced it |
|---|---|---|
| `multi_basin_coverage` | `resolved` | 358-359 |
| `single_basin_verified` | `resolved` | 358-359 |
| `unresolved_qc` | `unresolved` | 370-371 |
| `search_exhausted` | `search_exhausted` | 367-368 |

No row took the `else:` branch (373-375), and no row has a route string outside
the 7-name vocabulary. **There is no misspelling in the shipped CSV.**

---

## 2.4 Test references per route (question 3)

Commands: `ops_grep` (ripgrep) over `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\tests`,
one pattern per route name. Results are given as *occurrences across N files*,
then resolved to file:line below.

### (a) LITERAL hits — tests that name the route string literally

| route | occurrences | files | file:line for every literal hit |
|---|---|---|---|
| `multi_basin_coverage` | 7 | **3** | `tests/test_resolved_route_evidence.py:5,41,71`; `tests/test_strict_readiness_strict.py:91`; `tests/test_sampling_3to6_diff.py:409` |
| `single_basin_verified` | 6 | **2** | `tests/test_resolved_route_evidence.py:6,11,50,74`; `tests/test_strict_recovery_coverage.py:156` |
| `search_exhausted` | 10 | **3** | `tests/test_resolved_route_evidence.py:73`; `tests/test_strict_recovery_coverage.py:110,127,131,134,136,149,160`; `tests/test_acceptance_decision.py:84` |
| `unresolved_qc` | 4 | **2** | `tests/test_resolved_route_evidence.py:75`; `tests/test_strict_readiness_strict.py:81,169` |
| `known_basin_reproduction` | 2 | **1** | `tests/test_resolved_route_evidence.py:70,100` |
| `dedup_evidence_required` | 2 | **1** | `tests/test_resolved_route_evidence.py:69,101` |
| `pending` (as a **route**) | 3 | **1** | `tests/test_resolved_route_evidence.py:66,72,97` |

Note on `pending`: a plain grep for `pending` in `tests/` returns many more hits,
but **all of them are `status` fields, not routes**. Verified individually — the
non-route hits are:
`tests/test_import_ensemble_structures.py:235,300` (`row["status"] == "pending"`),
`tests/test_stage16_two_guess.py:613` (`validation.get("status") != "pending"`),
`tests/test_probe_route_in_flight.py:84,92,103` (`"status": "pending"`),
`tests/test_frontier_spin_qc.py:87` (`identity_qc_status == "pending"`),
`tests/test_build_production_ensemble_aggregator.py:224` (positional `"pending"`
arg), `tests/test_wp2_queue_smpd_guard.py:64` (`status = "pending"`),
`tests/test_strict_recovery_coverage.py:110` and `tests/test_acceptance_decision.py:84`
(both are **verdict** sets, not route names). A grep for `'pending'`
(single-quoted) returned **no matches**.

### (b) INDIRECT coverage — table-driven / synthetic / verdict-only

- `unresolved_qc`: **2 files name it literally but neither drives the route
  behaviourally.** `tests/test_strict_readiness_strict.py:81` and `:169` build a
  *synthetic row dict* `{"route": "unresolved_qc", ...}` to feed
  `strict_readiness_wiring`'s validator; they test the **consumer**, not
  `coverage_route()`. `tests/test_resolved_route_evidence.py:75` is the frozen
  vocabulary tuple. So the prior count's "0 (indirect via verdict)" is
  **confirmed as "0 behavioural tests"**, but must be corrected to "2 literal
  mentions in 2 files, all indirect".
- `search_exhausted`: `tests/test_strict_recovery_coverage.py:149`
  (`test_search_exhausted_is_never_treated_as_resolved`) is a genuine
  behavioural test, and `:110` is a verdict-set assertion.
- `multi_basin_coverage` / `single_basin_verified`: genuinely behavioural —
  `tests/test_resolved_route_evidence.py:41,50` branch on the route string and
  assert per-route evidence invariants against the real CSV.
- `known_basin_reproduction`, `dedup_evidence_required`, `pending`: **no
  behavioural test exists.** Their only mentions are the frozen vocabulary tuple
  (`tests/test_resolved_route_evidence.py:68-76`), that file's docstring
  (`:97`, `:100-101`), and one comment (`:66`).

### (c) Consequence for the claim's "zero tests" wording

**The claim is now PARTIALLY OUTDATED and must be restated.** As of the current
tree, `tests/test_resolved_route_evidence.py` exists and literally names all 7
routes — it was added *as the G5 fix* (see
`docs/handoffs/four_state_recovery_20261023/ACCEPTANCE_CHAIN_AUDIT_20261024.md:99-103`).
So:

- "zero **rows** in `coverage_reviews.csv`" — **still exactly true** for all
  three (measured 0/0/0 in §2.3).
- "zero **tests**" — **no longer literally true** (each is named in 1 file), but
  **true in the meaningful sense**: there is still **no behavioural test that
  exercises any of those three routes**. The only test that names them is a
  data-free AST vocabulary guard.

The prior count's table (`multi_basin_coverage` 8/3, `single_basin_verified` 2/1,
`unresolved_qc` 2/0, `search_exhausted` 2/2, and 0/0 for the other three) is
**fully reproduced by my measurements**, with the caveat that the "0 test files"
column for the three was measured *before* the guard test was added.

---

## 2.5 Repo-wide duplication census of the route vocabulary (the "also check" item)

Command: `ops_grep` over `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\scripts`
with pattern
`known_basin_reproduction|dedup_evidence_required|unresolved_qc|multi_basin_coverage|single_basin_verified|search_exhausted|COVERAGE_ROUTES`.

**Result: 40 occurrences across 7 files.** The route vocabulary is duplicated in
**three independent, editable copies**, exactly as the audit's own downward
revision warns (`ACCEPTANCE_CHAIN_AUDIT_20261024.md:94-97`):

| # | location | kind | what it holds |
|---|---|---|---|
| ① | `scripts/wp_production/build_coverage_reviews.py` lines **173,182,187,190,195,200,205,210,216,220** | **emit side** | the 7 strings `coverage_route()` returns |
| ② | `scripts/wp_production/build_coverage_reviews.py` lines **345** (hardcoded), **358, 361, 364, 367, 370** (mapping comparisons), **377, 380** (evidence-branch comparisons) | **consumer side, same module** | comparisons against the same strings |
| ③ | `scripts/wp_production/strict_readiness_wiring.py` lines **62-65** (`COVERAGE_ROUTES`), **66-67** (`COVERAGE_VERDICTS`), **68** (`COVERAGE_SETTLED`) | **downstream validator** | an independent frozenset copy of all 7 route names |

Plus **prose copies** (not executable, but they document the vocabulary and can
drift):
- `scripts/build_terminal_site.py:417-418`
- `scripts/build_github_readme.py:816-818`
- `scripts/wp_production/build_bgroup_pilot_preregistration.py:157`
- `scripts/wp_production/build_production_ensemble_aggregator.py:631,633`
- `scripts/wp_production/import_ensemble_structures.py:2399-2403` — **false
  positive**: these are `unresolved_qc_failure` disposition tokens, a different
  vocabulary that merely shares a prefix. Not a route copy.
- `docs/handoffs/four_state_recovery_20261023/ACCEPTANCE_CHAIN_AUDIT_20261024.md:76-116`
  (the audit itself) and `tests/test_resolved_route_evidence.py:68-76` (the
  frozen tuple) — a 4th and 5th copy, the latter being the deliberate guard.

### Verdict on the duplication risk
**Confirmed, and it is the real residual risk.** Copies ① and ② live in the same
file and are now pinned together by
`tests/test_resolved_route_evidence.py::test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete`
(assertion 1 at :112-114 pins ① to the frozen 7-tuple; assertion 2 at :116-121
requires every emitted route to be *named outside* `coverage_route()`, i.e. in
copy ②). Copy ③ is **not** covered by that test, but it is self-defended
downstream: `strict_readiness_wiring.py:167-168` rejects any route token not in
`COVERAGE_ROUTES`. So an inconsistent edit to ③ alone fails loudly at the gate,
and an inconsistent edit to ① or ② alone fails the guard test. The only
surviving hole is a **fully coordinated rename across ① + ② + ③**, which no test
would catch — and the three zero-data routes are precisely the ones where a
rename is most likely to be done incompletely, because no data row and no
behavioural test would notice.
