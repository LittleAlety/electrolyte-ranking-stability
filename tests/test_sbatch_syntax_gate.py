"""Generated sbatch scripts must be valid bash BEFORE they are ever uploaded.

A quoting bug in ``build_frontier_legs._SBATCH`` shipped a perfectly-looking
package whose every task died instantly::

    /var/spool/slurm/.../slurm_script: line 19:
        unexpected EOF while looking for matching `"'

Slurm reports the failure at *runtime*, per task, after the batch has been
submitted -- 8 wasted submissions and a batch id burned, with no ORCA output at
all.  The root cause was the ``sed`` line combining the arithmetic expansion and
the filename inside one quoted string::

    line=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p batch_%d.txt)   # broken

The fix uses an explicit index variable and the builder now refuses to emit a
script that fails ``bash -n`` (see ``_check_shell_syntax``).

These tests keep both properties.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "scripts" / "wp_production" / "build_frontier_legs.py"
PKG = REPO / "work" / "hpc_frontier_localization_v1"


def _m():
    spec = importlib.util.spec_from_file_location("frontier_build", BUILD)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(BUILD.parent))
    spec.loader.exec_module(mod)
    return mod


def test_builder_rejects_a_syntactically_broken_script(tmp_path):
    m = _m()
    bad = tmp_path / "bad.sbatch"
    bad.write_text("#!/bin/bash\nif [ -f x ]; then\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        m._check_shell_syntax(bad)


def test_builder_accepts_a_valid_script(tmp_path):
    m = _m()
    good = tmp_path / "good.sbatch"
    good.write_text('#!/bin/bash\nidx=1\necho "${idx}"\n', encoding="utf-8")
    m._check_shell_syntax(good)          # must not raise


def test_the_shipped_template_uses_an_explicit_index_variable():
    """The fragile one-liner must not come back."""
    src = BUILD.read_text(encoding="utf-8")
    assert 'idx=$((SLURM_ARRAY_TASK_ID + 1))' in src
    assert 'sed -n "${idx}p" batch_%d.txt' in src
    # the broken form put the arithmetic expansion and the filename in one string
    assert not re.search(r'p batch_%\d*\.?txt\)\s*$', src, re.M)


@pytest.mark.skipif(not PKG.is_dir(), reason="frontier package not built")
def test_every_generated_batch_script_parses():
    scripts = sorted(PKG.glob("batch_*.sbatch"))
    assert scripts, "no batch scripts found"
    for script in scripts:
        proc = subprocess.run(["bash", "-n", str(script)],
                              capture_output=True, text=True, errors="replace")
        assert proc.returncode == 0, "%s: %s" % (script.name, proc.stderr.strip())


@pytest.mark.skipif(not PKG.is_dir(), reason="frontier package not built")
def test_each_batch_reads_its_own_listing():
    """Batch N must read batch N's task list, never batch 1's."""
    for script in sorted(PKG.glob("batch_*.sbatch")):
        n = int(script.stem.split("_")[1])
        text = script.read_text(encoding="utf-8")
        assert "batch_%d.txt" % n in text, script.name
        if n != 1:
            assert "batch_1.txt" not in text, "%s still reads batch 1" % script.name
