"""方案 5.3 / 11 靶向复核**结果层**的回归测试（只读，不跑任何电子结构计算）。

这些测试守的是「结果表与计划表、成本账本三者必须互相咬合」这件事：
* 结果只覆盖计划里 ready 的行，blocked 的行一条都不许有；
* 每条结果都是冻结的第二泛函、且带几何哈希；
* 派生 delta 必须能由登记能量独立重算出来；
* 成本账本的预算行一旦变成 measured，数值就必须等于结果条数。
"""

from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RECHECK = REPO_ROOT / "outputs" / "physics_completion" / "pair_evidence" / "targeted_recheck"
METHOD_SETTINGS = REPO_ROOT / "outputs" / "physics_completion" / "method_audit" / "method_settings.csv"
FLIP = REPO_ROOT / "outputs" / "physics_completion" / "closure" / "flip_persistence.csv"
LEDGER = REPO_ROOT / "outputs" / "physics_completion" / "cost" / "cost_ledger.csv"
HARTREE_TO_EV = 27.211386245988
ORCA_KEYWORD = {"PBE0-D4": "PBE0 D4", "omegaB97X-D4": "wB97X-D4"}


def _rows(path: Path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _results():
    return _rows(RECHECK / "recheck_results.csv")


def _gaps():
    return _rows(RECHECK / "recheck_pair_gaps.csv")


def test_results_cover_exactly_the_ready_rows_and_the_plan_stays_result_free():
    plan = _rows(RECHECK / "job_plan.csv")
    results = _results()
    ready = {row["record_id"] for row in plan if row["status"] == "ready"}
    blocked = {row["record_id"] for row in plan if row["status"] != "ready"}
    assert len(plan) == 24 and len(ready) == 12 and len(blocked) == 12
    assert {row["record_id"] for row in results} == ready
    assert not (blocked & {row["record_id"] for row in results})
    result_columns = [field for field in plan[0]
                      if any(token in field for token in ("ev", "energy", "sign", "delta", "flip"))]
    assert result_columns == []


def test_every_result_is_a_terminated_frozen_second_functional_single_point():
    settings = {row["setting_id"]: row for row in _rows(METHOD_SETTINGS)}
    results = _results()
    assert results
    for row in results:
        assert row["status"] == "computed"
        assert row["terminated"] == "true" and row["scf_converged"] == "true"
        assert row["functional"] == settings[row["setting_id"]]["functional"] == "PBE0-D4"
        assert row["basis"] == settings[row["setting_id"]]["basis"]
        assert row["orca_keyword"] == "%s %s" % (ORCA_KEYWORD[row["functional"]], row["basis"])
        assert len(row["geometry_sha256"]) == 64
        assert int(row["cores"]) == 2
        assert row["geometry_source"].startswith("work/wp2prod/")


def test_energy_ev_is_recomputed_from_the_registered_hartree():
    for row in _results():
        assert abs(float(row["energy_ev"]) - float(row["energy_eh"]) * HARTREE_TO_EV) < 1e-6


def test_derived_pair_gaps_are_recomputed_from_the_registered_energies():
    results = _results()
    gaps = _gaps()
    assert {(row["pair"], row["setting_id"]) for row in gaps} == {
        ("EMC | GBL", "S3"), ("EMC | GBL", "S4"), ("EMC | SL", "S3"), ("EMC | SL", "S4")}
    by_key = {(row["name"], row["state"], row["setting_id"]): row for row in results}
    for row in gaps:
        eox = {}
        for name in (row["i"], row["j"]):
            neutral = by_key[(name, "M", row["setting_id"])]
            cation = by_key[(name, "M_plus", row["setting_id"])]
            assert neutral["basis"] == cation["basis"]
            eox[name] = float(cation["energy_ev"]) - float(neutral["energy_ev"])
        delta = eox[row["i"]] - eox[row["j"]]
        assert row["status"] == "computed" and row["same_basis"] == "true"
        assert abs(float(row["eox_i_ev"]) - eox[row["i"]]) < 1e-6
        assert abs(float(row["eox_j_ev"]) - eox[row["j"]]) < 1e-6
        assert abs(float(row["delta_ev"]) - delta) < 1e-5
        assert row["sign"] == ("positive" if delta > 0 else "negative")


def test_gap_signs_are_reported_against_the_frozen_r1b_sign():
    frozen = {row["pair"]: row["sign"] for row in _rows(FLIP) if row["rung"] == "R1b"}
    assert set(frozen) == {"EMC | GBL", "EMC | SL"}
    for row in _gaps():
        expected = "true" if row["sign"] == frozen[row["pair"]] else "false"
        assert row["matches_frozen_r1b_sign"] == expected


def test_cost_ledger_keeps_the_preregistered_budget_and_adds_a_measured_row():
    results = _results()
    computed = [row for row in results if row["status"] == "computed"]
    core_hours = sum(float(row["core_hours"]) for row in computed)
    rows = {row["item"]: row for row in _rows(LEDGER)}
    preregistered = rows["targeted_pair_second_method_single_points"]
    assert preregistered["kind"] == "planned" and preregistered["status"] == "planned"
    assert preregistered["value"] == "16-32"
    measured = rows["targeted_pair_second_method_single_points_computed"]
    assert measured["kind"] == "measured" and measured["status"] == "measured"
    assert int(measured["value"]) == len(computed) == 12
    assert ("%.3f" % core_hours) in measured["note"]
