"""T3 bare-CPCM dielectric scan figure (F10).

Panel (a): the mean (and population std) of the vertical gas -> bare-CPCM(eps)
shift of IP and EA, against the dielectric constant on a log axis. The point at
eps = 1 is the gas phase itself -- the shift is 0 there *by definition* -- and is
drawn hollow to make that explicit; it is a reference point, not a CPCM run.

Panel (b): how the two decision-relevant quantities move with the dielectric --
``sigma_env`` (the molecule-to-molecule spread of the shift, left axis, eV) and
the Kendall tau-b of the screened ranking against the gas-phase P1 ranking
(right axis, 1.0 = same order).

All labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_eps_scan_figure.py
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_cpcm_eps_scan import (  # noqa: E402
    CORE_SET,
    EPS_VALUES,
    P1_CSV,
    gas_energies,
    load_core_set,
    load_state_table,
    resolve_subset,
    vertical_ip_ea,
)

CSV = REPO_ROOT / "outputs" / "week4" / "t3_cpcm_eps_scan.csv"
SUMMARY = REPO_ROOT / "outputs" / "week4" / "t3_cpcm_eps_scan_summary.json"
FIGDIR = REPO_ROOT / "outputs" / "figures"
FIGNAME = "F10_cpcm_eps_scan.png"
MANIFEST = FIGDIR / "figure_manifest_week4_t3.md"

#: eps = 1 is the unscreened (gas-phase) limit and is added to every curve.
GAS_EPS = 1.0


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gas_spreads(p1_path: Path) -> dict:
    """Mean / population std of the gas-phase vertical IP and EA over the subset."""

    table = load_state_table(p1_path)
    subset = resolve_subset(load_core_set(CORE_SET))
    ips, eas = [], []
    for row in subset:
        ip, ea = vertical_ip_ea(gas_energies(table, row["name"]), row["name"])
        if ip is not None:
            ips.append(ip)
        if ea is not None:
            eas.append(ea)
    return {
        "n": len(ips),
        "ip_mean_ev": statistics.fmean(ips) if ips else None,
        "ip_std_ev": statistics.pstdev(ips) if len(ips) > 1 else None,
        "ea_mean_ev": statistics.fmean(eas) if eas else None,
        "ea_std_ev": statistics.pstdev(eas) if len(eas) > 1 else None,
    }

def shift_curves(per_eps, eps_values):
    """The panel (a) series, each with the eps = 1 gas point prepended."""

    xs = [GAS_EPS, *[float(eps) for eps in eps_values]]
    curves = []
    for mean_key, std_key in (("d_ip_mean_ev", "d_ip_std_ev"), ("d_ea_mean_ev", "d_ea_std_ev")):
        means, errors = [0.0], [0.0]
        for eps in eps_values:
            block = per_eps["%g" % float(eps)]
            means.append(block[mean_key])
            errors.append(block[std_key] or 0.0)
        curves.append((means, errors))
    return xs, curves[0], curves[1]


def decision_curves(per_eps, decisions, eps_values):
    """The panel (b) series: sigma_env on the left axis, Kendall tau_b on the right."""

    xs = [GAS_EPS, *[float(eps) for eps in eps_values]]
    sigma_ip = [0.0] + [per_eps["%g" % float(eps)]["sigma_env_ev"] for eps in eps_values]
    sigma_ea = [0.0] + [per_eps["%g" % float(eps)]["sigma_env_ea_ev"] for eps in eps_values]
    tau_ox = [1.0] + [decisions["%g" % float(eps)]["oxidation"].get("kendall_tau_b") for eps in eps_values]
    tau_red = [1.0] + [decisions["%g" % float(eps)]["reduction"].get("kendall_tau_b") for eps in eps_values]
    return xs, sigma_ip, sigma_ea, tau_ox, tau_red


def build_figure(per_eps, decisions, eps_values, gas, outdir: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs, (d_ip_mean, d_ip_err), (d_ea_mean, d_ea_err) = shift_curves(per_eps, eps_values)
    _, sigma_ip, sigma_ea, tau_ox, tau_red = decision_curves(per_eps, decisions, eps_values)
    tick_labels = ["1\n(gas)"] + ["%g" % float(eps) for eps in eps_values]

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.6))

    axis = axes[0]
    axis.axhline(0.0, color="#111827", linewidth=1.0)
    axis.errorbar(xs, d_ip_mean, yerr=d_ip_err, color="#1d4ed8", linewidth=1.8,
                  marker="o", markersize=5.5, capsize=4, elinewidth=1.2,
                  label=r"$\Delta$IP = IP(CPCM $\epsilon$) - IP(gas)")
    axis.errorbar(xs, d_ea_mean, yerr=d_ea_err, color="#0f766e", linewidth=1.8,
                  marker="s", markersize=5.5, capsize=4, elinewidth=1.2,
                  label=r"$\Delta$EA = EA(CPCM $\epsilon$) - EA(gas)")
    axis.plot([xs[0]], [d_ip_mean[0]], marker="o", markersize=10, markerfacecolor="white",
              markeredgecolor="#1d4ed8", markeredgewidth=1.9, linestyle="none", zorder=5)
    axis.plot([xs[0]], [d_ea_mean[0]], marker="s", markersize=10, markerfacecolor="white",
              markeredgecolor="#0f766e", markeredgewidth=1.9, linestyle="none", zorder=5)
    axis.set_xscale("log")
    axis.set_xticks(xs)
    axis.set_xticklabels(tick_labels)
    axis.set_xlim(0.8, 52.0)
    axis.set_xlabel(r"dielectric constant $\epsilon$ of the bare CPCM continuum")
    axis.set_ylabel("shift from the gas phase (eV)")
    axis.set_title("(a) the shift saturates as the dielectric grows", fontsize=11)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8.5, loc="center right", frameon=False)
    axis.text(0.03, 0.05,
              r"$\epsilon$ = 1 (hollow) is the gas-phase P1 reference: the shift is 0 there"
              "\nby definition -- it is not a CPCM calculation.",
              transform=axis.transAxes, fontsize=7.5, va="bottom", color="#6b7280")
    axis.text(0.03, 0.95,
              "gas-phase 1$\\sigma$ across the subset:  IP %.2f eV,  EA %.2f eV"
              % (gas["ip_std_ev"] or 0.0, gas["ea_std_ev"] or 0.0),
              transform=axis.transAxes, fontsize=7.5, va="top", color="#6b7280")

    axis = axes[1]
    axis.plot(xs, sigma_ip, marker="o", markersize=5.5, color="#1d4ed8", linewidth=1.8,
              label=r"$\sigma_{env}$ of $\Delta$IP  (eV)")
    axis.plot(xs, sigma_ea, marker="s", markersize=5.5, color="#0f766e", linewidth=1.8,
              label=r"$\sigma_{env}$ of $\Delta$EA  (eV)")
    axis.set_xscale("log")
    axis.set_xticks(xs)
    axis.set_xticklabels(tick_labels)
    axis.set_xlim(0.8, 52.0)
    axis.set_xlabel(r"dielectric constant $\epsilon$ of the bare CPCM continuum")
    axis.set_ylabel(r"$\sigma_{env}$ (eV) -- molecule-to-molecule spread of the shift")
    axis.grid(alpha=0.25)
    axis.set_title("(b) spread of the shift vs rank agreement with the gas phase", fontsize=11)

    twin = axis.twinx()
    twin.plot(xs, tau_ox, marker="^", markersize=6, linestyle="--", color="#b91c1c",
              linewidth=1.5, label=r"$\tau_b$ oxidation vs gas")
    twin.plot(xs, tau_red, marker="v", markersize=6, linestyle="--", color="#7c3aed",
              linewidth=1.5, label=r"$\tau_b$ reduction vs gas")
    twin.axhline(0.0, color="#111827", linewidth=0.8)
    twin.set_ylabel(r"Kendall $\tau_b$ against the gas-phase P1 ranking")
    twin.set_ylim(-0.12, 1.08)

    handles = axis.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = axis.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    axis.legend(handles, labels, fontsize=8, loc="center right", frameon=False)

    fig.suptitle(
        "T3: bare CPCM dielectric scan of the audit subset -- r2SCAN-3c, G1 geometry, "
        "vertical ionisation:  n = %d molecules x 3 states x %d dielectrics"
        % (gas["n"], len(eps_values)),
        fontsize=10.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / FIGNAME
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path

def write_manifest(summary, figure: Path, gas) -> Path:
    lines = [
        "# Figure manifest - T3 bare-CPCM dielectric scan (F10)",
        "",
        "| figure | file | inputs (SHA256) |",
        "| --- | --- | --- |",
        "| F10 | `" + figure.name + "` | `t3_cpcm_eps_scan_summary.json` " + sha256_of(SUMMARY)
        + " | `t3_cpcm_eps_scan.csv` " + sha256_of(CSV) + " | `p1_core_set.csv` " + sha256_of(P1_CSV) + " |",
        "",
        "F10 note: panel (a) shows the mean of the vertical gas -> bare-CPCM(eps) shift of IP",
        "and EA against the dielectric constant on a log axis, with error bars giving the",
        "population std over the molecules of the subset. The hollow marker at eps = 1 is the",
        "gas-phase P1 reference: the shift is zero there by definition, so eps = 1 is a reference",
        "point and NOT a CPCM calculation. Panel (b) puts sigma_env (left axis, eV) -- the",
        "molecule-to-molecule population std of that shift, which is 0 eV at the gas reference --",
        "next to the Kendall tau-b of the screened ranking against the gas-phase P1 ranking",
        "(right axis, 1.0 at the gas reference). The method (r2SCAN-3c) and the geometry (G1)",
        "are fixed throughout; the only variable is the bare CPCM dielectric, with no SMD",
        "non-electrostatic terms.",
        "",
        "- n_molecules: %d, n_jobs: %d, n_ok: %d, n_failed: %d, n_missing: %d" % (
            summary["n_molecules"], summary["n_jobs"], summary["n_ok"],
            summary["n_failed"], summary["n_missing"]),
        "- gas-phase 1-sigma across the subset: IP %.3f eV, EA %.3f eV" % (
            gas["ip_std_ev"] or 0.0, gas["ea_std_ev"] or 0.0),
        "- generated_utc: " + str(summary.get("generated_utc", "")),
        "",
        "Labels are English on purpose (no guaranteed CJK font in the workspace).",
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return MANIFEST


def main() -> int:
    if not SUMMARY.exists():
        raise SystemExit("missing " + str(SUMMARY) + "; run scripts/analyze_cpcm_eps_scan.py first")
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    gas = gas_spreads(P1_CSV)
    eps_values = summary["eps_values"]
    figure = build_figure(summary["per_eps"], summary["decisions"], eps_values, gas, FIGDIR)
    manifest = write_manifest(summary, figure, gas)
    print("wrote " + str(figure.relative_to(REPO_ROOT)))
    print("wrote " + str(manifest.relative_to(REPO_ROOT)))
    for eps in eps_values:
        key = "%g" % float(eps)
        print("eps=%-3g sigma_env(IP)=%.3f eV  sigma_env(EA)=%.3f eV  tau_b ox/red = %.3f / %.3f" % (
            eps, summary["per_eps"][key]["sigma_env_ev"], summary["per_eps"][key]["sigma_env_ea_ev"],
            summary["decisions"][key]["oxidation"]["kendall_tau_b"],
            summary["decisions"][key]["reduction"]["kendall_tau_b"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())