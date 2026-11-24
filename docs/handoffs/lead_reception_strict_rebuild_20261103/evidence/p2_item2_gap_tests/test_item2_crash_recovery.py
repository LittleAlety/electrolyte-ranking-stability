"""Item 2 崩溃恢复补测 · 写入中断/账本损坏后的拒收与恢复语义（只用 tmp_path，零共享对象写入）。

覆盖 P2_D7D8_entry_test_matrix.md 遗留缺口「崩溃恢复语义（中断后重跑）无独立用例」：
  1. append 中断（磁盘/断电模拟为半截账本）→ 重跑 fail-loud 拒收且损坏字节不被改写
  2. 恢复闭环：pre-append 备份 → 覆盖恢复 → 重跑成功追加（A+B 都在）
  3. 成员条目级半写（缺键的半条记录）→ LEDGER_MALFORMED_ENTRY 且字节不变
  4. 迁移中断恢复：迁移工具尚不存在 → 显式 skip（为切换预案的前置条件，不伪造通过）
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
    "dmc_staged_receiver_v5_crash", REPO / "work" / "dmc_staged_receiver_v5.py")
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


def H(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()


def record(opt_log: str = "optA", state: str = "CRASH|TEST") -> dict:
    return {
        "schema": R.SCHEMA,
        "member": {"state_key": state, "geometry_label": "L"},
        "stages": {
            "opt": {"log_sha256": H(opt_log), "final_geometry_sha256": H("geom")},
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


def test_interrupted_append_then_rerun_refuses_without_touching_damage(tmp_path):
    """半截账本（append 中断产物）→ 重跑 register 拒收 UNREADABLE，损坏字节逐位不变。"""
    target = tmp_path / "ledger.json"
    R.register(record("optA"), target)                       # 完整基线 A
    healthy = target.read_bytes()
    # 模拟中断：文件被截断在 JSON 中间（断电/磁盘满的可观测状态）
    damaged = healthy[: len(healthy) // 2]
    target.write_bytes(damaged)
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record("optB"), target)                   # 中断后重跑
    assert caught.value.code == "LEDGER_UNREADABLE"
    assert target.read_bytes() == damaged, "拒收不得改写损坏账本（保留恢复现场）"


def test_backup_restore_after_crash_recovers_and_continues(tmp_path):
    """恢复闭环：pre-append 备份覆盖恢复 → 重跑成功 → A+B 都在账本。"""
    target = tmp_path / "ledger.json"
    R.register(record("optA"), target)
    backup = tmp_path / "ledger.backup.json"
    backup.write_bytes(target.read_bytes())                  # 既有纪律：append 前备份

    # 中断：账本损坏
    target.write_bytes(target.read_bytes()[:20])
    with pytest.raises(R.ReceiverRefusal):
        R.register(record("optB"), target)

    # 恢复：从备份覆盖（等价于受控恢复步骤，不删现场之外的对象）
    target.write_bytes(backup.read_bytes())
    result = R.register(record("optB", state="CRASH|OTHER"), target)   # 恢复后重跑（新成员）
    assert result["appended"] is True and result["reason"] == "new_member"
    members = json.loads(target.read_text(encoding="utf-8"))["members"]
    assert len(members) == 2
    assert {m["member"]["state_key"] for m in members} == {"CRASH|TEST", "CRASH|OTHER"}


def test_half_written_member_entry_refused_and_bytes_unchanged(tmp_path):
    """成员条目级半写（JSON 合法但账本里只有半条记录、缺键）→ LEDGER_MALFORMED_ENTRY，字节不变。"""
    target = tmp_path / "ledger.json"
    # 直接构造"只有半条记录"的账本（模拟写到成员中间断电）
    doc = {"schema": R.LEDGER_SCHEMA,
           "members": [{"member": {"state_key": "CRASH|HALF"}}]}   # 半条：缺 stages/checks
    payload = (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    target.write_bytes(payload)
    with pytest.raises(R.ReceiverRefusal) as caught:
        R.register(record("optB"), target)
    assert caught.value.code == "LEDGER_MALFORMED_ENTRY"
    assert target.read_bytes() == payload


def test_migration_interrupt_recovery_awaiting_tool():
    """迁移中断/恢复：账本迁移工具（v2→v3 显式迁移）尚不存在——skip 并声明为切换前置条件。"""
    pytest.skip("migration tool not implemented; prerequisite listed in the switch plan "
                "(do not fabricate a pass)")
