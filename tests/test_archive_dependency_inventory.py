"""Step 12: the chain's machine-local dependencies must be DECLARED.

"大型原始计算证据可以通过声明的归档来源提供，但**依赖必须显式**，缺失不能被静默跳过."

``docs/handoffs/four_state_recovery_20261023/ARCHIVE_DEPENDENCIES.json`` declares,
for every closure-chain script that reads the gitignored ``work/`` layer, WHAT it
reads, WHY, WHICH archive the evidence comes from, and HOW it fails when the layer
is absent.

This test RE-DERIVES the set of such scripts from the chain and requires it to
match the declaration, so a new dependency cannot be introduced silently.  It also
forbids an entry from claiming silent degradation: the plan's whole point is that a
missing dependency must fail loudly.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CHAIN = REPO / "scripts" / "wp_production" / "finalize_wp2.ps1"
PROD = REPO / "scripts" / "wp_production"
INVENTORY = (REPO / "docs" / "handoffs" / "four_state_recovery_20261023"
             / "ARCHIVE_DEPENDENCIES.json")


def _inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))["entries"]


def _chain_scripts() -> set:
    """Scripts the closure chain invokes (either scripts/ or scripts/wp_production/)."""
    text = CHAIN.read_text(encoding="utf-8")
    names = set()
    for m in re.finditer(r"scripts\\(?:wp_production\\)?([A-Za-z0-9_]+\.py)", text):
        names.add(m.group(1))
    return names


def _readers(names: set) -> set:
    """Those of `names` that reference the machine-local work/ layer."""
    out = set()
    for n in names:
        for base in (PROD, REPO / "scripts"):
            p = base / n
            if not p.is_file():
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            for line in src.splitlines():
                if line.lstrip().startswith("#"):
                    continue
                if ('"work"' in line or "'work'" in line or "work/" in line):
                    out.add(n)
                    break
            break
    return out


def test_the_inventory_file_exists_and_is_machine_readable():
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    # the rule is authored in English in the JSON; the Chinese form lives in the MD
    assert "must fail loudly" in data["rule"]
    assert "silently" in data["rule"] or "silent" in data["rule"]
    assert data["entries"]


def test_every_chain_script_that_reads_work_is_declared():
    """The re-derived set must equal the declared set -- no silent new dependency."""
    declared = set(_inventory())
    derived = _readers(_chain_scripts())
    assert derived, "the derivation itself must find the known readers"
    missing = sorted(derived - declared)
    assert not missing, ("chain scripts reading work/ but not declared: %s" % missing)
    stale = sorted(declared - derived)
    assert not stale, ("declared but no longer reading work/: %s" % stale)


def test_every_entry_declares_what_why_where_and_how_it_fails():
    for name, entry in _inventory().items():
        assert entry.get("reads"), name
        assert entry.get("purpose"), name
        assert entry.get("declared_source"), name
        assert entry.get("on_missing"), name


def test_every_entry_declares_a_loud_failure_or_an_explicit_not_applicable():
    """POSITIVE test: the failure mode must say HOW it is loud.

    A substring test for "silent" is self-defeating here -- the refusal messages
    legitimately explain what the silent version WOULD have been ("an empty ledger
    is a silent skip, not zero cost").  Assert the loud marker instead.
    """
    loud = ("loud", "REFUSING", "raise", "fail", "not_applicable")
    offenders = [n for n, e in _inventory().items()
                 if not any(tok.lower() in e["on_missing"].lower() for tok in loud)]
    assert not offenders, offenders


def test_the_three_hardened_refusals_are_declared_as_loud():
    inv = _inventory()
    for name in ("build_ensemble_cost_by_family.py",
                 "build_coverage_reviews.py",
                 "build_recovery_budget_accounting.py"):
        assert name in inv, name
        assert "REFUSING" in inv[name]["on_missing"], inv[name]


def test_the_undeclared_archive_part_is_stated_honestly():
    """The main-state ledgers' archive address is NOT registered yet -- say so."""
    text = (INVENTORY.parent / "ARCHIVE_DEPENDENCIES.md").read_text(encoding="utf-8")
    assert "尚未声明来源" in text or "尚未在仓库内登记" in text


def test_the_three_refusals_actually_raise(tmp_path, monkeypatch):
    """The declaration is not a claim: each refusal is exercised."""
    sys.path.insert(0, str(PROD))
    for script, call, needle in (
            ("build_ensemble_cost_by_family", "build_rows", "silent skip"),
            ("build_recovery_budget_accounting", "collect", "nothing was spent")):
        spec = importlib.util.spec_from_file_location(script, PROD / (script + ".py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        monkeypatch.setattr(m, "REPO", tmp_path)
        with pytest.raises(SystemExit) as exc:
            getattr(m, call)()
        assert needle in str(exc.value), (script, str(exc.value))

    spec = importlib.util.spec_from_file_location(
        "build_coverage_reviews", PROD / "build_coverage_reviews.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "REPO", tmp_path)
    with pytest.raises(SystemExit) as exc:
        m._rejected_probe_members()
    assert "re-admit" in str(exc.value)