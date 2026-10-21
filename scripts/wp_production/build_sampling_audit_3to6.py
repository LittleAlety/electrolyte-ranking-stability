#!/usr/bin/env python
"""3 -> 6 sampling audit for the four designated molecules (plan §6.1 / v1.4 §5.2).

Designated set (frozen, registered before any screen): EMC / DEC / DME / TMP,
each in its four main states.  The audit answers ONE question honestly:

    does G_ensemble (and the derived ranking evidence) survive when the
    structure pool grows from round-1 (<=3) to the round-2 ceiling (<=6)?

It never fabricates structures to reach 6.  For every (molecule, state) it
records how many INDEPENDENT minima the frozen pools actually contain inside
the 6 kcal/mol window, then:

* ``executable``  -- enough distinct minima exist to run the 3 -> 6 extension
* ``pool_limited`` -- the pool tops out below 6: the audit records the REAL
  ceiling and the search evidence, and the state is marked ``sampling_limited``
  rather than padded with duplicates
* Li states additionally require a second-round motif search when the current
  pool cannot supply >=6 independent coordination motifs (plan §5.2)

Outputs
-------
outputs/physics_completion/sampling/sampling_audit_3to6.csv    per-state plan
outputs/physics_completion/sampling/sampling_audit_3to6.md     human-readable
outputs/physics_completion/sampling/sampling_audit_index.json  inputs hashes + stale flag
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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
LI_SCREEN = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
#: Round-2 Li motif search run record (plan item 7).  A leg appears here only
#: after the executor actually measured it; a leg whose registered parents could
#: not be hash-verified keeps its round-1 pool size and is marked as such.
LI_ROUND2 = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_round2_exec_index.json"
CONFORMERS = SAMPLING / "sampling_conformer_set.csv"
STRUCTURES = ENS / "production_ensemble_structures.csv"
OUT_CSV = SAMPLING / "sampling_audit_3to6.csv"
OUT_MD = SAMPLING / "sampling_audit_3to6.md"
OUT_INDEX = SAMPLING / "sampling_audit_index.json"

#: Frozen designated audit set (plan §3: 4 sampling-audit molecules).
AUDIT_MOLECULES = ("EMC", "DEC", "DME", "TMP")
STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
LI_STATES = ("LiM_plus", "LiM_2plus")
WINDOW_KCAL = 6.0
KJ_PER_KCAL = 4.184
ROUND2_CEILING = 6
ROUND1_CAP = 3


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def num(value):
    """CSV/JSON values arrive as STRINGS: convert explicitly (project lesson)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def free_pool_counts():
    """(name, state) -> (window_count, round1_count) for the free-state pool."""
    counts = {}
    if not CONFORMERS.is_file():
        return counts
    rows = list(csv.DictReader(CONFORMERS.open(encoding="utf-8")))
    for r in rows:
        name = r.get("name", "")
        if name not in AUDIT_MOLECULES:
            continue
        rel = num(r.get("rel_kcal"))
        if rel is None or rel > WINDOW_KCAL:
            continue
        key = (name, r.get("state", ""))
        window, round1 = counts.get(key, (0, 0))
        counts[key] = (window + 1, round1 + (1 if str(r.get("selected_round1", "")).strip().lower() == "true" else 0))
    return counts


def li_pool_counts():
    """(name, state) -> kept motif count inside the window."""
    counts = {}
    if not LI_SCREEN.is_file():
        return counts
    doc = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
    window_kj = WINDOW_KCAL * KJ_PER_KCAL
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        if name not in AUDIT_MOLECULES:
            continue
        kept = leg.get("kept") or []
        inside = [k for k in kept
                  if num(k.get("energy_rel_kj")) is not None
                  and num(k.get("energy_rel_kj")) <= window_kj
                  and k.get("status") == "ok"
                  and k.get("_intact", True)]
        counts[(name, leg.get("state", ""))] = len(inside)
    return counts


def li_round2_counts():
    """(name, state) -> measured round-2 pool, or {} when the search did not run.

    The measured ceiling is ``round1_kept + motifs that are not a round-1 kept
    motif`` (class + heavy-atom RMSD), so a placement that collapses back onto a
    known minimum never inflates the pool.  ``not_measured`` legs (all parents
    failed hash verification) are reported separately and never padded.
    """
    out = {}
    if not LI_ROUND2.is_file():
        return out
    doc = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
    # Fail closed when the run record and its CSV disagree: the audit would
    # otherwise size the Li pools from a stale execution while the bytes on disk
    # say something else (same class of error as pairing a rebuilt plan with an
    # older run).
    want = doc.get("exec_csv_sha256")
    exec_csv = LI_ROUND2.parent / str(doc.get("exec_csv", "")).split("/")[-1]
    if want:
        if not exec_csv.is_file() or sha256_file(exec_csv) != want:
            raise SystemExit("round-2 Li execution record does not match its CSV: "
                             "re-run run_li_motif_round2.py before rebuilding the audit")
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        if name not in AUDIT_MOLECULES:
            continue
        out[(name, leg.get("state", ""))] = {
            "status": leg.get("status", ""),
            "round1_kept": int(leg.get("round1_kept_motifs") or 0),
            "measured_ceiling": int(leg.get("measured_ceiling") or 0),
            "new_basins": int(leg.get("new_independent_basins") or 0),
            "registered_bound": int(leg.get("round2_ceiling_upper_bound") or 0),
            "parents_used": len(leg.get("parents_used") or []),
            "parents_registered": int(leg.get("parents_registered") or 0),
            "collapsed": int(leg.get("collapsed_onto_round1") or 0),
        }
    return out


def production_members():
    """(name, state) -> number of accepted/unique members already in the ensemble."""
    counts = {}
    if not STRUCTURES.is_file():
        return counts
    for r in csv.DictReader(STRUCTURES.open(encoding="utf-8")):
        if r["member_role"] != "primary":
            continue
        counts[(r["name"], r["slot"])] = 1
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and compare, never write")
    args = ap.parse_args(argv)

    free = free_pool_counts()
    li = li_pool_counts()
    li2 = li_round2_counts()
    primaries = production_members()

    rows = []
    for name in AUDIT_MOLECULES:
        for state in STATES:
            measured = li2.get((name, state)) if state in LI_STATES else None
            measured_note = ""
            if state in LI_STATES:
                pool = li.get((name, state), 0)
                pool_kind = "li_motif"
                needs_motif_search = pool < ROUND2_CEILING
                if measured is not None and measured["status"] == "executed":
                    # The measured value replaces the round-1 count ONLY upward:
                    # a measurement can add basins, never delete round-1 ones.
                    pool = max(pool, measured["measured_ceiling"])
                    pool_kind = "li_motif_round2_measured"
                    needs_motif_search = False
                    measured_note = ("; round-2 search measured %d independent minima "
                                     "(%d new, %d collapsed onto round-1, %d/%d parents verified)"
                                     % (measured["measured_ceiling"], measured["new_basins"],
                                        measured["collapsed"], measured["parents_used"],
                                        measured["parents_registered"]))
                elif measured is not None:
                    needs_motif_search = False
                    measured_note = ("; round-2 search could not run: 0 of %d registered parents "
                                     "passed hash verification, so the pool stays at the round-1 "
                                     "count (not padded, not replaced)"
                                     % measured["parents_registered"])
            else:
                pool = free.get((name, state), (0, 0))[0]
                pool_kind = "free_conformer"
                needs_motif_search = False
            if state not in LI_STATES:
                round1 = free.get((name, state), (0, 0))[1]
            elif measured is not None and measured["status"] == "executed":
                round1 = min(measured["round1_kept"], pool)   # the leg's REAL round-1 count
            else:
                round1 = min(ROUND1_CAP, pool)
            ceiling = min(ROUND2_CEILING, pool)
            have_primary = 1 if (name, state) in primaries else 0
            executable = ceiling > round1 or (ceiling >= ROUND2_CEILING)
            if pool >= ROUND2_CEILING:
                status = "executable"
                note = "pool supplies >=6 independent minima inside the window"
            elif executable:
                status = "executable_partial"
                note = ("pool tops out at %d independent minima: the 3->6 extension runs to "
                        "that real ceiling, never padded" % ceiling)
            else:
                status = "sampling_limited"
                note = ("pool holds only %d independent minimum inside the 6 kcal/mol window; "
                        "no honest 3->6 extension is possible" % pool)
            if state in LI_STATES and needs_motif_search:
                note += "; Li state requires a second-round motif search (plan §5.2)"
            note += measured_note
            rows.append({
                "mol_id": "", "name": name, "state": state,
                "pool_kind": pool_kind,
                "round1_structures": str(round1),
                "pool_independent_minima": str(pool),
                "round2_ceiling": str(ceiling),
                "has_primary": str(have_primary),
                "extension_available": "true" if ceiling > round1 else "false",
                "needs_second_round_motif_search": "true" if needs_motif_search else "false",
                "status": status,
                "note": note,
            })

    fieldnames = list(rows[0])
    def render_csv():
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()

    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    lines = [
        "# 3→6 采样审计计划（EMC / DEC / DME / TMP × 四主态）",
        "",
        "> 生成器：`scripts/wp_production/build_sampling_audit_3to6.py`",
        "> 冻结窗口 6 kcal/mol；round-1 上限 3；round-2 上限 6。**绝不用重复构象凑数。**",
        "",
        "## 结论",
        "",
        "| 状态 | 状态数 | 含义 |",
        "| --- | --- | --- |",
        f"| executable | {by_status.get('executable', 0)} | 池内 ≥6 个独立极小，可完整执行 3→6 |",
        f"| executable_partial | {by_status.get('executable_partial', 0)} | 池内不足 6，按真实上限执行 |",
        f"| sampling_limited | {by_status.get('sampling_limited', 0)} | 池内仅 1–3 个独立极小，无法诚实扩样 |",
        "",
        "## 逐态明细",
        "",
        "| 分子 | 态 | 池类型 | round1 | 池内独立极小 | round2 上限 | 可扩样 | 需第二轮 motif 搜索 | 判定 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], r["state"], r["pool_kind"], r["round1_structures"],
            r["pool_independent_minima"], r["round2_ceiling"],
            r["extension_available"], r["needs_second_round_motif_search"], r["status"]))
    lines += [
        "",
        "## 判读规则（预注册，不事后调整）",
        "",
        "1. **不复制构象凑足 6**：池内独立极小不足时，记录真实数量与搜索证据，状态记 `sampling_limited`。",
        "2. **Li 态**：第二轮 motif 搜索（`run_li_motif_round2.py`，独立的中性盆地做父几何）**已执行**，"
        "本表的 Li 池数取**实测**值（round-1 保留 + 真新盆地，同类重原子 RMSD 去重）；"
        "父体哈希核验不过的腿保持 round-1 池数并注明原因，绝不补数。",
        "3. **比较口径**：3 结构 vs 上限结构的 `G_ensemble`、氧化轴、Li 条件轴与 Top-k 集合变化；"
        "本轮按 2026-10-19 用户决定只报告这些差异，不判采样收敛；生产级独立容差尚未冻结。"
        " `sampling_limited` 只表示当前搜索池/扩样覆盖受限，不是数值收敛结论。",
        "4. 本表只登记**计划与可行性**；实际扩样结果另表登记，不得把本表当结果。",
        "",
    ]
    md = "\n".join(lines)

    rendered = ((OUT_CSV, render_csv()), (OUT_MD, md))
    if args.check:
        failures = []
        for path, text in rendered:
            if not path.is_file():
                failures.append("missing: " + path.name)
            elif path.read_bytes() != text.encode("utf-8"):
                failures.append("differs: " + path.name)
        if failures:
            for f in failures:
                print("STALE: " + f)
            return 1
        print("CHECK OK -- sampling audit outputs match recomputation")
        return 0

    SAMPLING.mkdir(parents=True, exist_ok=True)
    for path, text in rendered:
        path.write_text(text, encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {p.name: sha256_file(p) for p in (CONFORMERS, LI_SCREEN, LI_ROUND2, STRUCTURES)
                   if p.is_file()},
        "outputs": {p.name: sha256_file(p) for p in (OUT_CSV, OUT_MD)},
        "rules": {"window_kcal": WINDOW_KCAL, "round1_cap": ROUND1_CAP,
                  "round2_ceiling": ROUND2_CEILING,
                  "designated_molecules": list(AUDIT_MOLECULES),
                  "no_padding": "duplicate structures never count toward the ceiling"},
        "states": len(rows),
        "by_status": by_status,
    }
    OUT_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    print("audit states=%d %s" % (len(rows), by_status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
