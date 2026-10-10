"""契约测试：方案合规台账必须由产物现算，不能写死。

台账是「都做完没有」的唯一机器可查答案。若有人把状态或数字写死进
`build_plan_compliance.py`，下面这些断言会在任何一条生产腿落地后立刻失败。
"""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_plan_compliance.py"
CSV_PATH = REPO_ROOT / "outputs" / "physics_completion" / "compliance" / "plan_compliance.csv"

STATUSES = {"satisfied", "partial", "not_satisfied", "blocked_on_production"}


def _module():
    spec = importlib.util.spec_from_file_location("build_plan_compliance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows():
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_table_covers_every_plan_work_package() -> None:
    rows = _rows()
    assert rows, "compliance table is empty"
    sections = " ".join(r["plan_section"] for r in rows)
    for wp in ("WP0", "WP1", "WP2", "WP3", "WP4", "WP5", "WP6"):
        assert wp in sections, "compliance table never mentions %s" % wp


def test_statuses_come_from_the_frozen_vocabulary() -> None:
    for row in _rows():
        assert row["status"] in STATUSES, row
        assert row["item_id"] and row["requirement"] and row["evidence"], row


def test_wp2_counts_are_read_back_from_the_closure_table() -> None:
    """写死就会在任一腿落地后失败：这里用闭环表现算的同一口径比对台账。"""
    module = _module()
    states = module.read_rows("outputs/physics_completion/closure/four_molecule_state_closure.csv")
    produced = [r for r in states if r.get("register_status") == module.PRODUCED]
    row = next(r for r in _rows() if r["item_id"] == "wp2_production_state_ledger")
    assert "produced=%d total=%d" % (len(produced), len(states)) in row["measured"], row["measured"]


def test_overall_row_derives_from_the_live_ledgers() -> None:
    rows = _rows()
    overall = next(r for r in rows if r["item_id"] == "plan_overall_complete")
    main4 = next(r for r in rows if r["item_id"] == "wp2_four_state_complete")
    flip = next(r for r in rows if r["item_id"] == "wp2_flip_persistence")
    assert "flip_rungs=" in overall["measured"]
    assert "M/M+/LiM+/LiM2+=" in main4["measured"]
    assert "rungs_computed=" in flip["measured"]
    assert overall["status"] in STATUSES


def test_table_covers_the_sample_and_landing_sections() -> None:
    """§3（12 主集/8 方法集/4 采样集）与 §13（推荐落点）也必须有条目，不能只覆盖 WP0-WP6。"""
    sections = " ".join(r["plan_section"] for r in _rows())
    assert "\u00a73" in sections, "\u00a73 designated-set row missing"
    assert "\u00a713" in sections, "\u00a713 landing-path row missing"


def test_items_with_open_gaps_are_never_marked_satisfied() -> None:
    """登记完整 != 工作完成：下面三条只要有未闭合的缺口，就不许写成 satisfied。"""
    rows = {r["item_id"]: r for r in _rows()}

    method = rows["wp1_unique_production_method"]
    if "freeze_artifact=False" in method["measured"] or "production_settings=2" in method["measured"]:
        assert method["status"] == "partial", method

    sampling = rows["wp2_sampling_extension"]
    if sampling["status"] == "satisfied":
        assert "escalation_pending=0/" in sampling["measured"], sampling

    ligand = rows["wp6_explicit_ligand"]
    if "executed_jobs=0" in ligand["measured"]:
        assert ligand["status"] != "satisfied", ligand
