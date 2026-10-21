"""A submitted package must count as active (in-flight protection).

The protected submitter writes ``submission_journal.json``; an earlier check only
looked for ``submission.json``, so every submitted follow-up (reopt/continuation)
looked INACTIVE and its members were not protected from duplication.  Observed
consequence: the continuation for ``TMP|M_plus|c10`` also re-packaged
``TMP|M_plus|r3_c42``, which a different continuation had already been submitted
for -- the same calculation would have run twice.
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMP = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"


def _m():
    spec = importlib.util.spec_from_file_location("imp_active", IMP)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(IMP.parent))
    spec.loader.exec_module(mod)
    return mod


def test_submission_journal_marks_a_package_active():
    m = _m()
    cont = REPO / "work" / "hpc_production_ensemble_strict_recovery_v1_cont1"
    if not cont.is_dir():
        return
    # cont1 was submitted through the protected submitter -> journal, no submission.json
    assert (cont / "submission_journal.json").is_file()
    assert m.rescue_package_is_active(cont) is True


def test_continuation_packages_never_duplicate_a_member():
    """Two continuation packages must not own the same member."""
    members = {}
    for name in ("hpc_production_ensemble_strict_recovery_v1_cont1",
                 "hpc_production_ensemble_strict_recovery_v1_cont2"):
        man = REPO / "work" / name / "manifest.json"
        if not man.is_file():
            continue
        doc = json.loads(man.read_text(encoding="utf-8"))
        members[name] = {x["member_key"] for x in doc.get("members", [])}
    if len(members) < 2:
        return
    overlap = set.intersection(*members.values()) if len(members) > 1 else set()
    assert not overlap, "members owned by two packages: %s" % overlap


def test_reopt_package_is_active_and_would_not_be_duplicated():
    m = _m()
    reopt = REPO / "work" / "hpc_production_ensemble_strict_recovery_v1_reopt1"
    if not reopt.is_dir():
        return
    assert (reopt / "submission_journal.json").is_file()
    assert m.rescue_package_is_active(reopt) is True
