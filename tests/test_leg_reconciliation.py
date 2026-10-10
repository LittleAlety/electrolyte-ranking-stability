"""四分子 20 条腿的现场核对（provenance 层）：登记与磁盘事实必须能对上。

方案第 1 步的提交前纪律是「先核对本地正在运行及已完成但未入库的作业，避免重复计算」。
把该纪律钉成可复核的四件事：

* 20 条腿逐条登记一次，不重不漏；
* 磁盘上已有 ORCA 正常结束输出、清单里却没有 computed 作业行 => duplicate_work_risk，
  这是本表唯一的告警；
* 在跑 / 失败 / 未开始的腿不是「合格」，也不冒充数字；
* 交付出的 leg_reconciliation.csv 里 classification=computed 的集合与
  production_ledger.csv 完全一致。
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "build_compute_provenance.py"
RECON = REPO_ROOT / "outputs" / "physics_completion" / "provenance" / "leg_reconciliation.csv"
LEDGER = REPO_ROOT / "outputs" / "physics_completion" / "free_states" / "production_ledger.csv"


def _load():
    spec = importlib.util.spec_from_file_location("build_compute_provenance_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _manifest_row(name, state, job_state):
    return {"job_id": "wp2prod/%s/%s" % (name, state), "cohort": "wp2_production",
            "job_state": job_state, "terminated": "true" if job_state == "computed" else "false"}


def _leg(legs, leg_id):
    return next(row for row in legs if row["leg_id"] == leg_id)


def test_every_leg_is_classified_exactly_once(tmp_path):
    module = _load()
    legs = module.leg_reconciliation([], root=tmp_path)
    expected = ["%s|%s" % (name, state)
                for _mol_id, name in module.FOUR_MOLECULES
                for state in list(module.MAIN_STATES) + [module.EXTRA_STATE]]
    assert [row["leg_id"] for row in legs] == expected
    assert len({row["leg_id"] for row in legs}) == 20
    assert {row["classification"] for row in legs} == {"not_started"}
    assert all(row["raw_output_on_disk"] == "false" for row in legs)


def test_an_absent_leg_is_not_started_and_raises_no_duplicate_work_risk(tmp_path):
    module = _load()
    row = _leg(module.leg_reconciliation([], root=tmp_path), "DMC|M_tzvpd")
    assert row["classification"] == "not_started"
    assert row["manifest_job_id"] == "" and row["duplicate_work_risk"] == "false"


def test_a_finished_log_without_a_computed_row_is_the_only_duplicate_work_signal(tmp_path):
    module = _load()
    job = tmp_path / "DMC" / "M_tzvpd"
    job.mkdir(parents=True)
    (job / "DMC_M_tzvpd.inp").write_text("! wB97X-D4 def2-TZVPD SMD(acetonitrile) Opt NumFreq\n",
                                         encoding="utf-8")
    (job / "DMC_M_tzvpd.log").write_text("****ORCA TERMINATED NORMALLY****\n", encoding="utf-8")
    legs = module.leg_reconciliation([], root=tmp_path)
    flagged = _leg(legs, "DMC|M_tzvpd")
    assert flagged["classification"] == "unregistered_run_on_disk"
    assert flagged["log_terminated"] == "true" and flagged["duplicate_work_risk"] == "true"
    assert flagged["note"], "告警必须写清为什么重新排队等于重复计算"
    assert sum(1 for row in legs if row["duplicate_work_risk"] == "true") == 1


def test_an_in_flight_leg_is_not_a_duplicate_work_signal(tmp_path):
    module = _load()
    job = tmp_path / "GBL" / "LiM_plus"
    job.mkdir(parents=True)
    (job / "GBL_LiM_plus.inp").write_text("! wB97X-D4 def2-TZVPD\n", encoding="utf-8")
    legs = module.leg_reconciliation([_manifest_row("GBL", "LiM_plus", "in_flight")], root=tmp_path)
    row = _leg(legs, "GBL|LiM_plus")
    assert row["classification"] == "in_flight" and row["duplicate_work_risk"] == "false"


def test_a_stale_manifest_row_is_flagged_when_the_log_already_terminated(tmp_path):
    """清单说还在跑、日志其实已经正常结束 => 也要告警，否则这条腿会被重复排一遍。"""
    module = _load()
    job = tmp_path / "SL" / "M"
    job.mkdir(parents=True)
    (job / "SL_M.log").write_text("****ORCA TERMINATED NORMALLY****\n", encoding="utf-8")
    legs = module.leg_reconciliation([_manifest_row("SL", "M", "in_flight")], root=tmp_path)
    assert _leg(legs, "SL|M")["duplicate_work_risk"] == "true"


def test_a_computed_row_is_never_flagged(tmp_path):
    module = _load()
    job = tmp_path / "EMC" / "M"
    job.mkdir(parents=True)
    (job / "EMC_M.log").write_text("****ORCA TERMINATED NORMALLY****\n", encoding="utf-8")
    legs = module.leg_reconciliation([_manifest_row("EMC", "M", "computed")], root=tmp_path)
    row = _leg(legs, "EMC|M")
    assert row["classification"] == "computed" and row["duplicate_work_risk"] == "false"


def test_shipped_reconciliation_matches_the_delivered_ledger():
    legs = _rows(RECON)
    assert len(legs) == 20 and len({row["leg_id"] for row in legs}) == 20
    assert all(row["duplicate_work_risk"] == "false" for row in legs)
    computed = {row["leg_id"] for row in legs if row["classification"] == "computed"}
    ledger = {"%s|%s" % (row["name"], row["state"]) for row in _rows(LEDGER)}
    assert computed == ledger, "闭环现场核对与交付账本的 computed 集合必须一致"