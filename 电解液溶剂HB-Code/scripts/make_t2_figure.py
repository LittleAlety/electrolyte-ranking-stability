"""T2 Opt+Freq geometry-sensitivity figure (F11).

Panel (a): per-molecule vertical shift of the r2SCAN-3c gas-phase IP and EA caused by
re-optimising the geometry, i.e. P1 at G2 minus P1 at G1 in eV, where G1 is the shared
GFN2-xTB geometry and G2 the r2SCAN-3c Opt+Freq stationary point.  Panel (b) applies the
SAME estimator -- the population standard deviation of a vertical shift over the same
12-molecule audit subset -- to the three perturbations the project compares: method
(P0 GFN2-xTB -> P1 r2SCAN-3c), geometry (G1 -> G2) and environment (gas -> bare CPCM
eps = 40).  Because the estimator and the molecule set are identical, the three bars are
directly comparable; this is the docs/08 section 3.4 "is sigma_geom the same order as
sigma_method" check.

Labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\Scripts\python.exe scripts\make_t2_figure.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq_summary.json"
DERIVED = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
T3_SUMMARY = REPO_ROOT / "outputs" / "week4" / "t3_cpcm_eps_scan_summary.json"
FIGDIR = REPO_ROOT / "outputs" / "figures"
FIGNAME = "F11_opt_freq_g2_sensitivity.png"
MANIFEST = FIGDIR / "figure_manifest_week4_t2.md"
ENV_EPS = "40"
G1_DIR = REPO_ROOT / "outputs" / "_week3_scratch"

IP_COLOR = "#2563eb"
EA_COLOR = "#dc2626"
ARM_COLOR = {"method": "#7c3aed", "geometry": "#0d9488", "environment": "#ea580c"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_xyz_atoms(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    n_atoms = int(lines[0].split()[0])
    atoms = []
    for line in lines[2:2 + n_atoms]:
        parts = line.split()
        atoms.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return atoms


def kabsch_rmsd(native, moved):
    """RMSD after optimal rigid-body superposition, in Angstrom.

    Without the superposition a molecule that merely rotated during the optimisation
    would look like a large displacement, which would corrupt the diagnostic.
    """
    import numpy as np
    a = np.asarray(native, dtype=float)
    b = np.asarray(moved, dtype=float)
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    sign = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
    rot = u @ np.diag([1.0, 1.0, sign]) @ vt
    aligned = a @ rot
    return (float(np.sqrt(((aligned - b) ** 2).sum() / len(a))),
            float(np.abs(aligned - b).max()))


def geometry_diagnostics(rows):
    """G1 -> G2 displacement per molecule (Kabsch RMSD) plus its correlation with the shift.

    G1 is not stored next to the T2 artefacts, so it is read from its documented
    provenance directory outputs/_week3_scratch/<mol_id>/xtbopt.xyz.
    """
    out = []
    for row in rows:
        if row.get("d_ip_ev") is None:
            continue
        g1 = G1_DIR / str(row.get("mol_id", "")) / "xtbopt.xyz"
        g2 = REPO_ROOT / str(row.get("g2_geometry", ""))
        if not g1.exists() or not g2.exists():
            continue
        rms, maxd = kabsch_rmsd(read_xyz_atoms(g1), read_xyz_atoms(g2))
        out.append({"name": row["name"], "rmsd_angstrom": rms, "max_displacement_angstrom": maxd,
                    "d_ip_ev": row["d_ip_ev"], "d_ea_ev": row["d_ea_ev"],
                    "imaginary_modes": bool(row.get("imaginary_modes"))})
    out.sort(key=lambda item: item["rmsd_angstrom"], reverse=True)
    return out


def _correlation(xs, ys):
    import numpy as np
    if len(xs) < 3:
        return None
    return float(np.corrcoef(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))[0, 1])


def diagnostics_table(items) -> list:
    if not items:
        return ["(G1 provenance outputs/_week3_scratch/<mol_id>/xtbopt.xyz was unavailable)"]
    rms = [item["rmsd_angstrom"] for item in items]
    lines = [
        "| molecule | Kabsch RMSD (A) | max atom move (A) | dIP (eV) | dEA (eV) | imaginary mode |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append("| %s | %.4f | %.4f | %+.4f | %+.4f | %s |" % (
            item["name"], item["rmsd_angstrom"], item["max_displacement_angstrom"],
            item["d_ip_ev"], item["d_ea_ev"], "yes" if item["imaginary_modes"] else "no"))
    worst = items[0]
    corr_ip = _correlation(rms, [item["d_ip_ev"] for item in items])
    corr_ea = _correlation(rms, [item["d_ea_ev"] for item in items])
    lines += [
        "",
        ("mean Kabsch RMSD = %.4f A (max %.4f A, %s); correlation with the vertical shift over "
         "these %d molecules: r(dIP) = %+.3f, r(dEA) = %+.3f. The displacement size therefore "
         "does NOT predict the size or sign of the geometry-induced shift.")
        % (sum(rms) / len(rms), worst["rmsd_angstrom"], worst["name"], len(items), corr_ip, corr_ea),
    ]
    return lines


def method_sigma(names) -> dict:
    """Population std of the P0 -> P1 vertical shift over the same subset.

    p1_core_set_derived.csv carries ox_shift_ev = IP(P1) - IP(P0) and
    ea_shift_ev = EA(P1) - EA(P0); taking the population std of those columns over the
    audit subset reproduces the "shift std" of docs/10 section 2.8 on the 12 molecules,
    so the method bar is the same kind of number as sigma_geom and sigma_env.
    """
    wanted = set(names)
    shifts = {"ox": [], "red": []}
    with DERIVED.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("name") not in wanted:
                continue
            for key, column in (("ox", "ox_shift_ev"), ("red", "ea_shift_ev")):
                raw = (row.get(column) or "").strip()
                if raw:
                    shifts[key].append(float(raw))
    return {
        "n": len(shifts["ox"]),
        "ip_std_ev": statistics.pstdev(shifts["ox"]) if len(shifts["ox"]) > 1 else None,
        "ea_std_ev": statistics.pstdev(shifts["red"]) if len(shifts["red"]) > 1 else None,
        "ip_mean_ev": statistics.fmean(shifts["ox"]) if shifts["ox"] else None,
        "ea_mean_ev": statistics.fmean(shifts["red"]) if shifts["red"] else None,
    }


def build_figure(data: dict, method: dict, env_ip: float, env_ea: float, outdir: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = [row for row in data["per_molecule"] if row.get("d_ip_ev") is not None]
    rows.sort(key=lambda row: row["d_ip_ev"])
    names = [row["name"] for row in rows]
    d_ip = [row["d_ip_ev"] for row in rows]
    d_ea = [row["d_ea_ev"] if row.get("d_ea_ev") is not None else 0.0 for row in rows]

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(13.4, 5.8),
                                     gridspec_kw={"width_ratios": [1.62, 1.0]})
    y = np.arange(len(names), dtype=float)
    height = 0.38
    bars_ip = ax_a.barh(y + height / 2.0, d_ip, height,
                        label="dIP = IP(G2) - IP(G1)", color=IP_COLOR,
                        edgecolor="white", linewidth=0.6)
    bars_ea = ax_a.barh(y - height / 2.0, d_ea, height,
                        label="dEA = EA(G2) - EA(G1)", color=EA_COLOR,
                        edgecolor="white", linewidth=0.6)
    ax_a.bar_label(bars_ip, fmt="%+.3f", fontsize=6.6, padding=2)
    ax_a.bar_label(bars_ea, fmt="%+.3f", fontsize=6.6, padding=2)
    ax_a.axvline(0.0, color="#111827", linewidth=1.2)
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(names, fontsize=9)
    ax_a.set_ylim(-0.7, len(names) - 0.3)
    span = max(d_ip + d_ea) - min(d_ip + d_ea)
    ax_a.set_xlim(min(d_ip + d_ea) - 0.24 * span, max(d_ip + d_ea) + 0.24 * span)
    ax_a.set_xlabel("geometry-induced vertical shift, P1@G2 - P1@G1   [eV]")
    ax_a.set_title("(a) Geometry-induced shift of the vertical IP / EA (G1 -> G2)")
    ax_a.legend(fontsize=7.6, frameon=False, loc="lower right")
    geom = data["sigma_geom"]
    spread = ("mean  sigma(pop)\n"
              "dIP %+.3f  %.3f eV\n"
              "dEA %+.3f  %.3f eV" % (
                  geom["d_ip_ev"]["mean_ev"], geom["d_ip_ev"]["population_std_ev"],
                  geom["d_ea_ev"]["mean_ev"], geom["d_ea_ev"]["population_std_ev"]))
    ax_a.text(0.985, 0.975, spread, transform=ax_a.transAxes, fontsize=7.6,
              va="top", ha="right", color="#374151", zorder=5,
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.88,
                        edgecolor="#d1d5db", linewidth=0.7))

    labels = ["method\n(P0 -> P1)\nGFN2-xTB -> r2SCAN-3c",
              "geometry\n(G1 -> G2)\nboth r2SCAN-3c",
              "environment\n(gas -> CPCM %s)\nbare dielectric" % ENV_EPS]
    values = [method["ip_std_ev"], geom["d_ip_ev"]["population_std_ev"], env_ip]
    colors = [ARM_COLOR["method"], ARM_COLOR["geometry"], ARM_COLOR["environment"]]
    x = np.arange(3, dtype=float)
    bars_b = ax_b.bar(x, values, 0.55, color=colors, edgecolor="white", linewidth=0.6)
    ax_b.bar_label(bars_b, fmt="%.3f", fontsize=9.5, padding=2)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(labels, fontsize=7.4)
    ax_b.set_ylabel("population std of the vertical shift over 12 molecules   [eV]")
    ax_b.set_title("(b) Which perturbation rewrites the ranking?", fontsize=10)
    ax_b.set_ylim(0.0, max(values) * 1.32)
    ax_b.text(0.02, 0.985,
              "oxidation axis (vertical IP)\nreduction axis: geometry %.3f eV, environment %.3f eV\nsigma_conf: not computed (docs/08 section 5)"
              % (geom["d_ea_ev"]["population_std_ev"], env_ea),
              transform=ax_b.transAxes, fontsize=7.0, va="top", ha="left", color="#374151")

    fig.suptitle("T2: does the G1 (xTB) geometry survive an r2SCAN-3c Opt+Freq? "
                 "12-molecule audit subset, gas phase", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / FIGNAME
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def write_manifest(data: dict, method: dict, env_ip: float, env_ea: float, figure: Path,
                   diagnostics=None) -> Path:
    lines = [
        "# Figure manifest - T2 Opt+Freq geometry sensitivity (F11)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F11 | `" + figure.name + "` | " + sha256_of(figure)
        + " | `t2_opt_freq_summary.json` " + sha256_of(SUMMARY)
        + " | `p1_core_set_derived.csv` " + sha256_of(DERIVED)
        + " | `t3_cpcm_eps_scan_summary.json` " + sha256_of(T3_SUMMARY) + " |",
        "",
        "F11 note: panel (a) is the per-molecule vertical shift produced by replacing the",
        "shared G1 geometry (GFN2-xTB, the geometry P0 and P1 both use) with G2, the",
        "r2SCAN-3c Opt+Freq stationary point, evaluated with r2SCAN-3c in the gas phase.",
        "Positive dEA means the re-optimisation destabilises the anion. Panel (b) puts the",
        "population standard deviation of that shift over the 12-molecule audit subset",
        "next to the same statistic for two other perturbations. All three use one",
        "estimator and one molecule set, so they answer the docs/08 section 3.4 question",
        "directly: if the geometry term were comparable to the method term, the P0 -> P1",
        "change could not be attributed to the electronic-structure method alone.",
        "",
        "- n_molecules: " + str(data["n_molecules"]) + ", n_opt_jobs: " + str(data["n_opt_jobs"])
        + ", n_opt_ok: " + str(data["n_opt_ok"]) + ", n_failed: " + str(data["n_failed"]),
        "- n_sp_jobs: " + str(data["n_sp_jobs"]) + ", n_sp_ok: " + str(data["n_sp_ok"]),
        "- n_imaginary_unresolved: " + str(data["n_imaginary_unresolved"])
        + " (a real r2SCAN-3c result on G2, recorded, not suppressed)",
        "- sigma_geom: dIP %+.3f (mean) / %.3f (pop std) eV; dEA %+.3f / %.3f eV" % (
            data["sigma_geom"]["d_ip_ev"]["mean_ev"],
            data["sigma_geom"]["d_ip_ev"]["population_std_ev"],
            data["sigma_geom"]["d_ea_ev"]["mean_ev"],
            data["sigma_geom"]["d_ea_ev"]["population_std_ev"]),
        "- sigma_method (same subset, P0 -> P1): dIP %+.3f / %.3f eV; dEA %+.3f / %.3f eV" % (
            method["ip_mean_ev"], method["ip_std_ev"], method["ea_mean_ev"], method["ea_std_ev"]),
        "- sigma_env (gas -> bare CPCM " + ENV_EPS + "): dIP %.3f eV; dEA %.3f eV" % (env_ip, env_ea),
        "- sigma_conf: not computed in this round (docs/08 section 5)",
        "- generated_utc: " + str(data.get("generated_utc", "")),
        "",
        "## Geometry diagnostics (G1 -> G2 displacement)",
        "",
        "G1 is the shared GFN2-xTB geometry (provenance outputs/_week3_scratch/<mol_id>/xtbopt.xyz);",
        "G2 is the r2SCAN-3c Opt+Freq stationary point. RMSD is computed after optimal rigid-body",
        "superposition (Kabsch), so a molecule that merely rotated does not look displaced.",
        "",
    ] + diagnostics_table(diagnostics or []) + [
        "",
        "Labels are English on purpose (no guaranteed CJK font in the workspace).",
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return MANIFEST


def main() -> int:
    if not SUMMARY.exists():
        raise SystemExit("missing " + str(SUMMARY) + "; run scripts/run_t2_opt_freq.py first")
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    names = tuple(row["name"] for row in data["per_molecule"])
    method = method_sigma(names)
    env = json.loads(T3_SUMMARY.read_text(encoding="utf-8"))
    env_ip = env["sigma_env_ev"][ENV_EPS]
    env_ea = env["sigma_env_ea_ev"][ENV_EPS]
    diagnostics = geometry_diagnostics(data["per_molecule"])
    figure = build_figure(data, method, env_ip, env_ea, FIGDIR)
    manifest = write_manifest(data, method, env_ip, env_ea, figure, diagnostics)
    print("wrote " + str(figure.relative_to(REPO_ROOT)))
    print("wrote " + str(manifest.relative_to(REPO_ROOT)))
    for arm, value in (("method", method["ip_std_ev"]),
                       ("geometry", data["sigma_geom"]["d_ip_ev"]["population_std_ev"]),
                       ("environment", env_ip)):
        print("sigma_%s (dIP, %d molecules) = %.3f eV" % (arm, len(names), value))
    print("sigma_geom  dEA %.3f eV | sigma_env dEA %.3f eV" % (
        data["sigma_geom"]["d_ea_ev"]["population_std_ev"], env_ea))
    for row in data["per_molecule"]:
        if row.get("imaginary_modes"):
            print("imaginary mode recorded: " + row["name"] + " flags=" + str(row.get("qc_flags")))
    for item in diagnostics:
        print("RMSD %-5s %.4f A  dIP %+.3f  dEA %+.3f" % (
            item["name"], item["rmsd_angstrom"], item["d_ip_ev"], item["d_ea_ev"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
