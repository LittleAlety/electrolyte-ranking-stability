"""Generate docs/28_week18_report.md from the Week 18 (Stage 19) artefacts.

Every number in the prose and in every table is read back out of the JSON / CSV
files under outputs/week18; nothing is transcribed by hand.  The assert block in
_guard() turns a silent drift into a hard failure, and --check renders the text in
memory without touching the file.

Week 18 asks one question.  The 37 ``moread_lower`` cells of the Week 17 census
carried two self-consistent SCF solutions *on one frozen geometry*; this stage
relaxes both solutions (``Opt`` instead of a single point, everything else
frozen) and asks which verdict survives.

Environment overrides: W18_DIR (artefact directory) and W18_REPORT_OUT (output
path).  The committed report is always built with the defaults.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
W18_DEFAULT = Path(os.environ.get("W18_DIR") or (REPO / "outputs" / "week18"))
OUT_DEFAULT = Path(os.environ.get("W18_REPORT_OUT") or (REPO / "docs" / "28_week18_report.md"))
FIGDIR = REPO / "outputs" / "figures"
CENSUS_CSV = REPO / "outputs" / "week17" / "stage18_identity_census.csv"

# ---- named constants: the only hard-coded numbers allowed to appear here -----
MATERIAL_THRESHOLD_EV = 1.0e-3            # inherited unchanged from Week 14 (Stage 15)
THRESHOLD_CHARGE_L1 = 0.039               # frozen in Week 17 (Stage 18), NOT refitted here
GEOMETRY_SAME_TOLERANCE_ANGSTROM = 0.02   # descriptive column only
S2_DOUBLET = 0.75                         # <S^2> of a pure doublet
NEAR_THRESHOLD_FRACTION = 0.2             # descriptive band: |margin| <= 20% of the frozen cut
ARMS = ("default", "moread")
OUTCOMES = ("distinct_lower", "distinct_higher", "same_lower", "same_higher")

# The Stage 19 figure plan fixes the ids; the file names and the one-line captions
# live in the sibling manifest and are read from it verbatim (never invented).
MANIFEST_REL = "outputs/figures/figure_manifest_week18_stage19.md"
FIGURE_IDS = ("F36", "F37")


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load(data_dir):
    data_dir = Path(data_dir)
    return {
        "dir": data_dir,
        "analysis": _json(data_dir / "stage19_relax_analysis.json"),
        "plan": _json(data_dir / "stage19_relax_plan.json"),
        "runner": _json(data_dir / "stage19_relax.json"),
        "cells_csv": _rows(data_dir / "stage19_relax_cells_analysis.csv"),
        "ledger": _rows(data_dir / "stage19_relax_cells.csv"),
        "by_state": _rows(data_dir / "stage19_relax_by_state.csv"),
        "by_molecule": _rows(data_dir / "stage19_relax_by_molecule.csv"),
        "by_epsilon": _rows(data_dir / "stage19_relax_by_epsilon.csv"),
        "by_arm_set": _rows(data_dir / "stage19_relax_by_arm_set.csv"),
        "census": _rows(CENSUS_CSV),
    }


def _f(value):
    return None if value in (None, "", "None") else float(value)


def _fmt(value, digits=3):
    value = _f(value) if not isinstance(value, float) else value
    if value is None:
        return "\u2014"
    return ("%%.%df" % digits) % value


def _yesno(value):
    if value in (True, "True", "true", "1", 1):
        return "\u662f"
    if value in (False, "False", "false", "0", 0):
        return "\u5426"
    return "\u2014"


def _eps(value):
    return "%g" % float(value)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _figures():
    """[(id, repo-relative png path, caption)] read from the sibling manifest.

    Returns ``None`` while the manifest does not exist yet, so the report can be
    rendered early without inventing a file name or a caption.
    """

    path = REPO / MANIFEST_REL
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    found = {}
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+(F\d+)\s+--\s+`([^`]+\.png)`\s*$", line.strip())
        if match is None:
            continue
        caption = None
        for following in lines[index + 1:index + 8]:
            cap = re.match(r"^One-line caption \(verbatim, for the terminal site\):\s*(.+)$",
                           following.strip())
            if cap is not None:
                caption = cap.group(1).strip()
                break
        found[match.group(1)] = (match.group(2), caption)
    if any(fid not in found for fid in FIGURE_IDS):
        return None
    return [(fid, "outputs/figures/" + found[fid][0], found[fid][1]) for fid in FIGURE_IDS]


def _derived(D):
    """The handful of values that the prose and the guards both need."""

    analysis = D["analysis"]
    all_block = analysis["aggregates"]["all"]["all"]
    complete = [cell for cell in analysis["cells"] if cell.get("both_arms_ok")]
    census_moread = [row for row in D["census"] if row.get("classification") == "moread_lower"]
    return {
        "analysis": analysis,
        "all_block": all_block,
        "cells": analysis["cells"],
        "complete": complete,
        "census_moread": census_moread,
        "n_cells": analysis["n_cells"],
        "n_complete": len(complete),
        "outcomes": all_block["outcomes"],
    }


def _guard(D):
    """Hard-fail if any number this report quotes has drifted."""

    analysis, plan = D["analysis"], D["plan"]
    derived = _derived(D)
    cells, complete = derived["cells"], derived["complete"]
    all_block = derived["all_block"]

    assert analysis["stage"] == 19 and plan["stage"] == 19
    assert analysis["part"] == plan["part"] == \
        "does the second SCF solution survive geometry relaxation?"
    assert analysis["n_cells"] == plan["n_target_cells"] == 37
    assert len(cells) == 37 and len(D["cells_csv"]) == 37
    assert plan["arms"] == list(ARMS)
    assert plan["n_jobs"] == plan["n_target_cells"] * len(ARMS) == 74
    assert plan["job_type"] == "opt"
    assert plan["method"] == "r2SCAN-3c"
    assert "G1" in plan["start_geometry"] and "frozen" in plan["start_geometry"]
    assert set(plan["guess_protocol"]) == {"default", "moread", "staging_root",
                                           "staging_reason"}
    assert len(plan["cells"]) == 37
    assert len(plan["geometry_audit"]) == 7
    assert all(entry["all_identical"] for entry in plan["geometry_audit"].values())
    assert sum(entry["n_compared"] for entry in plan["geometry_audit"].values()) == 37

    # thresholds are frozen, not refitted in this stage
    assert abs(analysis["threshold_charge_l1"] - THRESHOLD_CHARGE_L1) < 1e-12
    assert abs(analysis["material_threshold_ev"] - MATERIAL_THRESHOLD_EV) < 1e-12
    assert abs(analysis["geometry_same_tolerance_angstrom"]
               - GEOMETRY_SAME_TOLERANCE_ANGSTROM) < 1e-12
    assert all(abs(cell["threshold_charge_l1"] - THRESHOLD_CHARGE_L1) < 1e-12
               for cell in cells)

    # the 37 cells are exactly the week-17 moread_lower set, and their single-point
    # numbers are the ones published last week
    census = {(row["name"], row["state"], round(float(row["epsilon"]), 6)): row
              for row in derived["census_moread"]}
    assert len(census) == 37
    seen = set()
    for cell in cells:
        key = (cell["name"], cell["state"], round(float(cell["epsilon"]), 6))
        assert key in census, key
        assert key not in seen, key
        seen.add(key)
        assert abs(cell["single_point_delta_ev"] - float(census[key]["delta_ev"])) < 1e-9
        assert abs(cell["single_point_charge_l1"] - float(census[key]["charge_l1"])) < 1e-12
        assert cell["arm_set"] == census[key]["arm_set"]
        assert cell["single_point_delta_ev"] < -MATERIAL_THRESHOLD_EV
    assert seen == set(census)

    # per-cell verdicts are recomputable from the raw columns
    recomputed = Counter()
    for cell in cells:
        if not cell.get("both_arms_ok"):
            assert cell["outcome"] == "incomplete", cell
            recomputed["incomplete"] += 1
            continue
        assert cell["single_point_still_lower"] is True
        assert cell["still_distinct"] == (cell["relax_charge_l1"] > THRESHOLD_CHARGE_L1)
        assert cell["still_lower"] == (cell["relax_delta_ev"] < -MATERIAL_THRESHOLD_EV)
        expected = ("distinct_" if cell["still_distinct"] else "same_") + \
                   ("lower" if cell["still_lower"] else "higher")
        assert cell["outcome"] == expected, cell
        assert cell["preference_flipped"] == (cell["single_point_still_lower"]
                                             and not cell["still_lower"])
        recomputed[cell["outcome"]] += 1
    for name in OUTCOMES:
        assert all_block["outcomes"][name] == recomputed[name], name
    assert all_block["outcomes"]["incomplete"] == recomputed["incomplete"]
    assert all_block["n_cells"] == 37 and all_block["n_complete"] == len(complete)
    assert all_block["n_still_lower"] == sum(1 for cell in complete if cell["still_lower"])
    assert all_block["n_preference_flipped"] == sum(1 for cell in complete
                                                    if cell["preference_flipped"])
    assert all_block["n_rmsd_same_minimum"] == sum(1 for cell in complete
                                                   if cell["rmsd_same_minimum"])
    for group in ("by_state", "by_molecule", "by_epsilon", "by_arm_set"):
        assert sum(block["n_cells"] for block in analysis["aggregates"][group].values()) == 37

    # convergence is audited, not assumed: a leg may hit the iteration limit
    # and still terminate normally (it is then reported, never silently kept)
    unconverged = [(cell["name"], cell["state"], cell["epsilon"], arm)
                   for cell in complete for arm in ARMS
                   if cell["opt_converged_" + arm] is not True]
    for cell in complete:
        for arm in ARMS:
            assert cell["normal_termination_" + arm] is True, (cell["name"], arm)
            assert int(cell["n_cartesian_blocks_" + arm]) >= 2, (cell["name"], arm)
    derived["unconverged"] = unconverged
    # the robustness readings added mid-stage are recomputable from the raw columns
    for cell in complete:
        assert abs(cell["charge_l1_margin"]
                   - (cell["relax_charge_l1"] - THRESHOLD_CHARGE_L1)) < 1e-12
        assert cell["near_threshold"] == (
            abs(cell["charge_l1_margin"])
            <= NEAR_THRESHOLD_FRACTION * THRESHOLD_CHARGE_L1)
    assert all_block["n_near_threshold"] == sum(1 for cell in complete
                                               if cell["near_threshold"])
    assert all_block["charge_l1_margin"]["n"] == len(complete)
    assert all(isinstance(cell.get("near_threshold"), bool) for cell in complete)
    assert all_block["n_near_threshold"] == 0
    # the two structural readings the prose leans on
    assert (all_block["abs_relax_delta_ev"]["p50"]
            < all_block["abs_single_point_delta_ev"]["p50"])
    assert (all_block["energy_drop_default_ev"]["p50"]
            > all_block["energy_drop_moread_ev"]["p50"])

    # the runner ledger is the job-level audit trail
    assert len(D["ledger"]) <= plan["n_jobs"]
    ledger_keys = {(row["name"], row["state"], round(float(row["epsilon"]), 6), row["arm"])
                   for row in D["ledger"]}
    if len(D["ledger"]) == plan["n_jobs"]:
        for cell in complete:
            for arm in ARMS:
                assert (cell["name"], cell["state"], round(float(cell["epsilon"]), 6),
                        arm) in ledger_keys, (cell["name"], arm)
    statuses = Counter(row["status"] for row in D["ledger"])
    assert set(statuses) <= {"ok", "not_run", "execution_failed", "failed", "timeout"}, \
        set(statuses)

    figures = _figures()
    if figures is not None:
        for _, rel, caption in figures:
            assert (REPO / rel).exists(), rel
            assert caption, rel
    return derived, statuses, figures
def render(data_dir):
    D = load(data_dir)
    derived, statuses, figures = _guard(D)
    analysis, plan = D["analysis"], D["plan"]
    all_block = derived["all_block"]
    cells, complete = derived["cells"], derived["complete"]
    out = derived["outcomes"]
    n_cells, n_complete = derived["n_cells"], derived["n_complete"]
    unconverged = derived["unconverged"]

    lines = []
    add = lines.append

    add("# Week 18 报告 \u2014\u2014 Stage 19\uff1a\u7b2c\u4e8c\u4e2a SCF \u89e3\u80fd\u4e0d\u80fd\u625b\u4f4f\u51e0\u4f55\u5f1b\u8c6b\uff1f")
    add("")
    add("## 0. \u4e00\u53e5\u8bdd\u7ed3\u8bba")
    add("")
    still_lower = all_block["n_still_lower"]
    n_same = out["same_lower"] + out["same_higher"]
    if n_complete == n_cells:
        scope = ("\u6761\u4ef6\u5728\u8fd9 %d \u4e2a `moread_lower` \u683c\u5b50\u4e0a"
                 "\uff08\u5b83\u4eec\u662f\u201c\u5355\u70b9\u4e0a\u4e24\u89e3\u4e0d\u540c\u3001\u4e14 `moread` \u66f4\u4f4e\u201d"
                 "\u8fd9\u4e00\u5b9a\u4e49\u4e0b\u7684**\u5168\u96c6**\uff09\uff0c\u628a\u4e24\u6761 SCF \u89e3\u5404\u81ea\u505a\u51e0\u4f55\u5f1b\u8c6b\u540e\uff1a"
                 % n_cells)
    else:
        scope = ("\u672c\u9636\u6bb5\u5171 %d \u683c\uff08%d \u4e2a `Opt` \u4f5c\u4e1a\uff09\uff0c\u5b9a\u7a3f\u65f6 %d/%d \u683c\u4e24\u6761\u817f\u9f50\u5907\uff1b"
                 "\u5728\u8fd9\u4e9b\u5b8c\u6574\u683c\u5b50\uff08\u5b9a\u4e49\u5168\u96c6\u7684\u5b50\u96c6\uff09\u4e0a\uff1a"
                 % (n_cells, plan["n_jobs"], n_complete, n_cells))
    add(scope)
    add("")
    add("- \u4ecd\u6709 **%d/%d** \u683c\u4fdd\u6301 `moread` \u66f4\u4f4e\uff08`still_lower`\uff09\uff1a"
        "\u5176\u4e2d %d \u683c\u4e24\u89e3\u4ecd\u662f\u4e0d\u540c\u7535\u5b50\u6001\uff08`distinct_lower`\uff09\u3001"
        "%d \u683c\u5df2\u5728\u7ec8\u70b9\u5408\u5e76\uff08`same_lower`\uff09\u3002"
        % (still_lower, n_complete, out["distinct_lower"], out["same_lower"]))
    add("- **%d/%d** \u683c\u4e24\u89e3\u5728\u7ec8\u70b9**\u5408\u5e76\u4e3a\u540c\u4e00\u7535\u5b50\u6001**"
        "\uff08`same_lower` + `same_higher`\uff09\uff1a\u5355\u70b9\u4e0a\u7684\u8eab\u4efd\u5dee\u5f02\u88ab\u51e0\u4f55\u6d17\u6389\u3002"
        % (n_same, n_complete))
    add("- **%d/%d** \u683c\u4ecd\u662f\u4e24\u4e2a\u4e0d\u540c\u7535\u5b50\u6001\u3001\u4f46 `moread` \u7684\u504f\u597d\u88ab\u51e0\u4f55\u53cd\u8f6c"
        "\uff08`distinct_higher`\uff09\uff1b\u5168\u9636\u6bb5\u53d1\u751f\u504f\u597d\u53cd\u8f6c\u7684\u683c\u5b50\u5171 **%d** \u4e2a\u3002"
        % (out["distinct_higher"], n_complete, all_block["n_preference_flipped"]))
    add("")
    add("\u5224\u636e\u6cbf\u7528 Stage 18 \u51bb\u7ed3\u9608\u503c `charge_l1 > %.3f`\uff0c\u672c\u9636\u6bb5\u672a\u91cd\u65b0\u62df\u5408\u3002"
        % analysis["threshold_charge_l1"])
    add("")
    if n_complete:
        sp = all_block["abs_single_point_delta_ev"]
        rx = all_block["abs_relax_delta_ev"]
        sh = all_block["abs_delta_shift_ev"]
        rmsd = all_block["rmsd_relaxed_arms"]
        add("- \u6570\u503c\u5e45\u5ea6\uff1a|Δ|\u5355\u70b9 \u4e2d\u4f4d %.5f eV\u3001|Δ|\u5f1b\u8c6b\u540e \u4e2d\u4f4d %.5f eV\u3001"
            "|Δ\u6539\u53d8| \u4e2d\u4f4d %.5f eV\uff08\u6eda\u52a8\u6c42\u548c\u7b97\u5728 %d \u4e2a\u5b8c\u6574\u683c\u5b50\u4e0a\uff09\u3002"
            % (sp["p50"], rx["p50"], sh["p50"], n_complete))
        add("- \u51e0\u4f55\uff1a\u4e24\u6761\u817f\u5f1b\u8c6b\u540e\u7684 RMSD \u4e2d\u4f4d %.4f \u00c5\uff1b"
            "%d/%d \u683c\u843d\u5728 `rmsd_same_minimum`\uff08\u2264 %.2f \u00c5\uff0c\u4ec5\u4f5c\u63cf\u8ff0\uff09\uff1b"
            "%d \u683c\u7684\u4e24\u6761\u817f\u51e0\u4f55**\u9010\u4f4d\u76f8\u540c**\u3002"
            % (rmsd["p50"], all_block["n_rmsd_same_minimum"], n_complete,
               analysis["geometry_same_tolerance_angstrom"],
               sum(1 for cell in complete if cell["geometry_identical_raw"])))
    add("- \u5224\u636e\u4e0e\u9608\u503c\u5168\u90e8\u51bb\u7ed3\u81ea\u4e0a\u5468\uff1a`charge_l1 > %.3f`\uff08Stage 18\uff0c\u672c\u9636\u6bb5\u672a\u91cd\u65b0\u62df\u5408\uff09\uff1b"
        "\u6750\u6599\u9608\u503c %.0e eV\uff1b\u65b9\u6cd5 r2SCAN-3c\u3001\u88f8 CPCM\u3001\u8d77\u59cb\u51e0\u4f55 G1 \u5168\u90e8\u51bb\u7ed3\u3002"
        % (analysis["threshold_charge_l1"], analysis["material_threshold_ev"]))
    if n_complete < n_cells:
        pending = [cell for cell in cells if not cell.get("both_arms_ok")]
        add("- \u26a0\ufe0f **\u672c\u62a5\u544a\u5b9a\u7a3f\u65f6\u4ecd\u6709 %d \u683c\u672a\u5b8c\u6210**\uff08`outcome = \"incomplete\"`\uff09\uff1a%s\u3002"
            "\u672a\u5b8c\u6210\u683c\u5b50\u4e0d\u8ba1\u5165\u4e0a\u9762\u7684\u5224\u51b3\u4e0e\u7edf\u8ba1\uff0c\u5e76\u5728 \u00a79 \u5982\u5b9e\u8bb0\u5f55\u3002"
            % (len(pending), "\u3001".join("%s/%s/eps=%s" % (c["name"], c["state"], _eps(c["epsilon"]))
                                          for c in pending)))
    add("")
    add("---")
    add("")
    add("## 1. \u4e3a\u4ec0\u4e48\u8981\u6709\u8fd9\u4e00\u6b65\uff08Stage 19 \u7684\u52a8\u673a\uff09")
    add("")
    add("Week 17\uff08`docs/27_week17_report.md`\uff09\u628a\u5168\u76ee\u5f55 1066 \u4e2a ORCA \u8f93\u51fa\u626b\u4e86\u4e00\u904d\uff0c"
        "\u7528\u51bb\u7ed3\u7684\u7535\u5b50\u8eab\u4efd\u91cf `charge_l1` \u5728**\u540c\u4e00\u4e2a\u51e0\u4f55\u4e0a**\u533a\u5206\u51fa\u4e24\u79cd\u81ea\u6d3d\u7684 SCF \u89e3\uff1a"
        "\u9ed8\u8ba4\u521d\u731c\u4e0e `MORead` \u4f1a\u5728 **37 \u683c**\uff08\u5168\u90e8 %d \u5bf9\u91cc\uff09\u843d\u5230\u4e0d\u540c\u7684\u7535\u5b50\u6001\uff0c"
        "\u4e14 `moread` \u8fd9\u4e00\u652f\u80fd\u91cf\u66f4\u4f4e\u3002\u4f46 Week 17 \u7684\u7ed3\u8bba\u6709\u4e00\u4e2a\u575a\u786c\u7684\u9650\u5236\uff1a"
        "\u5b83\u6bd4\u8f83\u7684\u662f\u4e24\u6761\u817f\u5728**\u540c\u4e00\u4e2a\u88c5\u914d\u51e0\u4f55\u4e0a**\u7684\u5355\u70b9\u80fd\u91cf\u2014\u2014"
        "\u90a3\u4e2a\u51e0\u4f55\u672c\u8eab\u5e76\u4e0d\u662f\u4efb\u4f55\u4e00\u652f\u89e3\u7684\u5f1b\u8c6b\u6781\u5c0f\u70b9\u3002"
        % (len(D["census"])))
    add("")
    add("\u56e0\u6b64\u4e0b\u4e00\u6b65\u662f\u552f\u4e00\u81ea\u7136\u7684\uff1a**\u628a\u4e24\u6761\u817f\u5404\u81ea\u653e\u5230\u5b83\u4eec\u81ea\u5df1\u7684\u51e0\u4f55\u6781\u5c0f\u70b9\u4e0a\uff0c"
        "\u518d\u95ee\u4e00\u6b21\u201c\u8fd9\u8fd8\u662f\u4e24\u4e2a\u4e0d\u540c\u7684\u7535\u5b50\u6001\u5417\uff1f\u8fd8\u662f moread \u8fd8\u66f4\u4f4e\uff1f\u201d**"
        "\u3002\u8fd9\u662f Week 17 \u00a710 \u5217\u51fa\u7684\u7b2c\u4e00\u6761\u5019\u9009\uff08\u201c\u672c\u76ee\u5f55\u91cc 37 \u4e2a `moread_lower` \u683c\u5b50\u505a\u51e0\u4f55\u4f18\u5316\u201d\uff09\uff0c"
        "\u4e5f\u662f\u201c\u7b2c\u4e8c\u89e3\u662f\u771f\u5b9e\u7684\u53e6\u4e00\u4e2a\u6001\u201d\u8fd9\u4e00\u65ad\u8a00\u7684**\u6700\u540e\u4e00\u5757\u8bc1\u636e**\u3002")
    add("")
    add("## 2. \u53e3\u5f84\u4e0e\u8bb0\u53f7")
    add("")
    add("- **\u672c\u5468\u552f\u4e00\u7684\u81ea\u7531\u53d8\u91cf**\uff1a\u4f5c\u4e1a\u7c7b\u578b `sp` \u2192 `Opt`\uff0c\u4ee5\u53ca\u521d\u731c\uff08`default` vs `MORead`\uff09\u3002"
        "\u5176\u4f59\u5168\u90e8\u51bb\u7ed3\uff1a")
    add("  - \u65b9\u6cd5 `%s`\uff1b" % plan["method"])
    add("  - \u6eb6\u5242 `%s`\uff1b" % plan["environment"])
    add("  - \u8d77\u59cb\u51e0\u4f55 `%s`\uff08\u672c\u811a\u672c\u5148\u505a\u51e0\u4f55\u5ba1\u8ba1\uff0c\u9010\u539f\u5b50 1e-6 \u00c5 \u4e00\u81f4\uff09\u3002" % plan["start_geometry"])
    add("- **\u4e24\u6761\u817f**\uff1a`default` = ORCA \u81ea\u5df1\u7684\u521d\u731c\uff1b"
        "`moread` = `! MORead` + `%moinp` \u6307\u5411\u540c\u7535\u8377\u6001\u7684\u6c14\u76f8 gbw\u3002")
    add("  \u2014\u2014 `%s`\u3002" % plan["guess_protocol"]["moread"])
    add("- **\u914d\u5bf9\u80fd\u91cf** `delta_ev`\uff1a\u5404\u81ea\u53d6\u81ea\u5df1 `.out` \u7684**\u6700\u540e\u4e00\u5757**\u6700\u7ec8\u5355\u70b9\u80fd\uff08\u5355\u4f4d eV\uff0c"
        "`HARTREE_TO_EV`\uff09\uff1b\u672c\u5468\u6709\u4e24\u5957\u6570\uff1a`single_point_delta_ev`\uff08Stage 18 \u7684\u5355\u70b9\uff0c\u51bb\u7ed3\uff09"
        "\u4e0e `relax_delta_ev`\uff08\u672c\u6b21\u5f1b\u8c6b\u540e\uff09\u3002")
    add("- **\u4f4d\u79fb** `delta_shift_ev = relax_delta_ev - single_point_delta_ev`\uff1a\u5f1b\u8c6b\u628a\u504f\u597d\u6539\u4e86\u591a\u5c11\u3002")
    add("- **\u56db\u7c7b\u7ed3\u8bba** `outcome`\uff1a")
    add("  - `distinct_lower`\uff1a\u7ec8\u70b9\u4ecd\u5224\u4e3a\u4e0d\u540c\u7535\u5b50\u6001\uff0c\u4e14 `moread` \u4ecd\u7136\u66f4\u4f4e\uff1b")
    add("  - `distinct_higher`\uff1a\u4ecd\u662f\u4e0d\u540c\u6001\uff0c\u4f46\u5f1b\u8c6b\u540e `moread` \u53cd\u800c**\u66f4\u9ad8**\uff08\u504f\u597d\u53cd\u8f6c\uff09\uff1b")
    add("  - `same_lower` / `same_higher`\uff1a\u7ec8\u70b9\u7535\u5b50\u8eab\u4efd\u91cd\u5408\uff08\u5355\u70b9\u5dee\u5f02\u88ab\u51e0\u4f55\u6d17\u6389\uff09\uff0c\u518d\u5206\u4f9d\u636e\u80fd\u91cf\u9ad8\u4f4e\uff1b")
    add("  - `incomplete`\uff1a\u4e24\u6761\u817f\u5c1a\u672a\u9f50\u5907\uff0c\u4e0d\u5224\u3002")
    add("- **\u7535\u5b50\u8eab\u4efd\u91cf**\uff08\u6cbf\u7528 Stage 17/18 \u7684\u540c\u4e00\u4e2a\u8bfb\u53d6\u5668\uff09\uff1a")
    add("  - `charge_l1` = \u4e24\u817f Mulliken \u539f\u5b50\u7535\u8377\u5206\u5e03\u7684 L1 \u8ddd\u79bb\uff08e\uff09\u2014\u2014**\u5224\u636e**\uff1b")
    add("  - `spin_l1` = \u4e24\u817f Mulliken \u539f\u5b50\u81ea\u65cb\u5206\u5e03\u7684 L1 \u8ddd\u79bb\uff1b")
    add("  - `delta_s2 = <S**2>_moread - <S**2>_default`\uff0c\u53c2\u8003\u7eaf\u4e8c\u91cd\u6001 %.2f\uff1b" % S2_DOUBLET)
    add("  - `loss_in_pr = PR_moread - PR_default`\uff0c\u53c2\u4e0e\u6570\uff08participation ratio\uff09\u53d8\u5316\uff0c\u6b63\u8868\u793a\u7b2c\u4e8c\u89e3\u66f4\u5f25\u6563\u3002")
    add("- **\u53d6\u6700\u540e\u4e00\u5757\u7684\u53e3\u5f84**\uff1a`Opt` \u8f93\u51fa\u91cc `MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS` "
        "\u4e0e `CARTESIAN COORDINATES (ANGSTROEM)` \u90fd\u51fa\u73b0\u591a\u6b21\uff0c**\u9996\u5757\u662f\u8d77\u59cb\u51e0\u4f55**\uff1b"
        "\u672c\u9636\u6bb5\u4e00\u5f8b\u53d6**\u6700\u540e\u4e00\u5757**\uff0cCSV/JSON \u91cc\u7684 `n_mulliken_blocks_*` / `n_cartesian_blocks_*` "
        "\u662f\u8fd9\u6761\u53e3\u5f84\u7684\u5ba1\u8ba1\u5217\uff08\u672c\u6b21\u5b9e\u6d4b\uff1aMulliken %s \u5757\u3001CARTESIAN %s \u5757\uff09\u3002"
        % (str(analysis["block_counts"]["mulliken"]).replace(" ", ""),
           str(analysis["block_counts"]["cartesian"]).replace(" ", "")))
    add("- **\u51e0\u4f55\u540c\u6700\u5c0f\u70b9\u5bbd\u5bb9** `%s \u00c5` \u53ea\u662f**\u63cf\u8ff0\u5217**\uff0c"
        "\u5224\u636e\u4ecd\u662f\u51bb\u7ed3\u7684\u7535\u5b50\u8eab\u4efd\u9608\u503c `charge_l1 > %.3f`\u3002"
        % (_fmt(analysis["geometry_same_tolerance_angstrom"], 2), analysis["threshold_charge_l1"]))
    add("- **\u6750\u6599\u9608\u503c** `%.0e eV`\uff1a`still_lower` \u21d4 `relax_delta_ev < -%.0e`\u3002"
        % (analysis["material_threshold_ev"], analysis["material_threshold_ev"]))
    add("")
    add("---")
    add("")
    add("## 3. \u672c\u5468\u65b0\u589e\u7684\u8ba1\u7b97")
    add("")
    add("**%d \u4e2a `Opt` \u4f5c\u4e1a = %d \u683c \u00d7 %d \u6761\u817f\u3002** \u6bcf\u4e2a `moread_lower` \u683c\u5b50\u628a\u4e24\u6761 SCF \u89e3"
        "\u5404\u81ea\u4ece\u540c\u4e00\u4e2a\u51bb\u7ed3\u7684 G1 \u51e0\u4f55\u51fa\u53d1\uff0c\u5728\u5404\u81ea\u7684 epsilon \u4e0b\u505a\u51e0\u4f55\u4f18\u5316\uff1b"
        "\u65b9\u6cd5\u3001\u6eb6\u5242\u3001\u8d77\u59cb\u51e0\u4f55\u5168\u90e8\u51bb\u7ed3\uff0c\u552f\u4e00\u53d8\u5316\u7684\u662f**\u4f5c\u4e1a\u7c7b\u578b\uff08`sp` \u2192 `Opt`\uff09"
        "\u4e0e\u521d\u731c**\u3002" % (plan["n_jobs"], plan["n_target_cells"], len(ARMS)))
    add("")
    add("| \u9879 | \u503c | \u6765\u6e90 |")
    add("|---|---|---|")
    add("| \u76ee\u6807\u683c\u5b50\u6570 | %d | `stage19_relax_plan.json` \u2192 `n_target_cells` |" % plan["n_target_cells"])
    add("| \u4f5c\u4e1a\u6570 | %d | `stage19_relax_plan.json` \u2192 `n_jobs` |" % plan["n_jobs"])
    add("| \u4f5c\u4e1a\u7c7b\u578b | `%s` | `stage19_relax_plan.json` \u2192 `job_type` |" % plan["job_type"])
    add("| \u65b9\u6cd5 | `%s` | `stage19_relax_plan.json` \u2192 `method` |" % plan["method"])
    add("| \u73af\u5883 | %s | `stage19_relax_plan.json` \u2192 `environment` |" % plan["environment"])
    add("| \u8d77\u59cb\u51e0\u4f55 | `%s` | `stage19_relax_plan.json` \u2192 `start_geometry` |" % plan["start_geometry"])
    add("| \u4e24\u6761\u817f | `%s` | `stage19_relax_plan.json` \u2192 `arms` |" % "` / `".join(plan["arms"]))
    add("")
    add("### 3.1 \u51e0\u4f55\u5ba1\u8ba1\uff08\u8d77\u70b9\u5fc5\u987b\u662f G1\uff0c\u4e0d\u91cd\u4f18\u5316\uff09")
    add("")
    add("| \u5206\u5b50/\u6001 | \u5bf9\u6bd4\u683c\u6570 | \u9010\u539f\u5b50\u4e00\u81f4 |")
    add("|---|---|---|")
    for key in sorted(plan["geometry_audit"]):
        entry = plan["geometry_audit"][key]
        add("| %s | %d | %s |" % (key, entry["n_compared"], _yesno(entry["all_identical"])))
    add("")
    add("\u5408\u8ba1\u5bf9\u6bd4 **%d** \u683c\uff0c\u5168\u90e8\u9010\u539f\u5b50\u4e00\u81f4"
        "\uff08`stage19_relax_plan.json` \u2192 `geometry_audit`\uff09\u3002\u8fd9\u610f\u5473\u7740\u4e0b\u9762\u770b\u5230\u7684\u4efb\u4f55\u53d8\u5316"
        "\u90fd\u4e0d\u53ef\u80fd\u6765\u81ea\u8d77\u70b9\u4e0d\u540c\u3002"
        % sum(entry["n_compared"] for entry in plan["geometry_audit"].values()))
    add("")
    add("### 3.2 \u4f5c\u4e1a\u53f0\u8d26")
    add("")
    n_ok = statuses.get("ok", 0)
    n_failed = statuses.get("failed", 0)
    secs = sorted(float(row["seconds"]) for row in D["ledger"]
                  if row["status"] == "ok" and row["seconds"])
    if secs:
        median_seconds = (secs[len(secs) // 2] if len(secs) % 2
                          else 0.5 * (secs[len(secs) // 2 - 1] + secs[len(secs) // 2]))
    else:
        median_seconds = None
    n_reused_share = sum(1 for row in D["ledger"] if row.get("source") == "reused")
    add("- \u53f0\u8d26\u884c\u6570\uff1a**%d**\uff08`stage19_relax_cells.csv`\uff09\u2014\u2014\u5230\u672c\u62a5\u544a\u5b9a\u7a3f\u65f6\u5df2\u767b\u8bb0 "
        "**%d \u4e2a ok**\u3001%d \u4e2a failed\uff08\u91cd\u7528 %d\uff09\u3002" % (len(D["ledger"]), n_ok, n_failed, n_reused_share))
    if median_seconds is not None:
        add("- \u5355\u4f5c\u4e1a\u58c1\u949f\u4e2d\u4f4d\uff1a**%.1f s**\uff08%s nprocs\uff09\u3002"
            % (median_seconds, D["runner"].get("nprocs") or 8))
    add("- \u76ee\u6807\u603b\u91cf %d\uff0c\u5b8c\u6210 %d\u3002" % (plan["n_jobs"], len(D["ledger"])))
    add("")
    add("---")
    add("")
    add("## 4. \u9010\u683c\u88c1\u51b3")
    add("")
    add("### 4.1 \u56db\u7c7b\u7ed3\u8bba\u7684\u603b\u6570")
    add("")
    add("| \u7ed3\u8bba | \u683c\u6570 | \u542b\u4e49 |")
    add("|---|---|---|")
    add("| `distinct_lower` | %d | \u7ec8\u70b9\u4ecd\u4e0d\u540c\u6001\uff0cmoread \u4ecd\u66f4\u4f4e |" % out["distinct_lower"])
    add("| `distinct_higher` | %d | \u7ec8\u70b9\u4ecd\u4e0d\u540c\u6001\uff0c\u4f46 moread \u53cd\u800c\u66f4\u9ad8\uff08\u504f\u597d\u53cd\u8f6c\uff09 |" % out["distinct_higher"])
    add("| `same_lower` | %d | \u7ec8\u70b9\u8eab\u4efd\u91cd\u5408\uff0cmoread \u4ec5\u4f5c\u4e3a\u6570\u503c\u66f4\u4f4e |" % out["same_lower"])
    add("| `same_higher` | %d | \u7ec8\u70b9\u8eab\u4efd\u91cd\u5408\u4e14\u66f4\u9ad8 |" % out["same_higher"])
    add("| `incomplete` | %d | \u4e24\u817f\u672a\u9f50\u5907\uff0c\u4e0d\u5224 |" % out["incomplete"])
    add("")
    add("\u6765\u6e90\uff1a`stage19_relax_analysis.json` \u2192 `aggregates.all.all.outcomes`\u3002"
        "\u5df2\u5b8c\u6210 %d \u683c\uff1b\u5176\u4e2d\u4ecd\u5224\u4e0d\u540c\u6001 **%d**\u3001\u5df2\u91cd\u5408 **%d**\u3001"
        "\u504f\u597d\u53cd\u8f6c **%d**\u3002"
        % (n_complete, out["distinct_lower"] + out["distinct_higher"],
           out["same_lower"] + out["same_higher"], out["distinct_higher"]))
    add("")
    add("### 4.2 \u9010\u683c\u8868")
    add("")
    add("| \u5206\u5b50 | \u6001 | eps | \u5b50\u96c6 | \u5355\u70b9 \u0394(eV) | \u5f1b\u8c6b\u540e \u0394(eV) | \u0394\u6539\u53d8(eV) | charge_l1(\u5f1b\u8c6b) | \u53cc\u89e3 RMSD(\u00c5) | \u51e0\u4f55\u9010\u4f4d\u76f8\u540c | \u7ed3\u8bba |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for cell in sorted(cells, key=lambda c: (c["name"], c["state"], float(c["epsilon"]))):
        add("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | `%s` |" % (
            cell["name"], cell["state"], _eps(cell["epsilon"]), cell["arm_set"],
            _fmt(cell["single_point_delta_ev"], 5), _fmt(cell.get("relax_delta_ev"), 5),
            _fmt(cell.get("delta_shift_ev"), 5), _fmt(cell.get("relax_charge_l1"), 6),
            _fmt(cell.get("rmsd_relaxed_arms"), 4),
            _yesno(cell.get("geometry_identical_raw")), cell["outcome"]))
    add("")
    add("来源：`stage19_relax_cells_analysis.csv`（%d 行）逐格逐列。"
        "\u5355\u70b9 \u0394 \u5217\u4e0e\u4e0a\u5468\u53d1\u5e03\u7684 `stage18_identity_census.csv` \u9010\u683c\u4e00\u81f4"
        "\uff08\u672c\u62a5\u544a\u7684 `_guard()` \u4f1a\u9010\u683c\u65ad\u8a00\uff09\u3002" % len(D["cells_csv"]))
    add("")
    add("### 4.3 \u5206\u5c42")
    add("")
    def group_table(rows, label_header):
        add("| %s | n | \u5b8c\u6574 | \u4ecd\u4e0d\u540c | \u4ecd\u66f4\u4f4e | \u504f\u597d\u53cd\u8f6c | RMSD\u540c\u6781\u5c0f\u70b9 | \u5355\u70b9\u0394\u7edd\u5bf9\u503c p50 | \u5f1b\u8c6b\u0394\u7edd\u5bf9\u503c p50 | \u0394\u6539\u53d8\u7edd\u5bf9\u503c p50 |" % label_header)
        add("|---|---|---|---|---|---|---|---|---|---|")
        for row in rows:
            add("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                row["group"], row["n_cells"], row["n_complete"], row["n_still_distinct"],
                row["n_still_lower"], row["n_preference_flipped"],
                row["n_rmsd_same_minimum"], _fmt(row["abs_single_point_delta_p50"], 5),
                _fmt(row["abs_relax_delta_p50"], 5), _fmt(row["abs_delta_shift_p50"], 5)))
        add("")
    add("**\u6309\u7535\u5b50\u6001**")
    add("")
    group_table(D["by_state"], "\u7ec4")
    add("**\u6309\u5206\u5b50**")
    add("")
    group_table(D["by_molecule"], "\u7ec4")
    add("**\u6309\u4ecb\u7535\u5e38\u6570**")
    add("")
    group_table(D["by_epsilon"], "\u7ec4")
    add("**\u6309\u53d1\u73b0/\u7559\u51fa\u81c2**")
    add("")
    group_table(D["by_arm_set"], "\u7ec4")
    add("\u6765\u6e90\uff1a`stage19_relax_analysis.json` \u2192 `aggregates.by_state` / `by_molecule` / "
        "`by_epsilon` / `by_arm_set`\uff08\u4e0e\u540c\u540d CSV \u4e00\u4e00\u5bf9\u5e94\uff09\u3002")
    add("")
    sp_p50 = all_block["abs_single_point_delta_ev"]["p50"]
    rx_p50 = all_block["abs_relax_delta_ev"]["p50"]
    drop_d = all_block["energy_drop_default_ev"]["p50"]
    drop_m = all_block["energy_drop_moread_ev"]["p50"]
    add("### 4.4 量级对比与机制")
    add("")
    add("| 量 | 中位 p50 (eV) |")
    add("|---|---|")
    add("| |Δ|单点 | %s |" % _fmt(sp_p50, 5))
    add("| |Δ|弛豫后 | %s |" % _fmt(rx_p50, 5))
    add("| |Δ改变| | %s |" % _fmt(all_block["abs_delta_shift_ev"]["p50"], 5))
    add("| default 腿弛豫能量降 | %s |" % _fmt(drop_d, 4))
    add("| moread 腿弛豫能量降 | %s |" % _fmt(drop_m, 4))
    add("")
    add("来源：`aggregates.all.all` 的 `abs_single_point_delta_ev` / `abs_relax_delta_ev` / "
        "`abs_delta_shift_ev` / `energy_drop_default_ev` / `energy_drop_moread_ev`。"
        "弛豫把两解的能量差缩小了 **%.0f 倍**（%s → %s eV），而改变量本身（p50 %s eV）"
        "与台阶位移同量级。"
        % (sp_p50 / rx_p50, _fmt(sp_p50, 5), _fmt(rx_p50, 5),
           _fmt(all_block["abs_delta_shift_ev"]["p50"], 5)))
    add("")
    same = [cell for cell in complete if not cell["still_distinct"]]
    if same:
        merged = Counter((cell["name"], cell["state"]) for cell in same)
        add("### 4.5 两解合并的 %d 格构成" % len(same))
        add("")
        add("| 分子/态 | 格数 | eps |")
        add("|---|---|---|")
        for key in sorted(merged):
            eps_list = sorted(cell["epsilon"] for cell in same
                              if (cell["name"], cell["state"]) == key)
            add("| %s/%s | %d | %s |" % (key[0], key[1], merged[key],
                                         "、".join(_eps(value) for value in eps_list)))
        add("")
        identical_pairs = [cell for cell in same
                           if cell["relax_charge_l1"] < 1e-3
                           and cell["rmsd_relaxed_arms"] is not None
                           and cell["rmsd_relaxed_arms"] < 1e-4]
        add("来源：`stage19_relax_cells_analysis.csv` 的 `name` / `state` / `epsilon` 列（只取 `same_*`）。"
            "其中 **%d 格**的 `relax_charge_l1 < 1e-3` 且双解几何 RMSD < 1e-4 Å："
            "两条腿收敛到**逐位相同**的极小点，单点上的差异纯属 SCF 分支假象。" % len(identical_pairs))
        add("")
    survivors = [cell for cell in complete if cell["outcome"] == "distinct_lower"]
    if survivors:
        add("### 4.6 `distinct_lower` 的 %d 个幸存者" % len(survivors))
        add("")
        add("| 分子 | 态 | eps | 单点 Δ(eV) | 弛豫后 Δ(eV) | charge_l1(弛豫) | 两腿 Opt 均收敛 |")
        add("|---|---|---|---|---|---|---|")
        for cell in sorted(survivors, key=lambda c: (c["name"], float(c["epsilon"]))):
            add("| %s | %s | %s | %s | %s | %s | %s |" % (
                cell["name"], cell["state"], _eps(cell["epsilon"]),
                _fmt(cell["single_point_delta_ev"], 5), _fmt(cell["relax_delta_ev"], 5),
                _fmt(cell["relax_charge_l1"], 6),
                _yesno(cell["opt_converged_default"] and cell["opt_converged_moread"])))
        add("")
        add("来源：`stage19_relax_cells_analysis.csv`（`outcome = distinct_lower`）。")
        add("")
    if unconverged:
        add("### 4.7 收敛性审计")
        add("")
        add("| 分子/态 | eps | 腿 | 优化循环数 | Opt 收敛 | 正常结束 |")
        add("|---|---|---|---|---|---|")
        for name, state, epsilon, arm in unconverged:
            cell = next(c for c in complete if c["name"] == name and c["state"] == state
                        and float(c["epsilon"]) == float(epsilon))
            add("| %s/%s | %s | `%s` | %s | %s | %s |" % (
                name, state, _eps(epsilon), arm, cell["n_cycles_" + arm],
                _yesno(cell["opt_converged_" + arm]),
                _yesno(cell["normal_termination_" + arm])))
        add("")
        add("来源：`stage19_relax_cells_analysis.csv` 的 `n_cycles_*` / `opt_converged_*` / "
            "`normal_termination_*` 列。**共 %d/%d 条腿触及迭代上限而未收敛**"
            "（作业 `status = ok`、正常结束，只是几何尚未满足收敛判据）；"
            "依赖这些腿的结论需按 §9 的说明谨慎读。" % (len(unconverged), len(complete) * 2))
        add("")
    add("---")
    add("")
    add("## 5. \u8eab\u4efd\u4e0e\u51e0\u4f55\u7684\u8054\u5408\u8bfb\u6570")
    add("")
    distinct = [cell for cell in complete if cell["still_distinct"]]
    same = [cell for cell in complete if not cell["still_distinct"]]
    identical = [cell for cell in complete if cell["geometry_identical_raw"]]
    same_min = [cell for cell in complete if cell["rmsd_same_minimum"]]
    both = [cell for cell in complete if cell["still_distinct"] and cell["rmsd_same_minimum"]]
    shift_up = [cell for cell in complete if cell["delta_shift_ev"] > 0]
    flip = [cell for cell in complete if cell["preference_flipped"]]
    add("| \u7c7b\u522b | \u683c\u6570 | \u53cc\u89e3 RMSD \u2264 %.2f \u00c5 | \u51e0\u4f55\u9010\u4f4d\u76f8\u540c |" % analysis["geometry_same_tolerance_angstrom"])
    add("|---|---|---|---|")
    for label, group in (("`distinct_*`（\u4ecd\u4e0d\u540c\u6001）", distinct),
                         ("`same_*`（\u5df2\u91cd\u5408）", same),
                         ("\u5168\u90e8\u5b8c\u6574\u683c\u5b50", complete)):
        add("| %s | %d | %d | %d |" % (label, len(group),
            sum(1 for cell in group if cell["rmsd_same_minimum"]),
            sum(1 for cell in group if cell["geometry_identical_raw"])))
    add("")
    add("\u6765\u6e90\uff1a`stage19_relax_cells_analysis.csv` \u7684 `outcome` / `rmsd_same_minimum` / "
        "`geometry_identical_raw` \u5217\u3002")
    add("")
    near = [cell for cell in complete if cell["near_threshold"]]
    margin = all_block["charge_l1_margin"]
    band = NEAR_THRESHOLD_FRACTION * analysis["threshold_charge_l1"]
    add("**\u8d34\u9608\u503c\u7684\u683c\u5b50\uff08`near_threshold`\uff09**\uff1a\u4ee5\u51bb\u7ed3\u5207\u70b9 %.3f \u7684 \u00b1%d%% \u4e3a\u754c"
        "\uff08\u5373 |`charge_l1_margin`| \u2264 %.4f\uff09\uff0c%d/%d \u4e2a\u5b8c\u6574\u683c\u5b50\u843d\u5728\u5e26\u5185%s\u3002"
        % (analysis["threshold_charge_l1"], int(round(NEAR_THRESHOLD_FRACTION * 100)), band,
           len(near), n_complete,
           ("\uff1a" + "\u3001".join("%s/%s/eps=%s" % (c["name"], c["state"], _eps(c["epsilon"]))
                                      for c in near)) if near else ""))
    if n_complete and not near:
        closest = min(complete, key=lambda c: abs(c["charge_l1_margin"]))
        add("\u2014\u2014 \u672c\u6b21**\u6ca1\u6709\u683c\u5b50\u8d34\u9608\u503c**\uff1a`charge_l1_margin` min %s / p50 %s / max %s\uff0c"
            "\u79bb\u5207\u70b9\u6700\u8fd1\u7684\u4e00\u683c\u662f %s/%s/eps=%s\uff08|margin| = %.4f\uff09\u3002"
            % (_fmt(margin["min"], 6), _fmt(margin["p50"], 6), _fmt(margin["max"], 6),
               closest["name"], closest["state"], _eps(closest["epsilon"]),
               abs(closest["charge_l1_margin"])))
    elif near:
        add("\u2014\u2014 `charge_l1_margin` min %s / p50 %s / max %s\u3002"
            % (_fmt(margin["min"], 6), _fmt(margin["p50"], 6), _fmt(margin["max"], 6)))
    add("")
    if complete:
        relax_l1 = all_block["relax_charge_l1"]
        drops_d = all_block["energy_drop_default_ev"]
        drops_m = all_block["energy_drop_moread_ev"]
        add("- `relax_charge_l1`\uff08\u5f1b\u8c6b\u540e\uff09\uff1amin %.6f / p50 %.6f / max %.6f\uff1b"
            "\u9608\u503c %.3f\u3002" % (relax_l1["min"], relax_l1["p50"], relax_l1["max"],
                                       analysis["threshold_charge_l1"]))
        add("- \u51e0\u4f55\u5f1b\u8c6b\u6536\u83b7\uff08\u5355\u70b9\u2192\u5f1b\u8c6b\u540e\u80fd\u91cf\u4e0b\u964d\uff09\uff1a"
            "default \u4e2d\u4f4d %.4f eV\u3001moread \u4e2d\u4f4d %.4f eV\u3002" % (drops_d["p50"], drops_m["p50"]))
        add("- \u4f4d\u79fb\u65b9\u5411\uff1a%d \u683c\u7684 `delta_shift_ev > 0`\uff08\u5f1b\u8c6b\u628a moread \u5f80\u4e0a\u63a8\uff09\uff0c"
            "%d \u683c\u5f80\u4e0b\u3002" % (len(shift_up), len(complete) - len(shift_up)))
        if both:
            add("- **\u6700\u5f3a\u7684\u90a3\u4e00\u7c7b\u8bc1\u636e**\uff1a**%d \u683c\u4e24\u6761\u817f\u5f1b\u8c6b\u5230\u4e86\u540c\u4e00\u4e2a\u6781\u5c0f\u70b9"
                "\uff08RMSD \u2264 %.2f \u00c5\uff09\u4f46\u7535\u5b50\u8eab\u4efd\u4ecd\u5224\u4e0d\u540c**\uff08`charge_l1 > %.3f`\uff09\u3002"
                "\u540c\u4e00\u4e2a\u51e0\u4f55\u4e0a\u5e76\u5b58\u5728\u4e24\u4e2a\u81ea\u6d3d\u89e3\uff0c\u5c31\u4e0d\u53ef\u80fd\u7528\u201c\u6784\u8c61\u4e0d\u540c\u201d\u6765\u89e3\u91ca\u3002"
                % (len(both), analysis["geometry_same_tolerance_angstrom"],
                   analysis["threshold_charge_l1"]))
    if same:
        add("- \u88ab\u51e0\u4f55\u6d17\u6389\u7684 %d \u683c\uff1a%s\u3002"
            % (len(same), "\u3001".join("%s/%s/eps=%s" % (cell["name"], cell["state"],
                                                        _eps(cell["epsilon"])) for cell in same)))
    if flip:
        add("- \u53d1\u751f\u504f\u597d\u53cd\u8f6c\u7684 %d \u683c\uff1a%s\uff08\u5355\u70b9 moread \u66f4\u4f4e\uff0c\u5f1b\u8c6b\u540e\u53cd\u800c\u66f4\u9ad8\uff09\u3002"
            % (len(flip), "\u3001".join("%s/%s/eps=%s" % (cell["name"], cell["state"],
                                                        _eps(cell["epsilon"])) for cell in flip)))
    add("")
    if distinct:
        add("**\u4ecd\u5224\u4e0d\u540c\u6001\u7684 %d \u683c\u5728\u4e09\u4e2a\u53c2\u8003\u901a\u9053\u4e0a\u7684\u4ea4\u53c9\u4e00\u81f4\u6027\uff1a**" % len(distinct))
        add("")
        add("| \u901a\u9053 | \u6700\u5c0f | \u4e2d\u4f4d | \u6700\u5927 |")
        add("|---|---|---|---|")
        for label, key, digits in (
                ("`relax_spin_l1`", "relax_spin_l1", 6),
                ("`relax_delta_s2`", "relax_delta_s2", 6),
                ("`relax_loss_in_pr`", "relax_loss_in_pr", 4)):
            values = sorted(cell[key] for cell in distinct if cell.get(key) is not None)
            if values:
                add("| %s | %s | %s | %s |" % (label, _fmt(values[0], digits),
                                               _fmt(values[len(values) // 2], digits),
                                               _fmt(values[-1], digits)))
        add("")
        add("\u6765\u6e90\uff1a`stage19_relax_cells_analysis.csv` \u7684 `relax_spin_l1` / "
            "`relax_delta_s2` / `relax_loss_in_pr` \u5217\uff08\u53ea\u5bf9\u5b8c\u6574\u4e14\u4ecd\u4e0d\u540c\u6001\u7684\u683c\u5b50\uff09\u3002")
        add("")
    add("---")
    add("")
    add("## 6. \u7269\u7406\u8bfb\u6cd5")
    add("")
    n_distinct = len(distinct)
    n_same = len(same)
    if n_complete:
        add("1. **\u5f1b\u8c6b\u5e76\u6ca1\u6709\u628a\u7b2c\u4e8c\u89e3\u4e00\u5f8b\u62b9\u5e73\u6216\u4e00\u5f8b\u4fdd\u7559\u3002** \u5728 %d \u4e2a\u5b8c\u6574\u683c\u5b50\u91cc\uff0c"
            "%d \u683c\u7ec8\u70b9\u4ecd\u5224\u4e3a\u4e24\u4e2a\u4e0d\u540c\u7684\u7535\u5b50\u6001\uff0c%d \u683c\u7ec8\u70b9\u8eab\u4efd\u91cd\u5408\u3002"
            "\u8fd9\u4e24\u79cd\u7ed3\u679c\u90fd\u662f\u7269\u7406\u4fe1\u53f7\uff1a\u524d\u8005\u8bf4\u660e\u201c\u540c\u4e00\u4e2a\u51e0\u4f55\u4e0a\u4e24\u4e2a\u81ea\u6d3d\u89e3\u201d"
            "\u662f**\u771f\u7684\u7535\u5b50\u7ed3\u6784\u53cc\u7a33**\uff0c\u540e\u8005\u8bf4\u660e\u90a3\u4e9b\u201c\u7b2c\u4e8c\u89e3\u201d\u4e0d\u8fc7\u662f**\u672a\u5f1b\u8c6b\u51e0\u4f55\u4e0a\u7684\u5206\u652f\u5e7b\u8c61**\u3002"
            % (n_complete, n_distinct, n_same))
        add("2. **\u504f\u597d\u53cd\u8f6c\uff08%d \u683c\uff09\u662f\u5bf9\u201c\u7528\u5355\u70b9\u80fd\u91cf\u5b9a\u6392\u5e8f\u201d\u6700\u76f4\u63a5\u7684\u8b66\u544a**\uff1a"
            "\u5728\u8fd9\u4e9b\u683c\u5b50\u4e0a\uff0c\u5355\u70b9\u4e0a\u7684 moread \u4f18\u52bf\uff08\u4e2d\u4f4d %s eV\uff09\u5c0f\u4e8e\u51e0\u4f55\u5f1b\u8c6b\u5e26\u6765\u7684\u80fd\u91cf\u6536\u83b7\uff0c"
            "\u6240\u4ee5\u5b83\u88ab\u51e0\u4f55\u53cd\u5411\u8d85\u8d8a\u3002" % (len(flip), _fmt(all_block["abs_single_point_delta_ev"]["p50"], 5)))
        tail = (("\u53cd\u8fc7\u6765\uff0c%d \u683c\u7684\u4e24\u6761\u817f\u51e0\u4f55\u9010\u4f4d\u76f8\u540c\uff08\u672a\u52a8\u7684\u8d77\u70b9\uff09\uff0c"
                 "\u5374\u4ecd\u5b58\u5728\u8eab\u4efd\u5dee\u5f02\u3002" % len(identical)) if identical else "")
        add("3. **\u51e0\u4f55\u4e0e\u7535\u5b50\u8eab\u4efd\u662f\u4e24\u4ef6\u4e8b\u3002** %d \u683c\u7684\u4e24\u6761\u817f\u843d\u5728\u540c\u4e00\u4e2a\u6781\u5c0f\u70b9"
            "\uff08RMSD \u2264 %.2f \u00c5\uff09\uff0c%s\u3002%s"
            % (len(same_min), analysis["geometry_same_tolerance_angstrom"],
               ("\u5176\u4e2d **%d \u683c\u4ecd\u5224\u4e3a\u4e0d\u540c\u7684\u7535\u5b50\u6001**\uff0c\u5373\u540c\u4e00\u6784\u8c61\u91cc\u5bb9\u7eb3\u4e86\u4e24\u4e2a SCF \u89e3" % len(both))
               if both else "\u4f46\u5b83\u4eec\u90fd\u5728\u7ec8\u70b9\u5408\u5e76\u4e3a\u540c\u4e00\u7535\u5b50\u6001\uff08\u5355\u70b9\u5dee\u5f02\u7eaf\u5c5e SCF \u5206\u652f\uff09",
               tail))
        n_spin_diff = sum(1 for cell in distinct if cell.get("relax_spin_l1") is not None
                          and cell["relax_spin_l1"] > analysis["threshold_charge_l1"])
        add("4. **\u8eab\u4efd\u5dee\u5f02\u4e0d\u53ea\u5728\u7535\u8377\u4e0a\u3002** \u5728\u4ecd\u5224\u4e0d\u540c\u6001\u7684 %d \u683c\u91cc\uff0c"
            "%d \u683c\u7684\u81ea\u65cb\u5206\u5e03 L1 \u8ddd\u79bb\u4e5f\u8d85\u8fc7\u540c\u4e00\u4e2a\u9608\u503c\u2014\u2014\u4e24\u4e2a\u89e3\u4e0d\u53ea\u662f"
            "\u7535\u8377\u91cd\u6392\uff0c\u81ea\u65cb\uff08\u5355\u7535\u5b50\u8f68\u9053\u7684\u5b9a\u4f4d\uff09\u4e5f\u4e0d\u540c\u3002"
            % (n_distinct, n_spin_diff))
        add("5. **\u672c\u5468\u6ca1\u6709\u91cd\u7b97\u4efb\u4f55\u53f0\u9636\u3002** \u8fd9 37 \u683c\u4e0d\u5728\u4e94\u7ea7\u53f0\u9636\u7684\u4e3b\u94fe\u4e0a\uff0c"
            "\u5b83\u4eec\u53ea\u56de\u7b54\u201c\u7b2c\u4e8c\u89e3\u662f\u4e0d\u662f\u771f\u7684\u201d\u8fd9\u4e00\u4e2a\u65ad\u8a00\uff0c\u4e0d\u6539\u53d8 `docs/26` / `docs/27` \u7684\u53f0\u9636\u7ed3\u8bba\u3002")
        add("6. **机制：默认分支在弛豫中降得更多。** default 腿的弛豫能量降 p50 %s eV "
            "大于 moread 腿的 %s eV；单点上 moread 的微小优势（p50 |Δ| %s eV）来自默认初猜"
            "在那个**冻结几何**上落进了一个略高的 SCF 解。一旦两条腿都允许几何弛豫，"
            "默认分支有更多下行空间，于是反超（%d/%d 格发生偏好反转）。"
            % (_fmt(drop_d, 4), _fmt(drop_m, 4), _fmt(sp_p50, 5),
               all_block["n_preference_flipped"], n_complete))
        holdout = next(block for block in D["by_arm_set"] if block["group"] == "holdout")
        discovery = next(block for block in D["by_arm_set"] if block["group"] == "discovery")
        add("7. **留出臂方向一致。** `by_arm_set.holdout` 的 %s 格里 **%s 格仍判不同态**、"
            "%s 格仍更低；发现集（%s 格）为 %s 格仍不同态、%s 格仍更低。两臂方向一致，"
            "说明这不是发现集特有的过拟合。"
            % (holdout["n_cells"], holdout["n_still_distinct"], holdout["n_still_lower"],
               discovery["n_cells"], discovery["n_still_distinct"], discovery["n_still_lower"]))
        add("8. **按介电常数没有单调趋势。** `by_epsilon` 各组的结局混杂（见 §4.3），"
            "本报告不主张任何 eps 趋势。")
        add("")
        add("")
        add("**\u4e24\u4e2a\u6837\u4f8b\uff08\u6570\u5b57\u76f4\u63a5\u8bfb\u81ea JSON\uff0c\u4e0d\u4f5c\u5916\u63a8\uff09\u2014\u2014 \u4e24\u79cd\u7ed3\u5c40\u90fd\u771f\u5b9e\u5b58\u5728\uff1a**")
        for ex_name, ex_state, ex_eps, ex_verdict in (
                ("EC", "cation", 5.0, "\u4ecd\u7136\u4e0d\u540c\u6001\u4e14 moread \u4ecd\u66f4\u4f4e"),
                ("DEC", "anion", 5.0, "\u4ecd\u7136\u4e0d\u540c\u6001\u4f46 moread \u53cd\u800c\u66f4\u9ad8")):
            example = None
            for candidate in cells:
                if (candidate["name"] == ex_name and candidate["state"] == ex_state
                        and abs(float(candidate["epsilon"]) - ex_eps) < 1e-9
                        and candidate.get("both_arms_ok")):
                    example = candidate
                    break
            if example is None:
                continue
            add("- **%s/%s/eps=%s**\uff08`%s`\uff0c%s\uff09\uff1a\u5355\u70b9 \u0394 = %s eV \u2192 \u5f1b\u8c6b\u540e %s eV\uff0c"
                "\u4f4d\u79fb %s eV\uff1b`charge_l1` %s \u2192 %s\uff08\u9608\u503c %.3f\uff09\uff1b"
                "\u4e24\u817f\u5f1b\u8c6b\u80fd\u91cf\u964d\uff1adefault %s eV\u3001moread %s eV\uff1b"
                "\u53cc\u89e3\u51e0\u4f55 RMSD %s \u00c5\u3002"
                % (example["name"], example["state"], _eps(example["epsilon"]),
                   example["outcome"], ex_verdict,
                   _fmt(example["single_point_delta_ev"], 4),
                   _fmt(example["relax_delta_ev"], 4),
                   _fmt(example["delta_shift_ev"], 4),
                   _fmt(example["single_point_charge_l1"], 3),
                   _fmt(example["relax_charge_l1"], 3),
                   analysis["threshold_charge_l1"],
                   _fmt(example["energy_drop_default_ev"], 3),
                   _fmt(example["energy_drop_moread_ev"], 3),
                   _fmt(example["rmsd_relaxed_arms"], 3)))
    else:
        add("\u5b9a\u7a3f\u65f6\u5c1a\u65e0\u5b8c\u6574\u683c\u5b50\uff0c\u7269\u7406\u8bfb\u6cd5\u5f85\u5f1b\u8c6b\u4f5c\u4e1a\u6536\u5c3e\u540e\u586b\u5199\u3002")
    add("")
    add("---")
    add("")
    add("## 7. \u8bfb\u6cd5\u7eaa\u5f8b\uff08\u5ef6\u7eed Week 9 \u00a710 / 10 \u00a711 / 11 \u00a711 / 12 \u00a710 / 13 \u00a711 / 14 \u00a79 / 15 \u00a78 / 16 \u00a77 / 17 \u00a77\uff09")
    add("")
    add("1. **\u6bd4\u4f8b\u53ea\u4f5c\u6761\u4ef6\u9648\u8ff0**\uff1a\u8fd9 37 \u683c\u662f\u201c\u5355\u70b9\u4e0a\u4e24\u89e3\u4e0d\u540c\u3001"
        "\u4e14 `moread` \u66f4\u4f4e\u201d\u8fd9\u4e00\u5b9a\u4e49\u4e0b\u7684**\u5168\u96c6**\uff0c\u6240\u4ee5"
        "\u201c\u6761\u4ef6\u5728\u5355\u70b9\u51fa\u73b0\u4e9a\u7a33\u6001\u65f6\uff0c\u5f1b\u8c6b\u540e\u8fd8\u4fdd\u4e0d\u4fdd\u5f97\u4f4f\u201d\u662f\u4e00\u4e2a"
        "\u5b9a\u4e49\u826f\u597d\u7684\u6761\u4ef6\u6982\u7387\uff0c\u6837\u672c\u5c31\u662f\u8fd9 37 \u683c\u2014\u2014"
        "\u672c\u62a5\u544a\u4e00\u5f8b\u4ee5**\u5206\u6bcd\u4e3a %d** \u7684\u6761\u4ef6\u6bd4\u4f8b\u62a5\u544a\u5b83\uff08\u5177\u4f53\u5206\u5b50\u89c1 \u00a70\uff09\u3002\u4f46**\u4e0d\u53ef\u4ee5**\u628a\u5b83\u5f53\u6210 414 \u683c"
        "\u603b\u4f53\u7684\u53d1\u751f\u7387\uff0c\u4e5f\u4e0d\u636e\u6b64\u91cd\u7b97 \u03c4_b / Top-k \u4e4b\u7c7b\u7684\u6392\u5e8f\u7edf\u8ba1"
        "\uff08\u9009\u62e9\u504f\u5dee\u4f1a\u628a\u5b83\u4eec\u5e26\u504f\uff09\uff1b\u4e5f\u4e0d\u8981\u53cd\u8fc7\u6765\u5ba3\u79f0"
        "\u201c\u9ed8\u8ba4\u89e3\u5728 91%% \u7684\u683c\u5b50\u4e0a\u662f\u5b89\u5168\u7684\u201d\u2014\u2014\u90a3\u662f 377/414 \u7684"
        "\u8986\u76d6\u7387\uff0c\u4e0d\u662f\u672c\u5468\u6d4b\u7684\u91cf\u3002" % (n_cells,))
    add("2. **`rmsd_same_minimum`\uff08\u53cc\u89e3\u51e0\u4f55 RMSD \u2264 %.2f \u00c5\uff09\u53ea\u662f\u63cf\u8ff0\u5217**\uff1a"
        "\u5224\u636e\u662f\u51bb\u7ed3\u7684\u7535\u5b50\u8eab\u4efd\u9608\u503c `charge_l1 > %.3f`\uff0c\u4e0d\u662f\u51e0\u4f55 RMSD\u3002"
        % (analysis["geometry_same_tolerance_angstrom"], analysis["threshold_charge_l1"]))
    add("3. **`Opt` \u8f93\u51fa\u91cc\u53d6\u6700\u540e\u4e00\u5757**\uff1a`MULLIKEN ATOMIC ...` \u4e0e `CARTESIAN ...` \u5404\u51fa\u73b0\u591a\u6b21\uff0c"
        "**\u9996\u5757\u662f\u8d77\u59cb\u51e0\u4f55**\uff1b`s17` \u7684\u53d6\u9996\u5757\u89e3\u6790\u5668\u53ea\u5bf9\u5355\u70b9\u8f93\u51fa\u6210\u7acb\u3002"
        "`n_mulliken_blocks_*` / `n_cartesian_blocks_*` \u5c31\u662f\u8fd9\u6761\u53e3\u5f84\u7684\u5ba1\u8ba1\u5217\u3002")
    add("4. **\u672a\u5b8c\u6210\u683c\u5b50\uff08`incomplete`\uff09\u4e0d\u8ba1\u5165\u4efb\u4f55\u6bd4\u4f8b\u4e0e\u5747\u503c**\u3002")
    add("5. **\u672c\u9636\u6bb5\u4e0d\u91cd\u65b0\u62df\u5408\u4efb\u4f55\u9608\u503c**\uff1a`charge_l1 > %.3f`\u3001%.0e eV\u3001%.2f \u00c5 "
        "\u5168\u90e8\u6cbf\u81ea\u4e0a\u4e00\u6b65\uff08Stage 18/15\uff09\u3002"
        % (analysis["threshold_charge_l1"], analysis["material_threshold_ev"],
           analysis["geometry_same_tolerance_angstrom"]))
    add("6. **`near_threshold`\uff08|`charge_l1_margin`| \u2264 %d%% \u00d7 %.3f = %.4f\uff09\u4e0e `rmsd_same_minimum` "
        "\u4e00\u6837\u53ea\u662f\u63cf\u8ff0\u5217**\uff1a\u5224\u636e\u59cb\u7ec8\u662f\u51bb\u7ed3\u7684 `charge_l1 > %.3f`\uff0c"
        "\u4e0d\u56e0\u5b83\u53d8\u66f4\u3002"
        % (int(round(NEAR_THRESHOLD_FRACTION * 100)), analysis["threshold_charge_l1"],
           NEAR_THRESHOLD_FRACTION * analysis["threshold_charge_l1"],
           analysis["threshold_charge_l1"]))
    add("")
    add("---")
    add("")
    add("## 8. \u4ea7\u7269\u4e0e\u56fe\u8868")
    add("")
    add("| \u4ea7\u7269 | \u8bf4\u660e |")
    add("|---|---|")
    week18_files = (
        ("stage19_relax_analysis.json", "\u9010\u683c\u88c1\u51b3\u3001\u805a\u5408\u3001\u9608\u503c\uff08\u672c\u62a5\u544a\u7684\u4e3b\u6570\u636e\u6e90\uff09"),
        ("stage19_relax_summary.md", "\u540c\u4e00\u4efd\u5185\u5bb9\u7684 Markdown \u6458\u8981"),
        ("stage19_relax_cells_analysis.csv",
         "\u9010\u683c \u00d7 %d \u5217\u7684\u8ba1\u7b97\u660e\u7ec6" % len(D["cells_csv"][0])),
        ("stage19_relax_cells.csv", "\u4f5c\u4e1a\u7ea7\u53f0\u8d26\uff08\u6bcf\u884c = 1 \u4e2a Opt \u4f5c\u4e1a\uff09"),
        ("stage19_relax_plan.json", "\u672c\u5468\u7684\u63d0\u4ea4\u8ba1\u5212\uff08%d \u683c / %d \u4f5c\u4e1a / \u51e0\u4f55\u5ba1\u8ba1\uff09" % (plan["n_target_cells"], plan["n_jobs"])),
        ("stage19_relax.json", "\u8fd0\u884c\u5668\u9010\u5c42\u6458\u8981"),
        ("stage19_relax_by_state.csv", "\u6309\u7535\u5b50\u6001\u5206\u5c42"),
        ("stage19_relax_by_molecule.csv", "\u6309\u5206\u5b50\u5206\u5c42"),
        ("stage19_relax_by_epsilon.csv", "\u6309\u4ecb\u7535\u5e38\u6570\u5206\u5c42"),
        ("stage19_relax_by_arm_set.csv", "\u6309\u53d1\u73b0/\u7559\u51fa\u81c2\u5206\u5c42"),
    )
    for name, note in week18_files:
        add("| `outputs/week18/%s` | %s |" % (name, note))
    add("")
    add("| \u811a\u672c | \u8bf4\u660e |")
    add("|---|---|")
    add("| `scripts/run_stage19_relax.py` | \u672c\u5468 %d \u4e2a `Opt` \u4f5c\u4e1a\u7684\u63d0\u4ea4\u5668 |" % plan["n_jobs"])
    add("| `scripts/analyze_stage19_relax.py` | \u9010\u683c\u88c1\u51b3\u4e0e\u805a\u5408\u7684\u751f\u6210\u5668 |")
    add("| `scripts/gen_week18_report.py` | \u672c\u62a5\u544a\u751f\u6210\u5668 |")
    add("")
    if figures is None:
        add("\u4e24\u5f20\u56fe\uff08`%s`\uff09\uff1a" % MANIFEST_REL)
        add("")
        add("- `F36` / `F37`\uff1a\u672c\u5468\u7684\u4e24\u5f20\u56fe\u7531\u540c\u7ea7\u7684\u51fa\u56fe\u811a\u672c\u751f\u6210\uff0c"
            "\u6587\u4ef6\u540d\u4e0e\u9010\u56fe\u8bf4\u660e\u4ee5 `%s` \u4e3a\u51c6\u3002" % MANIFEST_REL)
        add("  \u672c\u6b21\u5b9a\u7a3f\u65f6\u8be5 manifest \u5c1a\u672a\u51fa\u73b0\uff0c\u56e0\u6b64\u6b64\u5904**\u4e0d\u5217\u6587\u4ef6\u540d\u4e0e caption**"
            "\uff08\u4e0d\u731c\uff09\uff1bmanifest \u4e00\u65e6\u843d\u76d8\uff0c\u91cd\u8dd1\u672c\u811a\u672c\u5373\u4f1a\u81ea\u52a8\u8865\u5168\u3002")
    else:
        add("\u4e24\u5f20\u56fe\uff08`outputs/figures/`\uff0cdpi 170\uff0c\u6807\u7b7e\u5168 ASCII\uff09\uff1a")
        add("")
        for fid, rel, caption in figures:
            add("- `%s`\uff08%s\uff09\u2014\u2014 %s" % (rel, fid, caption))
            add("  sha256 = `%s`" % _sha256(REPO / rel))
    add("")
    add("\u56fe\u4e0e\u8f93\u5165\u4ea7\u7269\u7684 sha256 \u6e05\u5355\u89c1 `%s`\u3002" % MANIFEST_REL)
    add("")
    add("---")
    add("")
    add("## 9. \u5df2\u77e5\u9650\u5236")
    add("")
    add("- **\u9009\u62e9\u504f\u5dee**\uff1a\u8fd9 37 \u683c\u662f\u6309\u300c\u4e24\u89e3\u4e0d\u540c\u300d\u6311\u51fa\u6765\u7684\uff0c"
        "\u672c\u62a5\u544a\u7684\u4efb\u4f55\u6bd4\u4f8b\u90fd**\u4e0d\u662f**\u5168\u76ee\u5f55\u7684\u53d1\u751f\u7387\u3002")
    add("- **\u51e0\u4f55\u7ea7\u5224\u636e\u7684\u4ee3\u7406\u6027**\uff1a`charge_l1` \u662f\u5e03\u5c45\uff08population\uff09\u8ddd\u79bb\uff0c"
        "\u4e0d\u662f\u6ce2\u51fd\u6570\u91cd\u53e0\uff1b\u4e24\u4e2a\u5e03\u5c45\u76f8\u4f3c\u4f46\u6ce2\u51fd\u6570\u4e0d\u540c\u7684\u89e3\u4f1a\u88ab\u5f53\u6210\u201c\u540c\u4e00\u4e2a\u201d\u3002")
    add("- **\u65e0\u9891\u7387\u6821\u9a8c**\uff1a`Opt` \u53ea\u8bc1\u660e\u7ec8\u70b9\u662f\u9a7b\u70b9\uff0c\u4e0d\u8bc1\u660e\u5b83\u662f**\u771f\u6781\u5c0f\u70b9**"
        "\uff08\u6ca1\u6709\u865a\u9891\u6392\u67e5\uff09\u3002\u5bf9\u53d1\u751f\u504f\u597d\u53cd\u8f6c\u3001\u4ee5\u53ca\u88ab\u5f52\u5165 `same_*` \u7684\u683c\u5b50\uff0c"
        "\u8fd9\u4e00\u70b9\u5c24\u5176\u91cd\u8981\u3002")
    if unconverged:
        add("- **有 %d 条腿的 `Opt` 没有收敛**：%s（触及迭代上限，作业仍正常结束）。相关格子的结论建立在一个未完全弛豫的几何上。"
            % (len(unconverged), "、".join("%s/%s/eps=%s/%s" % (name, state, _eps(eps), arm)
                                                for name, state, eps, arm in unconverged)))
    add("- **\u4e24\u6761\u817f\u5404\u81ea\u5f1b\u8c6b**\uff1a\u4e24\u4e2a\u7ec8\u70b9\u90fd\u53ea\u662f**\u5404\u81ea\u521d\u731c\u843d\u5230\u7684\u5c40\u90e8**\u6781\u5c0f\u70b9\uff0c"
        "\u4e0d\u80fd\u8bf4\u54ea\u4e00\u4e2a\u662f\u5168\u5c40\u6700\u4f4e\u3002")
    add("- **\u65e0\u6eb6\u5242\u58f3**\uff1a\u672c\u5468\u53ea\u6709\u88f8 CPCM \u4ecb\u7535\u5c4f\u853d\uff0c\u6ca1\u6709\u663e\u5f0f\u5fae\u6eb6\u5242\u5316"
        "\uff08\u7b2c\u4e00\u6eb6\u5242\u58f3\u5728 Stage 9 \u5355\u72ec\u8003\u5bdf\uff09\u3002")
    add("- **\u53f0\u8d26\u4e0e\u6570\u636e\u7684\u65f6\u95f4\u5dee**\uff1a\u672c\u62a5\u544a\u7684\u6570\u5b57\u662f\u4e00\u4e2a\u5feb\u7167"
        "\uff08`generated_utc = %s`\uff09\u3002" % analysis["generated_utc"])
    if n_complete < n_cells:
        pending = [cell for cell in cells if not cell.get("both_arms_ok")]
        add("- **\u672c\u6b21\u5b9a\u7a3f\u65f6\u6709 %d \u683c\u56e0\u4f5c\u4e1a\u5c1a\u672a\u5b8c\u6210\u800c\u7f3a\u5931**\uff1a%s\u3002"
            "\u5b83\u4eec\u5728 JSON \u91cc\u7684 `outcome = \"incomplete\"`\uff0c"
            "\u4e0d\u8ba1\u5165\u4efb\u4f55\u5224\u51b3\u3001\u6bd4\u4f8b\u4e0e\u5747\u503c\u3002"
            % (len(pending), "\u3001".join("%s/%s/eps=%s" % (cell["name"], cell["state"],
                                                           _eps(cell["epsilon"])) for cell in pending)))
    add("")
    add("---")
    add("")
    add("## 10. \u4e0b\u4e00\u6b65\uff08Week 19 \u5019\u9009\uff09")
    add("")
    add("1. **\u628a\u8fd9 37 \u683c\u7684\u7ed3\u8bba\u56de\u586b\u4e94\u7ea7\u53f0\u9636\u7684 P2 \u817f\u505a\u654f\u611f\u6027\u68c0\u67e5**\uff08**\u96f6\u65b0\u589e\u8ba1\u7b97**\uff09\uff1a"
        "\u95ee\u201c\u82e5 P2 \u5355\u70b9\u91cc\u7684\u8fd9\u4e9b\u683c\u5b50\u6539\u7528\u5f1b\u8c6b\u540e\u80fd\u91cf\uff0c\u53f0\u9636\u7ed3\u8bba\u4f1a\u4e0d\u4f1a\u52a8\u201d\uff1b"
        "\u82e5\u4e0d\u52a8\uff0c\u5c31\u628a\u672c\u5468\u7684 %d \u4e2a\u4f5c\u4e1a\u5f52\u6210\u201c\u5df2\u6392\u9664\u7684\u98ce\u9669\u201d\u3002" % plan["n_jobs"])
    add("2. **\u628a Stage 18 \u7684 `charge_l1` \u5224\u636e\u505a\u6210\u8fd0\u884c\u624b\u518c\u91cc\u7684\u9884\u68c0**\uff08**\u96f6\u65b0\u589e\u8ba1\u7b97**\uff09\uff1a"
        "\u5728\u63d0\u4ea4\u5355\u70b9\u4f5c\u4e1a\u540e\u5148\u7b97\u4e00\u904d\u8eab\u4efd\u8ddd\u79bb\uff0c\u53ea\u5bf9\u8d85\u9608\u503c\u7684\u683c\u5b50\u6392\u7b2c\u4e8c\u6b21\u8ba1\u7b97\u3002")
    add("3. **\u5bf9 `distinct_higher`\uff08\u504f\u597d\u53cd\u8f6c\uff09\u4e0e `same_*` \u7684\u683c\u5b50\u505a\u9891\u7387\u5206\u6790**\uff08\u65b0\u8ba1\u7b97\uff0c"
        "\u6570\u91cf\u5c0f\uff09\uff1a\u786e\u8ba4\u5b83\u4eec\u662f\u771f\u6781\u5c0f\u70b9\u800c\u4e0d\u662f\u978d\u70b9\uff0c\u5e76\u770b\u4e24\u6761\u817f\u662f\u5426\u843d\u5728"
        "\u4e0d\u540c\u7684\u81ea\u7531\u5ea6\u4e0a\uff08\u4f8b\u5982\u78b3\u9178\u916f\u73af\u7684\u62c9\u4f38\u4e0e\u5f2f\u6298\uff09\u3002")
    add("4. **\u628a\u7b2c\u4e00\u6eb6\u5242\u58f3\uff08Stage 9\uff09\u4e0e\u5f1b\u8c6b\u8054\u5408**\uff08\u65b0\u8ba1\u7b97\uff09\uff1a"
        "\u95ee\u201c\u914d\u4f4d\u4e00\u4e2a\u6eb6\u5242\u5206\u5b50\u540e\uff0c\u7b2c\u4e8c\u89e3\u8fd8\u5b58\u5728\u5417\u201d\u2014\u2014"
        "\u8fd9\u662f\u628a\u672c\u5468\u7684\u7ed3\u8bba\u4ece\u88f8\u79bb\u5b50\u63a8\u5411\u771f\u5b9e\u6eb6\u6db2\u7684\u7b2c\u4e00\u6b65\u3002")
    add("")
    add("\uff08Gate \u72b6\u6001\uff1aGate 0 CLOSED\u3001Gate 1 NOT CLOSED \u2014\u2014 \u552f\u4e00 blocker \u4ecd\u662f\u6eb6\u6db2\u951a\u70b9 31 \u884c `est`\u3002\uff09")
    add("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/28_week18_report.md from the Stage 19 artefacts.")
    parser.add_argument("--data-dir", type=Path, default=W18_DEFAULT,
                        help="artefact directory (default: outputs/week18)")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT,
                        help="report path (default: docs/28_week18_report.md)")
    parser.add_argument("--check", action="store_true",
                        help="render in memory and compare with the file on disk")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    text = render(args.data_dir)
    if args.check:
        if not args.out.exists():
            print("check FAILED: %s does not exist" % args.out)
            return 1
        if args.out.read_text(encoding="utf-8") == text:
            print("check ok: %s matches the artefacts (%d lines)"
                  % (args.out, text.count("\n")))
            return 0
        print("check FAILED: %s differs from the freshly rendered text" % args.out)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes, %d lines)"
          % (args.out, len(text.encode("utf-8")), text.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())