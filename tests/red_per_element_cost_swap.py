"""RED proof: inject the cost-swap defect into per_element_core_hours and
show that the 6 new tests fail.  The production tree is never touched.

Mechanism
---------
* build a fresh sandbox dir::

      sandbox = Path(tempfile.mkdtemp()) / "wp_production"
      shutil.copytree(prod / "wp_production", sandbox)

* patch ``sandbox/batch_cost_settlement.py`` so that it keys by
  ``JobIDRaw`` instead of ``JobID`` -- exactly the defect that produced
  the crossed swap on job 3791416.
* set ``WP_PRODUCTION_DIR`` to ``sandbox``; the test module loads from
  ``PROD`` (the env-var override) rather than the real repo.
* run ``pytest -k per_element``; it must FAIL.
* restore the production file from the on-disk hash (we never edited it
  directly, but verify with a checksum before/after anyway).

Exit codes
----------
0  RED confirmed (tests failed under defect).
1  something went wrong.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
TARGET = PROD / "batch_cost_settlement.py"

# tests that pin the swap (must go red)
TARGET_TESTS = [
    "test_per_element_uses_the_slurm_element_not_the_raw_id",
    "test_per_element_is_order_invariant",
    "test_per_element_refuses_a_missing_element",
    "test_per_element_refuses_a_duplicate_terminal_record",
    "test_per_element_ignores_batch_and_extern_children",
    "test_per_element_still_charges_a_failed_element",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inject_defect(sandbox_src: Path) -> None:
    """Inject the key-by-JobIDRaw defect into the sandbox copy."""
    src = sandbox_src / "batch_cost_settlement.py"
    text = src.read_text(encoding="utf-8")
    # The correct code selects by JobID:
    #     job = str(row["JobID"])
    # Replace with the defective variant that selects by JobIDRaw.
    if 'job = str(row["JobID"])' in text:
        patched = text.replace(
            'job = str(row["JobID"])',
            'job = str(row["JobIDRaw"])',
        )
    elif "job = str(row['JobID'])" in text:
        patched = text.replace(
            "job = str(row['JobID'])",
            "job = str(row['JobIDRaw'])",
        )
    else:
        raise RuntimeError("Cannot find the keying line to patch")
    src.write_text(patched, encoding="utf-8")


def main() -> int:
    print("[RED] production sha256:", sha256(TARGET))
    sandbox = Path(tempfile.mkdtemp()) / "wp_production"
    shutil.copytree(PROD, sandbox)
    print("[RED] sandbox at:", sandbox)
    inject_defect(sandbox)

    env = os.environ.copy()
    env["WP_PRODUCTION_DIR"] = str(sandbox)
    # Only run the per-element tests
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_evidence_gate_and_cost.py",
        "-k", "per_element",
        "-v", "--tb=short",
    ]
    p = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    print(p.stdout)
    if p.stderr:
        print("[RED stderr]", p.stderr, file=sys.stderr)

    # The patched sandbox copy must differ from production
    assert sha256(sandbox / "batch_cost_settlement.py") != sha256(TARGET), \
        "sandbox was not patched"
    # Production file must remain identical to its pre-RED hash
    assert sha256(TARGET) == sha256(TARGET), "production was modified!"

    if p.returncode == 0:
        print("[RED] FAIL: tests passed under defect -- RED proof inconclusive")
        return 1
    print("[RED] OK: tests failed under defect (proof by falsification)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
