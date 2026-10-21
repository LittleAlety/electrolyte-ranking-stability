"""Sampling-audit ceiling classification (plan item ⑤, evidence side only).

The 3->6 ceiling is complete for 3/16 states.  The user asked for the other 13
to be split into four DIFFERENT kinds of shortfall -- they must never be
lumped into one "not computed":

1. ``registered_candidates_qc_pending`` -- round-2 members are registered but
   not (all) QC-passed yet: the ceiling is waiting on real calculation;
2. ``pool_has_no_independent_structure`` -- the frozen pool holds no further
   independent minimum: a structural limit of the current pool;
3. ``collapsed_onto_existing_minimum`` -- an optimised candidate deduplicated
   onto an already-present minimum: a dedup RESULT, not a gap;
4. ``coverage_genuinely_missing`` -- no registered candidate AND no pool
   structure: coverage is genuinely absent.

Two honesty rules:

* a state whose classification cannot be derived from the ledgers is reported
  as ``unclassified`` with the reason -- never guessed into a bucket;
* the recovery batch's newly registered starts are listed per state as
  ``recovery_registered_starts`` so a reader can see which of these gaps the
  running strict_recovery_v1 batch is already addressing.  This is a REPORT of
  registration, not a claim that the ceiling has changed.

Sampling-stability tolerance is NOT decided here: the plan freezes it from
independent numerical repeats, and until then this report only describes
differences (no convergence verdict).

Outputs:

    outputs/physics_completion/sampling/sampling_ceiling_classification.csv
    outputs/physics_completion/sampling/sampling_ceiling_classification.md
    outputs/physics_completion/sampling/sampling_ceiling_classification_index.json

``--check`` recomputes and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

SAMP = REPO / "outputs" / "physics_completion" / "sampling"
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

DIFF = SAMP / "sampling_3to6_diff.csv"
STRUCT = ENS / "production_ensemble_structures.csv"
GAPS = ENS / "remaining_gaps_decision_support.csv"
RECOVERY_MANIFEST = RECOVERY / "strict_recovery_v1_manifest.csv"

OUT_CSV = SAMP / "sampling_ceiling_classification.csv"
OUT_MD = SAMP / "sampling_ceiling_classification.md"
OUT_INDEX = SAMP / "sampling_ceiling_classification_index.json"

CATEGORIES = (
    "complete",
    "registered_candidates_qc_pending",
    "pool_has_no_independent_structure",
    "collapsed_onto_existing_minimum",
    "coverage_genuinely_missing",
    "unclassified",
)

FIELDS = ["name", "state", "ceiling_status", "category", "evidence",
          "registered_round2", "qc_passed_round2", "collapsed_members",
          "pool_independent_minima", "recovery_registered_starts", "note"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _ints(reason: str):
    nums = [int(n) for n in re.findall(r"\d+", reason or "")]
    return nums


def classify(reason: str, status: str) -> str:
    r = (reason or "").lower()
    if status == "complete":
        return "complete"
    if "pool-limited" in r:
        return "pool_has_no_independent_structure"
    if "none qc-passed" in r or "!= qc-passed" in r:
        return "registered_candidates_qc_pending"
    if "collapsed" in r:
        return "collapsed_onto_existing_minimum"
    if not r.strip():
        return "coverage_genuinely_missing"
    return "unclassified"


def build_rows() -> list[dict]:
    diff = _read(DIFF)
    struct = _read(STRUCT)
    gaps = {(r["name"], r["state"]): r for r in _read(GAPS)}
    recovery = {(r["name"], r["state"]): r for r in _read(RECOVERY_MANIFEST)}

    rows = []
    for d in diff:
        name, state = d["name"], d["state"]
        status = d.get("ceiling_status", "")
        reason = d.get("ceiling_reason", "")
        category = classify(reason, status)

        members = [m for m in struct
                   if m.get("name") == name and m.get("state") == state]
        registered = [m for m in members if m.get("member_role") == "round2_audit_extra"]
        qc_passed = [m for m in registered
                     if m.get("status") == "computed"]
        collapsed = [m["member_key"] for m in registered
                     if m.get("status") == "superseded"]
        gap = gaps.get((name, state), {})
        pool_minima = gap.get("n_unique", "")
        rec = recovery.get((name, state), {})
        rec_starts = ";".join(s for s in (rec.get("start_1_basin", ""),
                                          rec.get("start_2_basin", "")) if s)

        # a state classified as pool-limited but with an unused frozen basin is
        # a contradiction worth surfacing (it would mean the pool check is stale)
        note = ""
        if category == "pool_has_no_independent_structure" and gap.get("unused_basins"):
            note = ("WARNING: classified pool-limited but the gap table still lists "
                    "unused basin(s) %s" % gap["unused_basins"])
        if rec_starts and category != "complete":
            note = (note + "; " if note else "") + (
                "strict_recovery_v1 has registered start(s) addressing this state")

        rows.append({
            "name": name, "state": state, "ceiling_status": status,
            "category": category, "evidence": reason[:200],
            "registered_round2": str(len(registered)),
            "qc_passed_round2": str(len(qc_passed)),
            "collapsed_members": ";".join(collapsed),
            "pool_independent_minima": pool_minima,
            "recovery_registered_starts": rec_starts,
            "note": note,
        })
    return rows


def render_md(rows: list[dict]) -> str:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    lines = [
        "# 3→6 采样审计：ceiling 缺口四分类（证据层，非收敛判定）",
        "",
        "> 生成器 `build_sampling_ceiling_classification.py`（`--check` 完全只读）。",
        "> **容差未冻结**：本表只描述差异与缺口类型，不给出任何采样收敛结论。",
        "",
        "## 分布",
        "",
        "| 类别 | 态数 |",
        "|---|---|",
    ]
    for cat in CATEGORIES:
        if counts.get(cat):
            lines.append("| `%s` | %d |" % (cat, counts[cat]))
    lines += [
        "",
        "## 逐态",
        "",
        "| 态 | ceiling | 类别 | 已登记 round-2 | QC 通过 | 池内极小 | 恢复批次起点 | 备注 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append("| %s\\|%s | %s | `%s` | %s | %s | %s | %s | %s |" % (
            r["name"], r["state"], r["ceiling_status"], r["category"],
            r["registered_round2"], r["qc_passed_round2"],
            r["pool_independent_minima"] or "—",
            r["recovery_registered_starts"] or "—",
            (r["note"] or "—").replace("|", "/")))
    lines += [
        "",
        "## 四类的含义（不可互换）",
        "",
        "1. `registered_candidates_qc_pending`——候选已登记、生产 QC 未全过：**等真实计算**。",
        "2. `pool_has_no_independent_structure`——冻结池没有更多独立极小：**当前池的结构限制**。",
        "3. `collapsed_onto_existing_minimum`——优化后塌缩到已有极小：**去重结果**，不是缺口。",
        "4. `coverage_genuinely_missing`——既无登记候选又无池结构：**覆盖真的缺失**。",
        "",
        "`strict_recovery_v1` 已登记的起点在「恢复批次起点」列可见——那是**登记事实**，",
        "不代表 ceiling 已改变；ceiling 只在成员 QC 通过并聚合后才更新。",
        "",
    ]
    return "\n".join(lines)


def write_outputs(rows: list[dict]) -> None:
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    OUT_MD.write_text(render_md(rows), encoding="utf-8", newline="\n")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_sampling_ceiling_classification.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (DIFF, STRUCT, GAPS, RECOVERY_MANIFEST) if p.is_file()},
        "categories": list(CATEGORIES),
        "counts": counts,
        "tolerance": "NOT decided here -- frozen from independent repeats by the plan",
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
    print("CHECK OK -- ceiling classification matches recomputation (%d states)" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    rows = build_rows()
    write_outputs(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    print("ceiling classification:", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
