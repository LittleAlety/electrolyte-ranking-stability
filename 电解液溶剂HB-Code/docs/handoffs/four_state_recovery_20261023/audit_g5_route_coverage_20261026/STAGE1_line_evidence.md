# STAGE 1 — Line-level evidence for claim G5

**Audit target:** `scripts/wp_production/build_coverage_reviews.py` (repo root
`E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code`, 21525 bytes, 473 lines, mtime 2026/10/23 18:35:15)

**Claim under review (from `docs/handoffs/four_state_recovery_20261023/ACCEPTANCE_CHAIN_AUDIT_20261024.md` §G5):**
> (a) `coverage_route()` has 7 routes, of which 3 are "zero data + zero tests":
> `known_basin_reproduction`, `pending`, `dedup_evidence_required`.
> (b) the route→verdict mapping carries an `else: verdict="pending"` fallback
> (claimed at lines 357-375)
> (c) line 380 uses the same string to decide whether `kept_evidence` is taken
> from `duplicate_of`.

Status: **single-sided, not independently verified.** This stage is the first
independent verification of the line-level parts.

---

## 1.1 `coverage_route()` — definition span and every return

`coverage_route()` is defined at **line 163** and its body ends at **line 223**
(the `return ("single_basin_verified", ...)` at 220-223 is the last statement of
the function; line 224 is blank, 225-226 blank, 227 starts `def build_rows`).

There are **10 `return` statements** inside `coverage_route`, yielding **7
distinct route name strings**. Verified with `ops_grep` line-numbered content
mode over the file (35 matching lines, all shown):

| # | line(s) | route string returned | verdict-relevant note |
|---|---------|----------------------|-----------------------|
| 1 | 172-173 | `"pending"` | guard: any member `status` in `("pending","ready")` |
| 2 | 182-185 | `("search_exhausted", ...)` | `not latest_members and search_outcome == "no_new_minimum_found"` |
| 3 | 187-189 | `("unresolved_qc", ...)` | `latest_members` non-empty but none `computed` |
| 4 | 190-191 | `"pending"` | `latest_members` empty and search_outcome != no_new_minimum_found |
| 5 | 195-197 | `("dedup_evidence_required", ...)` | `"unresolved" in kinds` |
| 6 | 200-202 | `("multi_basin_coverage", ...)` | `min_unique_after >= 2 and "new" in kinds` |
| 7 | 204-206 | `("multi_basin_coverage", ...)` | `"new" in kinds` |
| 8 | 210-214 | `("known_basin_reproduction", ...)` | `not production_evidence` |
| 9 | 216-218 | `("known_basin_reproduction", ...)` | `not _search_scope_documented(...)` |
| 10 | 220-223 | `("single_basin_verified", ...)` | unconditional final return |

### Verdict on claim (a) — route COUNT
**CONFIRMED, with one clarification that matters.** The distinct route
vocabulary returned by `coverage_route()` is exactly 7:

```
pending, search_exhausted, unresolved_qc, dedup_evidence_required,
multi_basin_coverage, known_basin_reproduction, single_basin_verified
```

Clarification: the "7 routes" is a count of *distinct strings*, not of *return
statements*. There are 10 return statements (`multi_basin_coverage` returns at
both 200 and 205; `known_basin_reproduction` at both 210 and 216; `pending` at
both 173 and 190). A count of "7 return statements" would be **wrong**; the
claim as worded ("has 7 routes") is consistent with distinct strings and is
therefore accepted.

### Important structural fact — `coverage_route()` has NO `else` fallback
`coverage_route()` is a pure chain of early returns and a final unconditional
`return` at line 220. **There is no `else:` branch anywhere in lines 163-223**,
and no `return` after line 223. Every path that reaches the end of the function
is forced to `single_basin_verified`. Consequence: `coverage_route()` can never
return an unknown/other string — it is exhaustive by construction. This is
decisive for Stage 3 (the misspelling question), because a misspelled route
name would have to be *typed at a call site*, not produced by this dispatcher.

---

## 1.2 The route→verdict mapping (claim (b), "claimed at lines 357-375")

Located in `build_rows()`, immediately after `coverage_route()` is called
(lines 351-356). Quoted verbatim from the file:

```
357:        verdict_route = route
358:        if route in ("multi_basin_coverage", "single_basin_verified"):
359:            verdict = "resolved"
360:            note = route_note
361:        elif route == "known_basin_reproduction":
362:            verdict = "unresolved"
363:            note = route_note
364:        elif route == "pending":
365:            verdict = "pending"
366:            note = route_note
367:        elif route == "search_exhausted":
368:            verdict = "search_exhausted"
369:            note = route_note
370:        elif route in ("unresolved_qc", "dedup_evidence_required"):
371:            verdict = "unresolved"
372:            note = route_note
373:        else:
374:            verdict = "pending"
375:            note = route_note
```

### Verdict on claim (b) — line numbers
**CONFIRMED in substance, with an explicit line-number correction.**
- The route→verdict mapping **does** span lines **357-375**. ✓
- The `else:` fallback itself is at **lines 373-375** (`else:` on 373,
  `verdict = "pending"` on 374, `note = route_note` on 375). The claim's
  phrasing "claimed at lines 357-375" is correct **only if read as the whole
  mapping block**. Read as "the `else` lives at 357-375" it is imprecise — the
  `else` is the last 3 lines of that block. I state this explicitly rather than
  silently re-mapping, as instructed.

Two further facts about this block, both material to Stage 3:
1. Line 357 `verdict_route = route` — the emitted CSV `route` column (line 399)
   is `verdict_route`, i.e. **the route string itself**, not the verdict. The
   `verdict` column (line 404) is separate. So a route/verdict mismatch is
   visible in the CSV by comparing the two columns.
2. The `else` at 373 is **reachable only by a route string that is none of the
   7 above** — which, per §1.1, `coverage_route()` cannot produce. It *is*
   reachable from the hardcoded assignment at line 345 (see §1.4).

---

## 1.3 The `kept_evidence` branch (claim (c), "line 380")

Quoted verbatim:

```
377:        if route == "multi_basin_coverage":
378:            kept_evidence = ([k for k, v in novelty.items() if v == "new"]
379:                             or [r["member_key"] for r in qualified_all])
380:        elif route in ("single_basin_verified", "known_basin_reproduction"):
381:            kept_evidence = sorted({
382:                d.get("duplicate_of", "")
383:                for r in computed
384:                for d in [dedup_rows.get(r["member_key"])]
385:                if d and d.get("duplicate_of")
386:            } - {""})
387:        else:
388:            kept_evidence = []
```

### Verdict on claim (c)
**CONFIRMED exactly as stated.** Line 380 is
`elif route in ("single_basin_verified", "known_basin_reproduction"):`, i.e. it
literally contains the string `"known_basin_reproduction"` — the same string
literal used at line 361 in the route→verdict mapping. When that branch is
taken, `kept_evidence` is built from `d.get("duplicate_of", "")` (line 382),
sourced from `dedup_rows` (line 384) which is loaded from
`outputs/physics_completion/ensembles/production_ensemble_dedup.csv`
(lines 322-327). No re-mapping needed; the claimed line is exact.

---

## 1.4 Additional finding not in the claim: a SECOND site that hardcodes route names

This is directly relevant to the "duplicated vocabulary" question and is
recorded here because it is line-level evidence.

Line **345**, inside `build_rows()`, hardcodes a route name *before*
`coverage_route()` is ever consulted:

```
344:        if len(qualified_all) >= 2 and not pending:
345:            route = "multi_basin_coverage"
346:            route_note = ("%d weighted independent minima from the full qualified "
...
350:        else:
351:            route, route_note = coverage_route(
```

So `"multi_basin_coverage"` is written in **three** places in this one file
(345, 200, 205) plus twice more as a comparison (358, 377) = **5 occurrences**.
The literal `"known_basin_reproduction"` appears at 210, 216, 361, 380 = **4
occurrences**. See STAGE2/REPORT for the full repo-wide duplication census.

---

## 1.5 Stage 1 summary

| Claim part | Verdict | Evidence |
|---|---|---|
| (a) `coverage_route()` has 7 routes | **CONFIRMED** (7 *distinct strings*; 10 return statements) | lines 173,182,187,190,195,200,205,210,216,220 |
| (a) 3 are `known_basin_reproduction`, `pending`, `dedup_evidence_required` | **CONFIRMED** as route names that exist | lines 210/216, 173/190, 195 |
| (b) `else: verdict="pending"` fallback exists | **CONFIRMED** | lines 373-375 |
| (b) fallback "at lines 357-375" | **CONFIRMED for the mapping block; the `else` itself is 373-375** | lines 357, 373-375 |
| (c) line 380 uses the same string for `kept_evidence` from `duplicate_of` | **CONFIRMED exactly** | line 380 (`elif`), 382 (`duplicate_of`) |
| `coverage_route()` has an `else` fallback of its own | **DENIED** — no `else` in 163-223; final return at 220 is unconditional | lines 163-223 |

The "zero data + zero tests" part of the claim is **not** answered by this
stage; it is answered by STAGE2 (CSV row counts) and the tests grep.
