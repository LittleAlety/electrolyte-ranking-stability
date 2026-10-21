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
        if row["status"] in ("limited", "provisional"):
            # v1.4.2 fourth state: a bounded-coverage R4 value (limited) or an
            # unfinished pool (provisional).  Either way the rung may carry a
            # number so the coverage gap stays visible, and it must say
            # explicitly that it is NOT counted as computed.
            assert row["delta_ev"] != "", row
            assert "NOT counted as computed" in row["note"], row
            continue
        filled = row["status"] in ("computed", "computed_screen_only")
        assert (row["delta_ev"] != "") == filled, row
        if filled:
            assert row["sign"] in ("positive", "negative"), row
        else:
            assert row["status"] == "not_computed" and row["sign"] == "" and row["delta_ev"] == "", row


def test_r4_row_splits_on_every_legs_acceptance_status():
    """The final-label rebuild: limited / provisional / absent legs never yield computed.

    r4_row must check BOTH states (M_plus AND M) of BOTH molecules -- a limited
    neutral leg is as blocking as a limited cation leg -- and must carry the
    blocked leg's own limitation_reason verbatim instead of a generic phrase.
    """
    module = _module()

    def label(status="accepted", reason="", eh="-1.0", n="2"):
        return {"acceptance_status": status, "limitation_reason": reason,
                "g_ensemble_eh": eh, "n_unique": n}

    both_accepted = {
        ("A", "M_plus"): label(), ("A", "M"): label(eh="-2.0"),
        ("B", "M_plus"): label(eh="-1.5"), ("B", "M"): label(eh="-2.5"),
    }

    def with_leg(base, key, **overrides):
        clone = dict(base)
        clone[key] = label(**{**{"status": "accepted", "reason": "", "eh": "-1.0", "n": "2"},
                              **overrides})
        return clone

    row = module.r4_row("A | B", "A", "B", both_accepted)
    assert row["status"] == "computed", row
    assert row["delta_ev"] != "" and row["sign"] in ("positive", "negative")

    limited_cation = with_leg(both_accepted, ("A", "M_plus"),
                              status="limited", reason="species_drift_unrecoverable")
    row = module.r4_row("A | B", "A", "B", limited_cation)
    assert row["status"] == "limited", row
    assert "species_drift_unrecoverable" in row["note"], row
    assert "NOT counted as computed" in row["note"], row

    limited_neutral = with_leg(both_accepted, ("B", "M"),
                               status="limited", reason="rescue_budget_exhausted", eh="-2.5")
    row = module.r4_row("A | B", "A", "B", limited_neutral)
    assert row["status"] == "limited", row
    assert "B|M" in row["note"], row  # the blocked LEG is named, not just a molecule
    assert "rescue_budget_exhausted" in row["note"], row

    provisional_cation = with_leg(both_accepted, ("B", "M_plus"),
                                  status="provisional", eh="-1.5")
    row = module.r4_row("A | B", "A", "B", provisional_cation)
    assert row["status"] == "provisional", row
    assert "NOT counted as computed" in row["note"], row

    missing_leg = dict(both_accepted)
    missing_leg[("A", "M")] = {}
    row = module.r4_row("A | B", "A", "B", missing_leg)
    assert row["status"] == "not_computed", row
    assert row["delta_ev"] == "" and row["sign"] == "", row
    assert "A|M" in row["note"], row


def test_r4_status_on_disk_matches_the_final_labels():
    """Every on-disk R4 row must agree with the acceptance labels it cites.

    This is the regression for the 2026-10-20 rebuild: the two R4 rungs are
    limited because EMC|M_plus is limited (species_drift_unrecoverable) -- the
    old note claimed 'rescue budget exhausted' for every limited rung, which is
    the wrong cause for this leg.
    """
    module = _module()
    labels = module.load_production_ensemble()
    rows = [row for row in _rows(FLIP) if row["rung"] == "R4"]
    assert rows, "the production R4 rung must be present"
    for row in rows:
        rebuilt = module.r4_row(row["pair"], row["i"], row["j"], labels)
        assert rebuilt["status"] == row["status"], (row, rebuilt)
        assert rebuilt["delta_ev"] == row["delta_ev"], (row, rebuilt)
        assert rebuilt["note"] == row["note"], (row, rebuilt)


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


REPORT = CLOSURE / "wp3_rung_rebuild_report.md"


def test_rung_rebuild_report_is_registered_and_honest():
    """The rebuild report: 12 rung cells, the gap attribution, the Top-3 bound verdict.

    The report never declares convergence and it counts limited/provisional
    legs as non-computed -- the numbers below are recomputed from the frozen
    labels inside the test, not copied from the report prose.
    """
    if not REPORT.is_file():
        pytest.skip("the rebuild report is not registered yet")
    text = REPORT.read_text(encoding="utf-8")
    # 1. all twelve rung cells appear with their status
    rows = _rows(FLIP)
    assert len(rows) == 12
    for row in rows:
        assert row["rung"] in text, row["rung"]
        assert row["status"] in text
    # 2. every non-computed rung names the blocking leg's own reason
    for row in rows:
        if row["status"] == "limited":
            assert "species_drift_unrecoverable" in text, "EMC|M_plus blocks both R4 rungs"
    # 3. the Top-3 verdict matches an independent recomputation from the labels
    module = _module()
    labels = module.load_production_ensemble()
    kcal_per_ev = 96.48533212331002 / 4.184
    ranked = []
    for name in sorted({key[0] for key in labels}):
        m_plus, m = labels.get((name, "M_plus")), labels.get((name, "M"))
        if not m_plus or not m or m_plus["acceptance_status"] != "accepted" \
                or m["acceptance_status"] != "accepted":
            continue
        ranked.append((name, (float(m_plus["g_ensemble_eh"]) - float(m["g_ensemble_eh"]))
                      * module.EH_PER_EV))
    ranked.sort(key=lambda item: -item[1])
    assert len(ranked) >= 3, "the accepted-only ranking needs at least 3 molecules"
    top3 = [name for name, _ in ranked[:3]]
    assert " > ".join(top3) in text, top3
    # 4. the bound verdict: a contender whose interval crosses the accepted floor
    floor = ranked[2][1]
    crosses = []
    for name in sorted({key[0] for key in labels}):
        m_plus, m = labels.get((name, "M_plus")), labels.get((name, "M"))
        if not m_plus or not m:
            continue
        if (m_plus["acceptance_status"], m["acceptance_status"]) == ("accepted", "accepted"):
            continue
        gap = (float(m_plus["g_ensemble_eh"]) - float(m["g_ensemble_eh"])) * module.EH_PER_EV
        b_plus = float(m_plus.get("lowering_bound_rt_ln_n_kcal") or 0) / kcal_per_ev
        b_m = float(m.get("lowering_bound_rt_ln_n_kcal") or 0) / kcal_per_ev
        if gap + b_m > floor:
            crosses.append(name)
    if crosses:
        assert "Top-3 未被 bound 覆盖" in text, crosses
    else:
        assert "Top-3 被 bound 覆盖" in text
    # 5. the report never claims convergence
    assert "不判排序收敛" in text
