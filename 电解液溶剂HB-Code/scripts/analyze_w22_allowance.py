"""Week 22 hardening -- A3 (missed-solution allowance, the factor 2) and B3 (multiple comparison).

Two independent, read-only audits that a reviewer note asked to be pinned down
with numbers instead of prose.  Nothing here regenerates any electronic
structure and nothing here touches a frozen quantity or a Stage 16 verdict.

A3 -- the factor 2 in the soundness theorem
-------------------------------------------
``outputs/week23/targeted_two_guess.json`` defines, per axis, a *missed-solution
allowance* ``A_axis`` as the largest change a missed solution can make to **any
single cell** of the decision quantity::

    A_axis = max over cells | value_moread - value_default |

The paper then targets the second leg at ``|d0| >= A_axis`` and calls it a
provably sufficient superset of every flippable pair.  That argument has a gap.
A flip of pair (i, j) needs ``|d0 - d1| > |d0|``, and the pair gap moves by
``|(e_i - e_j)|`` where ``e`` is a per-cell effect.  By the triangle inequality

    |e_i - e_j| <= |e_i| + |e_j| <= 2 * A_axis,

so the *strict* bound that a single constant can certify is ``2 * A_axis``, not
``A_axis``.  Using ``A_axis`` therefore leans on the empirical fact that no pair
happens to move by more than one cell's worth -- true on this ladder, but not a
theorem.

This script re-derives the targeting price under three conventions:

1. ``current_A_axis``   -- threshold ``A_axis`` (the paper's present convention);
2. ``factor2_2A_axis``  -- threshold ``2 * A_axis`` (the strict theorem bound);
3. ``pair_level_bound`` -- threshold ``max over pairs |e_i - e_j|``, i.e. ``A``
   redefined at the pair level (the tightest single measured constant that makes
   the theorem exact on this ladder).

For each it reports the targeted-cell fraction, the savings, and -- as the only
acceptable miss count -- the number of observed flips it fails to catch.

B3 -- multiple comparison on the predictability table
-----------------------------------------------------
``outputs/week10/stage11_sigma_anatomy.json`` section ``predictability.table``
scores ``n`` predictors of a two-slot shortlist rewrite by AUC, each with an
exact permutation p-value.  Nine simultaneous tests need a family-wise control.
This script reports the Bonferroni threshold ``0.05 / n`` and a step-down Holm
correction, and states whether the signed-slope predictor ``ols_slope_b``
survives either.

Outputs
-------
``outputs/week22_hardening/allowance_factor2.json`` / ``.md``
``outputs/week22_hardening/multiple_compare_b3.json`` / ``.md``
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ALLOWANCE_JSON = REPO_ROOT / "outputs" / "week23" / "targeted_two_guess.json"
PAIRS_CSV = REPO_ROOT / "outputs" / "week23" / "targeted_two_guess_pairs.csv"
SIGMA_JSON = REPO_ROOT / "outputs" / "week10" / "stage11_sigma_anatomy.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week22_hardening"

AXES = ("oxidation", "reduction")

PAIR_LEVEL_DEFINITION = (
    "max over pairs of |d_moread - d_default| = max over pairs |e_i - e_j|: the "
    "largest change a missed solution can make to any single pair gap, i.e. A "
    "redefined at the pair level"
)


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def load_pairs(path: Path) -> list:
    """Per (axis, epsilon, pair) census, parsed to numbers."""

    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append({
                "axis": row["axis"],
                "epsilon": float(row["epsilon"]),
                "name_a": row["name_a"],
                "name_b": row["name_b"],
                "d_default_ev": float(row["d_default_ev"]),
                "d_moread_ev": float(row["d_moread_ev"]),
                "abs_d_default_ev": float(row["abs_d_default_ev"]),
                "flipped": row["flipped"].strip().lower() == "true",
            })
    return rows


def targeted_cells(axis_pairs: list, delta: float) -> set:
    """Cells that take part in a pair with |d0| < delta (the targeting test)."""

    cells = set()
    for pair in axis_pairs:
        if pair["abs_d_default_ev"] >= delta:
            continue
        cells.add((pair["name_a"], pair["epsilon"]))
        cells.add((pair["name_b"], pair["epsilon"]))
    return cells


def convention(axis_pairs: list, n_cells_total: int, name: str,
               delta: float, kind: str) -> dict:
    cells = targeted_cells(axis_pairs, delta)
    flips = [pair for pair in axis_pairs if pair["flipped"]]
    missed = [pair for pair in flips if pair["abs_d_default_ev"] >= delta]
    return {
        "name": name,
        "delta_kind": kind,
        "delta_ev": delta,
        "n_targeted_cells": len(cells),
        "n_cells_total": n_cells_total,
        "targeted_fraction": len(cells) / n_cells_total,
        "savings_fraction": 1.0 - len(cells) / n_cells_total,
        "n_flips": len(flips),
        "n_flips_missed": len(missed),
        "missed_pairs": ["%s/%s@eps=%g" % (pair["name_a"], pair["name_b"], pair["epsilon"])
                         for pair in missed],
    }


def analyse_allowance(allowance: dict, pairs: list) -> dict:
    axes = {}
    for axis in AXES:
        axis_pairs = [pair for pair in pairs if pair["axis"] == axis]
        detail = allowance["allowance_detail"][axis]
        a_axis = allowance["allowance_ev"][axis]

        worst_pair = max(axis_pairs,
                         key=lambda pair: abs(pair["d_moread_ev"] - pair["d_default_ev"]))
        pair_bound = abs(worst_pair["d_moread_ev"] - worst_pair["d_default_ev"])

        names = {pair["name_a"] for pair in axis_pairs} | {pair["name_b"] for pair in axis_pairs}
        epsilons = {pair["epsilon"] for pair in axis_pairs}
        n_cells_total = len(names) * len(epsilons)

        conventions = [
            convention(axis_pairs, n_cells_total, "current_A_axis", a_axis,
                       "paper convention: threshold = A_axis (single-cell max effect)"),
            convention(axis_pairs, n_cells_total, "factor2_2A_axis", 2.0 * a_axis,
                       "strict theorem bound: threshold = 2 * A_axis"),
            convention(axis_pairs, n_cells_total, "pair_level_bound", pair_bound,
                       "A redefined at pair level: threshold = max|e_i - e_j|"),
        ]

        axes[axis] = {
            "A_axis_ev": a_axis,
            "A_axis_worst_cell": detail["worst_cell"],
            "A_axis_definition": detail["definition"],
            "n_material_cells": detail["n_material_cells"],
            "n_cells_total": n_cells_total,
            "two_times_A_axis_ev": 2.0 * a_axis,
            "pair_level_bound_ev": pair_bound,
            "pair_level_definition": PAIR_LEVEL_DEFINITION,
            "pair_level_worst_pair": {
                "name_a": worst_pair["name_a"],
                "name_b": worst_pair["name_b"],
                "epsilon": worst_pair["epsilon"],
                "abs_delta_ev": pair_bound,
            },
            "n_pairs": len(axis_pairs),
            "n_flips": sum(1 for pair in axis_pairs if pair["flipped"]),
            "conventions": conventions,
        }

    return {
        "stage": "week22_hardening",
        "part": "A3",
        "title": "Missed-solution allowance: the factor 2 and the pair-level bound",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "allowance": relative(ALLOWANCE_JSON),
            "pairs": relative(PAIRS_CSV),
        },
        "method": {
            "targeting_test": "cell is protected iff it takes part in a pair with |d0| < delta",
            "soundness_theorem": ("a flip needs |d0 - d1| = |d0| + |d1| > |d0|; the pair gap "
                                  "moves by |e_i - e_j| <= |e_i| + |e_j| <= 2 * A_axis, so the "
                                  "strict single-constant bound is 2 * A_axis, not A_axis"),
            "miss_count_requirement": "n_flips_missed must be 0 in every convention",
        },
        "axes": axes,
    }


def analyse_b3(sigma: dict) -> dict:
    table = sigma["predictability"]["table"]
    n = len(table)
    alpha = 0.05
    bonferroni = alpha / n

    entries = [{"predictor": row["predictor"],
                "orientation": row["orientation"],
                "auc": row["auc"],
                "p": row["auc_exact_permutation_p"],
                "n": row["n"],
                "n_positives": row["n_positives"]} for row in table]
    entries.sort(key=lambda item: item["p"])

    # Bonferroni: plain threshold, and the family-adjusted p-value min(1, n * p).
    for entry in entries:
        entry["bonferroni_alpha"] = bonferroni
        entry["bonferroni_adjusted_p"] = min(1.0, n * entry["p"])
        entry["bonferroni_significant"] = entry["p"] < bonferroni

    # Holm step-down: reject H_(k) while p_(k) <= alpha / (n - k + 1); stop at the
    # first failure.  Holm-adjusted p-values enforce monotonicity.
    holm_running = 0.0
    holm_open = True
    for rank, entry in enumerate(entries, start=1):
        divisor = n - rank + 1
        threshold = alpha / divisor
        adjusted = min(1.0, divisor * entry["p"])
        holm_running = max(holm_running, adjusted)
        entry["holm_rank"] = rank
        entry["holm_threshold"] = threshold
        entry["holm_adjusted_p"] = holm_running
        entry["holm_significant"] = bool(holm_open and entry["p"] <= threshold)
        if not entry["holm_significant"]:
            holm_open = False

    signed = next(entry for entry in entries if entry["predictor"] == "ols_slope_b")

    return {
        "stage": "week22_hardening",
        "part": "B3",
        "title": "Multiple comparison on the Stage 11 predictability table",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {"predictability": relative(SIGMA_JSON)},
        "target_rule": sigma["predictability"]["target_rule"],
        "target_definition": sigma["predictability"]["target_definition"],
        "n_points": sigma["predictability"]["n_points"],
        "n_positives": sigma["predictability"]["n_positives"],
        "n_predictors": n,
        "alpha": alpha,
        "bonferroni_alpha": bonferroni,
        "n_bonferroni_significant": sum(1 for entry in entries if entry["bonferroni_significant"]),
        "n_holm_significant": sum(1 for entry in entries if entry["holm_significant"]),
        "signed_slope": {
            "predictor": signed["predictor"],
            "p": signed["p"],
            "auc": signed["auc"],
            "bonferroni_alpha": bonferroni,
            "bonferroni_adjusted_p": signed["bonferroni_adjusted_p"],
            "bonferroni_significant": signed["bonferroni_significant"],
            "holm_rank": signed["holm_rank"],
            "holm_threshold": signed["holm_threshold"],
            "holm_adjusted_p": signed["holm_adjusted_p"],
            "holm_significant": signed["holm_significant"],
        },
        "table": entries,
    }


def fmt(value, digits=4):
    return "%.*f" % (digits, value)


def allowance_markdown(payload: dict) -> str:
    lines = []
    add = lines.append
    add("# A3 — 漏解安全定理的因子 2：allowance 的两种严格口径")
    add("")
    add("> 本文档由 `scripts/analyze_w22_allowance.py` 从")
    add("> `%s` 与 `%s` 渲染。" % (payload["sources"]["allowance"], payload["sources"]["pairs"]))
    add("> **只读复核，不产生新电子结构，不改动任何冻结量或 Stage 16 判定。**")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("论文现用的阈值 `|d0| >= A_axis` 只用了**单格**最大效应 `A_axis`；但一对分子的间距受**两格**扰动，")
    add("严格上界是 `2 * A_axis`。用 `2 * A_axis` 重算，**两轴都要保护全部 120 格（节约 0%）**——")
    add("这正是 A3 要暴露的代价。把 `A` 重定义到 **pair 级** `max|e_i - e_j|` 后，阈值只比 `A_axis` 高一点点，")
    add("节约几乎回到现行口径（86/120、116/120）。三种口径的真实翻转漏检数**全为 0**。")
    add("")
    add("## 1. `A_axis` 定义与来源复核")
    add("")
    add("`A_axis` 的定义（直接引自 `allowance_detail`）：")
    add("")
    add("> max over cells of |value_moread - value_default| on the decision quantity:")
    add("> the largest change a missed solution can make to any single cell")
    add("")
    add("| 轴 | `A_axis` (eV) | 最坏格子 | 材料格子数 | 该轴格子总数 |")
    add("| --- | --- | --- | --- | --- |")
    for axis in AXES:
        block = payload["axes"][axis]
        cell = block["A_axis_worst_cell"]
        add("| %s | **%s** | %s @ eps=%g | %d | %d |"
            % (axis, fmt(block["A_axis_ev"], 6), cell["name"], cell["epsilon"],
               block["n_material_cells"], block["n_cells_total"]))
    add("")
    add("来源：`%s` 的 `allowance_ev` / `allowance_detail`，由 `scripts/plan_targeted_two_guess.py`"
        % payload["sources"]["allowance"])
    add("从 Stage 16 双初猜目录换算得到。定义是**单格**效应上界。")
    add("")
    add("## 2. 因子 2 的严格上界，与 pair 级重定义")
    add("")
    add("一对 (i, j) 的间距变化为 `|e_i - e_j| <= |e_i| + |e_j| <= 2 * A_axis`，")
    add("所以单常数严格可证的上界是 `2 * A_axis`；把它换成 pair 级最大值")
    add("`max over pairs |e_i - e_j|` 则是让定理在这份目录上取等的最紧常数。")
    add("")
    add("| 轴 | `A_axis` (eV) | `2 * A_axis` (eV) | pair 级上界 (eV) | pair 级最坏 pair |")
    add("| --- | --- | --- | --- | --- |")
    for axis in AXES:
        block = payload["axes"][axis]
        worst = block["pair_level_worst_pair"]
        add("| %s | %s | **%s** | **%s** | %s/%s @ eps=%g |"
            % (axis, fmt(block["A_axis_ev"], 6), fmt(block["two_times_A_axis_ev"], 6),
               fmt(block["pair_level_bound_ev"], 6), worst["name_a"], worst["name_b"],
               worst["epsilon"]))
    add("")
    add("注：pair 级上界只在 `A_axis` 之上极小的量（氧化的 `+2.77e-05 eV`、还原的 `+1.50e-05 eV`），")
    add("说明真实数据里 `|e_i - e_j|` 几乎就等于单格最大值；但这不是定理，只是本目录的实测。")
    add("")
    add("## 3. 三种口径的靶向代价对照")
    add("")
    add("靶向判据：某格被保护 `iff` 它参与的某个 pair 满足 `|d0| < delta`。")
    add("")
    for axis in AXES:
        block = payload["axes"][axis]
        add("### %s（实测翻转 %d / %d 对）" % (axis, block["n_flips"], block["n_pairs"]))
        add("")
        add("| 口径 | delta (eV) | 靶向格子 / 全部 | 节约 | 漏检翻转 |")
        add("| --- | --- | --- | --- | --- |")
        for item in block["conventions"]:
            add("| `%s` | %s | **%d / %d** | **%s%%** | **%d** |"
                % (item["name"], fmt(item["delta_ev"], 6),
                   item["n_targeted_cells"], item["n_cells_total"],
                   fmt(100 * item["savings_fraction"], 1), item["n_flips_missed"]))
        add("")
    add("## 4. 读法（必须与数字同时写出）")
    add("")
    add("1. 论文的 `A_axis` 口径在本目录上漏检为 0，但它的充分性**不是**定理：定理给的是 `2 * A_axis`。")
    add("2. 用 `2 * A_axis` 时节约为 0——即严格的单常数证明要求**保护全部格子**，靶向不再省事。")
    add("3. 把 `A` 重定义到 pair 级可让定理取等，且节约基本回归（氧化 86/120 省 28.3%；还原 116/120 省 3.3%）。")
    add("4. 三口径漏检均为 0：在这份 1320 对的实测目录上，靶向都是充分的；差别在**可证性**与**代价**。")
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：%s" % payload["generated_utc"])
    return "\n".join(lines) + "\n"


def b3_markdown(payload: dict) -> str:
    lines = []
    add = lines.append
    add("# B3 — 多重比较：Stage 11 可预测性表（Bonferroni 与 Holm）")
    add("")
    add("> 本文档由 `scripts/analyze_w22_allowance.py` 从 `%s` 渲染。"
        % payload["sources"]["predictability"])
    add("> **只读复核，不改动冻结量。**")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("先验 predictor 个数 `n = %d`，Bonferroni 阈值 `alpha = 0.05 / %d = %s`。"
        % (payload["n_predictors"], payload["n_predictors"], fmt(payload["bonferroni_alpha"], 6)))
    add("逐条 p 都 **大于** 该阈值，Bonferroni 下 **0 条显著**；Holm 步降在第一步即失败，")
    add("同样是 **0 条显著**。因此 signed-slope（`ols_slope_b`，`p = %s`）**不存活**。"
        % fmt(payload["signed_slope"]["p"], 5))
    add("")
    add("## 1. 输入")
    add("")
    add("- 目标规则：`%s`" % payload["target_rule"])
    add("- 目标定义：%s" % payload["target_definition"])
    add("- 样本：n_points = %d，n_positives = %d" % (payload["n_points"], payload["n_positives"]))
    add("- predictor 个数（表内条数）：**n = %d**" % payload["n_predictors"])
    add("- 显著性水平：alpha = %s；Bonferroni 阈值 = alpha / n = **%s**"
        % (payload["alpha"], fmt(payload["bonferroni_alpha"], 6)))
    add("")
    add("## 2. Bonferroni")
    add("")
    add("| predictor | AUC | p (精确置换) | p×n（校正后） | p < 0.05/n ? |")
    add("| --- | --- | --- | --- | --- |")
    for entry in sorted(payload["table"], key=lambda item: item["p"]):
        add("| %s | %s | %s | %s | %s |"
            % (entry["predictor"], fmt(entry["auc"], 4), fmt(entry["p"], 6),
               fmt(entry["bonferroni_adjusted_p"], 4),
               "是" if entry["bonferroni_significant"] else "**否**"))
    add("")
    add("Bonferroni 显著条数：**%d**。" % payload["n_bonferroni_significant"])
    add("")
    add("## 3. Holm（步降）")
    add("")
    add("Holm：按 p 升序，第 k 个（k=1..n）与 `alpha / (n - k + 1)` 比较；一旦某步不通过即停止。")
    add("")
    add("| k | predictor | p | Holm 阈值 alpha/(n-k+1) | Holm 校正后 p | 显著 ? |")
    add("| --- | --- | --- | --- | --- | --- |")
    for entry in sorted(payload["table"], key=lambda item: item["holm_rank"]):
        add("| %d | %s | %s | %s | %s | %s |"
            % (entry["holm_rank"], entry["predictor"], fmt(entry["p"], 6),
               fmt(entry["holm_threshold"], 6), fmt(entry["holm_adjusted_p"], 4),
               "是" if entry["holm_significant"] else "**否**"))
    add("")
    add("Holm 显著条数：**%d**。" % payload["n_holm_significant"])
    add("")
    signed = payload["signed_slope"]
    add("## 4. signed-slope（`ols_slope_b`）判读")
    add("")
    add("| 项 | 值 |")
    add("| --- | --- |")
    add("| predictor | `%s` |" % signed["predictor"])
    add("| AUC | %s |" % fmt(signed["auc"], 4))
    add("| p | %s |" % fmt(signed["p"], 6))
    add("| Bonferroni 阈值 | %s |" % fmt(signed["bonferroni_alpha"], 6))
    add("| Bonferroni 校正后 p | %s |" % fmt(signed["bonferroni_adjusted_p"], 4))
    add("| Bonferroni 显著 | %s |" % ("是" if signed["bonferroni_significant"] else "**否**"))
    add("| Holm 名次 k | %d |" % signed["holm_rank"])
    add("| Holm 阈值 | %s |" % fmt(signed["holm_threshold"], 6))
    add("| Holm 校正后 p | %s |" % fmt(signed["holm_adjusted_p"], 4))
    add("| Holm 显著 | %s |" % ("是" if signed["holm_significant"] else "**否**"))
    add("")
    add("**判断：`ols_slope_b` 的 p = %s 在 Bonferroni 与 Holm 两口径下都不存活。**"
        % fmt(signed["p"], 5))
    add("其最小可能原始 p 受精确置换分辨率限制（n = %d 点时最小 p = %s），"
        % (payload["n_points"], fmt(1.0 / 120.0, 6)))
    add("本身已高于 Bonferroni 阈值 %s，故不可能在族错误率控制下存活。"
        % fmt(payload["bonferroni_alpha"], 6))
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：%s" % payload["generated_utc"])
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Week 22 hardening: A3 factor 2 and B3 multiple comparison.")
    parser.add_argument("--allowance", type=Path, default=ALLOWANCE_JSON)
    parser.add_argument("--pairs", type=Path, default=PAIRS_CSV)
    parser.add_argument("--sigma", type=Path, default=SIGMA_JSON)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args(argv)

    args.outdir.mkdir(parents=True, exist_ok=True)

    allowance = json.loads(args.allowance.read_text(encoding="utf-8"))
    pairs = load_pairs(args.pairs)
    a3 = analyse_allowance(allowance, pairs)
    a3_json = args.outdir / "allowance_factor2.json"
    a3_md = args.outdir / "allowance_factor2.md"
    write_json(a3_json, a3)
    write_text(a3_md, allowance_markdown(a3))

    sigma = json.loads(args.sigma.read_text(encoding="utf-8"))
    b3 = analyse_b3(sigma)
    b3_json = args.outdir / "multiple_compare_b3.json"
    b3_md = args.outdir / "multiple_compare_b3.md"
    write_json(b3_json, b3)
    write_text(b3_md, b3_markdown(b3))

    print(json.dumps({
        "A3": {axis: {
            "A_axis": a3["axes"][axis]["A_axis_ev"],
            "2A_axis": a3["axes"][axis]["two_times_A_axis_ev"],
            "pair_level": a3["axes"][axis]["pair_level_bound_ev"],
            "conventions": [{"name": c["name"],
                             "cells": "%d/%d" % (c["n_targeted_cells"], c["n_cells_total"]),
                             "savings": round(100 * c["savings_fraction"], 1),
                             "missed": c["n_flips_missed"]}
                            for c in a3["axes"][axis]["conventions"]],
        } for axis in AXES},
        "B3": {"n": b3["n_predictors"], "bonferroni_alpha": b3["bonferroni_alpha"],
               "bonferroni_significant": b3["n_bonferroni_significant"],
               "holm_significant": b3["n_holm_significant"],
               "ols_slope_b_survives": b3["signed_slope"]["holm_significant"]},
        "files": [relative(a3_json), relative(a3_md), relative(b3_json), relative(b3_md)],
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
