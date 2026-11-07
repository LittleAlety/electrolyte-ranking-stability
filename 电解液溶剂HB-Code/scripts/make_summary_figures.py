"""Project-level summary figures (F0-F3) for the ranking-stability study.

Every figure is regenerated deterministically from repository artefacts, and a
figure_manifest.md records the inputs' SHA256 so a figure can never drift away
from the numbers it claims to show.  Figure labels are ASCII/English on purpose:
the workspace has no guaranteed CJK font, and a figure full of tofu boxes is
worse than an English figure.

Usage:
    .venv\Scripts\python.exe scripts\make_summary_figures.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FIGURE_NOTES = {
    "F0": "project pipeline: cheap proxy -> validated target -> rank change -> mechanism -> minimal budget",
    "F1": "chemical-space coverage: core set vs broad pool across structural families",
    "F2": "P0 proxy distributions by family / fluorination (needs outputs/week3/p0_broad_pool.csv)",
    "F3": "value error vs rank error for the xTB audit arms and the r2SCAN-3c P1 arm (the central anti-intuition result)",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_pool(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row.get("mol_id")]


def figure_f0(outdir: Path) -> Path:
    """Conceptual pipeline figure: what the project claims to isolate."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    stages = [
        ("P0 cheap proxy\nGFN2-xTB HOMO/LUMO", "#dbeafe"),
        ("P1 validated target\nr2SCAN-3c gas redox", "#bfdbfe"),
        ("P2 env. target\ncontinuum eps scan", "#93c5fd"),
        ("C1 conditional species\nLi+ coordination", "#60a5fa"),
        ("decision stability\ntop-k / robust inversion", "#3b82f6"),
    ]
    fig, ax = plt.subplots(figsize=(13.5, 3.4))
    ax.set_xlim(0, len(stages) * 2.6)
    ax.set_ylim(0, 3)
    ax.axis("off")
    for index, (label, colour) in enumerate(stages):
        x = index * 2.6 + 0.15
        box = FancyBboxPatch(
            (x, 1.05), 2.1, 0.95, boxstyle="round,pad=0.08,rounding_size=0.12",
            linewidth=1.2, edgecolor="#1e3a8a", facecolor=colour,
        )
        ax.add_patch(box)
        ax.text(x + 1.05, 1.52, label, ha="center", va="center", fontsize=9.5, color="#0f172a")
        if index < len(stages) - 1:
            arrow = FancyArrowPatch(
                (x + 2.13, 1.52), (x + 2.55, 1.52),
                arrowstyle="-|>", mutation_scale=14, linewidth=1.4, color="#1e3a8a",
            )
            ax.add_patch(arrow)
    ax.text(
        len(stages) * 2.6 / 2, 2.55,
        "What changes the MATERIALS DECISION, and by which physical mechanism?",
        ha="center", va="center", fontsize=12, fontweight="bold", color="#0f172a",
    )
    ax.text(
        len(stages) * 2.6 / 2, 0.55,
        "model complexity != accuracy != physical representativeness != materials decision",
        ha="center", va="center", fontsize=10, style="italic", color="#334155",
    )
    path = outdir / "F0_project_pipeline.png"
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_f1(outdir: Path) -> Path:
    """Coverage: how many molecules per family in core set vs broad pool."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    core = read_pool(REPO_ROOT / "data" / "metadata" / "core_set.csv")
    broad = read_pool(REPO_ROOT / "data" / "metadata" / "broad_pool.csv")
    families = sorted({row["family"] for row in core + broad})
    core_counts = [sum(1 for row in core if row["family"] == fam) for fam in families]
    broad_counts = [sum(1 for row in broad if row["family"] == fam) for fam in families]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0), gridspec_kw={"width_ratios": [1.35, 1.0]})
    positions = range(len(families))
    axes[0].barh([p - 0.2 for p in positions], core_counts, height=0.4, label="core set (N=18)", color="#1d4ed8")
    axes[0].barh([p + 0.2 for p in positions], broad_counts, height=0.4, label="broad pool (N=40)", color="#93c5fd")
    axes[0].set_yticks(list(positions))
    axes[0].set_yticklabels(families, fontsize=9)
    axes[0].set_xlabel("molecule count")
    axes[0].set_title("Family coverage: core set vs broad pool", fontsize=11)
    axes[0].legend(fontsize=9)
    axes[0].grid(axis="x", alpha=0.25)

    def donor_hist(pool: list[dict]) -> list[int]:
        counts = [0] * 7
        for row in pool:
            try:
                value = int(float(row.get("donor_count") or 0))
            except ValueError:
                value = 0
            counts[min(value, 6)] += 1
        return counts

    core_hist, broad_hist = donor_hist(core), donor_hist(broad)
    bins = [str(i) if i < 6 else "6+" for i in range(7)]
    width = 0.4
    axes[1].bar([i - width / 2 for i in range(7)], core_hist, width=width, label="core set", color="#1d4ed8")
    axes[1].bar([i + width / 2 for i in range(7)], broad_hist, width=width, label="broad pool", color="#93c5fd")
    axes[1].set_xticks(range(7))
    axes[1].set_xticklabels(bins)
    axes[1].set_xlabel("donor atom count")
    axes[1].set_ylabel("molecule count")
    axes[1].set_title("Donor-count coverage", fontsize=11)
    axes[1].legend(fontsize=9)
    axes[1].grid(axis="y", alpha=0.25)

    path = outdir / "F1_chemical_space_coverage.png"
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_f2(outdir: Path) -> Path | None:
    """P0 proxy distribution by family, coloured by fluorination (Week 3 only)."""

    source = REPO_ROOT / "outputs" / "week3" / "p0_broad_pool.csv"
    if not source.exists():
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with source.open(encoding="utf-8", newline="") as handle:
        raw_rows = [row for row in csv.DictReader(handle)]
    if not raw_rows:
        return None
    # The Week 3 producer writes p0_ox_ev / p0_red_ev; accept the short names too.
    fields = set(raw_rows[0])
    ox_key = "p0_ox_ev" if "p0_ox_ev" in fields else "p0_ox"
    red_key = "p0_red_ev" if "p0_red_ev" in fields else "p0_red"
    rows = [
        row
        for row in raw_rows
        if (row.get("status") or "").strip() == "ok" and row.get(ox_key)
    ]
    if not rows:
        return None

    families = sorted({row["family"] for row in rows})
    fluorinated = [("fluorinated" in (row.get("functionalization_tags") or "")) for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0))
    for axis, key, label in (
        (axes[0], ox_key, "-eps_HOMO (eV)  [oxidation proxy]"),
        (axes[1], red_key, "+eps_LUMO (eV)  [reduction proxy]"),
    ):
        plain, fluoro = [], []
        for family in families:
            plain.append(
                [float(row[key]) for row, is_f in zip(rows, fluorinated) if row["family"] == family and not is_f]
            )
            fluoro.append(
                [float(row[key]) for row, is_f in zip(rows, fluorinated) if row["family"] == family and is_f]
            )
        positions = list(range(len(families)))
        for offset, values, colour, name in (
            (-0.18, plain, "#1d4ed8", "non-fluorinated"),
            (0.18, fluoro, "#f97316", "fluorinated"),
        ):
            usable = [(p + offset, v) for p, v in zip(positions, values) if v]
            if not usable:
                continue
            xs, ys = zip(*usable)
            axis.boxplot(ys, positions=xs, widths=0.3, patch_artist=True,
                         boxprops={"facecolor": colour, "alpha": 0.75},
                         medianprops={"color": "black"})
            axis.plot([], [], color=colour, label=name)
        axis.set_xticks(positions)
        axis.set_xticklabels(families, rotation=35, ha="right", fontsize=8.5)
        axis.set_ylabel(label, fontsize=9.5)
        axis.grid(axis="y", alpha=0.25)
        axis.legend(fontsize=8.5)
    axes[0].set_title("P0 proxies by family (broad pool)", fontsize=11)
    path = outdir / "F2_p0_distributions_by_family.png"
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def figure_f3(outdir: Path) -> Path | None:
    """The central result: a smaller VALUE error does not buy a better RANKING."""

    summary_path = REPO_ROOT / "outputs" / "week2" / "method_audit_xtb_summary.json"
    if not summary_path.exists():
        return None
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    comparison = summary.get("comparison", {})
    if not comparison:
        return None

    # The r2SCAN-3c arm is optional on purpose: F3 has to keep rendering before
    # the T1 sweep exists, and the whole point of the figure is the comparison it
    # makes possible once it does.
    p1_comparison_path = REPO_ROOT / "outputs" / "week4" / "p1_anchor_comparison.json"
    p1_block = None
    if p1_comparison_path.exists():
        p1_payload = json.loads(p1_comparison_path.read_text(encoding="utf-8"))
        p1_block = p1_payload.get("P1_r2SCAN3c")
        if p1_block and p1_block.get("n"):
            comparison["P1_dscf_vertical"] = p1_block

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = {
        "IP_dscf_vertical": "dSCF vertical IP (P1-like)",
        "IP_koopmans": "Koopmans -eps_HOMO (P0)",
        "EA_koopmans": "Koopmans +eps_LUMO (P0)",
        "EA_dscf_vertical": "dSCF vertical EA",
        "P1_dscf_vertical": "r2SCAN-3c dSCF vertical IP (P1)",
    }
    colours = {
        "IP_dscf_vertical": "#1d4ed8",
        "IP_koopmans": "#dc2626",
        "EA_koopmans": "#16a34a",
        "EA_dscf_vertical": "#f59e0b",
        "P1_dscf_vertical": "#0f766e",
    }

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    offsets = {"P1_dscf_vertical": (14, -34), "IP_koopmans": (14, -30),
               "IP_dscf_vertical": (14, 6), "EA_koopmans": (14, 6),
               "EA_dscf_vertical": (-30, -34)}
    for name, block in comparison.items():
        tau = block.get("kendall_tau_b")
        mae = block.get("mae_ev")
        if tau is None or mae is None:
            continue
        axes[0].scatter(mae, tau, s=110, color=colours.get(name, "#334155"), zorder=3)
        axes[0].annotate(
            labels.get(name, name) + "\n(MAE %.2f eV, tau_b %.3f)" % (mae, tau),
            (mae, tau), textcoords="offset points",
            xytext=offsets.get(name, (12, -6)), fontsize=9,
        )
    axes[0].set_xlabel("mean absolute error vs anchor (eV)  ->  worse VALUE", fontsize=10)
    axes[0].set_ylabel("Kendall tau_b vs anchor ranking  ->  worse RANKING", fontsize=10)
    n_anchor = max((block.get("n", 0) for block in comparison.values()), default=0)
    axes[0].set_title(
        "Value error vs ranking error (n=%d molecules with an anchor)" % n_anchor, fontsize=11
    )
    axes[0].set_ylim(0, 1.05)
    axes[0].grid(alpha=0.25)

    arm = "IP_dscf_vertical" if "IP_dscf_vertical" in comparison else next(iter(comparison))
    pairs = comparison[arm].get("pairs", [])
    p1_pairs = [pair for pair in (p1_block or {}).get("pairs", []) if pair.get("mol_id")]
    if pairs:
        names = [pair["mol_id"] for pair in pairs]
        errors = [pair["error_ev"] for pair in pairs]
        positions = list(range(len(names)))
        width = 0.4 if p1_pairs else 0.8
        offset = 0.2 if p1_pairs else 0.0
        axes[1].bar([p - offset for p in positions], errors, width=width, color="#1d4ed8",
                    alpha=0.85, label="GFN2-xTB dSCF vertical IP error")
        if p1_pairs:
            p1_by_name = {pair["mol_id"]: pair["error_ev"] for pair in p1_pairs}
            axes[1].bar([p + offset for p in positions], [p1_by_name.get(name, 0.0) for name in names],
                        width=width, color="#0f766e", alpha=0.9,
                        label="r2SCAN-3c dSCF vertical IP error")
        axes[1].axhline(0, color="black", linewidth=0.8)
        bias = comparison[arm].get("bias_ev", 0.0)
        axes[1].axhline(bias, color="#dc2626", linestyle="--", linewidth=1.2,
                        label="xTB mean bias %.2f eV" % bias)
        spread = comparison[arm].get("error_std_ev")
        if spread is not None:
            axes[1].axhspan(bias - spread, bias + spread, color="#dc2626", alpha=0.12,
                            label="+/- 1 sd (%.2f eV)" % spread)
        axes[1].set_xticks(positions)
        axes[1].set_xticklabels(names, rotation=35, ha="right", fontsize=8.5)
        axes[1].set_ylabel("computed - anchor (eV)", fontsize=10)
        axes[1].set_title("A nearly constant offset keeps the RANKING intact", fontsize=11)
        axes[1].legend(fontsize=8.5)
        axes[1].grid(axis="y", alpha=0.25)

    path = outdir / "F3_value_error_vs_rank_error.png"
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the project summary figures.")
    parser.add_argument("--outdir", type=Path, default=REPO_ROOT / "outputs" / "figures")
    arguments = parser.parse_args(argv)
    arguments.outdir.mkdir(parents=True, exist_ok=True)

    inputs = [
        REPO_ROOT / "data" / "metadata" / "core_set.csv",
        REPO_ROOT / "data" / "metadata" / "broad_pool.csv",
        REPO_ROOT / "outputs" / "week2" / "method_audit_xtb_summary.json",
        REPO_ROOT / "outputs" / "week3" / "p0_broad_pool.csv",
        REPO_ROOT / "outputs" / "week4" / "p1_anchor_comparison.json",
    ]

    written: list[tuple[str, Path]] = []
    written.append(("F0", figure_f0(arguments.outdir)))
    written.append(("F1", figure_f1(arguments.outdir)))
    optional_f2 = figure_f2(arguments.outdir)
    if optional_f2 is not None:
        written.append(("F2", optional_f2))
    optional_f3 = figure_f3(arguments.outdir)
    if optional_f3 is not None:
        written.append(("F3", optional_f3))

    newline = chr(10)
    lines = [
        "# Figure manifest",
        "",
        "Every figure is regenerated by `scripts/make_summary_figures.py`; the digests below pin",
        "the exact inputs and outputs so a figure cannot silently drift from its numbers.",
        "",
        "| figure | file | what it shows |",
        "| --- | --- | --- |",
    ]
    for tag, path in written:
        lines.append("| " + tag + " | " + path.name + " | " + FIGURE_NOTES.get(tag, "") + " |")
    lines += ["", "## inputs", "", "| file | present | sha256 |", "| --- | --- | --- |"]
    for path in inputs:
        lines.append(
            "| " + path.relative_to(REPO_ROOT).as_posix() + " | "
            + ("yes" if path.exists() else "no") + " | "
            + (sha256_of(path) if path.exists() else "-") + " |"
        )
    lines += ["", "## outputs", "", "| file | sha256 |", "| --- | --- |"]
    for _, path in written:
        lines.append("| " + path.name + " | " + sha256_of(path) + " |")
    lines.append("")
    (arguments.outdir / "figure_manifest.md").write_text(newline.join(lines), encoding="utf-8", newline=newline)

    for tag, path in written:
        print("  " + tag + " -> " + path.relative_to(REPO_ROOT).as_posix())
    print("figures = " + str(len(written)) + "  manifest -> " + (arguments.outdir / "figure_manifest.md").relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())