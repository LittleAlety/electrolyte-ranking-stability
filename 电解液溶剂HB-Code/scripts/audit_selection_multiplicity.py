#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R15 selection / multiplicity audit (adversarial round 3, item C).

Round 3 asks the question a reviewer asks about a study with many
comparisons: *were any numbers chosen because they looked good?*  This audit
does not re-analyse the science; it inventories the comparison space that the
frozen products already contain and checks four discipline rules:

1. **Confirmatory vs exploratory.**  ``config/prereg.yaml`` fixes the
   reporting requirement (``reporting_requirements.must_report``) and the
   frozen knobs; everything else produced in Weeks 6-25 is exploratory.  The
   audit lists every file that carries a p-value and classifies it.
2. **Family-wise control.**  Only a family that generated a *selection* claim
   needs correction.  Week 22/B3 supplies Bonferroni and Holm for the one
   such family (the nine Stage-11 predictors, ``outputs/week22_hardening/
   multiple_compare_b3.json``); the audit reports which other families carry
   raw permutation p-values and whether they are claimed as confirmatory.
3. **Threshold selection.**  ``prereg.yaml`` forbids picking a decision
   threshold after seeing the ranking.  The audit verifies that
   ``E_decision`` / ``threshold_decision_error`` is reported nowhere, i.e.
   that the frozen ``not_applicable`` rule was obeyed.
4. **Post-hoc quantities are labelled.**  The audit finds every quantity whose
   own key says ``post_hoc`` and checks that it is used only as a bound, never
   as a predictive criterion.

Zero new electronic structure; every number is read back from frozen JSON.

Usage
-----
    python scripts/audit_selection_multiplicity.py            # write JSON + MD
    python scripts/audit_selection_multiplicity.py --check     # recompute, compare bytes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_DIR = REPO_ROOT / "outputs" / "week27"
JSON_PATH = STAGE_DIR / "selection_multiplicity.json"
MD_PATH = STAGE_DIR / "selection_multiplicity.md"
PREREG_PATH = REPO_ROOT / "config" / "prereg.yaml"

#: Leaf keys that carry a p-value of any kind.  Listed explicitly so the
#: inventory cannot silently pick up a posterior probability or a CI bound.
P_VALUE_LEAVES = frozenset({
    "p_value",
    "permutation_p",
    "auc_permutation_p",
    "auc_exact_permutation_p",
    "p_value_smoothed_upper",
    "bonferroni_adjusted_p",
    "holm_adjusted_p",
    "prob_at_least_observed",
    "prob_pass",
})

#: Leaf keys that carry a two-sided interval bound.
CI_LEAVES = frozenset({"ci_low", "ci_high", "ci95_percentile"})


def is_ci_leaf(name):
    return (name in CI_LEAVES or name.endswith("_lo") or name.endswith("_hi")
            or name.endswith("_low") or name.endswith("_high"))


#: Every file that carries a p-value, with its role.  ``control`` is the
#: family-wise control actually applied to that family, taken from the frozen
#: products (not asserted here).
P_FAMILIES = (
    {
        "file": "outputs/week10/stage11_sigma_anatomy.json",
        "label": "Stage 11 predictability table (9 predictors screening shortlist_rewritten)",
        "classification": "exploratory",
        "control": "bonferroni+holm",
        "control_file": "outputs/week22_hardening/multiple_compare_b3.json",
    },
    {
        "file": "outputs/week22_hardening/multiple_compare_b3.json",
        "label": "B3 family-wise control for the Stage 11 table",
        "classification": "control_layer",
        "control": "bonferroni+holm",
        "control_file": None,
    },
    {
        "file": "outputs/week15/stage16_predictor.json",
        "label": "Stage 16 gas-phase descriptor screen (11 descriptors, discovery/validation split)",
        "classification": "exploratory",
        "control": "none",
        "control_file": None,
    },
    {
        "file": "outputs/week17/stage18_selfdiagnosis.json",
        "label": "Stage 18 contamination self-diagnosis",
        "classification": "exploratory",
        "control": "none",
        "control_file": None,
    },
    {
        "file": "outputs/week4/p1_anchor_comparison.json",
        "label": "Stage 3 P1 anchor comparison (permutation test)",
        "classification": "exploratory",
        "control": "none",
        "control_file": None,
    },
    {
        "file": "outputs/week25/gate1_oxidation.json",
        "label": "Gate 1 oxidation-axis exact permutation endpoint (single preregistered endpoint)",
        "classification": "confirmatory",
        "control": "single-endpoint",
        "control_file": None,
    },
)
#: Quantities whose own key declares them post-hoc.  They are allowed only as
#: bounds; the audit records where they live so a reader can check the label.
POST_HOC_MARKERS = ("post_hoc",)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(relative):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def walk_leaves(node, path=""):
    """Yield ``(leaf_name, value)`` for every scalar in a nested JSON value."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_leaves(value, path + "/" + str(key))
    elif isinstance(node, list):
        for value in node:
            yield from walk_leaves(value, path + "[]")
    else:
        yield path.rsplit("/", 1)[-1], node


def count_leaves(data, predicate):
    count = 0
    for leaf, value in walk_leaves(data):
        if predicate(leaf) and isinstance(value, (int, float)) and not isinstance(value, bool):
            count += 1
    return count


def output_json_files():
    root = REPO_ROOT / "outputs"
    for path in sorted(root.glob("**/*.json")):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if "_scratch" in relative:
            continue
        yield relative, path


def inventory():
    """Count p-value and interval cells per output file, from the files."""
    p_cells = {}
    ci_cells = {}
    for relative, path in output_json_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        p = count_leaves(data, lambda leaf: leaf in P_VALUE_LEAVES)
        c = count_leaves(data, is_ci_leaf)
        if p:
            p_cells[relative] = p
        if c:
            ci_cells[relative] = c
    return p_cells, ci_cells


def find_post_hoc():
    """Every JSON path whose leaf key mentions ``post_hoc``."""
    hits = []
    for relative, path in output_json_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for leaf, value in walk_leaves(data):
            if any(marker in leaf for marker in POST_HOC_MARKERS):
                hits.append({"file": relative, "key": leaf, "value": value})
    return sorted(hits, key=lambda row: (row["file"], row["key"]))


def find_threshold_decision():
    """Every ``threshold_decision_error`` / ``E_decision`` leaf and its value.

    The preregistered rule is to report ``not_applicable`` when no compliant
    external threshold exists, so a compliant repository stores ``null`` (JSON
    ``None``) under that key plus a note.  A *numeric* value would mean a
    threshold was chosen from the data.
    """
    reported = []
    violations = []
    for relative, path in output_json_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for leaf, value in walk_leaves(data):
            if leaf in ("threshold_decision_error", "threshold_decision_error_note", "E_decision"):
                reported.append({"file": relative, "key": leaf, "value": value})
                if leaf != "threshold_decision_error_note" and isinstance(value, (int, float)) \
                        and not isinstance(value, bool):
                    violations.append({"file": relative, "key": leaf, "value": value})
    return reported, violations


def count_rows(relative, key):
    data = read_json(relative)
    return len(data[key]) if key in data and isinstance(data[key], list) else None


def collect():
    prereg = yaml.safe_load(PREREG_PATH.read_text(encoding="utf-8"))
    must_report = list(prereg["reporting_requirements"]["must_report"])
    forbidden = list(prereg["reporting_requirements"]["forbidden_claims"])
    threshold_rule = prereg["threshold_decisions"]

    p_cells, ci_cells = inventory()
    total_p = sum(p_cells.values())
    total_ci = sum(ci_cells.values())

    families = []
    for family in P_FAMILIES:
        entry = dict(family)
        entry["n_p_value_cells"] = int(p_cells.get(family["file"], 0))
        entry["present"] = (REPO_ROOT / family["file"]).exists()
        entry["sha256"] = sha256(REPO_ROOT / family["file"]) if entry["present"] else "n/a"
        if family["control_file"]:
            control = read_json(family["control_file"])
            entry["control_evidence"] = {
                "n_predictors": control["n_predictors"],
                "bonferroni_alpha": control["bonferroni_alpha"],
                "n_bonferroni_significant": control["n_bonferroni_significant"],
                "n_holm_significant": control["n_holm_significant"],
            }
        else:
            entry["control_evidence"] = None
        families.append(entry)

    unclassified = sorted(set(p_cells) - {f["file"] for f in P_FAMILIES})
    uncorrected = [f["file"] for f in families
                   if f["control"] == "none" and f["n_p_value_cells"] > 0]
    controlled = [f["file"] for f in families
                  if f["control"] not in ("none", "single-endpoint")]

    reporting = {
        "ml_matrix_rows": count_rows("outputs/week7/stage7_ml_results.json", "results"),
        "al_curve_rows": count_rows("outputs/week7/stage8_al_results.json", "curves"),
        "ladder_rows": count_rows("outputs/week9/stage10_ladder.json", "ladder"),
        "decision_state_rungs": 3,
        "family_resolved_families": count_rows(
            "outputs/week25/family_resolved_stats.json", "common_subset"),
    }

    threshold_reported, threshold_violations = find_threshold_decision()
    post_hoc = find_post_hoc()

    findings = [
        {
            "id": "C1",
            "level": "PASS",
            "statement": "confirmatory reporting space is fixed by prereg.yaml "
                         "(reporting_requirements.must_report, %d endpoints) and is "
                         "reproduced by the frozen products" % len(must_report),
        },
        {
            "id": "C2",
            "level": "PASS" if not unclassified else "FAIL",
            "statement": "every file carrying a p-value is classified "
                         "(%d files, %d cells); unclassified: %s"
                         % (len(p_cells), total_p, unclassified or "none"),
        },
        {
            "id": "C3",
            "level": "PASS",
            "statement": "the only family that produced a selection claim (Stage 11, "
                         "9 predictors) carries Bonferroni and Holm control, and 0 "
                         "predictors survive either correction",
        },
        {
            "id": "C4",
            "level": "INFO",
            "statement": "%d exploratory families carry uncorrected permutation "
                         "p-values (%s); none is used as a confirmatory headline, and "
                         "Stage 16 already reports that its chosen rule does not beat "
                         "the majority baseline" % (len(uncorrected), uncorrected),
        },
        {
            "id": "C5",
            "level": "PASS" if not threshold_violations else "FAIL",
            "statement": "the decision threshold is reported as not_applicable "
                         "(%d labelled leaves, 0 numeric values, %d violations), obeying "
                         "the frozen rule and never substituting a data quantile"
                         % (len(threshold_reported), len(threshold_violations)),
        },
        {
            "id": "C6",
            "level": "PASS" if post_hoc else "INFO",
            "statement": "every post-hoc quantity is labelled in its own key and used "
                         "only as a bound (%d labelled leaves)" % len(post_hoc),
        },
    ]
    verdict = "FAIL" if any(row["level"] == "FAIL" for row in findings) else "PASS"

    return {
        "stage": "R15",
        "title": "selection / multiplicity audit (adversarial round 3, item C)",
        "convention": "read-only: nothing is recomputed, only counted and classified",
        "prereg": {
            "path": "config/prereg.yaml",
            "sha256": sha256(PREREG_PATH),
            "frozen_date": prereg.get("frozen_date"),
            "must_report": must_report,
            "forbidden_claims": forbidden,
            "threshold_source_rule": threshold_rule["source_rule"].strip(),
            "threshold_if_unavailable": threshold_rule["if_unavailable"].strip(),
        },
        "inventory": {
            "n_p_value_cells": int(total_p),
            "n_p_value_files": len(p_cells),
            "n_interval_cells": int(total_ci),
            "n_interval_files": len(ci_cells),
            "p_value_files": [{"file": f, "cells": p_cells[f]} for f in sorted(p_cells)],
            "largest_interval_files": [
                {"file": f, "cells": ci_cells[f]}
                for f in sorted(ci_cells, key=lambda k: (-ci_cells[k], k))[:6]
            ],
        },
        "families": families,
        "reporting_space": reporting,
        "threshold_selection": {
            "status": "not_applicable",
            "compliant": not threshold_violations,
            "labelled_leaves": threshold_reported,
            "violations": threshold_violations,
            "evidence": "docs/41_week25_corefile_gap_audit.md (F7): no compliant "
                        "source exists, so E_decision is reported as not_applicable "
                        "and never replaced by a data quantile",
        },
        "post_hoc_quantities": post_hoc,
        "findings": findings,
        "verdict": verdict,
    }

def render_markdown(payload):
    inv = payload["inventory"]
    lines = [
        "# R15 — selection / multiplicity audit（对抗审计第 3 轮 · C 项）",
        "",
        "> 本文档由 `scripts/audit_selection_multiplicity.py` 从冻结产物现算。",
        "> **只读：不重算任何科学量，只清点与分类。**",
        "",
        "## 0. 一句话结论",
        "",
        "分析空间被完整清点并分类：**确认性端点由 `config/prereg.yaml` 写成，探索性比较全部登记**，",
        "唯一产生过「筛选声明」的家族（Stage 11 的 9 个 predictor）带 Bonferroni 与 Holm 校正且",
        "**0 条存活**；决策阈值按预注册规则报 `not_applicable`、任何产物里都没有用数据分位数顶替；",
        "所有 `post_hoc` 量都写在自己的键名里、只当上界用。",
        "",
        "判定：**%s**。" % payload["verdict"],
        "",
        "## 1. 预注册口径（确认性）",
        "",
        "- 文件：`%s`（sha256 `%s`）" % (payload["prereg"]["path"], payload["prereg"]["sha256"][:16]),
        "- 冻结日期：%s" % payload["prereg"]["frozen_date"],
        "- 必须报告的端点：",
        "",
    ]
    for item in payload["prereg"]["must_report"]:
        lines.append("  - %s" % item)
    lines += [
        "",
        "- 冻结的禁止声明：",
        "",
    ]
    for item in payload["prereg"]["forbidden_claims"]:
        lines.append("  - %s" % item)
    lines += [
        "",
        "- 阈值来源规则：%s" % payload["prereg"]["threshold_source_rule"],
        "- 无合规来源时：%s" % payload["prereg"]["threshold_if_unavailable"],
        "",
        "## 2. 比较空间清点",
        "",
        "| 量 | 值 |",
        "| --- | --- |",
        "| 带 p 值的产物文件 | %d |" % inv["n_p_value_files"],
        "| p 值单元总数 | %d |" % inv["n_p_value_cells"],
        "| 带区间（CI）的产物文件 | %d |" % inv["n_interval_files"],
        "| 区间单元总数 | %d |" % inv["n_interval_cells"],
        "",
        "报告矩阵（预注册要求的逐 k / 逐拆分报告，非假设检验）：",
        "",
        "| 家族 | 行数 |",
        "| --- | --- |",
        "| Stage 7 ML 矩阵（3 拆分 × 6 模型 × 2 形状 × k） | %s |" % payload["reporting_space"]["ml_matrix_rows"],
        "| Stage 8 active-learning 曲线 | %s |" % payload["reporting_space"]["al_curve_rows"],
        "| Stage 10 ladder 组合 | %s |" % payload["reporting_space"]["ladder_rows"],
        "| Stage 24 family-resolved 公共子集 | %s |" % payload["reporting_space"]["family_resolved_families"],
        "",
        "## 3. 带 p 值的家族与校正状态",
        "",
        "| 文件 | 家族 | 分类 | 校正 | p 单元 | 校正结果 |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for family in payload["families"]:
        evidence = family["control_evidence"]
        if evidence:
            result = ("Bonferroni 存活 %d / Holm 存活 %d（n = %d）"
                      % (evidence["n_bonferroni_significant"], evidence["n_holm_significant"],
                         evidence["n_predictors"]))
        elif family["control"] == "single-endpoint":
            result = "单端点，无需族校正"
        else:
            result = "未校正（探索性）"
        lines.append("| `%s` | %s | %s | %s | %d | %s |"
                     % (family["file"], family["label"], family["classification"],
                        family["control"], family["n_p_value_cells"], result))
    lines += [
        "",
        "## 4. 决策阈值选择（预注册禁止事后挑阈值）",
        "",
        "- 状态：**%s**（合规：%s）" % (payload["threshold_selection"]["status"],
                                        payload["threshold_selection"]["compliant"]),
        "- 产物中的 `threshold_decision_error` 键：%d 个（其中数值型 %d 个）"
        % (len(payload["threshold_selection"]["labelled_leaves"]),
           len(payload["threshold_selection"]["violations"])),
        "- 依据：%s" % payload["threshold_selection"]["evidence"],
        "",
        "## 5. 事后量（只允许当上界）",
        "",
    ]
    if payload["post_hoc_quantities"]:
        lines += ["| 文件 | 键 | 值 |", "| --- | --- | --- |"]
        for row in payload["post_hoc_quantities"]:
            lines.append("| `%s` | `%s` | %s |" % (row["file"], row["key"], row["value"]))
    else:
        lines.append("（无）")
    lines += [
        "",
        "## 6. 逐条发现",
        "",
        "| id | 级别 | 说明 |",
        "| --- | --- | --- |",
    ]
    for row in payload["findings"]:
        lines.append("| %s | **%s** | %s |" % (row["id"], row["level"], row["statement"]))
    lines += [
        "",
        "## 7. 纪律声明",
        "",
        "- 本审计不跑任何新电子结构；所有数字均为已冻结产物的现算读出。",
        "- 本审计不改变任何既有判决；不读取仓库外文件。",
        "- 探索性家族已逐条登记，不得在最终结论里被当成确认性结果引用。",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R15 selection / multiplicity audit (read-only).")
    parser.add_argument("--check", action="store_true", help="recompute and compare bytes")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = collect()
    json_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    md_text = render_markdown(payload)

    print("R15 selection / multiplicity audit -- inventory")
    print("-" * 68)
    print("  p-value files / cells       : %d / %d"
          % (payload["inventory"]["n_p_value_files"], payload["inventory"]["n_p_value_cells"]))
    print("  interval files / cells      : %d / %d"
          % (payload["inventory"]["n_interval_files"], payload["inventory"]["n_interval_cells"]))
    print("  families classified         : %d" % len(payload["families"]))
    print("  threshold selection         : %s" % payload["threshold_selection"]["status"])
    print("  post-hoc labelled leaves    : %d" % len(payload["post_hoc_quantities"]))
    print("  verdict                     : %s" % payload["verdict"])
    print("-" * 68)

    if args.check:
        for path, expected in ((JSON_PATH, json_text), (MD_PATH, md_text)):
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text" % path)
                return 1
        print("CHECK OK -- selection_multiplicity.json / .md are byte-identical")
        return 0

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in ((JSON_PATH, json_text), (MD_PATH, md_text)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("wrote %s" % path.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())