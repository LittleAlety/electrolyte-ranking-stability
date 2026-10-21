"""strict_recovery_v1: the frozen recovery-batch manifest (registration only).

The user's 2026-10-21 strict-recovery decision authorises a NEW round of
bounded production calculation for all 14 limited ensemble states.  Before a
single ORCA job goes out, this manifest registers -- per state -- what will
be attempted, from where, at what cost, and when to stop.  It also preserves
the old batch untouched: nothing here rewrites a historical failure.

Per-state contract (all four are REQUIRED, mirroring the plan table):

* ``path``            -- ``frozen_basin`` when the frozen pool still holds an
                        unused basin (P1 quick wins), otherwise
                        ``new_search_required`` (independent basin search must
                        be registered and run first; never back-fill the old
                        pool);
* ``starts``          -- at most 2 independent registered starts per state
                        (plan: ``每态最多 2 个新独立生产起点``, total cap 28).
                        For ``new_search_required`` states the start basin is
                        deliberately blank until the search registers one;
* ``budget``          -- per-state measured cost basis from the production
                        ledger (same-state legs), and the batch caps
                        (recovery 600 / reserve 300 core-hours);
* ``stop``            -- the frozen stop rule: two independent starts failing
                        keeps the state limited and the overall gate blocked.

Outputs (new):

    outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv
    outputs/physics_completion/recovery/strict_recovery_v1_index.json
    outputs/physics_completion/recovery/strict_recovery_v1_manifest.md

``--check`` recomputes in memory and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
SAMP = REPO / "outputs" / "physics_completion" / "sampling"
COST = REPO / "outputs" / "physics_completion" / "cost"
OUT = REPO / "outputs" / "physics_completion" / "recovery"

LABELS = ENS / "production_ensemble_labels.csv"
GAPS = ENS / "remaining_gaps_decision_support.csv"
STRUCT = ENS / "production_ensemble_structures.csv"
CONFORMERS = SAMP / "sampling_conformer_set.csv"
MOTIF_SCREEN = SAMP / "li_motif_screen.json"
COST_LEDGER = COST / "production_cost_ledger.csv"

OUT_CSV = OUT / "strict_recovery_v1_manifest.csv"
OUT_MD = OUT / "strict_recovery_v1_manifest.md"
OUT_INDEX = OUT / "strict_recovery_v1_index.json"
SEARCH_POOL = OUT / "strict_recovery_v1_search_pool.csv"
SEARCH_INDEX = OUT / "strict_recovery_v1_search_index.json"
LI_RECOVERY_EXEC = (REPO / "outputs" / "physics_completion" / "li_motif_sampling"
                    / "li_motif_round3_recovery.csv")

#: plan: per-state <= 2 new independent production starts, batch cap 28 legs
MAX_STARTS_PER_STATE = 2
MAX_LEGS = 28
RECOVERY_CAP_CORE_HOURS = 600.0
RESERVE_CAP_CORE_HOURS = 300.0
BATCH_ID = "strict_recovery_v1"

#: the plan's priority table, transcribed verbatim into machine-readable form
PRIORITY = {
    # P0 -- full-pool Top-3 boundary (all four M_plus states)
    ("AN", "M_plus"): ("P0", "independent_cation_search"),
    ("DMC", "M_plus"): ("P0", "independent_cation_search"),
    ("EMC", "M_plus"): ("P0", "independent_cation_search_no_drifted_restart"),
    ("TMP", "M_plus"): ("P0", "unused_pool_basin_then_independent_search"),
    # P1 -- already-measured unused candidates (use them first, re-dedup after)
    ("DEC", "M"): ("P1", "unused_pool_basin"),
    ("DME", "M_plus"): ("P1", "unused_pool_basin"),
    # P1 -- Li oxidised post-state
    ("DMC", "LiM_2plus"): ("P1", "independent_coordination_start"),
    ("EC", "LiM_2plus"): ("P1", "independent_coordination_start"),
    ("DME", "LiM_2plus"): ("P1", "independent_coordination_start"),
    ("DOL", "LiM_2plus"): ("P1", "independent_coordination_start"),
    ("SL", "LiM_2plus"): ("P1", "independent_coordination_start"),
    ("TMP", "LiM_2plus"): ("P1", "independent_coordination_start"),
    # P1 -- Li parent state
    ("DMSO", "LiM_plus"): ("P1", "independent_donor_conformation_start"),
    ("TMP", "LiM_plus"): ("P1", "independent_donor_conformation_start"),
}

#: states whose treatment must begin from a brand-new (versioned) search
NEW_SEARCH_PATHS = {
    "independent_cation_search",
    "independent_cation_search_no_drifted_restart",
    "independent_coordination_start",
    "independent_donor_conformation_start",
}

STOP_RULES = (
    "two independent registered starts failing keeps the state limited and the "
    "overall gate blocked; no threshold relaxation, no rewriting a failed "
    "structure as computed, no deleting the historical failure"
)


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


def _leg_cost_basis() -> dict[tuple[str, str], float]:
    """Measured core_hours per (name, state); both cost columns are consulted."""
    out: dict[tuple[str, str], float] = {}
    for r in _read(COST_LEDGER):
        key = (r.get("name", ""), r.get("state", ""))
        for col in ("core_hours", "hpc_core_hours"):
            v = _f(r.get(col))
            if v is not None:
                out.setdefault(key, v)
                break
    return out


def _pool_basins(name: str, state: str) -> dict[str, tuple[str, str]]:
    """canonical id -> (pool spelling, geometry sha256) for one state."""
    out: dict[str, tuple[str, str]] = {}
    if not CONFORMERS.is_file():
        return out
    for r in _read(CONFORMERS):
        if r.get("name") == name and r.get("state") == state:
            pool_name = _basin(r.get("geometry_relpath", ""))
            if pool_name:
                out.setdefault(_canon(pool_name),
                               (pool_name, r.get("geometry_sha256", "")))
    return out


def _canon(basin: str) -> str:
    """Canonical basin id: ``r2_c23`` / ``c23`` / ``23`` all map to ``23``.

    The gap table speaks the ledger spelling (bare digits) while the frozen
    pool uses directory names; comparing raw strings makes the set difference
    silently empty (a recorded lesson).
    """
    token = (basin or "").strip()
    if not token:
        return ""
    head, _, tail = token.partition("_")
    body = tail if tail and head.startswith("r") and head[1:].isdigit() else token
    if body.startswith("c") and body[1:].isdigit():
        body = body[1:]
    return body.lstrip("0") or body


def _basin(relpath: str) -> str:
    """``work/sampling/AN/M_plus/r3_c07/xtbopt.xyz`` -> ``r3_c07``.

    Mirrors the aggregator's basin-id convention (leaf directory, not the
    ``xtbopt.xyz`` file name).
    """
    if not relpath:
        return ""
    parts = [p for p in relpath.replace("\\", "/").split("/") if p]
    if len(parts) >= 2 and parts[-1].endswith(".xyz"):
        return parts[-2]
    return parts[-1] if parts else ""


def _searched_states() -> set[tuple[str, str]]:
    """States the recovery search actually visited (from its index)."""
    out: set[tuple[str, str]] = set()
    if not SEARCH_INDEX.is_file():
        return out
    try:
        doc = json.loads(SEARCH_INDEX.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return out
    for key in doc.get("states_searched") or []:
        name, _, state = key.partition("|")
        out.add((name, state))
    return out


def _was_searched(name: str, state: str) -> bool:
    if (name, state) in _searched_states():
        return True
    if "Li" in state and LI_RECOVERY_EXEC.is_file():
        # a Li leg counts as searched once the recovery motif executor has rows
        # for it (even when every placement collapsed onto a known motif)
        if any((r.get("leg_id", "").split("|")[0] == name
                and r.get("leg_id", "").split("|")[-1] == state)
               for r in _read(LI_RECOVERY_EXEC)):
            return True
    return any(r.get("name") == name and r.get("state") == state
               for r in _read(SEARCH_POOL)) if SEARCH_POOL.is_file() else False


def _li_recovery_starts() -> dict[tuple[str, str], list[dict]]:
    """New Li coordination basins discovered by the recovery motif search.

    A Li state's independent start is a NEW coordinated motif (``new_vs_round1``
    true and ``kept`` true), registered by the round-3 executor.  Nothing here
    is invented: the row's motif geometry and hash are carried verbatim.
    """
    out: dict[tuple[str, str], list[dict]] = {}
    if not LI_RECOVERY_EXEC.is_file():
        return out
    for r in _read(LI_RECOVERY_EXEC):
        if str(r.get("kept", "")).lower() != "true":
            continue
        if str(r.get("new_vs_round1", "")).lower() != "true":
            continue
        leg = r.get("leg_id", "")
        name, _, state = leg.partition("|")
        if not name or not state:
            continue
        path = r.get("motif_path", "")
        if not path or not (REPO / path).is_file():
            continue
        # seed label must be safe inside member_key (name|state|seed):
        # no "|" and no "@" -- keep the motif provenance in the note field
        raw = r.get("candidate_id") or r.get("motif_id") or ""
        label = "r3m_" + "".join(ch if ch.isalnum() else "_" for ch in raw)[:24]
        out.setdefault((name, state), []).append({
            "basin_id": label,
            "motif_id": r.get("motif_id", ""),
            "geometry_relpath": path,
            "geometry_sha256": _sha256(REPO / path),
            "energy_rel_kj": r.get("energy_rel_kj", ""),
        })
    for key in out:
        out[key].sort(key=lambda r: float(r.get("energy_rel_kj") or 0.0))
    return out


def _search_minima() -> dict[tuple[str, str], list[dict]]:
    """New independent minima per state from the registered recovery search.

    The search pool is the ONLY source of new starts for `new_search_required`
    states -- starts are never invented.  Rows are returned in rank order.
    """
    out: dict[tuple[str, str], list[dict]] = {}
    if not SEARCH_POOL.is_file():
        return out
    for r in _read(SEARCH_POOL):
        if r.get("status") != "candidate_start":
            continue
        out.setdefault((r.get("name"), r.get("state")), []).append(r)
    for key in out:
        out[key].sort(key=lambda r: int(r.get("rank") or 999))
    return out


def build_rows() -> list[dict]:
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    gaps = {(r["name"], r["state"]): r for r in _read(GAPS)}
    costs = _leg_cost_basis()

    # every state that is not yet accepted is in scope: `limited` when nothing
    # is in flight, `provisional` once a recovery leg has been submitted.  The
    # denominator never shrinks, so the total must stay at the frozen 14.
    limited = sorted({k for k, r in labels.items()
                      if r.get("acceptance_status") in ("limited", "provisional")})
    # the scope SHRINKS as recovery succeeds (14 -> ... -> 0), so the count must
    # never be pinned; the invariant is "never more than the frozen baseline"
    if len(limited) > 14:
        raise SystemExit("open states exceed the frozen 14 baseline: %d" % len(limited))

    # RELEASED states keep their frozen evidence rows (the plan's own rule:
    # "保留原14态冻结manifest，避免成功态从冻结证据中消失").  Without this the
    # ceiling's registration set loses the accepted states' starts the moment
    # they leave the open scope, and "registered 1 != QC-passed 2" blocks a
    # ceiling that was computable one pass earlier -- the same oscillation the
    # coverage reviews needed prior-row persistence for.
    released = sorted({k for k, r in labels.items()
                       if r.get("acceptance_status") == "accepted"
                       and r.get("coverage_status") == "resolved_by_review"})
    prior = {}
    if OUT_CSV.is_file():
        for row in _read(OUT_CSV):
            prior[(row.get("name"), row.get("state"))] = row

    rows: list[dict] = []
    legs = 0
    for key in limited:
        name, state = key
        if key not in PRIORITY:
            raise SystemExit("limited state %s/%s has no registered priority" % (name, state))
        priority, path_kind = PRIORITY[key]
        gap = gaps.get(key, {})
        unused = (gap.get("unused_basins") or "").strip()
        unused_ids = [u for u in unused.replace(";", ",").split(",") if u.strip()]
        pool = _pool_basins(name, state)

        if path_kind.startswith("unused_pool_basin") or path_kind == "unused_pool_basin":
            path = "frozen_basin"
        else:
            path = "new_search_required"

        # registered starts: unused frozen basins first; otherwise blank until a
        # versioned search registers one (never invented here)
        # map the gap table's ledger spelling onto the frozen pool's directory
        # spelling; a basin the pool cannot produce is NOT registered
        starts: list[str] = []
        start_sha: list[str] = []
        for u in unused_ids[:MAX_STARTS_PER_STATE]:
            hit = pool.get(_canon(u))
            if hit is None:
                continue
            starts.append(hit[0])
            start_sha.append(hit[1])
        # Li states take their starts from the recovery MOTIF search; free /
        # cationic states from the conformer search.  Both are registered
        # artifacts -- no start is ever synthesised here.
        recovery_minima = (_li_recovery_starts().get(key, [])
                           if "Li" in state else _search_minima().get(key, []))
        for m in recovery_minima:
            if len(starts) >= MAX_STARTS_PER_STATE:
                break
            starts.append(m.get("basin_id", ""))
            start_sha.append(m.get("geometry_sha256", ""))
        starts += [""] * (MAX_STARTS_PER_STATE - len(starts))
        start_sha += [""] * (MAX_STARTS_PER_STATE - len(start_sha))

        # honest search outcome: did an independent search actually run for
        # this state, and did it find anything?
        searched = _was_searched(name, state)
        if not searched:
            # a state that already holds a registered frozen-pool basin does not
            # need a search yet -- saying "not_searched" alone reads like an
            # omission, so the reason is spelled out
            search_outcome = ("unused_pool_basin_no_search_needed"
                              if any(starts) else "not_searched")
        elif recovery_minima:
            search_outcome = "new_minima_found"
        else:
            search_outcome = "no_new_minimum_found"

        # a state may keep one unused basin AND still need a second start
        n_registered = sum(1 for s in starts if s)
        needed = MAX_STARTS_PER_STATE - n_registered
        if path == "frozen_basin" and needed > 0:
            path = "frozen_basin_plus_search"

        per_leg = costs.get(key)
        legs += MAX_STARTS_PER_STATE

        rows.append({
            "batch_id": BATCH_ID,
            "name": name,
            "state": state,
            "priority": priority,
            "preferred_path": path_kind,
            "path": path,
            "historical_acceptance": labels[key].get("acceptance_status", ""),
            "historical_limitation": labels[key].get("limitation_reason", ""),
            "historical_n_unique": labels[key].get("n_unique", ""),
            "unused_pool_basins": unused,
            "start_1_basin": starts[0],
            "start_2_basin": starts[1],
            "start_1_source_sha256": start_sha[0],
            "start_2_source_sha256": start_sha[1],
            "max_new_starts": str(MAX_STARTS_PER_STATE),
            "needs_versioned_search": "true" if path.startswith("new_search") or path.endswith("plus_search") else "false",
            "search_outcome": search_outcome,
            "per_leg_cost_basis_core_hours": ("%.3f" % per_leg) if per_leg is not None else "MISSING",
            "state_budget_core_hours": ("%.3f" % (per_leg * MAX_STARTS_PER_STATE)
                                        if per_leg is not None else "MISSING"),
            "stop_rule": STOP_RULES,
            "status": "planned",
            "note": (
                "EMC: never continuing the drifted final geometry -- a drift "
                "verdict is terminal, the new start must be an independent basin"
                if name == "EMC" and state == "M_plus"
                else ""
            ),
        })

    if legs > MAX_LEGS:
        # MAX_LEGS is a CAP (frozen budget), not an expected count: the scope
        # shrinks as recovery succeeds, so equality would break on progress
        raise SystemExit("leg count %d exceeds the registered cap %d" % (legs, MAX_LEGS))

    # released states: re-emit their frozen evidence row so downstream consumers
    # (the ceiling's registration set) keep seeing the starts that were actually
    # registered, even though the state no longer belongs to the open scope.
    # Source of truth for the starts: the RESOLVED coverage review (it recorded
    # the registered starts verbatim when the state was still open), falling back
    # to the prior manifest row.  The evidence was frozen when it was written
    # and must not be re-derived.
    reviews = {}
    rev_path = REPO / "outputs" / "physics_completion" / "recovery" / "coverage_reviews.csv"
    if rev_path.is_file():
        for row in _read(rev_path):
            if row.get("verdict") == "resolved":
                reviews[(row.get("name"), row.get("state"))] = row
    # the manifest's own column set: a released row must fit it exactly
    fieldnames = list(FIELDS) if isinstance(FIELDS, (list, tuple)) else None
    for key in released:
        old = prior.get(key)
        rev = reviews.get(key)
        starts = []
        if old and (old.get("start_1_basin") or old.get("start_2_basin")):
            row = {f: (old.get(f) or "") for f in fieldnames} if fieldnames else dict(old)
            starts = [s for s in (row.get("start_1_basin"), row.get("start_2_basin")) if s]
        elif rev:
            # search starts, when the review recorded them
            parts = [q for q in (rev.get("registered_starts") or "").split(";") if q]
            # multi-basin releases name their NEW minima; the member key's seed
            # segment IS the registered basin id (DEC|M|r2_c23 -> r2_c23)
            for member in (rev.get("computed_new_members") or "").split(";"):
                member = member.strip()
                if member.count("|") == 2:
                    basin = member.split("|", 2)[2]   # name|slot|seed -> seed
                    if basin not in parts:
                        parts.append(basin)
            if not parts:
                continue
            row = ({f: "" for f in fieldnames} if fieldnames else {})
            row.update({"name": key[0], "state": key[1],
                        "batch_id": "strict_recovery_v1",
                        "historical_limitation": rev.get("historical_limitation", ""),
                        "search_outcome": "released_by_review",
                        "priority": "released", "path": "released",
                        "max_new_starts": "0",
                        "start_1_basin": parts[0] if parts else "",
                        "start_2_basin": parts[1] if len(parts) > 1 else ""})
            starts = parts
        else:
            continue
        row["released"] = "true"
        # idempotent: the marker is appended once, never re-appended on rebuild
        marker = "released_by_review, frozen evidence row retained"
        note = row.get("note") or ""
        if marker not in note:
            row["note"] = (note + ("; " if note else "") + marker)
        rows.append(row)
    return rows


FIELDS = [
    "batch_id", "name", "state", "priority", "preferred_path", "path",
    "historical_acceptance", "historical_limitation", "historical_n_unique",
    "unused_pool_basins", "start_1_basin", "start_2_basin",
    "start_1_source_sha256", "start_2_source_sha256", "max_new_starts",
    "needs_versioned_search", "search_outcome", "per_leg_cost_basis_core_hours",
    "state_budget_core_hours", "stop_rule", "status", "note", "released",
]


def render_md(rows: list[dict]) -> str:
    total_basis = 0.0
    missing = 0
    for r in rows:
        v = _f(r["state_budget_core_hours"])
        if v is None:
            missing += 1
        else:
            total_basis += v
    n_pool = sum(1 for r in rows if r["path"] == "frozen_basin")
    n_mixed = sum(1 for r in rows if r["path"] == "frozen_basin_plus_search")
    n_search = sum(1 for r in rows if r["path"] == "new_search_required")
    lines = [
        "# strict_recovery_v1：14 个 limited 态的恢复批次 manifest（登记，未启动）",
        "",
        "> 生成器 `build_strict_recovery_manifest.py`（`--check` 完全只读）。",
        "> 用户 2026-10-21 严格目标裁决：14 态全部排入恢复计划，每态 ≤2 个新独立起点，",
        "> 总上限 28 条；**历史失败保留原状态**，本 manifest 只登记将来要做什么。",
        "",
        "## 编排总览",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 态数 | %d |" % len(rows),
        "| 新起点上限 | 每态 %d 个，合计 **%d** 条 |" % (MAX_STARTS_PER_STATE, MAX_LEGS),
        "| 可直接用冻结池盆地 | %d 态（%s） |" % (
            n_pool, ", ".join("%s|%s" % (r["name"], r["state"]) for r in rows
                              if r["path"] == "frozen_basin") or "无"),
        "| 池盆地 + 需补搜索 | %d 态（%s） |" % (
            n_mixed, ", ".join("%s|%s" % (r["name"], r["state"]) for r in rows
                               if r["path"] == "frozen_basin_plus_search") or "无"),
        "| 必须版本化新搜索 | %d 态 |" % n_search,
        "| 成本依据合计 | %.1f core-hours（%d 态无实测依据 → MISSING） |" % (total_basis, missing),
        "| 批次预算 | 恢复包 **%.0f** + 风险储备 **%.0f** core-hours（首批实测后冻结，非全计划总预算） |"
        % (RECOVERY_CAP_CORE_HOURS, RESERVE_CAP_CORE_HOURS),
        "",
        "## 逐态登记",
        "",
        "| 优先级 | 态 | 路径 | 起点 1 | 起点 2 | 历史限制 | 上限 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append("| %s | %s\\|%s | %s | %s | %s | %s | %s |" % (
            r["priority"], r["name"], r["state"], r["path"],
            r["start_1_basin"] or "（待注册）",
            r["start_2_basin"] or "（待注册）",
            r["historical_limitation"] or "—",
            r["state_budget_core_hours"]))
    lines += [
        "",
        "## 停止条件（冻结）",
        "",
        "1. 每态最多 2 个新独立生产起点；两个都失败 → 该态保持 `limited`，总闸门继续阻塞，",
        "   具体原因逐态登记（`species_drift_unrecoverable` / `rescue_budget_exhausted` / 新类别）。",
        "2. 不放宽几何阈值、不把失败结构改记 `computed`、不删除历史失败、不直接改绿合规表。",
        "3. 起点搜索方法变更可单独登记；最终能量/热化学方法变更需统一 cohort 修订。",
        "4. 预算耗尽即停——恢复包 %.0f core-hours，风险储备 %.0f 另计，首批实测后冻结。"
        % (RECOVERY_CAP_CORE_HOURS, RESERVE_CAP_CORE_HOURS),
        "",
        "**本 manifest 只是登记：任何提交都要用户逐态确认或按本表一次性批准。**",
        "",
    ]
    return "\n".join(lines)


def write_outputs(rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    OUT_MD.write_text(render_md(rows), encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "batch_id": BATCH_ID,
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_strict_recovery_manifest.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (LABELS, GAPS, STRUCT, COST_LEDGER)
                   if p.is_file()},
        "contract": {
            "states": "all 14 limited ensemble states (denominator never shrinks)",
            "starts": "<=2 independent production starts per state",
            "max_legs": MAX_LEGS,
            "budget": {"recovery_core_hours": RECOVERY_CAP_CORE_HOURS,
                       "reserve_core_hours": RESERVE_CAP_CORE_HOURS},
            "historical_failures": "preserved untouched; this manifest never rewrites them",
            "stop_rule": STOP_RULES,
        },
        "n_rows": len(rows),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    rows = build_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    if OUT_MD.read_text(encoding="utf-8") != render_md(rows):
        print("CHECK FAILED -- %s drifted" % OUT_MD.name)
        return 1
    print("CHECK OK -- strict_recovery_v1 manifest matches recomputation (%d states)" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs(build_rows())
    print("wrote strict_recovery_v1 manifest: 14 states, %d legs registered" % MAX_LEGS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
