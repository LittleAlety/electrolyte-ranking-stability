"""D6 deliverable: the preregistration DRAFT for the four ranking-sensitive
M_plus states (AN / DMC / EMC / TMP) -- NOT a launch decision.

v3.0 D6 requires: "明确搜索动作、独立性、预算、候选选择与结束条件的
注册稿 | 未决定扩池时出限制报告；不自动启动".  This generator produces
that decision-support document from the frozen ledgers only:

* what is at stake (each state's Top-3 threat, bound vs current gap);
* the concrete search action a preregistration WOULD need (independence,
  cost ceiling, candidate selection, stop conditions) -- derived from the
  same basin/ledger conventions used elsewhere, never invented numbers;
* the honest limitation report branch (the default, per the user's
  2026-10-20 ruling: no automatic new-pool start).

Read-only inputs; deterministic outputs (no wall clock in the index);
``--check`` recomputes and byte-compares.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
SAMP = REPO / "outputs" / "physics_completion" / "sampling"
COST = REPO / "outputs" / "physics_completion" / "cost"

LABELS = ENS / "production_ensemble_labels.csv"
DIFF = SAMP / "sampling_3to6_diff.csv"
GAP = ENS / "remaining_gaps_decision_support.csv"
COST_LEDGER = COST / "production_cost_ledger.csv"

OUT_MD = ENS / "d6_ranking_sensitive_preregistration_draft.md"
OUT_INDEX = ENS / "d6_ranking_sensitive_preregistration_draft_index.json"

EH_TO_EV = 27.211386245988
#: the four states the WP3 rebuild singled out (Top-3 bound crosses the floor)
SENSITIVE_STATES = ("AN", "DMC", "EMC", "TMP")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _leg_cost() -> dict:
    cache = {}
    for r in _read(COST_LEDGER):
        key = (r.get("name"), r.get("state"))
        for col in ("core_hours", "hpc_core_hours"):
            v = _f(r.get(col))
            if v is not None:
                cache.setdefault(key, v)
                break
    return cache


def build() -> dict:
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    legs = _leg_cost()

    # accepted-only Top-3 on the oxidation axis (same recipe as the WP3 report)
    gaps = {}
    for name in sorted({k[0] for k in labels}):
        m, mp = labels.get((name, "M")), labels.get((name, "M_plus"))
        if not m or not mp:
            continue
        g_m, g_mp = _f(m.get("g_ensemble_eh")), _f(mp.get("g_ensemble_eh"))
        if g_m is None or g_mp is None:
            continue
        gaps[name] = {
            "gap_ev": (g_mp - g_m) * EH_TO_EV,
            "m_acc": m.get("acceptance_status"),
            "mp_acc": mp.get("acceptance_status"),
        }
    accepted = {n: v for n, v in gaps.items()
                if v["m_acc"] == "accepted" and v["mp_acc"] == "accepted"}
    ranked = sorted(accepted.items(), key=lambda kv: -kv[1]["gap_ev"])
    top3 = [n for n, _ in ranked[:3]]
    floor = accepted[top3[-1]]["gap_ev"] if len(top3) == 3 else None

    per_state = {}
    for name in SENSITIVE_STATES:
        mp = labels.get((name, "M_plus"), {})
        row = {
            "name": name,
            "gap_ev": gaps.get(name, {}).get("gap_ev"),
            "mp_acceptance": mp.get("acceptance_status", ""),
            "mp_limitation": mp.get("limitation_reason", ""),
            "n_unique": mp.get("n_unique", ""),
            "already_above_floor": (floor is not None
                                    and gaps.get(name, {}).get("gap_ev", 0) > floor),
            # per-candidate measured cost of ONE new production M_plus leg
            # (the prerequisite for any new basin in this state)
            "m_plus_leg_core_hours": legs.get((name, "M_plus")),
        }
        per_state[name] = row
    return {"top3": top3, "floor_ev": floor, "states": per_state}


def _pool_status_note() -> str:
    """Per-state frozen-pool status, DERIVED from the gap table on disk --
    never a blanket 'all pools exhausted' claim (the team review caught
    TMP/M_plus still holding the unused c10 basin, +4.235 kcal in window)."""
    notes = []
    try:
        gap_rows = _read(GAP)
    except OSError:
        return "（缺口表不可读；池状态未核对）"
    for name in SENSITIVE_STATES:
        for r in gap_rows:
            if r.get("name") == name and r.get("state") == "M_plus":
                if r.get("unused_basins"):
                    notes.append(
                        "%s：**池内仍有未用盆地 %s（%s）**——受限候选可能影响全池 Top-3，"
                        "现有候选扩展是否改变排序属独立问题，分列登记"
                        % (name, r["unused_basins"], r.get("unused_sources", "")))
                else:
                    notes.append("%s：冻结池内 M_plus 无未用盆地" % name)
    return "; ".join(notes) if notes else "（未找到四态的 M_plus 行）"


def render(data: dict) -> str:
    lines = [
        "# D6：四个排序敏感 M_plus 态的新池预注册稿（草案，未启动）",
        "",
        "> 生成器 `build_d6_preregistration_draft.py`（`--check` 完全只读）。零新增计算。",
        "> 用户 2026-10-20 裁决：limited 态默认不开新起点搜索，本稿只登记「若要开，"
        "必须预注册什么」，并给出限制报告分支（默认路径）。",
        "",
        "## 排序敏感的量化依据（accepted-only，RT 修正后口径）",
        "",
        "- accepted Top-3 = %s（地板 %.4f eV）" % (" > ".join(data["top3"]), data["floor_ev"]),
        "- 四个敏感态的当前 gap 与地板比较（M_plus 态受限）：",
        "",
        "| 分子 | M_plus gap (eV) | 当前位次含义 | M_plus 态 | 限制原因 | n_unique |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in sorted(data["states"].items()):
        verdict = ("**已越地板**——真值只需保持即可改写 Top-3"
                   if r["already_above_floor"] else "未越地板（上界敏感）")
        lines.append("| %s | %.4f | %s | %s | %s | %s |" % (
            name, r["gap_ev"], verdict,
            r["mp_acceptance"], r["mp_limitation"] or "—", r["n_unique"]))
    lines += [
        "",
        "## 若启动新池搜索，预注册必须冻结的四件事（v3.0 §13.5 + D6）",
        "",
        "1. **搜索动作与独立性**：对每个敏感态做新一轮独立构象/motif 搜索"
        "（不回填旧池、不沿旧盆地微扰）；母态结构可作起点但带电态需独立种子/扭转/Li motif"
        "（v3.0 §189）。搜索级 GFN2 与生产级 DFT 严格分层，GFN2 的 1.00 kcal/mol 只是筛选阈值。",
        "2. **成本上限（参考，预算尚未冻结）**：每个新盆地一条生产级 M_plus 腿。"
        "成本参考：M_plus 腿实测均值 11.75 core-hours（**12 条**主集实测，p50 更低）；"
        "启动前必须冻结每态的**新盆地数上限**与总 core-hours 上限，超限即停——"
        "本稿不预设具体数字，等预算冻结才进入可执行预注册。",
        "3. **候选选择**：新盆地必须与已 computed/failed 的全部成员过 DFT 级"
        "dedup（等价原子映射 + Li 给体 + RMSD + 扭转）；身份门（原子序 + 1.3× 键图）"
        "先于打包；**排序敏感判据在搜索前冻结**——什么样的新极小才算「足以改写 Top-3」"
        "（例：新极小使该态 gap 落到地板以下的能区），不得事后调整。",
        "4. **停止条件**：每态新起点 ≤2（与 2026-10-15 用户定规一致）；"
        "两个独立起点均失败 → 登记 `sampling_limited`（现有原因保留），不再续算；"
        "全部敏感态处理完或预算尽 → 本轮关闭。",
        "",
        "## 限制报告（默认分支，本轮生效）",
        "",
        "按用户裁决，本轮**不启动**新池搜索。四个敏感态维持 `limited` 及既有原因"
        "（provisional 已归零：语义修正后三个『救援在途』残留态已转 limited 终局）；"
        "「现有池不能认证 Top-3」作为独立事实登记（accepted Top-3 只是 6 个双 accepted 分子的"
        "子集结论，不能外推为全 12 分子的认证排序）。RT ln N bound 仅约束已知成员，"
        "对未发现盆地无约束力（AN/DMC 的 bound=0 是弱证据，如实登记）。",
        "",
        "### 各态冻结池现状（派生自缺口表，非笼统声明）",
        "",
        _pool_status_note() + "。",
        "",
        "### 稿件状态",
        "",
        "`limitation_report_complete; launch_preregistration_pending_budget` ——"
        "限制报告分支完整可交付；启动预注册仍待预算冻结（成本上限数字与每态盆地上限"
        "未定，定稿前不进入可执行状态）。「≤3 结构」指 3→6 审计口径的每态生产结构上限；"
        "「≤2 起点」指每态独立构象起点的救援上限——两个口径作用域不同，预注册时分别登记。",
        "",
        "**本稿为决策支持文档；启动任何新池搜索需用户逐态点名批准。**",
        "",
    ]
    per_cost = [r["m_plus_leg_core_hours"] for r in data["states"].values()
                if r["m_plus_leg_core_hours"] is not None]
    if per_cost:
        lines.append("参考（四态现有 M_plus 腿实测 core-hours：%s）"
                     % "; ".join("%s=%.2f" % (k, v) for k, v in
                                 sorted(((n, r["m_plus_leg_core_hours"])
                                         for n, r in data["states"].items()),
                                        key=lambda kv: kv[0])))
    return "\n".join(lines) + "\n"


def write_outputs(data: dict) -> None:
    OUT_MD.write_text(render(data), encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_d6_preregistration_draft.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (LABELS, DIFF, GAP, COST_LEDGER)},
        "decision": ("limitation_report_complete; "
                     "launch_preregistration_pending_budget; NO new-pool search launched"),
        "user_ruling": "2026-10-20: limited states get no automatic new starts",
        "n_states": len(SENSITIVE_STATES),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    data = build()
    if OUT_MD.read_text(encoding="utf-8") != render(data):
        print("STALE: differs: %s" % OUT_MD.name)
        return 1
    print("CHECK OK -- D6 preregistration draft matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs(build())
    print("wrote %s" % OUT_MD.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
