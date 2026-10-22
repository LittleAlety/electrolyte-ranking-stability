"""B-group pilot preregistration: production-level coverage diagnosis for AN/DMC M_plus.

User ruling (2026-10-21, B-group): start with the two most promising states of
the cheap-search-found-nothing set -- AN|M_plus and DMC|M_plus -- before any
wider diagnostic.  This generator registers that pilot EXACTLY as the plan
requires (版本化预注册：方法、成本上限、停止条件) and launches nothing.

Method choice rationale (per the plan's own option list):
* GFN2 already collapsed 64+256 independent starts onto one basin -- repeating
  it is excluded by the plan ("不重复大批相同 GFN2 搜索");
* direct DFT multi-start is the honest production-level probe for a CATIONIC
  conformer state: take the frozen pool's UNUSED conformers (they exist in the
  pool but were never run at production level), give each a full
  wB97X-D4/def2-TZVPD/SMD VeryTightOpt+AnFreq leg, and let the DFT surface
  decide whether a second basin exists;
* a torsion scan is the fallback if the pool has no unused conformers.

Stop rule (frozen):
* at most 2 production legs per state (the plan's per-state cap);
* if both collapse onto the known minimum -> `production_single_basin`,
  which upgrades the screening-level finding to the production level -- a
  much stronger statement than GFN2 collapse, and still not a proof that
  "all search methods fail" (the plan's own caveat);
* any new basin enters the normal coverage-review machinery.

Budget cap: 2 states x 2 legs x ~12 core-hours = ~48 core-hours (the measured
M_plus production average), inside the recovery pack's remaining ~430.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

POOL = REPO / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"
OUT_MD = RECOVERY / "bgroup_pilot_preregistration.md"
OUT_INDEX = RECOVERY / "bgroup_pilot_preregistration_index.json"

STATES = [("AN", "M_plus"), ("DMC", "M_plus")]
MAX_LEGS_PER_STATE = 2
BUDGET_NOTE_CORE_HOURS = 48.0


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unused_conformers(name: str, state: str) -> list[dict]:
    """Frozen-pool conformers of this state that never ran at production level.

    The structures table carries every member that DID run; a pool conformer
    whose seed appears in no member key is unused.  The pool's seed is the
    directory name (r2_cNN / cNN); the ledger's is the bare number -- the
    canonical basin-key mapping (strip rN_ prefix, strip c, strip leading
    zeros) makes the two comparable, exactly as the manifest builder does.
    """
    import re

    def _canon(seed: str) -> str:
        s = re.sub(r"^[rd]\d+_", "", seed)
        s = re.sub(r"^c", "", s)
        return str(int(s)) if s.isdigit() else s

    used = set()
    for r in _rows(ENS / "production_ensemble_structures.csv"):
        if r.get("name") == name and r.get("slot") == state:
            used.add(_canon(r.get("seed", "")))
    # the primary's production geometry IS a pool conformer (usually rank 1)
    out = []
    for r in _rows(POOL):
        if r.get("name") != name or r.get("state") != state:
            continue
        if _canon(r.get("geometry_relpath", "").split("/")[-2] or "") in used:
            continue
        out.append(r)
    return out


def render() -> str:
    lines = [
        "# B组试点预注册：AN/DMC 的 M_plus 生产级覆盖诊断（未启动）",
        "",
        "> 生成器 `build_bgroup_pilot_preregistration.py`（`--check` 完全只读）。",
        "> 用户裁决（2026-10-21）：「先做 2-3 个最可能的态（如 AN/DMC 的 M_plus），结果好再扩」。",
        "",
    ]
    pool_avail = {s: bool(unused_conformers(*s)) for s in STATES}
    if all(pool_avail.values()):
        lines += [
            "## 方法：直接 DFT 多起点",
            "",
            "GFN2 已在 64+256 个独立起点上塌缩到单一盆地——按计划不得重复。取冻结池里",
            "**未上过生产级**的构象各跑一条完整生产腿，让生产势面自己回答「是否存在第二盆地」。",            "",
        ]
    else:
        lines += [
            "## 方法结论（由冻结池数据自动给出，非人手设定）",
            "",
            "AN 与 DMC 的 M_plus 在冻结池里的构象**已全部上过生产级**——直接 DFT 多起点",
            "**无候选可用**。按计划的方法清单，这两态的生产级覆盖诊断应改走**相关扭转扫描**",
            "（对已收敛极小的关键柔性二面角做系统扫描，生产级评估各扭转构型是否落入新盆地）。",
            "该路径的候选、预算与停止条件须**另行登记**；本稿不擅自扩大范围。",
            "",
        ]
    lines += [
        "## 候选（每态 ≤2 条，从冻结池取）",
        "",
]
    for name, state in STATES:
        pool = unused_conformers(name, state)
        lines.append("### %s|%s（池内未用构象 %d 个）" % (name, state, len(pool)))
        lines.append("")
        if pool:
            lines.append("| 池 rank | 相对能 (kcal/mol) | 几何 |")
            lines.append("|---|---|---|")
            for r in pool[:MAX_LEGS_PER_STATE]:
                lines.append("| %s | %s | `%s` |" % (
                    r.get("rank", ""), r.get("rel_kcal", ""),
                    r.get("geometry_relpath", "")))
        else:
            lines.append("（冻结池的构象已全部上过生产级——**该态应改走扭转扫描**，"
                         "本试点不覆盖该路径，需另行登记）")
        lines.append("")
    lines += [
        "## 停止条件（冻结）",
        "",
        "1. 每态最多 **2** 条生产腿；",
        "2. 两条都塌缩到已知极小 → 登记 `production_single_basin`——这是**生产级**的单盆地",
        "   证据（远强于 GFN2 塌缩），但按计划仍然**不是**「所有搜索方法都无效」的证明；",
        "3. 发现任何新盆地 → 进入常规覆盖复核（multi_basin_coverage / single_basin_verified）；",
        "4. 不放宽阈值、不改记历史、不自动扩展到其余 5 态。",
        "",
        "## 预算上限",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 腿数 | ≤4（2 态 × 2） |",
        "| 单腿依据 | ~12 core-hours（M_plus 生产实测均值） |",
        "| **合计** | **~%s core-hours**（恢复包余量 ~430 内） |" % BUDGET_NOTE_CORE_HOURS,
        "",
        "**本稿不启动任何计算；须用户逐态批准或按本稿一次性批准。**",
        "",
    ]
    return "\n".join(lines)


def write_outputs() -> None:
    OUT_MD.write_text(render(), encoding="utf-8", newline="\n")
    OUT_INDEX.write_text(json.dumps({
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic)",
        "generator": "scripts/wp_production/build_bgroup_pilot_preregistration.py",
        "inputs": {str(p.relative_to(REPO)): _sha(p)
                   for p in (POOL, ENS / "production_ensemble_structures.csv")
                   if p.is_file()},
        "user_ruling": "B-group pilot: AN/DMC M_plus first (2026-10-21)",
        "method": "direct DFT multi-start from unused frozen-pool conformers",
        "states": ["%s|%s" % s for s in STATES],
        "stop_rule": "2 legs per state; double collapse -> production_single_basin",
        "budget_cap_core_hours": BUDGET_NOTE_CORE_HOURS,
        "launched": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def check() -> int:
    disk = OUT_MD.read_text(encoding="utf-8") if OUT_MD.is_file() else ""
    if disk != render():
        print("CHECK FAILED -- %s drifted" % OUT_MD.name)
        return 1
    print("CHECK OK -- B-group pilot preregistration matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    print("B-group pilot preregistration: %d states, NOT launched"
          % len(STATES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
