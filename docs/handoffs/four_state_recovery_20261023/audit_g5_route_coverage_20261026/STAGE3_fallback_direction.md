# STAGE 3 — Misspelling / fallback DIRECTION (the crux, question 4)

**Method.** Every number and every quoted line below comes from
`stage3_sim.py` (in this directory), whose verbatim stdout is saved as
`STAGE3_sim_output.txt`. The sim:

1. imports the **real** `scripts/wp_production/build_coverage_reviews.py` and
   calls the **real** `coverage_route()`;
2. extracts lines **357-388** of the real file verbatim, `textwrap.dedent`s them,
   and `exec`s that block — so the mapping under test is the shipped code, not a
   paraphrase;
3. imports the **real** `scripts/wp_production/strict_readiness_wiring.py` and
   calls the **real** `_check_coverage()`;
4. replicates the **real** guard test's AST assertions against in-memory mutated
   source.

**No repo file was modified.** The synthetic CSVs were written to the system
temp directory (`%TEMP%\g5_synthetic_*`), because the DSH sandbox denies writes
to the workspace from a spawned python process and because the repo had to stay
read-only regardless. `outputs/physics_completion/recovery/coverage_reviews.csv`
was never opened for writing; its mtime (2026/10/25 12:31:31) and sha256
(`6CD5E92E…F3A0F80`) are unchanged.

---

## 3.1 Does a misspelled route fall through the `else` into `pending`? — **YES, confirmed by execution**

Real code, real inputs engineered to land on the `known_basin_reproduction`
branch (one `computed` member, novelty `known`, `min_unique_after=1`,
`production_evidence=False`):

```
PART 1
coverage_route(...) -> 'known_basin_reproduction'
note: computed start(s) deduplicated onto known minima; **not a QC failure** --
these are independent reproductions. Coverage is not yet certifiable: the
production-side evidence set is incomplete
```

Then the extracted mapping block, run with the route string varied:

```
A) BASELINE  route = 'known_basin_reproduction'  (spelled correctly)
   verdict_route = 'known_basin_reproduction'
   verdict       = 'unresolved'
   kept_evidence = ['DMC|LiM_2plus|tors_3']

B) MISSPELLED  route = 'known_basin_reproducton'  (emit-side typo only)
   verdict_route = 'known_basin_reproducton'
   verdict       = 'pending'   <-- came from the else: at line 373-375
   kept_evidence = []          <-- emptied by the else: at line 387-388

C) MISSPELLED  route = 'dedup_evidence_requird'  (emit-side typo only)
   verdict       = 'pending'
   kept_evidence = []

D) MISSPELLED  route = 'pendingg'  (emit-side typo only)
   verdict       = 'pending'   <-- INDISTINGUISHABLE from a correct 'pending'
```

**Mechanism, with line numbers** (build_coverage_reviews.py):

| line | code | effect on a misspelled route |
|---|---|---|
| 361 | `elif route == "known_basin_reproduction":` | comparison fails (typo) |
| 364 | `elif route == "pending":` | comparison fails |
| 367 | `elif route == "search_exhausted":` | comparison fails |
| 370 | `elif route in ("unresolved_qc", "dedup_evidence_required"):` | comparison fails |
| **373** | `else:` | **taken** |
| **374** | `verdict = "pending"` | **verdict downgraded `unresolved` → `pending`** |
| 377 | `if route == "multi_basin_coverage":` | fails |
| **380** | `elif route in ("single_basin_verified", "known_basin_reproduction"):` | fails |
| **387** | `else:` | **taken** |
| **388** | `kept_evidence = []` | **coverage evidence silently discarded** |

So the typo does **two** things at once: it downgrades the verdict (374) **and**
it throws away the `duplicate_of` evidence (388). Case D shows a further
degeneracy: a typo in `pending` itself is **behaviourally invisible**, because
the correct route and the typo both land on `verdict = "pending"`.

---

## 3.2 Which direction is the failure? — **The answer is two-layered, and the layer matters**

### Layer 1 — INSIDE `build_coverage_reviews.py`: a **severity DOWNGRADE** (locally fail-open-looking)

`known_basin_reproduction` and `dedup_evidence_required` are both **blocking**
routes: the mapping sends them to `verdict = "unresolved"` (lines 362, 371).
`unresolved` is a *settled, negative* verdict — it says "this state is not
covered, and we know why". A typo converts that into `verdict = "pending"`
(line 374), which is *unsettled* and, per
`strict_readiness_wiring.py:68` `COVERAGE_SETTLED = frozenset(("resolved",
"unresolved", "search_exhausted"))`, is **not** a settled verdict at all.

Direction of the local change: `unresolved` (a definite NO) → `pending`
(nothing decided). That is a move **away from** a blocking answer. On its own,
inside this one function, it looks like **fail-open** — the review stops
asserting the limitation it should assert.

### Layer 2 — DOWNSTREAM in `strict_readiness_wiring.py`: **FAIL-CLOSED, hard block**

The chain does not stop at the CSV. `_check_coverage()` re-validates every row
and `_result()` (lines 133-136) returns `ok = bool(ok) and not problems`, so
**any** problem turns the whole check red.

Real, executed evidence:

```
-- _check_coverage on the REAL coverage_reviews.csv --
   ok = True ; problems = [] ; review_rows = 14

-- _check_coverage on synthetic_misspelled_route_only.csv --
   ok = False
   problem: AN|M_plus unknown route 'known_basin_reproducton'

-- _check_coverage on synthetic_misspelled_route_plus_pending.csv --
   ok = False
   problem: AN|M_plus unknown route 'known_basin_reproducton'
   problem: AN|M_plus review still pending (evidence not settled)
   problem: AN|M_plus accepts a review for a state that is not open
```

Two independent trip-wires, both confirmed by execution:

| line | code | catches |
|---|---|---|
| **167-168** | `if route not in COVERAGE_ROUTES:` → `problems.append("%s|%s unknown route %r" % …)` | the misspelled **route** token, because `COVERAGE_ROUTES` (62-65) is an independent copy of the 7-name vocabulary and `'known_basin_reproducton' in COVERAGE_ROUTES` → `False` |
| **179-180** | `if verdict == "pending":` → `problems.append("%s|%s review still pending (evidence not settled)" % key)` | the **verdict downgrade**, even if the route token were somehow accepted |

Plus a third, softer trip-wire: `COVERAGE_SETTLED` (line 68) excludes
`"pending"`, so a pending review is not "settled" for any consumer that asks
that question.

### Bottom line on direction

**FAIL-CLOSED at the chain level. The misspelling BLOCKS a release; it does not
let anything through.**

Precisely:
- It is **not** a silent pass. Both the unknown route (167-168) and the
  `pending` verdict (179-180) raise a problem, and `_result` (133-136) makes the
  gate red.
- It is also **not** a fail-open in the sense of "accepts an uncovered state".
  An `unresolved` review never becomes `resolved`; it becomes `pending`, which
  the gate rejects.
- What it *does* lose is **diagnostic precision**: the operator sees "review
  still pending (evidence not settled)" / "unknown route" instead of the true
  "computed start(s) deduplicated onto known minima; coverage is not yet
  certifiable" note (line 213-214), and the `duplicate_of` evidence is gone
  (line 388). So the failure is **loud but misleading** — a fail-closed
  *misdiagnosis*, not a fail-closed *correct diagnosis*.
- The one genuinely fail-open-looking residue is case D: a typo in the literal
  `"pending"` (line 173 or 190) produces `verdict = "pending"`, which is
  indistinguishable from a correct `pending`. But that is a *no-op* change — the
  verdict is already `pending` — so nothing is let through that shouldn't be.
  It is a **lost signal**, not a gained release.

---

## 3.3 What the guard test does and does not cover (RED evidence)

The G5 fix added
`tests/test_resolved_route_evidence.py::test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete`.
Running the real test: **exit code 0, 2 passed** (`..` `[100%]`).

Replicating its two assertions against in-memory mutations:

| mutation | assert 1 (vocab frozen, :112-114) | assert 2 (named outside, :116-121) | test |
|---|---|---|---|
| pristine | True | True | **PASSES** |
| **1. emit-side typo, lines 210 & 216 only** | **False** | **False** | **GOES RED** |
| **2. mapping-side typo, line 361 only** | True | **True** | **PASSES** ← blind spot |
| **3. coordinated rename, all occurrences in-module** | **False** | True | **GOES RED** |

### The blind spot (mutation 2) — measured, not speculated

A typo **only** in the mapping comparison at line 361 leaves the emitted
vocabulary intact and leaves `known_basin_reproduction` still named at lines
210, 216 and 380 (outside the function), so **both assertions pass**. Behaviour,
however, is broken:

```
correct route 'known_basin_reproduction' through the MUTATED mapping:
   verdict       = 'pending'   <-- WRONG, should be 'unresolved'
   kept_evidence = ['DMC|LiM_2plus|tors_3']

-- _check_coverage on synthetic_mapping_side_typo.csv --
   ok = False
   problem: AN|M_plus review still pending (evidence not settled)
   problem: AN|M_plus accepts a review for a state that is not open
```

So the guard test is **blind** to a mapping-side-only typo, but the downstream
gate is **not** — `verdict == "pending"` trips line 179-180. Net effect remains
fail-closed, caught one layer later and with a worse message.

### Residual hole

A **fully coordinated rename across all three vocabulary copies** —
① emit strings (build_coverage_reviews.py:173,182,187,190,195,200,205,210,216,220),
② in-module comparisons (345, 358, 361, 364, 367, 370, 377, 380), **and**
③ `COVERAGE_ROUTES` (strict_readiness_wiring.py:62-65) — would pass the guard
test *and* the downstream validator, because both sides of every comparison move
together. Nothing in the current tree detects that. It is only a defect if the
rename is incomplete, and the three zero-data routes (`known_basin_reproduction`,
`pending`, `dedup_evidence_required`) are exactly where an incomplete rename is
most likely, since no data row and no behavioural test exercises them.

---

## 3.4 Stage 3 summary

| question | answer |
|---|---|
| Does a misspelled route fall through the `else` into `pending`? | **YES** — executed: `known_basin_reproducton` → `verdict="pending"` via lines 373-374, and `kept_evidence=[]` via 387-388. |
| Does it BLOCK a release or let something through? | **BLOCKS (fail-closed)** at the chain level: `strict_readiness_wiring.py:167-168` rejects the unknown route token and `:179-180` rejects the `pending` verdict; `_result` (:133-136) turns the gate red. Measured `ok = False` on both synthetic variants. |
| Is it silent? | **No** — it is loud, but it **misdiagnoses**: the true reason (`unresolved`, with the `duplicate_of` evidence) is replaced by "review still pending (evidence not settled)" with the evidence discarded. |
| Guard test adequate? | **Partially.** Catches emit-side typos (mutation 1) and in-module coordinated renames (mutation 3). **Blind** to a mapping-side-only typo (mutation 2) — that one is caught only downstream, one layer later. |
| Fully coordinated rename across all 3 copies? | **Undetected by anything in the tree.** This is the residual risk, and it concentrates on the three zero-data routes. |
