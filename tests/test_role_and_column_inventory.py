"""Inventory guards for the two silent-failure bug classes found in this project.

Both bugs below shipped and looked healthy for a long time; neither raised, and
both made results silently vanish.

**Bug class 1 -- a role filter missing a role.**
``latest_attempt_per_member()`` in the aggregator read::

    if r["member_role"] != "round1_extra":
        continue

so rows with ``member_role = recovery_v1_start`` never entered ``latest``.  The
aggregator then treated every recovery member as "registered but no result yet"
(``n_pending``) and no state could ever leave ``limited``.  The same shape
appeared in ``members_in_flight()``'s ``covered`` set.

**Bug class 2 -- reading the wrong column name.**
``build_coverage_reviews.py`` filtered with ``r.get("state")`` while
``production_ensemble_structures.csv`` names that column ``slot``.  ``members``
was therefore permanently empty, which is why the ``unresolved`` verdict had
never once appeared in the project's history.

These tests are deliberately data-driven where possible so a future rename or a
newly introduced role fails loudly instead of degrading silently.
"""
import csv
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts" / "wp_production"
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

STRUCTURES = ENS / "production_ensemble_structures.csv"
LABELS = ENS / "production_ensemble_labels.csv"
CANDIDATES = ENS / "production_ensemble_candidates.csv"
WEIGHTS = ENS / "production_ensemble_weights.csv"


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _columns(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)
        return set(next(reader))


def _source(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def _function_body(source: str, func: str) -> str:
    """The text of ``def func(...)`` up to the next top-level ``def``."""
    m = re.search(r"^def %s\(" % re.escape(func), source, re.M)
    if not m:
        return ""
    rest = source[m.start():]
    nxt = re.search(r"^def ", rest[1:], re.M)
    return rest[: nxt.start() + 1] if nxt else rest


# --------------------------------------------------------------------------
# Bug class 1: role filters
# --------------------------------------------------------------------------

def test_every_role_present_in_the_ledger_is_handled_in_code():
    """A role that exists in the data must be named somewhere in the code.

    If someone introduces a new ``member_role`` and no code path recognises it,
    the member is silently ignored -- exactly how the acceptance path broke.
    """
    data_roles = {r["member_role"] for r in _rows(STRUCTURES) if r.get("member_role")}
    data_roles |= {r["member_role"] for r in _rows(CANDIDATES) if r.get("member_role")}
    assert data_roles, "no roles found in the ledger -- wrong fixture path?"

    code_roles = set()
    for path in SCRIPTS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        code_roles |= set(re.findall(r'"([a-z0-9_]+_extra)"', text))
        code_roles |= set(re.findall(r'"(recovery_v1_start)"', text))
        # the base role is referenced as a plain literal, never with a suffix
        code_roles |= set(re.findall(r'"(primary)"', text))
        # roles are also referenced through named constants (ROUND2_LEDGER_ROLE
        # == "round2_audit_extra"), so resolve those constants too
        for const, value in re.findall(
                r'^([A-Z0-9_]*ROLE[A-Z0-9_]*)\s*=\s*"([a-z0-9_]+)"', text, re.M):
            code_roles.add(value)
    missing = data_roles - code_roles
    assert not missing, "roles in the ledger that no code path names: %s" % sorted(missing)


@pytest.mark.parametrize("module,func,required", [
    # the pool builder: both roles are first-class members (acceptance + ceiling)
    ("build_production_ensemble_aggregator.py", "latest_attempt_per_member",
     ["round1_extra", "recovery_v1_start"]),
    # the candidate loader: same contract
    ("build_production_ensemble_aggregator.py", "load_candidates",
     ["round1_extra", "recovery_v1_start"]),
    # the in-flight protection set must know every role that can own an attempt,
    # otherwise a member looks permanently in flight and the next attempt is blocked
    ("import_ensemble_structures.py", "members_in_flight",
     ["round1_extra", "round2_audit_extra", "recovery_v1_start"]),
    # the 3->6 ceiling extension accepts both extension roles
    ("build_sampling_3to6_diff.py", "load_round2_members",
     ["round2_audit_extra", "recovery_v1_start"]),
])
def test_first_class_role_filters_list_every_required_role(module, func, required):
    body = _function_body(_source(module), func)
    assert body, "%s not found in %s" % (func, module)
    aliases = {"round2_audit_extra": ("round2_audit_extra", "ROUND2_LEDGER_ROLE")}
    missing = [role for role in required
               if not any(a in body for a in aliases.get(role, (role,)))]
    assert not missing, "%s() no longer handles %s" % (func, missing)


# --------------------------------------------------------------------------
# Bug class 2: column names
# --------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    STRUCTURES: [
        # read by the aggregator, the coverage reviews and the recovery report
        "member_key", "slot", "name", "seed", "member_role", "attempt",
        "status", "failure_class", "final_geometry_sha256", "log_sha256",
        "imaginary_modes", "lowest_freq_cm1", "convergence_note",
    ],
    LABELS: [
        "name", "state", "acceptance_status", "coverage_status",
        "coverage_review_id", "n_unique", "n_qc_failed", "limitation_reason",
        "g_ensemble_eh",
    ],
    # the candidates table identifies a member by (name, slot, seed); it has no
    # member_key column -- the aggregator composes the key itself
    CANDIDATES: ["name", "slot", "seed", "member_role", "geometry", "status"],
    WEIGHTS: ["member_key", "attempt", "name", "slot", "boltzmann_weight"],
}


@pytest.mark.parametrize("path", list(REQUIRED_COLUMNS), ids=lambda p: Path(p).name)
def test_every_required_column_exists(path):
    """A renamed column must fail here, not silently empty a filter."""
    columns = _columns(path)
    if not columns:
        pytest.skip("%s not built yet" % Path(path).name)
    missing = [c for c in REQUIRED_COLUMNS[path] if c not in columns]
    assert not missing, "%s is missing required columns %s" % (Path(path).name, missing)


def test_structures_identifies_states_by_slot_not_state():
    """The exact defect: structures has ``slot``; reading ``state`` yields nothing.

    ``labels`` does use ``state`` -- so the two tables must be read with
    different column names, and a copy-paste between them is always wrong.
    """
    if not STRUCTURES.is_file():
        pytest.skip("structures table not built yet")
    columns = _columns(STRUCTURES)
    assert "slot" in columns
    assert "state" not in columns, (
        "structures gained a 'state' column; revisit every reader that used 'slot'")

    body = _function_body(_source("build_coverage_reviews.py"), "build_rows")
    assert 'r.get("slot") == state' in body, (
        "coverage reviews must read the structures table's 'slot' column")
    assert 'r.get("state") == state' not in body


def test_labels_identifies_states_by_state():
    """The mirror image of the test above, so the asymmetry stays intentional."""
    if not LABELS.is_file():
        pytest.skip("labels table not built yet")
    columns = _columns(LABELS)
    assert "state" in columns
    assert "slot" not in columns, (
        "labels gained a 'slot' column; the label readers assume 'state'")


def test_resolved_reviews_claim_members_that_are_really_kept():
    """The anti-cheat direction: evidence for a resolution must be real."""
    reviews = _rows(RECOVERY / "coverage_reviews.csv")
    if not reviews:
        pytest.skip("coverage reviews not built yet")
    weights = {r["member_key"] for r in _rows(WEIGHTS)}
    for row in reviews:
        if row.get("verdict") != "resolved":
            continue
        # evidence shape follows the route: multi-basin claims the new minima
        # themselves; single-basin claims the KEPT minima the starts reproduced
        if row.get("route") == "single_basin_verified":
            claimed = [c for c in (row.get("kept_pool_evidence") or "").split(";") if c]
        else:
            claimed = [c for c in (row.get("computed_new_members") or "").split(";") if c]
        assert claimed, "a resolved review must name the member it released"
        for key in claimed:
            assert key in weights, (
                "%s resolved but %s is not a weighted (kept) member" % (row["review_id"], key))
