"""The chain must never contain a raw backspace from a mangled \\build escape.

This bug hit three times: writing a Step line via a Python heredoc turns the
``\\b`` of ``\\build_...`` into a literal backspace (0x08), so the step dies with
``can't open file ...\\x08uild_...`` at RUNTIME -- after the chain already ran
its first 40 steps.  The tests byte-scan the chain for any control character
below 0x20 (excluding CR/LF/TAB) so this whole failure class dies at pytest
time instead.
"""
from pathlib import Path

# --- declared dependency on the gitignored `work/` layer (step 12) -----------
# A clean clone has no `work/` (raw ledgers/logs/geometries, 12 GB, untracked).
# The builders refuse loudly when it is missing (pinned by
# test_clean_clone_dependencies.py), so a test consuming a dev-tree fixture
# declares the need and skips WITH A REASON -- never silently passing.
import pytest as _pytest_work_layer

if not (Path(__file__).resolve().parents[1] / "work" / "wp2prod").is_dir():
    _pytest_work_layer.skip(
        "the machine-local work/wp2prod evidence layer (gitignored) is absent in this checkout; "
        "the builders' loud refusal is pinned by test_clean_clone_dependencies.py",
        allow_module_level=True,
    )
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]
CHAIN = REPO / "scripts" / "wp_production" / "finalize_wp2.ps1"


def test_chain_contains_no_control_bytes():
    data = CHAIN.read_bytes()
    bad = [(i, b) for i, b in enumerate(data)
           if b < 0x20 and b not in (0x0A, 0x0D, 0x09)]
    assert not bad, "control bytes at offsets %s (first: %r)" % (
        [i for i, _ in bad[:5]], bad[0][1] if bad else None)


def test_every_step_references_an_existing_script():
    """Each Step's script path must exist -- catches backslash mangling too."""
    import re
    text = CHAIN.read_text(encoding="utf-8")
    # only .ps1/.py/.exe script references; flags like -m pytest are excluded
    steps = re.findall(r'Step "[^"]+" \{ & \$py -X utf8 ([^ }]+\.(?:py|ps1))', text)
    assert steps, "no steps found"
    missing = []
    for rel in steps:
        rel2 = rel.replace("\\\\", "\\")
        if not (REPO / rel2).exists():
            missing.append(rel)
    assert not missing, "step scripts missing: %s" % missing
