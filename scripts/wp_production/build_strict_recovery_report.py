"""Per-batch outcome report for strict_recovery_v1.

Consolidates, for every one of the 14 not-yet-accepted states:

* the registered independent starts and how many real attempts they consumed
  (the frozen budget allows at most two per member);
* the latest ledger outcome per member (computed / qc_failed + failure class);
* the coverage-review verdict (the ONLY route out of ``limited``);
* the resulting ensemble status.

It reports the observed state -- it decides nothing and launches nothing, and it
never turns a failure into a pass.  A leg that exhausted its attempts is printed
with its reason, exactly as the plan requires ("总闸门继续阻塞，保留原因").

    .venv\\Scripts\\python.exe -X utf8 scripts/wp_production/build_strict_recovery_report.py
    ... --check            # READ-ONLY: recompute in memory, byte-compare
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

LABELS = ENS / "production_ensemble_labels.csv"
STRUCTS = ENS / "production_ensemble_structures.csv"
MANIFEST = RECOVERY / "strict_recovery_v1_manifest.csv"
COVERAGE = RECOVERY / "coverage_reviews.csv"

OUT_MD = RECOVERY / "strict_recovery_v1_report.md"
OUT_INDEX = RECOVERY / "strict_recovery_v1_report_index.json"

MAX_ATTEMPTS = 2


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _latest_by_member(rows: list[dict]) -> dict[str, dict]:
    """Rows per recovery member, split into "latest attempt" and "last result".

    A queued remedy inserts a PENDING row at a higher attempt index.  Reporting
    only the highest attempt would then hide the completed failure entirely and
    make the batch look like "nothing has run".  So both are kept:

    * ``latest``  -- highest attempt index (may be pending: a remedy in flight);
    * ``result``  -- highest attempt index that actually RAN (has a log hash).

    The report must never let a planned row stand in for a real outcome.
    """
    latest: dict[str, dict] = {}
    result: dict[str, dict] = {}
    for r in rows:
        if r.get("member_role") != "recovery_v1_start":
            continue
        key = r["member_key"]
        cur = latest.get(key)
        if cur is None or int(r.get("attempt") or 0) > int(cur.get("attempt") or 0):
            latest[key] = r
        if r.get("log_sha256"):
            prev = result.get(key)
            if prev is None or int(r.get("attempt") or 0) > int(prev.get("attempt") or 0):
                result[key] = r
    return {"latest": latest, "result": result}


def _attempts_by_member(rows: list[dict]) -> dict[str, int]:
    """How many REAL calculations each recovery member has had.

    Counted by distinct ``log_sha256`` (a real run produces a log); a planned or
    pending row has none, so it never consumes budget.
    """
    seen: dict[str, set] = defaultdict(set)
    for r in rows:
        if r.get("member_role") != "recovery_v1_start":
            continue
        if r.get("log_sha256"):
            seen[r["member_key"]].add(r["log_sha256"])
    return {k: len(v) for k, v in seen.items()}


def collect() -> dict:
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    man = {(r["name"], r["state"]): r for r in _read(MANIFEST)}
    cov = {(r["name"], r["state"]): r for r in _read(COVERAGE)}
    structs = _read(STRUCTS)
    split = _latest_by_member(structs)
    latest, result = split["latest"], split["result"]
    attempts = _attempts_by_member(structs)

    members_by_state: dict[tuple, list[str]] = defaultdict(list)
    for key in latest:
        name, slot, _seed = key.split("|")
        members_by_state[(name, slot)].append(key)

    all_legs = []
    for key, detail_keys in members_by_state.items():
        for leg in detail_keys:
            row = latest[leg]
            done = result.get(leg)
            all_legs.append({
                "state": "%s|%s" % key,
                "member_key": leg,
                "status": row.get("status", ""),
                "failure_class": row.get("failure_class", ""),
                "last_result_status": (done or {}).get("status", ""),
                "last_result_class": (done or {}).get("failure_class", ""),
                "note": (row.get("convergence_note") or "")[:80],
                "attempts_used": attempts.get(leg, 0),
                "attempts_left": max(0, MAX_ATTEMPTS - attempts.get(leg, 0)),
            })

    released = []      # states that this batch moved from limited to accepted
    for key, r in sorted(labels.items()):
        if r.get("coverage_status") != "resolved_by_review":
            continue
        released.append({
            "state": "%s|%s" % key,
            "acceptance_status": r.get("acceptance_status", ""),
            "n_unique": r.get("n_unique", ""),
            "n_limited": r.get("n_qc_failed", ""),
            "g_ensemble_eh": r.get("g_ensemble_eh", ""),
        })

    states = []
    for key in sorted(k for k, r in labels.items() if r.get("acceptance_status") != "accepted"):
        name, state = key
        m = man.get(key, {})
        starts = [s for s in (m.get("start_1_basin"), m.get("start_2_basin")) if s]
        legs = sorted(members_by_state.get(key, []))
        detail = []
        for leg in legs:
            row = latest[leg]
            done = result.get(leg)
            detail.append({
                "member_key": leg,
                "status": row.get("status", ""),
                "failure_class": row.get("failure_class", ""),
                "note": (row.get("convergence_note") or "")[:80],
                "last_result_status": (done or {}).get("status", ""),
                "last_result_class": (done or {}).get("failure_class", ""),
                "attempts_used": attempts.get(leg, 0),
                "attempts_left": max(0, MAX_ATTEMPTS - attempts.get(leg, 0)),
            })
        states.append({
            "state": "%s|%s" % key,
            "acceptance_status": labels[key].get("acceptance_status", ""),
            "coverage_verdict": cov.get(key, {}).get("verdict", "no_review"),
            "search_outcome": m.get("search_outcome", ""),
            "registered_starts": len(starts),
            "max_new_starts": int(m.get("max_new_starts") or 0),
            "legs": detail,
        })
    totals = Counter(s["acceptance_status"] for s in labels.values())
    return {"states": states, "totals": dict(totals),
            "all_legs": all_legs, "released": released}


def render(doc: dict) -> str:
    states = doc["states"]
    totals = doc["totals"]
    accepted = totals.get("accepted", 0)
    legs_all = doc.get("all_legs") or []   # every leg, incl. released states
    statuses = Counter(leg["last_result_status"] or "never_ran" for leg in legs_all)
    classes = Counter(leg["last_result_class"] for leg in legs_all if leg["last_result_class"])
    in_flight = Counter(leg["status"] for leg in legs_all if leg["status"] == "pending")
    verdicts = Counter(s["coverage_verdict"] for s in states)

    lines = [
        "# strict_recovery_v1 批次结果报告",
        "",
        "> 生成器 `build_strict_recovery_report.py`（`--check` 完全只读）。",
        "> 只报告观测到的状态：**不把失败改写成通过、不清空 n_limited、不放宽任何阈值**。",
        "",
        "## 系综口径",
        "",
        "| 状态 | 态数 |",
        "|---|---|",
    ]
    for k in ("accepted", "provisional", "limited"):
        lines.append("| %s | %d |" % (k, totals.get(k, 0)))
    lines += [
        "",
        "分母固定 48；未 accepted 共 **%d** 态（`provisional` = 有登记补救在飞，`limited` = 首轮搜索耗尽）。" % len(states),
        "",
        "## 恢复腿终局统计（按**最后一次真实运行**；规划中的补救另计）",
        "",
        "| 状态 | 腿数 |",
        "|---|---|",
    ]
    for k, v in sorted(statuses.items()):
        lines.append("| `%s` | %d |" % (k, v))
    lines += ["", "**在飞补救（已提交、尚未产出结果）**：%d 条腿" % sum(in_flight.values()), ""]
    if classes:
        lines += ["", "失败类分布（最后一次真实运行）：", ""]
        lines += ["- `%s`: %d" % (k, v) for k, v in sorted(classes.items())]
    lines += [
        "",
        "## 覆盖复核裁决（离开 `limited` 的唯一通道）",
        "",
        "| verdict | 态数 |",
        "|---|---|",
    ]
    for k, v in sorted(verdicts.items()):
        lines.append("| `%s` | %d |" % (k, v))
    released = doc.get("released") or []
    lines += [
        "",
        "## 本批放行的态（覆盖复核 resolved）",
        "",
    ]
    if released:
        lines += ["| 态 | 系综状态 | n_unique | 历史 n_limited（保留） | g_ensemble (Eh) |",
                  "|---|---|---|---|---|"]
        for r in released:
            lines.append("| `%s` | `%s` | %s | **%s** | %s |" % (
                r["state"], r["acceptance_status"], r["n_unique"], r["n_limited"],
                (r["g_ensemble_eh"] or "")[:16]))
        lines += ["",
                  "`n_limited` 一列是**故意保留的历史计数**：这些态经复核放行，"
                  "但「曾经有限制」这件事仍然记在账本里——不是清空它。", ""]
    else:
        lines += ["（尚无）", ""]

    lines += [
        "",
        "## 逐态明细（仅未 accepted 的态）",
        "",
        "| 态 | 系综状态 | 复核 verdict | 搜索结论 | 注册起点 | 腿（尝试次数 / 最后真实结果 / 当前） |",
        "|---|---|---|---|---|---|",
    ]
    for s in states:
        legs = "<br>".join(
            "%s（%d/%d；结果 %s%s；当前 %s）" % (
                leg["member_key"].split("|", 1)[1].replace("|", "\|"),
                leg["attempts_used"], MAX_ATTEMPTS,
                leg["last_result_status"] or "未跑",
                "/" + leg["last_result_class"] if leg["last_result_class"] else "",
                leg["status"] or "-")
            for leg in s["legs"]) or "—（无恢复腿）"
        lines.append("| %s | `%s` | `%s` | `%s` | %d | %s |" % (
            s["state"].replace("|", "\\|"), s["acceptance_status"],
            s["coverage_verdict"], s["search_outcome"] or "-",
            s["registered_starts"], legs))
    exhausted = [s for s in states if s["registered_starts"] == 0]
    lines += [
        "",
        "## 本轮无法恢复的态（需换搜索方法，不在本批预算内）",
        "",
    ]
    if exhausted:
        for s in exhausted:
            lines.append("- `%s` — %s" % (s["state"], s["search_outcome"] or "未搜索"))
    else:
        lines.append("（无）")
    near = [leg for leg in legs_all
            if leg["status"] == "technical_complete_qc_failed" and leg["attempts_left"] == 0]
    lines += [
        "",
        "## 尝试预算已用尽的腿（不再自动重试，保留原因）",
        "",
    ]
    if near:
        for leg in near:
            lines.append("- `%s` — `%s`：%s"
                         % (leg["member_key"], leg["failure_class"], leg["note"] or "（无附注）"))
    else:
        lines.append("（无）")
    lines += [
        "",
        "**结论口径**：本报告不改变任何验收判定。系综达到 %d/48；"
        "`plan_overall_complete` 与 WP6 只有在 48/48 时才可能开闸。" % accepted,
        "",
    ]
    return "\n".join(lines)


def write_outputs() -> None:
    doc = collect()
    RECOVERY.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render(doc), encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_strict_recovery_report.py",
        "inputs": {str(p.relative_to(REPO)): _sha(p)
                   for p in (LABELS, STRUCTS, MANIFEST, COVERAGE) if p.is_file()},
        "totals": doc["totals"],
        "states_open": len(doc["states"]),
        "rule": ("report-only: never rewrites a failure as a pass, never clears n_limited, "
                 "never relaxes a threshold"),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    disk = OUT_MD.read_text(encoding="utf-8") if OUT_MD.is_file() else ""
    if disk != render(collect()):
        print("CHECK FAILED -- %s drifted" % OUT_MD.name)
        return 1
    print("CHECK OK -- recovery report matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    doc = collect()
    print("strict recovery report: %d open states, totals=%s"
          % (len(doc["states"]), doc["totals"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
