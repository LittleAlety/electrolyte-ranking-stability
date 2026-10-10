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
        assert abs(total - 1.0) < 1e-6, leg["leg_id"]
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
