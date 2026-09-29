"""Stage 7 feature-table tests: cost levels, manifest agreement, no overlap."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import build_ml_features as bmf  # noqa: E402

WEEK7 = REPO_ROOT / "outputs" / "week7"


def _manifest():
    with io.open(WEEK7 / "feature_manifest.json", encoding="utf-8") as handle:
        return json.load(handle)


def test_cost_levels_are_disjoint():
    x0, x1, x2 = set(bmf.X0_COLUMNS), set(bmf.X1_COLUMNS), set(bmf.X2_COLUMNS)
    assert not x0 & x1
    assert not x0 & x2
    assert not x1 & x2
    assert len(x0) + len(x1) + len(x2) == len(x0 | x1 | x2)


def test_manifest_matches_module_constants():
    payload = _manifest()
    levels = payload["feature_cost_levels"]
    assert tuple(levels["X0"]) == tuple(bmf.X0_COLUMNS)
    assert tuple(levels["X1"]) == tuple(bmf.X1_COLUMNS)
    assert tuple(levels["X2"]) == tuple(bmf.X2_COLUMNS)
    assert set(payload["tasks"]) == set(bmf.TASKS)


def test_no_feature_set_contains_an_x2_column():
    payload = _manifest()
    x2 = set(payload["feature_cost_levels"]["X2"])
    for task, spec in payload["tasks"].items():
        for name, features in spec["feature_sets"].items():
            assert not x2.intersection(features), (task, name)


def test_core_table_carries_every_declared_column():
    with io.open(WEEK7 / "features_core.csv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    header = set(rows[0])
    for column in bmf.CORE_COLUMNS:
        assert column in header
    assert len(rows) == payload_count("core")


def test_broad_table_is_x0_only():
    with io.open(WEEK7 / "features_broad.csv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    header = set(rows[0])
    assert set(bmf.BROAD_COLUMNS) == header
    assert not set(bmf.X1_COLUMNS) & header
    assert not set(bmf.X2_COLUMNS) & header
    assert len(rows) == payload_count("broad")


def payload_count(kind):
    payload = _manifest()
    counts = payload["counts"]
    return counts["core_n"] if kind == "core" else counts["broad_n"]


def test_group_key_follows_prereg_recipe():
    assert bmf.group_key("ester", "") == "ester|linear|H"
    assert bmf.group_key("ester", "cyclic") == "ester|cyclic|H"
    assert bmf.group_key("cyclic_carbonate", "cyclic|fluorinated") == "cyclic_carbonate|cyclic|F"