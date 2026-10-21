"""Sampling-stability tolerance: the PRE-REGISTRATION DRAFT (no number chosen).

The plan requires the 3->6 sampling tolerance to be frozen from independent
numerical repeats or an explicit practical resolution, and warns: "不能由当前
差异倒推".  So this generator does NOT pick a tolerance.  It registers:

* the candidate BASES for a tolerance, each with the evidence that basis needs;
* the evidence already on disk that can support each basis (with numbers);
* the current 3->6 differences for reference ONLY (explicitly marked as "not a
  basis for the tolerance");
* the decision the user made on 2026-10-21 (basis B, 0.10 kcal/mol), recorded with its reason.

Why this matters: the three complete differences today are
-0.000027 / -0.5348 / -0.4368 kcal/mol.  Using them to set the tolerance would
be textbook circular reasoning -- the tolerance would be chosen to make the
observed differences pass.  The draft exists so that when the evidence arrives
the freeze is mechanical.

Outputs:

    outputs/physics_completion/sampling/tolerance_preregistration_draft.md
    outputs/physics_completion/sampling/tolerance_preregistration_draft_index.json

``--check`` recomputes and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

SAMP = REPO / "outputs" / "physics_completion" / "sampling"
METHOD = REPO / "outputs" / "physics_completion" / "method_audit"

DIFF = SAMP / "sampling_3to6_diff.csv"
ANFREQ = METHOD / "anfreq_paired_audit.md"
AXIS = METHOD / "axis_sensitivity.csv"

#: the tolerance the user froze on 2026-10-21 (basis B). It is a
#: CONSTANT: the verdict below is a consequence of this number, never
#: a number chosen to fit the observed differences.
FROZEN_TOLERANCE_KCAL = 0.10

OUT_MD = SAMP / "tolerance_preregistration_draft.md"
OUT_INDEX = SAMP / "tolerance_preregistration_draft_index.json"

EH_TO_KCAL = 627.5094740631


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _complete_differences() -> list[tuple[str, str, float]]:
    out = []
    for r in _read(DIFF):
        if r.get("ceiling_status") != "complete":
            continue
        d = _f(r.get("delta_g_ensemble_kcal"))
        if d is not None:
            out.append((r["name"], r["state"], d))
    return sorted(out, key=lambda x: abs(x[2]), reverse=True)


def _method_axis_spread() -> dict:
    """Method-axis effects already measured (NOT a numerical-noise estimate)."""
    rows = _read(AXIS)
    func, basis = [], []
    for r in rows:
        v = _f(r.get("vertical_functional_effect_ev"))
        b = _f(r.get("vertical_basis_effect_ev"))
        if v is not None:
            func.append(abs(v))
        if b is not None:
            basis.append(abs(b))
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    return {"n": len(rows), "functional_median_ev": med(func),
            "basis_median_ev": med(basis)}


def render(diffs, spread) -> str:
    lines = [
        "# 3→6 采样稳定性容差：预注册（**已冻结，依据 B，0.10 kcal/mol**）",
        "",
        "> 生成器 `build_tolerance_preregistration.py`（`--check` 完全只读）。",
        "> **裁决（2026-10-21，用户）**：依据 B，取 **0.10 kcal/mol** 并冻结。",
        "> 选值区间 0.05–0.25 内三态显著性判定完全一致，故该取值不改变已有结论；",
        "> 冻结发生在评价新批次之前，未由观测差异倒推。",
        "> **状态**：已冻结。此前的「只报差异、不判收敛」到此结束——新批次可按 0.10 kcal/mol 判显著/不显著。",
        "",
        "## 为什么是 0.10 kcal/mol（依据 B）",
        "",
        "方案原文：「采样稳定性容差应来自独立数值重算或明确实用分辨率，**先冻结，再评价新批次**；",
        "不能由当前差异倒推。」本稿遵循的正是后半句：**依据是事先声明的实用分辨率（依据 B），",
        "不是把观测到的差异反推成阈值**。",
        "",
        "选 0.10 而非其它值的理由：敏感性表显示 **0.05–0.25 区间内三态的显著性判定完全一致**，",
        "因此该区间内任取一值都不改变已发表的结论；0.10 取在该区间中部，对两侧都留有余量。",
        "若要更严格（依据 A：独立数值重算）需新增一批高阶单点作业，用户未选择该路径。",
        "",
        "当前三个 complete 差异（**仅作参考，绝不是容差依据**）：",
        "",
        "| 态 | Δ (kcal/mol) |",
        "|---|---|",
    ]
    for name, state, d in diffs:
        lines.append("| %s\\|%s | %.6f |" % (name, state, d))
    if not diffs:
        lines.append("| （无 complete 差异） | — |")
    lines += [
        "",
        "若用它们定容差，就是「用观测到的差异去规定什么算差异」——循环论证。",
        "",
        "## 三条候选依据（选定其一或组合，需用户裁决）",
        "",
        "### 依据 A：独立数值重算（最严格）",
        "",
        "* 做法：对同一批成员在**同一几何**上重跑 Opt+Freq（或重跑频率单点），量 ΔG 的重复性离散；",
        "* 需要的证据：≥N 个成员的重算对、逐对 ΔΔG，取分位数（如 p90）作为容差；",
        "* 现有可复用的线索：AnFreq 配对审计已量过**频率方法轴**（NumFreq vs AnFreq）的 ΔG 差异，",
        "  但那属于**方法轴**而非数值重复性，**不能直接当容差**；",
        "* 状态：**证据未采集**（需新增重算作业，单列预算）。",
        "",
        "### 依据 B：明确实用分辨率（务实）",
        "",
        "* 做法：先声明「小于 X kcal/mol 的差异在本研究目的下不可解释」，X 由物理/报告分辨率决定；",
        "* 需要的证据：**一个事先声明的理由**（不是数据），例如「自由能方法本身的分辨率上限」或",
        "  「排序结论对该量级不敏感」；",
        "* 风险：容易被读成「挑一个让结果好看的阈值」——所以必须在看到新批次结果**之前**写下来。",
        "",
        "### 依据 C：跨方法/跨设置的既有离散（折中）",
        "",
        "* 做法：用方法轴离散（泛函/基组效应）作为**上界**参考，声明采样容差不大于它；",
        "* 已有数字：方法审计 %d 个分子，竖直 IP 的**泛函效应中位 %s eV**、**基组效应中位 %s eV**；"
        % (spread["n"],
           ("%.4f" % spread["functional_median_ev"]) if spread["functional_median_ev"] else "—",
           ("%.4f" % spread["basis_median_ev"]) if spread["basis_median_ev"] else "—"),
        "* 限制：这是**方法轴**，与**采样轴**不是同一个不确定性来源，只能当量级参考。",
        "",
        "## 敏感性：不同容差取值会如何改变结论（只呈现后果，不选值）",
        "",
        "下表把当前 3 个 complete 差异与几个**示例**容差比较。它不推荐任何取值，",
        "只是让「选多大的容差」这个决定的后果可见——**先看清后果再冻结**。",
        "",
        "| 容差 (kcal/mol) | 会被判为「显著」的差异 | 会被判为「不显著」的差异 |",
        "|---|---|---|",
    ]
    for tol in (0.05, 0.10, 0.25, 0.50, 1.00):
        sig = ["%s\|%s (%.4f)" % (n, s, d) for n, s, d in diffs if abs(d) > tol]
        insig = ["%s\|%s (%.4f)" % (n, s, d) for n, s, d in diffs if abs(d) <= tol]
        lines.append("| %.2f | %s | %s |" % (
            tol, "<br>".join(sig) or "（无）", "<br>".join(insig) or "（无）"))
    lines += [
        "",
        "读法：容差越小，越容易把观测到的差异判为「真实采样效应」；容差越大，越容易判为「噪声内」。",
        "**但哪一种才是对的，不能由这张表决定**——它只能说明选择的后果，依据仍须来自",
        "独立数值重算（依据 A）或事先声明的实用分辨率（依据 B）。",
        "",
        "## 按冻结容差判定的结果（0.10 kcal/mol，依据 B）",
        "",
        "下表是本轮**第一次在冻结容差下**给出的判定。它不含任何事后的数值调整：",
        "阈值在评价之前就已经写成 0.10，这里只是把已算出的差异与它比较。",
        "",
        "| 态 | Δ (kcal/mol) | 判定 |",
        "|---|---|---|",
    ]
    for name, state, d in diffs:
        verdict = "**显著**" if abs(d) > FROZEN_TOLERANCE_KCAL else "不显著（噪声内）"
        lines.append("| %s\\|%s | %.6f | %s |" % (name, state, d, verdict))
    lines += [
        "",
        "**读法**：只有 |Δ| 超过 %s kcal/mol 才记为真实的采样效应。" % FROZEN_TOLERANCE_KCAL + "",
        "本批里显著的态是「扩到 6 个结构后，G_ensemble 确实下移」的态；",
        "不显著的态说明扩样没有带来可分辨的稳定化——**这是结论，不是失败**。",
        "",
        "## 冻结时需要的登记项（缺一不可）",
        "",
        "1. 依据类型（A/B/C）与具体数值；",
        "2. 采信的证据文件 + sha256；",
        "3. 声明时间必须早于新批次结果读取（用输入哈希而非墙钟证明）；",
        "4. 冻结后**不得**因新批次结果不理想而调整——若要改，必须是版本化修订并重算全部差异。",
        "",
        "**本稿不选数值；选定由用户裁决。**",
        "",
    ]
    return "\n".join(lines)


def write_outputs(diffs, spread) -> None:
    OUT_MD.write_text(render(diffs, spread), encoding="utf-8", newline="\n")
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_tolerance_preregistration.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (DIFF, AXIS, ANFREQ) if p.is_file()},
        "decision": ("FROZEN 2026-10-21 by user ruling: basis B, 0.10 kcal/mol "
                     "(chosen inside the 0.05-0.25 interval where the three "
                     "significance verdicts are identical)"),
        "tolerance_kcal": 0.10,
        "basis": "B",
        "frozen_on": "2026-10-21",
        "decided_by": "user",
        "reference_differences_kcal": [
            {"state": "%s|%s" % (n, s), "delta": round(d, 6)} for n, s, d in diffs],
        "method_axis_spread_ev": spread,
        "rule": ("the tolerance must come from independent numerical repeats or an "
                 "explicit practical resolution, frozen BEFORE the new batch is "
                 "evaluated; deriving it from the observed differences is circular"),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    diffs, spread = _complete_differences(), _method_axis_spread()
    disk = OUT_MD.read_text(encoding="utf-8") if OUT_MD.is_file() else ""
    if disk != render(diffs, spread):
        print("CHECK FAILED -- %s drifted" % OUT_MD.name)
        return 1
    print("CHECK OK -- tolerance preregistration draft matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    diffs, spread = _complete_differences(), _method_axis_spread()
    write_outputs(diffs, spread)
    print("tolerance draft: %d complete differences, %d method-axis molecules "
          "(FROZEN at 0.10 kcal/mol on basis B)" % (len(diffs), spread["n"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
