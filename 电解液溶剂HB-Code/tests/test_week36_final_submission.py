# -*- coding: utf-8 -*-
"""Week 36 / 结题提交包的回归测试。

镜像目录在仓库之外（成果输出（part2）/week36），因此本测试**不自己拼仓库外路径**：它导入
生成器脚本，用生成器自己解析出的对象（module.DEFAULT_OUT / module.PAPER / module.sources()）
去核对，从而满足 clean-room 复现审计的 C4「测试绝不越出仓库」。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "scripts" / "build_week36_final_submission.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("week36_final_submission", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WEEK36 = _load_builder()

pytestmark = pytest.mark.skipif(not WEEK36.DEFAULT_OUT.is_dir(),
                                reason="week36 结题提交包尚未构建")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _submission() -> dict:
    return json.loads((WEEK36.DEFAULT_OUT / "SUBMISSION.json").read_text(encoding="utf-8"))


def test_every_source_the_builder_mirrors_exists() -> None:
    items = WEEK36.sources()
    assert len(items) == 23
    missing = [rel for src, rel in items if not src.is_file()]
    assert not missing, missing


def test_mirror_check_reports_byte_identical() -> None:
    proc = subprocess.run([sys.executable, str(BUILDER), "--check"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CHECK OK" in proc.stdout


def test_mirror_verification_is_all_green() -> None:
    payload = json.loads((WEEK36.DEFAULT_OUT / "verification.json").read_text(encoding="utf-8"))
    assert payload["n_checks"] == 15
    assert payload["n_failed"] == 0
    assert all(item["ok"] for item in payload["checks"])


def test_submission_records_match_the_mirrored_paper() -> None:
    paper = _submission()["paper"]
    assert _sha256(WEEK36.DEFAULT_OUT / paper["docx"]["path"]) == paper["docx"]["sha256"]
    assert _sha256(WEEK36.DEFAULT_OUT / paper["pdf"]["path"]) == paper["pdf"]["sha256"]
    assert _sha256(WEEK36.DEFAULT_OUT / paper["builder"]["path"]) == paper["builder"]["sha256"]
    assert _sha256(WEEK36.PAPER / "build_paper_docx.py") == paper["builder"]["sha256"]


def test_sha256sums_covers_every_mirrored_file() -> None:
    sums = (WEEK36.DEFAULT_OUT / "SHA256SUMS").read_text(encoding="utf-8")
    listed = {line.partition("  ")[2] for line in sums.splitlines() if line.strip()}
    actual = {p.relative_to(WEEK36.DEFAULT_OUT).as_posix() for p in WEEK36.DEFAULT_OUT.rglob("*")
              if p.is_file() and p.name != "SHA256SUMS"}
    assert listed == actual


def test_v6_to_v7_lineage_is_recorded() -> None:
    drift = _submission()["frozen_snapshots"][0]
    assert drift["repository_sha256_now"] == drift["week35_recorded_sha256"]
    assert drift["v6_backup_sha256"] == drift["v6_expected_sha256"]
    assert drift["v6_backup_sha256"] != drift["repository_sha256_now"]


def test_work_packages_cover_the_six_results_sections() -> None:
    packages = _submission()["work_packages"]
    assert [row["id"] for row in packages] == ["WP%d" % i for i in range(1, 8)]
    assert [row["week"] for row in packages] == ["week%d" % n for n in range(28, 35)]
    assert sorted({s for row in packages for s in row["paper_sections"]}) == \
        ["3.%d" % i for i in range(1, 7)]
    assert all("NOT CLOSED" in row["gate_status"] for row in packages)
