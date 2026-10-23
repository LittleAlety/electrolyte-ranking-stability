"""Step 12: "生成/check配对" -- close the two generators covered only indirectly.

Auditing the chain (79 steps: 42 generate + 37 check) leaves five scripts without
a `--check` step of their own:

* ``check_wp2_anchors`` / ``audit_clean_room`` / ``verify_archive`` -- they ARE
  checkers, nothing to pair;
* ``freeze_gates``  -- its products are verified by the chain's
  ``refreeze_manifest --check`` steps;
* ``emit_wp2``      -- **no argparse at all** (``--check`` is silently ignored),
  and its product (``scripts/build_physics_completion_batch.py``) is regenerated
  by the very next step, so ``check-gen`` compares recomputed batches against
  freshly written ones -- a drift in emit's anchors would move BOTH sides in
  lockstep and still pass.

This file supplies the missing assertion for the last two: ``emit_wp2`` must be
**idempotent** (byte-identical generator after a run), and the freeze gate must be
covered by a refreeze check.  The idempotence test restores the original file if
the invariant is violated, so a failure cannot corrupt the tree.
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"
GEN = REPO / "scripts" / "build_physics_completion_batch.py"
EMIT = REPO / "scripts" / "wp_production" / "emit_wp2.py"
CHAIN = REPO / "scripts" / "wp_production" / "finalize_wp2.ps1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.skipif(not PY.is_file(), reason="project venv interpreter not present")
def test_emit_wp2_is_idempotent(tmp_path):
    """Running emit_wp2 must reproduce the SAME generator bytes.

    Restores the original on violation: a failing invariant must not leave the
    tree modified (that would turn this test into the defect it guards against).
    """
    backup = tmp_path / "build_physics_completion_batch.py"
    shutil.copy2(GEN, backup)
    before = _sha(GEN)

    proc = subprocess.run([str(PY), "-X", "utf8", str(EMIT)], cwd=str(REPO),
                          capture_output=True, text=True, encoding="utf-8",
                          timeout=600)
    assert proc.returncode == 0, proc.stdout[-300:] + proc.stderr[-300:]

    after = _sha(GEN)
    if after != before:
        shutil.copy2(backup, GEN)          # put it back before failing
    assert after == before, (
        "emit_wp2 is not idempotent: it rewrote the generator. The chain would "
        "not notice (check-gen compares recomputed batches to freshly written "
        "ones), so this is the only guard. Original content restored.")


@pytest.mark.skipif(not PY.is_file(), reason="project venv interpreter not present")
def test_the_generator_still_reproduces_the_batches():
    """The generator's own --check must pass after emit: the pairing is real."""
    proc = subprocess.run(
        [str(PY), "-X", "utf8", str(REPO / "scripts"
                                    / "build_physics_completion_batch.py"), "--check"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        timeout=900)
    assert proc.returncode == 0, proc.stdout[-400:]


def test_the_freeze_gate_is_paired_with_refreeze_checks():
    """freeze_gates has no --check, so the chain must verify its products."""
    text = CHAIN.read_text(encoding="utf-8")
    checks = re.findall(r"refreeze_manifest\.py\s+--manifest\s+(\S+)\s+--check", text)
    assert len(checks) >= 3, checks
    assert any("week1" in c for c in checks)


def test_the_chain_order_makes_the_pairing_necessary():
    """The reason this test exists: emit precedes the generator it rewrites."""
    text = CHAIN.read_text(encoding="utf-8")
    assert text.index('Step "emit-wp2"') < text.index('Step "generator"')
    assert text.index('Step "generator"') < text.index('Step "check-gen"')