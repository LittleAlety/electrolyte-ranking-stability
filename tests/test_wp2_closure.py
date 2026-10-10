"""闭环层的契约测试：翻转阶梯只许报告它真的算过的层级。

钉住四条容易悄悄退化的性质：
1. 每对 pair 的阶梯恰好是 R1a/R1b/R2/R3/R4/R4_screen，没有重复行、没有多余行；
2. 「computed 必有值、未算必留空」——不许用外推的数字补 not_computed 的格子；
3. 方案第 2 步的三个问题只在两侧符号都存在时才给答案，缺一侧就是 None；
4. R2/R3 的两支腿必须同泛函 / 同基组 / 同 SMD / 同热化学处理（method_signature 纯函数）。
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_wp2_closure.py"
CLOSURE = REPO_ROOT / "outputs" / "physics_completion" / "closure"
FLIP = CLOSURE / "flip_persistence.csv"
INDEX = CLOSURE / "closure_index.json"
ACCEPTANCE = CLOSURE / "closure_acceptance.csv"
RUNGS = ("R1a", "R1b", "R2", "R3", "R4", "R4_screen")


def _module():
    spec = importlib.util.spec_from_file_location("wp2_closure_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(path: Path):
    if not path.is_file():
        pytest.skip("%s is not registered yet" % path.name)
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _index():
    if not INDEX.is_file():
        pytest.skip("the closure layer is not registered yet")
    return json.loads(INDEX.read_text(encoding="utf-8"))


def test_the_ladder_has_exactly_one_row_per_pair_and_rung():
    rows = _rows(FLIP)
    pairs = sorted({row["pair"] for row in rows})
    assert pairs, "the ladder must cover the two pairs"
    for pair in pairs:
        got = [row["rung"] for row in rows if row["pair"] == pair]
        assert sorted(got) == sorted(RUNGS), (pair, got)
        assert len(got) == len(set(got)), "duplicate rung rows for %s" % pair


def test_computed_rungs_carry_a_value_and_uncomputed_ones_stay_empty():
    for row in _rows(FLIP):
        filled = row["status"] in ("computed", "computed_screen_only")
        assert (row["delta_ev"] != "") == filled, row
        if filled:
            assert row["sign"] in ("positive", "negative"), row
        else:
            assert row["status"] == "not_computed" and row["sign"] == "" and row["delta_ev"] == "", row


def test_the_screen_rung_never_claims_the_production_label():
    screen = [row for row in _rows(FLIP) if row["rung"] == "R4_screen"]
    assert screen
    for row in screen:
        assert row["rung_kind"] == "screen_gfn2_ensemble"
        assert row["status"] != "computed"
        assert row["status"] in ("computed_screen_only", "not_computed")
        if row["status"] == "computed_screen_only":
            assert "NOT the production" in row["note"]


def test_the_three_plan_questions_are_only_answered_when_both_signs_exist():
    for item in _index()["ladder"]:
        signs = item["sign_by_rung"]
        if "R2" not in signs:
            assert item["fixed_geometry_to_solution_changes_the_sign"] is None, item["pair"]
            assert item["thermal_correction_changes_the_sign"] is None, item["pair"]
        if "R3" not in signs or not signs.get("R4"):
            assert item["sampling_changes_the_sign"] is None, item["pair"]
        if "R2" in signs and "R3" in signs:
            assert item["thermal_correction_changes_the_sign"] == (signs["R2"] != signs["R3"])


def test_method_signature_separates_functional_basis_solvent_and_thermochemistry():
    module = _module()
    base = {"level": "wB97X-D4 def2-TZVPD SMD(acetonitrile) Opt NumFreq", "basis": "def2-TZVPD",
            "qrrho": "true", "temp_k": "298.15", "pressure_atm": "1.0"}
    other_basis = dict(base, basis="def2-TZVP")
    other_functional = dict(base, level=base["level"].replace("wB97X-D4", "PBE0-D4"))
    other_solvent = dict(base, level=base["level"].replace("SMD(acetonitrile)", "SMD(water)"))
    other_thermo = dict(base, qrrho="false")
    assert module.method_signature(base) == module.method_signature(dict(base))
    for changed in (other_basis, other_functional, other_solvent, other_thermo):
        assert module.method_signature(changed) != module.method_signature(base)
    assert module.method_signature({}) == ("", "", "", "", "", "")


def test_the_method_consistency_gate_is_registered_and_green():
    rows = {row["check_id"]: row for row in _rows(ACCEPTANCE)}
    gate = rows["r2_r3_legs_share_functional_basis_solvent_and_thermochemistry"]
    assert gate["ok"] == "true", gate
    assert "compared=" in gate["detail"]
