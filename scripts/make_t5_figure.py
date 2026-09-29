
"""T5 diffuse-function control figure (F9).

Panel (a): vertical EA_dscf = E(anion) - E(neutral) for four molecules under three
settings that share the r2SCAN functional, so the only variable is the basis
(def2-TZVPP without diffuse, def2-TZVPD with diffuse, r2SCAN-3c production).
Positive means the gas-phase radical anion is unbound.  Panel (b): the pure
diffuse shift EA(def2-TZVPD) - EA(def2-TZVPP).

Labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\Scripts\python.exe scripts\make_t5_figure.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = REPO_ROOT / "outputs" / "week4" / "t5_diffuse_control_summary.json"
FIGDIR = REPO_ROOT / "outputs" / "figures"
FIGNAME = "F9_diffuse_function_control.png"
MANIFEST = FIGDIR / "figure_manifest_week4_t5.md"

MOL_ORDER = ("AN", "DMSO", "SN", "VC")
ARM_ORDER = ("scan3c", "tzvpp", "tzvpd")
ARM_LABEL = {
    "scan3c": "r2SCAN-3c (def2-mTZVPP)",
    "tzvpp": "r2SCAN / def2-TZVPP",
    "tzvpd": "r2SCAN / def2-TZVPD (diffuse)",
}
ARM_COLOR = {"scan3c": "#9ca3af", "tzvpp": "#2563eb", "tzvpd": "#16a34a"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
def build_figure(data: dict, outdir: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    by_arm = data["EA_dscf_eV_by_arm"]
    molecules = data["molecules"]
    anchors = {name: molecules[name].get("anchor_ea_eV") for name in MOL_ORDER}

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.4, 4.5))
    x = np.arange(len(MOL_ORDER), dtype=float)
    width = 0.26
    for index, arm in enumerate(ARM_ORDER):
        values = [by_arm[arm][name] for name in MOL_ORDER]
        offset = (index - 1) * width
        bars = ax_a.bar(
            x + offset, values, width,
            label=ARM_LABEL[arm], color=ARM_COLOR[arm],
            edgecolor="white", linewidth=0.6,
        )
        ax_a.bar_label(bars, fmt="%.2f", fontsize=7, padding=2)

    handles, labels = ax_a.get_legend_handles_labels()
    ax_a.axhline(0.0, color="#111827", linewidth=1.3)
    tick_labels = []
    for name in MOL_ORDER:
        anchor = anchors.get(name)
        if anchor is None:
            tick_labels.append(name)
        else:
            tick_labels.append(name + "\n(" + ("%.3f" % anchor) + " eV)")
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(tick_labels, fontsize=9)
    ax_a.text(0.02, 0.90, "values in parentheses = NIST gas-phase EA anchors",
              transform=ax_a.transAxes, fontsize=7, va="top", color="#6b7280")
    ax_a.set_ylabel(r"EA$_{dSCF}$ = E(anion) - E(neutral)   [eV]")
    ax_a.set_title("(a) Adding diffuse functions lowers EA but does not flip its sign")
    ax_a.text(0.02, 0.97, "positive = gas-phase anion unbound", transform=ax_a.transAxes,
              fontsize=7.5, va="top", color="#374151")
    ax_a.set_ylim(0.0, 4.6)
    ax_a.set_xlim(-0.62, len(MOL_ORDER) - 0.38)
    ax_a.legend(handles=handles, labels=labels, fontsize=6.8, frameon=False,
                loc="upper right", ncol=1)

    shift = [molecules[name]["diffuse_shift_eV"]["tzvpd_minus_tzvpp"] for name in MOL_ORDER] \
        if "tzvpd_minus_tzvpp" in molecules[MOL_ORDER[0]]["diffuse_shift_eV"] else \
        [by_arm["tzvpd"][name] - by_arm["tzvpp"][name] for name in MOL_ORDER]
    bars_b = ax_b.bar(x, shift, 0.55, color="#7c3aed", edgecolor="white", linewidth=0.6)
    ax_b.bar_label(bars_b, fmt="%.2f", fontsize=8, padding=2)
    ax_b.axhline(0.0, color="#111827", linewidth=1.3)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(MOL_ORDER)
    ax_b.set_ylabel(r"$\Delta$EA = EA(def2-TZVPD) - EA(def2-TZVPP)   [eV]")
    ax_b.set_title("(b) Pure diffuse shift (same functional, same geometry)")
    ax_b.set_ylim(min(shift) * 1.35, 0.15)

    fig.suptitle("T5: r2SCAN gas-phase EA, basis-set-only control (G1 geometry, vertical)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / FIGNAME
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
def write_manifest(data: dict, figure: Path) -> Path:
    lines = [
        "# Figure manifest - T5 diffuse-function control (F9)",
        "",
        "| figure | file | inputs (SHA256) |",
        "| --- | --- | --- |",
        "| F9 | `" + figure.name + "` | `t5_diffuse_control_summary.json` " + sha256_of(SUMMARY) + " |",
        "",
        "F9 note: panel (a) shows EA_dscf = E(anion) - E(neutral) in eV for the three",
        "arms that share the r2SCAN functional (only the basis changes); positive means",
        "the gas-phase radical anion is unbound. Panel (b) isolates the pure diffuse",
        "shift EA(def2-TZVPD) - EA(def2-TZVPP). All values are vertical (G1 geometry),",
        "gas phase, no continuum. The values in parentheses on the x axis are the NIST",
        "gas-phase EA anchors of AN (0.011 eV) and DMSO (0.014 eV); both sit on the zero",
        "line at this scale, which is exactly why a 0.01 eV-level binding decision lies",
        "outside this method's applicability domain.",
        "",
        "- n_jobs: " + str(data["n_jobs"]) + ", n_ok: " + str(data["n_ok"]) + ", n_failed: " + str(data["n_failed"]),
        "- generated_utc: " + str(data.get("generated_utc", "")),
        "",
        "Labels are English on purpose (no guaranteed CJK font in the workspace).",
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return MANIFEST


def main() -> int:
    if not SUMMARY.exists():
        raise SystemExit("missing " + str(SUMMARY))
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    figure = build_figure(data, FIGDIR)
    manifest = write_manifest(data, figure)
    print("wrote " + str(figure.relative_to(REPO_ROOT)))
    print("wrote " + str(manifest.relative_to(REPO_ROOT)))
    by_arm = data["EA_dscf_eV_by_arm"]
    for name in MOL_ORDER:
        print("%-5s tzvpp=%+.3f  tzvpd=%+.3f  scan3c=%+.3f" % (
            name, by_arm["tzvpp"][name], by_arm["tzvpd"][name], by_arm["scan3c"][name]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())