"""R3: the sigma identities are algebra, so their value is out-of-sample, not fit quality.

Why this module exists
----------------------
``docs/20`` (Stage 11) proved a family of *identities*: ``sigma_ij`` is exactly
``|delta_i - delta_j| / sqrt(2)``, its pairwise RMS is exactly the shift's sample
standard deviation, and the whole resolved/unresolved machine collapses to one
dimensionless criterion ``q_ij <= sqrt(2) / z``.  An identity has zero fitting
error *by construction*, so "the observed value reproduced the closed form to
0.00e+00" is not evidence of anything.  ``docs/31`` R3 asks for the two things
that are evidence:

1. say "identity" everywhere instead of implying predictive accuracy, and
2. run one **falsifiable** test: freeze a prediction, then score it.

The prediction frozen here is the Week 10 rule of ``docs/20`` section 7 --
"a rung rewrites the shortlist if, and only if, the (signed) OLS slope of the
shift on the target layer is low" -- applied to molecule sets that were **not**
part of the ten points the rule was calibrated on:

* ``all_non_discovery``: the 8 core-set molecules outside the Stage 10 common
  subset (DEC, EA, EMC, FEC, MA, PC, TEGDME, VC); n = 8, so the top-20 %
  shortlist is a genuine two-slot test (k = 2).
* ``stage16_holdout``: the six molecules ``docs/31`` names as the Stage 16
  holdout (DEC, EA, FEC, MA, TEGDME, VC); n = 6, so k = 1.

The naive alternative -- "large shift dispersion wrecks the ranking" -- is frozen
and scored on exactly the same sets, so the comparison is paired.

Honest boundary (stated again in the report): the underlying energies already
existed in the repository when this ran, so this is an **out-of-sample holdout**,
not a blind prospective trial.  What is genuinely time-ordered is the *rule*: it
was frozen in Week 10 (``docs/20`` section 7), the Stage 16 holdout was
designated in Week 13, and neither was ever used to pick the threshold.  The
prediction file is written and hashed *before* any outcome is computed.

Outputs
-------
outputs/week21/sigma_prospective_frozen.json   the prediction, timestamp, digest
outputs/week21/sigma_prospective.json          the scoring, hits, misses
outputs/week21/sigma_prospective.md            human-readable summary
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking  # noqa: E402

TOP_K_FRACTION = 0.20
DISCOVERY_ROWS = REPO_ROOT / "outputs" / "week10" / "stage11_sigma_anatomy.json"
DERIVED_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week21"

#: The Stage 10 common subset -- the ten points every Week 9/10 number is built on.
DISCOVERY_MOLECULES = ("AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP")
#: Named by docs/31 R3 as the Stage 16 holdout.
STAGE16_HOLDOUT = ("DEC", "EA", "FEC", "MA", "TEGDME", "VC")

ENERGY_KEYS = {
    "oxidation": ("p0_ox_ev", "p1_ox_ev"),
    "reduction": ("p0_red_ev", "p1_red_ev"),
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R3 out-of-sample test of the Week 10 shortlist rule.")
    parser.add_argument("--discovery", type=Path, default=DISCOVERY_ROWS)
    parser.add_argument("--derived", type=Path, default=DERIVED_CSV)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--refreeze", action="store_true",
                        help="replace an existing frozen prediction on purpose "
                             "(default: reuse it, so freeze-then-score stays honest)")
    return parser.parse_args(argv)


def _float(value):
    text = ("" if value is None else str(value)).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_derived(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[row["name"]] = row
    return out


def loo_threshold(values, labels, *, low_is_positive: bool) -> float:
    """Threshold that best separates the discovery points (balanced accuracy).

    Only the ten discovery points are ever passed in.  Candidate thresholds are
    the midpoints between adjacent sorted predictor values; ties in balanced
    accuracy are broken by the smallest absolute threshold, so the rule is
    deterministic and does not depend on the input order.
    """

    order = sorted(zip(values, labels), key=lambda item: item[0])
    xs = [item[0] for item in order]
    candidates = [xs[0] - 1.0]
    for a, b in zip(xs, xs[1:]):
        candidates.append(0.5 * (a + b))
    candidates.append(xs[-1] + 1.0)

    best = None
    for threshold in candidates:
        correct = 0.0
        for value, label in zip(values, labels):
            predicted = (value <= threshold) if low_is_positive else (value >= threshold)
            positive = bool(label)
            # balanced accuracy: average of sensitivity and specificity
            correct += 1.0 if predicted == positive else 0.0
        positives = sum(1 for label in labels if label)
        negatives = len(labels) - positives
        recall_pos = sum(
            1.0
            for value, label in zip(values, labels)
            if label and (((value <= threshold) if low_is_positive else (value >= threshold)))
        ) / positives
        recall_neg = sum(
            1.0
            for value, label in zip(values, labels)
            if (not label) and not (((value <= threshold) if low_is_positive else (value >= threshold)))
        ) / negatives
        score = 0.5 * (recall_pos + recall_neg)
        key = (score, -abs(threshold))
        if best is None or key > best[0]:
            best = (key, threshold)
    return float(best[1])


def ols_slope(x, y) -> float:
    """Slope of ``y = a + b x`` (the Stage 11 ``ols_slope_b``)."""

    xs = np.asarray(x, dtype=float)
    ys = np.asarray(y, dtype=float)
    return float(np.polyfit(xs, ys, 1)[0])


def k_for(n: int, fraction: float = TOP_K_FRACTION) -> int:
    return max(1, int(round(fraction * n)))


def observed_outcome(rows, names, axis) -> dict:
    """The number the prediction is about: is the top-20 % shortlist rewritten?"""

    p0_key, p1_key = ENERGY_KEYS[axis]
    p0 = [_float(rows[name][p0_key]) for name in names]
    p1 = [_float(rows[name][p1_key]) for name in names]
    k = k_for(len(names))
    overlap = ranking.top_k_overlap(p0, p1, k, higher_is_better=True)
    return {
        "n": len(names),
        "k": k,
        "tau_b_vs_cheap_layer": ranking.kendall_tau_b(p1, p0),
        "overlap": overlap,
        "shortlist_rewritten": bool(overlap < 1.0),
        "p0_values_ev": p0,
        "p1_values_ev": p1,
        "names": list(names),
    }


def sha256_of(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_prediction(discovery, derived) -> dict:
    values_b = [row["ols_slope_b"] for row in discovery]
    values_sigma = [row["sigma_rms_ev"] for row in discovery]
    labels = [bool(row["shortlist_rewritten"]) for row in discovery]
    threshold_b = loo_threshold(values_b, labels, low_is_positive=True)
    threshold_sigma = loo_threshold(values_sigma, labels, low_is_positive=False)

    sets = {
        "all_non_discovery": [name for name in derived if name not in set(DISCOVERY_MOLECULES)],
        "stage16_holdout": [name for name in STAGE16_HOLDOUT],
    }
    predictions = []
    for label, names in sets.items():
        names = sorted(names)
        for axis in ("oxidation", "reduction"):
            p0_key, p1_key = ENERGY_KEYS[axis]
            p0 = [_float(derived[name][p0_key]) for name in names]
            p1 = [_float(derived[name][p1_key]) for name in names]
            delta = [b - a for a, b in zip(p0, p1)]
            predictor_b = ols_slope(p1, delta)
            predictor_sigma = statistics.stdev(delta) if len(delta) > 1 else 0.0
            predictions.append({
                "set": label,
                "axis": axis,
                "n": len(names),
                "k": k_for(len(names)),
                "molecules": names,
                "delta_mean_ev": statistics.fmean(delta),
                "delta_sd_ev": predictor_sigma,
                "ols_slope_b": predictor_b,
                "rule_signed_says_rewritten": bool(predictor_b <= threshold_b),
                "rule_naive_says_rewritten": bool(predictor_sigma >= threshold_sigma),
                "claim": (
                    "the top-20%% shortlist (k=%d of %d) for %s / %s is %s"
                    % (
                        k_for(len(names)), len(names), label, axis,
                        "REWRITTEN" if predictor_b <= threshold_b else "PRESERVED",
                    )
                ),
            })
    return {
        "frozen_rule": {
            "source": "docs/20_week10_report.md section 7 (Week 10, Stage 11)",
            "signed_rule": {
                "predictor": "ols_slope_b (OLS slope of delta on the target layer P1)",
                "direction": "low is dangerous",
                "threshold": threshold_b,
                "fitted_on": "the 10 Stage 10 common-subset (rung, axis) points",
            },
            "naive_rule": {
                "predictor": "sigma_rms_ev = sd(delta) (the Week 9 H_var quantity, no sign)",
                "direction": "high is dangerous",
                "threshold": threshold_sigma,
                "fitted_on": "the 10 Stage 10 common-subset (rung, axis) points",
            },
            "discovery_points": [
                {
                    "rung": row["rung"], "axis": row["axis"],
                    "ols_slope_b": row["ols_slope_b"],
                    "sigma_rms_ev": row["sigma_rms_ev"],
                    "shortlist_rewritten": bool(row["shortlist_rewritten"]),
                }
                for row in discovery
            ],
        },
        "predictions": predictions,
        "frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "discipline": (
            "This file is written and digested before any holdout outcome is computed. "
            "The rule and its threshold come from the ten Stage 10 discovery points only; "
            "the holdout molecules were never used to pick them."
        ),
    }


def score(prediction, derived) -> dict:
    rows = []
    for item in prediction["predictions"]:
        truth = observed_outcome(derived, item["molecules"], item["axis"])
        rows.append({
            **{key: item[key] for key in ("set", "axis", "n", "k", "molecules",
                                          "delta_sd_ev", "ols_slope_b")},
            "predicted_signed": item["rule_signed_says_rewritten"],
            "predicted_naive": item["rule_naive_says_rewritten"],
            "observed_rewritten": truth["shortlist_rewritten"],
            "observed_overlap": truth["overlap"],
            "tau_b_vs_cheap_layer": truth["tau_b_vs_cheap_layer"],
            "signed_hit": bool(item["rule_signed_says_rewritten"] == truth["shortlist_rewritten"]),
            "naive_hit": bool(item["rule_naive_says_rewritten"] == truth["shortlist_rewritten"]),
        })
    n = len(rows)
    signed = sum(1 for row in rows if row["signed_hit"])
    naive = sum(1 for row in rows if row["naive_hit"])
    misses = [row for row in rows if not row["signed_hit"] or not row["naive_hit"]]
    return {
        "n_predictions": n,
        "signed_rule_hits": signed,
        "signed_rule_accuracy": signed / n if n else None,
        "naive_rule_hits": naive,
        "naive_rule_accuracy": naive / n if n else None,
        "n_observed_rewrites": sum(1 for row in rows if row["observed_rewritten"]),
        "rows": rows,
        "misses": [
            {
                "set": row["set"], "axis": row["axis"],
                "signed_hit": row["signed_hit"], "naive_hit": row["naive_hit"],
                "predicted_signed": row["predicted_signed"],
                "predicted_naive": row["predicted_naive"],
                "observed_rewritten": row["observed_rewritten"],
                "observed_overlap": row["observed_overlap"],
            }
            for row in misses
        ],
    }


def render_markdown(prediction, scoring, frozen_digest) -> str:
    lines = [
        "# R3 — Week 10 规则的样本外检验（前瞻检验）",
        "",
        "规则在 Week 10（`docs/20` §7）冻结，分子集在 Week 13（Stage 16）指定，",
        "两者都没有参与本文件的阈值选择。预测文件在**任何**结果被计算之前写出并取摘要。",
        "",
        "- 预测文件：`outputs/week21/sigma_prospective_frozen.json`",
        "- 预测摘要 SHA256：`%s`" % frozen_digest,
        "- 冻结时刻（UTC）：`%s`" % prediction["frozen_utc"],
        "",
        "## 冻结的规则",
        "",
        "| 规则 | 预测子 | 危险方向 | 阈值（在 10 个发现点上拟合） |",
        "| --- | --- | --- | --- |",
        "| 带符号（Week 10 §7） | `ols_slope_b` | 低 = 危险 | %.4f |"
        % prediction["frozen_rule"]["signed_rule"]["threshold"],
        "| 朴素（Week 9 H_var） | `sd(delta)` | 高 = 危险 | %.4f eV |"
        % prediction["frozen_rule"]["naive_rule"]["threshold"],
        "",
        "## 打分",
        "",
        "| 分子集 | 轴 | n | k | sd(delta) /eV | ols_slope_b | 带符号预测 | 朴素预测 | 实测 | 重叠 | 带符号命中 | 朴素命中 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in scoring["rows"]:
        lines.append(
            "| %s | %s | %d | %d | %.3f | %+.3f | %s | %s | %s | %.2f | %s | %s |"
            % (
                row["set"], row["axis"], row["n"], row["k"], row["delta_sd_ev"], row["ols_slope_b"],
                "改写" if row["predicted_signed"] else "保留",
                "改写" if row["predicted_naive"] else "保留",
                "改写" if row["observed_rewritten"] else "保留",
                row["observed_overlap"],
                "OK" if row["signed_hit"] else "MISS",
                "OK" if row["naive_hit"] else "MISS",
            )
        )
    lines += [
        "",
        "**命中率**：带符号规则 %d/%d = %.3f；朴素规则 %d/%d = %.3f。"
        % (
            scoring["signed_rule_hits"], scoring["n_predictions"], scoring["signed_rule_accuracy"],
            scoring["naive_rule_hits"], scoring["n_predictions"], scoring["naive_rule_accuracy"],
        ),
        "",
    ]
    if scoring["misses"]:
        lines.append("**落空清单（必须保留在报告里）**：")
        lines.append("")
        for miss in scoring["misses"]:
            lines.append(
                "- %s / %s：带符号 %s、朴素 %s，实测 %s（重叠 %.2f）"
                % (
                    miss["set"], miss["axis"],
                    "命中" if miss["signed_hit"] else "**落空**",
                    "命中" if miss["naive_hit"] else "**落空**",
                    "改写" if miss["observed_rewritten"] else "保留",
                    miss["observed_overlap"],
                )
            )
        lines.append("")
    lines += [
        "## 诚实边界",
        "",
        "这些分子的能量在仓库里已经存在，所以这是**样本外留出检验**，不是盲前瞻试验。",
        "真正按时间排序的是**规则**：它在 Week 10 冻结、阈值从未被留出分子影响；",
        "预测文件先落盘再打分，可用上面的 SHA256 复核。",
        "边界与 `docs/20` §7.3 第 4 条一致：留一阈值不是外部验证，本文件才是。",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    args = parse_args(argv)
    discovery_doc = json.loads(args.discovery.read_text(encoding="utf-8"))
    discovery = discovery_doc["rows"]
    derived = load_derived(args.derived)

    args.outdir.mkdir(parents=True, exist_ok=True)
    prediction = build_prediction(discovery, derived)
    digest = sha256_of(prediction)
    frozen_path = args.outdir / "sigma_prospective_frozen.json"
    reused = False
    if frozen_path.exists() and not args.refreeze:
        existing = json.loads(frozen_path.read_text(encoding="utf-8"))
        stored = existing.pop("frozen_sha256", None)
        same_rule = existing.get("frozen_rule") == prediction.get("frozen_rule")
        same_predictions = existing.get("predictions") == prediction.get("predictions")
        if not (same_rule and same_predictions):
            raise SystemExit(
                "sigma_prospective_frozen.json no longer matches a fresh build "
                "(rule=%s predictions=%s); pass --refreeze to replace it on purpose"
                % (same_rule, same_predictions))
        if sha256_of(existing) != stored:
            raise SystemExit(
                "sigma_prospective_frozen.json fails its own digest check; "
                "pass --refreeze to replace it on purpose")
        prediction, digest, reused = existing, stored, True
    if not reused:
        frozen_path.write_text(
            json.dumps({**prediction, "frozen_sha256": digest}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n",
        )

    scoring = score(prediction, derived)
    result = {
        "stage": "R3-prospective-test",
        "frozen_file": frozen_path.relative_to(REPO_ROOT).as_posix(),
        "frozen_sha256": digest,
        "scoring": scoring,
        "sources": [
            args.discovery.relative_to(REPO_ROOT).as_posix(),
            args.derived.relative_to(REPO_ROOT).as_posix(),
        ],
    }
    (args.outdir / "sigma_prospective.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    report = args.outdir / "sigma_prospective.md"
    report.write_text(render_markdown(prediction, scoring, digest), encoding="utf-8", newline="\n")

    print(json.dumps({
        "signed_rule": {"hits": scoring["signed_rule_hits"], "n": scoring["n_predictions"],
                        "accuracy": scoring["signed_rule_accuracy"]},
        "naive_rule": {"hits": scoring["naive_rule_hits"], "n": scoring["n_predictions"],
                       "accuracy": scoring["naive_rule_accuracy"]},
        "frozen_sha256": digest,
        "frozen_reused": reused,
        "report": report.relative_to(REPO_ROOT).as_posix(),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
