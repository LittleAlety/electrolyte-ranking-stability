"""Step 12: a skip must be DECLARED --- "缺失不能被静默跳过".

The plan's clean-environment rule applies to the test suite too: a test that
quietly skips because an input is missing turns a missing dependency into a green
run.

Measured in this checkout: **8 skips, all with an explicit reason**

    test_week36_final_submission.py (7)  module-level ``pytestmark = skipif``
                                         on the week36 submission evidence
    test_hpc_numfreq_import.py     (1)  ``pytest.skip("external raw continuation
                                         fixture or its original local source is
                                         unavailable")``

The analysis walks the **AST**, not the source text: a regex over source matches
its own documentation (measured -- the first version of this file reported its own
docstring as a "bare skip", and missed the module-level ``pytestmark`` form
entirely).  Both mistakes are pinned by the last test here.
"""
import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

#: dependencies that are legitimately unavailable in this checkout; each skip
#: must NAME what is missing so a reader knows what to restore.
DECLARED_UNAVAILABLE = {
    "test_week36_final_submission.py": "WEEK36",
    "test_hpc_numfreq_import.py": "unavailable",
}


def _read(path: Path) -> str:
    """Decode tolerating a BOM.

    Measured: some test files carry U+FEFF and ``read_text(encoding="utf-8")``
    keeps it, so ``ast.parse`` raises on a perfectly valid file.
    """
    return path.read_text(encoding="utf-8-sig")


def _test_files():
    return sorted(TESTS.glob("test_*.py"))


def _skip_calls(path: Path):
    """Every ``pytest.skip(...)`` / ``pytest.mark.skipif(...)`` call, via AST."""
    tree = ast.parse(_read(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        fn = node.func
        base = fn.value
        if fn.attr == "skip" and isinstance(base, ast.Name) and base.id == "pytest":
            found.append(("skip", node))
        elif fn.attr == "skipif":
            found.append(("skipif", node))
    return found


def test_every_pytest_skip_carries_a_reason():
    offenders = []
    for path in _test_files():
        for name, node in _skip_calls(path):
            if name != "skip":
                continue
            if not node.args:
                offenders.append((path.name, node.lineno, "no argument"))
            elif isinstance(node.args[0], ast.Constant) and not node.args[0].value:
                offenders.append((path.name, node.lineno, "empty reason"))
    assert not offenders, offenders


def test_every_pytest_skipif_carries_a_condition():
    """A reasonless ``skipif`` still prints its condition under ``-rs``; an empty
    one would print nothing at all."""
    offenders = []
    for path in _test_files():
        for name, node in _skip_calls(path):
            if name == "skipif" and not node.args:
                offenders.append((path.name, node.lineno, "no condition"))
    assert not offenders, offenders


def test_the_declared_unavailable_dependencies_name_what_is_missing():
    for filename, token in DECLARED_UNAVAILABLE.items():
        calls = _skip_calls(TESTS / filename)
        assert calls, filename
        rendered = [ast.unparse(node) for _n, node in calls]
        assert any(token in r for r in rendered), (filename, rendered)


def test_the_module_level_skip_is_found_by_the_ast_walk():
    """The week36 form (module-level ``pytestmark``) must not stay invisible."""
    calls = _skip_calls(TESTS / "test_week36_final_submission.py")
    assert calls, "the module-level skipif must be detected"
    assert any("WEEK36" in ast.unparse(node) for _n, node in calls)


def test_the_suite_is_parseable_so_the_guards_are_sound():
    for path in _test_files():
        ast.parse(_read(path))


def test_this_guard_does_not_walk_source_text():
    """Pin the lesson: a source-text regex matches its own documentation.

    NOTE: ``assert "re.finditer" not in src`` is itself self-matching -- the
    assertion's own source contains the token (measured: this test failed on
    itself).  Ask the AST whether such a call EXISTS, instead of searching text.
    """
    tree = ast.parse(_read(Path(__file__)))
    bad = [ast.unparse(node) for node in ast.walk(tree)
           if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
           and node.func.attr == "finditer"]
    assert not bad, bad
    # and no `import re` at all: the guard must not need it
    imports = [ast.unparse(node) for node in ast.walk(tree)
               if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert not any("re" == getattr(n, "name", None)
                   for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for n in node.names), imports