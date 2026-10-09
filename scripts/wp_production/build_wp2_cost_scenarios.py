# -*- coding: utf-8 -*-
"""方案 11：剩余生产成本的按类中位 / p90 与低-中-高资源情景（零新增电子结构计算）。

方案 11 要求：用已测作业类别的中位与 p90 估算剩余成本，给出低 / 中 / 高资源情景与可用并发，
并且先检查 Opt / Freq / SP 的分项成本。本脚本只读已登记的产物：

* outputs/physics_completion/closure/four_molecule_state_closure.csv  20 条登记腿及其状态
* outputs/physics_completion/cost/production_cost_ledger.csv          生产腿 Opt+NumFreq（逐作业）
* outputs/physics_completion/cost/audit_cost_ledger.csv               WP1 单点 / 几何准备（逐作业）
* outputs/physics_completion/cost/pilot_cost_ledger.csv               pilot xTB / SP / 唯一的 freq-only
* outputs/physics_completion/cost/cost_ledger.csv                     已登记的绝对成本三项与 SP 预算

三条硬约束（与方案一致，勿放宽）：
* 缺值不写 0；没有实测作业的类别显式标 unmeasured，用带标记的界给出，不冒充估计值；
* 绝对成本三项在四分子闭环前仍是 MISSING，本脚本不改写它们，只登记可测的分项；
* 历史产物按方案 13 不被覆盖（outputs/week25 的 cpu_core_hours_available=false 只在 index 里登记 supersedes）。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_wp2_cost_scenarios.py
    .venv\\Scripts\\python.exe scripts\\build_wp2_cost_scenarios.py --check
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COST = REPO / "outputs" / "physics_completion" / "cost"
CLOSURE = REPO / "outputs" / "physics_completion" / "closure" / "four_molecule_state_closure.csv"

PRODUCTION = COST / "production_cost_ledger.csv"
AUDIT = COST / "audit_cost_ledger.csv"
PILOT = COST / "pilot_cost_ledger.csv"
COST_LEDGER = COST / "cost_ledger.csv"

#: 生产腿按状态归类的类别名（与 def2 基组口径绑定，不可混用）。
CLASS_OF_STATE = {
    "M": "free_neutral_def2TZVP",
    "M_tzvpd": "free_neutral_def2TZVPD",
    "M_plus": "free_cation_def2TZVPD",
    "LiM_plus": "li_complex_def2TZVPD",
    "LiM_2plus": "li_complex_def2TZVPD",
}
ORDER = ("M", "M_tzvpd", "M_plus", "LiM_plus", "LiM_2plus")
WORKER_CORES = 4
WORKER_CHOICES = (2, 3, 4)
CURRENT_POLICY_WORKERS = 2
JOINT_NOTE = ("production legs are joint Opt + NumFreq jobs, so Opt and Freq cannot be "
              "separated from their wall time")

RES_FIELDS = ("job_class", "mol_id", "name", "state", "basis_note", "measured_class",
              "estimate_kind", "core_hours_low", "core_hours_mid", "core_hours_high",
              "basis_low", "basis_mid", "basis_high", "note")
ACC_FIELDS = ("check_id", "description", "ok", "detail")


def read_csv(path):
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(fieldnames, rows):
    out = io.StringIO()
    out.write(",".join(fieldnames) + "\n")
    for row in rows:
        cells = []
        for key in fieldnames:
            value = row.get(key, "")
            value = "" if value is None else str(value)
            if "," in value or '"' in value or "\n" in value:
                value = '"' + value.replace('"', '""') + '"'
            cells.append(value)
        out.write(",".join(cells) + "\n")
    return out.getvalue()


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def round6(value):
    return round(float(value), 6)


def p90(values):
    """最近秩定义（小样本下等于最大值），此处显式声明而不是用插值假装样本充足。"""
    ordered = sorted(values)
    index = max(1, math.ceil(0.9 * len(ordered)))
    return ordered[index - 1]


def stats(values):
    return {"n": len(values), "min": round6(min(values)), "median": round6(statistics.median(values)),
            "p90": round6(p90(values)), "max": round6(max(values))}


def production_legs():
    """已折入生产账本的腿：{state: [core_hours, ...]} 与是否已折入。"""
    by_state = {}
    measured = set()
    for record in read_csv(PRODUCTION):
        state = record.get("state", "")
        try:
            hours = float(record.get("core_hours", ""))
        except ValueError:
            continue
        by_state.setdefault(state, []).append(hours)
        measured.add((record.get("mol_id", ""), state))
    return by_state, measured


def production_classes(by_state):
    """把已测腿按类别归并（state -> class）。"""
    per_class = {}
    for state, values in by_state.items():
        per_class.setdefault(CLASS_OF_STATE[state], []).extend(values)
    return per_class


def sp_stats():
    """固定几何单点成本：pilot（逐分子-态）与 WP1 审计（逐 setting）分别统计，不合并口径。"""
    pilot = {}
    for record in read_csv(PILOT):
        if record.get("phase") != "orca_sp":
            continue
        method = record.get("method", "")
        basis = "def2-TZVP" if "def2-TZVP " in method + " " else "def2-TZVPD"
        try:
            pilot.setdefault((record.get("state", ""), basis), []).append(
                float(record.get("core_hours", "")))
        except ValueError:
            continue
    audit = {}
    for record in read_csv(AUDIT):
        if record.get("phase") != "orca_audit_single_point":
            continue
        key = (record.get("state", ""), record.get("basis", ""))
        try:
            audit.setdefault(key, []).append(float(record.get("core_hours", "")))
        except ValueError:
            continue
    return pilot, audit


def freq_only():
    for record in read_csv(PILOT):
        if record.get("phase") == "orca_freq":
            return record
    return {}


def opt_only():
    for record in read_csv(AUDIT):
        if record.get("phase") == "orca_emc_li_opt":
            return record
    return {}


def closure_rows():
    rows = read_csv(CLOSURE)
    rows.sort(key=lambda row: (row.get("name", ""), ORDER.index(row.get("state", "M"))))
    return rows


def build():
    legs = closure_rows()
    by_state, measured_keys = production_legs()
    per_class = production_classes(by_state)
    pilot_sp, audit_sp = sp_stats()
    all_measured = [value for values in per_class.values() for value in values]
    global_max = max(all_measured) if all_measured else 0.0

    pending = [row for row in legs if row.get("register_status") != "produced_single_conformer"]
    estimate_rows = []
    for row in pending:
        state = row.get("state", "")
        job_class = CLASS_OF_STATE[state]
        samples = per_class.get(job_class, [])
        entry = {
            "job_class": job_class, "mol_id": row.get("mol_id", ""), "name": row.get("name", ""),
            "state": state, "basis_note": row.get("basis", "") or "def2-TZVPD",
            "measured_class": "true" if samples else "false",
        }
        if samples:
            entry.update({
                "estimate_kind": "measured_class",
                "core_hours_low": round6(min(samples)), "core_hours_mid": round6(statistics.median(samples)),
                "core_hours_high": round6(max(samples)),
                "basis_low": "class min (n=%d)" % len(samples),
                "basis_mid": "class median (n=%d)" % len(samples),
                "basis_high": "class p90/max (n=%d)" % len(samples),
                "note": "measured from production_cost_ledger.csv rows of the same state class",
            })
        else:
            entry.update({
                "estimate_kind": "declared_floor_unmeasured_class",
                "core_hours_low": round6(global_max), "core_hours_mid": round6(global_max),
                "core_hours_high": round6(2.0 * global_max),
                "basis_low": "declared floor = largest measured leg (no leg measured in this class)",
                "basis_mid": "declared floor = largest measured leg (no leg measured in this class)",
                "basis_high": "2 x declared floor (no leg measured in this class)",
                "note": ("no Li-complex leg has been produced yet; the largest measured leg is used "
                         "as a declared floor rather than the class minimum, because a Li complex "
                         "carries more atoms and charge than any free leg. The first completed Li "
                         "leg replaces this."),
            })
        estimate_rows.append(entry)

    scenarios = {}
    for key in ("low", "mid", "high"):
        total = sum(float(row["core_hours_" + key]) for row in estimate_rows)
        scenarios[key] = {
            "core_hours": round6(total),
            "wall_hours": {str(workers): round6(total / (workers * WORKER_CORES))
                           for workers in WORKER_CHOICES},
        }

    pilot_table = {("%s|%s" % key): stats(values) for key, values in sorted(pilot_sp.items())}
    audit_table = {("%s|%s" % key): stats(values) for key, values in sorted(audit_sp.items())}
    sp_all = [value for values in list(pilot_sp.values()) + list(audit_sp.values())
              for value in values]
    freq = freq_only()
    opt = opt_only()
    absolute = [{"item": row.get("item", ""), "status": row.get("status", ""),
                 "value": row.get("value", ""), "note": row.get("note", "")}
                for row in read_csv(COST_LEDGER) if row.get("kind") == "absolute"]
    targeted = [row for row in read_csv(COST_LEDGER)
                if row.get("item") == "targeted_pair_second_method_single_points"]

    checks = []
    checks.append({
        "check_id": "every_registered_leg_is_accounted_for",
        "description": "20 条登记腿全部归位：已测 7 条 + 待补 13 条，不丢腿",
        "ok": str(len(legs) == 20 and len(measured_keys) + len(pending) == 20).lower(),
        "detail": "registered=%d measured=%d pending=%d" % (len(legs), len(measured_keys), len(pending)),
    })
    pending_keys = {(row["mol_id"], row["state"]) for row in pending}
    checks.append({
        "check_id": "pending_legs_are_exactly_the_legs_without_a_production_label",
        "description": "待补集合 = 闭环表里没有产出的腿，不夹带已算腿重复计费",
        "ok": str(pending_keys.isdisjoint(measured_keys)).lower(),
        "detail": "overlap=%d" % len(pending_keys & measured_keys),
    })
    monotone = all(float(row["core_hours_low"]) <= float(row["core_hours_mid"]) <= float(row["core_hours_high"])
                   for row in estimate_rows)
    checks.append({
        "check_id": "per_leg_scenarios_are_monotone",
        "description": "每条腿 low <= mid <= high，不允许出现低情景高于高情景",
        "ok": str(bool(estimate_rows) and monotone).lower(),
        "detail": "checked %d pending legs" % len(estimate_rows),
    })
    checks.append({
        "check_id": "totals_are_the_sum_of_their_rows",
        "description": "情景总量等于逐腿之和（内部一致，可逐条复核）",
        "ok": str(all(abs(scenarios[key]["core_hours"]
                          - sum(float(row["core_hours_" + key]) for row in estimate_rows)) < 1e-9
                      for key in ("low", "mid", "high"))).lower(),
        "detail": "low=%.6f mid=%.6f high=%.6f core-hours" % (scenarios["low"]["core_hours"],
                                                             scenarios["mid"]["core_hours"],
                                                             scenarios["high"]["core_hours"]),
    })
    named = all(row["basis_low"] and row["basis_mid"] and row["basis_high"] and row["estimate_kind"]
                for row in estimate_rows)
    checks.append({
        "check_id": "every_estimate_names_its_basis",
        "description": "每个数字都写明口径（类别实测 / 声明界），没有来源不明的数",
        "ok": str(bool(estimate_rows) and named).lower(),
        "detail": "%d/%d rows labelled" % (sum(1 for row in estimate_rows if row["basis_low"]),
                                           len(estimate_rows)),
    })
    unmeasured = [row for row in estimate_rows if row["measured_class"] == "false"]
    flagged = all(row["estimate_kind"] == "declared_floor_unmeasured_class" and row["note"]
                  for row in unmeasured)
    checks.append({
        "check_id": "unmeasured_classes_are_flagged_not_invented",
        "description": "没有实测作业的类别（Li 复合腿）显式标 unmeasured + 声明下界，不冒充估计值",
        "ok": str(flagged).lower(),
        "detail": "%d rows: %s" % (len(unmeasured), " ".join(sorted({row["job_class"] for row in unmeasured})) or "none"),
    })
    checks.append({
        "check_id": "phase_split_is_limited_to_measured_phases",
        "description": "分项成本只报有实测的 phase（SP / freq-only / 几何准备），并登记 Opt+Freq 联合作业不可拆分",
        "ok": str(bool(pilot_sp) and bool(audit_sp)).lower(),
        "detail": "SP pilot keys=%d audit keys=%d; freq_only=%s; %s" % (
            len(pilot_sp), len(audit_sp), freq.get("job_id", "none"), JOINT_NOTE),
    })
    checks.append({
        "check_id": "absolute_cost_items_stay_missing",
        "description": "绝对成本三项在四分子闭环前仍标 MISSING 且值为空，不用部分数据填成 headline 数",
        "ok": str(len(absolute) == 3 and all(row["status"] == "MISSING" and row["value"] == ""
                                             for row in absolute)).lower(),
        "detail": "items=%s" % " ".join(row["item"] for row in absolute),
    })

    index = {
        "scope": ("plan 11: per-class median / p90 of the measured jobs and low / mid / high scenarios "
                  "for the 13 legs still missing from the four-molecule loop; zero new electronic structure"),
        "measured": {
            "legs": len(measured_keys),
            "core_hours_total": round6(sum(all_measured)),
            "per_class": {name: stats(values) for name, values in sorted(per_class.items())},
        },
        "phase_split": {
            "sp_jobs": {"pilot_by_state_basis": pilot_table, "audit_by_state_basis": audit_table,
                        "n_merged": len(sp_all), "median_core_hours_merged": round6(statistics.median(sp_all)) if sp_all else ""},
            "freq_only": {"job_id": freq.get("job_id", ""), "method": freq.get("method", ""),
                          "wall_sec": freq.get("wall_sec", ""), "core_hours": freq.get("core_hours", ""),
                          "n_measured": 1 if freq else 0},
            "opt_only": {"job_id": opt.get("job_id", ""), "basis": opt.get("basis", ""),
                         "wall_sec": opt.get("wall_sec", ""), "core_hours": opt.get("core_hours", ""),
                         "comparable_to_production": False,
                         "note": "the only standalone optimisation is the r2SCAN-3c geometry preparation, "
                                 "so it is not an wB97X-D4 Opt cost"},
            "joint_opt_freq": {"n_jobs": len(read_csv(PRODUCTION)), "note": JOINT_NOTE},
        },
        "pending": {"legs": len(pending),
                    "per_class_counts": {name: sum(1 for row in pending
                                                    if CLASS_OF_STATE[row["state"]] == name)
                                         for name in sorted(set(CLASS_OF_STATE.values()))}},
        "scenarios": scenarios,
        "concurrency": {
            "worker_cores": WORKER_CORES, "worker_choices": list(WORKER_CHOICES),
            "current_policy_workers": CURRENT_POLICY_WORKERS,
            "note": ("wall hours = core-hours / (workers x %d); core-hours are concurrency-invariant. "
                     "The current policy caps production at %d concurrent ORCA jobs to keep the desktop "
                     "usable, so the low / mid / high wall times above are quoted at that cap and at the "
                     "wider alternatives." % (WORKER_CORES, CURRENT_POLICY_WORKERS)),
        },
        "targeted_recheck": {
            "registered_budget": targeted[0].get("value", "") if targeted else "",
            "registered_note": targeted[0].get("note", "") if targeted else "",
            "estimated_core_hours_per_sp": round6(statistics.median(sp_all)) if sp_all else "",
        },
        "absolute_items": absolute,
        "supersedes": ("outputs/week25/compute_budget_ledger.json records cpu_core_hours_available=false "
                       "and 'no nprocs*wall field'; that described the repository as of week25. Since "
                       "physics_completion_v1, allocated core-hours are recorded per job in the three "
                       "ledgers summarised here. Per plan 13 the historical artifact is not overwritten."),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }

    md = [
        "# 方案 11：剩余生产成本情景（低 / 中 / 高）",
        "",
        "> 由 `scripts/wp_production/build_wp2_cost_scenarios.py` 生成；零新增电子结构计算，只汇总已登记台账。",
        "> 口径：`wall hours = core-hours / (workers x %d)`；core-hours 与并发无关。" % WORKER_CORES,
        "",
        "## 已测作业（%d 条生产腿）" % len(measured_keys),
        "",
        "| 类别 | n | min | median | p90 | max | 单位 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, values in sorted(per_class.items()):
        entry = stats(values)
        md.append("| %s | %d | %.3f | %.3f | %.3f | %.3f | core-hour |"
                  % (name, entry["n"], entry["min"], entry["median"], entry["p90"], entry["max"]))
    md += [
        "",
        "## 待补 %d 条腿的情景" % len(pending),
        "",
        "| 分子 | 态 | 类别 | 实测类别? | low | mid | high | 口径 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in estimate_rows:
        md.append("| %s | %s | %s | %s | %.3f | %.3f | %.3f | %s |"
                  % (row["name"], row["state"], row["job_class"], row["measured_class"],
                     float(row["core_hours_low"]), float(row["core_hours_mid"]),
                     float(row["core_hours_high"]), row["basis_mid"]))
    md += [
        "",
        "| 情景 | core-hours | 墙上时间 @2 worker | @3 worker | @4 worker |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key in ("low", "mid", "high"):
        scenario = scenarios[key]
        md.append("| %s | %.3f | %.2f h | %.2f h | %.2f h |"
                  % (key, scenario["core_hours"], scenario["wall_hours"]["2"],
                     scenario["wall_hours"]["3"], scenario["wall_hours"]["4"]))
    md += [
        "",
        "* `li_complex_def2TZVPD` 目前没有任何实测腿，因此该类的 low / mid 都用**声明下界**"
        "（最大已测腿）而不是类别最小值；high 取该下界的 2 倍。第一条 Li 腿落地后应替换。",
        "",
        "## 分项成本（方案 11 要求先检查 Opt / Freq / SP）",
        "",
        "* 固定几何单点：pilot 与 WP1 审计分别有 %d / %d 条实测；合并中位 `%.6f` core-hour/SP。"
        % (sum(entry["n"] for entry in pilot_table.values()),
           sum(entry["n"] for entry in audit_table.values()),
           float(index["phase_split"]["sp_jobs"]["median_core_hours_merged"] or 0.0)),
        "* 只跑频率（freq-only）：实测 %d 条（`%s`，%s core-hour）。"
        % (index["phase_split"]["freq_only"]["n_measured"],
           index["phase_split"]["freq_only"]["job_id"] or "-",
           index["phase_split"]["freq_only"]["core_hours"] or "-"),
        "* 只做优化（opt-only）：唯一一条是 `%s`（%s），方法口径与生产腿不同，不能当作 wB97X-D4 的 Opt 成本。"
        % (index["phase_split"]["opt_only"]["job_id"] or "-",
           index["phase_split"]["opt_only"]["basis"] or "-"),
        "* 生产腿是 Opt + NumFreq 联合作业，Opt 与 Freq 无法从同一作业的墙上时间里拆分，本条如实登记而不估算。",
        "",
        "## 仍然 MISSING 的绝对三项",
        "",
        "| item | status | note |",
        "| --- | --- | --- |",
    ]
    for row in absolute:
        md.append("| %s | %s | %s |" % (row["item"], row["status"], row["note"]))
    md += [
        "",
        "## 历史口径",
        "",
        "* `outputs/week25/compute_budget_ledger.json` 的 `cpu_core_hours_available=false` 描述的是 week25 时的仓库；",
        "  自本批次起 allocated core-hours 已逐作业记录。按方案 13「历史产物不被覆盖」不改写该文件。",
        "",
    ]
    return {
        "outputs/physics_completion/cost/remaining_cost_scenarios.csv":
            csv_text(RES_FIELDS, estimate_rows),
        "outputs/physics_completion/cost/remaining_cost_scenarios.md": "\n".join(md),
        "outputs/physics_completion/cost/cost_scenario_index.json": dump(index),
        "outputs/physics_completion/cost/cost_scenario_acceptance.csv": csv_text(ACC_FIELDS, checks),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the plan-11 cost scenarios for the pending legs.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    files = build()
    if args.check:
        failures = []
        for rel, text in sorted(files.items()):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_text(encoding="utf-8") != text:
                failures.append("differs %s" % rel)
        if COST.is_dir():
            for path in sorted(COST.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(REPO).as_posix()
                    if rel.startswith("outputs/physics_completion/cost/cost_scenario") \
                            or rel.endswith("remaining_cost_scenarios.csv") \
                            or rel.endswith("remaining_cost_scenarios.md"):
                        if rel not in files:
                            failures.append("stray %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:20]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d cost-scenario files are byte-identical" % len(files))
        return 0
    for rel, text in sorted(files.items()):
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    n_checks = sum(1 for line in files[
        "outputs/physics_completion/cost/cost_scenario_acceptance.csv"].splitlines()[1:] if line)
    n_failed = sum(1 for line in files[
        "outputs/physics_completion/cost/cost_scenario_acceptance.csv"].splitlines()[1:]
        if line.split(",")[2] == "false")
    print("wp2 cost scenarios")
    print("-" * 70)
    print("  files      : %d" % len(files))
    print("  acceptance : %d checks / %d failed" % (n_checks, n_failed))
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())