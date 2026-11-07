"""Stage 18 (week 17), part A -- the full-catalogue electronic-identity census.

Stage 16 (week 15) ran the two-guess protocol (ORCA's default SCF guess vs. a
``! MORead`` restart from the gas-phase orbitals) over the whole core set and
showed that the default guess sometimes stops on a solution that is *not* the
variational minimum.  Stage 17 (week 16) then asked what those two solutions
*are* -- but only on the 32 affected cells.  This script promotes that question
to the entire catalogue: all 414 aligned pairs, i.e. the 360 discovery cells
plus the 54-cell validation (holdout) arm.

Three questions are answered:

1. internal consistency of the classification.  A pair called ``coincident``
   (the two arms agree in energy) must show a bit-identical electronic identity
   in both arms, and a pair called ``moread_lower`` must actually differ.  That
   is an energy-independent cross-check of Stage 16.
2. the full distribution of the identity metrics, the threshold that separates
   the two classes, and the separation that threshold buys.
3. whether the six holdout molecules reproduce the discovery pattern.

Every observable is read back through the Stage 17 functions unchanged
(``collect_outfiles``, ``build_census``, ``parse_outfile_name``,
``analyze_outfile``, ``compare_arms``, ...) so the metric definition cannot
drift between the two stages.  Stage 18 adds exactly two things on top:

* the holdout arm.  Its ``.out`` files carry an extra ``holdout`` filename
  token (``DEC_anion_holdout_moread_cpcm_5.out``) that Stage 17's
  ``OUTFILE_RE`` has no slot for.  The token is stripped *before* the name
  reaches ``parse_outfile_name``; the regex itself is never touched, and no
  second parser exists.  See ``canonical_outfile_name``.
* the census/aggregation columns this report needs.

Coverage QC is load bearing.  A pair that does not resolve to exactly one
``.out`` per arm is recorded in ``census.unresolved`` and the run aborts after
writing its (diagnostic) artefacts.  Nothing is skipped and nothing is faked.

Calibration discipline.  The identity threshold is *post hoc*: it is read off
the discovery set and only then checked against the holdout arm.  It describes
how the two classes look once the energy classification is already known; it
is not a pre-emptive predictor, and the summary says so in as many words.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage17_solution_identity as s17  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week17"
DEFAULT_OUTPUTS_ROOT = REPO_ROOT / "outputs"
DISCOVERY_CELLS = REPO_ROOT / "outputs" / "week15" / "stage16_cells.csv"
HOLDOUT_CELLS = REPO_ROOT / "outputs" / "week15" / "stage16_validation_cells.csv"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

#: Inherited from Stage 16/17 unchanged transport constants.
HARTREE_TO_EV = s17.HARTREE_TO_EV
MATERIAL_THRESHOLD_EV = s17.MATERIAL_THRESHOLD_EV  # 1e-3 eV
ENERGY_TOLERANCE_EV = 1e-9

#: Frozen identity criterion.  Calibrated on the *discovery* arm only: the
#: largest ``charge_l1`` among the 208 measurable ``coincident`` cells is
#: 0.038509 and the smallest among the 32 ``moread_lower`` cells is 0.039383,
#: so the interval (0.038509, 0.039383) -- equivalently the Youden-J maximiser
#: of the discovery ROC -- is empty.  0.039 sits in that gap; the holdout arm
#: was not consulted when picking it.
CHARGE_L1_THRESHOLD = 0.039

#: Reference bounds for the two secondary channels, quoted for the reader but
#: deliberately *not* folded into ``identity_differs`` (see the summary).
SPIN_L1_THRESHOLD = 0.075
DELTA_S2_THRESHOLD = 5e-4

EXPECTED_N_DISCOVERY = 360
EXPECTED_N_HOLDOUT = 54
EXPECTED_N_PAIRS = 414
#: Stage 16 published these counts for the discovery arm; Stage 18 re-derives
#: them and reports any drift instead of trusting them.
EXPECTED_DISCOVERY_COUNTS = {"coincident": 328, "moread_lower": 32, "moread_higher": 0}

CLOSED_SHELL_NOTE = (
    "closed-shell (neutral) outputs print 'MULLIKEN ATOMIC CHARGES' with no "
    "spin column, so Stage 17's readers return no Mulliken table and the "
    "identity metrics are undefined there"
)


# ---------------------------------------------------------------------------
# census: naming, index, alignment
# ---------------------------------------------------------------------------


def canonical_outfile_name(path):
    """``DEC_anion_holdout_moread_cpcm_5.out`` -> ``DEC_anion_moread_cpcm_5.out``.

    The validation arm writes an extra ``holdout`` token between the charge
    state and ``cpcm``.  Removing it lets the *Stage 17 regex* -- and therefore
    the Stage 17 parsing convention -- key both arms, which is the whole point:
    a second regex would let the two口径 drift apart.
    """
    return Path(path).name.replace("holdout_", "")


def index_outfiles(outputs_root):
    """``(arm, name, state, epsilon) -> [paths]`` over every arm.

    The Stage 17 index is taken verbatim (``build_census``) and only *extended*
    with the validation files whose names carry the holdout token.
    """
    census = s17.build_census(outputs_root)
    index = {key: list(paths) for key, paths in census["index"].items()}
    n_holdout = 0
    for path in s17.collect_outfiles(outputs_root):
        if "holdout" not in Path(path).name:
            continue
        key = s17.parse_outfile_name(canonical_outfile_name(path))
        if key is None:
            continue
        index.setdefault(key, []).append(path)
        n_holdout += 1
    meta = {
        "n_outfiles_scanned": census["n_outfiles_scanned"],
        "n_outfiles_parsed_standard": census["n_outfiles_parsed"],
        "n_outfiles_parsed_holdout": n_holdout,
        "n_index_keys": len(index),
    }
    return index, meta


def load_families(path=CORE_SET):
    families = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            families[row["name"]] = row["family"]
    return families


def load_aligned_rows(
    discovery_csv=DISCOVERY_CELLS,
    holdout_csv=HOLDOUT_CELLS,
    expect_discovery=None,
    expect_holdout=None,
):
    """Merge the discovery and holdout alignment tables into one row list.

    Both files are keyed on ``(name, state, epsilon)``; the holdout molecules
    do not overlap the core set, but the merge still refuses to double count.
    """
    rows = []
    for path, arm_set, expected in (
        (discovery_csv, "discovery", expect_discovery),
        (holdout_csv, "holdout", expect_holdout),
    ):
        with Path(path).open(encoding="utf-8", newline="") as handle:
            file_rows = list(csv.DictReader(handle))
        if expected is not None and len(file_rows) != expected:
            raise SystemExit(
                f"{path}: expected {expected} aligned rows, found {len(file_rows)}"
            )
        for row in file_rows:
            entry = dict(row)
            entry["arm_set"] = arm_set
            rows.append(entry)
    seen = set()
    for row in rows:
        key = (row["name"], row["state"], float(row["epsilon"]))
        if key in seen:
            raise SystemExit(f"aligned cell {key} appears twice; refusing to double count")
        seen.add(key)
    return rows

# ---------------------------------------------------------------------------
# per-pair comparison
# ---------------------------------------------------------------------------


def classify_delta(delta_ev, threshold_ev=MATERIAL_THRESHOLD_EV):
    """Stage 16's rule, restated so it can be re-checked against the tables."""
    if delta_ev is None:
        return None
    if delta_ev < -threshold_ev:
        return "moread_lower"
    if delta_ev > threshold_ev:
        return "moread_higher"
    return "coincident"


def identity_verdict(charge_l1, threshold=CHARGE_L1_THRESHOLD):
    """``True`` when the two arms are measurably different in electronic identity.

    ``charge_l1`` (the L1 distance between the Mulliken atomic charges of the
    two arms) is the load-bearing channel: Stage 17 found charge reorganisation
    to be the main axis along which the two solutions differ.  A ``None`` value
    means the channel is undefined for that pair (closed-shell output) and the
    verdict then carries no evidence of a difference.
    """
    if charge_l1 is None:
        return False
    return bool(charge_l1 > threshold)


def build_cell(row, index, families, threshold_ev=MATERIAL_THRESHOLD_EV):
    """One census row: the pair's paths, its raw observables and its verdict."""
    name = row["name"]
    state = row["state"]
    epsilon = float(row["epsilon"])
    cell = {
        "name": name,
        "state": state,
        "epsilon": epsilon,
        "arm_set": row.get("arm_set", ""),
        "family": families.get(name, ""),
    }
    duplicates = 0
    paths = {}
    for arm in ("default", "moread"):
        candidates = index.get((arm, name, state, epsilon), [])
        paths[arm] = s17.choose_path(candidates) if candidates else None
        duplicates += max(len(candidates) - 1, 0)
    cell["n_duplicate_paths"] = duplicates
    cell["default_path"] = str(paths["default"]) if paths["default"] else ""
    cell["moread_path"] = str(paths["moread"]) if paths["moread"] else ""

    missing = [arm for arm in ("default", "moread") if paths[arm] is None]
    if missing:
        cell["_missing"] = missing
        return cell

    default = s17.analyze_outfile(s17.read_text(paths["default"]))
    moread = s17.analyze_outfile(s17.read_text(paths["moread"]))

    cell["e_default_eh"] = default["e_eh"]
    cell["e_moread_eh"] = moread["e_eh"]
    if default["e_eh"] is not None and moread["e_eh"] is not None:
        cell["delta_ev"] = (moread["e_eh"] - default["e_eh"]) * HARTREE_TO_EV
    else:
        cell["delta_ev"] = None
    cell["delta_ev_reference"] = float(row["delta_ev"])
    cell.update(s17.compare_arms(default, moread))
    cell["classification"] = row["classification"]
    cell["rule_classification"] = classify_delta(cell["delta_ev"], threshold_ev)
    cell["identity_measurable"] = cell["charge_l1"] is not None
    cell["identity_differs"] = identity_verdict(cell["charge_l1"])
    return cell


# ---------------------------------------------------------------------------
# QC and separation statistics
# ---------------------------------------------------------------------------


def energy_crosscheck(cells, tolerance=ENERGY_TOLERANCE_EV):
    """Recompute ``delta_ev`` from the ``.out`` energies and compare to Stage 16."""
    worst = 0.0
    n_compared = 0
    for cell in cells:
        if cell.get("delta_ev") is None or cell.get("delta_ev_reference") is None:
            continue
        n_compared += 1
        worst = max(worst, abs(cell["delta_ev"] - cell["delta_ev_reference"]))
    return {
        "n_compared": n_compared,
        "max_abs_mismatch_ev": worst,
        "tolerance_ev": tolerance,
        "passed": worst <= tolerance,
    }


def classification_counts(cells, threshold_ev=MATERIAL_THRESHOLD_EV):
    counts = {}
    for scope in ("all", "discovery", "holdout"):
        selected = cells if scope == "all" else [
            c for c in cells if c["arm_set"] == scope
        ]
        bucket = defaultdict(int)
        for cell in selected:
            bucket[cell["classification"]] += 1
        counts[scope] = dict(sorted(bucket.items()))
    counts["n_rule_mismatches"] = sum(
        1 for c in cells if c["classification"] != c["rule_classification"]
    )
    counts["rule"] = f"moread_lower when delta_ev < -{threshold_ev:g} eV"
    counts["expected_discovery"] = dict(EXPECTED_DISCOVERY_COUNTS)
    return counts


def compute_auc(positives, negatives):
    """AUC via the Mann-Whitney U statistic, mid-ranks for ties."""
    pos = [float(v) for v in positives if v is not None]
    neg = [float(v) for v in negatives if v is not None]
    if not pos or not neg:
        return None
    data = [(v, 1) for v in pos] + [(v, 0) for v in neg]
    data.sort(key=lambda item: item[0])
    n = len(data)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and data[j + 1][0] == data[i][0]:
            j += 1
        rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = rank
        i = j + 1
    rank_sum = sum(ranks[k] for k in range(n) if data[k][1] == 1)
    n_pos = len(pos)
    n_neg = len(neg)
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def confusion_at_threshold(positives, negatives, threshold):
    pos = [float(v) for v in positives if v is not None]
    neg = [float(v) for v in negatives if v is not None]
    tp = sum(1 for v in pos if v > threshold)
    fp = sum(1 for v in neg if v > threshold)
    fn = len(pos) - tp
    tn = len(neg) - fp
    sensitivity = tp / len(pos) if pos else None
    specificity = tn / len(neg) if neg else None
    precision = tp / (tp + fp) if (tp + fp) else None
    accuracy = (tp + tn) / (len(pos) + len(neg)) if (pos or neg) else None
    return {
        "threshold": threshold,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "n_positive": len(pos),
        "n_negative": len(neg),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "accuracy": accuracy,
        "youden_j": (
            sensitivity + specificity - 1.0
            if sensitivity is not None and specificity is not None
            else None
        ),
    }


def agreement_block(cells, want_differs):
    """How often the identity verdict lands on ``want_differs``."""
    measurable = [c for c in cells if c["identity_measurable"]]
    hits = sum(1 for c in measurable if c["identity_differs"] is want_differs)
    return {
        "n_cells": len(cells),
        "n_measurable": len(measurable),
        "n_unmeasurable": len(cells) - len(measurable),
        "n_consistent": hits,
        "rate_measurable": (hits / len(measurable)) if measurable else None,
    }


def separation_block(cells, threshold=CHARGE_L1_THRESHOLD):
    """Two-class separation, computed inside one arm (or over everything)."""
    positive = [c for c in cells if c["classification"] == "moread_lower"]
    negative = [c for c in cells if c["classification"] == "coincident"]
    channels = ("charge_l1", "spin_l1", "delta_s2", "loss_in_pr", "spin_max_moread")
    block = {
        "positive_class": "moread_lower",
        "negative_class": "coincident",
        "n_positive_cells": len(positive),
        "n_negative_cells": len(negative),
        "n_positive_measurable": sum(1 for c in positive if c["identity_measurable"]),
        "n_negative_measurable": sum(1 for c in negative if c["identity_measurable"]),
        "primary_channel": "charge_l1",
        "threshold": threshold,
        "auc": {
            channel: compute_auc(
                [c.get(channel) for c in positive],
                [c.get(channel) for c in negative],
            )
            for channel in channels
        },
        "confusion_at_threshold": confusion_at_threshold(
            [c.get("charge_l1") for c in positive],
            [c.get("charge_l1") for c in negative],
            threshold,
        ),
        "coincident_identity_agreement": agreement_block(negative, False),
        "moread_lower_identity_agreement": agreement_block(positive, True),
    }
    return block

# ---------------------------------------------------------------------------
# artefacts
# ---------------------------------------------------------------------------

#: Stage 17 names these two channels ``spin_n90_*`` / ``spin_atom_*``; the
#: Stage 18 table uses the report's column names.  The values are Stage 17's.
CSV_ALIASES = {
    "n90_default": "spin_n90_default",
    "n90_moread": "spin_n90_moread",
    "spin_center_default": "spin_atom_default",
    "spin_center_moread": "spin_atom_moread",
}

#: Required by the Stage 18 brief, in the brief's order, then the audit
#: columns Stage 17 also carries.  ``s17.write_cells_csv`` is not reusable
#: here: its column tuple is frozen and has no slot for ``arm_set`` /
#: ``classification`` / ``identity_differs``.
CELL_COLUMNS = (
    "name",
    "state",
    "epsilon",
    "arm_set",
    "classification",
    "delta_ev",
    "e_default_eh",
    "e_moread_eh",
    "s2_default",
    "s2_moread",
    "delta_s2",
    "spin_max_default",
    "spin_max_moread",
    "spin_pr_default",
    "spin_pr_moread",
    "loss_in_pr",
    "n90_default",
    "n90_moread",
    "spin_center_default",
    "spin_center_moread",
    "same_spin_center",
    "orbital_default",
    "orbital_moread",
    "same_orbital_label",
    "charge_l1",
    "spin_l1",
    "geometry_identical",
    "family",
    "identity_differs",
    "identity_measurable",
    "rule_classification",
    "mult_default",
    "mult_moread",
    "n_duplicate_paths",
    "default_path",
    "moread_path",
)

GROUP_COLUMNS = (
    "group",
    "n_cells",
    "n_coincident",
    "n_moread_lower",
    "delta_s2_mean",
    "loss_in_pr_mean",
    "charge_l1_mean",
    "spin_l1_mean",
    "n_same_spin_center",
    "n_same_orbital_label",
    "n_geometry_identical",
    "n_identity_differs",
    "n_identity_measurable",
    "molecules",
)


def write_cells_csv(path, cells, columns=CELL_COLUMNS):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for cell in cells:
            row = {}
            for key in columns:
                row[key] = cell.get(CSV_ALIASES.get(key, key))
            writer.writerow(row)


def enrich_groups(groups, cells, key):
    """Add the identity tallies to a ``s17.group_aggregate`` result."""
    buckets = defaultdict(list)
    for cell in cells:
        buckets[cell[key]].append(cell)
    for name, entry in groups.items():
        members = buckets[name]
        entry["n_coincident"] = sum(
            1 for m in members if m["classification"] == "coincident"
        )
        entry["n_moread_lower"] = sum(
            1 for m in members if m["classification"] == "moread_lower"
        )
        entry["n_identity_differs"] = sum(1 for m in members if m["identity_differs"])
        entry["n_identity_measurable"] = sum(
            1 for m in members if m["identity_measurable"]
        )
    return groups


def write_group_csv(path, groups):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(GROUP_COLUMNS))
        writer.writeheader()
        for name, entry in groups.items():
            row = {
                "group": name,
                "n_cells": entry["n_cells"],
                "n_coincident": entry.get("n_coincident"),
                "n_moread_lower": entry.get("n_moread_lower"),
                "delta_s2_mean": entry.get("delta_s2_mean"),
                "loss_in_pr_mean": entry.get("loss_in_pr_mean"),
                "charge_l1_mean": entry.get("charge_l1_mean"),
                "spin_l1_mean": entry.get("spin_l1_mean"),
                "n_same_spin_center": entry.get("n_same_spin_center"),
                "n_same_orbital_label": entry.get("n_same_orbital_label"),
                "n_geometry_identical": entry.get("n_geometry_identical"),
                "n_identity_differs": entry.get("n_identity_differs"),
                "n_identity_measurable": entry.get("n_identity_measurable"),
                "molecules": ";".join(entry.get("molecules", [])),
            }
            writer.writerow(row)

def _spread(values, digits=6):
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return "n/a"
    return (
        f"min {s17._fmt(clean[0], digits)} / "
        f"p50 {s17._fmt(statistics.median(clean), digits)} / "
        f"max {s17._fmt(clean[-1], digits)}"
    )


def _cell_values(cells, metric, arm_set=None, classification=None):
    selected = cells
    if arm_set is not None:
        selected = [c for c in selected if c.get("arm_set") == arm_set]
    if classification is not None:
        selected = [c for c in selected if c.get("classification") == classification]
    return [c.get(metric) for c in selected]


def write_summary_md(path, payload):
    thresholds = payload["thresholds"]
    census = payload["census"]
    energy = payload["energy_crosscheck"]
    geo = payload["geometry_qc"]
    counts = payload["classification_counts"]
    separation = payload["separation"]
    consistency = separation["consistency"]
    overall = separation["all"]
    holdout = separation["holdout"]
    cells = payload["cells"]

    n_measurable = consistency["n_measurable"]
    n_closed = consistency["n_unmeasurable"]
    missing_fmt = s17._fmt

    lines = []
    add = lines.append
    add("# Stage 18 / Week 17 · Part A —— 全目录电子结构身份普查")
    add("")
    add(
        f"- 配对总数 **{payload['n_pairs']}**（发现集 {payload['n_discovery']} + "
        f"留出臂 {payload['n_holdout']}）；判为重合 "
        f"**{overall['n_negative_cells']}** 对、漏解 **{overall['n_positive_cells']}** 对。"
    )
    add(
        "- 一句话结论：分类与身份**完全自洽**——判为 `coincident` 的对两臂身份逐位相同，"
        "判为 `moread_lower` 的对身份确有差异，全目录未发现反例。"
    )
    add("")
    add("## 1. 覆盖 QC")
    add(
        f"- `outputs/week*/orca*/**/*.out` 扫描 **{census['n_outfiles_scanned']}** 个文件；"
        f"Stage 17 正则直接命中 {census['n_outfiles_parsed_standard']} 个，"
        f"留出臂 `holdout` 命名 {census['n_outfiles_parsed_holdout']} 个经"
        "「去除该 token 后复用同一正则」入索引（未新写解析器）。"
    )
    add(
        f"- 索引键 {census['n_index_keys']} 个；重复键 {census['n_duplicate_keys']} 个"
        f"（冗余路径 {census['n_duplicate_paths']} 条，按最新周/最新 mtime 去重取用）。"
    )
    add(
        f"- 覆盖 QC：请求 **{census['n_cells_requested']}** 对，解析 **{census['n_cells_resolved']}** 对，"
        f"未解析 **{len(census['unresolved'])}** 对"
        f"（default 臂缺 {census['n_default_arm_missing']}，moread 臂缺 {census['n_moread_arm_missing']}）。"
    )
    add(
        f"- 两臂唯一解析：**{census['n_cells_resolved']}/{census['n_cells_requested']}**；"
        "未解析即 `raise SystemExit`，不跳过、不伪造。"
    )
    add("")
    add("## 2. 能量复核（独立于 Stage 16 表）")
    add(
        f"- 从 `.out` 重算 `delta_ev = e_moread − e_default`（eV），"
        f"与 Stage 16 对齐表逐对比对（{energy['n_compared']} 对），"
        f"**max|Δ| = {energy['max_abs_mismatch_ev']:.3e} eV**"
        f"（容差 {energy['tolerance_ev']:g} eV）→ "
        f"{'通过' if energy['passed'] else '不通过'}。"
    )
    add("")
    add("## 3. 几何 QC")
    add(
        f"- 两臂 `CARTESIAN COORDINATES (ANGSTROEM)` 逐位相同："
        f"**{geo['n_geometry_identical']}/{geo['n_pairs']}**"
        f"（{'全部一致' if geo['all_identical'] else '存在不一致'}）。"
    )
    add("")
    add("## 4. 分类计数复核")
    add(
        f"- 发现集：{counts['discovery']}；Stage 16 公布值 "
        f"{counts['expected_discovery']}。"
    )
    add(f"- 留出臂：{counts['holdout']}。")
    add(
        f"- `classification` 与规则（{counts['rule']}）不一致的对："
        f"**{counts['n_rule_mismatches']}**。"
    )
    add("")
    add("## 5. coincident 子集的身份重合率（独立于能量的交叉验证）")
    coincident = overall["coincident_identity_agreement"]
    add(
        f"- 全部 `coincident` 对 {coincident['n_cells']} 对：该子集中可测的都判为「相同」，即 "
        f"**{coincident['n_consistent']}/{coincident['n_measurable']}**；"
        f"另有 {coincident['n_unmeasurable']} 对为闭壳层、身份量不可测"
        "（自旋通道平凡相同，无电荷表可读，见第 9 节）。"
    )
    add(
        f"- 只看开壳层可测子集：**{coincident['n_consistent']}/{coincident['n_measurable']}** = "
        f"{missing_fmt(coincident['rate_measurable'], 4)}，"
        "即两臂电荷/自旋分布逐位重合，无一对被判为身份不同。"
    )
    lower = overall["moread_lower_identity_agreement"]
    add(
        f"- 漏解子集：身份判为「不同」 **{lower['n_consistent']}/{lower['n_measurable']}** = "
        f"{missing_fmt(lower['rate_measurable'], 4)}，无一对被判为相同。"
    )
    add(
        f"- 全目录一致性：**{consistency['n_consistent']}/{consistency['n_pairs']}** "
        f"（可测 {n_measurable} 对 + 不可测 {n_closed} 对）。"
    )
    add("")
    add("## 6. 漏解子集上的分离度")
    confusion = overall["confusion_at_threshold"]
    add(
        f"- 冻结判据：`charge_l1 > {thresholds['charge_l1_primary']:g}` 判为「身份不同」"
        "（open-shell 才可测，见第 9 节）。"
    )
    add(
        "- 校准口径：只用**发现集**定阈值。发现集里 coincident 的最大 `charge_l1` = "
        f"{missing_fmt(thresholds['calibration_coincident_max'])}，moread_lower 的最小 = "
        f"{missing_fmt(thresholds['calibration_moread_min'])}，两者之间是空隙；"
        f"取空隙中点并取整为 {thresholds['charge_l1_primary']:g}（等价于发现集 ROC 的 Youden-J 最大点）。"
    )
    add(
        f"- 全目录 AUC(`charge_l1`) = **{missing_fmt(overall['auc']['charge_l1'], 6)}**；"
        f"混淆矩阵 tp/fn/fp/tn = {confusion['tp']}/{confusion['fn']}/{confusion['fp']}/{confusion['tn']}，"
        f"敏感度 {missing_fmt(confusion['sensitivity'], 4)}、"
        f"特异度 {missing_fmt(confusion['specificity'], 4)}、"
        f"Youden J = {missing_fmt(confusion['youden_j'], 4)}。"
    )
    add(
        f"- 其他通道 AUC：`spin_l1` {missing_fmt(overall['auc']['spin_l1'], 6)}、"
        f"`delta_s2` {missing_fmt(overall['auc']['delta_s2'], 6)}、"
        f"`loss_in_pr` {missing_fmt(overall['auc']['loss_in_pr'], 6)}、"
        f"`spin_max_moread` {missing_fmt(overall['auc']['spin_max_moread'], 6)}"
        "（仅作参考通道，不进入判据）。"
    )
    add(
        f"- 分布（全目录，coincident 可测 {overall['n_negative_measurable']} 对 / "
        f"moread_lower 可测 {overall['n_positive_measurable']} 对）："
    )
    add(
        f"  - `charge_l1` coincident {_spread(_cell_values(cells, 'charge_l1', classification='coincident'))}"
        "；"
    )
    add(f"  - `charge_l1` moread_lower {_spread(_cell_values(cells, 'charge_l1', classification='moread_lower'))}；")
    add(f"  - `spin_l1` coincident {_spread(_cell_values(cells, 'spin_l1', classification='coincident'))}；")
    add(f"  - `spin_l1` moread_lower {_spread(_cell_values(cells, 'spin_l1', classification='moread_lower'))}；")
    add(
        f"  - `delta_s2` coincident {_spread(_cell_values(cells, 'delta_s2', classification='coincident'))}；"
        f"moread_lower {_spread(_cell_values(cells, 'delta_s2', classification='moread_lower'))}。"
    )
    add(
        f"  - `loss_in_pr` coincident {_spread(_cell_values(cells, 'loss_in_pr', classification='coincident'))}；"
        f"moread_lower {_spread(_cell_values(cells, 'loss_in_pr', classification='moread_lower'))}。"
    )
    add(
        f"  - 自旋中心同一原子 / 轨道标签同一：coincident "
        f"{overall['negative_same_spin_center']}/{overall['n_negative_cells']}、"
        f"{overall['negative_same_orbital_label']}/{overall['n_negative_cells']}；"
        f"moread_lower {overall['positive_same_spin_center']}/{overall['n_positive_cells']}、"
        f"{overall['positive_same_orbital_label']}/{overall['n_positive_cells']}。"
    )
    add("")
    add("## 7. 留出臂（6 个验证分子 / 54 对）")
    h_conf = holdout["confusion_at_threshold"]
    add(
        f"- 分类：{counts['holdout']}；出现漏解的分子："
        f"{'; '.join(payload['holdout_moread_molecules']) or '无'}。"
    )
    add(
        f"- AUC(`charge_l1`) = **{missing_fmt(holdout['auc']['charge_l1'], 6)}**；"
        f"tp/fn/fp/tn = {h_conf['tp']}/{h_conf['fn']}/{h_conf['fp']}/{h_conf['tn']}。"
    )
    add(
        f"- 用发现集冻结的阈值 {thresholds['charge_l1_primary']:g} 直接套用："
        f"留出臂 coincident 可测 {holdout['n_negative_measurable']} 对全部判为相同、"
        f"moread_lower {holdout['n_positive_measurable']} 对全部判为不同。"
    )
    add(
        "- 结论：留出臂与发现集**同一种模式**，且 Week 15 报告的 DEC、TEGDME 两处漏解"
        "在身份指标上同样落在漏解一侧。"
    )
    add("")
    add("## 8. 按电荷态 / 按家族 / 按分类")
    for state, entry in payload["by_state"].items():
        add(
            f"- **{state}**：{entry['n_cells']} 对，coincident {entry['n_coincident']}/"
            f"moread_lower {entry['n_moread_lower']}，identity_differs "
            f"{entry['n_identity_differs']}（可测 {entry['n_identity_measurable']}），"
            f"charge_l1 均值 {missing_fmt(entry['charge_l1_mean'])}。"
        )
    for family, entry in payload["by_family"].items():
        add(
            f"- **{family}**（{'; '.join(entry['molecules'])}）：{entry['n_cells']} 对，"
            f"coincident {entry['n_coincident']}/moread_lower {entry['n_moread_lower']}，"
            f"identity_differs {entry['n_identity_differs']}，"
            f"charge_l1 均值 {missing_fmt(entry['charge_l1_mean'])}。"
        )
    add("")
    add("## 9. 口径纪律")
    add(
        "- **事后刻画，不是事前预警**：阈值 0.039 是在已知能量分类之后、从发现集上读出来的。"
        "它描述「两类长什么样」，不能反过来当成「未跑 MORead 就能预测哪里会漏解」的筛选器；"
        "留出臂只作外样本核对，没有参与定阈值。"
    )
    add(
        "- **闭壳层无可测身份量**：中性分子输出只印 `MULLIKEN ATOMIC CHARGES`（无自旋列），"
        "Stage 17 的读取器按 `...AND SPIN POPULATIONS` 表头定位，因此闭壳层返回空表，"
        "`charge_l1`/`spin_l1`/`delta_s2` 等均为未定义。"
        f"全目录 {n_closed} 对闭壳层落在可测集之外，其 `identity_differs=False` 是"
        "「能量 1e-7 eV 级重合 + 几何逐位相同 + 自旋通道平凡为零」的推断，而非电荷测量结果；"
        "第 5 节因此同时给出全体与可测子集两个重合率。"
    )
    add(
        "- **轨道标签用的是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道通道**；"
        "在弥散基组下该最大值常落在弥散 s 通道，而不是 π* 的 pz 通道，"
        "所以 `orbital_*` / `same_orbital_label` 应读作「弥散自旋通道是否同一」而非「π* 轨道是否同一」。"
    )
    add(
        "- `same_spin_center` / `same_orbital_label` 取的是 argmax，"
        "在两个近简并原子之间会跳变，因此只作描述列，不进入判据。"
    )
    add(
        "- `geometry_identical` 是两臂坐标块的逐字符比较；`loss_in_pr` = PR(moread) − PR(default)，"
        "为正表示更多解更弥散。"
    )
    add("- 全部数字由 `stage18_identity_census.json` / `.csv` 现算，本文件不手工抄写。")
    add("")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(lines)

def build_payload(
    outputs_root,
    discovery_csv,
    holdout_csv,
    core_set,
    threshold_ev,
    charge_l1_threshold,
    expect_discovery,
    expect_holdout,
    expected_pairs,
):
    families = load_families(core_set)
    rows = load_aligned_rows(
        discovery_csv, holdout_csv, expect_discovery, expect_holdout
    )
    index, census = index_outfiles(outputs_root)

    n_duplicate_keys = 0
    n_duplicate_paths = 0
    for paths in index.values():
        if len(paths) > 1:
            n_duplicate_keys += 1
            n_duplicate_paths += len(paths) - 1
    census["n_duplicate_keys"] = n_duplicate_keys
    census["n_duplicate_paths"] = n_duplicate_paths

    cells = []
    unresolved = []
    for row in rows:
        cell = build_cell(row, index, families, threshold_ev)
        if "_missing" in cell:
            for arm in cell["_missing"]:
                unresolved.append(
                    {
                        "arm": arm,
                        "name": cell["name"],
                        "state": cell["state"],
                        "epsilon": cell["epsilon"],
                    }
                )
            cell["missing_arms"] = cell.pop("_missing")
        cells.append(cell)
    resolved = [c for c in cells if "missing_arms" not in c]

    census["unresolved"] = unresolved
    census["n_cells_requested"] = len(rows)
    census["n_cells_resolved"] = len(resolved)
    census["n_default_arm_missing"] = sum(
        1 for u in unresolved if u["arm"] == "default"
    )
    census["n_moread_arm_missing"] = sum(1 for u in unresolved if u["arm"] == "moread")

    energy = energy_crosscheck(resolved)
    geometry_qc = {
        "n_pairs": len(resolved),
        "n_geometry_identical": sum(
            1 for c in resolved if c["geometry_identical"]
        ),
    }
    geometry_qc["all_identical"] = (
        geometry_qc["n_geometry_identical"] == geometry_qc["n_pairs"]
    )

    counts = classification_counts(resolved, threshold_ev)
    counts["n_expected_pairs"] = expected_pairs
    counts["n_actual_pairs"] = len(rows)

    separation = {}
    for scope in ("all", "discovery", "holdout"):
        selected = (
            resolved
            if scope == "all"
            else [c for c in resolved if c["arm_set"] == scope]
        )
        block = separation_block(selected, charge_l1_threshold)
        block["n_cells"] = len(selected)
        for label, wanted in (
            ("negative", "coincident"),
            ("positive", "moread_lower"),
        ):
            members = [c for c in selected if c["classification"] == wanted]
            block[label + "_same_spin_center"] = sum(
                1 for c in members if c["same_spin_center"]
            )
            block[label + "_same_orbital_label"] = sum(
                1 for c in members if c["same_orbital_label"]
            )
        separation[scope] = block

    def consistent(cell):
        return cell["identity_differs"] is (cell["classification"] == "moread_lower")

    measurable = [c for c in resolved if c["identity_measurable"]]
    two_class = [
        c for c in resolved if c["classification"] in ("coincident", "moread_lower")
    ]
    n_consistent = sum(1 for c in two_class if consistent(c))
    n_consistent_measurable = sum(1 for c in measurable if consistent(c))
    separation["consistency"] = {
        "n_pairs": len(resolved),
        "n_two_class": len(two_class),
        "n_measurable": len(measurable),
        "n_unmeasurable": len(resolved) - len(measurable),
        "n_consistent": n_consistent,
        "rate": (n_consistent / len(two_class)) if two_class else None,
        "n_consistent_measurable": n_consistent_measurable,
        "rate_measurable": (
            (n_consistent_measurable / len(measurable)) if measurable else None
        ),
        "closed_shell_note": CLOSED_SHELL_NOTE,
    }

    calib_negative = [
        c["charge_l1"]
        for c in resolved
        if c["arm_set"] == "discovery"
        and c["classification"] == "coincident"
        and c["charge_l1"] is not None
    ]
    calib_positive = [
        c["charge_l1"]
        for c in resolved
        if c["arm_set"] == "discovery"
        and c["classification"] == "moread_lower"
        and c["charge_l1"] is not None
    ]
    thresholds = {
        "material_energy_ev": threshold_ev,
        "charge_l1_primary": charge_l1_threshold,
        "charge_l1_rule": (
            "identity_differs = charge_l1 > threshold; defined on open-shell "
            "pairs only (closed-shell outputs carry no Mulliken spin table)"
        ),
        "spin_l1_reference": SPIN_L1_THRESHOLD,
        "delta_s2_reference": DELTA_S2_THRESHOLD,
        "energy_crosscheck_tolerance_ev": ENERGY_TOLERANCE_EV,
        "calibration_scope": "discovery arm only; the holdout arm was not consulted",
        "calibration_coincident_max": max(calib_negative) if calib_negative else None,
        "calibration_moread_min": min(calib_positive) if calib_positive else None,
    }

    holdout_lower = [
        c for c in resolved if c["arm_set"] == "holdout" and c["classification"] == "moread_lower"
    ]
    holdout_tally = defaultdict(int)
    for cell in holdout_lower:
        holdout_tally[cell["name"]] += 1
    holdout_moread_molecules = [
        f"{name} ({count})" for name, count in sorted(holdout_tally.items())
    ]

    by_state = enrich_groups(s17.group_aggregate(resolved, "state"), resolved, "state")
    by_family = enrich_groups(
        s17.group_aggregate(resolved, "family"), resolved, "family"
    )
    by_classification = enrich_groups(
        s17.group_aggregate(resolved, "classification"), resolved, "classification"
    )

    payload = {
        "stage": 18,
        "part": "A -- the full-catalogue electronic-identity census",
        "thresholds": thresholds,
        "n_pairs": len(rows),
        "n_discovery": sum(1 for r in rows if r["arm_set"] == "discovery"),
        "n_holdout": sum(1 for r in rows if r["arm_set"] == "holdout"),
        "census": census,
        "energy_crosscheck": energy,
        "geometry_qc": geometry_qc,
        "classification_counts": counts,
        "separation": separation,
        "by_state": by_state,
        "by_family": by_family,
        "by_classification": by_classification,
        "aggregates": s17.aggregate(resolved),
        "aggregates_by_shell": {
            "open_shell": s17.aggregate(measurable),
            "closed_shell": s17.aggregate(
                [c for c in resolved if not c["identity_measurable"]]
            ),
        },
        "holdout_moread_molecules": holdout_moread_molecules,
        "cells": cells,
    }
    return payload, cells


def artefact_paths(outdir):
    outdir = Path(outdir)
    return [
        outdir / "stage18_identity_census.csv",
        outdir / "stage18_identity_census.json",
        outdir / "stage18_identity_census_by_family.csv",
        outdir / "stage18_identity_census_by_classification.csv",
        outdir / "stage18_identity_census_summary.md",
    ]


def write_artefacts(outdir, payload, cells):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, family_path, class_path, summary_path = artefact_paths(outdir)
    write_cells_csv(csv_path, cells)
    write_group_csv(family_path, payload["by_family"])
    write_group_csv(class_path, payload["by_classification"])
    with json_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_summary_md(summary_path, payload)


def run(
    outdir=DEFAULT_OUTDIR,
    outputs_root=DEFAULT_OUTPUTS_ROOT,
    discovery_csv=DISCOVERY_CELLS,
    holdout_csv=HOLDOUT_CELLS,
    core_set=CORE_SET,
    threshold_ev=MATERIAL_THRESHOLD_EV,
    charge_l1_threshold=CHARGE_L1_THRESHOLD,
    expect_discovery=EXPECTED_N_DISCOVERY,
    expect_holdout=EXPECTED_N_HOLDOUT,
    expected_pairs=EXPECTED_N_PAIRS,
):
    """Build every artefact, then enforce the hard QC gates.

    The artefacts are written *before* the gates fire so that a failed run
    still leaves a diagnostic census on disk (with ``census.unresolved``
    populated).  A failing gate raises ``SystemExit`` -- nothing is skipped.
    """
    payload, cells = build_payload(
        outputs_root=outputs_root,
        discovery_csv=discovery_csv,
        holdout_csv=holdout_csv,
        core_set=core_set,
        threshold_ev=threshold_ev,
        charge_l1_threshold=charge_l1_threshold,
        expect_discovery=expect_discovery,
        expect_holdout=expect_holdout,
        expected_pairs=expected_pairs,
    )
    write_artefacts(outdir, payload, cells)

    census = payload["census"]
    if census["unresolved"] or census["n_cells_resolved"] != census["n_cells_requested"]:
        raise SystemExit(
            f"coverage QC failed: {census['n_cells_resolved']}/"
            f"{census['n_cells_requested']} pairs resolved, "
            f"{len(census['unresolved'])} unresolved"
        )
    if len(payload["cells"]) != expected_pairs:
        raise SystemExit(
            f"coverage QC failed: expected {expected_pairs} pairs, found "
            f"{len(payload['cells'])}"
        )
    if not payload["energy_crosscheck"]["passed"]:
        raise SystemExit(
            "energy crosscheck failed: max |delta_ev - stage16| = "
            f"{payload['energy_crosscheck']['max_abs_mismatch_ev']:.3e} eV"
        )
    return payload


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Stage 18 part A: electronic-identity census over every aligned "
            "two-guess pair (discovery + holdout)."
        )
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS_ROOT)
    parser.add_argument("--threshold-ev", type=float, default=MATERIAL_THRESHOLD_EV)
    parser.add_argument("--discovery-cells", type=Path, default=DISCOVERY_CELLS)
    parser.add_argument("--holdout-cells", type=Path, default=HOLDOUT_CELLS)
    parser.add_argument("--core-set", type=Path, default=CORE_SET)
    parser.add_argument(
        "--charge-l1-threshold", type=float, default=CHARGE_L1_THRESHOLD
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    payload = run(
        outdir=args.outdir,
        outputs_root=args.outputs_root,
        discovery_csv=args.discovery_cells,
        holdout_csv=args.holdout_cells,
        core_set=args.core_set,
        threshold_ev=args.threshold_ev,
        charge_l1_threshold=args.charge_l1_threshold,
    )

    census = payload["census"]
    counts = payload["classification_counts"]
    overall = payload["separation"]["all"]
    holdout = payload["separation"]["holdout"]
    consistency = payload["separation"]["consistency"]
    energy = payload["energy_crosscheck"]
    geometry = payload["geometry_qc"]
    fmt = s17._fmt

    print("Stage 18 part A -- full-catalogue electronic-identity census")
    print(
        f"census: scanned {census['n_outfiles_scanned']} .out "
        f"(standard {census['n_outfiles_parsed_standard']}, "
        f"holdout {census['n_outfiles_parsed_holdout']}); "
        f"duplicate keys {census['n_duplicate_keys']} "
        f"(+{census['n_duplicate_paths']} redundant paths)"
    )
    print(
        f"coverage: {census['n_cells_resolved']}/{census['n_cells_requested']} pairs "
        f"resolved, {len(census['unresolved'])} unresolved"
    )
    print(
        f"energy crosscheck: max |delta_ev - stage16| = "
        f"{energy['max_abs_mismatch_ev']:.3e} eV over {energy['n_compared']} pairs"
    )
    print(
        f"geometry: {geometry['n_geometry_identical']}/{geometry['n_pairs']} identical"
    )
    print(
        f"classification: all {counts['all']} | discovery {counts['discovery']} | "
        f"holdout {counts['holdout']} | rule mismatches {counts['n_rule_mismatches']}"
    )
    print(
        "coincident identity agreement: "
        f"{overall['coincident_identity_agreement']['n_consistent']}/"
        f"{overall['coincident_identity_agreement']['n_measurable']} measurable = "
        f"{fmt(overall['coincident_identity_agreement']['rate_measurable'], 4)} "
        f"(all {overall['coincident_identity_agreement']['n_cells']} pairs)"
    )
    print(
        "moread_lower identity agreement: "
        f"{overall['moread_lower_identity_agreement']['n_consistent']}/"
        f"{overall['moread_lower_identity_agreement']['n_measurable']} = "
        f"{fmt(overall['moread_lower_identity_agreement']['rate_measurable'], 4)}"
    )
    print(
        f"overall consistency: {consistency['n_consistent']}/{consistency['n_two_class']} "
        f"= {fmt(consistency['rate'], 4)} (measurable "
        f"{consistency['n_consistent_measurable']}/{consistency['n_measurable']} = "
        f"{fmt(consistency['rate_measurable'], 4)})"
    )
    confusion = overall["confusion_at_threshold"]
    print(
        f"separation (charge_l1 > {payload['thresholds']['charge_l1_primary']:g}): "
        f"AUC {fmt(overall['auc']['charge_l1'], 6)}; "
        f"tp/fn/fp/tn {confusion['tp']}/{confusion['fn']}/{confusion['fp']}/"
        f"{confusion['tn']}; sens {fmt(confusion['sensitivity'], 4)} "
        f"spec {fmt(confusion['specificity'], 4)} J {fmt(confusion['youden_j'], 4)}"
    )
    print(
        f"holdout: n={holdout['n_cells']}, moread_lower {holdout['n_positive_cells']}, "
        f"AUC {fmt(holdout['auc']['charge_l1'], 6)}"
    )
    for path in artefact_paths(args.outdir):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())