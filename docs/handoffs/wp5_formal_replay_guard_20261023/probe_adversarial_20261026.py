"""Adversarial probe for the WP5 outer auditor (independent review 2026-10-26).

Injects the six historical bad-evidence classes plus the three-way evidence-state
distinctions through audit.py, using the author's own synthetic fixture.
Writes ONLY inside this review directory (probe_runs_20261026/ + results json).
The input-hash bookkeeping (rehash_*) is deliberate: it keeps the STALE_INPUT_HASH
gate PASSING so that what is actually tested is the SEMANTIC defense, not the hash.
Never a gate; a probe.
"""
from contextlib import redirect_stdout
import csv
import hashlib
import importlib.util
import io
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # .../wp5_formal_replay_guard_20261023
spec = importlib.util.spec_from_file_location("wp5_tests", HERE / "tests" / "test_audit.py")
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)                             # imports audit.py as t.m
m = t.m
BASE, LABELS, COST, FEATURES = t.BASE, t.LABELS, t.COST, t.FEATURES
TARGET_CSV = BASE + "/target_pool_AB.csv"
TARGET_INDEX = BASE + "/target_pool_AB_index.json"

WORK = HERE / "probe_runs_20261026"
RESULTS = []


def read_rows(root, rel):
    with (root / rel).open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def new_case(name, n=7, version="knn_v1"):
    """Fresh, complete, VALID fixture (sub-pool n -> baseline exit 2 PASS/BLOCKED)."""
    root = WORK / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    t.fixture(root, n=n, version=version)
    return root


def run(name, root, version="knn_v1", note=""):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = m.main(["--repo-root", str(root), "--acq-version", version])
    report = json.loads(buf.getvalue())
    RESULTS.append({
        "case": name, "exit": code,
        "integrity": report["integrity"], "full_pool": report["full_pool"],
        "codes": [i["code"] for i in report["issues"]],
        "messages": [i["message"] for i in report["issues"]],
        "submission_gate": report["submission_gate"], "note": note,
    })


def mutate_csv(root, rel, edit):
    rows = read_rows(root, rel)
    edit(rows)
    path = root / rel
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def mutate_json(root, rel, edit):
    path = root / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def rehash_all(root):
    """Refresh BOTH index input-hash maps so the hash gate stays green and the
    SEMANTIC check is what we are actually probing."""
    def fix_target(index):
        index["inputs"][LABELS] = hashlib.sha256((root / LABELS).read_bytes()).hexdigest()
    mutate_json(root, TARGET_INDEX, fix_target)
    replay = root._replay if hasattr(root, "_replay") else BASE

    def fix_ab(index):
        for rel in list(index["inputs"]):
            p = root / rel.replace("\\", "/")
            index["inputs"][rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    mutate_json(root, replay + "/AB_index.json", fix_ab)


def rehash_ab(root, replay):
    def fix(index):
        for rel in list(index["inputs"]):
            p = root / rel.replace("\\", "/")
            index["inputs"][rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    mutate_json(root, replay + "/AB_index.json", fix)


def rehash_target(root):
    def fix(index):
        index["inputs"][LABELS] = hashlib.sha256((root / LABELS).read_bytes()).hexdigest()
    mutate_json(root, TARGET_INDEX, fix)


WORK.mkdir(exist_ok=True)

# ---- control: valid sub-pool must be exit 2, integrity PASS, no issues ----
run("base_valid_subset", new_case("base_valid_subset"),
    note="CONTROL: valid sub-pool must exit 2 / PASS / BLOCKED")

# ---- C1 inline missing key: required field blanked ----
r = new_case("c1a"); mutate_csv(r, BASE + "/AB_round_summary.csv", lambda rows: rows[0].__setitem__("O_3", ""))
run("c1a_missing_key_blank", r, note="C1 one required O_3 field blanked")

# ---- C1b: row physically shorter than header (fewer fields, i.e. dropped keys) ----
r = new_case("c1b")
p = r / (BASE + "/AB_round_summary.csv")
lines = p.read_text(encoding="utf-8").splitlines()
shortened = lines[1][: lines[1].rfind(",")]           # drop the LAST field entirely
p.write_text("\n".join([lines[0], shortened] + lines[2:]) + "\n", encoding="utf-8")
run("c1b_short_row", r, note="C1 first data row has one FEWER field than header (missing key)")

# ---- C2 identity table self-certified with one row ----
r = new_case("c2")
mutate_csv(r, LABELS, lambda rows: rows.__setitem__(slice(None), rows[:1]))
rehash_target(r)
run("c2_one_row_labels", r, note="C2 labels collapsed to 1 row; must NOT self-certify 48")

# ---- C3 status=MISSING but carrying a number ----
r = new_case("c3")
mutate_csv(r, BASE + "/AB_round_summary.csv", lambda rows: rows[0].__setitem__("cumulative_cost_status", "MISSING"))
run("c3_missing_status_with_number", r, note="C3 MISSING cost status but nonblank number kept")

# ---- C3b endpoint status flipped, budget number kept ----
r = new_case("c3b")
mutate_csv(r, BASE + "/AB_axis_endpoint.csv", lambda rows: rows[0].__setitem__("stop_budget_status", "not_reached_within_pool"))
run("c3b_status_flip_number_kept", r, note="C3 says not_reached but keeps stop_budget_n_T")

# ---- C4 invalid status token ----
r = new_case("c4")
mutate_csv(r, LABELS, lambda rows: rows[0].__setitem__("acceptance_status", "invalid_input"))
rehash_target(r)
run("c4_invalid_status", r, note="C4 acceptance_status = invalid_input")

# ---- C5 NaN cost ----
r = new_case("c5")
mutate_csv(r, BASE + "/AB_round_summary.csv", lambda rows: rows[0].__setitem__("cumulative_core_hours_measured", "NaN"))
run("c5_nan_cost", r, note="C5 cost = NaN (a nonempty, parseable-but-not-finite string)")

# ---- C6 trigger/admission flag hardcoded False ----
r = new_case("c6")
mutate_csv(r, TARGET_CSV, lambda rows: [rr.__setitem__("qc_complete_pair", "False") for rr in rows if rr["task"] == "B"])
rehash_all(r)
run("c6_qc_flag_hardcoded_false", r, note="C6 B qc_complete_pair forced False though legs accepted")

# ---- three-way evidence-state distinctions ----
r = new_case("w1")
(r / (BASE + "/AB_index.json")).unlink()
run("w1_not_produced", r, note="W1 artifact NEVER produced -> expect MISSING")

r = new_case("w2")
mutate_json(r, BASE + "/AB_index.json", lambda ix: ix["rows"].__setitem__("AB_axis_endpoint", ix["rows"]["AB_axis_endpoint"] + 1))
run("w2_declared_not_delivered", r, note="W2 index declares a row the artifact does not contain")

r = new_case("w3")
p = r / COST
p.write_bytes(p.read_bytes() + b"\n")
run("w3_stale_declared_input", r, note="W3 declared input bytes changed after index wrote its hash")

r = new_case("w4")
mutate_csv(r, BASE + "/AB_axis_endpoint.csv", lambda rows: rows[0].__setitem__("stop_budget_n_T", "999"))
run("w4_exists_but_fails", r, note="W4 evidence exists but forged stop budget -> STOP_RULE")

run("w5_legal_blocked_subset", new_case("w5", n=7),
    note="W5 legal sub-pool: PASS integrity, BLOCKED full_pool, exit 2")

# ---- report ----
out = HERE / "probe_results_20261026.json"
out.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(RESULTS, ensure_ascii=False, indent=2))
print("PROBE_DONE", len(RESULTS), "cases")
