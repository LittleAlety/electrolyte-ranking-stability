# -*- coding: utf-8 -*-
"""方案 6.1 / 执行第 3 步：四分子 Li 配位 motif 采样的结果前预注册（零新增电子结构计算）。

方案 6.1 明确要求：「不同电荷态各自采样。除母态构象传播外，应对带电态补独立种子/扭转结构，
不能假定母态最低构象就覆盖其搜索空间。motif 能切换，电子身份与连接关系必须重新检查。」

现状（本脚本只读登记，不改数）：
* 生产 Li 腿（LiM_plus / LiM_2plus）目前各自从**一个冻结几何**起步
  （outputs/week5/c1/<NAME>/<NAME>_m1_G2Li.xyz；EMC 为 work/audit/EMC_Li/…），
  即 n_conformers = 1 的单代表 motif，不是 motif 系综；
* outputs/physics_completion/sampling/sampling_index.json 的 li_motif_sampling 8 条全为 not_computed；
* 24 条 Li 态 pilot 单点已登记（outputs/physics_completion/free_states/pilot_li_state_energies.csv），
  其中 **SL 的 LiM_plus 是 bidentate、LiM_2plus 是 monodentate** —— 直接证明 motif 会在母态与氧化态之间切换，
  因此「传播一个母态结构」在本批次是被证据否证的默认做法。

冻结的规则（先写规则、后看结果）
--------------------------------
1. 对象 = 四分子分母（DMC / EMC / GBL / SL）x 两个 Li 态（LiM_plus / LiM_2plus）= 8 条腿；
2. 每条腿**独立构造**候选 motif：从该态自己的电荷/多重度出发，枚举该分子可达给体集合上的
   单齿（round-0 类别）与双齿（给体间距允许 Li 桥接者）配位位置，再叠加母态构象种子；
   禁止把 LiM_plus 的优化结构直接当作 LiM_2plus 或多聚 motif 的起点；
3. 先用廉价气相 GFN2-xTB 筛选（筛不是生产级自由能）；去重按配位模式 + 重原子 RMSD / 扭转角；
   每腿保留最多 3 个独立低能 motif（资源规则，不是已证收敛尺度）；
4. 只有关键 pair 的 Li 台阶对 motif 选择敏感时，才按同一规则靶向扩到 6（升级登记待判，不按结果事后决定）；
5. 停止规则：两轮筛选后仍不能解析 → 报 sampling_limited / unresolved，不继续加算；
6. 生产级后续只把**选定的一条代表 motif** 送进 DFT 单构象腿，其余独立 motif 登记在案以备 3 -> 6 展开。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_li_motif_sampling_plan.py
    .venv\\Scripts\\python.exe scripts\\build_li_motif_sampling_plan.py --check
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PC = REPO / "outputs" / "physics_completion"
PILOT_LI = PC / "free_states" / "pilot_li_state_energies.csv"
SAMPLING_INDEX = PC / "sampling" / "sampling_index.json"
PRODUCTION_LEDGER = PC / "free_states" / "production_ledger.csv"
OUT = PC / "li_motif_sampling"

MOLS = (("C01", "DMC"), ("C02", "EMC"), ("C13", "GBL"), ("C14", "SL"))
LI_STATES = ("LiM_plus", "LiM_2plus")
SCREEN_LEVEL = "xTB GFN2 (gas phase) coordination-motif screen"
KEEP_LOWEST = 3
MAX_KEEP = 6
STARTS_ROUND1 = 16
PRODUCTION = "produced_single_conformer"

PLAN_FIELDS = ("record_id", "mol_id", "name", "state", "charge", "multiplicity",
               "screen_level", "round0_identity", "round0_donor_contacts", "round0_li_o_ang",
               "round0_core_hours", "motif_classes_to_enumerate", "starts_round1", "keep_lowest",
               "max_keep", "production_start_kind", "production_leg_status", "motif_screen_status",
               "note")
ACC_FIELDS = ("check_id", "description", "ok", "detail")


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


def donor_class(identity):
    for token in ("carbonyl", "ether", "sulfone", "sulfoxide", "nitrile", "phosphoryl"):
        if token in identity:
            return token
    return "unknown"


def build():
    pilot = {row["record_id"]: row for row in read_csv(PILOT_LI)}
    sampling = read_json(SAMPLING_INDEX)
    registered = {(row["mol_id"], row["state"]): row for row in read_csv(PRODUCTION_LEDGER)}

    sampling_status = {(entry["mol_id"], entry["state"]): entry for entry in sampling["li_motif_sampling"]}

    plan_rows = []
    for mol_id, name in MOLS:
        for state in LI_STATES:
            key = "%s|%s" % (mol_id, state)
            evidence = pilot.get(key, {})
            identity = evidence.get("identity", "")
            klass = donor_class(identity)
            contacts = evidence.get("donor_contacts", "")
            core_hours = 0.0
            if evidence:
                core_hours = float(evidence["cores"]) * float(evidence["wall_sec"]) / 3600.0
            leg = registered.get((mol_id, state))
            plan_rows.append({
                "record_id": key,
                "mol_id": mol_id, "name": name, "state": state,
                "charge": evidence.get("charge", ""),
                "multiplicity": evidence.get("multiplicity", ""),
                "screen_level": SCREEN_LEVEL,
                "round0_identity": identity,
                "round0_donor_contacts": contacts,
                "round0_li_o_ang": evidence.get("li_o_ang", ""),
                "round0_core_hours": ("%.6f" % core_hours) if evidence else "",
                "motif_classes_to_enumerate": (
                    "monodentate %s (the round-0 class) plus every bidentate pair formed by donor atoms of "
                    "this molecule whose donor-donor distance allows a Li bridge; enumerate from this state's "
                    "own connectivity, never from the other Li state" % klass),
                "starts_round1": str(STARTS_ROUND1),
                "keep_lowest": str(KEEP_LOWEST),
                "max_keep": str(MAX_KEEP),
                "production_start_kind": "single_frozen_motif",
                "production_leg_status": "computed" if leg else "not_computed",
                "motif_screen_status": "not_computed",
                "note": ("round-0 evidence is the registered Li pilot single point for this exact leg; the "
                         "production leg still starts from one frozen geometry, so the motif ensemble is "
                         "registered here rather than claimed"),
            })

    mother_vs_oxidised = sorted({row["name"] for row in plan_rows
                                 if any(other["name"] == row["name"]
                                        and other["state"] != row["state"]
                                        and other["round0_identity"] != row["round0_identity"]
                                        for other in plan_rows)})
    pilot_core_hours = sum(float(row["round0_core_hours"] or 0.0) for row in plan_rows)
    round0_registered = sum(1 for row in plan_rows if row["round0_identity"])
    screening_untouched = all(entry["status"] == "not_computed"
                              for entry in sampling["li_motif_sampling"])

    checks = [
        {"check_id": "covers_every_li_leg_of_the_four_molecule_subcohort",
         "description": "覆盖四分子分母 x 两个 Li 态 = 8 条腿",
         "ok": len(plan_rows) == len(MOLS) * len(LI_STATES),
         "detail": "%d legs = %d molecules x %d Li states" % (len(plan_rows), len(MOLS), len(LI_STATES))},
        {"check_id": "mother_and_oxidised_states_are_screened_separately",
         "description": "母态与氧化态各自构造、各自筛选，计划里是独立两行",
         "ok": all(len([row for row in plan_rows if row["mol_id"] == mol_id]) == len(LI_STATES)
                   for mol_id, _ in MOLS),
         "detail": "两条 Li 态在每条腿上都单列，构造规则写明从该态自己的连通性出发"},
        {"check_id": "single_motif_propagation_is_prohibited",
         "description": "禁止把一个 Li 态的优化结构当作另一个 Li 态的起点",
         "ok": all("never from the other Li state" in row["motif_classes_to_enumerate"]
                   for row in plan_rows),
         "detail": "8/8 rows carry the prohibition; production_start_kind=single_frozen_motif is "
                   "registered as a caveat, not as an ensemble"},
        {"check_id": "motif_switching_is_documented_from_the_pilot",
         "description": "母态与氧化态 motif 会切换这一点有已登记证据（不是假设）",
         "ok": bool(mother_vs_oxidised),
         "detail": "round-0 pilot identities differ between the two Li states for: %s"
                   % (", ".join(mother_vs_oxidised) or "none")},
        {"check_id": "round0_evidence_is_taken_from_the_registered_pilot",
         "description": "round-0 身份/给体接触数取自已登记的 Li pilot 单点，逐条对得上 record_id",
         "ok": round0_registered == len(plan_rows),
         "detail": "%d/%d legs have a registered round-0 identity from "
                   "outputs/physics_completion/free_states/pilot_li_state_energies.csv"
                   % (round0_registered, len(plan_rows))},
        {"check_id": "screen_level_is_cheap_and_labelled_as_a_screen",
         "description": "筛选层是廉价气相 GFN2-xTB，且显式标注为筛选而非生产级自由能",
         "ok": all(row["screen_level"] == SCREEN_LEVEL for row in plan_rows),
         "detail": SCREEN_LEVEL},
        {"check_id": "keep_three_independent_motifs_with_registered_escalation",
         "description": "每腿保留最多 3 个独立 motif，3 -> 6 只在敏感性触发时按同一规则扩",
         "ok": all(row["keep_lowest"] == str(KEEP_LOWEST) and row["max_keep"] == str(MAX_KEEP)
                   for row in plan_rows),
         "detail": "keep_lowest=%d, max_keep=%d on every leg" % (KEEP_LOWEST, MAX_KEEP)},
        {"check_id": "stop_rule_is_registered",
         "description": "两轮筛选仍不解析即报 sampling_limited / unresolved",
         "ok": True,
         "detail": "stop rule registered in selection_rule.json / selection_rule.md"},
        {"check_id": "budget_uses_the_measured_li_pilot_cost",
         "description": "预算不靠廉价单点外推：引用已实测的 Li pilot 成本与每腿起点数",
         "ok": pilot_core_hours > 0 and all(row["starts_round1"] == str(STARTS_ROUND1) for row in plan_rows),
         "detail": "8 legs measured round-0 core-hours = %.6f (sum of cores x wall over the 8 Li pilot "
                   "single points); round-1 starts per leg = %d" % (pilot_core_hours, STARTS_ROUND1)},
        {"check_id": "nothing_is_claimed_computed_yet",
         "description": "本层只登记规则与证据：motif 筛选一条都没跑，采样层占位仍为 not_computed",
         "ok": all(row["motif_screen_status"] == "not_computed" for row in plan_rows) and screening_untouched,
         "detail": "8/8 motif screens not_computed; sampling_index li_motif_sampling untouched"},
    ]
    n_failed = sum(0 if item["ok"] else 1 for item in checks)

    rule = {
        "scope": ("plan 6.1 / execution step 3: pre-registration of the Li coordination-motif screen for the "
                  "four-molecule subcohort (zero new electronic structure)"),
        "registered_before_any_motif_screen": True,
        "frozen_inputs": {
            "li_pilot_single_points": "outputs/physics_completion/free_states/pilot_li_state_energies.csv",
            "sampling_index": "outputs/physics_completion/sampling/sampling_index.json",
            "production_ledger": "outputs/physics_completion/free_states/production_ledger.csv",
        },
        "selection_rule": [
            "object = the four-molecule subcohort (DMC / EMC / GBL / SL) x the two Li states LiM_plus / LiM_2plus",
            "each leg is constructed from its own charge and multiplicity; the two Li states are never chained",
            "candidates = monodentate placements on the round-0 donor class plus bidentate pairs whose donor-donor "
            "distance allows a Li bridge, layered with the state's own conformer seeds",
            "screen level = gas-phase GFN2-xTB (a screen, never a production free energy)",
            "deduplicate by coordination mode and heavy-atom RMSD / torsion; keep the lowest 3 independent motifs",
            "extend 3 -> 6 only if the key-pair Li rung is sensitive to the motif choice; the escalation is "
            "registered in advance, never decided from the outcome",
            "stop rule = after two screen rounds without resolution report sampling_limited / unresolved",
            "only one selected representative motif enters the DFT single-conformer production leg; the other "
            "independent motifs stay registered for the 3 -> 6 expansion",
        ],
        "prohibited": ["propagating one Li state's optimised structure to the other Li state",
                       "treating the single frozen production start geometry as a motif ensemble",
                       "calling the gas-phase screen a production free energy",
                       "widening the window to obtain a preferred motif"],
        "evidence": {
            "round0_li_pilot_single_points": round0_registered,
            "motif_switching_between_the_two_li_states": mother_vs_oxidised,
            "measured_core_hours_for_the_8_li_legs": round(pilot_core_hours, 6),
            "kernel": ("the round-0 pilot already shows the motif changes between the two Li states, so "
                       "assuming transfer would be contradicted by registered evidence"),
        },
        "budget": {"legs": len(plan_rows), "starts_round1_per_leg": STARTS_ROUND1,
                   "keep_lowest": KEEP_LOWEST, "max_keep": MAX_KEEP,
                   "level": SCREEN_LEVEL},
        "production_start_kind": "single_frozen_motif",
        "motif_screen_status": "not_computed",
        "plan": plan_rows,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": n_failed,
    }

    md = [
        "# 方案 6.1 / 执行第 3 步：四分子 Li 配位 motif 采样预注册",
        "",
        "> 由 `scripts/wp_production/build_li_motif_sampling_plan.py` 生成；**零新增电子结构计算**。",
        "> 规则在任何 motif 筛选跑出结果之前登记，不随后续结果修改。",
        "",
        "## 为什么必须先冻结这条规则",
        "",
        "方案 6.1 要求带电态补独立种子、且 motif 切换时重新检查电子身份与连接关系。"
        "已登记的 round-0 pilot 单点直接给出了证据：",
        "",
        "| 分子 | LiM_plus 身份 | LiM_2plus 身份 |",
        "| --- | --- | --- |",
    ]
    for mol_id, name in MOLS:
        a = next(row for row in plan_rows if row["mol_id"] == mol_id and row["state"] == "LiM_plus")
        b = next(row for row in plan_rows if row["mol_id"] == mol_id and row["state"] == "LiM_2plus")
        md.append("| %s | %s | %s |" % (name, a["round0_identity"] or "-", b["round0_identity"] or "-"))
    md += [
        "",
        "即：**同一分子的两个 Li 态 motif 并不总是同一个**（上表差异即为证），"
        "而生产 Li 腿目前各自只从**一个冻结几何**起步（`n_conformers = 1`，`production_start_kind = "
        "single_frozen_motif`）。因此本层登记 motif 系综的选取规则，不宣称 motif 采样已完成。",
        "",
        "## 冻结的选取规则",
        "",
    ]
    for item in rule["selection_rule"]:
        md.append("* %s" % item)
    md += [
        "",
        "## 作业计划（%d 条腿，逐条登记）" % len(plan_rows),
        "",
        "| 记录 | 分子 | 态 | q/m | round-0 身份 | 给体接触 | Li–O (Å) | round-0 实测 core-hour | "
        "round-1 起点 | 保留 | 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in plan_rows:
        md.append("| %s | %s | %s | %s/%s | %s | %s | %s | %s | %s | %s | %s |"
                  % (row["record_id"], row["name"], row["state"], row["charge"], row["multiplicity"],
                     row["round0_identity"] or "-", row["round0_donor_contacts"] or "-",
                     row["round0_li_o_ang"] or "-", row["round0_core_hours"] or "-",
                     row["starts_round1"], row["keep_lowest"], row["motif_screen_status"]))
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
        "* 本层**没有跑任何 motif 筛选**：8 条腿全部 `motif_screen_status = not_computed`，"
        "`outputs/physics_completion/sampling/sampling_index.json` 的 `li_motif_sampling` 占位也保持不变。",
        "* round-0 身份/给体接触数逐条取自已登记的 Li pilot 单点，不是推断；其成本为重测值（cores x wall）。",
        "* 生产级 Li 腿仍是单代表 motif：本层只登记「系综该怎么做、怎么做才算不违规」。",
        "",
    ]

    files = {
        "outputs/physics_completion/li_motif_sampling/selection_rule.json": dump(rule),
        "outputs/physics_completion/li_motif_sampling/selection_rule.md": "\n".join(md),
        "outputs/physics_completion/li_motif_sampling/motif_plan.csv": csv_text(PLAN_FIELDS, plan_rows),
        "outputs/physics_completion/li_motif_sampling/acceptance.csv": csv_text(ACC_FIELDS, checks),
    }
    meta = {"files": len(files), "legs": len(plan_rows), "checks": len(checks), "failed": n_failed,
            "pilot_core_hours": pilot_core_hours, "switching": mother_vs_oxidised}
    return files, meta


def main(argv=None):
    parser = argparse.ArgumentParser(description="Register the plan-6.1 Li coordination-motif screen.")
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
        print("CHECK OK -- %d Li-motif-plan files are byte-identical" % len(files))
        return 0

    for rel, text in sorted(files.items()):
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    print("wp2 Li coordination-motif sampling plan (plan 6.1 / step 3)")
    print("-" * 70)
    print("  files      : %d" % meta["files"])
    print("  legs       : %d" % meta["legs"])
    print("  motif switching documented for: %s" % (", ".join(meta["switching"]) or "none"))
    print("  measured round-0 pilot cost: %.6f core-hour" % meta["pilot_core_hours"])
    print("  acceptance : %d checks / %d failed" % (meta["checks"], meta["failed"]))
    return 0 if meta["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())