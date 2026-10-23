"""Step 3: a NEW campaign must be recognised without touching any name list.

The user's acceptance for the recovery wiring:

    新 campaign/member/attempt 必须被候选注册、导入器、去重器、覆盖复核、成本和
    下游消费者完整识别。**不依赖目录前缀猜测成员角色。**
    合成端到端测试先通过，再生成与提交实际任务。

Two measured hazards motivate these tests:

* discovery was a list of globs keyed on the package NAME, so a new campaign
  naming family was dropped until somebody remembered to extend the list (the
  "UNKNOWN task not in candidates -> continue" family, seen ~8 times);
* the role was DEFAULTED (``pm.get("member_role") or ROUND2_LEDGER_ROLE`` and
  ``cand.get("member_role", "round1_extra")``), so a member whose role was never
  declared silently landed in the wrong bucket -- wrong for dedup, the ceiling
  channel and coverage review.

Failures here must be REFUSALS that get recorded, never silent skips.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"


@pytest.fixture(scope="module")
def imp():
    spec = importlib.util.spec_from_file_location("imp", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(m)
    return m


def _write_pkg(root: Path, name: str, members: list) -> Path:
    pkg = root / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "manifest.json").write_text(
        json.dumps({"package": name, "members": members}), encoding="utf-8")
    return pkg


# ---- discovery: by manifest, not by name ---------------------------------

def test_new_campaign_is_discovered_by_its_manifest(imp, monkeypatch, tmp_path):
    """A family whose NAME matches no glob must still be enumerated."""
    work = tmp_path / "work"
    work.mkdir()
    _write_pkg(work, "hpc_synthetic_campaign_2099",
               [{"member_key": "XX|M_plus|s1", "member_role": "synthetic_role"}])
    monkeypatch.setattr(imp, "REPO", tmp_path)
    names = {p.name for p in imp.iter_packages()}
    assert "hpc_synthetic_campaign_2099" in names


def test_package_without_members_is_not_an_ensemble_package(imp, monkeypatch, tmp_path):
    """The discovery channel must not swallow unrelated work/ packages."""
    work = tmp_path / "work"
    work.mkdir()
    (work / "hpc_unrelated_package").mkdir()
    (work / "hpc_unrelated_package" / "manifest.json").write_text(
        json.dumps({"package": "hpc_unrelated_package"}), encoding="utf-8")
    monkeypatch.setattr(imp, "REPO", tmp_path)
    assert "hpc_unrelated_package" not in {p.name for p in imp.iter_packages()}


def test_malformed_manifest_does_not_raise(imp, tmp_path):
    pkg = tmp_path / "hpc_broken"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{not json", encoding="utf-8")
    assert imp.read_package_manifest(pkg) is None


# ---- the role comes from a DECLARATION, never from the name --------------

def test_role_comes_from_the_manifest_not_the_package_name(imp):
    """A name that LOOKS like a known family must not decide the role."""
    pkg = Path("work/hpc_production_ensemble_strict_recovery_v9")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1",
        {"mol_id": "1", "member_role": "synthetic_role"}, None, {})
    assert reason == ""
    assert role == "synthetic_role", "the manifest declaration must win"
    assert source == "package_manifest"
    assert cand["name"] == "XX" and cand["slot"] == "M_plus"


def test_no_declared_role_is_refused_not_defaulted(imp):
    """The old code produced round2_audit_extra here. It must refuse instead."""
    pkg = Path("work/hpc_production_ensemble_r2_reopt99")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1", {"mol_id": "1"}, None, {})
    assert cand is None and role == ""
    assert reason == "member_role_undeclared"
    assert source == ""


def test_role_falls_back_to_the_candidate_registry(imp):
    """Historical r1 follow-ups declare no role in their manifest but ARE
    registered with one in the candidate registry -- that is a declaration."""
    pkg = Path("work/hpc_production_ensemble_r1_reopt")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1", {"mol_id": "1", "charge": "1"},
        {"mol_id": "1", "member_role": "round1_extra"}, {})
    assert reason == "" and role == "round1_extra"
    assert source == "candidate_registry"


def test_role_falls_back_to_the_structure_ledger(imp):
    """The 101 follow-up members with no manifest role: the ledger already
    declared their role, so that is a declared source rather than a guess."""
    pkg = Path("work/hpc_production_ensemble_r2_reopt4")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1", {"mol_id": "1"}, None,
        {"XX|M_plus|s1": "round2_audit_extra"})
    assert reason == "" and role == "round2_audit_extra"
    assert source == "structure_ledger"


def test_missing_identity_everywhere_is_refused(imp):
    pkg = Path("work/hpc_synthetic_campaign")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1", None, None, {})
    assert cand is None and reason == "member_identity_unknown"


def test_identity_prefers_the_manifest_for_manifest_carrying_families(imp):
    pkg = Path("work/hpc_production_ensemble_strict_recovery_v1")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1",
        {"mol_id": "7", "charge": "2", "multiplicity": "1",
         "source_geometry": "g.xyz", "member_role": "recovery_v1_start"},
        {"mol_id": "999", "member_role": "round1_extra"}, {})
    assert reason == ""
    assert role == "recovery_v1_start", "manifest declares the role"
    assert cand["mol_id"] == "7", "manifest carries the identity"
    assert cand["source_kind"] == "round2_pool_extension"


def test_registry_identity_is_used_when_the_manifest_has_no_role(imp):
    """r1_000-017 shape: manifest member exists but declares no role."""
    pkg = Path("work/hpc_production_ensemble_r1_000-017")
    cand, role, source, reason = imp.resolve_member_identity(
        pkg, "XX", "M_plus", "s1", {"mol_id": "manifest"},
        {"mol_id": "registry", "member_role": "round1_extra"}, {})
    assert reason == "" and role == "round1_extra"
    assert cand["mol_id"] == "registry"


# ---- the production path really calls the resolver -----------------------

def test_importer_loop_calls_the_resolver(imp):
    src = SCRIPT.read_text(encoding="utf-8")
    assert "resolve_member_identity(" in src
    assert "cand, role, role_source, reason = resolve_member_identity(" in src
    # no silent skip and no literal role default may come back
    assert 'print(f"  UNKNOWN task not in candidates' not in src
    assert 'or ROUND2_LEDGER_ROLE' not in src
    assert 'cand.get("member_role", "round1_extra")' not in src


def test_followup_builders_declare_the_role(imp):
    """New packages must be self-describing, so the ledger fallback stays a
    back-compat path rather than the norm."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert src.count('"member_role": row["member_role"]') >= 2


def test_ledger_roles_are_consistent_per_member(imp):
    """Why the ledger is a valid declaration source: one role per member."""
    path = (REPO / "outputs" / "physics_completion" / "ensembles"
            / "production_ensemble_structures.csv")
    if not path.is_file():
        pytest.skip("no structure ledger in this checkout")
    import csv
    by_member = {}
    for row in csv.DictReader(path.open(encoding="utf-8")):
        by_member.setdefault(row["member_key"], set()).add(row["member_role"])
    conflicting = {k: v for k, v in by_member.items() if len(v) > 1}
    assert not conflicting, conflicting
    assert all(v != {""} for v in by_member.values()), "a member with no role"