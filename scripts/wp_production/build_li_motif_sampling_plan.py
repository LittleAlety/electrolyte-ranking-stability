# -*- coding: utf-8 -*-
"""方案 6.1 / 执行第 3 步：主集分子 Li 配位 motif 采样的结果前预注册（零新增电子结构计算）。

方案 6.1 明确要求：「不同电荷态各自采样。除母态构象传播外，应对带电态补独立种子/扭转结构，
不能假定母态最低构象就覆盖其搜索空间。motif 能切换，电子身份与连接关系必须重新检查。」

现状（本脚本只读登记，不改数）：
* 生产 Li 腿（LiM_plus / LiM_2plus）目前各自从**一个冻结几何**起步，
  即 n_conformers = 1 的单代表 motif，不是 motif 系综；
* 分子集不是硬编码的四分子，而是**从冻结的 data/metadata/physics_completion_set.csv 的
  in_main=true 集合推导**（12 个主集分子），每个分子两个 Li 态 = 24 条腿；
* 24 条 Li 态 pilot 单点已登记（outputs/physics_completion/free_states/pilot_li_state_energies.csv），
  其中 **SL 的 LiM_plus 是 bidentate、LiM_2plus 是 monodentate** —— 直接证明 motif 会在母态与氧化态之间切换，
  因此「传播一个母态结构」在本批次是被证据否证的默认做法。

冻结的规则（先写规则、后看结果）
--------------------------------
1. 对象 = physics_completion_set.csv 的 in_main 分子集（12 个）x 两个 Li 态（LiM_plus / LiM_2plus）= 24 条腿；
2. 每条腿**独立构造**候选 motif：从该态自己的电荷/多重度出发，枚举该分子可达给体集合上的
   单齿（round-0 类别）与双齿（给体间距允许 Li 桥接者）配位位置，再叠加母态构象种子；
   禁止把 LiM_plus 的优化结构直接当作 LiM_2plus 或多聚 motif 的起点；
3. 先用廉价气相 GFN2-xTB 筛选（筛不是生产级自由能）；去重按配位模式 + 重原子 RMSD / 扭转角；
   每腿保留最多 3 个独立低能 motif（资源规则，不是已证收敛尺度）；
4. 只有关键 pair 的 Li 台阶对 motif 选择敏感时，才按同一规则靶向扩到 6（升级登记待判，不按结果事后决定）；
5. 停止规则：两轮筛选后仍不能解析 → 报 sampling_limited / unresolved，不继续加算；
6. 生产级后续只把**选定的一条代表 motif** 送进 DFT 单构象腿，其余独立 motif 登记在案以备 3 -> 6 展开。

登记纪律
--------
`screen_parent_current` / `production_leg_status` / `motif_screen_status` / `screen_verdict` 逐腿取自
**已登记的运行记录**：没有记录的腿保持 `not_computed` 且结论字段留空，绝不默认通过；
有记录的腿必须与记录逐字一致（present+kept -> computed，present+无保留 -> unresolved）。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_li_motif_sampling_plan.py
    .venv\\Scripts\\python.exe scripts\\build_li_motif_sampling_plan.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PC = REPO / "outputs" / "physics_completion"
PILOT_LI = PC / "free_states" / "pilot_li_state_energies.csv"
SAMPLING_INDEX = PC / "sampling" / "sampling_index.json"
PRODUCTION_LEDGER = PC / "free_states" / "production_ledger.csv"
PHYSICS_SET = REPO / "data" / "metadata" / "physics_completion_set.csv"
OUT = PC / "li_motif_sampling"


def _read_csv_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _main_cohort_molecules():
    """(mol_id, name) of the frozen in_main set, in the frozen file order.

    The molecule list is *derived* from the registered cohort definition instead
    of being transcribed into this script: a second hard-coded copy is exactly
    how the previous four-molecule list would drift away from the plan.
    """
    pairs = []
    for row in _read_csv_rows(PHYSICS_SET):
        if row.get("in_main", "").strip().lower() != "true":
            continue
        pair = (row["mol_id"], row["name"])
        if pair not in pairs:
            pairs.append(pair)
    if not pairs:
        raise SystemExit("no in_main molecule found in " + str(PHYSICS_SET))
    return tuple(pairs)


MOLS = _main_cohort_molecules()
LI_STATES = ("LiM_plus", "LiM_2plus")
SCREEN_LEVEL = "xTB GFN2 (gas phase) coordination-motif screen"
KEEP_LOWEST = 3
MAX_KEEP = 6
STARTS_ROUND1 = 16
PRODUCTION = "produced_single_conformer"
SCREEN_JSON = OUT / "li_motif_screen.json"
SCREEN_CSV = OUT / "li_motif_screen.csv"
SCREEN_OUTPUTS = (
    "outputs/physics_completion/li_motif_sampling/li_motif_screen.csv",
    "outputs/physics_completion/li_motif_sampling/li_motif_screen.json",
    "outputs/physics_completion/li_motif_sampling/li_motif_screen.md",
)
#: Outputs owned by the ROUND-2 layers (`build_li_motif_plan_round2.py` and
#: `run_li_motif_round2.py`).  This layer neither writes nor verifies them; they
#: are listed so the stray check does not claim another layer's files (and so it
#: never suggests deleting them).
ROUND2_OUTPUTS = (
    "outputs/physics_completion/li_motif_sampling/li_motif_plan_round2.csv",
    "outputs/physics_completion/li_motif_sampling/li_motif_plan_round2_index.json",
    "outputs/physics_completion/li_motif_sampling/li_motif_round2_exec.csv",
    "outputs/physics_completion/li_motif_sampling/li_motif_round2_exec.md",
    "outputs/physics_completion/li_motif_sampling/li_motif_round2_exec_index.json",
)

PLAN_FIELDS = ("record_id", "mol_id", "name", "state", "charge", "multiplicity",
               "screen_level", "round0_identity", "round0_donor_contacts", "round0_li_o_ang",
               "round0_core_hours", "motif_classes_to_enumerate", "starts_round1", "keep_lowest",
               "max_keep", "production_start_kind", "production_leg_status", "motif_screen_status",
               "screen_kept_motifs", "screen_verdict", "screen_parent_current",
               "note")
ACC_FIELDS = ("check_id", "description", "ok", "detail")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def screen_parent_current(entry):
    """Is the geometry the screen was run on still the geometry on disk?"""
    parent = REPO / entry["parent_path"]
    if not parent.is_file():
        return "parent_missing"
    return "true" if sha256_file(parent) == entry["parent_sha256"] else "stale_parent_changed"


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
    screen = read_json(SCREEN_JSON) if SCREEN_JSON.is_file() else None
    screen_legs = {entry["record_id"]: entry for entry in (screen or {}).get("legs", [])}

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
            screen_leg = screen_legs.get(key)
            # 逐腿如实登记：没有运行记录条目的腿保持 not_computed，结论字段留空。
            # 绝不用「计划里有这一行」冒充「已经算过」。
            if screen_leg is None:
                screen_status = "not_computed"
            elif screen_leg["kept"]:
                screen_status = "computed"
            else:
                screen_status = "unresolved"
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
                "motif_screen_status": screen_status,
                "screen_kept_motifs": "" if screen_leg is None else str(len(screen_leg["kept"])),
                "screen_verdict": "" if screen_leg is None else screen_leg["verdict"],
                "screen_parent_current": "" if screen_leg is None else screen_parent_current(screen_leg),
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
    screen_legs_out = sum(1 for row in plan_rows if row["motif_screen_status"] != "not_computed")
    screen_legs_computed = sum(1 for row in plan_rows if row["motif_screen_status"] == "computed")
    screen_stale = [row["record_id"] for row in plan_rows
                    if row["screen_parent_current"] not in ("", "true")]

    # 逐腿复算运行记录的回显：有记录的腿必须与记录逐字一致，没记录的腿必须留空。
    def _expected(row):
        entry = screen_legs.get(row["record_id"])
        if entry is None:
            return ("not_computed", "", "", "")
        status = "computed" if entry["kept"] else "unresolved"
        return (status, str(len(entry["kept"])), entry["verdict"], screen_parent_current(entry))

    misregistered = [
        row["record_id"] for row in plan_rows
        if (row["motif_screen_status"], row["screen_kept_motifs"], row["screen_verdict"],
            row["screen_parent_current"]) != _expected(row)
    ]
    record_ids = set(screen_legs)
    plan_ids = {row["record_id"] for row in plan_rows}
    stray_record_legs = sorted(record_ids - plan_ids)
    # sampling_index 是另一个登记处（由 build_physics_completion_batch.py 写）；它声称 computed 的腿
    # 必须有本层的运行记录条目，否则两个登记处互相矛盾。
    sampling_claims_without_record = sorted(
        "%s|%s" % (mol_id, state) for (mol_id, state), entry in sampling_status.items()
        if entry.get("status") == "computed" and "%s|%s" % (mol_id, state) not in record_ids
    )

    checks = [
        {"check_id": "covers_every_li_leg_of_the_main_cohort",
         "description": "覆盖 physics_completion_set.csv 的 in_main 分子集（12 个）x 两个 Li 态 = 24 条腿",
         "ok": (len(plan_rows) == len(MOLS) * len(LI_STATES)
                and {row["record_id"] for row in plan_rows}
                == {"%s|%s" % (mol_id, state) for mol_id, _ in MOLS for state in LI_STATES}),
         "detail": "%d legs = %d in_main molecules x %d Li states" % (len(plan_rows), len(MOLS), len(LI_STATES))},
        {"check_id": "mother_and_oxidised_states_are_screened_separately",
         "description": "母态与氧化态各自构造、各自筛选，计划里是独立两行",
         "ok": all(len([row for row in plan_rows if row["mol_id"] == mol_id]) == len(LI_STATES)
                   for mol_id, _ in MOLS),
         "detail": "两条 Li 态在每条腿上都单列，构造规则写明从该态自己的连通性出发"},
        {"check_id": "single_motif_propagation_is_prohibited",
         "description": "禁止把一个 Li 态的优化结构当作另一个 Li 态的起点",
         "ok": all("never from the other Li state" in row["motif_classes_to_enumerate"]
                   for row in plan_rows),
         "detail": "%d/%d rows carry the prohibition; production_start_kind=single_frozen_motif is "
                   "registered as a caveat, not as an ensemble" % (len(plan_rows), len(plan_rows))},
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
         "detail": "%d legs measured round-0 core-hours = %.6f (sum of cores x wall over the Li pilot "
                   "single points); round-1 starts per leg = %d"
                   % (len(plan_rows), pilot_core_hours, STARTS_ROUND1)},
        {"check_id": "screen_claims_match_the_run_record",
         "description": "逐腿回显运行记录：有记录的腿与 li_motif_screen.json 逐字一致，没记录的腿必须是 "
                        "not_computed 且结论字段留空（不许默认通过）；记录里不许出现计划外的腿",
         "ok": not misregistered and not stray_record_legs,
         "detail": ("no run record: %d/%d not_computed" % (len(plan_rows), len(plan_rows))
                    if screen is None else
                    "run record present: %d/%d legs carry an outcome (%d computed, %d unresolved); "
                    "%d leg(s) without a record stay not_computed; stray record legs: %s"
                    % (screen_legs_out, len(plan_rows), screen_legs_computed,
                       screen_legs_out - screen_legs_computed, len(plan_rows) - screen_legs_out,
                       ", ".join(stray_record_legs) or "none"))},
        {"check_id": "sampling_index_does_not_claim_a_leg_this_layer_never_screened",
         "description": "sampling_index.json 声称 computed 的腿必须有本层运行记录条目，两个登记处不许互相矛盾",
         "ok": not sampling_claims_without_record,
         "detail": ("all sampling_index computed claims are backed by a run-record leg"
                    if not sampling_claims_without_record else
                    "claims without a run record: " + ", ".join(sampling_claims_without_record))},
        {"check_id": "screen_parent_geometries_are_current",
         "description": "筛选所用父几何与登记一致；生产腿重跑后必须重跑筛选（重跑约 30 秒）",
         "ok": not screen_stale,
         "detail": ("no run record yet" if screen is None else (
             "all %d screened parents unchanged" % screen_legs_out if not screen_stale
             else "stale parent geometry for: " + ", ".join(screen_stale)))},
        {"check_id": "uncomputed_legs_are_registered_as_uncomputed",
         "description": "筛选进度如实登记：未算的腿只报 not_computed 且结论字段留空，不冒充 computed",
         "ok": all((row["motif_screen_status"] == "not_computed")
                   == (row["screen_verdict"] == "" and row["screen_kept_motifs"] == ""
                       and row["screen_parent_current"] == "")
                   for row in plan_rows),
         "detail": "%d/%d legs carry a run-record outcome; the remaining %d stay not_computed "
                   "(re-run scripts/wp_production/screen_li_motifs.py to close the gap)"
                   % (screen_legs_out, len(plan_rows), len(plan_rows) - screen_legs_out)},
    ]
    n_failed = sum(0 if item["ok"] else 1 for item in checks)

    rule = {
        "scope": ("plan 6.1 / execution step 3: pre-registration of the Li coordination-motif screen for the "
                  "main cohort (physics_completion_set.csv in_main = %d molecules x %d Li states = %d legs; "
                  "zero new electronic structure)" % (len(MOLS), len(LI_STATES), len(plan_rows))),
        "registered_before_any_motif_screen": True,
        "cohort_source": "data/metadata/physics_completion_set.csv (in_main = true)",
        "frozen_inputs": {
            "li_pilot_single_points": "outputs/physics_completion/free_states/pilot_li_state_energies.csv",
            "sampling_index": "outputs/physics_completion/sampling/sampling_index.json",
            "production_ledger": "outputs/physics_completion/free_states/production_ledger.csv",
            "cohort_definition": "data/metadata/physics_completion_set.csv",
        },
        "selection_rule": [
            "object = the %d in_main molecules of physics_completion_set.csv x the two Li states "
            "LiM_plus / LiM_2plus = %d legs" % (len(MOLS), len(plan_rows)),
            "the molecule list is derived from the frozen cohort file, never transcribed into this script",
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
                       "widening the window to obtain a preferred motif",
                       "reporting an unscreened leg as computed (uncomputed legs stay not_computed)"],
        "evidence": {
            "round0_li_pilot_single_points": round0_registered,
            "motif_switching_between_the_two_li_states": mother_vs_oxidised,
            "measured_core_hours_for_the_%d_li_legs" % len(plan_rows): round(pilot_core_hours, 6),
            "kernel": ("the round-0 pilot already shows the motif changes between the two Li states, so "
                       "assuming transfer would be contradicted by registered evidence"),
        },
        "budget": {"legs": len(plan_rows), "starts_round1_per_leg": STARTS_ROUND1,
                   "keep_lowest": KEEP_LOWEST, "max_keep": MAX_KEEP,
                   "level": SCREEN_LEVEL},
        "production_start_kind": "single_frozen_motif",
        "motif_screen_status": "computed" if screen_legs_computed == len(plan_rows) else "not_computed",
        "screen_executor": "scripts/wp_production/screen_li_motifs.py",
        "screen_run_record": ("outputs/physics_completion/li_motif_sampling/li_motif_screen.json"
                              if screen is not None else ""),
        "screen_legs_computed": screen_legs_computed,
        "screen_legs_with_an_outcome": screen_legs_out,
        "plan": plan_rows,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": n_failed,
    }

    md = [
        "# 方案 6.1 / 执行第 3 步：主集 Li 配位 motif 采样预注册",
        "",
        "> 由 `scripts/wp_production/build_li_motif_sampling_plan.py` 生成；**零新增电子结构计算**。",
        "> 规则在任何 motif 筛选跑出结果之前登记，不随后续结果修改。",
        "> 对象 = `data/metadata/physics_completion_set.csv` 的 `in_main` 分子集（%d 个）x 两个 Li 态 = %d 条腿。"
        % (len(MOLS), len(plan_rows)),
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
        "round-1 起点 | 保留 | 筛选状态 | 筛选保留 motif |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in plan_rows:
        md.append("| %s | %s | %s | %s/%s | %s | %s | %s | %s | %s | %s | %s | %s |"
                  % (row["record_id"], row["name"], row["state"], row["charge"], row["multiplicity"],
                     row["round0_identity"] or "-", row["round0_donor_contacts"] or "-",
                     row["round0_li_o_ang"] or "-", row["round0_core_hours"] or "-",
                     row["starts_round1"], row["keep_lowest"], row["motif_screen_status"],
                     row["screen_kept_motifs"] or "-"))
    screen_summary = []
    if screen is not None:
        screen_summary = [
            "",
            "## 已执行的筛选结果（运行记录 li_motif_screen.json）",
            "",
            "| 记录 | 起点数 | 成功 | 保留 motif | 判定 | 最低 motif |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in plan_rows:
            entry = screen_legs.get(row["record_id"])
            if entry is None:
                continue
            lowest = entry["kept"][0]["_motif_class"] if entry["kept"] else "-"
            screen_summary.append("| %s | %d | %d | %d | %s | %s |" % (
                row["record_id"], entry["n_sites"], entry["n_ok"], len(entry["kept"]), entry["verdict"], lowest))
        screen_summary += ["", "> 筛选层是气相 GFN2-xTB，不是生产自由能；保留结构的几何路径见 li_motif_screen.md。",
                           "> 本次运行记录覆盖 %d/%d 条腿；其余 %d 条腿保持 `not_computed`，等执行器重跑后补齐。"
                           % (screen_legs_out, len(plan_rows), len(plan_rows) - screen_legs_out), ""]
    md += screen_summary
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
        "* 本层只登记规则；筛选由 `scripts/wp_production/screen_li_motifs.py` 执行，运行记录写在"
        "`outputs/physics_completion/li_motif_sampling/li_motif_screen.json`。没有运行记录条目的腿仍是"
        "`motif_screen_status = not_computed`；有记录条目的腿逐条写 computed / unresolved，并核对父几何是否已被重跑。",
        "* round-0 身份/给体接触数逐条取自已登记的 Li pilot 单点，不是推断；其成本为重测值（cores x wall）。",
        "* 分子集从冻结的 `physics_completion_set.csv` 的 `in_main` 集合推导，不在本脚本里另抄一份。",
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
            "pilot_core_hours": pilot_core_hours, "switching": mother_vs_oxidised,
            "screen_expected": screen is not None, "screen_legs_out": screen_legs_out}
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
        for rel in sorted(SCREEN_OUTPUTS):
            if not (REPO / rel).is_file() and meta["screen_expected"]:
                failures.append("missing %s" % rel)
        if OUT.is_dir():
            for path in sorted(OUT.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(REPO).as_posix()
                    if rel not in files and rel not in SCREEN_OUTPUTS \
                            and rel not in ROUND2_OUTPUTS:
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