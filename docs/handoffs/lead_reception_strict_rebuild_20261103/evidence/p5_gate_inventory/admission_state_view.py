"""P5b · 准入状态汇聚视图（Plan action item 5 收尾：五维机读状态及依据单点保存）。

只读聚合五态（DEC|LiM_2plus, DEC|M_plus, GBL|LiM_plus, PC|M_plus, TMP|M）的
成员资格/身份/协议可比性/阶段绑定/coverage 五个维度：
  - 状态与依据全部来自活文件实测或已审定证据（binding_package / coverage_recheck / P1 基线），
    不手填 resolved、不做任何裁定；
  - 阶段绑定三轴取活哈希与 P1 记录对照，漂移即标记 SHARED_OBJECT_DRIFT（暂停发布规则）；
  - 依赖顺序按批准规则声明，未获授权的维度停在 PENDING。
输出仅进本 evidence 目录。
"""
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent                      # evidence/p5_gate_inventory/
REPO = HERE.parents[4]
BP = HERE.parent / "p4_five_state_binding/binding_package.json"
CR = REPO / "docs/handoffs/strict_rebuild_20261103/verification_20261103/coverage_recheck.json"
P1 = HERE.parent / "P1_D7D8_version_reconciliation.md"
CRITERION = REPO / "config/comparability_criterion_v1.json"
AXES = {
    "receiver_shared": (REPO / "work/dmc_staged_receiver_v5.py",
                        "205f1ba93d9a0b69f2ea5f86595eef527da03db6d6aa8b2a331dd25a2ca9bb66"),
    "receiver_d8_candidate": (REPO / "work/admission_closure_20261102/rev5_candidate_d8/dmc_staged_receiver_v5_candidate.py",
                              "138df33b6c2a677ac2697825ae3680650c0ea1b3235d219a66e7d4dd13dd153c"),
    "ledger": (REPO / "work/dmc_staged_staging_ledger.json",
               "c336acb5051deb31c276dc54c8bfefbcc64bf93d0244c82cb722a8869fd382d2"),
}
OUT = HERE / "admission_state_view.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    bp = json.loads(BP.read_text(encoding="utf-8"))
    cr = json.loads(CR.read_text(encoding="utf-8"))
    cr_by_state = {e.get("state") or e.get("state_key"): e for e in cr if isinstance(e, dict)}
    states = bp["states"]
    assert len(states) == 5, f"expected 5 bound states, got {len(states)}"

    # comparability: live file check, fail-closed
    if CRITERION.is_file():
        crit = json.loads(CRITERION.read_text(encoding="utf-8"))
        comparability = {"state": "CRITERION_FILE_PRESENT",
                         "approved": crit.get("approved") is True,
                         "basis": f"{CRITERION.relative_to(REPO).as_posix()} sha256={sha(CRITERION)}"}
        if crit.get("approved") is not True:
            comparability["state"] = "CRITERION_PRESENT_NOT_APPROVED"
    else:
        comparability = {"state": "NOT_APPROVED_CRITERION_ABSENT", "approved": False,
                         "basis": "config/comparability_criterion_v1.json absent (fail-closed; "
                                  "generation and delta selection are out of this session's authority)"}

    # stage linkage: live three-axis hashes vs P1 baseline
    axes = {}
    drift = False
    for name, (path, expected) in AXES.items():
        actual = sha(path) if path.is_file() else "MISSING"
        ok = actual == expected
        drift = drift or not ok
        axes[name] = {"path": path.relative_to(REPO).as_posix(), "expected_p1": expected,
                      "actual": actual, "match": ok}
    stage_state = ("SHARED_OBJECT_DRIFT" if drift else
                   "HISTORICAL_V4_ACTIVE_SWITCH_UNAUTHORIZED")
    stage_basis = ("三轴与 P1 记录全等；账本盘上 schema=v2 而模块期望 v3（三轴偏斜在案），"
                   "切换与迁移未授权（Plan open question 1）→ 停留历史 v4 记录等级"
                   if not drift else "任一轴活哈希≠P1 记录 → 按停止规则暂停受影响发布、重新绑定版本")

    view_states = []
    for s in states:
        key = s["state_key"]
        rep = s.get("qualified_representative")
        membership = {
            "state": "QUALIFIED_REPRESENTATIVE_PRESENT" if rep else "NO_QUALIFIED_REPRESENTATIVE",
            "basis": {"rows_in_registry": s.get("membership_rows_in_registry"),
                      "representative": rep.get("member_key") if rep else None,
                      "source": "binding_package.json (P4, adjudicated lineage)"}}
        recheck = cr_by_state.get(key, {})
        identity = {
            "state": "PENDING_INDEPENDENT_IDENTITY_ADJUDICATION",
            "basis": {"binding_identity_review": s.get("identity_review"),
                      "missing_verbatim": s.get("missing"),
                      "recheck_search_outcome": recheck.get("search_outcome"),
                      "authority": "data-analysis (this session must not adjudicate identity)"}}
        coverage = {"production_coverage_state": s.get("coverage_status"),
                    "review_status": s.get("status_verbatim"),
                    "basis": {"reason_verbatim": s.get("reason_verbatim"),
                              "old_claim_verbatim": s.get("old_claim_verbatim"),
                              "handfilled_resolved": False}}
        view_states.append({
            "state_key": key,
            "membership": membership,
            "identity": identity,
            "comparability": comparability,
            "stage_linkage": {"state": stage_state, "basis": stage_basis, "axes": axes},
            "coverage": coverage,
            "binding_status": s.get("binding_status"),
            "production_written": s.get("production_written"),
        })

    view = {
        "schema": "admission_state_view/v1",
        "mode": "ISOLATED_READ_ONLY",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "binding_package": {"path": BP.relative_to(REPO).as_posix(), "sha256": sha(BP)},
            "coverage_recheck": {"path": CR.relative_to(REPO).as_posix(), "sha256": sha(CR)},
            "p1_report": {"path": P1.relative_to(REPO).as_posix(), "sha256": sha(P1)},
            "comparability_criterion": comparability["basis"],
        },
        "dependency_order_per_approved_rules": [
            "1. identity + coverage adjudication (data-analysis) → 2. comparability criterion approval "
            "(Lead/user) → 3. D7/D8 switch + ledger migration authorization (Lead, open question 1) → "
            "4. formal acceptance / authorized release batch (open question 2)",
            "current stop point: all five states at steps 1-3 PENDING; nothing may advance by default, "
            "old cache, or another entry"],
        "states": view_states,
        "selfcheck": {},
    }

    # fail-loud self-checks: no resolved anywhere, all coverage pending, no production writes
    blob = json.dumps(view, ensure_ascii=False)
    assert '"resolved"' not in blob and ": resolved" not in blob, "hand-filled resolved leaked into view"
    assert all(s["coverage"]["production_coverage_state"] == "NOT_TOUCHED" for s in view_states), "coverage touched"
    assert all(s["coverage"]["review_status"].startswith("PENDING") for s in view_states), "non-pending review"
    assert all(s["production_written"] is False for s in view_states), "production write flag set"
    view["selfcheck"] = {"no_resolved_anywhere": True, "coverage_not_touched_all": True,
                         "review_pending_all": True,
                         "production_written_false": True, "stage_axis_drift": drift,
                         "states": len(view_states)}
    OUT.write_text(json.dumps(view, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(view["selfcheck"], ensure_ascii=False))
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
