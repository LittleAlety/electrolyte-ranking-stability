"""Week 24 -- Stage 8 active-learning replay distilled into a minimal expensive-label budget.

Read-only distillation of the frozen Stage 8 replay.  This script never calls
ORCA / xTB and never modifies a frozen artefact.

Mapping to the core file (v2):
* Sec.14      n_T -> {tau_b, O_k, R_k} curves for four acquisition baselines;
* Sec.14.3    ranking-aware acquisition (binary entropy of the posterior
              Top-k membership probability) is the reference smart baseline;
* Sec.23 (11) high-cost-label budget vs decision accuracy;
* Sec.24 F7   flagged as possibly the most methodologically distinctive figure.

Outputs
-------
outputs/week24_corealign/al_budget.json   structured results
outputs/week24_corealign/al_budget.csv    the tau_b >= 0.80 budget table
outputs/week24_corealign/al_budget.md     narrative + three-line tables
outputs/figures/F49_al_budget.png         decision triple at the recovery budget

Determinism
-----------
No wall-clock time is written.  The only generated time recorded is the one
already frozen inside the input JSON, so re-running reproduces the outputs byte
for byte.  --check recomputes everything in memory and compares against disk,
including the recorded input SHA256 fingerprints.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEEK7 = REPO_ROOT / "outputs" / "week7"
RESULTS_JSON = WEEK7 / "stage8_al_results.json"
CURVES_CSV = WEEK7 / "stage8_al_curves.csv"
SUMMARY_MD = WEEK7 / "stage8_al_summary.md"
F17_PNG = REPO_ROOT / "outputs" / "figures" / "F17_stage8_active_learning.png"

OUTDIR = REPO_ROOT / "outputs" / "week24_corealign"
OUT_JSON = OUTDIR / "al_budget.json"
OUT_CSV = OUTDIR / "al_budget.csv"
OUT_MD = OUTDIR / "al_budget.md"
OUT_FIG = REPO_ROOT / "outputs" / "figures" / "F49_al_budget.png"

TAU_THRESHOLD = 0.80
TAU_EPS = 1e-9
TAU = "kendall_tau_b"

TASK_ORDER = ("C", "E", "M")
OBJECTIVE_ORDER = ("oxidation", "reduction")
POOLS = [(t, o) for t in TASK_ORDER for o in OBJECTIVE_ORDER]
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")
SIMPLE_BASELINES = ("random", "diversity", "uncertainty")
SMART = "ranking_aware"
K_FRACS = (10, 20, 30)
AXIS_ZH = {"oxidation": "氧化", "reduction": "还原"}

BASELINE_COLORS = {
    "random": "#8c8c8c",
    "diversity": "#2ca02c",
    "uncertainty": "#ff7f0e",
    "ranking_aware": "#7d3fbf",
}

INPUTS = (
    ("stage8_al_results.json", RESULTS_JSON),
    ("stage8_al_curves.csv", CURVES_CSV),
    ("stage8_al_summary.md", SUMMARY_MD),
    ("F17_stage8_active_learning.png", F17_PNG),
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def okey(k):
    return "top_k_overlap_{}%".format(k)


def rkey(k):
    return "selection_regret_{}%".format(k)


def r3(x):
    if x is None:
        return None
    return round(float(x), 3)


def f3(x):
    if x is None:
        return ""
    return "{:.3f}".format(float(x))


def label(t, o):
    return "{} · {}".format(t, AXIS_ZH[o])


def ascii_label(t, o):
    return "{}/{}".format(t, "ox" if o == "oxidation" else "red")


def load_results():
    with open(RESULTS_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def pool_sizes(doc):
    out = {}
    for key, meta in doc["pools"].items():
        t, o = key.split(":")
        out[(t, o)] = int(meta["n_pool"])
    return out


def index_curves(doc):
    curves = {}
    for row in doc["curves"]:
        key = (row["task"], row["objective"])
        curves.setdefault(key, {}).setdefault(row["baseline"], {})[int(row["n_T"])] = row
    return curves


def valid_nt(curves, sizes, t, o, baseline):
    n_pool = sizes[(t, o)]
    return sorted(n for n in curves[(t, o)][baseline] if n < n_pool)


# --------------------------------------------------------------------------- #
# analyses
# --------------------------------------------------------------------------- #
def budget_entry(curves, sizes, t, o, b):
    n_pool = sizes[(t, o)]
    valid = valid_nt(curves, sizes, t, o, b)
    last_nt = max(valid)
    star = None
    for n in valid:
        if curves[(t, o)][b][n][TAU] >= TAU_THRESHOLD - TAU_EPS:
            star = n
            break
    if star is None:
        return {
            "task": t, "objective": o, "baseline": b, "pool_n": n_pool,
            "last_nontrivial_n_T": last_nt,
            "budget_n_T": "> n", "budget_n_T_value": None,
            "reached_before_endpoint": False,
            "tau_b": None, "tau_b_lo": None, "tau_b_hi": None,
        }
    row = curves[(t, o)][b][star]
    return {
        "task": t, "objective": o, "baseline": b, "pool_n": n_pool,
        "last_nontrivial_n_T": last_nt,
        "budget_n_T": star, "budget_n_T_value": star,
        "reached_before_endpoint": True,
        "tau_b": r3(row[TAU]), "tau_b_lo": r3(row[TAU + "_lo"]),
        "tau_b_hi": r3(row[TAU + "_hi"]),
    }


def compare_entries(curves, sizes, t, o):
    out = []
    for n in valid_nt(curves, sizes, t, o, SMART):
        ra = curves[(t, o)][SMART][n]
        for b in SIMPLE_BASELINES:
            base = curves[(t, o)][b][n]
            d_tau = ra[TAU] - base[TAU]
            ov_tau = (ra[TAU + "_lo"] <= base[TAU + "_hi"]) and (base[TAU + "_lo"] <= ra[TAU + "_hi"])
            entry = {
                "task": t, "objective": o, "n_T": n, "baseline": b, "reference": SMART,
                "d_tau_b": r3(d_tau),
                "d_tau_b_lo": r3(ra[TAU + "_lo"] - base[TAU + "_hi"]),
                "d_tau_b_hi": r3(ra[TAU + "_hi"] - base[TAU + "_lo"]),
                "ci_overlap_tau_b": bool(ov_tau),
            }
            any_overlap = ov_tau
            for k in K_FRACS:
                ov = (ra[rkey(k) + "_lo"] <= base[rkey(k) + "_hi"]) and (base[rkey(k) + "_lo"] <= ra[rkey(k) + "_hi"])
                entry["d_R{}".format(k)] = r3(ra[rkey(k)] - base[rkey(k)])
                entry["d_R{}_lo".format(k)] = r3(ra[rkey(k) + "_lo"] - base[rkey(k) + "_hi"])
                entry["d_R{}_hi".format(k)] = r3(ra[rkey(k) + "_hi"] - base[rkey(k) + "_lo"])
                entry["ci_overlap_R{}".format(k)] = bool(ov)
                any_overlap = any_overlap or ov
            entry["any_ci_overlap"] = bool(any_overlap)
            entry["evidence_label"] = "提示性证据（区间重叠）" if any_overlap else "区间不重叠"
            out.append(entry)
    return out


def key_nt(curves, sizes, t, o):
    """Smallest non-trivial n_T at which all four baselines have median tau_b >= 0.80."""
    valid = valid_nt(curves, sizes, t, o, SMART)
    for n in valid:
        if all(curves[(t, o)][b][n][TAU] >= TAU_THRESHOLD - TAU_EPS for b in BASELINES):
            return n
    return max(valid)


def triple_entry(curves, t, o, n, b):
    row = curves[(t, o)][b][n]
    e = {"task": t, "objective": o, "n_T": n, "baseline": b,
         "tau_b": r3(row[TAU]), "tau_b_lo": r3(row[TAU + "_lo"]),
         "tau_b_hi": r3(row[TAU + "_hi"])}
    for k in K_FRACS:
        e["O{}".format(k)] = r3(row[okey(k)])
        e["O{}_lo".format(k)] = r3(row[okey(k) + "_lo"])
        e["O{}_hi".format(k)] = r3(row[okey(k) + "_hi"])
    for k in K_FRACS:
        e["R{}".format(k)] = r3(row[rkey(k)])
        e["R{}_lo".format(k)] = r3(row[rkey(k) + "_lo"])
        e["R{}_hi".format(k)] = r3(row[rkey(k) + "_hi"])
    return e


def endpoint_check(doc, sizes):
    n_rows = 0
    bad = []
    for row in doc["curves"]:
        n_pool = sizes[(row["task"], row["objective"])]
        if int(row["n_T"]) == n_pool:
            n_rows += 1
            if abs(row[TAU] - 1.0) > 1e-9:
                bad.append([row["task"], row["objective"], row["baseline"], r3(row[TAU])])
    return {
        "statement": ("n_T = n（池大小）时排序 = 已知标签真值 + 未标注模型预测，τ_b ≡ 1 是构造性端点、"
                      "不是成绩；本报告的全部统计与表格均已排除该点。"),
        "n_endpoint_rows": n_rows,
        "all_endpoint_tau_equals_1": len(bad) == 0,
        "endpoint_violations": bad,
        "excluded_from_statistics": True,
    }


# --------------------------------------------------------------------------- #
# narrative
# --------------------------------------------------------------------------- #
SUMMARY_ZH = (
    "回溯式主动学习重放（6 池 × 4 采集 × 20 组冻结种子，排除 n_T=n 构造端点）给出 median τ_b "
    "首次 ≥0.80 所需昂贵标签数：C 池（10）两轴均 9；n=18 池 12–15（E·氧化 uncertainty 12 / "
    "random 15）。uncertainty 最省或并列；ranking_aware 未稳定更优，其与另外三者的 Δτ_b 在多数 "
    "n_T 上区间重叠，只能作提示性证据。池仅 18（C 为 10）个分子，不得外推为真实 DFT 预算。"
)


def build_payload():
    doc = load_results()
    sizes = pool_sizes(doc)
    curves = index_curves(doc)

    sha = {}
    for name, path in INPUTS:
        sha[name] = sha256_file(path)

    budget = [budget_entry(curves, sizes, t, o, b) for (t, o) in POOLS for b in BASELINES]
    compare = [e for (t, o) in POOLS for e in compare_entries(curves, sizes, t, o)]
    key = {po: key_nt(curves, sizes, *po) for po in POOLS}
    triple = [triple_entry(curves, t, o, key[(t, o)], b) for (t, o) in POOLS for b in BASELINES]
    ep = endpoint_check(doc, sizes)

    settings = doc["settings"]
    protocol = doc["protocol"]

    payload = {
        "stage": "week24_corealign/al_budget",
        "title": "Stage 8 active-learning replay distilled into a minimal expensive-label budget",
        "source_file": "outputs/week7/stage8_al_results.json",
        "source_generated_utc": doc.get("generated_utc"),
        "source_plan_reference": doc.get("plan_reference"),
        "source_stage": doc.get("stage"),
        "inputs_sha256": sha,
        "source_settings_fingerprints": settings.get("inputs_sha256", {}),
        "protocol_fields": protocol,
        "settings_used": {
            "repeats": settings.get("repeats"),
            "initial_seed_size": settings.get("initial_seed_size"),
            "batch_size": settings.get("batch_size"),
            "acquisition_features": settings.get("acquisition_features"),
            "k_fractions": settings.get("k_fractions"),
            "baselines": settings.get("baselines"),
            "al_seeds": settings.get("al_seeds"),
            "n_posterior": settings.get("n_posterior"),
        },
        "pool_sizes": {"{}:{}".format(t, o): sizes[(t, o)] for (t, o) in POOLS},
        "tau_threshold": TAU_THRESHOLD,
        "n_repeats": settings.get("repeats"),
        "quantile_interval": "2.5/97.5 percentile over repeats",
        "endpoint_self_check": ep,
        "tau80_budget": budget,
        "baseline_compare": compare,
        "decision_triple_key_n_T": triple,
        "key_n_T_by_pool": {"{}:{}".format(t, o): key[(t, o)] for (t, o) in POOLS},
        "summary_zh": SUMMARY_ZH,
        "summary_zh_length": len(SUMMARY_ZH),
        "notes": [
            "endpoint n_T = n excluded from every statistic and every table",
            "intervals are descriptive 2.5/97.5 percentiles over 20 repeats, not a formal significance test",
            "core pool is 18 molecules (C task 10); no extrapolation to a real DFT budget is permitted",
            "acquisition uses X0 descriptors only; the ranking rule is known truth plus model prediction",
        ],
    }
    return payload, doc, sizes, curves, budget, key, triple


# --------------------------------------------------------------------------- #
# renderers
# --------------------------------------------------------------------------- #
def render_json(payload):
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def render_csv(budget):
    head = ["task", "objective", "baseline", "pool_n", "last_nontrivial_n_T",
            "budget_n_T", "reached_before_endpoint",
            "kendall_tau_b", "kendall_tau_b_lo", "kendall_tau_b_hi"]
    lines = [",".join(head)]
    for e in budget:
        row = [e["task"], e["objective"], e["baseline"], str(e["pool_n"]),
               str(e["last_nontrivial_n_T"]), str(e["budget_n_T"]),
               "1" if e["reached_before_endpoint"] else "0",
               f3(e["tau_b"]), f3(e["tau_b_lo"]), f3(e["tau_b_hi"])]
        lines.append(",".join(row))
    return ("\n".join(lines) + "\n").encode("utf-8")


def md_tau_tables(curves, sizes, pool_list):
    out = []
    for (t, o) in pool_list:
        valid = valid_nt(curves, sizes, t, o, SMART)
        out.append("**{}（池 n = {}）**".format(label(t, o), sizes[(t, o)]))
        out.append("")
        out.append("| 任务 · 轴 | baseline | " + " | ".join(str(n) for n in valid) + " |")
        out.append("|---|---|" + "---|" * len(valid))
        for b in BASELINES:
            cells = [f3(curves[(t, o)][b][n][TAU]) for n in valid]
            out.append("| {} | {} | ".format(label(t, o), b) + " | ".join(cells) + " |")
        out.append("")
    return out


def md_budget_table(budget):
    out = ["| 任务 · 轴 | 池 n | random | diversity | uncertainty | ranking_aware |",
           "|---|---|---|---|---|---|"]
    idx = {(e["task"], e["objective"], e["baseline"]): e for e in budget}
    for (t, o) in POOLS:
        cells = []
        for b in BASELINES:
            e = idx[(t, o, b)]
            if not e["reached_before_endpoint"]:
                cells.append("> n")
            else:
                cells.append("{}（τ_b = {} [{}, {}]）".format(
                    e["budget_n_T"], f3(e["tau_b"]), f3(e["tau_b_lo"]), f3(e["tau_b_hi"])))
        out.append("| {} | {} | ".format(label(t, o), idx[(t, o, "random")]["pool_n"]) + " | ".join(cells) + " |")
    return out


def md_compare_table(compare, key):
    out = ["| 任务 · 轴 | 关键 n_T | 对比 baseline | Δτ_b | ΔR10% | ΔR20% | ΔR30% | τ_b 区间重叠 | R_k 有重叠 | 判读 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for (t, o) in POOLS:
        n = key[(t, o)]
        for b in SIMPLE_BASELINES:
            e = next(x for x in compare if (x["task"], x["objective"], x["n_T"], x["baseline"]) == (t, o, n, b))
            r_ov = any(e["ci_overlap_R{}".format(k)] for k in K_FRACS)
            out.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                label(t, o), n, b, f3(e["d_tau_b"]), f3(e["d_R10"]), f3(e["d_R20"]), f3(e["d_R30"]),
                "是" if e["ci_overlap_tau_b"] else "否", "是" if r_ov else "否", e["evidence_label"]))
    return out


def md_triple_table(triple):
    out = ["| 任务 · 轴 | 关键 n_T | baseline | τ_b [2.5–97.5] | O10% | O20% | O30% | R10% | R20% | R30% |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for e in triple:
        out.append("| {} | {} | {} | {} [{}, {}] | {} | {} | {} | {} | {} | {} |".format(
            label(e["task"], e["objective"]), e["n_T"], e["baseline"],
            f3(e["tau_b"]), f3(e["tau_b_lo"]), f3(e["tau_b_hi"]),
            f3(e["O10"]), f3(e["O20"]), f3(e["O30"]),
            f3(e["R10"]), f3(e["R20"]), f3(e["R30"])))
    return out


def render_md(payload, sizes, curves, budget, compare, key, triple):
    doc = load_results()
    lines = []
    lines.append("# Week 24 · Stage 8 主动学习重放：最小昂贵标签预算")
    lines.append("")
    lines.append("本文件由 scripts/analyze_w24_al.py 生成，请勿手改。内容是对既有冻结产物 "
                 "outputs/week7/stage8_al_results.json（296 行曲线、6 个 task×objective 池、4 个 baseline、20 次重复）"
                 "的只读蒸馏；脚本零新增电子结构计算，不调用 ORCA / xTB。")
    lines.append("")
    lines.append("对应核心文件 v2：§14（n_T → τ_b / O_k / R_k 三条曲线、4 baseline、§14.3 ranking-aware 二元熵）、"
                 "§23 第 11 条（high-cost-label budget vs decision accuracy）、§24 Figure 7。")
    lines.append("")
    lines.append("## 0 可直接粘进论文的中文小结")
    lines.append("")
    lines.append("> " + SUMMARY_ZH)
    lines.append("")
    lines.append("（小结 {} 字。）".format(len(SUMMARY_ZH)))
    lines.append("")
    lines.append("## 1 口径与协议")
    lines.append("")
    lines.append("- 初始种子 initial_seed_size = {}，每轮 batch_size = {}，重复 n_repeats = {}（冻结种子 {}）。".format(
        payload["settings_used"]["initial_seed_size"], payload["settings_used"]["batch_size"],
        payload["settings_used"]["repeats"], ", ".join(str(s) for s in payload["settings_used"]["al_seeds"][:3]) + ", …"))
    lines.append("- acquisition 只能用 X0 特征（acquisition_features = \"{}\"）；X2 严禁进入，否则等于先做昂贵计算再决定是否做昂贵计算。".format(
        payload["settings_used"]["acquisition_features"]))
    lines.append("- 批内 hygiene：{}；每轮标准化与 GPR 只看当轮可见标签，不偷看全量标签。".format(
        payload["protocol_fields"].get("in_loop_hygiene")))
    lines.append("- 排序规则：{}（hidden_label_replay = {}）。".format(
        payload["protocol_fields"].get("ranking_rule"), payload["protocol_fields"].get("hidden_label_replay")))
    lines.append("- 每个数字为 20 次重复的 median；区间为重复间的 2.5/97.5 百分位（非正式显著性检验）。")
    lines.append("- 「恢复排序」判据：median τ_b 首次 ≥ {:.2f}。".format(TAU_THRESHOLD))
    lines.append("")
    lines.append("输入 SHA256：")
    lines.append("")
    lines.append("| 输入文件 | SHA256 |")
    lines.append("|---|---|")
    for name, h in payload["inputs_sha256"].items():
        lines.append("| {} | {} |".format(name, h))
    lines.append("")
    lines.append("## 2 端点自检（n_T = n 不算成绩）")
    lines.append("")
    ep = payload["endpoint_self_check"]
    lines.append(ep["statement"])
    lines.append("")
    lines.append("- 端点行数 n_endpoint_rows = {}（6 池 × 4 baseline = 24）。".format(ep["n_endpoint_rows"]))
    lines.append("- 所有端点 τ_b ≡ 1 成立：{}。".format("是" if ep["all_endpoint_tau_equals_1"] else "否"))
    lines.append("- 端点已从下文所有曲线、均值、预算判据中排除。")
    lines.append("")
    lines.append("## 3 baseline × n_T → median τ_b")
    lines.append("")
    lines.append("每个数字为 20 次重复的 median。列只列非平凡点（n_T ≤ n−1），端点 n_T = n 不列。")
    lines.append("")
    lines.append("### 3.1 池 n = 18")
    lines.append("")
    lines.extend(md_tau_tables(curves, sizes, [po for po in POOLS if sizes[po] == 18]))
    lines.append("### 3.2 池 n = 10")
    lines.append("")
    lines.extend(md_tau_tables(curves, sizes, [po for po in POOLS if sizes[po] == 10]))
    lines.append("## 4 达到 τ_b ≥ 0.80 所需 n_T")
    lines.append("")
    lines.append("单元格 = 首次达到的 n_T（该点 τ_b 的 median 与 2.5/97.5 区间）。「> n」表示在非平凡区间内从未达到。")
    lines.append("")
    lines.extend(md_budget_table(budget))
    lines.append("")
    lines.append("## 5 ranking_aware 相对其它 baseline 的 Δτ_b / ΔR_k（关键 n_T）")
    lines.append("")
    lines.append("关键 n_T = 该池内四个 baseline 的 median τ_b 全部首次 ≥ 0.80 的最小 n_T。"
                 "Δ 为 ranking_aware 减该 baseline（Δτ_b > 0 或 ΔR_k < 0 才表示 ranking_aware 更好）。"
                 "「区间重叠」按 20 次重复的 2.5/97.5 区间是否相交判断；只要有一项重叠即记为提示性证据。")
    lines.append("")
    lines.extend(md_compare_table(compare, key))
    lines.append("")
    lines.append("## 6 决策量三件套：τ_b + Top-k 重叠 O_k + selection regret R_k（关键 n_T）")
    lines.append("")
    lines.append("同一 n_T 上同时给出排序（τ_b）、入选清单（O_k，k = 10/20/30%）与决策损失（R_k）三个视角。")
    lines.append("")
    lines.extend(md_triple_table(triple))
    lines.append("")
    lines.append("## 7 限制")
    lines.append("")
    lines.append("- 池只有 18（C 为 10）个分子，曲线只有 15（C 为 7）个非平凡点，20 次重复的百分位区间很粗。")
    lines.append("- 本图只能比较方法的相对行为，禁止把 n_T 换算成真实项目要买多少张 DFT。")
    lines.append("- posterior sampling 来自 GPR 后验协方差（样本数 {}），未做不确定性校准；在 18 个点上无法可信校准，"
                 "这与 stage8 摘要的诚实边界一致。".format(payload["settings_used"]["n_posterior"]))
    lines.append("- 「区间重叠即提示性证据」是保守写法；未做多重比较校正。")
    lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_png(curves, sizes, key):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.0))
    x = np.arange(len(POOLS))
    width = 0.2
    labels = [ascii_label(t, o) for (t, o) in POOLS]

    def grouped(ax, value_fn, title, ylabel):
        for i, b in enumerate(BASELINES):
            vals = [value_fn(po, b) for po in POOLS]
            ax.bar(x + (i - 1.5) * width, vals, width, label=b, color=BASELINE_COLORS[b])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=15)
        ax.grid(True, axis="y", alpha=0.3)

    def budget_val(po, b):
        e = next(x for x in budget_cache if (x["task"], x["objective"], x["baseline"]) == (po[0], po[1], b))
        return e["budget_n_T_value"] if e["reached_before_endpoint"] else e["last_nontrivial_n_T"]

    budget_cache = [budget_entry(curves, sizes, t, o, b) for (t, o) in POOLS for b in BASELINES]

    def triple_val(po, b, field):
        return curves[po][b][key[po]][field]

    grouped(axes[0][0], budget_val, "(a) n_T needed for median tau_b >= 0.80", "n_T")
    grouped(axes[0][1], lambda po, b: triple_val(po, b, TAU), "(b) median tau_b at the key n_T", "tau_b")
    grouped(axes[1][0], lambda po, b: triple_val(po, b, okey(20)), "(c) Top-20% overlap O20 at the key n_T", "O20%")
    grouped(axes[1][1], lambda po, b: triple_val(po, b, rkey(20)), "(d) selection regret R20 at the key n_T", "R20% (eV)")

    axes[0][1].axhline(TAU_THRESHOLD, color="crimson", ls="--", lw=1.0)
    handles, lbls = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, lbls, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("F49  Stage 8 AL replay: expensive-label budget and the decision triple", y=0.98)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, metadata={"Software": "analyze_w24_al.py"})
    plt.close(fig)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def build_outputs():
    payload, doc, sizes, curves, budget, key, triple = build_payload()
    compare = payload["baseline_compare"]
    outputs = {}
    outputs[OUT_JSON] = render_json(payload)
    outputs[OUT_CSV] = render_csv(budget)
    outputs[OUT_MD] = render_md(payload, sizes, curves, budget, compare, key, triple)
    outputs[OUT_FIG] = render_png(curves, sizes, key)
    return outputs, payload, sizes, curves, budget, key, triple


def write_outputs(outputs):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for path, data in outputs.items():
        path.write_bytes(data)


def check_outputs(outputs, payload):
    ok = True
    # 1. verify the recorded input fingerprints still match
    for name, path in INPUTS:
        want = payload["inputs_sha256"][name]
        got = sha256_file(path)
        status = "OK" if want == got else "MISMATCH"
        if want != got:
            ok = False
        print("[check] input {:<38} {}".format(name, status))
    # 2. verify byte-for-byte identical regenerated outputs
    for path, data in outputs.items():
        if not path.exists():
            print("[check] output {:<38} MISSING".format(path.name))
            ok = False
            continue
        got = path.read_bytes()
        same = got == data
        if not same:
            ok = False
        print("[check] output {:<37} {}".format(path.name, "OK" if same else "DIFF ({} vs {} bytes)".format(len(data), len(got))))
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description="Distil Stage 8 AL replay into a minimal expensive-label budget.")
    parser.add_argument("--check", action="store_true",
                        help="recompute in memory and verify on-disk outputs byte for byte (no writing)")
    args = parser.parse_args(argv)

    outputs, payload, sizes, curves, budget, key, triple = build_outputs()

    if args.check:
        ok = check_outputs(outputs, payload)
        print("[check] summary_zh length = {} chars".format(len(SUMMARY_ZH)))
        print("[check] RESULT {}".format("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    write_outputs(outputs)
    print("wrote:")
    for path in outputs:
        print("  " + str(path))
    print("tau_b >= {} budget:".format(TAU_THRESHOLD))
    for e in budget:
        star = e["budget_n_T"]
        print("  {:<4} {:<9} {:<14} -> n_T* = {:>4}".format(e["task"], e["objective"], e["baseline"], str(star)))
    print("summary_zh length = {} chars".format(len(SUMMARY_ZH)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
