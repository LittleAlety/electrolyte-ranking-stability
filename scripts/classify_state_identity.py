"""C1 state-identity stratification: which reduced states may enter the ranking?

Why this module exists
----------------------
Week 5's ``outputs/week5/c1_decision_stability.json`` reports, for the C0 -> C1
(reduction) axis, ``tau_b = -0.467`` with ``f_robust_inv = 0``.  Read on its own
that looks like "Li+ coordination reorders the reduction ranking".  But the same
week's state-identity QC (``outputs/week5/c1_state_identity.csv``) shows that in
**11 of the 12** reduced cells the added electron sits on Li, not on the molecule
(``Li_centered_or_mixed_redox``).  Where the electron leaves the molecule, a
change in the numeric ranking is not ranking instability -- it is an
**observable-identity failure**: the two models are no longer ranking the same
observable.

R13 therefore stratifies the reduction axis (``config/scientific_definitions.yaml``
``axis_B_environment_states.C1.redox_state_identity_stratification``): only
``molecule_centered_redox`` states may enter the main reduction ranking; every
other label is reported separately as a mechanistic state-identity outcome.

This stage re-reads the two already-frozen Week-5 products, joins them, and
writes the stratified ranking plus the label buckets under
``outputs/state_identity/``.  It runs **no** new electronic structure.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking.decision_state import (  # noqa: E402
    DECISION_LABELS,
    decision_state_fractions,
    decision_state_matrix,
    resolution_curve,
)
from electrolyte_ranking.ranking import (  # noqa: E402
    kendall_tau_b,
    pair_differences,
    resolved_mask,
    spearman_rho,
)

WEEK5 = REPO_ROOT / "outputs" / "week5"
SHIFTS_CSV = WEEK5 / "c1_coord_shifts.csv"
IDENTITY_CSV = WEEK5 / "c1_state_identity.csv"
DECISION_JSON = WEEK5 / "c1_decision_stability.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "state_identity"

MAIN_RANKING_LABEL = "molecule_centered_redox"

#: Frozen label -> directory slug for the mechanistic-outcome buckets.
LABEL_SLUGS = {
    "molecule_centered_redox": "molecule_centered",
    "Li_centered_or_mixed_redox": "li_centered_or_mixed",
    "motif_switch": "state_switch",
    "no_intact_minimum_found": "no_intact_minimum",
    "dissociated_optimized_product": "dissociated",
    "state_identity_ambiguous": "ambiguous",
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stratify the C1 redox ranking by state identity.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def load_csv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def labels_by_cell(rows) -> dict:
    """(mol_id, motif_id) -> {'dication': label, 'reduced': label}."""

    table: dict = {}
    for row in rows:
        table.setdefault((row["mol_id"], row["motif_id"]), {})[row["redox_state"]] = row[
            "state_identity_label"
        ]
    return table


def primary_rows(shifts) -> list:
    return [row for row in shifts if row["is_primary"] == "True"]


def axis_values(rows, axis: str):
    """(C0 values, C1 values) for one redox axis on the given rows."""

    if axis == "reduction":
        return (
            [float(row["ea_c0_g2_ev"]) for row in rows],
            [float(row["ea_c1_ev"]) for row in rows],
        )
    return (
        [float(row["ip_c0_g2_ev"]) for row in rows],
        [float(row["ip_c1_ev"]) for row in rows],
    )


def ranking_block(rows, axis: str) -> dict:
    """tau_b / rho / f_unresolved for C0 -> C1 on the given rows."""

    names = [row["name"] for row in rows]
    block = {"n": len(rows), "n_pairs": len(rows) * (len(rows) - 1) // 2, "members": names}
    if len(rows) < 2:
        block.update(
            {
                "defined": False,
                "note": "fewer than two members: no pair can be ranked after stratification",
            }
        )
        return block
    c0, c1 = axis_values(rows, axis)
    block.update(
        {
            "defined": True,
            "kendall_tau_b": kendall_tau_b(c0, c1),
            "spearman_rho": spearman_rho(c0, c1),
        }
    )
    return block


def frozen_reduction_decision_states(decision: dict) -> dict:
    """Re-label every frozen C0 -> C1 reduction pair with the R13 vocabulary.

    The per-pair ``sigma_ev`` of ``c1_decision_stability.json`` is reused verbatim
    as the pair uncertainty of both models, so the classification is a pure
    re-read of frozen numbers.
    """

    pairs = decision["reduction"]["pair_differences"]
    names = sorted({pair["i"] for pair in pairs} | {pair["j"] for pair in pairs})
    index = {name: position for position, name in enumerate(names)}
    n = len(names)
    diff0 = [[0.0] * n for _ in range(n)]
    diff1 = [[0.0] * n for _ in range(n)]
    sigma = [[0.0] * n for _ in range(n)]
    for pair in pairs:
        i, j = index[pair["i"]], index[pair["j"]]
        diff0[i][j], diff0[j][i] = pair["d_p0_ev"], -pair["d_p0_ev"]
        diff1[i][j], diff1[j][i] = pair["d_p1_ev"], -pair["d_p1_ev"]
        sigma[i][j] = sigma[j][i] = pair["sigma_ev"]

    import numpy as np

    d0, d1, s = np.array(diff0), np.array(diff1), np.array(sigma)
    mask0 = resolved_mask(d0, s, z=1.0)
    mask1 = resolved_mask(d1, s, z=1.0)
    matrix = decision_state_matrix(d0, d1, mask0, mask1)
    fractions = decision_state_fractions(matrix)
    curve0 = resolution_curve(d0, s)
    curve1 = resolution_curve(d1, s)
    return {
        "members": names,
        "counts": {label: int(round(fractions.get(label, 0.0) * len(pairs))) for label in DECISION_LABELS},
        "fractions": {label: fractions.get(label, 0.0) for label in DECISION_LABELS},
        "n_pairs": len(pairs),
        "resolution_curve_p0": curve0,
        "resolution_curve_p1": curve1,
    }


def write_buckets(outdir: Path, labels: dict, shifts: dict) -> dict:
    """One directory per frozen state-identity label, listing its member cells."""

    buckets: dict = {}
    for (mol_id, motif_id), by_state in labels.items():
        for state, label in by_state.items():
            slug = LABEL_SLUGS.get(label)
            if slug is None:
                slug = "other"
            buckets.setdefault((slug, label), []).append(
                {
                    "mol_id": mol_id,
                    "name": shifts.get((mol_id, motif_id), {}).get("name", ""),
                    "family": shifts.get((mol_id, motif_id), {}).get("family", ""),
                    "motif_id": motif_id,
                    "redox_state": state,
                    "state_identity_label": label,
                }
            )

    summary = {}
    for (slug, label), members in sorted(buckets.items()):
        target = outdir / slug
        target.mkdir(parents=True, exist_ok=True)
        with (target / "members.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["mol_id", "name", "family", "motif_id", "redox_state", "state_identity_label"],
            )
            writer.writeheader()
            for member in sorted(members, key=lambda row: (row["redox_state"], row["mol_id"])):
                writer.writerow(member)
        summary[slug] = {"label": label, "n_members": len(members)}
    return summary


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    shifts = load_csv(SHIFTS_CSV)
    identity = load_csv(IDENTITY_CSV)
    decision = json.loads(DECISION_JSON.read_text(encoding="utf-8"))

    labels = labels_by_cell(identity)
    shift_index = {(row["mol_id"], row["motif_id"]): row for row in shifts}
    primary = primary_rows(shifts)

    # --- reduction axis: all states vs molecule-centered only ---------------
    red_primary = [row for row in primary if row["ea_c1_ev"]]
    red_molecule = [
        row
        for row in red_primary
        if labels.get((row["mol_id"], row["motif_id"]), {}).get("reduced") == MAIN_RANKING_LABEL
    ]
    ox_primary = [row for row in primary if row["ip_c1_ev"]]
    ox_molecule = [
        row
        for row in ox_primary
        if labels.get((row["mol_id"], row["motif_id"]), {}).get("dication") == MAIN_RANKING_LABEL
    ]

    reduction_all = ranking_block(red_primary, "reduction")
    reduction_stratified = ranking_block(red_molecule, "reduction")
    oxidation_all = ranking_block(ox_primary, "oxidation")
    oxidation_stratified = ranking_block(ox_molecule, "oxidation")

    frozen_states = frozen_reduction_decision_states(decision)
    buckets = write_buckets(outdir, labels, shift_index)

    payload = {
        "stage": "R13 C1 state-identity stratification",
        "definition": (
            "Only molecule_centered_redox states enter the main reduction ranking; every other "
            "state-identity label is reported separately as a mechanistic outcome "
            "(config/scientific_definitions.yaml axis_B_environment_states.C1."
            "redox_state_identity_stratification)."
        ),
        "main_ranking_label": MAIN_RANKING_LABEL,
        "label_counts_reduced": _count_labels(identity, "reduced"),
        "label_counts_dication": _count_labels(identity, "dication"),
        "reduction_all_states": reduction_all,
        "reduction_molecule_centered": reduction_stratified,
        "oxidation_all_states": oxidation_all,
        "oxidation_molecule_centered": oxidation_stratified,
        "frozen_reduction_decision_states": frozen_states,
        "buckets": buckets,
        "inputs": {
            "shifts": str(SHIFTS_CSV.relative_to(REPO_ROOT).as_posix()),
            "identity": str(IDENTITY_CSV.relative_to(REPO_ROOT).as_posix()),
            "decision_stability": str(DECISION_JSON.relative_to(REPO_ROOT).as_posix()),
        },
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    (outdir / "state_identity_stratification.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    _write_csv(outdir / "state_identity_stratification.csv", primary, labels)
    _write_report(outdir / "state_identity_summary.md", payload)
    print("state-identity stratification: reduction all n=%d tau_b=%s ; molecule-centered n=%d" % (
        reduction_all["n"],
        _fmt(reduction_all.get("kendall_tau_b")),
        reduction_stratified["n"],
    ))
    return 0


def _count_labels(identity, redox_state):
    counts: dict = {}
    for row in identity:
        if row["redox_state"] != redox_state:
            continue
        label = row["state_identity_label"]
        counts[label] = counts.get(label, 0) + 1
    return counts


def _fmt(value):
    return "n/a" if value is None else "%.3f" % value


def _write_csv(path: Path, primary, labels) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "name",
                "family",
                "motif_id",
                "reduction_label",
                "oxidation_label",
                "in_reduction_all",
                "in_reduction_molecule_centered",
            ]
        )
        for row in primary:
            cell = labels.get((row["mol_id"], row["motif_id"]), {})
            red = cell.get("reduced", "")
            writer.writerow(
                [
                    row["name"],
                    row["family"],
                    row["motif_id"],
                    red,
                    cell.get("dication", ""),
                    bool(row["ea_c1_ev"]),
                    red == MAIN_RANKING_LABEL,
                ]
            )


def _write_report(path: Path, payload) -> None:
    red_all = payload["reduction_all_states"]
    red_mol = payload["reduction_molecule_centered"]
    lines = [
        "# C1 还原轴 state-identity 分层（R13）",
        "",
        "> 本文件由 `scripts/classify_state_identity.py` 从已冻结的 Week-5 产物现算，不跑任何新 QM 计算。",
        "",
        "## 一句话结论",
        "",
        "- 全部主 motif 还原态：**n = %d**，C0→C1 Kendall **τ_b = %s**，f_robust_inv = 0。" % (
            red_all["n"],
            _fmt(red_all.get("kendall_tau_b")),
        ),
        "- 只用 `%s` 的还原态：**n = %d**，%s。" % (
            MAIN_RANKING_LABEL,
            red_mol["n"],
            "排序无定义（成员少于两个，配不成 pair）" if not red_mol["defined"] else "τ_b = " + _fmt(red_mol.get("kendall_tau_b")),
        ),
        "- 冻结标签计数（还原态）：`%s`。" % json.dumps(payload["label_counts_reduced"], ensure_ascii=False),
        "",
        "## 为什么必须分层",
        "",
        "12 个还原态里 %d 个外加电子落在 Li 上（`Li_centered_or_mixed_redox`）。电子一旦离开分子，"
        % payload["label_counts_reduced"].get("Li_centered_or_mixed_redox", 0),
        "数值 ranking 的变化就不再是「同一 observable 的排序不稳定」，而是 **observable identity failure**。",
        "因此主还原 ranking 只接受 `%s`，其余标签一律作为 mechanistic state-identity outcome 单独统计。"
        % MAIN_RANKING_LABEL,
        "",
        "## 分层结果",
        "",
        "| 轴 | 集合 | n | n_pairs | τ_b | ρ | 说明 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for axis, all_block, mol_block in (
        ("reduction", red_all, red_mol),
        ("oxidation", payload["oxidation_all_states"], payload["oxidation_molecule_centered"]),
    ):
        lines.append(
            "| %s | all states | %d | %d | %s | %s | %s |"
            % (
                axis,
                all_block["n"],
                all_block["n_pairs"],
                _fmt(all_block.get("kendall_tau_b")),
                _fmt(all_block.get("spearman_rho")),
                "可排名" if all_block["defined"] else "无定义",
            )
        )
        lines.append(
            "| %s | molecule-centered | %d | %d | %s | %s | %s |"
            % (
                axis,
                mol_block["n"],
                mol_block["n_pairs"],
                _fmt(mol_block.get("kendall_tau_b")),
                _fmt(mol_block.get("spearman_rho")),
                "可排名" if mol_block["defined"] else "**无定义（成员 < 2）**",
            )
        )
    lines += [
        "",
        "## 冻结还原对的三态重标注",
        "",
        "| 状态 | n | 占比 |",
        "| --- | --- | --- |",
    ]
    for label in DECISION_LABELS:
        lines.append(
            "| %s | %d/%d | %.3f |"
            % (
                label,
                payload["frozen_reduction_decision_states"]["counts"].get(label, 0),
                payload["frozen_reduction_decision_states"]["n_pairs"],
                payload["frozen_reduction_decision_states"]["fractions"].get(label, 0.0),
            )
        )
    lines += [
        "",
        "> 还原轴 tau_b = -0.467 的「表面翻转」由 UNRESOLVED 主导（f_unresolved = 0.8），robust inversion = 0；",
        "> 再叠加 state-identity 分层后，只有分子中心还原的态才有资格进入排序，而这类态在本 core set 里只剩 1 个。",
        "",
        "## 桶目录",
        "",
    ]
    for slug, info in sorted(payload["buckets"].items()):
        lines.append("- `outputs/state_identity/%s/members.csv` —— %s（%d 行）" % (slug, info["label"], info["n_members"]))
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
