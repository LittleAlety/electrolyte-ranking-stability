"""系综层的契约测试：筛选层的每个数字都必须能对回已登记的池。

钉住五条容易悄悄退化的性质：
1. xTB 的虚频计数必须认复数措辞（"found 2 significant imaginary frequencies"），
   否则双虚频结构会被当成极小点混进系综；
2. 每一行都来自两个已登记池之一，几何 sha256 与登记值一致，不引入未登记几何；
3. 每条腿的 Boltzmann 权重和为 1，且两种口径满足数学界
   (-RT ln N <= G_state - G_min <= 0 <= G_avg - G_min)；
4. 带虚频的结构留在表里、带虚频数、被排除出系综，不是删掉；
5. 闭环表里的 R4_screen 是逐字读回本层产物，且只准标 computed_screen_only。
"""

from __future__ import annotations

import importlib.util
import io
import csv
import hashlib
import json
import math
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_wp2_ensemble_free_energies.py"
ENSEMBLES = REPO_ROOT / "outputs" / "physics_completion" / "ensembles"
INDEX = ENSEMBLES / "ensemble_index.json"
RECORDS = ENSEMBLES / "ensemble_raw_records.csv"
PER_STRUCTURE = ENSEMBLES / "ensemble_free_energies.csv"
PAIR_RUNGS = ENSEMBLES / "ensemble_pair_rungs.csv"
POOL = REPO_ROOT / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"
SAMPLING_SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_wp2_sampling.py"
SAMPLING_DIR = REPO_ROOT / "outputs" / "physics_completion" / "sampling"
SAMPLING_INDEX = SAMPLING_DIR / "sampling_index.json"
SAMPLING_ROUND1 = SAMPLING_DIR / "sampling_round1.csv"
SAMPLING_ESCALATION = SAMPLING_DIR / "sampling_escalation.csv"
COMPLETION_SET = REPO_ROOT / "data" / "metadata" / "physics_completion_set.csv"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
FREE_STATES = ("M", "M_plus")
LI_SCREEN = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
FLIP = REPO_ROOT / "outputs" / "physics_completion" / "closure" / "flip_persistence.csv"
KJ_PER_EV = 96.48533212331002
KJ_PER_EH = 2625.499638


def _module():
    spec = importlib.util.spec_from_file_location("wp2_ensemble_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(path: Path):
    if not path.is_file():
        pytest.skip("%s is not registered yet" % path.name)
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _payload():
    if not INDEX.is_file():
        pytest.skip("the ensemble layer is not registered yet")
    return json.loads(INDEX.read_text(encoding="utf-8"))


def test_parse_enso_counts_the_plural_wording_too():
    """回归：复数措辞曾经漏检，把双虚频结构变成 counted_in_ensemble=true。"""
    module = _module()
    plural = "found            2  significant imaginary frequencies\n"
    singular = "found            1  significant imaginary frequency\n"
    assert module.parse_enso(plural)["n_imaginary"] == 2
    assert module.parse_enso(singular)["n_imaginary"] == 1
    assert module.parse_enso("")["n_imaginary"] == 0
    header = "          :  # imaginary freq.                       3 \n"
    assert module.parse_enso(header)["n_imaginary"] == 3
    assert module.parse_enso(header + plural)["n_imaginary"] == 3


def test_every_row_comes_from_one_of_the_two_registered_pools():
    if not (Path(__file__).resolve().parents[1] / "work" / "wp2prod").is_dir():
        pytest.skip(
            "the machine-local work/ layer (gitignored) is absent in this checkout; "
            "this test pins the dev-tree figure, the refusal side is covered by "
            "the sibling clean-clone tests",
        )
    rows = _rows(PER_STRUCTURE)
    pool = {(row["mol_id"] + "|" + row["state"], row["geometry_relpath"]): row["geometry_sha256"]
            for row in _rows(POOL)}
    screen = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
    motifs = {}
    for entry in screen["legs"]:
        for order, motif in enumerate(entry["kept"], start=1):
            motifs[(entry["record_id"], str(order))] = motif["motif_path"]
    assert rows, "the ensemble layer must cover registered structures"
    for row in rows:
        geometry = REPO_ROOT / row["geometry_relpath"]
        assert geometry.is_file(), row["geometry_relpath"]
        digest = hashlib.sha256(geometry.read_bytes()).hexdigest()
        assert digest == row["geometry_sha256"], row["leg_id"]
        if row["source"] == "free_state_conformer_pool":
            key = (row["leg_id"], row["geometry_relpath"])
            assert key in pool, row["leg_id"]
            assert pool[key] == row["geometry_sha256"], row["leg_id"]
        elif row["source"] == "li_motif_screen":
            assert motifs.get((row["leg_id"], row["rank"])) == row["geometry_relpath"]
        else:
            raise AssertionError("unknown pool: %s" % row["source"])


def test_boltzmann_weights_sum_to_one_and_the_two_conventions_obey_their_bounds():
    payload = _payload()
    rows = _rows(PER_STRUCTURE)
    rt = payload["rt_kj_per_mol"]
    for leg in payload["legs"]:
        counted = [row for row in rows if row["leg_id"] == leg["leg_id"]
                   and row["counted_in_ensemble"] == "true"]
        assert len(counted) == leg["n_counted"]
        if not counted:
            assert leg["g_state_eh"] is None and leg["g_avg_eh"] is None
            continue
        total = sum(float(row["boltzmann_weight"]) for row in counted)
        # 权重按 "%.6f" 发布，每项舍入误差 <= 5e-7；n 项累加的上界就是 n*5e-7。
        # 用舍入预算而不是固定 1e-6：它随结构数自适应，池子变大不会误报，也不会放过真错误。
        assert abs(total - 1.0) <= len(counted) * 5e-7 + 1e-9, leg["leg_id"]
        lowest = min(float(row["total_free_energy_eh"]) for row in counted)
        assert abs(leg["g_lowest_eh"] - lowest) < 1e-8, "the CSV rounds G to 8 decimals"
        assert -rt * math.log(len(counted)) - 1e-6 <= leg["entropy_shift_kj"] <= 1e-9
        assert -1e-9 <= leg["avg_shift_kj"]
        assert leg["g_state_eh"] <= leg["g_lowest_eh"] + 1e-8
        assert leg["g_avg_eh"] >= leg["g_lowest_eh"] - 1e-8


def test_imaginary_structures_are_kept_in_the_table_and_never_counted():
    rows = _rows(PER_STRUCTURE)
    assert rows
    for row in rows:
        if row["n_imaginary"] not in ("", "0"):
            assert int(row["n_imaginary"]) >= 1
            assert row["counted_in_ensemble"] == "false", row["leg_id"]
            assert row["note"], row["leg_id"]
            assert row["boltzmann_weight"] == "", row["leg_id"]
        else:
            assert row["counted_in_ensemble"] in ("true", "false")
    records = _rows(RECORDS)
    assert len(records) == len(rows), "published GFN2 records must cover every registered structure"
    for record in records:
        if record["status"] == "ok":
            assert math.isfinite(float(record["total_free_energy_eh"]))
            assert record["n_imaginary"] != ""


def test_leg_summaries_agree_with_their_own_leg_id():
    payload = _payload()
    assert payload["legs"]
    for leg in payload["legs"]:
        assert leg["leg_id"] == "%s|%s" % (leg["mol_id"], leg["state"]), leg["leg_id"]


def test_pair_rows_never_mix_stoichiometries_and_their_deltas_recompute():
    payload = _payload()
    rows = _rows(PAIR_RUNGS)
    assert rows
    for row in rows:
        assert "|" in row["left_leg"] and "|" in row["right_leg"]
        if row["delta_kj_left_minus_right"]:
            expected = (float(row["left_value_eh"]) - float(row["right_value_eh"])) * KJ_PER_EH
            assert abs(float(row["delta_kj_left_minus_right"]) - expected) < 1e-3, row["pair_id"]
    for agreement in payload["pair_state_agreement"]:
        assert agreement["left_molecule"] != agreement["right_molecule"]
        assert agreement["levels_compared"] == ["E_min", "G_min", "G_state", "G_avg"]


def test_closure_screen_rung_is_read_back_from_this_layer():
    payload = _payload()
    flip = _rows(FLIP)
    screen_rows = [row for row in flip if row["rung"] == "R4_screen"]
    assert screen_rows, "closure must carry the screen-level rung explicitly"
    for row in screen_rows:
        assert row["status"] in ("computed_screen_only", "not_computed")
        assert row["status"] != "computed", "the screen rung must never claim the production label"
        if row["status"] != "computed_screen_only":
            continue
        gap = next(item for item in payload["pair_state_agreement"]
                   if item["left_molecule"] == row["i"] and item["right_molecule"] == row["j"])
        headline = gap["free_ionisation_gap_kj"]["G_state"]
        assert abs(float(row["delta_ev"]) - headline / KJ_PER_EV) < 5e-7, row["pair"]
        assert "NOT the production" in row["note"]


def test_the_two_source_pools_are_registered_by_hash():
    payload = _payload()
    sources = payload["sources"]
    for key, path in (("free_state_conformer_pool", POOL), ("li_motif_screen", LI_SCREEN)):
        assert sources[key].endswith(path.name)
        assert sources[key + "_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 自由态构象池的覆盖契约（方案 §3.1 主集 12 分子）
# ---------------------------------------------------------------------------

def _sampling_module():
    spec = importlib.util.spec_from_file_location("wp2_sampling_under_test", SAMPLING_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _completion_rows():
    with io.open(COMPLETION_SET, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _core_smiles():
    with io.open(CORE_SET, encoding="utf-8", newline="") as handle:
        return {row["mol_id"]: row["smiles"] for row in csv.DictReader(handle)}


def _sampling_payload():
    if not SAMPLING_INDEX.is_file():
        pytest.skip("the sampling layer is not registered yet")
    return json.loads(SAMPLING_INDEX.read_text(encoding="utf-8"))


def test_free_state_pool_covers_every_main_cohort_molecule():
    """方案 §3.1 主集 12 分子的自由态（M / M_plus）都要进池子，一个不少也不许多。"""
    module = _sampling_module()
    expected = sorted((row["mol_id"], row["name"]) for row in _completion_rows()
                      if row.get("cohort") == "main")
    got = sorted((mol_id, name) for mol_id, name, _smiles in module.MOLS)
    assert len(expected) == 12, "the main cohort is registered as 12 molecules"
    assert got == expected, "MOLS must be exactly the registered main cohort"
    assert len({mol_id for mol_id, _name, _smiles in module.MOLS}) == len(module.MOLS)


def test_free_state_pool_smiles_are_copied_from_the_registered_core_set():
    """SMILES 逐字来自 core_set.csv：不许臆造，也不许用等价但不同的写法顶替。"""
    module = _sampling_module()
    registered = _core_smiles()
    for mol_id, name, smiles in module.MOLS:
        assert mol_id in registered, "unregistered molecule id: %s" % mol_id
        assert smiles == registered[mol_id], ("%s (%s) SMILES is not the registered one"
                                              % (name, mol_id))


def test_free_state_pool_keeps_the_registered_screen_discipline():
    """扩覆盖不许放松既有纪律：KEEP / 去重容差 / 升级容差 / 两态定义都不变。"""
    module = _sampling_module()
    assert module.KEEP == 3
    assert module.DUP_TOL_KCAL == 0.10
    assert module.ESCALATE_TOL_KCAL == 1.00
    assert module.MAX_POOL == 6
    assert module.ROUND1_STATES == [("M", 0, 0), ("M_plus", 1, 1)]
    assert "GFN2" in module.LEVEL and "gas phase" in module.LEVEL


def _prod_module(filename):
    """Load a ``scripts/wp_production`` module by filename (they are stdlib-light)."""
    import sys as _sys
    _sys.dont_write_bytecode = True
    path = REPO_ROOT / "scripts" / "wp_production" / filename
    spec = importlib.util.spec_from_file_location("frozen_window_" + filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: Every module that restates the frozen screening window.
WINDOW_MODULES = (
    "build_production_ensemble_manifest.py",
    "build_gap_decision_support.py",
    "build_sampling_audit_3to6.py",
)


def test_the_frozen_six_kcal_window_is_identical_in_every_module_that_restates_it():
    """The window decides which screened basins may become production candidates.

    Measured 2026-10-24: ``WINDOW_KCAL = 6.0`` lived in THREE independent modules
    and NOTHING under ``tests/`` referenced ``WINDOW_KCAL``, ``ENERGY_WINDOW_KJ``,
    ``window_kcal`` or "6 kcal" -- so editing one copy alone would silently change
    which basins are admitted, with no failing test.  (Contrast ``DUP_TOL_KCAL`` /
    ``ESCALATE_TOL_KCAL``, which the test above already pins.)
    """
    values = {}
    for filename in WINDOW_MODULES:
        values[filename] = _prod_module(filename).WINDOW_KCAL
    assert set(values.values()) == {6.0}, values
    manifest = _prod_module(WINDOW_MODULES[0])
    assert manifest.WINDOW_KJ == pytest.approx(manifest.WINDOW_KCAL * manifest.KJ_PER_KCAL)


def test_the_li_motif_kj_window_is_never_looser_than_the_frozen_kcal_window():
    """A second representation of the same window exists, expressed in kJ.

    ``screen_li_motifs.ENERGY_WINDOW_KJ = 25.0`` kJ = 5.975 kcal/mol, i.e. slightly
    TIGHTER than 6.0 kcal/mol (6 kcal = 25.104 kJ).  Pinning the relation, not only
    the number, records that difference instead of hiding it: an edit that let the
    kJ window reach past 6 kcal/mol fails here first.
    """
    module = _prod_module("screen_li_motifs.py")
    assert module.ENERGY_WINDOW_KJ == pytest.approx(25.0)
    assert module.ENERGY_WINDOW_KJ / 4.184 <= 6.0 + 1e-12


def test_designated_sampling_set_is_still_the_section_3_3_cohort():
    """方案 §3.3 的采样审计集是 C02/C03/C08/C17；扩覆盖不等于改写指定集。"""
    payload = _sampling_payload()
    cohort = sorted(row["mol_id"] for row in _completion_rows()
                    if row.get("cohort") == "sampling_audit")
    assert cohort == ["C02", "C03", "C08", "C17"]
    assert sorted(payload["cohort_deviation"]["registered_set"]["mol_ids"]) == cohort


def test_executed_set_is_read_back_from_the_rows_that_actually_ran():
    """「执行集」= 真正跑出结果的分子；不许把「声明覆盖 12 个」写成「12 个都跑了」。"""
    payload = _sampling_payload()
    rows = _rows(SAMPLING_ROUND1)
    assert rows, "sampling_round1.csv must be registered"
    ran = sorted({row["mol_id"] for row in rows if row["verdict"] != "not_computed"})
    registered = sorted(payload["cohort_deviation"]["executed_set"]["mol_ids"])
    assert registered == ran, ("cohort_deviation.executed_set must be the molecules with a real "
                               "verdict, not the declared coverage")


def test_the_deviation_between_designated_and_executed_is_stated_not_hidden():
    """偏差必须写在产物里：未执行的指定分子要读得出来，且不许宣称完成 §3.3。"""
    payload = _sampling_payload()
    dev = payload["cohort_deviation"]
    designated = set(dev["registered_set"]["mol_ids"])
    executed = set(dev["executed_set"]["mol_ids"])
    text = json.dumps(dev, ensure_ascii=False)
    assert "3.3" in text, "the deviation note must name the section it does not claim"
    names = {row["mol_id"]: row["name"] for row in _completion_rows()}
    for mol_id in sorted(designated - executed):
        assert mol_id in text or names[mol_id] in text, (
            "%s is designated but not executed; the deviation must say so" % mol_id)
