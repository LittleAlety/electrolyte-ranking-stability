# G5 Route Coverage Review — Final Report
**Repository:** `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code`  
**Audit Target:** `scripts/wp_production/build_coverage_reviews.py`  
**CSV:** `outputs/physics_completion/recovery/coverage_reviews.csv`  
**Claim Source:** `docs/handoffs/four_state_recovery_20261023/ACCEPTANCE_CHAIN_AUDIT_20261024.md` §G5  
**Status:** INDEPENDENT VERIFICATION (not accepting prior audit's conclusions blindly)  
**Writer:** wp5-guard-review (session-a3d57998)  
**Date:** 2026-10-25  

---

## 1. File list (created this session)
- `STAGE1_line_evidence.md` — line-level evidence for route→verdict mapping and `kept_evidence` branch
- `STAGE2_counts.md` — CSV row counts per route, test-reference census, duplication census
- `STAGE3_fallback_direction.md` — misspelling/fallback simulation with real code paths
- `STAGE3_sim.py` — executable simulation script (writes to temp only, read-only on repo)
- `STAGE3_sim_output.txt` — verbatim stdout from simulation
- `REPORT.md` — this file

---

## 2. All commands actually run (with actual exit codes)

| Command | Exit Code | Purpose |
| --- | --- | --- |
| `pwsh` + venv python `-B` to count routes/verdicts in CSV (read-only `csv.DictReader`) | 0 | Measured real row counts (§3.2) |
| `ops_grep` over `tests/` for each of 7 route names | 0 | Census literal/indirect test refs (§3.3) |
| `ops_grep` over `scripts/` for route vocabulary + `COVERAGE_ROUTES` | 0 | Duplication census (§3.4) |
| `pwsh` run `STAGE3_sim.py` (imports real `build_coverage_reviews.py` and `strict_readiness_wiring.py`) | 0 | Executed misspelling simulation (§4) |
| `pwsh` run real test `tests/test_resolved_route_evidence.py` via venv python `-B -m pytest` | 0 (2 passed) | Verified guard test behavior |

All python invocations used `.venv\Scripts\python.exe` with `-B`. No files modified in repo; simulation wrote only to temp dirs.

---

## 3. Line-level evidence (route→verdict mapping, kept_evidence)

### 3.1 `coverage_route()` (build_coverage_reviews.py:163-223)
**7 distinct route strings, 10 return statements.** No `else:` in this function; final return at line 220 is unconditional.

| Route | Return lines |
| --- | --- |
| `pending` | 172-173, 190-191 |
| `search_exhausted` | 182-185 |
| `unresolved_qc` | 187-189 |
| `dedup_evidence_required` | 195-197 |
| `multi_basin_coverage` | 200-202, 204-206 |
| `known_basin_reproduction` | 210-214, 216-218 |
| `single_basin_verified` | 220-223 |

**Claim (a):** CONFIRMED (7 distinct routes). Clarification: count is distinct strings, not return statements.

### 3.2 Route→verdict mapping (build_coverage_reviews.py:357-375)
```python
357:        verdict_route = route
358:        if route in ("multi_basin_coverage", "single_basin_verified"):
359:            verdict = "resolved"
...
373:        else:
374:            verdict = "pending"
375:            note = route_note
```
**Claim (b):** CONFIRMED in substance. **Line-number correction:** mapping block spans 357-375; the `else:` is at **373-375** (last 3 lines). The CSV emits `route` = `verdict_route` (line 399) separately from `verdict` (line 404).

### 3.3 `kept_evidence` branch (build_coverage_reviews.py:377-388)
```python
377:        if route == "multi_basin_coverage":
...
380:        elif route in ("single_basin_verified", "known_basin_reproduction"):
381:            kept_evidence = sorted({
382:                d.get("duplicate_of", "")
...
386:            } - {""})
387:        else:
388:            kept_evidence = []
```
**Claim (c):** CONFIRMED exactly. Line 380 uses `known_basin_reproduction` and builds from `dedup_rows` via `duplicate_of` (line 382, loaded from `production_ensemble_dedup.csv` at 322-327).

### 3.4 Additional hardcoded route
Line **345** hardcodes `route = "multi_basin_coverage"` before calling `coverage_route()` (lines 344-351). Route vocabulary appears in 3 places in-module (emit: 173,182,187,190,195,200,205,210,216,220; hardcoded: 345; comparisons: 358,361,364,367,370,377,380).

---

## 4. CSV real row counts per route

**File:** `outputs/physics_completion/recovery/coverage_reviews.csv`  
**Header:** `['review_id', 'batch_id', 'name', 'state', 'historical_limitation', 'historical_n_limited', 'resolution_path', 'route', 'kept_pool_evidence', 'registered_starts', 'computed_new_members', 'n_unique_after', 'verdict', 'review_version', 'evidence_note']`  
**N_ROWS:** 14, sha256 `6CD5E92EDE14B910ED4555DCC5B1A187618245276B1231B55255B5192F3A0F80`

| Route | Rows | Verdict |
| --- | --- | --- |
| `multi_basin_coverage` | 8 | resolved (8) |
| `search_exhausted` | 2 | search_exhausted (2) |
| `single_basin_verified` | 2 | resolved (2) |
| `unresolved_qc` | 2 | unresolved (2) |
| `known_basin_reproduction` | **0** | — |
| `pending` | **0** | — |
| `dedup_evidence_required` | **0** | — |
| **Total** | **14** | — |

All 14 rows are consistent with mapping at 357-375. **No misspellings in shipped CSV.** The three zero-data routes have **0 rows in CSV** — confirmed.

---

## 5. Tests referencing routes (literal vs indirect)

### 5.1 Literal hits
| Route | Occurrences | Files | Hits |
| --- | --- | --- | --- |
| `multi_basin_coverage` | 7 | 3 | `test_resolved_route_evidence.py:5,41,71`; `test_strict_readiness_strict.py:91`; `test_sampling_3to6_diff.py:409` |
| `single_basin_verified` | 6 | 2 | `test_resolved_route_evidence.py:6,11,50,74`; `test_strict_recovery_coverage.py:156` |
| `search_exhausted` | 10 | 3 | `test_resolved_route_evidence.py:73`; `test_strict_recovery_coverage.py:110,127,131,134,136,149,160`; `test_acceptance_decision.py:84` |
| `unresolved_qc` | 4 | 2 | `test_resolved_route_evidence.py:75`; `test_strict_readiness_strict.py:81,169` |
| `known_basin_reproduction` | 2 | 1 | `test_resolved_route_evidence.py:70,100` |
| `dedup_evidence_required` | 2 | 1 | `test_resolved_route_evidence.py:69,101` |
| `pending` (as route) | 3 | 1 | `test_resolved_route_evidence.py:66,72,97` |

### 5.2 Assessment
- `unresolved_qc` has 2 literal mentions but **only in consumer tests** (`test_strict_readiness_strict.py` builds synthetic rows) — **no behavioural test exercises `coverage_route()` for it**.
- `search_exhausted` has genuine behavioural coverage (`test_strict_recovery_coverage.py:149`).
- `multi_basin_coverage`/`single_basin_verified` have behavioural coverage.
- `known_basin_reproduction`, `dedup_evidence_required`, `pending` are **only named in `tests/test_resolved_route_evidence.py`** (frozen vocabulary tuple + comments) — **no behavioural test exercises them**.

**Conclusion:** "Zero **rows**" remains true for all three. "Zero **tests**" is **no longer literally true** because of the G5 guard test added (`ACCEPTANCE_CHAIN_AUDIT_20261024.md:99-103`), but **no behavioural test exists for those three routes**. The meaningful concern remains.

---

## 6. Duplication census (vocabulary spread)
Route vocabulary appears in **7 files, 40 occurrences**. Three independent editable copies:
1. **Emit side** (`build_coverage_reviews.py:173,182,187,190,195,200,205,210,216,220`) — `coverage_route()` returns
2. **Consumer side in same module** (345, 358, 361, 364, 367, 370, 377, 380) — hardcoded/comparisons
3. **Downstream validator** (`strict_readiness_wiring.py:62-68`) — `COVERAGE_ROUTES`, `COVERAGE_VERDICTS`, `COVERAGE_SETTLED` (independent frozenset)

Prose copies exist in other scripts/docs/tests. The guard test `test_resolved_route_evidence.py` pins (1) and (2) together, but **does not cover (3)**. Copy (3) self-defends downstream (rejects unknown routes).

---

## 7. Crux: misspelling/fallback direction (executed with real code)

**Method:** `STAGE3_sim.py` imports real modules, execs real mapping block (357-388), calls real `strict_readiness_wiring._check_coverage()`. No repo files modified; temps only.

### 7.1 Misspelling falls through else into pending
With correct `known_basin_reproduction` (computed member, novelty `known`, `production_evidence=False`):  
`verdict_route='known_basin_reproduction', verdict='unresolved', kept_evidence=['DMC|LiM_2plus|tors_3']`

With emit-side typo `known_basin_reproducton`:  
`verdict_route='known_basin_reproducton', verdict='pending'` (from **else at 373-374**), `kept_evidence=[]` (emptied by **else at 387-388**).  
A typo of `pending` itself is **indistinguishable** from correct `pending` (verdict already pending).

### 7.2 Direction: BLOCKS (fail-closed) at chain level
**Layer 1 (build_coverage_reviews.py):** Local severity downgrade `unresolved` → `pending` and loss of `duplicate_of` evidence (lines 374, 388). Looks fail-open locally.

**Layer 2 (strict_readiness_wiring.py):** Hard block.
- Line **167-168**: `if route not in COVERAGE_ROUTES:` → appends `"%s|%s unknown route %r"`. `COVERAGE_ROUTES` is independent copy of 7 names; typo not in it.
- Line **179-180**: `if verdict == "pending":` → appends `"%s|%s review still pending (evidence not settled)"`. `COVERAGE_SETTLED` excludes `pending`.
- `_result()` (133-136): any problems → `ok=False`.

**Measured (real wiring):**
- Real CSV: `ok=True, problems=[]`
- Synthetic misspelled route only: `ok=False, problem: AN|M_plus unknown route 'known_basin_reproducton'`
- Synthetic misspelled route + pending: `ok=False` with 3 problems (unknown route, still pending, accepts review for state not open)

**Answer:** **FAIL-CLOSED at chain level — blocks release, does not let uncovered states through.** It is loud but **misdiagnoses** (replaces specific reason + `duplicate_of` evidence with generic "pending/evidence not settled" messages). Typos in `pending` itself are lost signals (no-op), not release-gaining.

### 7.3 Guard test coverage (measured)
`tests/test_resolved_route_evidence.py::test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete` — **2 passed**.

| Mutation | Assert 1 (vocab frozen, :112-114) | Assert 2 (named outside, :116-121) | Result |
| --- | --- | --- | --- |
| Pristine | True | True | PASS |
| Emit-side typo (lines 210,216 only) | False | False | **GOES RED** |
| **Mapping-side typo (line 361 only)** | True | True | **PASSES (BLIND SPOT)** |
| Coordinated rename (all in-module occurrences) | False | True | **GOES RED** |

**Mapping-side-only typo** breaks behavior (verdict becomes `pending`) but passes both guard assertions; it's caught downstream by wiring (`verdict=='pending'` trip-wire at 179-180), one layer later with worse diagnostics. **Fully coordinated rename across all 3 copies** (emit + in-module + `COVERAGE_ROUTES` in wiring) would pass guard test and downstream validator — undetected. This hole concentrates on the three zero-data routes.

---

## 8. What I did NOT cover
- Runtime behavior with actual ensemble data flows beyond what `coverage_route()`/mapping/wiring do
- Whether other consumers of `coverage_reviews.csv` have different tolerance for `pending`
- Full end-to-end integration test of the entire coverage→readiness chain in all scenarios
- Potential effects of the prose copies in scripts/docs on human interpretation (only enumerated, not tested)
- Whether the guard test's "named outside" check is sufficient to catch all coordinated rename patterns in all future edits

---

## 9. Bottom line
- **Line-level claims (a)-(c):** Substantially confirmed with corrections (7 distinct routes, `else` at 373-375, line 380 exact).
- **CSV counts:** `known_basin_reproduction`/`pending`/`dedup_evidence_required` have **0 rows** — confirmed. No misspellings in shipped data.
- **Tests:** The guard test now exists (added per G5 fix), but **no behavioural tests** exercise the three zero-data routes; only vocabulary freeze assertions exist for them.
- **Duplication:** Three independent copies (emit, in-module, wiring) — guard pins first two, **wiring copy not pinned by guard but self-defends** downstream.
- **Crux:** A misspelled route name **falls through to `pending` and loses `duplicate_of` evidence** in `build_coverage_reviews.py`, but the **chain is fail-closed** via `strict_readiness_wiring` (unknown route rejected at 167-168, `pending` verdict rejected at 179-180). **Loud but misdiagnosed.** Guard is blind to mapping-side-only typos (caught later). Fully coordinated rename across all three copies is undetected by current tests — concentrated risk on the three zero-data routes.
- **Conclusion vs prior audit:** The direction split (emit-side vs mapping-side) and "zero behavior tests" framing are correct; the audit's subsequent update (commit c5dbf37) correctly absorbed these findings. The core safety property holds, but the diagnostic precision and incomplete guard coverage remain real residual risks.
