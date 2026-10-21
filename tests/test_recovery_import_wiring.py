"""The recovery batches must be importable (plan items ①/③ wiring).

Two silent-skip hazards are pinned here, both of which would make a finished
production leg vanish without any error:

1. ``iter_packages()`` must enumerate the recovery package family -- otherwise
   the importer never looks inside them;
2. ``_is_round2_package()`` must accept them -- otherwise their members are not
   matched against the package manifest and the loop prints
   "UNKNOWN task not in candidates", then skips the leg.

And the role semantics: a recovery member is ``recovery_v1_start`` -- it counts
for BOTH acceptance and the ceiling, unlike ``round2_audit_extra``.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMP = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"
AGG = REPO / "scripts" / "wp_production" / "build_production_ensemble_aggregator.py"
DIFF = REPO / "scripts" / "wp_production" / "build_sampling_3to6_diff.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


def test_retry_packages_are_enumerated():
    m = _load("imp", IMP)
    names = {p.name for p in m.iter_packages()}
    assert any("strict_recovery" in n for n in names), sorted(names)


def test_recovery_packages_are_recognised_as_manifest_member_packages():
    """Without this the importer reports UNKNOWN task and silently drops legs."""
    m = _load("imp", IMP)
    for name in ("hpc_production_ensemble_strict_recovery_v1",
                 "hpc_production_ensemble_strict_recovery_v1_b2"):
        assert m._is_round2_package(Path(name)) is True, name
    # a plain round-1 package is still not one
    assert m._is_round2_package(Path("hpc_production_ensemble_r1_000-017")) is False


def test_aggregator_treats_recovery_members_as_first_class():
    src = AGG.read_text(encoding="utf-8")
    assert '"round1_extra", "recovery_v1_start"' in src
    # and the coverage-review gate is still the only route out of `limited`
    assert "n_limited and not cov_resolved" in src


def test_ceiling_channel_accepts_recovery_members():
    src = DIFF.read_text(encoding="utf-8")
    assert '"round2_audit_extra", "recovery_v1_start"' in src


def test_package_manifest_carries_the_recovery_role():
    """The submitted batch-1 package must already declare the new role."""
    import json
    man = (REPO / "work" / "hpc_production_ensemble_strict_recovery_v1"
           / "manifest.json")
    if not man.is_file():
        return
    doc = json.loads(man.read_text(encoding="utf-8"))
    roles = {m.get("member_role") for m in doc.get("members", [])}
    assert roles == {"recovery_v1_start"}, roles
