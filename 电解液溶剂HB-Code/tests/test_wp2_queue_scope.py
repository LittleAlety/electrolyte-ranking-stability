"""队列覆盖范围与起点几何档位：两处最容易无声漂移、又都会让生产停摆的地方。

背景（2026-10-11 核实）：`run_wp2_queue.MOL_IDS` 曾写死四分子，20/20 跑完后队列永远
empty，监守与看护各自按「算完了」退出，生产静默停在 16/48 而无人报错。同时监守的
`$target` 与看护的 `$Target` 也各自写死 20，与队列口径是两个独立的数字。

这里钉住三件事：

* 队列覆盖范围恰好等于 `physics_completion_set.csv` 的 `in_main=true` 集合；
* 监守/看护取 target 的唯一入口（`supervisor_policy.queue_total`）与队列一致；
* 起点几何的**档位**被如实标出——DEC 全态与 PC 的 Li 态没有冻结 r2SCAN-3c 几何，
  只能降到 GFN2-xTB，账本必须照实写，不许把 xtb 起点冒充 r2SCAN-3c。
"""

from __future__ import annotations

import csv
import importlib.util
import sys
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

REPO_ROOT = Path(__file__).resolve().parents[1]
WP = REPO_ROOT / "scripts" / "wp_production"
SET_CSV = REPO_ROOT / "data" / "metadata" / "physics_completion_set.csv"


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", WP / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _main_set():
    with open(SET_CSV, encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["in_main"] == "true"]
    return {row["mol_id"] for row in rows}


def test_queue_covers_exactly_the_main_set():
    queue = _load("run_wp2_queue")
    assert set(queue.MOL_IDS) == _main_set()
    assert len(queue.MOL_IDS) == len(set(queue.MOL_IDS)), "队列里不得有重复分子"


def test_queue_total_and_computed_count_share_one_definition():
    policy = _load("supervisor_policy")
    queue = _load("run_wp2_queue")
    assert policy.queue_total() == len(queue.MOL_IDS) * len(queue.LEGS)


def test_every_leg_resolves_to_an_existing_geometry_with_a_declared_level():
    """60 条腿逐条解析起点：要么解析到已存在的文件，要么明确报缺失，不得静默给个不存在路径。"""
    production = _load("run_wp2_production")
    queue = _load("run_wp2_queue")
    levels = {}
    for mol_id in queue.MOL_IDS:
        name = queue.name_of(mol_id)
        for state, _owner in queue.LEGS:
            try:
                path, level = production.geometry_start_with_level(mol_id, name, state)
            except SystemExit:
                levels[(name, state)] = "MISSING"
                continue
            assert path.exists(), "%s %s 解析到不存在的路径 %s" % (name, state, path)
            assert level in production.GEOMETRY_LEVELS, level
            levels[(name, state)] = level

    # 起点档位是**如实登记**的：已知 DEC 全态与 PC 的 Li 态只能走 GFN2-xTB，其余走 r2SCAN-3c。
    # 若将来补齐了冻结几何，这里会失败——那时应当更新本断言，而不是放宽它。
    assert levels[("DEC", "M")] == "GFN2-xTB"
    assert levels[("PC", "LiM_plus")] == "GFN2-xTB"
    assert levels[("DMC", "M")] == "r2SCAN-3c"
    assert levels[("EC", "LiM_plus")] == "r2SCAN-3c"


def test_mtzvpd_and_m_share_one_starting_geometry():
    """中性腿的 def2-TZVPD 版本必须与中性 M 同一起点，否则两条腿不可相减。"""
    production = _load("run_wp2_production")
    extra = _load("run_wp2_extra")
    for mol_id in ("C01", "C03", "C05", "C17"):
        name = _load("run_wp2_queue").name_of(mol_id)
        assert extra.geometry_start_with_level(mol_id, name, "M_tzvpd") == \
            production.geometry_start_with_level(mol_id, name, "M")
