"""Stage 2 / P0 -> P1 analysis: which changes move a number, which move a decision.

Why this module exists
----------------------
The project question (v2 section 22.2) is not "how accurate is the cheap proxy"
but "does the cheap proxy support the same *material decision*". Those two are
different: a method change can shift every value by a large, nearly constant
amount and leave the ordering -- and therefore the shortlist -- completely
intact, or it can shift almost nothing on average and still swap two molecules
across the decision boundary.

This module turns the T1 sweep (outputs/week4/p1_core_set.csv) into that
statement by holding everything except the electronic-structure method fixed:

* value comparison -- every arm (P0 Koopmans -eps_HOMO, the GFN2-xTB Delta-SCF
  arm from the method audit, the r2SCAN-3c arm) against the curated gas-phase
  anchors, reported as MAE / bias / spread *and* as rank agreement
  (Kendall tau_b, Spearman rho);
* decision comparison -- the P0 and P1 orderings against each other: Top-k
  overlap O_k, Jaccard J_k, selection regret, Kendall tau_b, and the
  uncertainty-aware f_unresolved / f_robust_inv, with the pair uncertainty taken
  from the method spread itself (two realisations: P0 and P1). That is the
  honest internal estimate -- it needs no external reference.

Oxidation and reduction are reported separately and never merged: they are
controlled by different orbitals and, as this analysis shows, they behave very
differently under the method change.

Outputs
-------
outputs/week4/p1_core_set_derived.csv        one row per molecule, all arms
outputs/week4/p1_anchor_comparison.json      value + rank comparison per arm
outputs/week4/p1_decision_stability.json/md  the decision numbers
outputs/figures/F4..F7*.png                  the figures (English labels)
outputs/figures/figure_manifest_week4.md     figure -> input digests
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking, uncertainty  # noqa: E402

HARTREE_TO_EV = 27.211386245988
Z_PRIMARY = 1.0    # config/prereg.yaml: pair_comparison.z_factor.value (frozen)
Z_SENSITIVITY = 1.96  # conservative 95% two-sided band, reported alongside
TOP_K_FRACTIONS = (0.10, 0.20, 0.30)

#: Frozen in config/prereg.yaml (uncertainty.bootstrap). Twenty seeds x 2000
#: paired resamples, percentile interval; the reported interval is the median of
#: the twenty lower/upper bounds, so the result does not depend on one lucky seed.
BOOTSTRAP_REPETITIONS = 2000
BOOTSTRAP_ALPHA = 0.05
BOOTSTRAP_SEEDS = (101, 211, 307, 401, 503, 601, 701, 809, 907, 1009,
                   1103, 1201, 1301, 1409, 1511, 1601, 1709, 1801, 1901, 2003)


def tau_b_interval(a, b):
    """Prereg-compliant bootstrap interval for Kendall tau_b (v2 section 9.3).

    With 10-18 molecules a single tau_b is a noisy number, so every tau_b in this
    report is quoted with its interval; an interval that contains 0 means the
    ranking agreement is not established at all.
    """

    if len(a) < 3:
        return None
    lows, highs = [], []
    for seed in BOOTSTRAP_SEEDS:
        low, high = uncertainty.bootstrap_tau_b_ci(
            a, b, BOOTSTRAP_REPETITIONS, seed, BOOTSTRAP_ALPHA
        )
        lows.append(low)
        highs.append(high)
    return [float(statistics.median(lows)), float(statistics.median(highs))]

P1_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
P0_CSV = REPO_ROOT / "outputs" / "week3" / "p0_core_set.csv"
XTB_CSV = REPO_ROOT / "outputs" / "week2" / "method_audit_xtb.csv"
ANCHOR_CSV = REPO_ROOT / "data" / "anchors" / "gas_phase_anchors.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_FIGDIR = REPO_ROOT / "outputs" / "figures"

DERIVED_COLUMNS = [
    "mol_id", "name", "family", "role", "status", "geometry_source",
    "ip_koopmans_ev", "ip_xtb_dscf_ev", "ip_r2scan3c_ev",
    "ea_koopmans_ev", "ea_xtb_dscf_ev", "ea_r2scan3c_ev", "ea_r2scan3c_bound",
    "ox_shift_ev", "ea_shift_ev",
    "p0_ox_ev", "p0_red_ev", "p1_ox_ev", "p1_red_ev",
    "anchor_ip_ev", "anchor_ip_uncertainty_ev", "anchor_ip_source",
    "ip_err_p0_ev", "ip_err_xtb_dscf_ev", "ip_err_p1_ev",
    "qc_flags",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="P0 -> P1 value/decision analysis for the core set.")
    parser.add_argument("--p1", type=Path, default=P1_CSV)
    parser.add_argument("--p0", type=Path, default=P0_CSV)
    parser.add_argument("--xtb", type=Path, default=XTB_CSV)
    parser.add_argument("--anchors", type=Path, default=ANCHOR_CSV)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--figdir", type=Path, default=DEFAULT_FIGDIR)
    return parser.parse_args(argv)


def _float(value):
    text = ("" if value is None else str(value)).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_p1(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[(row["name"], row["state"])] = row
    return out


def load_by_name(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            # p0_core_set.csv carries both mol_id (C01...) and name (EC...);
            # method_audit_xtb.csv only carries mol_id, which holds the name there.
            key = (row.get("name") or row.get("mol_id") or "").strip()
            if key:
                out[key] = row
    return out


def load_anchors(path: Path) -> dict:
    """Primary anchor per (species, property), plus the spread across determinations.

    The primary determination is the experimental one with the smallest stated
    uncertainty. The spread over every determination that carries a value is kept
    as well, because it is itself an uncertainty source (v2 section 7.1) and must
    not be hidden by quietly picking a convenient number.
    """

    grouped = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if _float(row.get("value_eV")) is None:
                continue
            grouped.setdefault((row["species"], row["property"]), []).append(row)

    out = {}
    for key, rows in grouped.items():
        ordered = sorted(
            rows,
            key=lambda r: (
                0 if r.get("method") == "exp" else 1,
                _float(r.get("uncertainty_eV")) if _float(r.get("uncertainty_eV")) is not None else 1e9,
            ),
        )
        primary = ordered[0]
        values = [_float(r["value_eV"]) for r in rows]
        out[key] = {
            "value_eV": _float(primary["value_eV"]),
            "uncertainty_eV": _float(primary.get("uncertainty_eV")),
            "method": primary.get("method", ""),
            "source_type": primary.get("source_type", ""),
            "n_determinations": len(rows),
            "spread_eV": (max(values) - min(values)) if len(values) > 1 else 0.0,
        }
    return out

def build_derived(p1, p0, xtb, anchors) -> list:
    """One row per molecule, with every arm on the same footing.

    The P1 ranking keys are oriented exactly like the frozen P0 ones: both are
    "maximise = more stable", i.e. harder to oxidise (p_ox) and harder to reduce
    (p_red). p0_red = +eps_LUMO is -EA_Koopmans in disguise, so its P1 twin is
    -EA_r2SCAN-3c, not EA itself; writing that out is what makes the two
    reduction rankings comparable at all.
    """

    by_name = {}
    for (name, _state), row in p1.items():
        by_name.setdefault(name, row)

    rows = []
    for name, state_row in sorted(by_name.items(), key=lambda item: item[1]["mol_id"]):
        neutral = p1.get((name, "neutral"))
        cation = p1.get((name, "cation"))
        anion = p1.get((name, "anion"))

        def energy(record):
            if record is None or record.get("status") != "ok":
                return None
            return _float(record.get("final_energy_eh"))

        e_neutral = energy(neutral)
        e_cation = energy(cation)
        e_anion = energy(anion)

        ip_p1 = None if (e_neutral is None or e_cation is None) else (e_cation - e_neutral) * HARTREE_TO_EV
        ea_p1 = None if (e_neutral is None or e_anion is None) else (e_neutral - e_anion) * HARTREE_TO_EV

        base = p0.get(name, {})
        p0_ox = _float(base.get("p0_ox_ev"))
        p0_red = _float(base.get("p0_red_ev"))
        ea_koopmans = None if p0_red is None else -p0_red

        xtb_row = xtb.get(name, {})
        ip_xtb = _float(xtb_row.get("vertical_ip_ev"))
        ea_xtb = _float(xtb_row.get("vertical_ea_ev"))
        if str(xtb_row.get("unbound_anion", "")).strip().lower() == "true":
            # An unbound anion has no electron affinity; the audit records the
            # numeric Delta-SCF difference anyway, so it is dropped here rather
            # than reported as if it were a binding energy (v2 section 7.3).
            ea_xtb = None

        anchor = anchors.get((name, "IP"))
        anchor_ip = None if anchor is None else anchor["value_eV"]

        rows.append({
            "mol_id": state_row.get("mol_id", ""),
            "name": name,
            "family": state_row.get("family", ""),
            "role": state_row.get("role", ""),
            "status": state_row.get("status", ""),
            "geometry_source": state_row.get("geometry_source", ""),
            "ip_koopmans_ev": p0_ox,
            "ip_xtb_dscf_ev": ip_xtb,
            "ip_r2scan3c_ev": ip_p1,
            "ea_koopmans_ev": ea_koopmans,
            "ea_xtb_dscf_ev": ea_xtb,
            "ea_r2scan3c_ev": ea_p1,
            "ea_r2scan3c_bound": None if ea_p1 is None else bool(ea_p1 > 0.0),
            "ox_shift_ev": None if (ip_p1 is None or p0_ox is None) else ip_p1 - p0_ox,
            "ea_shift_ev": None if (ea_p1 is None or ea_koopmans is None) else ea_p1 - ea_koopmans,
            "p0_ox_ev": p0_ox,
            "p0_red_ev": p0_red,
            "p1_ox_ev": ip_p1,
            "p1_red_ev": None if ea_p1 is None else -ea_p1,
            "anchor_ip_ev": anchor_ip,
            "anchor_ip_uncertainty_ev": None if anchor is None else anchor["uncertainty_eV"],
            "anchor_ip_source": "" if anchor is None else anchor["method"],
            "ip_err_p0_ev": None if (p0_ox is None or anchor_ip is None) else p0_ox - anchor_ip,
            "ip_err_xtb_dscf_ev": None if (ip_xtb is None or anchor_ip is None) else ip_xtb - anchor_ip,
            "ip_err_p1_ev": None if (ip_p1 is None or anchor_ip is None) else ip_p1 - anchor_ip,
            "qc_flags": ";".join(sorted({
                flag
                for record in (neutral, cation, anion)
                if record is not None
                for flag in (record.get("qc_flags") or "").split(";")
                if flag
            })),
        })
    return rows



def shift_by_family(derived) -> list:
    """The P0 -> P1 shift, grouped by chemical family.

    The shift is not one constant: it is a chemical-structure effect. This table
    is what turns "the cheap proxy is offset" into "the cheap proxy is offset
    *here*", which is the part a chemist can act on.
    """

    groups = {}
    for row in derived:
        groups.setdefault(row["family"], []).append(row)
    table = []
    for family, rows in sorted(groups.items()):
        ox = [row["ox_shift_ev"] for row in rows if row["ox_shift_ev"] is not None]
        ea = [row["ea_shift_ev"] for row in rows if row["ea_shift_ev"] is not None]
        p0 = [row["ip_koopmans_ev"] for row in rows if row["ip_koopmans_ev"] is not None]
        p1 = [row["ip_r2scan3c_ev"] for row in rows if row["ip_r2scan3c_ev"] is not None]
        table.append({
            "family": family,
            "n": len(rows),
            "members": [row["name"] for row in rows],
            "ox_shift_mean_ev": statistics.fmean(ox) if ox else None,
            "ox_shift_std_ev": statistics.pstdev(ox) if len(ox) > 1 else None,
            "ox_shift_min_ev": min(ox) if ox else None,
            "ox_shift_max_ev": max(ox) if ox else None,
            "ea_shift_mean_ev": statistics.fmean(ea) if ea else None,
            "ip_p0_mean_ev": statistics.fmean(p0) if p0 else None,
            "ip_p1_mean_ev": statistics.fmean(p1) if p1 else None,
        })
    table.sort(key=lambda item: item["ox_shift_mean_ev"] if item["ox_shift_mean_ev"] is not None else 0.0)
    return table


def compare_arm(computed: list, reference: list, labels=None) -> dict:
    """Value error and rank error of one arm against the external anchors.

    Reporting both is the point: an arm can be badly wrong in absolute terms
    (large MAE) and still preserve the ordering (tau_b near 1), which is exactly
    the case v2 section 22.2 asks about.
    """

    pairs = [(c, r) for c, r in zip(computed, reference) if c is not None and r is not None]
    if not pairs:
        return {"n": 0}
    if labels is not None:
        labels = [label for label, c, r in zip(labels, computed, reference) if c is not None and r is not None]
    errors = [c - r for c, r in pairs]
    result = {
        "n": len(pairs),
        "mae_ev": sum(abs(e) for e in errors) / len(errors),
        "bias_ev": statistics.fmean(errors),
        "max_abs_error_ev": max(abs(e) for e in errors),
        "error_std_ev": statistics.pstdev(errors) if len(errors) > 1 else 0.0,
        "kendall_tau_b": None,
        "spearman_rho": None,
        "pairs": [
            {
                "mol_id": labels[index] if labels is not None else None,
                "computed_ev": c,
                "anchor_ev": r,
                "error_ev": c - r,
            }
            for index, (c, r) in enumerate(pairs)
        ],
    }
    if len(pairs) >= 2:
        values = [c for c, _ in pairs]
        refs = [r for _, r in pairs]
        result["kendall_tau_b"] = ranking.kendall_tau_b(values, refs)
        result["spearman_rho"] = ranking.spearman_rho(values, refs)
        result["kendall_tau_b_ci95"] = tau_b_interval(values, refs)
    return result


def layer_stability(p0_values, p1_values, labels, *, higher_is_better=True) -> dict:
    """Compare two layers on one axis: do they support the same decision?

    The pair uncertainty sigma_ij comes from the method spread itself, using the
    two layers as two realisations. With two realisations that is
    |dP0_ij - dP1_ij| / sqrt(2): an internal, reference-free estimate of how
    method-dependent each pair ordering is, which is what the resolved/unresolved
    test of v2 section 9.1 needs.
    """

    paired = [
        (a, b, label)
        for a, b, label in zip(p0_values, p1_values, labels)
        if a is not None and b is not None
    ]
    if len(paired) < 2:
        return {"n": len(paired)}
    a_vals = [a for a, _, _ in paired]
    b_vals = [b for _, b, _ in paired]
    n = len(paired)

    sigma = uncertainty.quantify_method_sigma([a_vals, b_vals], ddof=1, stat="std")
    diff_p0 = ranking.pair_differences(a_vals)
    diff_p1 = ranking.pair_differences(b_vals)
    # Primary decision criterion is the frozen preregistered z (config/prereg.yaml:
    # pair_comparison.z_factor.value = 1.0). The conservative 95% two-sided band
    # (z = 1.96) is computed alongside and reported as a sensitivity column.
    mask_p0 = ranking.resolved_mask(diff_p0, sigma, z=Z_PRIMARY)
    mask_p1 = ranking.resolved_mask(diff_p1, sigma, z=Z_PRIMARY)
    mask_p0_z1p96 = ranking.resolved_mask(diff_p0, sigma, z=Z_SENSITIVITY)
    mask_p1_z1p96 = ranking.resolved_mask(diff_p1, sigma, z=Z_SENSITIVITY)

    per_k = {}
    for fraction in TOP_K_FRACTIONS:
        k = max(1, round(fraction * n))
        per_k["k=%.2f" % fraction] = {
            "k": k,
            "overlap": ranking.top_k_overlap(a_vals, b_vals, k, higher_is_better=higher_is_better),
            "jaccard": ranking.jaccard_at_k(a_vals, b_vals, k, higher_is_better=higher_is_better),
            "selection_regret": ranking.selection_regret(b_vals, a_vals, k, higher_is_better=higher_is_better),
        }

    pair_rows = []
    for i in range(n):
        for j in range(n):
            if i < j:
                pair_rows.append({
                    "i": labels[i],
                    "j": labels[j],
                    "d_p0_ev": float(diff_p0[i, j]),
                    "d_p1_ev": float(diff_p1[i, j]),
                    "sigma_ev": float(sigma[i, j]),
                })
    pair_rows.sort(key=lambda item: item["d_p1_ev"])

    off_diagonal = [abs(v) for v in sigma.ravel() if v]
    return {
        "n": n,
        "higher_is_better": higher_is_better,
        "kendall_tau_b": ranking.kendall_tau_b(a_vals, b_vals),
        "kendall_tau_b_ci95": tau_b_interval(a_vals, b_vals),
        "spearman_rho": ranking.spearman_rho(a_vals, b_vals),
        "z_primary": Z_PRIMARY,
        "z_sensitivity": Z_SENSITIVITY,
        "f_unresolved_p0": ranking.unresolved_pair_fraction(mask_p0),
        "f_unresolved_p1": ranking.unresolved_pair_fraction(mask_p1),
        "f_robust_inv": ranking.robust_inversion_fraction(diff_p0, diff_p1, mask_p0, mask_p1),
        "f_unresolved_p0_z1p96": ranking.unresolved_pair_fraction(mask_p0_z1p96),
        "f_unresolved_p1_z1p96": ranking.unresolved_pair_fraction(mask_p1_z1p96),
        "f_robust_inv_z1p96": ranking.robust_inversion_fraction(diff_p0, diff_p1, mask_p0_z1p96, mask_p1_z1p96),
        "sigma_median_ev": float(statistics.median(off_diagonal)) if off_diagonal else None,
        "top_k": per_k,
        "pair_differences": pair_rows,
    }

def _ranks(values, labels, higher_is_better=True):
    """Competition ranking (1 = best), skipping molecules with a missing value."""

    pairs = [(v, label) for v, label in zip(values, labels) if v is not None]
    pairs.sort(key=lambda item: item[0], reverse=higher_is_better)
    return {label: index + 1 for index, (_, label) in enumerate(pairs)}


def _bump_panel(axis, labels, rank_p0, rank_p1, title, ylabel, fraction=0.20):
    """P0 -> P1 rank migration with the shortlist boundary drawn on it."""

    k_cut = max(1, round(fraction * len(labels)))
    for label in labels:
        crosses = (rank_p0[label] <= k_cut) != (rank_p1[label] <= k_cut)
        axis.plot(
            [0, 1],
            [rank_p0[label], rank_p1[label]],
            "-o",
            color="#b91c1c" if crosses else "#9ca3af",
            linewidth=2.2 if crosses else 1.0,
            markersize=5,
            alpha=0.95 if crosses else 0.6,
        )
        axis.text(-0.03, rank_p0[label], label, ha="right", va="center", fontsize=8)
        axis.text(1.03, rank_p1[label], label, ha="left", va="center", fontsize=8)
    axis.axhline(k_cut + 0.5, color="#111827", linestyle="--", linewidth=1.0)
    axis.text(
        0.5, k_cut + 0.8, "Top-%d (%.0f%%) shortlist boundary" % (k_cut, fraction * 100),
        ha="center", fontsize=8, color="#111827",
    )
    axis.set_xticks([0, 1])
    axis.set_xticklabels(["P0 (GFN2-xTB)", "P1 (r2SCAN-3c)"])
    axis.set_xlim(-0.35, 1.35)
    axis.set_ylim(len(labels) + 0.9, 0.2)
    axis.set_ylabel(ylabel)
    axis.set_title(title, fontsize=11)
    axis.grid(axis="y", alpha=0.2)
    return k_cut


def figure_migration(derived, figdir):
    """F4: the shift (left) and the reordering it does or does not cause (right)."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with_anchor = sorted(
        [row for row in derived if row["anchor_ip_ev"] is not None], key=lambda row: row["anchor_ip_ev"]
    )
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.2))

    axis = axes[0]
    x = list(range(len(with_anchor)))
    axis.plot(x, [row["anchor_ip_ev"] for row in with_anchor], "o", color="#111827",
              markersize=8, label="NIST / published anchor", zorder=5)
    axis.plot(x, [row["ip_koopmans_ev"] for row in with_anchor], "s", color="#dc2626",
              markersize=6, alpha=0.85, label="P0: GFN2-xTB Koopmans $-\\epsilon_{HOMO}$")
    axis.plot(x, [row["ip_r2scan3c_ev"] for row in with_anchor], "^", color="#1d4ed8",
              markersize=7, label="P1: r2SCAN-3c $\\Delta$SCF vertical IP")
    for index, row in enumerate(with_anchor):
        axis.plot([index, index], [row["anchor_ip_ev"], row["ip_koopmans_ev"]], "-",
                  color="#dc2626", alpha=0.25, linewidth=1.0)
        axis.plot([index, index], [row["anchor_ip_ev"], row["ip_r2scan3c_ev"]], "-",
                  color="#1d4ed8", alpha=0.32, linewidth=1.0)
    axis.set_xticks(x)
    axis.set_xticklabels([row["name"] for row in with_anchor], rotation=45, ha="right")
    axis.set_ylabel("vertical ionisation energy (eV)")
    axis.set_title("(a) the shift: three layers against the anchor", fontsize=11)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(fontsize=9, loc="lower right")

    labels = [row["name"] for row in derived]
    rank_p0 = _ranks([row["p0_ox_ev"] for row in derived], labels, True)
    rank_p1 = _ranks([row["p1_ox_ev"] for row in derived], labels, True)
    _bump_panel(
        axes[1], labels, rank_p0, rank_p1,
        "(b) the reordering: P0 -> P1, oxidation axis",
        "rank on the oxidation axis (1 = most oxidation-resistant)",
    )

    fig.suptitle(
        "P0 -> P1: a large systematic shift in the values, and what it does to the order", fontsize=12
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = figdir / "F4_rank_migration_p0_to_p1.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_reduction(derived, figdir):
    """F5: the reduction axis -- a qualitative failure, not a shift."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.2))

    axis = axes[0]
    ordered = sorted(
        derived, key=lambda row: (row["ea_koopmans_ev"] is None, row["ea_koopmans_ev"] or 0.0)
    )
    x = list(range(len(ordered)))
    axis.bar([i - 0.2 for i in x], [row["ea_koopmans_ev"] or 0.0 for row in ordered], width=0.4,
             color="#dc2626", alpha=0.85, label="P0: Koopmans EA $-\\epsilon_{LUMO}$")
    axis.bar([i + 0.2 for i in x], [row["ea_r2scan3c_ev"] or 0.0 for row in ordered], width=0.4,
             color="#1d4ed8", alpha=0.9, label="P1: r2SCAN-3c $\\Delta$SCF vertical EA")
    axis.axhline(0.0, color="#111827", linewidth=1.2)
    axis.annotate(
        "EA = 0: below this line the gas-phase radical anion is NOT bound",
        xy=(0.02, 0.04), xycoords="axes fraction", fontsize=8, color="#111827",
    )
    axis.set_xticks(x)
    axis.set_xticklabels([row["name"] for row in ordered], rotation=45, ha="right")
    axis.set_ylabel("vertical electron affinity (eV)")
    axis.set_title("(a) the qualitative failure: Koopmans EA vs a real anion", fontsize=11)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(fontsize=9)

    labels = [row["name"] for row in derived]
    rank_p0 = _ranks([row["p0_red_ev"] for row in derived], labels, True)
    rank_p1 = _ranks([row["p1_red_ev"] for row in derived], labels, True)
    _bump_panel(
        axes[1], labels, rank_p0, rank_p1,
        "(b) P0 -> P1 rank migration, reduction axis",
        "rank on the reduction axis (1 = most reduction-resistant)",
    )

    fig.suptitle(
        "Reduction axis: the cheap orbital proxy is not even qualitatively right", fontsize=12
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = figdir / "F5_reduction_axis_koopmans_vs_dscf.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_indicators(ox, red, figdir):
    """F6: the decision metrics, and the pairs the uncertainty band cannot resolve."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.9))

    axis = axes[0]
    keys = sorted(ox["top_k"])
    positions = list(range(len(keys)))
    width = 0.19
    series = (
        ("oxidation: overlap $O_k$", [ox["top_k"][k]["overlap"] for k in keys], "#1d4ed8"),
        ("oxidation: Jaccard $J_k$", [ox["top_k"][k]["jaccard"] for k in keys], "#93c5fd"),
        ("reduction: overlap $O_k$", [red["top_k"][k]["overlap"] for k in keys], "#b91c1c"),
        ("reduction: Jaccard $J_k$", [red["top_k"][k]["jaccard"] for k in keys], "#fca5a5"),
    )
    for index, (label, values, colour) in enumerate(series):
        axis.bar([p + (index - 1.5) * width for p in positions], values, width=width,
                 color=colour, label=label)
    axis.set_xticks(positions)
    axis.set_xticklabels(["%s\nk=%d" % (k, ox["top_k"][k]["k"]) for k in keys])
    axis.set_ylim(0, 1.15)
    axis.axhline(1.0, color="#111827", linestyle=":", linewidth=1.0)
    axis.set_ylabel("agreement between the P0 and P1 shortlists")
    axis.set_title("(a) does the cheap layer pick the same shortlist?", fontsize=11)
    axis.legend(fontsize=8, loc="lower left")
    axis.grid(axis="y", alpha=0.25)

    axis = axes[1]
    for label, block, colour in (("oxidation", ox, "#1d4ed8"), ("reduction", red, "#b91c1c")):
        pairs = block["pair_differences"]
        axis.plot(range(len(pairs)), [abs(item["d_p1_ev"]) for item in pairs], "-",
                  color=colour, linewidth=1.4, label="%s: |$\\Delta P_{ij}$| under P1" % label)
        axis.plot(range(len(pairs)), [Z_SENSITIVITY * item["sigma_ev"] for item in pairs], "--",
                  color=colour, alpha=0.6, linewidth=1.2,
                  label="%s: $z\\sigma_{ij}$ (z=1.96) from the P0/P1 spread" % label)
    axis.set_xlabel("the %d unordered pairs, sorted by P1 separation" % len(ox["pair_differences"]))
    axis.set_ylabel("pair separation (eV)")
    axis.set_title("(b) which pair orderings survive the uncertainty band?", fontsize=11)
    axis.legend(fontsize=8)
    axis.grid(axis="y", alpha=0.25)

    fig.suptitle(
        "$f_{unresolved}$ (z=1.0) = %.2f (ox) / %.2f (red);  $f_{robust\\_inv}$ (z=1.0) = %.2f (ox) / %.2f (red);"
        "  $\\tau_b$ = %.2f (ox) / %.2f (red)"
        % (
            ox["f_unresolved_p1"], red["f_unresolved_p1"],
            ox["f_robust_inv"], red["f_robust_inv"],
            ox["kendall_tau_b"], red["kendall_tau_b"],
        ),
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    path = figdir / "F6_decision_stability_indicators.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_shift_structure(derived, figdir):
    """F7: is the cheap layer a shifted ruler or a different ruler?"""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.9))
    panels = (
        (axes[0], "ip_koopmans_ev", "ip_r2scan3c_ev", "vertical IP (eV)",
         "(a) oxidation axis: a near-constant offset, except for the ethers"),
        (axes[1], "ea_koopmans_ev", "ea_r2scan3c_ev", "vertical EA (eV)",
         "(b) reduction axis: the points scatter across the diagonal"),
    )
    for axis, x_key, y_key, unit, title in panels:
        rows = [row for row in derived if row[x_key] is not None and row[y_key] is not None]
        if not rows:
            continue
        xs = [row[x_key] for row in rows]
        ys = [row[y_key] for row in rows]
        axis.scatter(xs, ys, s=44, color="#1d4ed8", alpha=0.85, zorder=3)
        for row in rows:
            axis.annotate(row["name"], (row[x_key], row[y_key]), textcoords="offset points",
                          xytext=(4, 4), fontsize=7.5)
        low = min(min(xs), min(ys))
        high = max(max(xs), max(ys))
        axis.plot([low, high], [low, high], "--", color="#111827", linewidth=1.0)
        axis.set_xlabel("P0 (GFN2-xTB) " + unit)
        axis.set_ylabel("P1 (r2SCAN-3c) " + unit)
        axis.set_title(title, fontsize=11)
        axis.grid(alpha=0.25)
    fig.suptitle("Is the cheap layer a shifted ruler, or a different ruler?", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = figdir / "F7_shift_structure.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(figdir: Path, entries, sources) -> Path:
    """Pin every figure to the inputs it was drawn from."""

    lines = [
        "# Figure manifest -- week 4 (P0 -> P1)",
        "",
        "Regenerated by `scripts/analyze_p1_core_set.py`. Digests pin each figure to the",
        "inputs it was drawn from, so a figure cannot silently drift from its numbers.",
        "",
        "| figure | file | what it shows |",
        "| --- | --- | --- |",
        "| F4 | F4_rank_migration_p0_to_p1.png | the value shift vs the anchor, and the P0 -> P1 rank migration on the oxidation axis |",
        "| F5 | F5_reduction_axis_koopmans_vs_dscf.png | the reduction axis: Koopmans EA is not even qualitatively right, and the migration it forces |",
        "| F6 | F6_decision_stability_indicators.png | Top-k overlap / Jaccard per axis, and the pair separations against the P0/P1 uncertainty band |",
        "| F7 | F7_shift_structure.png | is the cheap layer a shifted ruler or a different ruler (IP and EA scatters) |",
        "",
        "## inputs",
        "",
        "| file | present | sha256 |",
        "| --- | --- | --- |",
    ]
    for source in sources:
        if source.exists():
            lines.append("| %s | yes | %s |" % (source.relative_to(REPO_ROOT).as_posix(), sha256(source)))
        else:
            lines.append("| %s | no | missing |" % source.relative_to(REPO_ROOT).as_posix())
    lines += ["", "## outputs", "", "| file | sha256 |", "| --- | --- |"]
    for _, path in entries:
        lines.append("| %s | %s |" % (path.name, sha256(path)))
    lines.append("")
    manifest = figdir / "figure_manifest_week4.md"
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return manifest


def _fmt(value, digits=2):
    return "-" if value is None else ("%.*f" % (digits, value))


def write_report(path, derived, comparison, ox, red, figures, family_table) -> Path:
    """The week 4 decision report: numbers first, then the per-molecule table."""

    lines = [
        "# P0 -> P1 决策稳定性分析（core set，N=18）",
        "",
        "唯一变量：电子结构方法（GFN2-xTB -> r2SCAN-3c）。几何同为 G1（GFN2-xTB 优化几何），",
        "环境同为气相，全部为垂直量。因此排序上的任何变化都只能归因于方法本身。",
        "",
        "## 1. 数值层面：与外部气相锚点（NIST / 已发表值）比较",
        "",
        "| 臂 | n | MAE (eV) | bias (eV) | max abs err (eV) | err std (eV) | Kendall tau_b | Spearman rho |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, block in comparison.items():
        if not block or not block.get("n"):
            continue
        tau = block.get("kendall_tau_b")
        rho = block.get("spearman_rho")
        ci = block.get("kendall_tau_b_ci95")
        tau_text = "-" if tau is None else "%.3f" % tau
        if ci is not None:
            tau_text += " [%.2f, %.2f]" % (ci[0], ci[1])
        lines.append(
            "| %s | %d | %.3f | %+.3f | %.3f | %.3f | %s | %s |"
            % (
                label, block["n"], block["mae_ev"], block["bias_ev"],
                block["max_abs_error_ev"], block["error_std_ev"],
                tau_text,
                "-" if rho is None else "%.3f" % rho,
            )
        )
    lines += [
        "",
        "Kendall tau_b 后方的方括号是按 config/prereg.yaml 冻结设置（20 个 seed x 2000 次 paired",
        "bootstrap、percentile 95%）给出的区间中位数。n 只有 10-12，单点 tau_b 的噪声不可忽略；",
        "区间跨越 0 表示该臂与锚点排序的一致性没有被建立起来。",
        "",
        "读法：MAE 大不等于决策错。若某臂 MAE 很大而 tau_b 接近 1，它只是把同一把尺子整体平移，",
        "排序（因而筛选名单）没有被破坏；tau_b 明显低于 1 才意味着排序本身被改写。",
        "",
        "## 2. 决策层面：P0 -> P1",
        "",
        "| 轴 | n | Kendall tau_b | Spearman rho | O_k(10%) | O_k(20%) | O_k(30%) | J_k(20%) | selection regret(20%) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, block in (("氧化", ox), ("还原", red)):
        if block.get("n", 0) < 2:
            continue
        kk = block["top_k"]
        ci = block.get("kendall_tau_b_ci95")
        tau_text = "%.3f" % block["kendall_tau_b"]
        if ci is not None:
            tau_text += " [%.2f, %.2f]" % (ci[0], ci[1])
        lines.append(
            "| %s | %d | %s | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f |"
            % (
                label, block["n"], tau_text, block["spearman_rho"],
                kk["k=0.10"]["overlap"], kk["k=0.20"]["overlap"], kk["k=0.30"]["overlap"],
                kk["k=0.20"]["jaccard"], kk["k=0.20"]["selection_regret"],
            )
        )
    lines += [
        "",
        "### 2.1 不确定度感知指标",
        "",
        "主判据为 config/prereg.yaml 冻结的 pair_comparison.z_factor.value = 1.0；",
        "z = 1.96（95% 双侧带）作为保守敏感性与之并列报告。",
        "",
        "| 轴 | f_unresolved(P0) z=1.0（主判据） | f_unresolved(P1) z=1.0（主判据） | f_robust_inv z=1.0（主判据） | f_unresolved(P0) z=1.96（敏感性） | f_unresolved(P1) z=1.96（敏感性） | f_robust_inv z=1.96（敏感性） | sigma 中位数 (eV) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, block in (("氧化", ox), ("还原", red)):
        if block.get("n", 0) < 2:
            continue
        lines.append(
            "| %s | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %s |"
            % (
                label, block["f_unresolved_p0"], block["f_unresolved_p1"],
                block["f_robust_inv"],
                block["f_unresolved_p0_z1p96"], block["f_unresolved_p1_z1p96"],
                block["f_robust_inv_z1p96"],
                _fmt(block["sigma_median_ev"], 3),
            )
        )
    lines += [
        "",
        "sigma 由两臂自身的方法离散度给出（两个 realization：P0 与 P1），不需要外部参考；",
        "因此 f_unresolved 读作「这一对分子连谁更稳都说不清」的比例，f_robust_inv 读作",
        "「两臂都认为自己分得清、但结论相反」的比例。",
    ]
    lines += [
        "",
        "## 3. 平移的化学结构依赖（物理机制）",
        "",
        "P0 -> P1 的平移不是一个常数，而是明显依赖官能团；下表按家族聚合。",
        "",
        "| 家族 | n | 成员 | 平均 IP 平移 (eV) | 平移范围 (eV) | 平均 EA 平移 (eV) | P0 平均 IP | P1 平均 IP |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for block in family_table:
        lines.append(
            "| %s | %d | %s | %s | %s | %s | %s | %s |"
            % (
                block["family"], block["n"], ", ".join(block["members"]),
                _fmt(block["ox_shift_mean_ev"]),
                "%s .. %s" % (_fmt(block["ox_shift_min_ev"]), _fmt(block["ox_shift_max_ev"])),
                _fmt(block["ea_shift_mean_ev"]),
                _fmt(block["ip_p0_mean_ev"]), _fmt(block["ip_p1_mean_ev"]),
            )
        )
    lines += [
        "",
        "平移 = P1 - P0。负的 IP 平移表示廉价层高估了氧化稳定性。EA 平移全部为负，原因是 P1 给出的",
        "气相阴离子根本不束缚（EA < 0），而定域在 LUMO 上的 Koopmans 图像永远给不出这一点。",
        "",
    ]

    lines += [
        "",
        "## 4. 逐分子表",
        "",
        "| 分子 | 家族 | IP anchor | P0 Koopmans IP | P1 r2SCAN-3c IP | P0 err | P1 err | EA Koopmans | EA r2SCAN-3c | 气相阴离子束缚 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    ordered = sorted(
        derived, key=lambda row: row["anchor_ip_ev"] if row["anchor_ip_ev"] is not None else 1e9
    )
    for row in ordered:
        bound = row["ea_r2scan3c_bound"]
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                row["name"], row["family"],
                _fmt(row["anchor_ip_ev"]), _fmt(row["ip_koopmans_ev"]), _fmt(row["ip_r2scan3c_ev"]),
                _fmt(row["ip_err_p0_ev"]), _fmt(row["ip_err_p1_ev"]),
                _fmt(row["ea_koopmans_ev"]), _fmt(row["ea_r2scan3c_ev"]),
                "-" if bound is None else ("yes" if bound else "NO"),
            )
        )
    lines += ["", "## 5. 图", ""]
    for name, figure in figures:
        lines.append("- %s: `%s`" % (name, figure.relative_to(REPO_ROOT).as_posix()))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.p1.exists():
        print("error: missing %s; run scripts/run_core_set_p1.py first" % args.p1, file=sys.stderr)
        return 2

    p1 = load_p1(args.p1)
    p0 = load_by_name(args.p0)
    xtb = load_by_name(args.xtb)
    anchors = load_anchors(args.anchors)
    derived = build_derived(p1, p0, xtb, anchors)

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.figdir.mkdir(parents=True, exist_ok=True)

    derived_path = args.outdir / "p1_core_set_derived.csv"
    with derived_path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=DERIVED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in derived:
            writer.writerow(row)

    with_anchor = [row for row in derived if row["anchor_ip_ev"] is not None]
    shifts = [row["ox_shift_ev"] for row in derived if row["ox_shift_ev"] is not None]
    ips = [row["ip_r2scan3c_ev"] for row in derived if row["ip_r2scan3c_ev"] is not None]
    comparison = {
        "anchor_source": "data/anchors/gas_phase_anchors.csv, property=IP (experimental determination preferred)",
        "n_with_anchor": len(with_anchor),
        "P0_koopmans_xTB": compare_arm(
            [row["ip_koopmans_ev"] for row in with_anchor],
            [row["anchor_ip_ev"] for row in with_anchor],
            [row["name"] for row in with_anchor],
        ),
        "GFN2_dSCF_xTB": compare_arm(
            [row["ip_xtb_dscf_ev"] for row in with_anchor],
            [row["anchor_ip_ev"] for row in with_anchor],
            [row["name"] for row in with_anchor],
        ),
        "P1_r2SCAN3c": compare_arm(
            [row["ip_r2scan3c_ev"] for row in with_anchor],
            [row["anchor_ip_ev"] for row in with_anchor],
            [row["name"] for row in with_anchor],
        ),
        "shift_statistics": {
            "n": len(shifts),
            "ox_shift_mean_ev": statistics.fmean(shifts) if shifts else None,
            "ox_shift_std_ev": statistics.pstdev(shifts) if len(shifts) > 1 else None,
            "p1_ip_range_ev": (max(ips) - min(ips)) if ips else None,
            "p1_n_bound_anion": sum(1 for row in derived if row["ea_r2scan3c_bound"]),
            "p0_n_positive_koopmans_ea": sum(1 for row in derived if (row["ea_koopmans_ev"] or 0) > 0),
        },
    }
    family_table = shift_by_family(derived)
    comparison["shift_by_family"] = family_table
    (args.outdir / "p1_anchor_comparison.json").write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    labels = [row["name"] for row in derived]
    ox = layer_stability(
        [row["p0_ox_ev"] for row in derived], [row["p1_ox_ev"] for row in derived], labels, higher_is_better=True
    )
    red = layer_stability(
        [row["p0_red_ev"] for row in derived], [row["p1_red_ev"] for row in derived], labels, higher_is_better=True
    )
    (args.outdir / "p1_decision_stability.json").write_text(
        json.dumps({"oxidation": ox, "reduction": red}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    figures = [
        ("F4", figure_migration(derived, args.figdir)),
        ("F5", figure_reduction(derived, args.figdir)),
        ("F6", figure_indicators(ox, red, args.figdir)),
        ("F7", figure_shift_structure(derived, args.figdir)),
    ]
    manifest = write_manifest(args.figdir, figures, [args.p1, args.p0, args.xtb, args.anchors])

    report = write_report(
        args.outdir / "p1_decision_stability.md",
        derived,
        {
            "P0 Koopmans (GFN2-xTB)": comparison["P0_koopmans_xTB"],
            "GFN2-xTB Delta-SCF": comparison["GFN2_dSCF_xTB"],
            "P1 r2SCAN-3c": comparison["P1_r2SCAN3c"],
        },
        ox,
        red,
        figures,
        family_table,
    )

    print(json.dumps({
        "n_molecules": len(derived),
        "n_with_anchor": len(with_anchor),
        "anchor_mae_ev": {
            "P0_koopmans": comparison["P0_koopmans_xTB"].get("mae_ev"),
            "GFN2_dSCF": comparison["GFN2_dSCF_xTB"].get("mae_ev"),
            "P1_r2SCAN3c": comparison["P1_r2SCAN3c"].get("mae_ev"),
        },
        "oxidation": {"tau_b": ox.get("kendall_tau_b"), "overlap_20": ox.get("top_k", {}).get("k=0.20", {}).get("overlap")},
        "reduction": {"tau_b": red.get("kendall_tau_b"), "overlap_20": red.get("top_k", {}).get("k=0.20", {}).get("overlap")},
        "derived_csv": derived_path.relative_to(REPO_ROOT).as_posix(),
        "report": report.relative_to(REPO_ROOT).as_posix(),
        "manifest": manifest.relative_to(REPO_ROOT).as_posix(),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())