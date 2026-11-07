"""Stage 5 / T4 (C1) figure (F13): where the redox electron actually goes.

Three panels, all fed by ``outputs/week5/c1_state_identity.json`` -- which is
derived from the Mulliken charge/spin blocks ORCA had already written, so this
figure costs no new quantum chemistry:

(a) Mulliken spin population on Li in the oxidised ([Li M]2+) and reduced
    ([Li M]0) state of every motif.  Near 1 means the redox electron sits on
    lithium, near 0 means it sits on the molecule.  The two frozen indicator
    thresholds (0.15 and 0.5) are drawn as reference lines;
(b) the Mulliken charge of Li in the three states -- the [Li M]+ reference, the
    oxidised state and the reduced state -- so the ~1 e drop of the Li-centred
    reductions is visible next to the ~0.05 e change of the oxidations;
(c) the state-identity label counts of the frozen vocabulary, oxidation and
    reduction separately.

Labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    python scripts\\make_c1_state_identity_figure.py
    python scripts\\make_c1_state_identity_figure.py --outdir <dir> --manifest <file>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEEK5 = REPO_ROOT / "outputs" / "week5"
IDENTITY = WEEK5 / "c1_state_identity.json"
C1_CSV = WEEK5 / "c1_li_coordination.csv"
MOTIFS = WEEK5 / "li_motif_generation.json"
FIGDIR = REPO_ROOT / "outputs" / "figures"
FIGNAME = "F13_c1_state_identity.png"
MANIFEST = FIGDIR / "figure_manifest_week5_state_identity.md"

OX_COLOR = "#1d4ed8"
RED_COLOR = "#b45309"
REF_COLOR = "#6b7280"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path) -> list:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"]
    if not rows:
        raise SystemExit("no state-identity rows in %s" % path)
    return rows


def row_key(row) -> str:
    return "%s %s" % (row["name"], row["motif_id"])


def index_rows(rows) -> dict:
    table = {}
    for row in rows:
        table.setdefault(row_key(row), {})[row["redox_state"]] = row
    return table


def build_figure(payload, outdir: Path, figure_name: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = payload["rows"]
    table = index_rows(rows)
    keys = sorted(table, key=lambda key: (key.split()[1], key.split()[0]))
    axes_labels = [key.replace(" ", " ") for key in keys]
    x = np.arange(len(keys), dtype=float)
    width = 0.38

    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(16.0, 5.6))

    # ---- (a) spin population on Li -----------------------------------------
    ox_spin = [abs(table[key]["dication"]["spin_li_state"] or 0.0) for key in keys]
    red_spin = [abs(table[key]["reduced"]["spin_li_state"] or 0.0) for key in keys]
    ax_a.bar(x - width / 2.0, ox_spin, width, color=OX_COLOR, label="oxidised [Li M]2+")
    ax_a.bar(x + width / 2.0, red_spin, width, color=RED_COLOR, label="reduced [Li M]0")
    ax_a.axhline(0.5, color="#111827", linewidth=0.9, linestyle="--")
    ax_a.axhline(0.15, color="#9ca3af", linewidth=0.9, linestyle=":")
    box = dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor="none")
    ax_a.text(len(keys) - 0.5, 0.52, "0.5 -> Li-centred", fontsize=7.0, ha="right",
              color="#111827", bbox=box)
    ax_a.text(len(keys) - 0.5, 0.17, "0.15 -> molecule-centred", fontsize=7.0, ha="right",
              color="#6b7280", bbox=box)
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(axes_labels, rotation=45, ha="right", fontsize=8)
    ax_a.set_ylim(0.0, 1.18)
    ax_a.set_ylabel("|Mulliken spin population on Li|   [e]")
    ax_a.set_title("(a) Where the redox electron sits\n(oxidised state: every |spin on Li| <= %.3f e)"
                   % max(ox_spin))
    ax_a.legend(fontsize=8.0, frameon=False, loc="upper left")

    # ---- (b) Li Mulliken charge in the three states -------------------------
    q_ref = [table[key]["dication"]["q_li_ref"] or 0.0 for key in keys]
    q_ox = [table[key]["dication"]["q_li_state"] or 0.0 for key in keys]
    q_red = [table[key]["reduced"]["q_li_state"] or 0.0 for key in keys]
    ax_b.bar(x - width, q_ref, width * 0.9, color=REF_COLOR, label="[Li M]+ reference")
    ax_b.bar(x, q_ox, width * 0.9, color=OX_COLOR, label="oxidised [Li M]2+")
    ax_b.bar(x + width, q_red, width * 0.9, color=RED_COLOR, label="reduced [Li M]0")
    ax_b.axhline(0.0, color="#111827", linewidth=1.0)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(axes_labels, rotation=45, ha="right", fontsize=8)
    ax_b.set_ylim(-0.52, 1.12)
    ax_b.set_ylabel("Mulliken charge of Li   [e]")
    ax_b.set_title("(b) Li keeps ~+0.9 e on oxidation, gains ~1 e on reduction")
    ax_b.legend(fontsize=8.0, frameon=False, loc="lower left")

    # ---- (c) label counts --------------------------------------------------
    counts = payload["per_redox_state"]
    states = ["dication", "reduced"]
    name_map = {
        "molecule_centered_redox": ("molecule_centered_redox", "#059669"),
        "Li_centered_or_mixed_redox": ("Li_centered_or_mixed_redox", RED_COLOR),
        "no_intact_minimum_found": ("no_intact_minimum_found", "#7c3aed"),
        "motif_switch": ("motif switch", "#0891b2"),
        "dissociated_optimized_product": ("dissociated product", "#be123c"),
        "state_identity_ambiguous": ("ambiguous", "#a16207"),
    }
    position = np.arange(len(states), dtype=float)
    bottom = np.zeros(len(states))
    for label, (pretty, colour) in name_map.items():
        values = [counts[state]["labels"].get(label, 0) for state in states]
        if not any(values):
            continue
        ax_c.bar(position, values, 0.55, bottom=bottom, color=colour, label=pretty)
        for xpos, value, base in zip(position, values, bottom):
            if not value:
                continue
            # Label the segments in place: a legend here would cover the counts.
            caption = "%s %d" % (pretty, value) if xpos == 0 else str(value)
            ax_c.text(xpos, base + value / 2.0, caption, ha="center", va="center",
                      fontsize=7.0 if xpos == 0 else 9.0, color="white")
        bottom = bottom + np.asarray(values, dtype=float)
    ax_c.set_xticks(position)
    ax_c.set_xticklabels(["oxidised\n[Li M]2+", "reduced\n[Li M]0"], fontsize=9)
    ax_c.set_ylim(0.0, max(bottom) * 1.18 if max(bottom) else 1.0)
    ax_c.set_ylabel("number of motifs")
    ax_c.set_title("(c) state-identity labels (frozen vocabulary)")

    fig.suptitle("Stage 5 / T4 (F13): state identity of the Li+-coordinated redox states, "
                 "r2SCAN-3c Mulliken analysis", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / figure_name
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path

def write_manifest(manifest_path: Path, figure_path: Path, identity_path: Path, payload) -> Path:
    ox = payload["per_redox_state"]["dication"]
    red = payload["per_redox_state"]["reduced"]
    thresholds = payload["thresholds"]
    rows = payload["rows"]
    red_rows = [row for row in rows if row["redox_state"] == "reduced"]
    li_like = [row for row in red_rows if row["state_identity_label"] == "Li_centered_or_mixed_redox"]
    spin_lo = min((row["spin_li_state"] for row in li_like), default=None)
    lines = [
        "# Figure manifest - Stage 5 / T4 C1 state identity (F13)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F13 | `" + figure_path.name + "` | " + sha256_of(figure_path)
        + " | `c1_state_identity.json` " + sha256_of(identity_path)
        + " | `c1_li_coordination.csv` " + sha256_of(C1_CSV) + " |",
        "| | | | `li_motif_generation.json` " + sha256_of(MOTIFS) + " |",
        "",
        "F13 note: the classification is read off the Mulliken charge/spin block that",
        "every C1 ORCA job already wrote, so the figure costs no new quantum chemistry.",
        "Panel (a) is the Mulliken projection of the singly occupied orbital onto Li,",
        "used as the practical stand-in for the SOMO/LUMO localisation that",
        "config/scientific_definitions.yaml requires; panel (b) is the same evidence",
        "seen as a charge ladder. Both come from the relaxed redox geometry where the",
        "state was re-optimised and from the gas-phase vertical single point otherwise.",
        "",
        "- n (molecule, motif, redox state) determinations: " + str(payload["n_rows"]),
        "- oxidised [Li M]2+: " + "; ".join("%s %d" % (key, value)
                                            for key, value in ox["labels"].items()),
        "- reduced [Li M]0: " + "; ".join("%s %d" % (key, value)
                                          for key, value in red["labels"].items()),
        "- frozen indicator thresholds: spin "
        + str(thresholds["spin_li_molecule_centered"]) + " / "
        + str(thresholds["spin_li_centered"]) + ", charge "
        + str(thresholds["charge_li_molecule_centered"]) + " / "
        + str(thresholds["charge_li_centered"]),
        "- lowest |spin on Li| among the " + str(len(li_like))
        + " Li-centred reductions: " + ("%.3f" % spin_lo if spin_lo is not None else "n/a"),
        "",
        payload["definition"],
        "",
        "Labels are English on purpose (no guaranteed CJK font in the workspace).",
    ]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8", newline=chr(10))
    return manifest_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render the F13 C1 state-identity figure and its manifest.")
    parser.add_argument("--identity", default=str(IDENTITY),
                        help="c1_state_identity.json (default: " + str(IDENTITY) + ")")
    parser.add_argument("--outdir", default=str(FIGDIR),
                        help="output directory for the PNG (default: " + str(FIGDIR) + ")")
    parser.add_argument("--figure-name", default=FIGNAME,
                        help="PNG file name (default: " + FIGNAME + ")")
    parser.add_argument("--manifest", default=str(MANIFEST),
                        help="manifest markdown path (default: " + str(MANIFEST) + ")")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    identity_path = Path(args.identity)
    payload = json.loads(identity_path.read_text(encoding="utf-8"))
    figure = build_figure(payload, Path(args.outdir), args.figure_name)
    manifest = write_manifest(Path(args.manifest), figure, identity_path, payload)
    print("wrote " + str(figure))
    print("wrote " + str(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())