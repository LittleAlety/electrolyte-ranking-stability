# -*- coding: utf-8 -*-
"""方案 5.3 / 11 的关键 pair 第二泛函靶向复核 —— 结果前冻结的预注册计划（零新增电子结构计算）。

方案 5.3 要求「明确选择规则，属于靶向复核」；方案 11 给该靶向复核登记 16-32 个单点的预算。
本脚本把规则**在结果产生之前**写成可核验的产物：不跑任何 ORCA/xTB，不改写任何已有数值，
也不动历史产物（方案 13）。

只读输入
--------
* outputs/physics_completion/method_audit/method_settings.csv                S1..S4 的冻结定义
* outputs/physics_completion/method_audit/robust_inversion_certification.json 被认证为稳健翻转的 pair
* outputs/physics_completion/closure/four_molecule_state_closure.csv        20 条腿的登记状态
* outputs/physics_completion/cost/cost_ledger.csv                           方案 11 的 16-32 SP 预算行

冻结的选取规则（先写规则、后看结果）
------------------------------------
1. pair = 在冻结几何方法轴上被认证为 robust inversion 的那几对（读认证文件）；
2. 分子 = 这些 pair 的成员里、同时属于四分子生产分母（DMC / EMC / GBL / SL）的那些，落选者显式登记；
3. 每条腿 = 上述分子 x 4 个主态 M / M_plus / LiM_plus / LiM_2plus；
4. 设定 = 两个预先接受的第二泛函设定 S3 与 S4（PBE0-D4 的 def2-TZVP / def2-TZVPD 两支）；
5. 几何 = 该腿**已登记的生产最终 Opt 几何**，不重优化、不算频率；
6. 触发 = 某腿的生产 Opt/Freq 登记完成（terminated、opt_converged、imaginary_modes=0）后，
   该腿的两支 SP 才可入队；未登记的腿标 blocked_on_production_leg，不预跑、不替补；
7. 禁止 = 不按结果挑点、不因某对翻转与否增删行、不复跑整套 128 单点矩阵。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_pair_recheck_plan.py
    .venv\\Scripts\\python.exe scripts\\build_pair_recheck_plan.py --check
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PC = REPO / "outputs" / "physics_completion"
METHOD_SETTINGS = PC / "method_audit" / "method_settings.csv"
CERTIFICATION = PC / "method_audit" / "robust_inversion_certification.json"
CLOSURE = PC / "closure" / "four_molecule_state_closure.csv"
COST_LEDGER = PC / "cost" / "cost_ledger.csv"
OUT = PC / "pair_evidence" / "targeted_recheck"

MAIN_STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
SETTINGS = ("S3", "S4")
BUDGET_ITEM = "targeted_pair_second_method_single_points"
EXPECTED_SECOND_FUNCTIONAL = "PBE0-D4"
PRODUCED = "produced_single_conformer"

GEOMETRY_TEMPLATE = "work/wp2prod/{name}/{state}/{name}_{state}_opt.xyz"
GEOMETRY_NOTE = ("registered production Opt geometry; the raw ORCA output stays outside the "
                 "repository and outside the delivery mirror")

PLAN_FIELDS = ("record_id", "mol_id", "name", "state", "setting_id", "functional", "basis",
               "geometry_source", "geometry_available", "geometry_kind", "adds_new_geometry",
               "adds_new_frequency", "budget_sp", "status", "blocked_on", "note")
ACC_FIELDS = ("check_id", "description", "ok", "detail")
RESULT_COLUMN_TOKENS = ("ev", "energy", "sign", "delta", "flip")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_text(fields, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def dump(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def normalize_pair(label):
    return "|".join(part.strip() for part in label.split("|"))


def parse_budget(value):
    low, _, high = value.partition("-")
    return int(low), int(high)


def selection_rule():
    return [
        "pairs = exactly the pairs certified as a robust inversion on the frozen-geometry method axis",
        "molecules = the members of those pairs that also belong to the four-molecule production subcohort",
        "legs = every scoped molecule x the four main states M / M_plus / LiM_plus / LiM_2plus",
        "settings = the two pre-accepted second-functional settings S3 and S4",
        "geometry = the leg production Opt geometry; no re-optimisation and no frequency",
        "trigger = a leg two single points are queued only after that leg production Opt/Freq is registered",
        "prohibited = no result-based point selection, no adding or dropping rows by outcome, "
        "no re-running the whole 128 single-point matrix",
    ]


def build():
    settings = {row["setting_id"]: row for row in read_csv(METHOD_SETTINGS)}
    certification = read_json(CERTIFICATION)

    closure = read_csv(CLOSURE)
    subcohort = sorted({(row["mol_id"], row["name"]) for row in closure if row["state"] in MAIN_STATES})
    name_to_mol = {name: mol_id for mol_id, name in subcohort}
    register_status = {(row["mol_id"], row["state"]): row["register_status"] for row in closure}

    certified_pairs = sorted(normalize_pair(entry["pair"]) for entry in certification["pairs"]
                             if entry.get("certified"))
    pair_members = sorted({part for label in certified_pairs for part in label.split("|")})
    scope_members = [name for name in pair_members if name in name_to_mol]
    outside = [name for name in pair_members if name not in name_to_mol]
    scope = [(name_to_mol[name], name) for name in scope_members]

    plan_rows = []
    ready = []
    blocked = []
    for mol_id, name in scope:
        for state in MAIN_STATES:
            registered = register_status.get((mol_id, state)) == PRODUCED
            for setting_id in SETTINGS:
                setting = settings[setting_id]
                row = {
                    "record_id": "%s|%s|%s" % (mol_id, state, setting_id),
                    "mol_id": mol_id, "name": name, "state": state,
                    "setting_id": setting_id, "functional": setting["functional"],
                    "basis": setting["basis"],
                    "geometry_source": GEOMETRY_TEMPLATE.format(name=name, state=state),
                    "geometry_available": str(registered).lower(),
                    "geometry_kind": "production_optimised",
                    "adds_new_geometry": "false", "adds_new_frequency": "false",
                    "budget_sp": "1",
                    "status": "ready" if registered else "blocked_on_production_leg",
                    "blocked_on": "" if registered else "%s|%s" % (mol_id, state),
                    "note": GEOMETRY_NOTE if registered else
                            "the production Opt/Freq leg is not registered yet; both single points "
                            "are queued only after it lands",
                }
                plan_rows.append(row)
                (ready if registered else blocked).append(row)

    planned = len(scope) * len(MAIN_STATES) * len(SETTINGS)
    ready_legs = sorted({(row["mol_id"], row["state"]) for row in ready})
    blocked_legs = sorted({(row["mol_id"], row["state"]) for row in blocked})
    registered_legs = sorted(key for key in register_status
                             if key[0] in {mol_id for mol_id, _ in scope}
                             and key[1] in MAIN_STATES and register_status[key] == PRODUCED)

    cost_rows = read_csv(COST_LEDGER)
    budget_row = next((row for row in cost_rows if row.get("item") == BUDGET_ITEM), {})
    budget_value = budget_row.get("value", "")
    budget_low, budget_high = parse_budget(budget_value) if "-" in budget_value else (0, 0)
    result_columns = [field for field in PLAN_FIELDS
                      if any(token in field for token in RESULT_COLUMN_TOKENS)]

    checks = [
        {"check_id": "registered_before_any_recheck_sp",
         "description": "规则与作业计划在任何一个复核单点跑出结果之前登记，计划里没有任何已完成状态",
         "ok": all(row["status"] in ("ready", "blocked_on_production_leg") for row in plan_rows),
         "detail": "status only takes ready / blocked_on_production_leg; %d planned, 0 run" % len(plan_rows)},
        {"check_id": "scope_is_exactly_the_certified_pairs",
         "description": "对象正好是认证文件里 certified=True 的那几对，不多不少",
         "ok": (bool(certified_pairs)
                and certified_pairs == sorted(normalize_pair(entry["pair"])
                                              for entry in certification["pairs"] if entry.get("certified"))
                and len(certified_pairs) == certification["n_pairs_certified"]),
         "detail": "pairs=%s; n_pairs_certified=%s"
                   % ("; ".join(certified_pairs), certification["n_pairs_certified"])},
        {"check_id": "molecules_are_the_certified_members_in_the_subcohort",
         "description": "分子取 pair 成员的并集与四分子生产分母的交集，被排除的成员显式登记",
         "ok": (set(scope_members) == set(pair_members) - set(outside)
                and set(scope_members) <= set(name_to_mol)),
         "detail": "pair members=%s; in scope=%s; outside the four-molecule subcohort=%s"
                   % (", ".join(pair_members), ", ".join(scope_members), ", ".join(outside) or "none")},
        {"check_id": "planned_sp_matches_the_rule",
         "description": "计划行数 = 分子 x 4 主态 x 2 设定，且每行都归入 ready 或 blocked",
         "ok": (planned == len(plan_rows) and len(ready) + len(blocked) == len(plan_rows)
                and len(plan_rows) == len(scope) * len(MAIN_STATES) * len(SETTINGS)),
         "detail": "%d molecules x %d states x %d settings = %d single points (ready %d / blocked %d)"
                   % (len(scope), len(MAIN_STATES), len(SETTINGS), planned, len(ready), len(blocked))},
        {"check_id": "planned_sp_inside_the_plan_11_budget",
         "description": "计划的单点数落在方案 11 登记的 16-32 预算内",
         "ok": budget_low <= planned <= budget_high,
         "detail": "plan 11 row %s = %s; planned = %d" % (BUDGET_ITEM, budget_value, planned)},
        {"check_id": "settings_are_the_frozen_second_functional",
         "description": "两个设定来自已冻结的第二泛函（audit control），不是新挑的泛函",
         "ok": all(settings.get(s, {}).get("functional") == EXPECTED_SECOND_FUNCTIONAL
                   and settings.get(s, {}).get("role") == "audit_control" for s in SETTINGS),
         "detail": "; ".join("%s = %s/%s (role=%s)" % (s, settings.get(s, {}).get("functional", "?"),
                                                       settings.get(s, {}).get("basis", "?"),
                                                       settings.get(s, {}).get("role", "?"))
                             for s in SETTINGS)},
        {"check_id": "production_registered_legs_are_ready",
         "description": "已登记的生产腿才标 ready，且每条 ready 腿恰好两支单点",
         "ok": (ready_legs == registered_legs
                and all(sum(1 for row in ready if (row["mol_id"], row["state"]) == leg) == len(SETTINGS)
                        for leg in ready_legs)),
         "detail": "ready legs %d/%d: %s" % (len(ready_legs), len(scope) * len(MAIN_STATES),
                                             ", ".join("%s|%s" % leg for leg in ready_legs) or "none")},
        {"check_id": "unregistered_legs_are_blocked_and_named",
         "description": "未登记的腿标 blocked，逐行写明缺哪条腿，且没有几何可用",
         "ok": (blocked_legs == sorted(set(registered_legs) ^
                                      {(mol_id, state) for mol_id, _ in scope for state in MAIN_STATES})
                and all(row["blocked_on"] == "%s|%s" % (row["mol_id"], row["state"])
                        and row["geometry_available"] == "false" for row in blocked)
                and all(row["geometry_available"] == "true" for row in ready)),
         "detail": "blocked rows %d, each naming its missing leg: %s"
                   % (len(blocked), ", ".join("%s|%s" % leg for leg in blocked_legs) or "none")},
        {"check_id": "no_new_geometry_no_new_frequency_no_result_columns",
         "description": "只加第二泛函单点：不新增几何、不新增频率，计划表不含任何结果列",
         "ok": (all(row["adds_new_geometry"] == "false" and row["adds_new_frequency"] == "false"
                    for row in plan_rows) and not result_columns),
         "detail": "result-bearing columns: %s" % (", ".join(result_columns) or "none")},
        {"check_id": "budget_row_in_cost_ledger_still_planned",
         "description": "方案 11 的该预算行仍是 planned，说明复核尚未开始",
         "ok": budget_row.get("status") == "planned",
         "detail": "%s status=%s" % (BUDGET_ITEM, budget_row.get("status", "missing"))},
    ]
    n_failed = sum(0 if item["ok"] else 1 for item in checks)

    rule = {
        "scope": ("plan 5.3 / 11 targeted second-functional re-check of the certified pair inversions "
                  "(zero new geometry, zero new frequency, zero new electronic structure so far)"),
        "registered_before_any_recheck_sp": True,
        "frozen_inputs": {
            "method_settings": "outputs/physics_completion/method_audit/method_settings.csv",
            "certification": "outputs/physics_completion/method_audit/"
                             "robust_inversion_certification.json",
            "state_registration": "outputs/physics_completion/closure/"
                                  "four_molecule_state_closure.csv",
            "plan_11_budget": "outputs/physics_completion/cost/cost_ledger.csv",
        },
        "selection_rule": selection_rule(),
        "certified_pairs": certified_pairs,
        "pair_members": pair_members,
        "scope_molecules": scope_members,
        "members_outside_the_four_molecule_subcohort": outside,
        "states": list(MAIN_STATES),
        "settings": {s: {"functional": settings.get(s, {}).get("functional", ""),
                         "basis": settings.get(s, {}).get("basis", ""),
                         "role": settings.get(s, {}).get("role", "")} for s in SETTINGS},
        "planned_single_points": planned,
        "plan_11_budget": budget_value,
        "planned_within_budget": budget_low <= planned <= budget_high,
        "ready_single_points": len(ready),
        "blocked_single_points": len(blocked),
        "ready_legs": ["%s|%s" % leg for leg in ready_legs],
        "blocked_legs": ["%s|%s" % leg for leg in blocked_legs],
        "geometry_policy": GEOMETRY_NOTE,
        "trigger": ("a leg's two single points are queued only after that leg's production Opt/Freq is "
                    "registered (terminated, opt_converged, imaginary_modes=0) in "
                    "outputs/physics_completion/closure/four_molecule_state_closure.csv"),
        "prohibited": ["selecting points by result", "adding or dropping rows by outcome",
                       "re-running the whole 128 single-point method-audit matrix"],
        "status": "registered_not_started",
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": n_failed,
    }

    md = [
        "# 方案 5.3 / 11：关键 pair 第二泛函靶向复核 —— 预注册计划",
        "",
        "> 由 `scripts/wp_production/build_pair_recheck_plan.py` 生成；**零新增电子结构计算**。",
        "> 本文件在任何一个复核单点跑出结果之前登记；规则不随后续结果修改。",
        "",
        "## 选取规则（结果前冻结）",
        "",
    ]
    for item in selection_rule():
        md.append("* %s" % item)
    md += [
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "| 认证的 pair | %s |" % "、".join(certified_pairs),
        "| pair 成员 | %s |" % "、".join(pair_members),
        "| 本次范围内的分子 | %s |" % "、".join(scope_members),
        "| 落在四分子分母之外的成员 | %s |" % ("、".join(outside) or "无"),
        "| 主态 | %s |" % " / ".join(MAIN_STATES),
        "| 第二泛函设定 | %s |" % " / ".join("%s (%s/%s)" % (s, settings[s]["functional"], settings[s]["basis"])
                                              for s in SETTINGS),
        "| 计划单点总数 | %d |" % planned,
        "| 方案 11 预算 | %s |" % budget_value,
        "| 可用（生产腿已登记） | %d |" % len(ready),
        "| 阻塞（生产腿未登记） | %d |" % len(blocked),
    ]
    md += [
        "",
        "## 作业计划（%d 行，逐行登记）" % len(plan_rows),
        "",
        "| 记录 | 分子 | 态 | 设定 | 泛函/基组 | 几何来源 | 几何可用 | 新增几何 | 新增频率 | 状态 | 阻塞于 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in plan_rows:
        md.append("| %s | %s | %s | %s | %s/%s | `%s` | %s | %s | %s | %s | %s |"
                  % (row["record_id"], row["name"], row["state"], row["setting_id"],
                     row["functional"], row["basis"], row["geometry_source"],
                     row["geometry_available"], row["adds_new_geometry"], row["adds_new_frequency"],
                     row["status"], row["blocked_on"] or "-"))
    md += [
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - n_failed, len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        md.append("| %s | %s | %s |" % (item["check_id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    md += [
        "",
        "## 边界",
        "",
        "* 这不是复核结果：本层只登记规则、对象、设定、几何来源与预算，**一个复核单点都还没跑**。",
        "* 生产腿一旦登记，按同一规则自动解锁该腿的两支单点；解锁只取决于登记状态，不取决于任何能量或符号。",
        "* 生产腿的最终 Opt 几何与原始 ORCA 输出留在仓库外 `work/wp2prod/`，不入交付镜像（与既有边界一致）。",
        "",
    ]

    files = {
        "outputs/physics_completion/pair_evidence/targeted_recheck/selection_rule.json": dump(rule),
        "outputs/physics_completion/pair_evidence/targeted_recheck/selection_rule.md": "\n".join(md),
        "outputs/physics_completion/pair_evidence/targeted_recheck/job_plan.csv":
            csv_text(PLAN_FIELDS, plan_rows),
        "outputs/physics_completion/pair_evidence/targeted_recheck/acceptance.csv":
            csv_text(ACC_FIELDS, checks),
    }
    meta = {"files": len(files), "planned": planned, "ready": len(ready), "blocked": len(blocked),
            "checks": len(checks), "failed": n_failed, "budget": budget_value,
            "pairs": certified_pairs}
    return files, meta


def main(argv=None):
    parser = argparse.ArgumentParser(description="Register the plan-5.3/11 targeted pair re-check plan.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    files, meta = build()

    if args.check:
        failures = []
        for rel, text in sorted(files.items()):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_text(encoding="utf-8") != text:
                failures.append("differs %s" % rel)
        if OUT.is_dir():
            for path in sorted(OUT.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(REPO).as_posix()
                    if rel not in files:
                        failures.append("stray %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:20]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d targeted-recheck files are byte-identical" % len(files))
        return 0

    for rel, text in sorted(files.items()):
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    print("wp2 pair recheck plan (plan 5.3 / 11)")
    print("-" * 70)
    print("  files      : %d" % meta["files"])
    print("  pairs      : %s" % "; ".join(meta["pairs"]))
    print("  planned SP : %d (plan 11 budget %s)" % (meta["planned"], meta["budget"]))
    print("  ready      : %d / blocked %d" % (meta["ready"], meta["blocked"]))
    print("  acceptance : %d checks / %d failed" % (meta["checks"], meta["failed"]))
    return 0 if meta["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())