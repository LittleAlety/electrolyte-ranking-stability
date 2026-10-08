"""R15 -- the estimator-circularity audit (adversarial round 3, item A/E).

What this asks
--------------
Round 3 does not add science; it tries to *break* the repository's own
negative results.  This script attacks the smallest hole that could explain
them all: **is the resolved/unresolved machinery measuring the data, or is it
measuring itself?**

The frozen primary convention feeds exactly two realizations into
``uncertainty.quantify_method_sigma`` -- the two models being compared (the
"two-arm" sigma of ``docs/10`` section 2.4).  Two numbers have sample standard
deviation ``|x0 - x1| / sqrt(2)``, so the uncertainty is a *function of the
two models' own disagreement*.  ``electrolyte_ranking.robustness`` states the
consequences; this script proves them on the frozen products and freezes them.

Theorems proved here (``--check`` reproduces every number byte-identically)
-----------------------------------------------------------------------
T1  ``sigma_ij = |dP_A(i,j) - dP_B(i,j)| / sqrt(2)``  (Stage 11 identity, re-asserted)
T6a ``ROBUST_INVERSION`` is impossible for ``z > 1/sqrt(2)``; the frozen
    ``z = 1.0`` and ``z = 1.96`` both exceed it, so ``f_robust_inv = 0`` is a
    definitional invariant, not an observation.
T6b Stronger: the both-resolved subsample contains **zero discordant pairs**
    in every block and at every frozen ``z``.  The pipeline cannot certify a
    disagreement at all; ``f_robust_inv = 0`` is a tautology here.
T7  The resolved mask equals a pure *ratio* rule on ``|dY|/|dX|``
    (``robustness.resolution_band``), so ``f_unresolved`` carries no absolute
    energy scale and no independent noise -- it is a function of how far apart
    the two models place each pair.

Consequence for one preregistered hypothesis
--------------------------------------------
Stage 10 recorded hypothesis **C** ("structured robust inversion") as
``NOT OBSERVED``.  Under the frozen two-arm convention it was never
*observable*: the estimator excludes it for every data set.  The audit
re-labels it ``NOT TESTABLE`` and shows the *positive control* that makes the
hypothesis testable -- the multi-source sigma of ``docs/08`` section 5, which
pools five realizations and already produced ``f_robust_inv`` up to 1.96 % in
the frozen dielectric scan (``outputs/week4/t3_cpcm_eps_scan_summary.json``).

Outputs
-------
outputs/week27/estimator_circularity.json
outputs/week27/estimator_circularity.md
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking, robustness  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week27"

#: (label, frozen source json, dotted getter for {axis}) of every rung that
#: still carries per-pair evidence.
BLOCKS = (
    ("P0->P1v", "outputs/week4/p1_decision_stability.json", "{axis}"),
    ("P1v->P2a", "outputs/week4/p2_decision_stability.json", "p1_to_p2.{axis}"),
    ("P0->P2a", "outputs/week4/p2_decision_stability.json", "p0_to_p2.{axis}"),
    ("C0->C1", "outputs/week5/c1_decision_stability.json", "{axis}"),
)
AXES = ("oxidation", "reduction")

#: The frozen sigma conventions.  ``two_arm`` is the primary convention of every
#: decision-stability table in the repository; ``multi_source`` is the docs/08
#: section 5 pooled convention used by the dielectric scan.
T3_SCAN = "outputs/week4/t3_cpcm_eps_scan_summary.json"
STAGE10 = "outputs/week9/stage10_ladder.json"


def read_json(relative):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def dig(obj, dotted):
    current = obj
    for key in dotted.split("."):
        current = current[key]
    return current


def matrices(pairs):
    names = sorted({p["i"] for p in pairs} | {p["j"] for p in pairs})
    index = {name: position for position, name in enumerate(names)}
    n = len(names)
    d0 = np.zeros((n, n))
    d1 = np.zeros((n, n))
    sigma = np.zeros((n, n))
    for pair in pairs:
        i, j = index[pair["i"]], index[pair["j"]]
        d0[i, j], d0[j, i] = pair["d_p0_ev"], -pair["d_p0_ev"]
        d1[i, j], d1[j, i] = pair["d_p1_ev"], -pair["d_p1_ev"]
        sigma[i, j] = sigma[j, i] = pair["sigma_ev"]
    return names, d0, d1, sigma


def audit_block(label, axis, block):
    names, d0, d1, sigma = matrices(block["pair_differences"])
    n = len(names)
    z_primary = float(block.get("z_primary") or 1.0)
    z_sensitivity = float(block.get("z_sensitivity") or 1.96)

    sigma_err = float(np.max(np.abs(robustness.two_arm_sigma(d0, d1) - sigma)))

    rows = {}
    for tag, z in (("z_primary", z_primary), ("z_sensitivity", z_sensitivity)):
        ref0 = ranking.resolved_mask(d0, sigma, z=z)
        ref1 = ranking.resolved_mask(d1, sigma, z=z)
        rule0 = robustness.resolution_rule(d0, d1, z)
        rule1 = robustness.resolution_rule(d1, d0, z)
        both = robustness.both_resolved_from_rule(d0, d1, z)
        n_both = int(np.count_nonzero(both["both"]))
        n_disc = int(np.count_nonzero(both["discordant"]))
        rows[tag] = {
            "z": z,
            "rule_mismatch": int(np.count_nonzero(ref0 != rule0) + np.count_nonzero(ref1 != rule1)),
            "n_pairs": int(both["n_pairs"]),
            "n_resolved_both": n_both,
            "n_discordant_both": n_disc,
            "n_concordant_both": int(np.count_nonzero(both["concordant"])),
            "f_unresolved_both": None if not both["n_pairs"] else 1.0 - n_both / both["n_pairs"],
            "f_robust_inv": None if n_both == 0 else n_disc / n_both,
            "inversion_possible": robustness.inversion_possible(z),
        }

    return {
        "rung": label,
        "axis": axis,
        "n": n,
        "n_pairs": int(n * (n - 1) // 2),
        "sigma_identity_max_abs_err_ev": sigma_err,
        "f_robust_inv_frozen": block.get("f_robust_inv"),
        "f_unresolved_p0_frozen": block.get("f_unresolved_p0"),
        "f_unresolved_p1_frozen": block.get("f_unresolved_p1"),
        "kendall_tau_b_frozen": block.get("kendall_tau_b"),
        "bands": rows,
    }

#: Every Stage-10 hypothesis that names a decision metric, with the metric's
#: dependence on the two-arm sigma written out.  ``robust_inv``-dependent
#: hypotheses are the ones the estimator can exclude a priori.
HYPOTHESIS_METRIC = {
    "A_cheap_proxy_already_stable": ("tau_b / O_k / f_unresolved", False),
    "B_large_shift_small_rank_damage": ("tau_b / O_k / f_robust_inv", True),
    "C_structured_robust_inversion": ("f_robust_inv", True),
    "D_coordination_state_identity_change": ("state identity", False),
    "E_delta_learning_beats_direct": ("ML error", False),
    "F_delta_not_learnable_from_cheap": ("ML transfer", False),
    "G_most_pairs_unresolved": ("f_unresolved", False),
}


def hypothesis_table():
    doc = read_json(STAGE10)
    verdicts = doc.get("verdicts") or {}
    rows = []
    for key in sorted(verdicts):
        if key.startswith("_"):
            continue
        item = verdicts[key] or {}
        metric, robust_dependent = HYPOTHESIS_METRIC.get(key, (None, False))
        if key == "C_structured_robust_inversion":
            testability = "NOT TESTABLE"
            why = (
                "the metric f_robust_inv is identically 0 for every data set under the "
                "frozen two-arm sigma with z > 1/sqrt(2) (theorem T6a/T6b); the frozen "
                "verdict 'NOT OBSERVED' records an impossibility, not a test"
            )
        elif robust_dependent:
            testability = "PARTIALLY TESTABLE"
            why = (
                "the hypothesis also rests on tau_b / O_k, which are point-ordering "
                "statistics and remain testable; only its f_robust_inv clause is void"
            )
        else:
            testability = "TESTABLE"
            why = "the frozen metric does not depend on the two-arm sigma identity"
        rows.append(
            {
                "hypothesis": key,
                "metric": metric,
                "frozen_verdict": item.get("verdict"),
                "short": item.get("short"),
                "testability_under_frozen_convention": testability,
                "why": why,
            }
        )
    return rows


def multisource_contrast():
    """The positive control: same data, five pooled realizations, inversions appear."""

    doc = read_json(T3_SCAN)
    block = doc.get("robust_inversion") or {}
    conventions = block.get("sigma_conventions") or {}
    return {
        "source": T3_SCAN,
        "two_arm": conventions.get("two_arm"),
        "multi_source": conventions.get("multi_source"),
        "max_n_robust_inversions_z1p0": block.get("max_n_robust_inversions_z1p0"),
        "n_realizations": {
            "two_arm": 2,
            "multi_source": 5,
        },
        "reading": (
            "Same molecules, same layers; only the sigma convention changes. Two-arm "
            "sigma (R = 2) yields zero inversions because T6a forbids them; the pooled "
            "five-realization sigma (R = 5) is not pinned to the pair of models being "
            "compared, so the impossibility lifts and one pair does invert. Hypothesis C "
            "is therefore testable -- just not under the convention it was frozen with."
        ),
    }


def build(z_primary=None):
    blocks = []
    for label, source, template in BLOCKS:
        document = read_json(source)
        for axis in AXES:
            block = dig(document, template.format(axis=axis))
            blocks.append(audit_block(label, axis, block))

    sigma_err = max(b["sigma_identity_max_abs_err_ev"] for b in blocks)
    rule_mismatch = max(
        b["bands"]["z_primary"]["rule_mismatch"] + b["bands"]["z_sensitivity"]["rule_mismatch"]
        for b in blocks
    )
    discordant = max(
        b["bands"]["z_primary"]["n_discordant_both"] + b["bands"]["z_sensitivity"]["n_discordant_both"]
        for b in blocks
    )
    z_values = sorted(
        {b["bands"][tag]["z"] for b in blocks for tag in ("z_primary", "z_sensitivity")}
    )
    theorems = {
        "T1_two_arm_sigma_identity": {
            "statement": "sigma_ij = |dP_A(i,j) - dP_B(i,j)| / sqrt(2) on every frozen block",
            "max_abs_err_ev": sigma_err,
            "ok": bool(sigma_err < 1e-9),
        },
        "T6a_inversion_impossible": {
            "statement": (
                "ROBUST_INVERSION requires z <= 1/sqrt(2); the frozen z values are all larger, "
                "so f_robust_inv is identically zero under the primary convention"
            ),
            "z_max_for_inversion": float(robustness.TWO_ARM_INVERSION_Z_MAX),
            "frozen_z_values": [float(z) for z in z_values],
            "all_frozen_z_exclude_inversion": bool(
                all(not robustness.inversion_possible(z) for z in z_values)
            ),
        },
        "T6b_no_certifiable_disagreement": {
            "statement": (
                "the both-resolved subsample contains zero discordant pairs in every block and "
                "at every frozen z; the pipeline never certifies a disagreement"
            ),
            "max_n_discordant_both": discordant,
            "ok": bool(discordant == 0),
        },
        "T7_ratio_rule": {
            "statement": (
                "the resolved mask equals the closed-form ratio rule of "
                "robustness.resolution_band on |dY|/|dX| (no absolute scale enters)"
            ),
            "rule_mismatch": rule_mismatch,
            "ok": bool(rule_mismatch == 0),
        },
    }
    return {
        "stage": "R15 estimator-circularity audit",
        "question": (
            "Is the resolved/unresolved machinery measuring the data, or is it measuring "
            "the two models' own disagreement?"
        ),
        "convention": (
            "two-arm sigma: quantify_method_sigma([model A, model B], ddof=1, stat='std'); "
            "resolved <=> |dP| >= z * sigma and |dP| > 0; ROBUST_INVERSION <=> both resolved "
            "and opposite signs; f_robust_inv = N_robust / N_resolved_in_both"
        ),
        "theorems": theorems,
        "blocks": blocks,
        "hypotheses": hypothesis_table(),
        "multisource_contrast": multisource_contrast(),
        "verdict": (
            "The two-arm estimator is self-referential: it cannot certify any disagreement, so "
            "the frozen f_robust_inv = 0 (and the 'NOT OBSERVED' verdict on hypothesis C) are "
            "definitional, not empirical. The project's headline conclusion is unaffected and in "
            "fact strengthened -- the evidence really does not identify the ranking -- but three "
            "statements must be re-worded, and f_robust_inv must always be reported with its "
            "sigma convention and its (void) denominator."
        ),
    }

def _num(value, digits=3):
    if value is None:
        return "-"
    if isinstance(value, float) and not np.isfinite(value):
        return "-"
    return ("%." + str(digits) + "f") % value


def render_markdown(payload):
    th = payload["theorems"]
    lines = [
        "# 27 · R15 估计量循环性审计（对抗审计 round 3 · 项目 A/E）",
        "",
        "- 触发：第二轮收口后，评审要求「反过来攻击自己的负结果」——`NOT CLOSABLE` / `unresolved`",
        "  本身是否被分析流程人为制造。",
        "- 生成器：`scripts/audit_estimator_circularity.py`（离线只读，零新增电子结构）",
        "- 产物：`outputs/week27/estimator_circularity.json`、`outputs/week27/estimator_circularity.md`",
        "",
        "## 0. 一句话结论",
        "",
        "**本仓库的解析/不可解析判据是自指的**：主约定把**被比较的两个模型本身**喂给不确定度估计器",
        "（两臂 sigma，R = 2），于是 `sigma_ij = |dP_A - dP_B| / sqrt(2)`（T1）。由此可证：",
        "在冻结的 `z` 下 **`ROBUST_INVERSION` 根本不可能发生**（T6a），而且**双方都解析的 pair 里",
        "一对反向的都没有**（T6b）——也就是说，这条流水线**从来不能认证任何分歧**。",
        "`f_robust_inv = 0` 因此不是经验观察，而是**定义性不变量**；Stage 10 的预注册假设 C",
        "（structured robust inversion）不是「未观察到」，而是**在该约定下不可检验**。",
        "",
        "这不是推翻结论，而是把结论**从经验巧合升级为代数必然**：数据确实无法识别排序。",
        "但它要求三处口径改写（见 §6）。",
        "",
        "## 1. 口径",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "| sigma | `" + str(payload["convention"]).split(";")[0].replace("|", "/") + "` |",
        "| 解析 | `|dP| >= z * sigma` 且 `|dP| > 0` |",
        "| ROBUST_INVERSION | 两模型都解析且符号相反 |",
        "| f_robust_inv | `N_robust / N_resolved_in_both`（分母是两个模型都解析的 pair 数） |",
        "| 冻结 z | " + ", ".join("`%.3g`" % z for z in th["T6a_inversion_impossible"]["frozen_z_values"]) + " |",
        "",
        "## 2. 四条定理（`--check` 逐字节复核）",
        "",
        "| 定理 | 陈述 | 检验量 | 结果 |",
        "| --- | --- | --- | --- |",
    ]
    t1 = th["T1_two_arm_sigma_identity"]
    lines.append("| T1 | `sigma_ij = \\|dP_A - dP_B\\| / sqrt(2)` | max abs err | **%.2e eV** |"
                 % t1["max_abs_err_ev"])
    t6a = th["T6a_inversion_impossible"]
    lines.append("| T6a | 反转需 `z <= 1/sqrt(2)`；冻结 `z` 全部超过 | `z*` = %.6f | **%s** |"
                 % (t6a["z_max_for_inversion"],
                    "冻结 z 全部排除反转" if t6a["all_frozen_z_exclude_inversion"] else "存在可反转的 z"))
    t6b = th["T6b_no_certifiable_disagreement"]
    lines.append("| T6b | 双方解析子集内反向 pair 数为 0 | max 计数 | **%d** |" % t6b["max_n_discordant_both"])
    t7 = th["T7_ratio_rule"]
    lines.append("| T7 | 解析判据 = `\\|dY\\|/\\|dX\\|` 的比值律 | 与 `resolved_mask` 不符数 | **%d** |"
                 % t7["rule_mismatch"])
    lines += [
        "",
        "比值律（T7 的显式形式）：",
        "",
        "- 同号：`(1 - sqrt(2)/z) <= |dY|/|dX| <= (1 + sqrt(2)/z)`",
        "- 反号：`|dY|/|dX| <= sqrt(2)/z - 1`（`z >= sqrt(2)` 时为空集）",
        "",
        "## 3. 逐 block 结果",
        "",
        "| rung | 轴 | n | f_robust_inv（冻结） | 双方解析(z=1) | 反向(z=1) | 双方解析(z=1.96) | 反向(z=1.96) | 比值律不符 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for b in payload["blocks"]:
        p = b["bands"]["z_primary"]
        s = b["bands"]["z_sensitivity"]
        lines.append(
            "| %s | %s | %d | %s | %d | %d | %d | %d | %d |"
            % (b["rung"], b["axis"], b["n"], _num(b["f_robust_inv_frozen"], 3),
               p["n_resolved_both"], p["n_discordant_both"],
               s["n_resolved_both"], s["n_discordant_both"],
               p["rule_mismatch"] + s["rule_mismatch"])
        )
    mc = payload["multisource_contrast"]
    two = mc["two_arm"] or {}
    multi = mc["multi_source"] or {}
    lines += [
        "",
        "## 4. 多来源 σ 对照（把假设 C 变成可检验）",
        "",
        "同一批分子、同一批层，**只换 σ 约定**：",
        "",
        "| σ 约定 | 实现数 R | 最大 f_robust_inv (z=1) | 是否出现反转 |",
        "| --- | --- | --- | --- |",
        "| 两臂（主约定） | 2 | %s | %s |"
        % (_num(two.get("max_f_robust_inv_z1p0"), 4), "否" if not two.get("any_gt_0_z1p0") else "是"),
        "| 多来源（docs/08 §5） | 5 | %s | %s |"
        % (_num(multi.get("max_f_robust_inv_z1p0"), 4), "是" if multi.get("any_gt_0_z1p0") else "否"),
        "",
        "> %s" % mc["reading"],
        "> 绝对计数：`max_n_robust_inversions_z1p0 = %s`（分母是**双方都解析**的 51–60 对，不是 66 对）。"
        % mc["max_n_robust_inversions_z1p0"],
        "",
        "## 5. 预注册假设的可检验性",
        "",
        "| 假设 | 冻结判据 | 冻结结论 | 该约定下可检验性 |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["hypotheses"]:
        lines.append("| `%s` | %s | %s | **%s** |"
                     % (row["hypothesis"], row["metric"] or "-",
                        row["frozen_verdict"] or "-",
                        row["testability_under_frozen_convention"]))
    lines += [
        "",
        "## 6. 必须改写的三处口径",
        "",
        "1. **`f_robust_inv = 0` 不得再作为经验观察引用**。它是两臂 σ 约定下的定义性不变量",
        "   （T6a：`z > 1/sqrt(2)` 即不可能）；引用时必须同时给出 σ 约定与该约定下的分母。",
        "2. **Stage 10 假设 C 由 `NOT OBSERVED` 改判 `NOT TESTABLE`**。可检验版本必须换用",
        "   R >= 3 的多来源 σ（§4 已给出阳性对照：同一数据下出现 1 对反转）。",
        "3. **`f_unresolved` 是比值量**（T7）：它度量的是两个模型对同一 pair 的分歧**相对于**",
        "   pair 自身间距的大小，不含任何绝对噪声尺度。报告应同时给出比值分布或其分位。",
        "",
        "## 7. 产物与复现",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\audit_estimator_circularity.py --check",
        ".venv\\Scripts\\python.exe scripts\\audit_estimator_circularity.py",
        "```",
        "",
        "本审计零新增电子结构计算；全部数字从 `outputs/week4`、`outputs/week5`、`outputs/week9`",
        "的冻结产物读回。结论见 `docs/49_round3_adversarial_audit.md`。",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R15 estimator-circularity audit (read-only).")
    parser.add_argument("--check", action="store_true", help="compare against the frozen artefacts")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = build()
    js = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    md = render_markdown(payload)
    outdir = args.outdir
    artefacts = (("estimator_circularity.json", js), ("estimator_circularity.md", md))
    if args.check:
        stale = []
        for name, text in artefacts:
            path = outdir / name
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        if stale:
            print("STALE: " + ", ".join(stale))
            return 1
        print("CHECK OK -- estimator-circularity artefacts are byte-identical")
        return 0
    outdir.mkdir(parents=True, exist_ok=True)
    for name, text in artefacts:
        (outdir / name).write_text(text, encoding="utf-8", newline="\n")
    th = payload["theorems"]
    print("R15 estimator-circularity audit")
    print("  T1 sigma identity max err : %.2e eV" % th["T1_two_arm_sigma_identity"]["max_abs_err_ev"])
    print("  T6a z* (inversion)        : %.6f" % th["T6a_inversion_impossible"]["z_max_for_inversion"])
    print("  T6b discordant-in-both    : %d" % th["T6b_no_certifiable_disagreement"]["max_n_discordant_both"])
    print("  T7 ratio-rule mismatches  : %d" % th["T7_ratio_rule"]["rule_mismatch"])
    print("  wrote %s" % outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())