"""Stage 2 / P1 -> P2 analysis: what does a continuum solvent actually change?

Why this module exists
----------------------
docs/08 section 1 fixes the second single-variable step of the ladder:

    P1 -> P2   change the environment only  (method r2SCAN-3c and geometry G1 fixed)

So this module takes the gas-phase T1 sweep and the SMD(acetonitrile) P2 sweep --
same functional, same basis, same dispersion, same grid, same G1 geometry, same
charge and multiplicity -- and asks the same question the P0 -> P1 analysis asks:
is the solvent a constant offset on the values, or does it reorder the materials?

Because the geometry is not allowed to relax, the difference is purely the
electronic response of the continuum: no geometry relaxation can hide inside it.

Outputs
-------
outputs/week4/p2_environment_effects.csv      per molecule: the gas -> solvent shift
outputs/week4/p2_decision_stability.json/md   P1 -> P2 and P0 -> P2 decision numbers
outputs/figures/F8_environment_layer_p1_to_p2.png
outputs/figures/figure_manifest_week4_p2.md
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_p1_core_set import (  # noqa: E402
    Z_PRIMARY,
    Z_SENSITIVITY,
    _float,
    layer_stability,
)

HARTREE_TO_EV = 27.211386245988
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_FIGDIR = REPO_ROOT / "outputs" / "figures"
P1_CSV = DEFAULT_OUTDIR / "p1_core_set.csv"
P2_CSV = DEFAULT_OUTDIR / "p2_core_set_smd_acetonitrile.csv"
P0_CSV = REPO_ROOT / "outputs" / "week3" / "p0_core_set.csv"

COLUMNS = [
    "mol_id", "name", "family", "role", "status",
    "ip_gas_ev", "ip_smd_ev", "d_ip_ev", "d_ip_ev_per_unit",
    "ea_gas_ev", "ea_smd_ev", "d_ea_ev",
    "p1_ox_ev", "p2_ox_ev", "p1_red_ev", "p2_red_ev",
    "ox_shift_ev", "red_shift_ev", "qc_flags",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="P1 -> P2 (gas -> continuum solvent) analysis.")
    parser.add_argument("--p1", type=Path, default=P1_CSV)
    parser.add_argument("--p2", type=Path, default=P2_CSV)
    parser.add_argument("--p0", type=Path, default=P0_CSV)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--figdir", type=Path, default=DEFAULT_FIGDIR)
    return parser.parse_args(argv)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_states(path: Path) -> dict:
    """(name, state) -> row, for either the T1 or the P2 table."""

    out = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[(row["name"], row["state"])] = row
    return out


def molecule_record(name: str, gas: dict, smd: dict) -> dict:
    """Everything P1 -> P2 needs for one molecule, from the two state tables."""

    def energy(table, state):
        row = table.get((name, state))
        if row is None or row.get("status") != "ok":
            return None
        return _float(row.get("final_energy_eh"))

    g_neu, g_cat, g_an = energy(gas, "neutral"), energy(gas, "cation"), energy(gas, "anion")
    s_neu, s_cat, s_an = energy(smd, "neutral"), energy(smd, "cation"), energy(smd, "anion")

    ip_gas = None if (g_neu is None or g_cat is None) else (g_cat - g_neu) * HARTREE_TO_EV
    ip_smd = None if (s_neu is None or s_cat is None) else (s_cat - s_neu) * HARTREE_TO_EV
    ea_gas = None if (g_neu is None or g_an is None) else (g_neu - g_an) * HARTREE_TO_EV
    ea_smd = None if (s_neu is None or s_an is None) else (s_neu - s_an) * HARTREE_TO_EV

    reference = (
        gas.get((name, "neutral"))
        or gas.get((name, "cation"))
        or gas.get((name, "anion"))
        or {}
    )
    flags = sorted({
        flag
        for table in (gas, smd)
        for state in ("neutral", "cation", "anion")
        for flag in ((table.get((name, state)) or {}).get("qc_flags") or "").split(";")
        if flag
    })
    return {
        "mol_id": reference.get("mol_id", ""),
        "name": name,
        "family": reference.get("family", ""),
        "role": reference.get("role", ""),
        "status": "ok" if None not in (ip_gas, ip_smd, ea_gas, ea_smd) else "incomplete",
        "ip_gas_ev": ip_gas,
        "ip_smd_ev": ip_smd,
        "d_ip_ev": None if None in (ip_gas, ip_smd) else ip_smd - ip_gas,
        "ea_gas_ev": ea_gas,
        "ea_smd_ev": ea_smd,
        "d_ea_ev": None if None in (ea_gas, ea_smd) else ea_smd - ea_gas,
        "p1_ox_ev": ip_gas,
        "p2_ox_ev": ip_smd,
        "p1_red_ev": None if ea_gas is None else -ea_gas,
        "p2_red_ev": None if ea_smd is None else -ea_smd,
        "ox_shift_ev": None if None in (ip_gas, ip_smd) else ip_smd - ip_gas,
        "red_shift_ev": None if None in (ea_gas, ea_smd) else (-ea_smd) - (-ea_gas),
        "qc_flags": ";".join(flags),
    }


def figure_environment(rows, ox, red, figdir):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.0))

    axis = axes[0]
    ordered = sorted(rows, key=lambda row: (row["d_ip_ev"] is None, row["d_ip_ev"] or 0.0))
    ordered = [row for row in ordered if row["d_ip_ev"] is not None or row["d_ea_ev"] is not None]
    x = list(range(len(ordered)))
    axis.bar([i - 0.2 for i in x], [row["d_ip_ev"] or 0.0 for row in ordered], width=0.4,
             color="#1d4ed8", alpha=0.9, label="$\\Delta$ IP  (solvent - gas)")
    axis.bar([i + 0.2 for i in x], [row["d_ea_ev"] or 0.0 for row in ordered], width=0.4,
             color="#0f766e", alpha=0.9, label="$\\Delta$ EA  (solvent - gas)")
    axis.axhline(0.0, color="#111827", linewidth=1.0)
    mean_ip = statistics.fmean([row["d_ip_ev"] for row in ordered if row["d_ip_ev"] is not None])
    axis.axhline(mean_ip, color="#1d4ed8", linestyle="--", linewidth=1.0, alpha=0.7,
                 label="mean $\\Delta$ IP = %+.3f eV" % mean_ip)
    axis.set_xticks(x)
    axis.set_xticklabels([row["name"] for row in ordered], rotation=45, ha="right")
    axis.set_ylabel("shift from gas phase (eV)")
    axis.set_title("(a) what the continuum does to the vertical energies", fontsize=11)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(fontsize=8.5)

    axis = axes[1]
    for label, block, colour in (("oxidation", ox, "#1d4ed8"), ("reduction", red, "#b91c1c")):
        pairs = block["pair_differences"]
        axis.plot(range(len(pairs)), [abs(item["d_p1_ev"]) for item in pairs], "-",
                  color=colour, linewidth=1.4, label="%s: |$\\Delta P_{ij}$| under P2" % label)
        axis.plot(range(len(pairs)), [Z_SENSITIVITY * item["sigma_ev"] for item in pairs], "--",
                  color=colour, alpha=0.6, linewidth=1.2,
                  label="%s: $z\\sigma_{ij}$ (z=1.96) from the P1/P2 spread" % label)
    axis.set_xlabel("unordered pairs, sorted by P2 separation")
    axis.set_ylabel("pair separation (eV)")
    axis.set_title("(b) does the solvent resolve pairs, or does it blur them?", fontsize=11)
    axis.legend(fontsize=8)
    axis.grid(axis="y", alpha=0.25)

    fig.suptitle(
        "P1 -> P2 (gas -> SMD acetonitrile): $f_{unresolved}$ (z=1.0) = %.2f (ox) / %.2f (red);"
        "  $\\tau_b$ = %.2f (ox) / %.2f (red);  top-20%% overlap = %.2f / %.2f"
        % (
            ox["f_unresolved_p1"], red["f_unresolved_p1"],
            ox["kendall_tau_b"], red["kendall_tau_b"],
            ox["top_k"]["k=0.20"]["overlap"], red["top_k"]["k=0.20"]["overlap"],
        ),
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    path = figdir / "F8_environment_layer_p1_to_p2.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.p2.exists():
        print("error: missing %s; run scripts/run_core_set_p2.py first" % args.p2, file=sys.stderr)
        return 2

    gas = load_states(args.p1)
    smd = load_states(args.p2)
    names = sorted({name for name, _ in gas} & {name for name, _ in smd})
    rows = [molecule_record(name, gas, smd) for name in names]

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.figdir.mkdir(parents=True, exist_ok=True)

    table = args.outdir / "p2_environment_effects.csv"
    with table.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    labels = [row["name"] for row in rows]
    ox = layer_stability([row["p1_ox_ev"] for row in rows], [row["p2_ox_ev"] for row in rows],
                         labels, higher_is_better=True)
    red = layer_stability([row["p1_red_ev"] for row in rows], [row["p2_red_ev"] for row in rows],
                          labels, higher_is_better=True)

    p0_by_name = {}
    if args.p0.exists():
        with args.p0.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                p0_by_name[row["name"]] = row
    ox_p0_p2 = red_p0_p2 = None
    if p0_by_name:
        ox_p0_p2 = layer_stability(
            [_float(p0_by_name.get(name, {}).get("p0_ox_ev")) for name in labels],
            [row["p2_ox_ev"] for row in rows], labels, higher_is_better=True)
        red_p0_p2 = layer_stability(
            [_float(p0_by_name.get(name, {}).get("p0_red_ev")) for name in labels],
            [row["p2_red_ev"] for row in rows], labels, higher_is_better=True)

    shifts_ip = [row["d_ip_ev"] for row in rows if row["d_ip_ev"] is not None]
    shifts_ea = [row["d_ea_ev"] for row in rows if row["d_ea_ev"] is not None]
    payload = {
        "layers": {
            "P1": "r2SCAN-3c, gas phase, G1 geometry",
            "P2": "r2SCAN-3c, CPCM(SMD, acetonitrile), same G1 geometry",
        },
        "n_molecules": len(rows),
        "delta_ip": {
            "n": len(shifts_ip),
            "mean_ev": statistics.fmean(shifts_ip) if shifts_ip else None,
            "std_ev": statistics.pstdev(shifts_ip) if len(shifts_ip) > 1 else None,
            "min_ev": min(shifts_ip) if shifts_ip else None,
            "max_ev": max(shifts_ip) if shifts_ip else None,
            "gas_range_ev": (
                max(row["ip_gas_ev"] for row in rows if row["ip_gas_ev"] is not None)
                - min(row["ip_gas_ev"] for row in rows if row["ip_gas_ev"] is not None)
            ) if shifts_ip else None,
        },
        "delta_ea": {
            "n": len(shifts_ea),
            "mean_ev": statistics.fmean(shifts_ea) if shifts_ea else None,
            "std_ev": statistics.pstdev(shifts_ea) if len(shifts_ea) > 1 else None,
            "min_ev": min(shifts_ea) if shifts_ea else None,
            "max_ev": max(shifts_ea) if shifts_ea else None,
        },
        "p1_to_p2": {"oxidation": ox, "reduction": red},
        "p0_to_p2": {"oxidation": ox_p0_p2, "reduction": red_p0_p2},
    }
    (args.outdir / "p2_decision_stability.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    figure = figure_environment(rows, ox, red, args.figdir)

    lines = [
        "# P1 -> P2 环境层分析（core set，N=%d）" % len(rows),
        "",
        "唯一变量：环境（气相 -> CPCM(SMD, acetonitrile)）。方法同为 r2SCAN-3c，几何同为 G1，",
        "全部为垂直量。",
        "",
        "## 1. 能量位移",
        "",
        "| 量 | n | 平均位移 (eV) | 位移 std (eV) | 范围 (eV) | 气相下的分子间跨度 (eV) |",
        "| --- | --- | --- | --- | --- | --- |",
        "| 垂直 IP | %d | %s | %s | %s .. %s | %s |" % (
            payload["delta_ip"]["n"],
            "%.3f" % payload["delta_ip"]["mean_ev"],
            "%.3f" % payload["delta_ip"]["std_ev"],
            "%.3f" % payload["delta_ip"]["min_ev"],
            "%.3f" % payload["delta_ip"]["max_ev"],
            "%.2f" % payload["delta_ip"]["gas_range_ev"],
        ),
        "| 垂直 EA | %d | %s | %s | %s .. %s | - |" % (
            payload["delta_ea"]["n"],
            "%.3f" % payload["delta_ea"]["mean_ev"],
            "%.3f" % payload["delta_ea"]["std_ev"],
            "%.3f" % payload["delta_ea"]["min_ev"],
            "%.3f" % payload["delta_ea"]["max_ev"],
        ),
        "",
        "## 2. 决策影响",
        "",
        "主判据为预注册冻结的 z = %s；z = %s（95%% 双侧带）作为保守敏感性并列。" % (Z_PRIMARY, Z_SENSITIVITY),
        "",
        "| 比较 | 轴 | Kendall tau_b | O_k(20%) | J_k(20%) | f_unresolved(P2) z=1.0（主判据） | f_robust_inv z=1.0（主判据） | f_unresolved(P2) z=1.96（敏感性） | f_robust_inv z=1.96（敏感性） |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, block in (("氧化", ox), ("还原", red)):
        lines.append("| P1 -> P2 | %s | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f |" % (
            label, block["kendall_tau_b"], block["top_k"]["k=0.20"]["overlap"],
            block["top_k"]["k=0.20"]["jaccard"],
            block["f_unresolved_p1"], block["f_robust_inv"],
            block["f_unresolved_p1_z1p96"], block["f_robust_inv_z1p96"]))
    for label, block in (("氧化", ox_p0_p2), ("还原", red_p0_p2)):
        if block and block.get("n", 0) >= 2:
            lines.append("| P0 -> P2 | %s | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f |" % (
                label, block["kendall_tau_b"], block["top_k"]["k=0.20"]["overlap"],
                block["top_k"]["k=0.20"]["jaccard"],
                block["f_unresolved_p1"], block["f_robust_inv"],
                block["f_unresolved_p1_z1p96"], block["f_robust_inv_z1p96"]))
    lines += [
        "",
        "## 3. 逐分子位移",
        "",
        "| 分子 | 家族 | IP(气) | IP(SMD) | dIP | EA(气) | EA(SMD) | dEA |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    def fmt(value, digits=3):
        return "-" if value is None else ("%.*f" % (digits, value))

    for row in sorted(rows, key=lambda item: (item["d_ip_ev"] is None, item["d_ip_ev"] or 0.0)):
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["family"], fmt(row["ip_gas_ev"], 2), fmt(row["ip_smd_ev"], 2),
            fmt(row["d_ip_ev"]), fmt(row["ea_gas_ev"], 2), fmt(row["ea_smd_ev"], 2),
            fmt(row["d_ea_ev"])))
    lines += ["", "图：`%s`（相对路径 `../figures/%s`）" % (_relative(figure), figure.name), ""]
    report = args.outdir / "p2_decision_stability.md"
    report.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    manifest = args.figdir / "figure_manifest_week4_p2.md"
    manifest.write_text("\n".join([
        "# Figure manifest -- week 4, P1 -> P2 environment layer",
        "",
        "Generated by `scripts/analyze_p2_environment.py`.",
        "",
        "| figure | file | what it shows |",
        "| --- | --- | --- |",
        "| F8 | %s | (a) the per-molecule gas -> solvent shift of the vertical IP and EA;"
        " (b) pair separations against the P1/P2 uncertainty band |" % figure.name,
        "",
        "Note on numbering: `docs/08` reserves F7 for the CPCM epsilon scan and F8 for the",
        "budget replay. Neither is produced yet, so this environment figure takes the next",
        "free identifier; when the epsilon scan and the budget replay are run they will be",
        "recorded as F9 and F10 in this file.",
        "",
        "## inputs",
        "",
        "| file | present | sha256 |",
        "| --- | --- | --- |",
    ] + [
        "| %s | %s | %s |" % (
            _relative(source), "yes" if source.exists() else "no",
            sha256(source) if source.exists() else "-",
        )
        for source in (args.p1, args.p2, args.p0)
    ] + [
        "",
        "## outputs",
        "",
        "| file | sha256 |",
        "| --- | --- |",
        "| %s | %s |" % (figure.name, sha256(figure)),
        "",
    ]), encoding="utf-8", newline="\n")

    print(json.dumps({
        "n_molecules": len(rows),
        "delta_ip_mean_ev": payload["delta_ip"]["mean_ev"],
        "delta_ip_std_ev": payload["delta_ip"]["std_ev"],
        "delta_ea_mean_ev": payload["delta_ea"]["mean_ev"],
        "ox_tau_b": ox["kendall_tau_b"],
        "red_tau_b": red["kendall_tau_b"],
        "ox_overlap_20": ox["top_k"]["k=0.20"]["overlap"],
        "red_overlap_20": red["top_k"]["k=0.20"]["overlap"],
        "effects_csv": _relative(table),
        "report": _relative(report),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())