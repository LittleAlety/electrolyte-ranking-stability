"""Item 2 缺口补测 · 接收链三个未证类别的真实入口测试（只用 tmp_path，零共享对象写入）。

补的缺口（见 P2_D7D8_entry_test_matrix.md）：
  1. 未知 schema 拒收（register :1787 守卫，原缺独立用例）
  2. 重复接收：同内容幂等（duplicate_member，不双计）+ 异内容拒收（MEMBER_NOT_UNIQUE）
  3. 拒收不污染账本：malformed/unreadable 账本与未知 schema 拒收后字节不变
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # p2_item2_gap_tests → evidence → lead_reception... → handoffs → docs → 仓库根
SPEC = importlib.util.spec_from_file_location(
    "dmc_staged_receiver_v5_gap", REPO / "work" / "dmc_staged_receiver_v5.py")
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


def H(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()


def record(schema: str = None, opt_log: str = "optA") -> dict:
    return {
        "schema": schema if schema is not None else R.SCHEMA,
        "member": {"state_key": "GAP|TEST", "geometry_label": "L"},
        "stages": {
            "opt": {"log_sha256": H(opt_log), "final_geometry_sha256": H("geom") },
            "freq": {"log_sha256": H(opt_log + "f"), "hessian_sha256": H("hess"),
                     "geometry_sha256": H("geom")},
        },
        "labels": {"numerical_qc": "passed"},
        "checks": {"identity_consistent_with_composition": True,
                   "hessian_positive_semidefinite": True,
                   "freq_log_matches_hessian": True,
                   "zpe_consistent_with_modes": True},
        "trust": {"boundary": "sealed_registry"},
    }


def test_unknown_schema_is_refused_and_creates_no_ledger(tmp_path):
    """未知 schema → LEDGER_RECORD_INVALID，且拒收不落任何账本文件。"""
    target = tmp_path / "ledger.json"
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record(schema="dmc_staged_receiver/v99"), target)
    assert caught.value.code == "LEDGER_RECORD_INVALID"
    assert not target.exists(), "拒收不得创建/污染目标账本"


def test_duplicate_same_content_is_idempotent_not_double_counted(tmp_path):
    """同内容重复接收：第二次 appended=false + duplicate_member，账本字节不变、成员数=1。"""
    target = tmp_path / "ledger.json"
    first = R.register(record(), target)
    assert first["appended"] is True and first["reason"] == "new_member"
    before = target.read_bytes()
    second = R.register(record(), target)
    assert second["appended"] is False and second["reason"] == "duplicate_member"
    assert target.read_bytes() == before, "幂等重复不得改写账本"
    assert len(json.loads(target.read_text(encoding="utf-8"))["members"]) == 1


def test_duplicate_member_with_different_evidence_is_refused(tmp_path):
    """同成员异证据 → MEMBER_NOT_UNIQUE 拒收，账本字节不变（不静默版本化）。"""
    target = tmp_path / "ledger.json"
    R.register(record(), target)
    before = target.read_bytes()
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record(opt_log="optB"), target)
    assert caught.value.code == "MEMBER_NOT_UNIQUE"
    assert target.read_bytes() == before, "拒收不得改写账本"


def test_malformed_existing_ledger_refuses_and_bytes_unchanged(tmp_path):
    """既有账本无 members 列表 → LEDGER_MALFORMED_ENTRY，原字节逐位不变。"""
    target = tmp_path / "ledger.json"
    payload = json.dumps({"schema": R.LEDGER_SCHEMA, "members": "not-a-list"}).encode()
    target.write_bytes(payload)
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record(), target)
    assert caught.value.code == "LEDGER_MALFORMED_ENTRY"
    assert target.read_bytes() == payload


def test_unreadable_existing_ledger_refuses_and_bytes_unchanged(tmp_path):
    """既有账本不可解析 → LEDGER_UNREADABLE（file left untouched），原字节逐位不变。"""
    target = tmp_path / "ledger.json"
    payload = b"{not-json!!"
    target.write_bytes(payload)
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record(), target)
    assert caught.value.code == "LEDGER_UNREADABLE"
    assert target.read_bytes() == payload


def test_directory_target_is_refused(tmp_path):
    """账本路径是目录 → LEDGER_PATH_INVALID，不写入。"""
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record(), tmp_path)
    assert caught.value.code == "LEDGER_PATH_INVALID"
