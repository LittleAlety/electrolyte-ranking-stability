"""Li 配位 motif 筛选的契约测试：执行器必须忠于已登记的规则与运行记录。

钉住三条容易悄悄退化的性质：
1. 规则先登记后执行：没有 motif_plan.csv 就不许跑筛选（load_legs 直接退出）；
2. 运行记录与落盘 CSV 必须同版（sha256 + 行数），且逐腿与登记计划一一对应；
3. 保留 motif 不超过登记上限，每个保留结构都带父几何 sha256，父几何路径仍在仓库外缓存里。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "screen_li_motifs.py"
PLAN = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "motif_plan.csv"
RUN_RECORD = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
SCREEN_CSV = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.csv"


def _module():
    spec = importlib.util.spec_from_file_location("screen_li_motifs_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_screen_module_imports_the_frozen_rule_instead_of_restating_it():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "build_li_motifs" in source, "筛选必须复用冻结的枚举规则，不能另写一套"
    module = _module()
    assert module.RULE_SOURCE.name == "build_li_motifs.py"


def test_screen_refuses_to_run_without_the_registered_plan(monkeypatch, tmp_path):
    module = _module()
    monkeypatch.setattr(module, "PLAN_PATH", tmp_path / "absent.csv")
    with pytest.raises(SystemExit):
        module.load_legs(None)


def test_run_record_matches_the_registered_plan(tmp_path):
    if not RUN_RECORD.is_file():
        pytest.skip("no screen run record registered yet")
    payload = json.loads(RUN_RECORD.read_text(encoding="utf-8"))
    rows = SCREEN_CSV.read_text(encoding="utf-8")
    assert hashlib.sha256(rows.encode("utf-8")).hexdigest() == payload["screen_csv_sha256"]
    modules = _module()
    plan_ids = {row.split(",")[0] for row in PLAN.read_text(encoding="utf-8").strip().splitlines()[1:]}
    assert {entry["record_id"] for entry in payload["legs"]} == plan_ids
    assert payload["n_failed"] == 0
    for entry in payload["legs"]:
        assert len(entry["kept"]) <= modules.MAX_KEEP
        parent = REPO_ROOT / entry["parent_path"]
        assert parent.is_file(), entry["parent_path"]
        for motif in entry["kept"]:
            assert motif["parent_sha256"] == entry["parent_sha256"]
            assert motif["parent_kind"].startswith("state_own")
            assert motif["motif_path"].startswith("work/")
