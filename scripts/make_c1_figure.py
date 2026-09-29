r"""Stage 5 / T4 C1 figure (F12): what Li+ coordination does to the decision.

Four panels, all fed by outputs/week5/c1_summary.json and the tables the analysis
step writes:

(a) the per-molecule coordination shift of the vertical IP and EA, C1 minus C0;
    a molecule with no C1 result is left blank (NaN bar) and flagged "(n/a)" on
    the axis, never drawn as a zero shift;
(b) the same dispersion statistic -- population std of the vertical shift -- for
    the four single-variable perturbations the project compares: method, geometry,
    environment and coordination.  All four are measured on the same molecule list
    with the same estimator, and the usable n is printed on every bar (a step can
    lose molecules, e.g. when a redox state fails to optimise, so n may differ).
    Only the dispersion scale is comparable across the four steps: the coordination
    step has a different reference state (neutral C0 vs the [Li M]+ cation, see
    docs/12_week5_report.md sections 2.6 and 7), so its baseline cannot be added to
    the other three and the four bars are not an additive decomposition;
(c) the ligand-exchange quantity dGdG_bind(M;R) against the frozen reference ligand
    R, with the secondary reference overlaid as an R-dependence check
    (config/scientific_definitions.yaml); R is read from the data, not hard-coded;
(d) the decision metrics of the C0 -> C1 comparison: tau_b, Top-20% overlap,
    Jaccard and f_robust_inv, oxidation and reduction separately.

Labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\Scripts\python.exe scripts\make_c1_figure.py
    .venv\Scripts\python.exe scripts\make_c1_figure.py --outdir <dir> --manifest <file>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEEK5 = REPO_ROOT / "outputs" / "week5"
SUMMARY = WEEK5 / "c1_summary.json"
SHIFTS = WEEK5 / "c1_coord_shifts.csv"
EXCHANGE = WEEK5 / "c1_ligand_exchange.csv"
STABILITY = WEEK5 / "c1_decision_stability.json"
C1_CSV = WEEK5 / "c1_li_coordination.csv"
MOTIFS = WEEK5 / "li_motif_generation.json"
FIGDIR = REPO_ROOT / "outputs" / "figures"
FIGNAME = "F12_li_coordination_c1.png"
MANIFEST = FIGDIR / "figure_manifest_week5_c1.md"

IP_COLOR = "#2563eb"
EA_COLOR = "#dc2626"
STEP_COLOR = {
    "method": "#7c3aed",
    "geometry": "#0d9488",
    "environment": "#ea580c",
    "coordination": "#be123c",
}
STEP_LABEL = {
    "method": "method\n(P0 -> P1)\nGFN2-xTB -> r2SCAN-3c",
    "geometry": "geometry\n(G1 -> G2)\nboth r2SCAN-3c",
    "environment": "environment\n(gas -> SMD AN)\nfixed continuum",
    "coordination": "coordination\n(C0 -> C1)\n+ Li+, same method",
}
SHIFT_COLUMNS = [
    "mol_id", "name", "family", "motif_id", "is_primary", "li_contacts",
    "ip_c0_g2_ev", "ip_c1_ev", "d_ip_ev", "d_ip_kj", "ip_c1_relaxed_ev",
    "d_ip_relaxed_ev", "ea_c0_g2_ev", "ea_c1_ev", "d_ea_ev", "d_ea_kj",
    "ea_c1_relaxed_ev", "d_ea_relaxed_ev", "ip_c1_smd_ev", "d_ip_smd_ev",
    "ea_c1_smd_ev", "d_ea_smd_ev", "qc_flags", "status_flags",
]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_table(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_float(value) -> float:
    """Return the parsed number, or NaN when the value is missing/unparseable.

    ``number`` collapses "0.0" and "missing" the same way a bare ``or`` would,
    so this helper keeps a genuine zero as 0.0 and only maps true gaps to NaN.
    """
    parsed = number(value)
    return float("nan") if parsed is None else float(parsed)


def is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def fmt_bar(values, fmt: str, missing: str = "") -> list:
    """Bar labels with an empty (or custom) string where the value is NaN."""
    return [missing if is_missing(v) else fmt % v for v in values]


def resolve_primary(shifts: list) -> list:
    primary = [row for row in shifts if row["is_primary"] == "True"]
    primary.sort(key=lambda row: number(row["d_ip_ev"]) if number(row["d_ip_ev"]) is not None else 0.0)
    return primary


def build_figure(summary: dict, shifts: list, exchange: list, stability: dict,
                 outdir: Path, figure_name: str = FIGNAME) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    primary = resolve_primary(shifts)
    names = [row["name"] for row in primary]
    d_ip = [as_float(row["d_ip_ev"]) for row in primary]
    d_ea = [as_float(row["d_ea_ev"]) for row in primary]
    labels_a = [
        name + (" (n/a)" if (is_missing(ip) or is_missing(ea)) else "")
        for name, ip, ea in zip(names, d_ip, d_ea)
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14.4, 10.0))
    ax_a, ax_b, ax_c, ax_d = axes.ravel()

    y = np.arange(len(names), dtype=float)
    height = 0.38
    bars_ip = ax_a.barh(y + height / 2.0, d_ip, height, label="dIP = IP(C1) - IP(C0)",
                        color=IP_COLOR, edgecolor="white", linewidth=0.6)
    bars_ea = ax_a.barh(y - height / 2.0, d_ea, height, label="dEA = EA(C1) - EA(C0)",
                        color=EA_COLOR, edgecolor="white", linewidth=0.6)
    ax_a.bar_label(bars_ip, labels=fmt_bar(d_ip, "%+.2f"), fontsize=7.0, padding=2)
    ax_a.bar_label(bars_ea, labels=fmt_bar(d_ea, "%+.2f"), fontsize=7.0, padding=2)
    ax_a.axvline(0.0, color="#111827", linewidth=1.2)
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(labels_a, fontsize=9)
    ax_a.set_ylim(-0.7, len(names) - 0.3)
    finite_a = [v for v in d_ip + d_ea if not is_missing(v)]
    if finite_a:
        lo, hi = min(finite_a), max(finite_a)
        span = (hi - lo) or 1.0
        ax_a.set_xlim(lo - 0.30 * span, hi + 0.30 * span)
    else:
        ax_a.set_xlim(-1.0, 1.0)
    ax_a.set_xlabel("coordination shift of the vertical IP / EA, C1 - C0   [eV]")
    ax_a.set_title("(a) Li+ coordination shift, primary motif m1")
    ax_a.legend(fontsize=7.8, frameon=False, loc="lower right")
    ip_block = summary["delta_ip_ev"]
    ea_block = summary["delta_ea_ev"]
    ax_a.text(0.985, 0.975,
              "mean  sigma(pop)\ndIP %+.2f  %.2f eV\ndEA %+.2f  %.2f eV"
              % (ip_block["mean"], ip_block["std"], ea_block["mean"], ea_block["std"]),
              transform=ax_a.transAxes, fontsize=7.8, va="top", ha="right", color="#374151",
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.9,
                        edgecolor="#d1d5db", linewidth=0.7))
    if any(is_missing(v) for v in d_ip + d_ea):
        ax_a.text(0.985, 0.03, "(n/a) = no C1 result for that molecule; bar omitted",
                  transform=ax_a.transAxes, fontsize=7.0, ha="right", va="bottom", color="#6b7280")

    steps = ["method", "geometry", "environment", "coordination"]
    step_blocks = summary["four_step_sigma"]["steps"]
    ip_values, ea_values, ip_ns, ea_ns = [], [], [], []
    for step in steps:
        ip_b = step_blocks.get(step, {}).get("ip_ev", {})
        ea_b = step_blocks.get(step, {}).get("ea_ev", {})
        ip_values.append(as_float(ip_b.get("std")))
        ea_values.append(as_float(ea_b.get("std")))
        ip_ns.append(ip_b.get("n", 0) or 0)
        ea_ns.append(ea_b.get("n", 0) or 0)
    x = np.arange(len(steps), dtype=float)
    width = 0.36
    bars_b1 = ax_b.bar(x - width / 2.0, ip_values, width, color=IP_COLOR,
                       edgecolor="white", linewidth=0.6, label="sigma(dIP)")
    bars_b2 = ax_b.bar(x + width / 2.0, ea_values, width, color=EA_COLOR,
                       edgecolor="white", linewidth=0.6, label="sigma(dEA)")
    ip_labels = ["%.3f\nn=%d" % (v, n) if not is_missing(v) else "n/a\nn=%d" % n
                 for v, n in zip(ip_values, ip_ns)]
    ea_labels = ["%.3f\nn=%d" % (v, n) if not is_missing(v) else "n/a\nn=%d" % n
                 for v, n in zip(ea_values, ea_ns)]
    ax_b.bar_label(bars_b1, labels=ip_labels, fontsize=7.6, padding=2)
    ax_b.bar_label(bars_b2, labels=ea_labels, fontsize=7.6, padding=2)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels([STEP_LABEL[step] for step in steps], fontsize=7.4)
    ax_b.set_ylabel("population std of the vertical shift   [eV]")
    ax_b.set_title("(b) Same estimator, one molecule list, but usable n can differ per step")
    finite_b = [v for v in ip_values + ea_values if not is_missing(v)]
    ax_b.set_ylim(0.0, (max(finite_b) if finite_b else 1.0) * 1.30)
    ax_b.legend(fontsize=8.0, frameon=False, loc="upper left")
    # Placed over the short geometry/environment bars: at y=0.70 on the right it
    # used to run into the coordination bar labels (0.790 / n=10).
    ax_b.text(0.295, 0.955, "same molecule list, same estimator as week 4;\n"
                            "usable n differs per step (bar labels).\n"
                            "only the dispersion scale is comparable -- the\n"
                            "coordination baseline is a different state.",
              transform=ax_b.transAxes, fontsize=7.2, va="top", ha="left", color="#374151",
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.9,
                        edgecolor="none"))

    reference = None
    if isinstance(stability, dict):
        reference = stability.get("reference_ligand")
    if reference in (None, ""):
        for row in exchange:
            if row.get("reference_ligand_name"):
                reference = row["reference_ligand_name"]
                break

    def matches_reference(row) -> bool:
        return row.get("reference_ligand") == reference or row.get("reference_ligand_name") == reference

    gas = [row for row in exchange if row.get("continuum") == "gas" and matches_reference(row)]
    smd = [row for row in exchange if row.get("continuum") == "smd" and matches_reference(row)]
    ref_label = gas[0].get("reference_ligand_name") or reference if gas else reference

    if not gas:
        ax_c.set_xticks([])
        ax_c.set_yticks([])
        ax_c.text(0.5, 0.5,
                  "reference ligand R = %s not found in c1_ligand_exchange.csv;\n"
                  "no ligand-exchange bars drawn" % reference,
                  transform=ax_c.transAxes, fontsize=9.6, ha="center", va="center",
                  color="#b91c1c", wrap=True)
        ax_c.set_title("(c) Ligand exchange against the frozen reference R = %s (missing)" % reference)
    else:
        order = {row["name"]: index for index, row in enumerate(primary)}
        gas.sort(key=lambda row: order.get(row["name"], 99))
        smd_map = {row["name"]: row for row in smd}
        names_c = [row["name"] for row in gas]
        y_c = np.arange(len(names_c), dtype=float)
        gas_values = [as_float(row.get("dGdG_bind_kj")) for row in gas]
        smd_values = [as_float(smd_map.get(name, {}).get("dGdG_bind_kj")) for name in names_c]
        labels_c = [n + (" (n/a)" if is_missing(v) else "") for n, v in zip(names_c, gas_values)]
        bars_c1 = ax_c.barh(y_c + height / 2.0, gas_values, height, color="#1d4ed8",
                            edgecolor="white", linewidth=0.6, label="gas phase")
        bars_c2 = ax_c.barh(y_c - height / 2.0, smd_values, height, color="#059669",
                            edgecolor="white", linewidth=0.6, label="CPCM(SMD, acetonitrile)")
        ax_c.bar_label(bars_c1, labels=fmt_bar(gas_values, "%+.1f"), fontsize=7.0, padding=2)
        ax_c.bar_label(bars_c2, labels=fmt_bar(smd_values, "%+.1f"), fontsize=7.0, padding=2)
        ax_c.axvline(0.0, color="#111827", linewidth=1.2)
        ax_c.set_yticks(y_c)
        ax_c.set_yticklabels(labels_c, fontsize=9)
        ax_c.set_ylim(-0.7, len(names_c) - 0.3)
        ax_c.set_xlabel("dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M)   [kJ/mol]")
        ax_c.set_title("(c) Ligand exchange against the frozen reference R = %s" % ref_label)
        ax_c.legend(fontsize=8.0, frameon=False, loc="lower right")
        # Anchored on the reference row, whose two bars are 0 by construction:
        # at the old y=0.975 the note sat on the longest row and its white box
        # clipped that row's value labels.
        ax_c.text(0.985, 0.780,
                  "negative = M binds Li+ better than %s\nself-exchange (%s) is 0 by construction"
                  % (ref_label, ref_label),
                  transform=ax_c.transAxes, fontsize=7.6, va="top", ha="right", color="#374151",
                  bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.9,
                            edgecolor="none"))

    display = ["tau_b", "O_20%", "J_20%", "1 - f_robust_inv"]
    ox = stability["oxidation"]
    red = stability["reduction"]

    def values(block):
        if not block or block.get("n", 0) < 2:
            return [float("nan")] * 4
        return [
            block["kendall_tau_b"],
            block["top_k"]["k=0.20"]["overlap"],
            block["top_k"]["k=0.20"]["jaccard"],
            1.0 - block["f_robust_inv"],
        ]

    ox_values = values(ox)
    red_values = values(red)
    x_d = np.arange(len(display), dtype=float)
    bars_d1 = ax_d.bar(x_d - width / 2.0, ox_values, width, color="#0f766e",
                       edgecolor="white", linewidth=0.6, label="oxidation axis")
    bars_d2 = ax_d.bar(x_d + width / 2.0, red_values, width, color="#b45309",
                       edgecolor="white", linewidth=0.6, label="reduction axis")
    ax_d.bar_label(bars_d1, labels=fmt_bar(ox_values, "%.3f", missing="n/a"), fontsize=8.2, padding=2)
    ax_d.bar_label(bars_d2, labels=fmt_bar(red_values, "%.3f", missing="n/a"), fontsize=8.2, padding=2)
    ax_d.set_xticks(x_d)
    ax_d.set_xticklabels(display, fontsize=9)
    # tau_b ranges over [-1, 1], and a fixed lower bound of 0 silently rendered
    # the reduction tau_b (-0.467) as "no bar at all".  Let the data set both ends.
    finite_d = [v for v in (list(ox_values) + list(red_values)) if not np.isnan(v)]
    low = min([0.0] + finite_d) - 0.10 if finite_d else -0.10
    high = max([1.0] + finite_d) + 0.16 if finite_d else 1.16
    ax_d.set_ylim(low, high)
    ax_d.axhline(0.0, color="#6b7280", linewidth=0.9)
    ax_d.axhline(1.0, color="#9ca3af", linewidth=0.9, linestyle="--")
    ax_d.set_ylabel("C0 vs C1 agreement (1.0 = decision unchanged)")
    ax_d.set_title("(d) Does coordination change the decision?" + _decision_note(ox, red))
    ax_d.legend(fontsize=8.0, frameon=False, loc="lower right")
    ax_d.text(0.985, 0.975,
              "f_robust_inv: ox %s, red %s\nf_unresolved(C1): ox %s, red %s"
              % (
                  _stat(ox, "f_robust_inv"),
                  _stat(red, "f_robust_inv"),
                  _stat(ox, "f_unresolved_p1", "%.2f"),
                  _stat(red, "f_unresolved_p1", "%.2f"),
              ),
              transform=ax_d.transAxes, fontsize=7.6, va="top", ha="right", color="#374151")

    fig.suptitle("Stage 5 / T4 (F12): the C1 conditional state -- Li+ coordinated molecules, "
                 "r2SCAN-3c, vertical IP/EA", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / figure_name
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _stat(block, key, fmt: str = "%.3f") -> str:
    if not block or block.get(key) is None:
        return "n/a"
    try:
        return fmt % float(block[key])
    except (TypeError, ValueError):
        return "n/a"


def _decision_note(ox, red) -> str:
    notes = []
    for label, block in (("oxidation", ox), ("reduction", red)):
        if not block or block.get("n", 0) < 2:
            notes.append("%s n=%d" % (label, (block or {}).get("n", 0)))
    if not notes:
        return ""
    return "\n(insufficient n: " + ", ".join(notes) + ")"

def write_manifest(summary, shifts, exchange, stability, figure: Path,
                   manifest_path: Path = MANIFEST,
                   summary_path: Path = SUMMARY, shifts_path: Path = SHIFTS,
                   exchange_path: Path = EXCHANGE, stability_path: Path = STABILITY) -> Path:
    ip_block = summary["delta_ip_ev"]
    ea_block = summary["delta_ea_ev"]
    steps = summary["four_step_sigma"]["steps"]
    lines = [
        "# Figure manifest - Stage 5 / T4 C1 Li+ coordination (F12)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F12 | `" + figure.name + "` | " + sha256_of(figure)
        + " | `c1_summary.json` " + sha256_of(summary_path)
        + " | `c1_coord_shifts.csv` " + sha256_of(shifts_path) + " |",
        "| | | | `c1_ligand_exchange.csv` " + sha256_of(exchange_path)
        + " | `c1_decision_stability.json` " + sha256_of(stability_path) + " |",
        "| | | | `c1_li_coordination.csv` " + sha256_of(C1_CSV)
        + " | `li_motif_generation.json` " + sha256_of(MOTIFS) + " |",
        "",
        "F12 note: C0 is the free molecule at its r2SCAN-3c geometry (T2, P1 at G2);",
        "C1 is r2SCAN-3c at the optimised [Li M]+ geometry of the same molecule. Both",
        "are vertical, so the difference isolates the chemical state, not the method,",
        "the geometry basis or the continuum. Panel (b) places the coordination",
        "dispersion next to the three terms week 4 measured using one estimator and one",
        "molecule list; the usable n can differ per step and is printed on each bar. The",
        "coordination step uses a different reference state (neutral C0 vs the [Li M]+",
        "cation, docs/12_week5_report.md sections 2.6 and 7), so only the dispersion",
        "scale is comparable and the four bars are not an additive decomposition.",
        "",
        "- n_molecules: " + str(summary["n_molecules"]) + "; molecules: "
        + ", ".join(summary["molecules"]),
        "- n_motifs (all, incl. secondary): " + str(summary["n_motifs"]),
        "- dIP(C1-C0): mean %+.3f eV, pop std %.3f eV" % (ip_block["mean"], ip_block["std"]),
        "- dEA(C1-C0): mean %+.3f eV, pop std %.3f eV" % (ea_block["mean"], ea_block["std"]),
        "- sigma(method) dIP %.3f eV / dEA %.3f eV (n %d / %d)" % (
            steps["method"]["ip_ev"]["std"], steps["method"]["ea_ev"]["std"],
            steps["method"]["ip_ev"]["n"], steps["method"]["ea_ev"]["n"]),
        "- sigma(geometry) dIP %.3f eV / dEA %.3f eV (n %d / %d)" % (
            steps["geometry"]["ip_ev"]["std"], steps["geometry"]["ea_ev"]["std"],
            steps["geometry"]["ip_ev"]["n"], steps["geometry"]["ea_ev"]["n"]),
        "- sigma(environment, SMD AN) dIP %.3f eV / dEA %.3f eV (n %d / %d)" % (
            steps["environment"]["ip_ev"]["std"], steps["environment"]["ea_ev"]["std"],
            steps["environment"]["ip_ev"]["n"], steps["environment"]["ea_ev"]["n"]),
        "- sigma(coordination) dIP %.3f eV / dEA %.3f eV (n %d / %d)" % (
            steps["coordination"]["ip_ev"]["std"], steps["coordination"]["ea_ev"]["std"],
            steps["coordination"]["ip_ev"]["n"], steps["coordination"]["ea_ev"]["n"]),
        "- decision C0 vs C1: tau_b(ox) " + str(summary["decision_stability"]["oxidation"]["kendall_tau_b"])
        + ", tau_b(red) " + str(summary["decision_stability"]["reduction"]["kendall_tau_b"]),
        "- f_robust_inv: ox " + str(summary["decision_stability"]["oxidation"]["f_robust_inv"])
        + ", red " + str(summary["decision_stability"]["reduction"]["f_robust_inv"]),
        "",
        summary["four_step_sigma"]["definition"],
        "",
        "Labels are English on purpose (no guaranteed CJK font in the workspace).",
    ]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render the F12 C1 (Li+ coordination) four-panel figure and its manifest.")
    parser.add_argument("--summary", default=str(SUMMARY),
                        help="c1_summary.json (default: " + str(SUMMARY) + ")")
    parser.add_argument("--shifts", default=str(SHIFTS),
                        help="c1_coord_shifts.csv (default: " + str(SHIFTS) + ")")
    parser.add_argument("--exchange", default=str(EXCHANGE),
                        help="c1_ligand_exchange.csv (default: " + str(EXCHANGE) + ")")
    parser.add_argument("--stability", default=str(STABILITY),
                        help="c1_decision_stability.json (default: " + str(STABILITY) + ")")
    parser.add_argument("--outdir", default=str(FIGDIR),
                        help="output directory for the PNG (default: " + str(FIGDIR) + ")")
    parser.add_argument("--figure-name", default=FIGNAME,
                        help="PNG file name (default: " + FIGNAME + ")")
    parser.add_argument("--manifest", default=str(MANIFEST),
                        help="manifest markdown path (default: " + str(MANIFEST) + ")")
    return parser


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary_path = Path(args.summary)
    shifts_path = Path(args.shifts)
    exchange_path = Path(args.exchange)
    stability_path = Path(args.stability)
    manifest_path = Path(args.manifest)
    if not summary_path.exists():
        raise SystemExit("missing " + str(summary_path)
                         + "; run scripts/analyze_c1_coordination.py first")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    shifts = read_table(shifts_path)
    exchange = read_table(exchange_path)
    stability = json.loads(stability_path.read_text(encoding="utf-8"))
    figure = build_figure(summary, shifts, exchange, stability, Path(args.outdir), args.figure_name)
    manifest = write_manifest(summary, shifts, exchange, stability, figure, manifest_path,
                              summary_path, shifts_path, exchange_path, stability_path)
    print("wrote " + str(_display_path(figure)))
    print("wrote " + str(_display_path(manifest)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())