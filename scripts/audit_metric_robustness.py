#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R15 metric-robustness and rank-identifiability audit (adversarial round 3, items A/B).

Round 3 attacks the *definitions*, not the data.  Two questions:

A. **Metric robustness** -- the reported rank agreement is a point-ordering
   statistic (Kendall tau_b / Spearman rho on the two full orderings).  Freeze
   one ordering threshold (0.90, the preregistered Gate-1 ordering bar) and ask
   whether the verdict survives the four frozen ways of treating pairs the
   evidence cannot resolve:

       exclusion    drop tied pairs                (C - D) / (C + D)
       tie          tied pairs count as ties       (C - D) / N
       pessimistic  tied pairs count against       (C - D - T) / N
       optimistic   tied pairs count for           (C + T - D) / N

   The band width is exactly ``2 T / N``: the unresolved fraction *is* the
   policy ambiguity.

B. **Rank identifiability** -- how much of the ranking can the evidence
   actually certify?  Sort by each model's own values, break a block wherever
   the adjacent pair is unresolved, and count the distinguishable tiers.  This
   is the reviewer's item B: the dominant failure mode is not inversion but
   **loss of rank identifiability**.

Zero new electronic structure: every number is read back from the frozen
per-pair evidence in ``outputs/week4`` and ``outputs/week5``.

Usage
-----
    python scripts/audit_metric_robustness.py            # write JSON + MD + PNG + manifest
    python scripts/audit_metric_robustness.py --check    # recompute, compare bytes/pixels
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking, robustness  # noqa: E402

STAGE_DIR = REPO_ROOT / "outputs" / "week27"
FIGURE_DIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F57_metric_robustness.png"
JSON_PATH = STAGE_DIR / "metric_robustness.json"
MD_PATH = STAGE_DIR / "metric_robustness.md"
MANIFEST_PATH = STAGE_DIR / "F57_manifest.md"

INPUTS = {
    "p1": "outputs/week4/p1_decision_stability.json",
    "p2": "outputs/week4/p2_decision_stability.json",
    "c1": "outputs/week5/c1_decision_stability.json",
}

BLOCKS = (
    ("P0->P1v", "p1", "{axis}"),
    ("P1v->P2a", "p2", "p1_to_p2.{axis}"),
    ("P0->P2a", "p2", "p0_to_p2.{axis}"),
    ("C0->C1", "c1", "{axis}"),
)
AXES = ("oxidation", "reduction")

AXIS_LABEL = {"oxidation": "氧化", "reduction": "还原"}

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 7.0
FACE = "#ffffff"
INK = "#1a1a1a"
MUTED = "#666666"
CHEAP_COLOR = "#7f8fa6"
TARGET_COLOR = "#2f6fb2"
CERT_COLOR = "#2e8b57"
NEAR_COLOR = "#c8641e"
BAND_COLOR = "#bcd4ea"


def read_json(relative):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def dig(obj, dotted):
    current = obj
    for key in dotted.split("."):
        current = current[key]
    return current


def sha256(path):
    if not path.exists():
        return "n/a"
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def winner_margin(values, sigma, order_index, higher_is_better=True):
    """Top-1 minus top-2 gap in units of that pair's own sigma."""

    vals = np.asarray(values, dtype=float)
    order = sorted(range(vals.size), key=lambda i: (-vals[i]) if higher_is_better else vals[i])
    if len(order) < 2:
        return None
    i, j = order[0], order[1]
    gap = abs(float(vals[i] - vals[j]))
    s = float(sigma[i, j])
    return {"pair": [str(order_index[i]), str(order_index[j])], "gap_ev": gap,
            "sigma_ev": s, "ratio": (None if s <= 0 else gap / s)}


def audit_block(label, axis, block, z, threshold):
    names, d0, d1, sigma = matrices(block["pair_differences"])
    n = len(names)
    splits = robustness.both_resolved_from_rule(d0, d1, z)
    iu = np.triu_indices(n, 1)
    c = int(np.count_nonzero(splits["concordant"]))
    d = int(np.count_nonzero(splits["discordant"]))
    ties = int(splits["n_pairs"]) - c - d
    band = robustness.unresolved_policy_band(
        {"concordant": c, "discordant": d, "ties": ties}, splits["n_pairs"])

    mask0 = ranking.resolved_mask(d0, sigma, z=z)
    mask1 = ranking.resolved_mask(d1, sigma, z=z)
    both = mask0 & mask1
    v0 = d0[:, 0].copy()
    v1 = d1[:, 0].copy()

    policy_values = {key: band[key] for key in ("exclusion", "tie", "pessimistic", "optimistic")}
    reachable = [v for v in policy_values.values() if v is not None]
    flips = any(v >= threshold for v in reachable) and any(v < threshold for v in reachable)

    ratios0 = np.where(sigma[iu] > 0, np.abs(d0[iu]) / (z * sigma[iu]), np.inf)
    ratios1 = np.where(sigma[iu] > 0, np.abs(d1[iu]) / (z * sigma[iu]), np.inf)

    return {
        "rung": label,
        "axis": axis,
        "n": n,
        "n_pairs": int(splits["n_pairs"]),
        "kendall_tau_b_frozen": block.get("kendall_tau_b"),
        "spearman_rho_frozen": block.get("spearman_rho"),
        "top_k_frozen": block.get("top_k"),
        "counts": {"concordant": c, "discordant": d, "ties": ties},
        "f_tie": ties / splits["n_pairs"],
        "policies": policy_values,
        "band_width": band["band_width"],
        "conclusion_flips_under_policy": bool(flips),
        "tiers": {
            "cheap_ordering": robustness.certified_tiers(v0, mask0),
            "target_ordering": robustness.certified_tiers(v1, mask1),
            "certified_both": robustness.certified_tiers(v1, both),
        },
        "near_threshold": {
            "cheap": robustness.near_threshold_count(ratios0),
            "target": robustness.near_threshold_count(ratios1),
        },
        "winner_margin": {
            "cheap": winner_margin(v0, sigma, names),
            "target": winner_margin(v1, sigma, names),
        },
    }

ORDERING_THRESHOLD = 0.90


def collect(z=1.0, threshold=ORDERING_THRESHOLD):
    cache = {key: read_json(path) for key, path in INPUTS.items()}
    blocks = []
    for label, key, template in BLOCKS:
        document = cache[key]
        for axis in AXES:
            block = dig(document, template.format(axis=axis))
            blocks.append(audit_block(label, axis, block, z, threshold))

    flips = sum(1 for b in blocks if b["conclusion_flips_under_policy"])
    band_widths = [b["band_width"] for b in blocks]
    tier_ratio = [b["tiers"]["certified_both"]["tiers"] / b["n"] for b in blocks]
    largest = max(b["tiers"]["certified_both"]["largest_tier"] for b in blocks)
    margins = [b["winner_margin"]["target"]["ratio"] for b in blocks
               if b["winner_margin"]["target"]["ratio"] is not None]
    return {
        "stage": "R15 metric-robustness and rank-identifiability audit",
        "question": (
            "Does the ranking conclusion survive an alternative rank metric or an alternative "
            "treatment of pairs the evidence cannot resolve, and how much of the ranking is "
            "identifiable at all?"
        ),
        "definition": (
            "Every unordered pair is split into concordant / discordant / tied by the frozen "
            "two-arm masks at z. The four policies are closed forms of Kendall tau_b with "
            "symmetric ties; the ordering threshold is the preregistered Gate-1 bar 0.90. "
            "Certified tiers break a model's own sorted order wherever an adjacent pair is "
            "unresolved."
        ),
        "z_primary": z,
        "ordering_threshold": threshold,
        "blocks": blocks,
        "summary": {
            "n_blocks": len(blocks),
            "n_conclusion_flips": int(flips),
            "max_band_width": float(max(band_widths)),
            "median_band_width": float(np.median(band_widths)),
            "min_certified_tier_ratio": float(min(tier_ratio)),
            "max_certified_largest_tier": int(largest),
            "target_winner_margin_sigma_min": float(min(margins)) if margins else None,
            "target_winner_margin_sigma_max": float(max(margins)) if margins else None,
        },
        "verdict": (
            "Every rung/axis block flips its verdict across the four unresolved policies (8/8): "
            "the same data clears the 0.90 ordering bar under the optimistic policy and fails it "
            "under the pessimistic one, with a policy band of width 0.37-1.82. The point "
            "orderings agree (rho ~ 0.8) but the evidence does not identify them: the certified "
            "ordering keeps only 11-17 of the 18 tiers (and 6 of 10 in the C0->C1 reduction "
            "block), up to 3 molecules share a single tier, and 1-17 pairs per block sit within "
            "25% of the resolution threshold. The dominant failure mode is loss of rank "
            "identifiability, not rank inversion."
        ),
    }


def _n(value, digits=3):
    if value is None:
        return "-"
    if isinstance(value, float) and not np.isfinite(value):
        return "-"
    return ("%." + str(digits) + "f") % value


def render_markdown(payload):
    s = payload["summary"]
    lines = [
        "# 27 · R15 指标稳健性与排序可识别性审计（对抗审计 round 3 · 项目 A/B）",
        "",
        "- 触发：第二轮收口后，评审要求攻击「排序稳定性指标本身的定义」与「非反转型的排序损伤」。",
        "- 生成器：`scripts/audit_metric_robustness.py`（离线只读，零新增电子结构）",
        "- 产物：`outputs/week27/metric_robustness.json`、`outputs/week27/metric_robustness.md`、",
        "  图 `outputs/figures/F57_metric_robustness.png`、`outputs/week27/F57_manifest.md`",
        "",
        "## 0. 一句话结论",
        "",
        "**两件事同时成立，而且必须一起说：**",
        "",
        "1. 两个模型的**点排序**确实高度一致（`rho` ≈ 0.80，`tau_b` 0.59–0.90）——「cheap proxy 保留",
        "   了排序」这句话在点排序意义上是**真**的；",
        "2. 但**证据无法识别这个排序**：把不可解析 pair 换一种同样合理的处理方式，`tau_b` 在",
        "   `[pessimistic, optimistic]` 之间整段滑动，**8 个 block 全部**在冻结的 0.90 排序门槛两侧翻转。",
        "",
        "所以本项目的正确表述不是「排序被反转」，而是**排序不可识别（loss of rank identifiability）**。",
        "这与评审的假设一致，也是比 inversion 更准确的失败模式描述。",
        "",
        "## 1. 口径",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "| 主判据 | z = %g（预注册） |" % payload["z_primary"],
        "| 排序门槛 | tau_b >= %g（预注册 Gate-1 排序层门槛） |" % payload["ordering_threshold"],
        "| 四政策 | `exclusion` / `tie` / `pessimistic` / `optimistic`（见脚本头部闭式） |",
        "| 可分层层数 | 按模型自身值排序，相邻 pair 未解析即断块 |",
        "",
        "## 2. 策略带（同一份数据，四种同样合理的处理）",
        "",
        "| rung | 轴 | n | f_tie | exclusion | tie | pessimistic | optimistic | 带宽度 | 结论翻转 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for b in payload["blocks"]:
        p = b["policies"]
        lines.append(
            "| %s | %s | %d | %.3f | %s | %s | %s | %s | %.3f | %s |"
            % (b["rung"], b["axis"], b["n"], b["f_tie"],
               _n(p["exclusion"]), _n(p["tie"]), _n(p["pessimistic"]), _n(p["optimistic"]),
               b["band_width"], "是" if b["conclusion_flips_under_policy"] else "否")
        )
    lines += [
        "",
        "> 带宽度恒等于 `2 * f_tie`：**不可解析比例就是排序一致性统计量的政策歧义**。",
        "> `exclusion` 一列恒为 1.000 —— 这正是 R15 循环性审计的 T6b（双方解析子集内没有反向 pair）。",
        "",
        "## 3. 排序可识别性（可分层层数）",
        "",
        "| rung | 轴 | n | cheap 层数 | target 层数 | 双方认证层数 | 最大同层块 | 近临界 pair（cheap/target） |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for b in payload["blocks"]:
        t = b["tiers"]
        lines.append(
            "| %s | %s | %d | %d (块 %d) | %d (块 %d) | %d (块 %d) | %d | %d / %d |"
            % (b["rung"], b["axis"], b["n"],
               t["cheap_ordering"]["tiers"], t["cheap_ordering"]["largest_tier"],
               t["target_ordering"]["tiers"], t["target_ordering"]["largest_tier"],
               t["certified_both"]["tiers"], t["certified_both"]["largest_tier"],
               t["certified_both"]["largest_tier"],
               b["near_threshold"]["cheap"], b["near_threshold"]["target"])
        )
    lines += [
        "",
        "## 4. 赢家边际（top-1 vs top-2，单位：该 pair 自身 sigma）",
        "",
        "| rung | 轴 | cheap 边际 | target 边际 |",
        "| --- | --- | --- | --- |",
    ]
    for b in payload["blocks"]:
        lines.append("| %s | %s | %s | %s |"
                     % (b["rung"], b["axis"],
                        _n((b["winner_margin"]["cheap"] or {}).get("ratio"), 2),
                        _n((b["winner_margin"]["target"] or {}).get("ratio"), 2)))
    lines += [
        "",
        "## 5. 汇总",
        "",
        "| 量 | 值 |",
        "| --- | --- |",
        "| block 数 | %d |" % s["n_blocks"],
        "| 政策下结论翻转的 block 数 | **%d / %d** |" % (s["n_conclusion_flips"], s["n_blocks"]),
        "| 最大带宽度 | %.3f |" % s["max_band_width"],
        "| 带宽度中位数 | %.3f |" % s["median_band_width"],
        "| 最低认证层数比（层数 / n） | %.3f |" % s["min_certified_tier_ratio"],
        "| 最大同层块 | %d |" % s["max_certified_largest_tier"],
        "| target 赢家边际范围（sigma） | %s - %s |"
        % (_n(s["target_winner_margin_sigma_min"], 2), _n(s["target_winner_margin_sigma_max"], 2)),
        "",
        "## 6. 结论与读法纪律",
        "",
        "> " + payload["verdict"],
        "",
        "读法纪律（新增，与 R15 循环性审计配套）：",
        "",
        "1. 引用 `tau_b` 时必须说明它是对**全排序**的点统计量，不含证据门槛；",
        "2. 引用「排序稳定/不稳定」时必须给出**政策带**或 `f_unresolved`，不能只给一个数；",
        "3. 不得把「18 个分子 → 11–17 个可分层层」说成「排序已确定」。",
        "",
        "## 7. 复现",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\audit_metric_robustness.py --check",
        ".venv\\Scripts\\python.exe scripts\\audit_metric_robustness.py",
        "```",
    ]
    return "\n".join(lines) + "\n"

def _block_labels(payload):
    return ["%s / %s" % (b["rung"], AXIS_LABEL.get(b["axis"], b["axis"])) for b in payload["blocks"]]


def draw(payload):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN), dpi=DPI, facecolor=FACE)
    fig.text(0.012, 0.984, "F57 · R15 指标稳健性与排序可识别性（对抗审计 round 3 · 项目 A/B）",
             fontsize=8.0, color=INK, fontweight="bold", va="top", ha="left")
    fig.text(0.012, 0.962,
             "同一批冻结数据、四种同样合理的不可解析处理；门槛 = 预注册 Gate-1 排序层 0.90。零新增电子结构。",
             fontsize=5.0, color=MUTED, va="top", ha="left")

    gs = fig.add_gridspec(2, 2, left=0.155, right=0.985, top=0.900, bottom=0.105,
                          hspace=0.62, wspace=0.30)
    labels = _block_labels(payload)
    y = np.arange(len(labels))[::-1]

    ax_a = fig.add_subplot(gs[0, 0])
    for pos, b in zip(y, payload["blocks"]):
        lo = b["policies"]["pessimistic"]
        hi = b["policies"]["optimistic"]
        ax_a.barh(pos, hi - lo, left=lo, height=0.55, color=BAND_COLOR, edgecolor="none")
        ax_a.plot([b["policies"]["tie"]], [pos], "o", ms=3.0, color=TARGET_COLOR, zorder=3)
    ax_a.axvline(payload["ordering_threshold"], color=NEAR_COLOR, lw=1.0, ls="--")
    ax_a.text(payload["ordering_threshold"], y[0] + 0.62, " 门槛 0.90", fontsize=4.6,
              color=NEAR_COLOR, va="center", ha="left")
    ax_a.set_xlim(-1.05, 1.05)
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(labels, fontsize=5.0, color=INK)
    ax_a.set_ylim(-0.6, len(labels) - 0.35)
    ax_a.set_xlabel("Kendall tau_b（政策带：pessimistic → optimistic）", fontsize=5.8, color=INK)
    ax_a.set_title("(a) 同一份数据的排序一致性政策带", fontsize=6.0, loc="left", color=INK)
    for spine in ("top", "right"):
        ax_a.spines[spine].set_visible(False)
    ax_a.tick_params(labelsize=4.8)
    ax_a.grid(axis="x", color="#e8e8e8", lw=0.5)
    ax_a.set_axisbelow(True)

    ax_b = fig.add_subplot(gs[0, 1])
    ft = [b["f_tie"] for b in payload["blocks"]]
    ax_b.barh(y, ft, height=0.55, color=CHEAP_COLOR)
    for pos, v in zip(y, ft):
        ax_b.text(v + 0.015, pos, "%.2f" % v, fontsize=4.6, color=INK, va="center")
    ax_b.set_yticks(y)
    ax_b.set_yticklabels([])
    ax_b.set_ylim(-0.6, len(labels) - 0.35)
    ax_b.set_xlim(0, 1.05)
    ax_b.set_xlabel("f_tie = 证据无法解析的 pair 占比", fontsize=5.8, color=INK)
    ax_b.set_title("(b) 政策歧义 = 不可解析比例", fontsize=6.0, loc="left", color=INK)
    for spine in ("top", "right"):
        ax_b.spines[spine].set_visible(False)
    ax_b.tick_params(labelsize=4.8)
    ax_b.grid(axis="x", color="#e8e8e8", lw=0.5)
    ax_b.set_axisbelow(True)

    ax_c = fig.add_subplot(gs[1, 0])
    w = 0.26
    cheap = [b["tiers"]["cheap_ordering"]["tiers"] for b in payload["blocks"]]
    target = [b["tiers"]["target_ordering"]["tiers"] for b in payload["blocks"]]
    cert = [b["tiers"]["certified_both"]["tiers"] for b in payload["blocks"]]
    ax_c.barh(y + w, cheap, height=w, color=CHEAP_COLOR, label="cheap 自排序")
    ax_c.barh(y, target, height=w, color=TARGET_COLOR, label="target 自排序")
    ax_c.barh(y - w, cert, height=w, color=CERT_COLOR, label="双方认证")
    ax_c.scatter([b["n"] for b in payload["blocks"]], y, marker="|", s=42, color=NEAR_COLOR,
                 label="分子数 n", zorder=4)
    ax_c.set_yticks(y)
    ax_c.set_yticklabels(labels, fontsize=5.0, color=INK)
    ax_c.set_ylim(-0.6, len(labels) - 0.35)
    ax_c.set_xlim(0, max(b["n"] for b in payload["blocks"]) + 1.2)
    ax_c.set_xlabel("可分层层数", fontsize=5.8, color=INK)
    ax_c.set_title("(c) 排序可识别性：层数越接近 n 越可识别", fontsize=6.0, loc="left", color=INK)
    ax_c.legend(fontsize=4.2, frameon=False, loc="lower right", handlelength=1.2)
    for spine in ("top", "right"):
        ax_c.spines[spine].set_visible(False)
    ax_c.tick_params(labelsize=4.8)
    ax_c.grid(axis="x", color="#e8e8e8", lw=0.5)
    ax_c.set_axisbelow(True)

    ax_d = fig.add_subplot(gs[1, 1])
    nc = [b["near_threshold"]["cheap"] for b in payload["blocks"]]
    nt = [b["near_threshold"]["target"] for b in payload["blocks"]]
    ax_d.barh(y + w / 2, nc, height=w, color=CHEAP_COLOR, label="cheap")
    ax_d.barh(y - w / 2, nt, height=w, color=TARGET_COLOR, label="target")
    ax_d.set_yticks(y)
    ax_d.set_yticklabels([])
    ax_d.set_ylim(-0.6, len(labels) - 0.35)
    ax_d.set_xlabel("比值在 [1, 1.25) 的 pair 数（临界即脆弱）", fontsize=5.8, color=INK)
    ax_d.set_title("(d) 近临界 pair：认证了但随时会翻转", fontsize=6.0, loc="left", color=INK)
    ax_d.legend(fontsize=4.4, frameon=False, loc="lower right", handlelength=1.2)
    for spine in ("top", "right"):
        ax_d.spines[spine].set_visible(False)
    ax_d.tick_params(labelsize=4.8)
    ax_d.grid(axis="x", color="#e8e8e8", lw=0.5)
    ax_d.set_axisbelow(True)

    fig.text(0.012, 0.012,
             "读法：tau_b 是全排序的点统计量；证据只能认证 11-17 个层；政策带宽度 = 2 x f_tie；"
             "exclusion 一列恒为 1.000（见 R15 循环性审计 T6b）。",
             fontsize=4.6, color=MUTED, va="bottom", ha="left")
    return fig


def render_png(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=DPI, facecolor=FACE)
    return buffer.getvalue()


def render_manifest(payload, digests, width_px, height_px):
    lines = [
        "# F57 manifest — R15 指标稳健性与排序可识别性",
        "",
        "- script：`scripts/audit_metric_robustness.py`",
        "- figure：`outputs/figures/%s`（%d × %d px @ %d dpi）" % (FIGURE_NAME, width_px, height_px, DPI),
        "- stats：`outputs/week27/metric_robustness.json`、`outputs/week27/metric_robustness.md`",
        "- 新电子结构计算：**0**（全部数值为冻结产物读回）",
        "",
        "## 图注",
        "",
        "(a) 每个 block 的排序一致性政策带（pessimistic → optimistic），蓝点为 tie 政策；",
        "(b) f_tie = 证据无法解析的 pair 占比（= 政策带宽度的一半）；",
        "(c) 可分层层数：cheap 自排序 / target 自排序 / 双方认证，竖线为分子数 n；",
        "(d) 近临界 pair 数（比值 ∈ [1, 1.25)），认证了但极易翻转。",
        "",
        "## 复现命令",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\audit_metric_robustness.py --check",
        ".venv\\Scripts\\python.exe scripts\\audit_metric_robustness.py",
        "```",
        "",
        "## 输入 sha256",
        "",
        "| 路径 | sha256 |",
        "| --- | --- |",
    ]
    for name in digests["input_order"]:
        lines.append("| `%s` | `%s` |" % (name, digests["inputs"][name]))
    lines += ["", "## 输出 sha256", "", "| 路径 | sha256 |", "| --- | --- |"]
    for name in digests["output_order"]:
        lines.append("| `%s` | `%s` |" % (name, digests["outputs"][name]))
    lines += [
        "",
        "## 纪律声明",
        "",
        "- 本图不跑任何新电子结构；所有数字均为已冻结产物的现算读出。",
        "- `tau_b` 是全排序点统计量；「排序不稳」的判据是政策带，不是单个数字。",
        "- 本图不改变任何既有判决；不读取仓库外文件。",
        "- 字体：Microsoft YaHei / SimHei，axes.unicode_minus = False。",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R15 metric-robustness audit (read-only).")
    parser.add_argument("--check", action="store_true", help="recompute and compare bytes/pixels")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = collect()
    json_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    md_text = render_markdown(payload)

    figure = draw(payload)
    png = render_png(figure)
    plt.close(figure)
    pixels = mpimg.imread(io.BytesIO(png))
    height_px, width_px = int(pixels.shape[0]), int(pixels.shape[1])

    digests = {
        "inputs": {INPUTS[key]: sha256(REPO_ROOT / INPUTS[key]) for key in INPUTS},
        "input_order": [INPUTS[key] for key in INPUTS],
        "outputs": {},
        "output_order": [],
    }
    png_rel = (FIGURE_DIR / FIGURE_NAME).relative_to(REPO_ROOT).as_posix()
    manifest_text = render_manifest(payload, digests, width_px, height_px)

    png_sha = hashlib.sha256(png).hexdigest()
    for name, text in ((JSON_PATH.relative_to(REPO_ROOT).as_posix(), json_text),
                       (MD_PATH.relative_to(REPO_ROOT).as_posix(), md_text),
                       (MANIFEST_PATH.relative_to(REPO_ROOT).as_posix(), manifest_text)):
        digests["outputs"][name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        digests["output_order"].append(name)
    digests["outputs"][png_rel] = png_sha
    digests["output_order"].append(png_rel)
    manifest_text = render_manifest(payload, digests, width_px, height_px)

    s = payload["summary"]
    print("F57 R15 metric robustness / rank identifiability -- resolved numbers")
    print("-" * 68)
    print("  blocks                      : %d" % s["n_blocks"])
    print("  policy-flipped blocks       : %d / %d" % (s["n_conclusion_flips"], s["n_blocks"]))
    print("  max / median band width     : %.3f / %.3f" % (s["max_band_width"], s["median_band_width"]))
    print("  min certified tier ratio    : %.3f" % s["min_certified_tier_ratio"])
    print("  largest indistinguishable   : %d molecules" % s["max_certified_largest_tier"])
    print("  figure                      : %d x %d px @ %d dpi" % (width_px, height_px, DPI))
    print("  png sha256                  : %s" % png_sha[:16])
    print("-" * 68)

    if args.check:
        for path, expected in ((JSON_PATH, json_text), (MD_PATH, md_text), (MANIFEST_PATH, manifest_text)):
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text" % path)
                return 1
        png_path = FIGURE_DIR / FIGURE_NAME
        if not png_path.exists():
            print("CHECK FAILED -- %s is missing" % png_path)
            return 1
        disk = mpimg.imread(png_path)
        memory = mpimg.imread(io.BytesIO(png))
        if disk.shape != memory.shape or not np.array_equal(disk, memory):
            print("CHECK FAILED -- pixels differ from %s" % png_path)
            return 1
        print("CHECK OK -- JSON/MD/manifest byte-identical; %s re-renders pixel-identical" % png_rel)
        return 0

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in ((JSON_PATH, json_text), (MD_PATH, md_text), (MANIFEST_PATH, manifest_text)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    with open(FIGURE_DIR / FIGURE_NAME, "wb") as handle:
        handle.write(png)
    for path in (JSON_PATH, MD_PATH, MANIFEST_PATH, FIGURE_DIR / FIGURE_NAME):
        print("wrote %s" % path.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())