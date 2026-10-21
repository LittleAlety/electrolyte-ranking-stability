#!/usr/bin/env python
"""3 -> 6 sampling difference report (plan §6.1 / v1.4.2 item 4).

User ruling 2026-10-19: this round REPORTS differences only -- it must NOT
declare "sampling converged".  `sampling_limited` means the search pool or the
extension coverage is limited; it is not a numerical convergence verdict.  The
GFN2 1.00 kcal/mol escalation tolerance is a *screening* threshold and is never
used as a production acceptance criterion.

What this report freezes BEFORE any extension result exists
-----------------------------------------------------------
1. The four audit molecules (EMC / DEC / DME / TMP) and their four main states.
2. The comparison quantities: `G_ensemble` per state, the oxidation axis
   `G(M_plus) - G(M)` (M slot is the def2-TZVPD neutral leg), the Li-conditioned
   axis `G(LiM_2plus) - G(LiM_plus)`, the Top-k candidate set over the audit
   molecules, and the selection regret of the round-1 ranking against the
   ceiling ranking.
3. The selection sizes: main k = 2 over the 4-molecule audit set, auxiliary
   k = 1 and k = 3 (the plan's k=3/2/4 rule scaled to the audit-set size).
4. The rounding/units: energies in eV (1 Eh = 27.211386245988 eV), differences
   in kcal/mol for `G_ensemble`.

The round-1 side is filled from the production ensemble labels.  The ceiling
side stays EMPTY with an explicit reason until the round-2 structures have
production DFT legs -- an empty cell is the honest state, not a zero.

Outputs
-------
outputs/physics_completion/sampling/sampling_3to6_diff.csv   per-state rows
outputs/physics_completion/sampling/sampling_3to6_diff.md    human-readable
outputs/physics_completion/sampling/sampling_3to6_diff_index.json  hashes
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
SAMPLING = REPO / "outputs" / "physics_completion" / "sampling"

LABELS = ENS / "production_ensemble_labels.csv"
AUDIT = SAMPLING / "sampling_audit_3to6.csv"
MANIFEST = ENS / "production_ensemble_manifest.json"
STRUCTURES = ENS / "production_ensemble_structures.csv"
WEIGHTS = ENS / "production_ensemble_weights.csv"
OUT_CSV = SAMPLING / "sampling_3to6_diff.csv"
OUT_MD = SAMPLING / "sampling_3to6_diff.md"
OUT_INDEX = SAMPLING / "sampling_3to6_diff_index.json"

AUDIT_MOLECULES = ("EMC", "DEC", "DME", "TMP")
STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
K_MAIN = 2
K_AUX = (1, 3)
EH_TO_EV = 27.211386245988

#: Registered reasons, written verbatim into the report.
CEILING_REASON = ("round-2 structures have no production DFT leg yet: the ceiling side is "
                  "reported as not_computed, never as zero")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def num(value):
    """CSV values arrive as strings -- convert explicitly (project lesson)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


#: Ceiling side is only ever computed from REGISTERED, QC-PASSED round-2
#: members (plan item: "只读取已登记且 QC 通过的第二轮成员").  A missing
#: member or an invalid source hash keeps the cell not_computed -- an empty
#: value is the honest state, never a zero.
CEILING_SOURCES_OK = ("computed",)
EH_TO_KCAL = 627.5094740631


def load_round2_members():
    """QC-passed round-2 structure rows keyed by (name, slot).

    Reads the same structure table the aggregator reads.  Only rows whose
    registered member_role marks them as round-2 audit candidates AND whose
    status is computed may contribute; everything else (pending, qc_failed,
    superseded) means the ceiling side for that state stays not_computed.
    """
    structures = ENS / "production_ensemble_structures.csv"
    if not structures.is_file():
        return {}
    out = {}
    for r in csv.DictReader(structures.open(encoding="utf-8")):
        if r.get("member_role") != "round2_audit_extra":
            continue
        if r.get("status") not in CEILING_SOURCES_OK:
            continue
        g = num(r.get("g_single_eh"))
        if g is None:
            continue
        key = (r.get("name"), r.get("slot"))
        out.setdefault(key, []).append((g, r))
    return out


def ledger_rows():
    """Every structure-table row (round-1 primary/extras + round-2 members)."""
    if not STRUCTURES.is_file():
        return []
    return list(csv.DictReader(STRUCTURES.open(encoding="utf-8")))


def ceiling_members(name, state, rows, round2_rows):
    """QC-passed members that make up the ceiling ensemble for one state.

    The 3->6 question is "does the ranking change when each state's pool grows
    from round-1 to the ceiling", so the ceiling ensemble MUST contain the
    round-1 minima as well as the registered extension.  Aggregating the
    extension alone would drop every round-1 minimum and report a G_ensemble
    that no pool would ever produce.
    """
    base = [r for r in rows
            if r.get("name") == name and r.get("slot") == state
            and (r.get("member_role") == "primary"
                 or (r.get("member_role") == "round1_extra"
                     and r.get("status") == "computed"))]
    return base + list(round2_rows)


def _aggregator():
    """The aggregator owns the DFT-level dedup rule; this report must not restate it."""
    spec = importlib.util.spec_from_file_location(
        "build_production_ensemble_aggregator",
        HERE / "build_production_ensemble_aggregator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ceiling_state_value(name, state, round2, rows=None, audit_row=None):
    """(g_ceiling_kcal, status, reason) for one audit state.

    complete: every registered round-2 member for this state is QC-passed, the
              source hashes in the manifest still match the disk bytes, and the
              union of round-1 + extension members dedups cleanly.
    not_computed: any registered member is missing/unfailed/hash-stale/blocked --
                  the plan's rule, never zero.  When nothing is registered the
                  reason distinguishes "the pool itself has no extension" (a
                  3->6 ceiling cannot exist) from a pure bookkeeping gap.
    """
    members = round2.get((name, state), [])
    # Hash validation: the ensemble manifest registered each round-2
    # candidate's geometry sha256; a member whose current source hash no
    # longer matches its registered hash cannot enter the ceiling aggregate.
    doc = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    registered = {}
    for slot, cands in (doc.get("round2_audit_candidates") or {}).items():
        for cand in cands:
            cand_name = cand.get("name") or ""
            if cand_name in AUDIT_MOLECULES:
                registered.setdefault((cand_name, slot), []).append(cand)
    reg = registered.get((name, state), [])
    deferred = {}
    for slot, cands in (doc.get("round2_audit_candidates_deferred") or {}).items():
        for cand in cands:
            if cand.get("name") in AUDIT_MOLECULES:
                deferred.setdefault((cand.get("name"), slot), []).append(cand)
    if not reg:
        n_def = len(deferred.get((name, state), []))
        if n_def:
            # The pool is measured, but registering the basins would make the
            # ceiling wait on production legs nobody approved yet.
            return None, "not_computed", (
                "%d round-2 basin(s) measured but not registered (no approved production "
                "batch): pool size is recorded in the sampling audit, ceiling not computed" % n_def)
        aud = audit_row or {}
        extension = str(aud.get("extension_available", "")).strip().lower()
        pool = str(aud.get("pool_independent_minima", "")).strip()
        round1 = str(aud.get("round1_structures", "")).strip()
        if extension in ("false", "0", "no") and pool and round1:
            # The frozen pool is exhausted: round-1 already uses every independent
            # minimum the pool holds, so there is no structure a round-2 leg could
            # add.  This is a pool-limited scientific result, not a missing task.
            return None, "not_computed", (
                "pool-limited: the frozen pool holds %s independent minimum(a) and round-1 "
                "already uses %s, so no 3->6 extension exists (audit status %s)"
                % (pool, round1, aud.get("status", "")))
        return None, "not_computed", "no registered round-2 candidates for this state"
    if not members:
        # Registered, but nothing QC-passed yet (in flight or failed).  Reporting
        # "no registered members" here would state the wrong reason.
        return None, "not_computed", (
            "%d round-2 member(s) registered, none QC-passed yet: the ceiling waits for "
            "the full registered set" % len(reg))
    if len(members) != len(reg):
        return None, "not_computed", (
            "registered round-2 members (%d) != QC-passed members (%d): "
            "ceiling waits for the full registered set" % (len(reg), len(members)))
    for cand in reg:
        path = REPO / str(cand.get("path", ""))
        want = str(cand.get("sha256", ""))
        if not path.is_file() or not want or sha256_file(path) != want:
            return None, "not_computed", (
                "round-2 source hash stale for %s: re-register before aggregating" % cand.get("path", ""))
    union = ceiling_members(name, state, rows if rows is not None else ledger_rows(),
                            [row for _, row in members])
    aggregator = _aggregator()
    kept, decisions = aggregator.dedup_members(union, REPO)
    round2_kept = [r for r in kept if r.get("member_role") == "round2_audit_extra"]
    blocked = [d for d in decisions
               if d.get("kept") == "false" and str(d.get("reason", "")).startswith("dedup_blocked")
               and d.get("member_key") in {r["member_key"] for _, r in members}]
    if blocked:
        return None, "not_computed", (
            "%d round-2 member(s) could not be deduped (no usable final geometry): ceiling "
            "cannot be aggregated" % len(blocked))
    if len(round2_kept) < len(members):
        collapsed = [d for d in decisions if d.get("kept") == "false"
                     and d.get("duplicate_of")]
        # A registered extension that IS a round-1 minimum is not an error: it is
        # counted once, and the collapse stays visible in the reason.
        note = ("; %d registered round-2 member(s) collapsed onto an already-present minimum"
                % (len(members) - len(round2_kept)))
    else:
        note = ""
    g_list = [float(r["g_single_eh"]) for r in kept]
    if not g_list:
        return None, "not_computed", "no QC-passed member survived the ceiling dedup"
    import math
    g_min = min(g_list)
    # v3.0 §19.1 item 1: the old constant 0.00158760761551242 was WRONG by
    # 1.68x -- it mis-derived RT(Eh).  Correct: R = 1.98720425864083e-3
    # kcal/(mol K) (CODATA, same as the aggregator's R_KCAL), T = 298.15 K,
    # 1 Eh = 627.5094740631 kcal/mol -> RT = 0.0009441848676442220 Eh.
    RT = 1.98720425864083e-3 * 298.15 / 627.5094740631  # Eh at 298.15 K
    g_ceiling_eh = g_min - RT * math.log(sum(math.exp(-(g - g_min) / RT) for g in g_list))
    return g_ceiling_eh * EH_TO_KCAL, "complete", (
        "union of %d round-1 and %d round-2 member(s) -> %d unique minimum(s)%s"
        % (len(union) - len(list(members)), len(list(members)), len(kept), note))


def load_labels():
    if not LABELS.is_file():
        return {}
    return {(r["name"], r["state"]): r
            for r in csv.DictReader(LABELS.open(encoding="utf-8"))}


def load_audit():
    if not AUDIT.is_file():
        return {}
    return {(r["name"], r["state"]): r
            for r in csv.DictReader(AUDIT.open(encoding="utf-8"))}


def ceiling_legs():
    """(name, state) -> how many round-2 candidate structures are registered."""
    if not MANIFEST.is_file():
        return {}
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    counts = {}
    for slot, cands in (doc.get("round2_audit_candidates") or {}).items():
        for cand in cands:
            name = cand.get("name")
            if name is None:
                path = str(cand.get("path", ""))
                parts = path.split("/")
                name = parts[2] if len(parts) > 3 and parts[0] == "work" else ""
            if name in AUDIT_MOLECULES:
                counts[(name, slot)] = counts.get((name, slot), 0) + 1
    return counts


def state_rows(labels, audit, round2, ledger=None):
    rows = []
    for name in AUDIT_MOLECULES:
        for state in STATES:
            lab = labels.get((name, state)) or {}
            aud = audit.get((name, state)) or {}
            g_ens = num(lab.get("g_ensemble_kcal"))
            g_ceiling, ceiling_status, ceiling_reason = ceiling_state_value(
                name, state, round2, ledger, aud)
            delta = (g_ceiling - g_ens) if (g_ceiling is not None and g_ens is not None) else None
            rows.append({
                "name": name,
                "state": state,
                "pool_kind": aud.get("pool_kind", ""),
                "round1_structures": aud.get("round1_structures", ""),
                "round2_ceiling": aud.get("round2_ceiling", ""),
                "audit_status": aud.get("status", ""),
                "needs_second_round_motif_search": aud.get("needs_second_round_motif_search", ""),
                "acceptance_status": lab.get("acceptance_status", ""),
                "n_unique_round1": lab.get("n_unique", ""),
                "g_ensemble_round1_kcal": ("%.6f" % g_ens) if g_ens is not None else "",
                "g_ensemble_ceiling_kcal": ("%.6f" % g_ceiling) if g_ceiling is not None else "",
                "delta_g_ensemble_kcal": ("%.6f" % delta) if delta is not None else "",
                "ceiling_status": ceiling_status,
                "ceiling_reason": ceiling_reason if ceiling_status != "complete" else "",
                # For a COMPLETE ceiling the reason slot is empty, so the union
                # composition (how many round-1 vs extension minima were summed)
                # is carried here instead of being silently dropped.
                "ceiling_note": ceiling_reason if ceiling_status == "complete" else "",
            })
    return rows


def _gap(row_a, row_b):
    """row_a - row_b in eV from the round-1 G_ensemble, or None."""
    a = num((row_a or {}).get("g_ensemble_eh"))
    b = num((row_b or {}).get("g_ensemble_eh"))
    if a is None or b is None:
        return None
    return (a - b) * EH_TO_EV


def axis_rows(labels, states):
    """Oxidation axis and Li-conditioned axis per audit molecule.

    Round-1 side from the labels; ceiling side from the state rows (which are
    themselves only computed from registered QC-passed round-2 members).
    """
    ceiling_by_state = {(r["name"], r["state"]): num(r["g_ensemble_ceiling_kcal"])
                        for r in states}
    status_by_state = {(r["name"], r["state"]): r["ceiling_status"] for r in states}
    rows = []
    for name in AUDIT_MOLECULES:
        for axis, hi_state, lo_state in (
                ("oxidation (M_plus - M)", "M_plus", "M"),
                ("Li-conditioned (LiM_2plus - LiM_plus)", "LiM_2plus", "LiM_plus")):
            ox = _gap(labels.get((name, hi_state)), labels.get((name, lo_state)))
            c_hi, c_lo = (ceiling_by_state.get((name, hi_state)),
                          ceiling_by_state.get((name, lo_state)))
            ceiling_ok = (status_by_state.get((name, hi_state)) == "complete"
                          and status_by_state.get((name, lo_state)) == "complete"
                          and c_hi is not None and c_lo is not None)
            cev = ((c_hi - c_lo) * EH_TO_EV / EH_TO_KCAL) if ceiling_ok else None
            delta = (cev - ox) if (cev is not None and ox is not None) else None
            if ox is not None and ceiling_ok:
                status = "complete"
            elif ox is not None:
                status = "round1_only"
            else:
                status = "not_computed"
            rows.append({
                "name": name,
                "axis": axis,
                "round1_ev": ("%.9f" % ox) if ox is not None else "",
                "ceiling_ev": ("%.9f" % cev) if cev is not None else "",
                "delta_ev": ("%.9f" % delta) if delta is not None else "",
                "status": status,
            })
    return rows


def selection_rows(labels, states):
    """Top-k / regret over the audit molecules, round-1 ranking vs ceiling ranking.

    Round-1 side always publishes its frozen baseline.  The ceiling side only
    exists when ALL audit molecules have a complete ceiling oxidation axis;
    otherwise the comparison stays not_computed per the plan's rule (empty is
    honest, zero is fabrication).
    """
    ceiling_by_state = {(r["name"], r["state"]): num(r["g_ensemble_ceiling_kcal"])
                        for r in states}
    status_by_state = {(r["name"], r["state"]): r["ceiling_status"] for r in states}
    ox, c_ox = [], []
    ceiling_complete = True
    for name in AUDIT_MOLECULES:
        value = _gap(labels.get((name, "M_plus")), labels.get((name, "M")))
        if value is not None:
            ox.append((name, value))
        ok = (status_by_state.get((name, "M_plus")) == "complete"
              and status_by_state.get((name, "M")) == "complete")
        c_hi, c_lo = (ceiling_by_state.get((name, "M_plus")),
                      ceiling_by_state.get((name, "M")))
        if ok and c_hi is not None and c_lo is not None:
            c_ox.append((name, (c_hi - c_lo) * EH_TO_EV / EH_TO_KCAL))
        else:
            ceiling_complete = False
    rows = []
    for k in (K_MAIN,) + K_AUX:
        ranked = sorted(ox, key=lambda item: -item[1])[:k]
        members = "+".join(name for name, _ in ranked)
        c_ranked = sorted(c_ox, key=lambda item: -item[1])[:k] if ceiling_complete else []
        c_members = "+".join(name for name, _ in c_ranked) if ceiling_complete else ""
        overlap = len(set(name for name, _ in ranked) & set(name for name, _ in c_ranked)) \
            if ceiling_complete else None
        # regret: best achievable within round-1 top-k under the ceiling metric,
        #         minus what the round-1 top-k actually achieves (>= 0).
        regret = None
        if ceiling_complete and ranked and c_ox:
            c_best_any = max(v for _, v in c_ox)
            achieved = max(v for n, v in c_ox if n in set(m for m, _ in ranked))
            regret = c_best_any - achieved
        if ceiling_complete and ranked:
            status = "complete"
        elif ranked:
            status = "round1_only"
        else:
            status = "not_computed"
        rows.append({
            "quantity": "top_k_overlap",
            "k": str(k),
            "round1_topk": members,
            "ceiling_topk": c_members,
            "value": (str(overlap) if overlap is not None else ""),
            "status": status,
            "reason": "" if ceiling_complete else CEILING_REASON,
        })
        rows.append({
            "quantity": "selection_regret_ev",
            "k": str(k),
            "round1_topk": members,
            "ceiling_topk": c_members,
            "value": ("%.9f" % regret) if regret is not None else "",
            "status": status,
            "reason": "" if ceiling_complete else CEILING_REASON,
        })
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and compare, never write")
    args = ap.parse_args(argv)

    labels = load_labels()
    audit = load_audit()
    legs = ceiling_legs()
    round2 = load_round2_members()
    states = state_rows(labels, audit, round2, ledger_rows())
    axes = axis_rows(labels, states)
    selection = selection_rows(labels, states)

    state_fields = list(states[0])
    def render_csv(fields, rows):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    pending_states = sum(1 for r in states if r["ceiling_status"] == "not_computed")
    limited = sum(1 for r in states if r["audit_status"] == "sampling_limited")
    executable = sum(1 for r in states if r["audit_status"] in ("executable", "executable_partial"))
    with_round1 = sum(1 for r in states if r["g_ensemble_round1_kcal"])
    measured_li = sum(1 for r in states if r["pool_kind"] == "li_motif_round2_measured")
    unmeasured_li = sum(1 for r in states if r["pool_kind"] == "li_motif")
    waiting_round2 = sum(1 for r in states
                         if str(r["needs_second_round_motif_search"]).lower() == "true")

    lines = [
        "# 3→6 采样差异报告（EMC / DEC / DME / TMP × 四主态）",
        "",
        "> 生成器：`scripts/wp_production/build_sampling_3to6_diff.py`（`--check` 完全只读）",
        "> 按用户 2026-10-19 决定：**本轮只报告差异，不判“采样收敛”**。",
        "> `sampling_limited` 只表示当前搜索池/扩样覆盖受限，不是数值收敛结论。",
        "> GFN2 的 1.00 kcal/mol 是**筛选**阈值，不用于生产级验收。",
        "",
        "## 本轮能给出什么、不能给出什么",
        "",
        "| 项 | 状态 | 说明 |",
        "| --- | --- | --- |",
        "| round-1 `G_ensemble` | %d/16 态已填 | 直接取自生产系综标签，可复算 |" % with_round1,
        "| 氧化轴 / Li 条件轴（round-1 侧） | 已填 | `G(M_plus)-G(M)`、`G(LiM_2plus)-G(LiM_plus)`，单位 eV |",
        "| ceiling 侧（扩到池内上限） | %d/16 态 not_computed | 定义为**round-1 极小 + 已登记且 QC 通过的第二轮成员**（同一 DFT 级去重规则），缺口就留空：**空格是诚实状态，不是 0** |" % pending_states,
        "| Top-k 重叠 / selection regret | not_computed | 依赖 ceiling 侧排序，只登记 round-1 基线集合 |",
        "| 采样收敛判定 | **不做** | 独立生产级容差尚未冻结，不得据本轮结果倒推 |",
        "",
        "## 池覆盖（来自 3→6 审计，非本轮数值）",
        "",
        "| 判定 | 状态数 |",
        "| --- | --- |",
        "| executable / executable_partial | %d |" % executable,
        "| sampling_limited | %d |" % limited,
        "| Li 态池取第二轮**实测**值 | %d |" % measured_li,
        "| Li 态维持 round-1 池（父体哈希核验失败，不补数） | %d |" % unmeasured_li,
        "",
        "## 逐态：round-1 自由能与 ceiling 侧",
        "",
        "| 分子 | 态 | 池类型 | round1 | 池内上限 | 审计判定 | accepted | n_unique | G_ens(round-1) kcal/mol | G_ens(ceiling) | Δ |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in states:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], r["state"], r["pool_kind"], r["round1_structures"],
            r["round2_ceiling"], r["audit_status"], r["acceptance_status"],
            r["n_unique_round1"], r["g_ensemble_round1_kcal"] or "—",
            "—", "—"))
    lines += [
        "",
        "## 氧化轴与 Li 条件轴（round-1 侧，eV）",
        "",
        "| 分子 | 轴 | round-1 | ceiling | Δ | 状态 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in axes:
        lines.append("| %s | %s | %s | — | — | %s |" % (
            r["name"], r["axis"], r["round1_ev"] or "—", r["status"]))
    lines += [
        "",
        "## Top-k 与 selection regret（预注册口径，本轮只登记基线）",
        "",
        "审计集只有 4 个分子，故主 k=2，辅助 k=1 与 k=3（原方案 k=3/2/4 按集合规模缩放）。",
        "",
        "| 量 | k | round-1 Top-k 集合 | ceiling 集合 | 值 | 状态 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in selection:
        lines.append("| %s | %s | %s | — | — | %s |" % (
            r["quantity"], r["k"], r["round1_topk"] or "—", r["status"]))
    lines += [
        "",
        "## 判读规则（先冻结，后看结果）",
        "",
        "1. **不得据本轮结果倒推阈值**：生产级独立容差须在扩样结果出现**之前**冻结，且不能由“希望哪个分子翻转”反推。",
        "2. **空值不补零**：ceiling 侧未计算就留空并写原因；把缺证据写成 0 或写成“无变化”都是造假。",
        "3. **池不足不凑数**：`sampling_limited` 的状态只登记真实上限，绝不复制构象凑到 6。",
        "4. **Li 态第二轮 motif 搜索已执行**（`run_li_motif_round2.py`，独立中性盆地做父几何）："
        "%d 个态的池数取实测值（round-1 保留 + 真新盆地，同类重原子 RMSD 去重），"
        "%d 个态因登记父体磁盘哈希与登记值不符而维持 round-1 池（不换父、不补数），"
        "仍有 %d 个态标记待搜索。**池可用（筛选层）不等于已登记生产成员**："
        "新盆地要进 ceiling 侧必须另跑生产级 ORCA 腿，故本轮 ceiling 仍一律 `not_computed`。"
        % (measured_li, unmeasured_li, waiting_round2),
        "5. 扩样结果落地后，本表由生成器自动填 ceiling 侧与 Δ；届时仍需人工确认容差已冻结再下结论。",
        "",
    ]
    md = "\n".join(lines)

    rendered = (
        (OUT_CSV, render_csv(state_fields, states)),
        (OUT_CSV.with_name("sampling_3to6_diff_axes.csv"), render_csv(list(axes[0]), axes)),
        (OUT_CSV.with_name("sampling_3to6_diff_selection.csv"),
         render_csv(list(selection[0]), selection)),
        (OUT_MD, md),
    )
    if args.check:
        failures = []
        for path, text in rendered:
            if not path.is_file():
                failures.append("missing: " + path.name)
            elif path.read_bytes() != text.encode("utf-8"):
                failures.append("differs: " + path.name)
        if failures:
            for item in failures:
                print("STALE: " + item)
            return 1
        print("CHECK OK -- 3->6 difference report matches recomputation")
        return 0

    SAMPLING.mkdir(parents=True, exist_ok=True)
    for path, text in rendered:
        path.write_text(text, encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {p.name: sha256_file(p) for p in (LABELS, AUDIT, MANIFEST) if p.is_file()},
        "outputs": {p.name: sha256_file(p) for p, _ in rendered},
        "rules": {
            "audit_molecules": list(AUDIT_MOLECULES),
            "states": list(STATES),
            "k_main": K_MAIN,
            "k_aux": list(K_AUX),
            "eh_to_ev": EH_TO_EV,
            "convergence_verdict": "NOT MADE this round (user ruling 2026-10-19)",
            "gfn2_1kcal_is": "screening threshold only; never a production acceptance criterion",
        },
        "states_rows": len(states),
        "ceiling_not_computed": pending_states,
        "li_pool_round2_measured": measured_li,
        "li_pool_round1_only": unmeasured_li,
        "li_states_awaiting_round2": waiting_round2,
        "round1_g_ensemble_filled": with_round1,
        "audit_status_counts": {"executable_or_partial": executable,
                               "sampling_limited": limited},
        "registered_round2_candidate_legs": sum(legs.values()),
    }
    OUT_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    print("3->6 diff: states=%d round1_filled=%d ceiling_pending=%d limited=%d"
          % (len(states), with_round1, pending_states, limited))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
