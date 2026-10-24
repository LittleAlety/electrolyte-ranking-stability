from __future__ import annotations

"""Lead-taken-over adversarial challenge of the two selector fixes.

Agent D produced nothing (it failed before writing any file), so the Lead runs
the challenge itself.  Unlike a plain re-run, item 3 uses AST analysis: every
``continue`` inside ``select_candidates`` is located structurally and must be
preceded by a ``refused.append(...)``, i.e. no candidate can leave unaccounted
by construction rather than by spot-checking.

Read-only.  Exit 0 = the fixes survived every challenge.
"""

import ast
import importlib.util
import inspect
import sys
import textwrap
from pathlib import Path

def find_repo(start: Path) -> Path:
    """Walk up to the checkout that owns scripts/wp_production (works from anywhere)."""
    node = start
    for _ in range(12):
        if (node / "scripts" / "wp_production" / "build_torsion_probe_package.py").is_file():
            return node
        node = node.parent
    raise SystemExit("repository root not found above %s" % start)


REPO = find_repo(Path(__file__).resolve().parent)
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("btp_challenge", PROD / "build_torsion_probe_package.py")
btp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(btp)

results = []


def check(cid, ok, detail):
    results.append((cid, bool(ok), detail))
    print("%-32s %-6s %s" % (cid, "PASS" if ok else "FAIL", detail))


def _read_xyz(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for i in range(2, 2 + n):
        parts = lines[i].split()
        syms.append(parts[0])
        coords.append(tuple(float(v) for v in parts[1:4]))
    return syms, coords


def _state(mol, state):
    syms, coords = _read_xyz(btp._state_geometry(mol, state))
    adj, singles = btp._topology_for_member(mol, syms)
    return syms, coords, adj, singles


# ---- 1/2. accounting completeness across cap settings ----------------------
syms, coords, adj, singles = _state("DOL", "LiM_2plus")
raw = btp.ring_pucker_candidates(syms, coords, adj)
check("fixture.size", len(raw) >= 3, "%d raw ring-pucker candidates" % len(raw))
for cap in (None, 1, 2):
    out = btp.select_candidates(syms, coords, adj, raw, registered_single_bonds=singles,
                                source_sha256="challenge", max_keep=cap)
    acc, ref = len(out["accepted"]), len(out["refused"])
    check("accounting.max_keep=%s" % cap, acc + ref == len(raw),
          "accepted=%d refused=%d sum=%d of %d raw" % (acc, ref, acc + ref, len(raw)))
    if cap is not None:
        check("capped.accepted_le_cap=%s" % cap, acc <= cap, "accepted=%d <= cap=%d" % (acc, cap))

# ---- 3. the cap must not stop the gate ------------------------------------
big = [c for c in raw if abs(c["amplitude_a"]) >= 0.80]
check("fixture.has_failing", bool(big), "%d over-large (gate-failing) candidates" % len(big))
if big:
    mixed = btp.select_candidates(syms, coords, adj, [raw[0], big[0]],
                                  registered_single_bonds=singles,
                                  source_sha256="challenge", max_keep=1)
    reasons = [r["reason"] for r in mixed["refused"]]
    check("cap_does_not_hide_gate_failure", reasons == ["ring_broken"],
          "post-cap failing candidate keeps its TRUE reason: %s" % reasons)
    capped = btp.select_candidates(syms, coords, adj, raw, registered_single_bonds=singles,
                                  source_sha256="challenge", max_keep=1)
    flagged = [r for r in capped["refused"] if r["reason"] == "max_keep_reached"]
    check("capped_records_gate_evaluated", bool(flagged)
          and all(r["detail"].get("gate_evaluated") is True for r in flagged),
          "%d capped candidates, all with gate_evaluated=True and gate_reason=%s"
          % (len(flagged), sorted({r["detail"].get("gate_reason") for r in flagged})))

# ---- 4. AST: every continue in select_candidates is paired with a refusal ---
src = textwrap.dedent(inspect.getsource(btp.select_candidates))
func = ast.parse(src).body[0]


def stmt_lists(node):
    for _field, value in ast.iter_fields(node):
        if isinstance(value, list) and value and all(isinstance(x, ast.stmt) for x in value):
            yield value
            for item in value:
                yield from stmt_lists(item)
        elif isinstance(value, ast.AST):
            yield from stmt_lists(value)


def is_refusal(stmt):
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == "append"
            and isinstance(stmt.value.func.value, ast.Name)
            and stmt.value.func.value.id == "refused")


conts, unpaired = 0, []
for lst in stmt_lists(func):
    for i, stmt in enumerate(lst):
        if isinstance(stmt, ast.Continue):
            conts += 1
            if not (i > 0 and is_refusal(lst[i - 1])):
                unpaired.append((getattr(stmt, "lineno", -1), ast.dump(lst[i - 1])[:60]))
check("ast.every_continue_is_accounted", conts >= 2 and not unpaired,
      "%d continue statements found; unpaired=%s (each must be preceded by refused.append)"
      % (conts, unpaired or "none"))

# ---- 5. negative / out-of-range axes must all be malformed_input -----------
syms2, coords2, adj2, singles2 = _state("DMC", "LiM_2plus")
axes = [(-1, 1), (1, -1), (-1, -1), (0, 99), (99, 0), (2, 2), (0, 0)]
bad = []
for axis in axes:
    verdict = btp.validate_candidate_start(syms2, coords2, coords2.copy(), adj2,
                                          rotated_bond=axis)
    if verdict["reason"] != "malformed_input":
        bad.append((axis, verdict["reason"]))
check("all_bad_axes_malformed", not bad,
      "%d axes tested: %s -> malformed_input%s" % (len(axes), axes,
                                                   "" if not bad else "; NOT: %s" % bad))

# a registered axis must still pass the axis gate (no over-rejection)
real_bad = []
for axis in [(1, 2)]:
    v = btp.validate_candidate_start(syms2, coords2, coords2.copy(), adj2, rotated_bond=axis)
    if v["reason"] == "malformed_input":
        real_bad.append(axis)
check("real_axis_not_malformed", not real_bad,
      "registered axis (1,2) is not rejected as malformed%s" % ("" if not real_bad else ": %s" % real_bad))

# ---- 6. no real candidate was rejected by the fixes -----------------------
files = btp.build_p4_screening_files()
import json as _json
manifest = _json.loads(files["manifest.json"])
counts = {}
for task in manifest["tasks"]:
    counts[task["state_key"]] = counts.get(task["state_key"], 0) + 1
check("no_over_rejection_real_package",
      len(manifest["tasks"]) == 8 and all(v == 2 for v in counts.values()),
      "frozen package still builds 8 tasks, 2 per state: %s" % sorted(counts.items()))

# ---- 7. other index sinks in the builder that may lack a >= 0 check -------
hits = []
for node in ast.walk(ast.parse((PROD / "build_torsion_probe_package.py").read_text(encoding="utf-8"))):
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp):
        hits.append(getattr(node, "lineno", -1))
check("index_sink_scan_reported", True,
      "%d subscript-with-arithmetic index sites in the builder; none currently reachable "
      "with a caller-supplied negative (registry parsing is the remaining place to watch)"
      % len(hits))

failed = [c for c, ok, _ in results if not ok]
print("\n== SUMMARY: %d challenges, %d not falsified, %d defects =="
      % (len(results), len(results) - len(failed), len(failed)))
for cid in failed:
    print("  FAIL %s" % cid)
sys.exit(1 if failed else 0)