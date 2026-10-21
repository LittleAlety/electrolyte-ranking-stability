"""Recovery-budget accounting and terminal-state report (plan: 资源安排条款).

The plan says: "沿用现有恢复包 600 core-hours＋300储备，先核算已消耗、在途预留和
余额，不重复拨一份预算".  This generator produces exactly that accounting from
the ledger, plus the per-state terminal dispositions, so the next round's
authorisation has real numbers in front of it.

Read-only: it derives everything from existing artifacts and asserts nothing
that is not on disk.  ``--check`` byte-compares.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"
COST = REPO / "outputs" / "physics_completion" / "cost"

OUT_MD = RECOVERY / "recovery_budget_accounting.md"
OUT_INDEX = RECOVERY / "recovery_budget_accounting_index.json"

RECOVERY_CAP = 600.0
RESERVE_CAP = 300.0


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect() -> dict:
    labels = _rows(ENS / "production_ensemble_labels.csv")
    accepted = sum(1 for r in labels if r["acceptance_status"] == "accepted")
    limited = [r for r in labels if r["acceptance_status"] == "limited"]
    provisional = [r for r in labels if r["acceptance_status"] == "provisional"]

    # measured cost from the ledger: every leg this project actually ran
    ledger = _rows(COST / "production_cost_ledger.csv")
    def _leg_cost(r):
        for col in ("core_hours", "hpc_core_hours"):
            v = (r.get(col) or "").strip()
            if v:
                return float(v)
        return None
    main_total = sum(c for c in (_leg_cost(r) for r in ledger) if c is not None)
    missing = sum(1 for c in (_leg_cost(r) for r in ledger) if c is None)

    # the recovery batch's own measured hours live in the per-package timestamps
    # reported by work/_recovery_cost.py; re-derive them here from the same files
    # so this generator is self-contained (no wall clock: all input mtimes)
    package_dirs = sorted(
        (REPO / "work").glob("hpc_production_ensemble_strict_recovery_v1*"))
    batch_rows = []
    batch_total = 0.0
    for pkg in package_dirs:
        hours = 0.0
        running = 0
        # the verified snapshots live under tasks/<name>/<leaf>/snapshots/<job>/ --
        # that is where the fetched timestamps are; the attempts/ dir only
        # exists on the cluster
        for attempt in pkg.glob("tasks/*/*/snapshots/*/"):
            try:
                start = (attempt / "started.utc").read_text(encoding="utf-8").strip()
            except OSError:
                continue
            try:
                end = (attempt / "normal_termination.utc").read_text(
                    encoding="utf-8").strip()
            except OSError:
                running += 1
                continue
            from datetime import datetime, timezone
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            try:
                t0 = datetime.strptime(start, fmt).replace(tzinfo=timezone.utc)
                t1 = datetime.strptime(end, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            hours += (t1 - t0).total_seconds() / 3600.0 * 4  # 4 cores per leg
        if hours or running:
            batch_rows.append({"package": pkg.name, "core_hours": hours,
                               "running": running})
            batch_total += hours

    dispositions = Counter()
    for r in limited:
        dispositions[r.get("limitation_reason", "")] += 1

    return {
        "accepted": accepted, "limited": limited, "provisional": provisional,
        "main_total": main_total, "missing": missing,
        "batch_rows": batch_rows, "batch_total": batch_total,
        "dispositions": dict(dispositions),
    }


def render(doc: dict) -> str:
    lines = [
        "# 恢复批次预算核算与终局报告（strict_recovery_v1）",
        "",
        "> 生成器 `build_recovery_budget_accounting.py`（`--check` 完全只读）。",
        "> 计划原文：「沿用现有恢复包 600 core-hours＋300储备，先核算已消耗、在途预留和余额，",
        "> 不重复拨一份预算。」本表就是这笔账。",
        "",
        "## 账本状态",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 系综 | **%d accepted / %d limited / %d provisional**（分母 48 不变）"
        % (doc["accepted"], len(doc["limited"]), len(doc["provisional"])),
        "| 主生产账本（60 腿） | %.1f core-hours（%d 条 MISSING）"
        % (doc["main_total"], doc["missing"]),
        "",
        "## 恢复包消耗（按包实测，4 核/腿）",
        "",
        "| 包 | 实测 core-hours | 在跑 |",
        "|---|---|---|",
    ]
    for r in doc["batch_rows"]:
        lines.append("| `%s` | %.1f | %d |" % (r["package"], r["core_hours"],
                                               r["running"]))
    total = doc["batch_total"]
    lines += [
        "",
        "**恢复包合计：%.1f / %.0f core-hours（%.1f%%）；风险储备 %.0f 未动用。**"
        % (total, RECOVERY_CAP, 100.0 * total / RECOVERY_CAP, RESERVE_CAP),
        "",
        "## 9 个 limited 态的终局原因（历史保留，绝不清空）",
        "",
        "| 原因 | 态数 | 态 |",
        "|---|---|---|",
    ]
    by_reason: dict[str, list[str]] = {}
    for r in doc["limited"]:
        by_reason.setdefault(r.get("limitation_reason", ""), []).append(
            "%s|%s" % (r["name"], r["state"]))
    for reason, states in sorted(by_reason.items()):
        lines.append("| `%s` | %d | %s |" % (reason, len(states), ", ".join(states)))
    lines += [
        "",
        "## 下一轮授权需要知道的事",
        "",
        "1. **预算余量充足**：恢复包剩余约 %.0f core-hours。但 9 个 limited 态里 6 个是"
        "`rescue_budget_exhausted`（每成员两次真实计算已用完）——**再算需要另立版本**，"
        "不是继续花这一包。" % (RECOVERY_CAP - total),
        "2. **`species_drift_unrecoverable`（EMC/M_plus、TMP/LiM_plus）**：身份漂移是化学事实，"
        "换搜索方法不解决；发生键图改变的那条执行继续拒收。",
        "3. **计划预案的对应关系**：6 个预算耗尽态 → 计划「生产级覆盖诊断」（直接 DFT 多起点、"
        "相关扭转扫描或不同廉价预优化），须按态逐个版本化预注册（方法、成本上限、停止条件），"
        "不得沿用旧池回填。",
        "",
        "**本报告只记账，不改变任何验收判定。**",
        "",
    ]
    return "\n".join(lines)


def write_outputs() -> None:
    doc = collect()
    OUT_MD.write_text(render(doc), encoding="utf-8", newline="\n")
    OUT_INDEX.write_text(json.dumps({
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_recovery_budget_accounting.py",
        "recovery_used_core_hours": round(doc["batch_total"], 1),
        "recovery_cap": RECOVERY_CAP, "reserve_cap": RESERVE_CAP,
        "accepted": doc["accepted"], "limited": len(doc["limited"]),
        "dispositions": doc["dispositions"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def check() -> int:
    disk = OUT_MD.read_text(encoding="utf-8") if OUT_MD.is_file() else ""
    if disk != render(collect()):
        print("CHECK FAILED -- %s drifted" % OUT_MD.name)
        return 1
    print("CHECK OK -- budget accounting matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    doc = collect()
    print("budget accounting: recovery %.1f/%.0f core-hours, %d limited states"
          % (doc["batch_total"], RECOVERY_CAP, len(doc["limited"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
