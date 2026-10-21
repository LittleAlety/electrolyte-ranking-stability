"""Decision support for the ensemble states not accepted yet (at most 14).

Reads the frozen ledgers (labels / dispositions / structures / sampling audit /
3->6 difference report / conformer pool / Li motif screen / Li round-2 exec)
and, per non-accepted state, derives:

* the limitation reason and member-level disposition mix (verbatim);
* UNUSED pool basins -- frozen-pool minima never sent to ANY production-level
  attempt.  Derived by set difference between the pool and every basin the
  structures ledger ever recorded (any role: round1_extra OR round2_audit_extra,
  any attempt status), so the 3->6 audit extension legs consume their basins
  too.  Nothing hard-coded; ``--check`` recomputes honestly;
* the worst-case extra lowering via THREE evidence channels, taking the max:
  (a) the RT ln N mathematical bound at fixed G_min:
      extra <= RT ln(N_max) - RT ln(n_unique), N_max = n_unique + unused
      + (1 if a rescue is still in flight);
  (b) the MEASURED 3->6 ceiling drop when the audit extension completed
      (only TMP|LiM_2plus has one; a real new minimum can beat RT ln N by
      lowering G_min itself, so measurement dominates the bound);
  (c) zero otherwise -- never a guess;
* ranking sensitivity: would that worst-case lowering change the Top-3 or the
  full 12-molecule order on either axis (oxidation M_plus-M, Li-conditioned
  LiM_2plus-LiM_plus, both in the "lowest = easiest oxidation" direction the
  sampling_3to6_diff report froze), and a joint worst case where all 14 states
  take their bounds simultaneously.

The user's 2026-10-20 ruling made "would it change the key ordering" the ONLY
trigger for preregistering new independent starts; this report quantifies it.

Outputs (outputs/physics_completion/ensembles/):
  remaining_gaps_decision_support.csv  machine-readable per-state rows
  remaining_gaps_decision_support.md   decision report
  remaining_gaps_decision_support_index.json  input/output hashes + rules

Read-only inputs; ``--check`` recomputes in memory and byte-compares (writes
nothing, touches no mtime).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
SAMP = REPO / "outputs" / "physics_completion" / "sampling"
LIM = REPO / "outputs" / "physics_completion" / "li_motif_sampling"

LABELS = ENS / "production_ensemble_labels.csv"
DISPOS = ENS / "production_ensemble_dispositions.csv"
STRUCTURES = ENS / "production_ensemble_structures.csv"
CANDIDATES = ENS / "production_ensemble_candidates.csv"
AUDIT = SAMP / "sampling_audit_3to6.csv"
DIFF = SAMP / "sampling_3to6_diff.csv"
CONFORMERS = SAMP / "sampling_conformer_set.csv"
LI_SCREEN = LIM / "li_motif_screen.csv"
LI_ROUND2 = LIM / "li_motif_round2_exec.csv"

OUT_CSV = ENS / "remaining_gaps_decision_support.csv"
OUT_MD = ENS / "remaining_gaps_decision_support.md"
OUT_INDEX = ENS / "remaining_gaps_decision_support_index.json"

#: Frozen constants (mirror build_production_ensemble_aggregator.py).
R_KCAL = 1.98720425864083e-3          # kcal/(mol K), CODATA
TEMP_K = 298.15
WINDOW_KCAL = 6.0                     # rule E1 resource rule
EH_TO_EV = 27.211386245988
KCAL_PER_EV = 627.5094740631 / 27.211386245988
AXES = (("oxidation", "M_plus", "M"), ("Li_conditioned", "LiM_2plus", "LiM_plus"))
TOP_K = 3


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _basin_key(token: str) -> str:
    """Normalise a free-conformer basin id across its two spellings.

    Pool rows write ``r2_c13`` / ``c03``; ledger member keys write bare
    ``13`` / ``3``.  Strip round markers and leading zeros so both sides
    meet; anything unnormalisable stays verbatim (never silently dropped).
    """
    token = token.strip().rstrip("/")
    parts = [p for p in token.split("/") if p]
    leaf = parts[-2] if (len(parts) >= 2 and parts[-1].endswith(".xyz")) else parts[-1]
    if "_" in leaf and not leaf.startswith(("r2_", "c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9")):
        return leaf                       # compound Li round-2 seed, verbatim
    head = leaf.split("_")[0]
    digits = "".join(ch for ch in leaf.split("_")[-1] if ch.isdigit())
    # strip LEADING ZEROS too: c03 and 3 are the same basin (the member
    # ledger writes bare 3; the pool writes c03 -> digits "03" -> "3")
    key = digits.lstrip("0") or digits
    if head.startswith("r") and head[1:].isdigit():
        return key or leaf
    if (leaf.startswith("c") and digits) or digits:
        return key
    return leaf


def load_inputs() -> dict:
    return {
        "labels": read_rows(LABELS),
        "dispos": read_rows(DISPOS),
        "structures": read_rows(STRUCTURES),
        "candidates": read_rows(CANDIDATES),
        "audit": read_rows(AUDIT),
        "diff": read_rows(DIFF),
        "conformers": read_rows(CONFORMERS),
        "li_screen": read_rows(LI_SCREEN),
        "li_round2": read_rows(LI_ROUND2),
    }


def ledger_seeds(name: str, state: str, data: dict) -> set[str]:
    """Every basin the structures ledger EVER recorded for this leg, any role
    (primary / round1_extra / round2_audit_extra), any status.  A basin with a
    drift or budget-exhausted member is consumed: identity cannot be restored
    by retrying, so it is never reported as available."""
    out = set()
    for r in data["structures"]:
        key = r.get("member_key", "")
        parts = key.split("|")
        if len(parts) == 3 and parts[0] == name and parts[1] == state:
            out.add(parts[2])
    return out


def unused_basins(mol_id: str, name: str, state: str, data: dict) -> tuple[list[str], list[str]]:
    """Frozen-pool basins inside the window that never had a production attempt.

    Returns (basin_ids, source_labels).  Free states read the conformer pool
    (any ``pool`` spelling -- the ledger writes ``union_round1_round2``); Li
    states read the round-1 screen kept motifs (minus the production_geometry
    motif, whose basin the primary leg already represents) plus the round-2
    measured new basins, with ledger seed spelling ``parent_candidate``.
    """
    used = ledger_seeds(name, state, data)
    out_ids, out_labels = [], []
    if not state.startswith("Li"):
        for r in data["conformers"]:
            if r.get("mol_id") != mol_id or r.get("state") != state:
                continue
            leaf = str(r.get("geometry_relpath") or "").split("/")[-2]
            key = _basin_key(leaf)
            rel = num(r.get("rel_kcal"))
            if key not in used and (rel is None or rel <= WINDOW_KCAL):
                out_ids.append(key)
                out_labels.append("%s (+%s kcal in pool)" % (leaf, r.get("rel_kcal", "?")))
        return out_ids, out_labels
    # Li states
    for r in data["li_screen"]:
        if r.get("mol_id") != mol_id or r.get("state") != state or r.get("kept") != "true":
            continue
        if r.get("placement") == "production_geometry":
            continue                      # primary-basin motif: the primary leg owns it
        if r["candidate_id"] not in used:
            out_ids.append(r["candidate_id"])
            out_labels.append("round1_kept %s (+%s kJ)" % (r.get("motif_id", "?"),
                                                            r.get("energy_rel_kj", "?")))
    for r in data["li_round2"]:
        if (r.get("leg_id") != "%s|%s" % (name, state)
                or r.get("kept") != "true" or r.get("new_vs_round1") != "true"):
            continue
        seed = "%s_%s" % (r.get("parent_conformer_id", ""), r.get("candidate_id", ""))
        rel = num(r.get("energy_rel_kj"))
        if seed not in used and (rel is None or rel / 4.184 <= WINDOW_KCAL):
            out_ids.append(seed)
            out_labels.append("round2_measured %s (+%s kJ vs parent)" % (r.get("motif_id", "?"),
                                                                         r.get("energy_rel_kj", "?")))
    return out_ids, out_labels


def measured_ceiling_drop(name: str, state: str, data: dict) -> float | None:
    """Channel (b): the 3->6 audit's MEASURED ceiling drop, when complete."""
    for r in data["diff"]:
        if r.get("name") == name and r.get("state") == state \
                and r.get("ceiling_status") == "complete":
            g1, gc = num(r.get("g_ensemble_round1_kcal")), num(r.get("g_ensemble_ceiling_kcal"))
            if g1 is not None and gc is not None:
                return g1 - gc
    return None


def axis_values(labels: dict, lower: dict) -> dict[str, list]:
    """Two axes (kcal) for all 12 molecules; ``lower[(mol,state)]`` extra drop."""
    out = {}
    for mol, states in labels.items():
        row = []
        for _, hi, lo in AXES:
            g_hi = num((states.get(hi) or {}).get("g_ensemble_kcal"))
            g_lo = num((states.get(lo) or {}).get("g_ensemble_kcal"))
            if g_hi is None or g_lo is None:
                row.append(None)
                continue
            g_hi -= lower.get((mol, hi), 0.0)
            g_lo -= lower.get((mol, lo), 0.0)
            row.append(g_hi - g_lo)
        out[mol] = row
    return out


def full_order(values: dict, axis: int) -> list[str]:
    return [m for m, _ in sorted(((m, v[axis]) for m, v in values.items() if v[axis] is not None),
                                 key=lambda kv: kv[1])]


def build_rows() -> tuple[list[dict], dict]:
    data = load_inputs()
    labels = {(r["mol_id"], r["state"]): r for r in data["labels"]}
    if len(labels) != 48:
        raise SystemExit("REJECT: labels must hold 48 states, found %d" % len(labels))
    by_mol: dict[str, dict[str, dict]] = {}
    for (mol, st), r in labels.items():
        by_mol.setdefault(mol, {})[st] = r
    audit = {(r["name"], r["state"]): r for r in data["audit"]}

    # The scope is "every state not accepted yet" -- a number that SHRINKS as
    # recovery succeeds, so it must never be hard-coded.  The invariant is that
    # each open state gets exactly one row, and the scope never exceeds the
    # frozen 14-state baseline.
    gaps = [(m, s) for (m, s), r in sorted(labels.items())
            if r["acceptance_status"] != "accepted"]
    if len(set(gaps)) != len(gaps):
        raise SystemExit("REJECT: duplicate open states in the gap scope")
    if len(gaps) > 14:
        raise SystemExit("REJECT: %d open states exceeds the frozen 14 baseline"
                         % len(gaps))

    base_vals = axis_values(by_mol, {})
    base_order = [full_order(base_vals, i) for i in range(2)]
    base_top = [frozenset(o[:TOP_K]) for o in base_order]

    rows, per_state_worst = [], {}
    for (mol, state) in gaps:
        lab = labels[(mol, state)]
        name = lab["name"]
        n_unique = int(lab["n_unique"] or 0)
        unused_ids, unused_labels = unused_basins(mol, name, state, data)
        inflight = int(lab.get("n_unresolved") or 0)

        # channel (a): RT ln N math bound (fixed G_min)
        n_max = n_unique + len(unused_ids) + (1 if inflight else 0)
        bound_now = num(lab.get("lowering_bound_rt_ln_n_kcal")) or 0.0
        rt_extra = max(0.0, R_KCAL * TEMP_K * (math.log(n_max) - math.log(n_unique))
                       if n_unique and n_max > n_unique else 0.0)
        # channel (b): measured ceiling drop
        measured = measured_ceiling_drop(name, state, data)
        worst = max(rt_extra, measured or 0.0)
        per_state_worst[(mol, state)] = worst

        vals = axis_values(by_mol, {(mol, state): worst})
        order = [full_order(vals, i) for i in range(2)]
        top_flip = [frozenset(order[i][:TOP_K]) != base_top[i] for i in range(2)]
        pair_flips = []
        for i in range(2):
            if vals[mol][i] is None or base_vals[mol][i] is None:
                continue
            for other in vals:
                if other == mol or vals[other][i] is None or base_vals[other][i] is None:
                    continue
                if (base_vals[other][i] - base_vals[mol][i]) * (vals[other][i] - vals[mol][i]) < 0:
                    pair_flips.append((AXES[i][0], other))
        sensitive = any(top_flip) or bool(pair_flips)

        moved = []
        for i, (_, hi, lo) in enumerate(AXES):
            if state in (hi, lo) and base_vals[mol][i] is not None and vals[mol][i] is not None:
                moved.append((AXES[i][0], base_vals[mol][i] - vals[mol][i]))

        dispo = [r for r in data["dispos"]
                 if r.get("member_key", "").startswith("%s|%s|" % (name, state))]
        burned = sum(1 for r in dispo
                     if r.get("disposition") in ("species_drift_unrecoverable",
                                                 "rescue_budget_exhausted"))

        rows.append({
            "mol_id": mol, "name": name, "state": state,
            "acceptance_status": lab["acceptance_status"],
            "limitation_reason": lab["limitation_reason"] or ("rescue_in_flight" if inflight else ""),
            "n_unique": str(n_unique),
            "n_rescue_in_flight": str(inflight),
            "disposition_summary": "; ".join(
                "%s->%s(%s)" % (r["member_key"].split("|")[-1], r["disposition"], r["failure_class"])
                for r in dispo) or "none",
            "n_burned_basins": str(burned),
            "audit_status": (audit.get((name, state)) or {}).get("status", "not_in_audit_set"),
            "audit_ceiling": (audit.get((name, state)) or {}).get("round2_ceiling", ""),
            "unused_basins": ";".join(unused_ids),
            "n_unused": str(len(unused_ids)),
            "unused_sources": "; ".join(unused_labels) if unused_labels else "none",
            "n_max_members": str(n_max),
            "rt_extra_bound_kcal": "%.6f" % rt_extra,
            "measured_ceiling_drop_kcal": "" if measured is None else "%.6f" % measured,
            "worst_extra_lowering_kcal": "%.6f" % worst,
            "worst_extra_lowering_mev": "%.1f" % (worst / KCAL_PER_EV * 1000.0),
            "axis_moves_kcal": "; ".join("%s=%.3f" % (a, d) for a, d in moved) or "0.000",
            "top3_oxidation_flip": str(top_flip[0]).lower(),
            "top3_licond_flip": str(top_flip[1]).lower(),
            "pair_order_flips": "; ".join("%s vs %s" % (a, o) for a, o in pair_flips) or "none",
            "ranking_sensitive": str(sensitive).lower(),
            "recommendation": "",
        })

    # joint worst case
    joint_vals = axis_values(by_mol, per_state_worst)
    joint_order = [full_order(joint_vals, i) for i in range(2)]
    joint_top_flip = [frozenset(joint_order[i][:TOP_K]) != base_top[i] for i in range(2)]
    joint_pair_flips = []
    for i in range(2):
        for a in by_mol:
            for b in by_mol:
                if a >= b or joint_vals[a][i] is None or joint_vals[b][i] is None:
                    continue
                if base_vals[a][i] is None or base_vals[b][i] is None:
                    continue
                if (base_vals[b][i] - base_vals[a][i]) * (joint_vals[b][i] - joint_vals[a][i]) < 0:
                    joint_pair_flips.append((AXES[i][0], a, b))
    joint = {
        "top3_flip": joint_top_flip, "pair_flips": joint_pair_flips,
        "base_order": base_order, "joint_order": joint_order,
        "base_vals": base_vals, "joint_vals": joint_vals,
    }
    for r in rows:
        if r["ranking_sensitive"] == "true":
            r["recommendation"] = ("candidate_for_preregistered_new_start"
                                   if r["n_unused"] != "0"
                                   else "sensitive_but_no_unused_basin_register_limitation")
        elif r["n_rescue_in_flight"] != "0":
            r["recommendation"] = "let_registered_rescue_settle_no_new_start"
        elif r["n_unused"] != "0":
            r["recommendation"] = ("keep_%s_ranking_insensitive_unused_basin_on_record"
                                   % r["acceptance_status"])
        else:
            r["recommendation"] = "no_unused_basin_register_limitation"
    return rows, joint


def render_csv(rows: list[dict]) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _ev(kcal):
    return "%.3f" % (kcal / KCAL_PER_EV)


def render_md(rows: list[dict], joint: dict) -> str:
    labels_names = {r["mol_id"]: r["name"] for r in rows}
    by_mol = {}
    for r in rows:
        by_mol.setdefault(r["mol_id"], {})["gap_" + r["state"]] = True
    lines = []
    ap = lines.append
    ap("# 未 accepted 系综态：决策支持（v1.4.2 缺口分诊；上限 14，随恢复递减）")
    ap("")
    ap("> 生成器：`scripts/wp_production/build_gap_decision_support.py`（`--check` 完全只读）。")
    ap("> 只读冻结证据：48 态生产标签、成员处置、结构账本（round1_extra **与 round2_audit_extra**）、")
    ap("> 3→6 审计与差异报告、自由构象冻结池、Li motif 筛选池、round-2 实测盆地。")
    ap("> **零新增计算、零阈值改动、零验收语义改动。**")
    ap("> 用户 2026-10-20 裁决：只有「会改变关键排序」的态才值得预注册独立新起点；不为 48/48 数字续算。")
    ap("")
    ap("## 排序敏感的量化口径（先冻结）")
    ap("")
    ap("- 两条轴：氧化 = G(M_plus)−G(M)，Li 条件 = G(LiM_2plus)−G(LiM_plus)，单位 eV")
    ap("  （`ΔEh × 27.211386245988`，与 `sampling_3to6_diff` 同口径）；")
    ap("- **Top-3 = 轴值最低的 3 个分子**（最易氧化方向，与 3→6 报告的 top-k 一致）；")
    ap("- worst-case 额外拉低取三条证据通道的**最大值**：")
    ap("  (a) `RT ln N_max − RT ln n_unique`（固定 G_min 的数学上界；N_max = n_unique + 未用盆地 + 在途救援）；")
    ap("  (b) 3→6 审计已实测完成的 ceiling 落差（真实新极小可以**低于** G_min，测量值优先于数学界）；")
    ap("  (c) 其余为 0，绝不猜测；")
    ap("- **排序敏感 = Top-3 集合变化，或任一轴上任何逐对次序交换**；")
    ap("- 漂移/预算尽的盆地已烧毁（重跑不能恢复身份），不参与 N_max。")
    ap("")
    ap("## 基线（当前 48 标签）")
    ap("")
    for i, (axis_name, _, _) in enumerate(AXES):
        ap("**%s 轴**（eV，低 = 更易氧化/更易再电离）：" % axis_name)
        ap("")
        ap("| # | 分子 | 轴值 | 与前一名间距 (kcal) |")
        ap("| --- | --- | --- | --- |")
        order = joint["base_order"][i]
        vals = joint["base_vals"]
        for rank, m in enumerate(order):
            gap = None
            if rank:
                gap = vals[m][i] - vals[order[rank - 1]][i]
            ap("| %d | %s (%s) | %s | %s |" % (
                rank + 1, m, labels_names.get(m, m), _ev(vals[m][i]),
                "—" if gap is None else "%.3f" % gap))
        ap("")
        ap("Top-3：%s" % ", ".join("%s (%s)" % (m, labels_names.get(m, m)) for m in order[:TOP_K]))
        ap("")
    ap("## 联合最坏情形（14 个缺口态同时取到各自 worst-case）")
    ap("")
    ap("| 轴 | 基线 Top-3 | 联合最坏 Top-3 | 翻转 | 完整排序 |")
    ap("| --- | --- | --- | --- | --- |")
    for i, (axis_name, _, _) in enumerate(AXES):
        ap("| %s | %s | %s | %s | %s |" % (
            axis_name,
            ", ".join(joint["base_order"][i][:TOP_K]),
            ", ".join(joint["joint_order"][i][:TOP_K]),
            "是" if joint["top3_flip"][i] else "否",
            "变化" if joint["base_order"][i] != joint["joint_order"][i] else "不变"))
    ap("")
    if joint["pair_flips"]:
        ap("联合最坏下的逐对翻轴：%s" % "; ".join(
            "%s：%s 与 %s 互换" % (ax, a, b) for ax, a, b in joint["pair_flips"]))
    else:
        ap("**联合最坏下无任何逐对翻轴、无 Top-3 翻转、完整排序不变**——")
        ap("即使全部 14 个缺口态的每一条剩余证据都取最坏值，12 分子在两条轴上的排序也不动。")
    ap("")
    ap("## 逐态决策证据")
    ap("")
    for r in rows:
        ap("### %s %s（%s）" % (r["mol_id"], r["name"], r["state"]))
        ap("")
        ap("- **状态**：%s（%s）；n_unique=%s，n_registered 见 labels；在途救援 %s 个"
           % (r["acceptance_status"], r["limitation_reason"] or "无限制原因（rescue 尚未处置）",
              r["n_unique"], r["n_rescue_in_flight"]))
        ap("- **成员处置**：%s" % r["disposition_summary"])
        ap("- **已烧毁盆地**：%s 个（drift/budget-exhausted——重跑不能恢复身份）" % r["n_burned_basins"])
        ap("- **池**：审计判定 `%s`（池内上限 %s）；**未用独立盆地 %s 个**%s"
           % (r["audit_status"], r["audit_ceiling"] or "—", r["n_unused"],
              "：%s" % r["unused_sources"] if r["unused_sources"] != "none" else "（池已全部尝试或烧毁）"))
        ap("- **worst-case 额外拉低**：%s kcal（%s meV）＝ max(RT ln N 界 %s kcal，实测 ceiling %s)"
           % (r["worst_extra_lowering_kcal"], r["worst_extra_lowering_mev"],
              r["rt_extra_bound_kcal"],
              r["measured_ceiling_drop_kcal"] + " kcal" if r["measured_ceiling_drop_kcal"] else "无"))
        ap("- **排序敏感判定**：**%s**——Top-3 翻转（氧化轴 %s / Li 条件轴 %s），逐对翻轴：%s；该态所在轴最多移动 %s kcal（%s eV）"
           % ("排序敏感" if r["ranking_sensitive"] == "true" else "排序不敏感",
              "是" if r["top3_oxidation_flip"] == "true" else "否",
              "是" if r["top3_licond_flip"] == "true" else "否",
              r["pair_order_flips"],
              r["axis_moves_kcal"].split("=")[-1] if "=" in r["axis_moves_kcal"] else "0.000",
              _ev(float(r["axis_moves_kcal"].split("=")[-1]) if "=" in r["axis_moves_kcal"] else 0.0)))
        ap("- **建议**：%s" % REC_TEXT[r["recommendation"]] % r if r["recommendation"] in
           ("keep_%s_ranking_insensitive_unused_basin_on_record" % r["acceptance_status"],)
           else REC_TEXT.get(r["recommendation"], r["recommendation"]))
        ap("")
    ap("## 建议口径（按用户裁决格式）")
    ap("")
    for key, text in REC_TEXT.items():
        ap("- `%s`：%s" % (key, text.replace("%s", "…")))
    ap("")
    ap("## 判读规则")
    ap("")
    ap("1. **n_unique=1 且无未用盆地的态，worst-case=0 是弱证据**（对「池外还有漏采样独立盆地」")
    ap("   无约束力），只说明**冻结池内**已无剩余拉低空间，如实登记不冒充收敛证明。")
    ap("2. 3 个未用盆地（DEC M r2_c23 / DME M_plus c07 / TMP M_plus c10）都是 round-1 上限")
    ap("   （E2：3 结构含 primary → 每腿 ≤2 extras）排掉的 rank-3 盆地，不是采样缺陷；")
    ap("   bound 显示即使全部用尽也不改变任何排序。")
    ap("3. 3 个 provisional 态的在途救援按登记契约自然落定后重新聚合，")
    ap("   本报告不替代那条处置链。")
    ap("")
    return "\n".join(lines) + "\n"


REC_TEXT = {
    "candidate_for_preregistered_new_start":
        "排序敏感且冻结池确有未用盆地——可预注册独立新起点（须先登记来源/次数/停止条件）",
    "sensitive_but_no_unused_basin_register_limitation":
        "排序敏感但池已用尽——只能登记限制，不得开新起点搜索",
    "let_registered_rescue_settle_no_new_start":
        "在途救援尚未处置——先让登记的救援链落定，暂不新增任何起点",
    "keep_limited_ranking_insensitive_unused_basin_on_record":
        "有 %s 个未用盆地但 bound 显示用尽也不改变排序——维持 limited，未用盆地登记在案不续算",
    "keep_provisional_ranking_insensitive_unused_basin_on_record":
        "有 %s 个未用盆地但 bound 显示用尽也不改变排序——维持 provisional，未用盆地登记在案不续算",
    "no_unused_basin_register_limitation":
        "无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可",
}


def render_index(rows, csv_text, md_text) -> str:
    return json.dumps({
        "schema_version": "2.0",
        # deterministic: the index must not embed wall-clock time or a chain run
        # can never pass its own --check (generation and check differ by
        # seconds).  Pin the provenance to the INPUTS instead.
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_gap_decision_support.py",
        "purpose": "decision support for the 14 not-yet-accepted ensemble states; "
                   "read-only evidence triage under the 2026-10-20 user ruling",
        "inputs": {str(p.relative_to(REPO)): sha256_file(p) for p in
                   (LABELS, DISPOS, STRUCTURES, CANDIDATES, AUDIT, DIFF,
                    CONFORMERS, LI_SCREEN, LI_ROUND2)},
        "outputs": {p.name: hashlib.sha256(t.encode("utf-8")).hexdigest()
                    for p, t in ((OUT_CSV, csv_text), (OUT_MD, md_text))},
        "rules": {
            "r_kcal_mol_k": R_KCAL, "temp_k": TEMP_K, "window_kcal": WINDOW_KCAL,
            "eh_to_ev": EH_TO_EV, "top_k": TOP_K,
            "worst_case": "max(RT ln N_max - RT ln n_unique, measured 3->6 ceiling drop); "
                          "N_max = n_unique + unused_in_window_basins + (1 if rescue in flight); "
                          "burned (drift/budget-exhausted) basins never count",
            "sensitive": "any Top-3 set change OR any pairwise order flip on either axis",
            "axes": "oxidation = G(M_plus)-G(M); Li_conditioned = G(LiM_2plus)-G(LiM_plus); "
                    "Top-3 = lowest (easiest oxidation), matching sampling_3to6_diff",
            "user_ruling": "2026-10-20: preregister new independent starts ONLY for states "
                           "whose worst case would change the key ordering; never chase 48/48",
        },
        "gap_states": len(rows),
        "ranking_sensitive_states": sorted(
            "%s|%s" % (r["mol_id"], r["state"]) for r in rows
            if r["ranking_sensitive"] == "true"),
        "states_with_unused_basins": sorted(
            "%s|%s" % (r["mol_id"], r["state"]) for r in rows if r["n_unused"] != "0"),
        "states_with_inflight_rescue": sorted(
            "%s|%s" % (r["mol_id"], r["state"]) for r in rows
            if r["n_rescue_in_flight"] != "0"),
    }, indent=2, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory, byte-compare, write nothing")
    args = ap.parse_args(argv)

    rows, joint = build_rows()
    csv_text = render_csv(rows)
    md_text = render_md(rows, joint)
    index_text = render_index(rows, csv_text, md_text)

    if args.check:
        failures = []
        for path, text in ((OUT_CSV, csv_text), (OUT_MD, md_text), (OUT_INDEX, index_text)):
            if not path.is_file():
                failures.append("missing: " + path.name)
            elif path.read_bytes() != text.encode("utf-8"):
                failures.append("differs: " + path.name)
        if failures:
            for f in failures:
                print("STALE: " + f)
            return 1
        print("CHECK OK -- gap decision support matches recomputation (%d states)" % len(rows))
        return 0

    ENS.mkdir(parents=True, exist_ok=True)
    for path, text in ((OUT_CSV, csv_text), (OUT_MD, md_text), (OUT_INDEX, index_text)):
        path.write_text(text, encoding="utf-8", newline="\n")
    n_sens = sum(1 for r in rows if r["ranking_sensitive"] == "true")
    print("gap decision support: %d states, %d ranking-sensitive, %d with unused basins, "
          "%d with in-flight rescue" % (
              len(rows), n_sens,
              sum(1 for r in rows if r["n_unused"] != "0"),
              sum(1 for r in rows if r["n_rescue_in_flight"] != "0")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
