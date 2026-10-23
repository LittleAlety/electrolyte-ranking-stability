"""Step 11: significance at the frozen tolerance is allowed; CONVERGENCE is not.

The user's rulings, in order:

* 2026-10-19: report differences only, do not judge sampling convergence;
* 2026-10-21: the tolerance is frozen at **0.10 kcal/mol** on basis B, and the
  freeze was declared BEFORE the new batch was evaluated ("未由观测差异倒推"),
  so new batches may be judged significant / not significant at 0.10;
* current objective: "未独立冻结容差前，不宣称采样收敛。**已看过结果后的容差修订
  必须披露**".

Two different statements are being kept apart, and these tests pin the
separation:

* **significance** (|Δ| > tolerance) is a permitted conclusion now;
* **convergence** (the search has found everything) must still NOT be claimed,
  and every artifact that reports differences must say so.

Also pinned: the frozen number must not drift silently between the code constant
and the declared artifact.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SAMPLING = REPO / "outputs" / "physics_completion" / "sampling"
TOLERANCE = SAMPLING / "tolerance_preregistration_draft.md"

#: artifacts that report 3->6 differences and must therefore carry the disclaimer
DIFFERENCE_ARTIFACTS = (
    SAMPLING / "sampling_3to6_diff.md",
    SAMPLING / "sampling_audit_3to6.md",
    SAMPLING / "sampling_ceiling_classification.md",
)

#: a positive convergence claim -- the thing that must never appear
CONVERGENCE_CLAIM = re.compile(
    r"(采样|sampling)[^。\n]{0,12}(已收敛|已经收敛|收敛已达成|已确认收敛)")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_tolerance_is_declared_frozen_with_its_basis():
    text = _text(TOLERANCE)
    assert "已冻结" in text
    assert "0.10 kcal/mol" in text
    assert "依据 B" in text


def test_the_freeze_is_declared_to_precede_the_new_batch():
    """A post-hoc tolerance would be reverse-engineered from the result."""
    text = _text(TOLERANCE)
    assert "未由观测差异倒推" in text or "先冻结" in text


def test_no_difference_artifact_claims_convergence():
    for path in DIFFERENCE_ARTIFACTS:
        assert path.is_file(), path
        text = _text(path)
        assert not CONVERGENCE_CLAIM.search(text), path.name


def test_every_difference_artifact_states_that_it_does_not_judge_convergence():
    for path in DIFFERENCE_ARTIFACTS:
        text = _text(path)
        assert "收敛" in text, path.name
        negated = ("不判" in text or "不给出" in text or "不是" in text
                   or "非收敛判定" in text)
        assert negated, path.name


def test_the_frozen_number_does_not_drift_between_code_and_artifact():
    spec = importlib.util.spec_from_file_location(
        "tol", REPO / "scripts" / "wp_production" / "build_tolerance_preregistration.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "scripts" / "wp_production"))
    spec.loader.exec_module(m)
    assert m.FROZEN_TOLERANCE_KCAL == pytest.approx(0.10), m.FROZEN_TOLERANCE_KCAL
    assert "0.10" in _text(TOLERANCE)


def test_the_gfn2_one_kcal_threshold_is_not_the_production_tolerance():
    """The screening threshold must never be presented as the production one.

    NOTE: a plain ``"1 kcal" in text`` check is WRONG -- ``"0.1 kcal/mol"``
    contains it (measured: the first version of this test failed on a correct
    artifact for exactly that reason).  Use a boundary-anchored pattern.
    """
    screening = re.compile(r"(?<![\d.])1(?:\.00)? kcal")
    text = _text(TOLERANCE)
    for match in screening.finditer(text):
        window = text[max(0, match.start() - 40):match.end() + 20]
        assert "筛选" in window, window
    for path in DIFFERENCE_ARTIFACTS:
        body = _text(path)
        for match in screening.finditer(body):
            window = body[max(0, match.start() - 40):match.end() + 20]
            assert "筛选" in window, (path.name, window)