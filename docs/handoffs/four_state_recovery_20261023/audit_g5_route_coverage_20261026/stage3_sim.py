"""STAGE 3 harness: run the REAL mapping block from build_coverage_reviews.py
under a misspelled route, and run the REAL downstream validator.

READ-ONLY on every existing repo file. The only files written are the two
synthetic CSVs in the system TEMP directory (NOT in the repo): the DSH sandbox
denies writes to the workspace from a spawned python process, and the repo must
stay untouched anyway.
"""
import csv
import importlib.util
import tempfile
import textwrap
import types
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
SCRIPT = REPO / "scripts" / "wp_production" / "build_coverage_reviews.py"
WIRING = REPO / "scripts" / "wp_production" / "strict_readiness_wiring.py"
OUTDIR = Path(tempfile.mkdtemp(prefix="g5_synthetic_"))
SRC = SCRIPT.read_text(encoding="utf-8")


def load(path, name):
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


real = load(SCRIPT, "real_bcr")
wiring = load(WIRING, "real_srw")

print("=" * 78)
print("PART 1 -- coverage_route() itself, real code, real inputs")
print("=" * 78)
# inputs engineered to land on the known_basin_reproduction branch (line 210)
members = [{"member_key": "DMC|LiM_2plus|tors_7", "status": "computed"}]
route, note = real.coverage_route(
    members, {"DMC|LiM_2plus|tors_7": "known"},
    min_unique_after=1, registered_starts=["tors_7"],
    search_outcome="no_new_minimum_found", production_evidence=False)
print("coverage_route(...) -> %r" % route)
print("note: %s" % note)
assert route == "known_basin_reproduction", route

print()
print("=" * 78)
print("PART 2 -- the REAL route->verdict mapping block, executed verbatim")
print("=" * 78)
# lines 357-388 (1-based, inclusive) = indices 356:388
BLOCK_LINES = (357, 388)
block_src = "\n".join(SRC.splitlines()[BLOCK_LINES[0] - 1:BLOCK_LINES[1]])
block_src = textwrap.dedent(block_src)
print("--- extracted verbatim from %s lines %d-%d ---"
      % (SCRIPT.name, BLOCK_LINES[0], BLOCK_LINES[1]))
print(block_src)
print("--- end extract ---")


def run_mapping(route_value, novelty, computed, dedup_rows,
                qualified_all=(), route_note="<note>"):
    """Execute the real mapping+evidence block with `route` bound to route_value."""
    ns = {"route": route_value, "route_note": route_note, "novelty": novelty,
          "qualified_all": list(qualified_all), "computed": computed,
          "dedup_rows": dedup_rows}
    exec(compile(block_src, "<real-mapping-block>", "exec"), ns)
    return (ns["verdict_route"], ns["verdict"], ns["kept_evidence"])


NOV = {"DMC|LiM_2plus|tors_7": "known"}
COMPUTED = [{"member_key": "DMC|LiM_2plus|tors_7", "status": "computed"}]
DEDUP = {"DMC|LiM_2plus|tors_7": {"member_key": "DMC|LiM_2plus|tors_7",
                                  "duplicate_of": "DMC|LiM_2plus|tors_3"}}

print()
print("A) BASELINE  route = 'known_basin_reproduction'  (spelled correctly)")
vr, v, kept = run_mapping("known_basin_reproduction", NOV, COMPUTED, DEDUP)
print("   verdict_route = %r" % vr)
print("   verdict       = %r" % v)
print("   kept_evidence = %r" % kept)

print()
print("B) MISSPELLED  route = 'known_basin_reproducton'  (emit-side typo only)")
vr, v, kept = run_mapping("known_basin_reproducton", NOV, COMPUTED, DEDUP)
print("   verdict_route = %r" % vr)
print("   verdict       = %r   <-- came from the else: at line 373-375" % v)
print("   kept_evidence = %r   <-- emptied by the else: at line 387-388" % kept)

print()
print("C) MISSPELLED  route = 'dedup_evidence_requird'  (emit-side typo only)")
vr, v, kept = run_mapping("dedup_evidence_requird", {}, COMPUTED, DEDUP)
print("   verdict       = %r" % v)
print("   kept_evidence = %r" % kept)

print()
print("D) MISSPELLED  route = 'pendingg'  (emit-side typo only)")
vr, v, kept = run_mapping("pendingg", {}, [], {})
print("   verdict       = %r   <-- INDISTINGUISHABLE from a correct 'pending'" % v)

print()
print("=" * 78)
print("PART 3 -- downstream: strict_readiness_wiring._check_coverage")
print("=" * 78)
print("COVERAGE_ROUTES (wiring.py:62-65) = %s"
      % sorted(wiring.COVERAGE_ROUTES))
print("COVERAGE_VERDICTS (wiring.py:66-67) = %s"
      % sorted(wiring.COVERAGE_VERDICTS))
print("COVERAGE_SETTLED  (wiring.py:68)    = %s"
      % sorted(wiring.COVERAGE_SETTLED))
print()
for tok in ("known_basin_reproduction", "known_basin_reproducton"):
    print("  %-28r in COVERAGE_ROUTES -> %s" % (tok, tok in wiring.COVERAGE_ROUTES))
print("  %-28r in COVERAGE_SETTLED  -> %s"
      % ("pending", "pending" in wiring.COVERAGE_SETTLED))

# --- run the REAL validator on the real CSV, then on misspelled variants ---
COV = REPO / "outputs" / "physics_completion" / "recovery" / "coverage_reviews.csv"
real_rows = list(csv.DictReader(COV.open(encoding="utf-8")))
FIELDS = list(real_rows[0].keys())


def write_variant(tag, mutate):
    rows = [dict(r) for r in real_rows]
    mutate(rows)
    p = OUTDIR / ("synthetic_%s.csv" % tag)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return p


def m_route(rows):
    rows[0]["route"] = "known_basin_reproducton"   # emit-side typo, verdict kept


def m_both(rows):
    rows[0]["route"] = "known_basin_reproducton"
    rows[0]["verdict"] = "pending"                 # + the else: downgrade


print()
print("-- _check_coverage on the REAL coverage_reviews.csv --")
ok, detail = wiring._check_coverage(COV)
print("   ok = %s ; problems = %r ; review_rows = %s"
      % (ok, detail["problems"], detail.get("review_rows")))

for tag, fn in (("misspelled_route_only", m_route), ("misspelled_route_plus_pending", m_both)):
    p = write_variant(tag, fn)
    ok, detail = wiring._check_coverage(p)
    print()
    print("-- _check_coverage on %s --" % p.name)
    print("   ok = %s" % ok)
    for prob in detail["problems"]:
        print("   problem: %s" % prob)

print()
print("synthetic CSVs written to (temp, NOT the repo): %s" % OUTDIR)
print("=" * 78)
print()
print("=" * 78)
print("PART 5 -- would the guard test CATCH the typo? (RED evidence, in-memory)")
print("=" * 78)
print("Replicating the exact assertions of")
print("tests/test_resolved_route_evidence.py::test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete")
print("against an in-memory mutated source. The repo file is NOT touched.")
print()

FROZEN = ("dedup_evidence_required", "known_basin_reproduction",
          "multi_basin_coverage", "pending", "search_exhausted",
          "single_basin_verified", "unresolved_qc")


def guard(source):
    """Return (emitted_set, span, unnamed_list) exactly as the test computes them."""
    import ast
    emitted, span = set(), None
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "coverage_route":
            span = (node.lineno, node.end_lineno)
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Return) and isinstance(sub.value, ast.Tuple)
                        and sub.value.elts):
                    first = sub.value.elts[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        emitted.add(first.value)
    lines = source.splitlines(keepends=True)
    outside = "".join(lines[:span[0] - 1] + lines[span[1]:])
    unnamed = [r for r in sorted(emitted) if '"%s"' % r not in outside]
    return emitted, span, unnamed


def report(tag, source):
    emitted, span, unnamed = guard(source)
    a1 = emitted == set(FROZEN)
    a2 = not unnamed
    print("%-42s span=%s  assert1(vocab frozen)=%-5s  assert2(named outside)=%-5s"
          % (tag, span, a1, a2))
    if not a1:
        print("      -> FAILS 'route vocabulary drifted': emitted=%s" % sorted(emitted))
    if not a2:
        print("      -> FAILS 'never named elsewhere': %s" % unnamed)
    print("      -> test %s" % ("PASSES" if (a1 and a2) else "GOES RED"))
    return a1 and a2


print("pristine source:")
report("no mutation", SRC)
print()

# mutation 1: emit-side typo only (lines 210 and 216, 1-based)
lines = SRC.splitlines(keepends=True)
m1 = list(lines)
for ln in (210, 216):
    m1[ln - 1] = m1[ln - 1].replace('"known_basin_reproduction"',
                                    '"known_basin_reproducton"')
print("mutation 1 -- emit-side typo at lines 210 and 216 only:")
report("emit-side typo", "".join(m1))
print()

# mutation 2: mapping-side typo only (line 361)
m2 = list(lines)
m2[361 - 1] = m2[361 - 1].replace('"known_basin_reproduction"',
                                  '"known_basin_reproducton"')
print("mutation 2 -- mapping-side typo at line 361 only:")
report("mapping-side typo", "".join(m2))
print()

# mutation 3: fully coordinated rename inside this module (emit + mapping + evidence)
m3 = "".join(lines).replace("known_basin_reproduction", "known_basin_reproducton")
print("mutation 3 -- coordinated rename of ALL occurrences in this module:")
ok3 = report("coordinated rename in-module", m3)
print("      -> in-module guard %s" % ("PASSES" if ok3 else "GOES RED"))
print("      -> but downstream COVERAGE_ROUTES still holds the old spelling, so")
print("         strict_readiness_wiring.py:167-168 would reject it (see PART 3).")

print()
print("=" * 78)
print("PART 6 -- the guard's BLIND SPOT: mapping-side-only typo (line 361)")
print("=" * 78)
print("Mutation 2 PASSES the guard test (see PART 5). What does it actually do")
print("to behaviour? Run the MUTATED mapping block with the CORRECT route name.")
print()

m2_block = textwrap.dedent("\n".join(m2[BLOCK_LINES[0] - 1:BLOCK_LINES[1]]))
ns = {"route": "known_basin_reproduction", "route_note": "<note>", "novelty": NOV,
      "qualified_all": [], "computed": COMPUTED, "dedup_rows": DEDUP}
exec(compile(m2_block, "<mutated-mapping-block>", "exec"), ns)
print("correct route 'known_basin_reproduction' through the MUTATED mapping:")
print("   verdict       = %r   <-- WRONG, should be 'unresolved'" % ns["verdict"])
print("   kept_evidence = %r" % ns["kept_evidence"])

# now feed that outcome to the real downstream validator
rows = [dict(r) for r in real_rows]
rows[0]["route"] = "known_basin_reproduction"   # still a VALID route token
rows[0]["verdict"] = ns["verdict"]              # but downgraded to 'pending'
rows[0]["kept_pool_evidence"] = ""
rows[0]["computed_new_members"] = ""
p = OUTDIR / "synthetic_mapping_side_typo.csv"
with p.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
ok, detail = wiring._check_coverage(p)
print()
print("-- _check_coverage on synthetic_mapping_side_typo.csv --")
print("   ok = %s" % ok)
for prob in detail["problems"]:
    print("   problem: %s" % prob)
print()
print("   => the guard test is BLIND to this mutation, but the downstream gate")
print("      is NOT: verdict=='pending' trips strict_readiness_wiring.py:179-180.")


print("PART 4 -- is the vocabulary guard test present and does it pass?")
print("=" * 78)
import subprocess
import sys
res = subprocess.run(
    [sys.executable, "-B", "-m", "pytest", "-q",
     "tests/test_resolved_route_evidence.py", "-p", "no:cacheprovider"],
    cwd=str(REPO), capture_output=True, text=True)
print("pytest exit code = %d" % res.returncode)
print(res.stdout[-2500:])
if res.stderr.strip():
    print("STDERR:", res.stderr[-1500:])
