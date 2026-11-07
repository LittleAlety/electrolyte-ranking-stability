"""Summarise and plot the first real r2SCAN-3c (P1) numbers for EC.

This is a *pilot*: one molecule, gas phase, vertical (neutral) geometry. Its job
is to check that the P1 layer behaves sensibly next to the external anchor and
next to the two cheap P0-style proxies already measured with GFN2-xTB, before the
full T1 sweep is started.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE = REPO_ROOT / "outputs" / "week3" / "orca_smoke"
HARTREE_TO_EV = 27.211386245988


def read_record(name: str) -> dict:
    path = SMOKE / f"{name}_orca.json"
    if not path.exists():
        raise SystemExit(f"missing pilot record: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def anchor_ip(species: str) -> float | None:
    path = REPO_ROOT / "data" / "anchors" / "gas_phase_anchors.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("species") == species and row.get("property") == "IP" and row.get("value_eV"):
                return float(row["value_eV"])
    return None


def xtb_row(mol_id: str) -> dict | None:
    path = REPO_ROOT / "outputs" / "week2" / "method_audit_xtb.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("mol_id") == mol_id:
                return row
    return None


def main() -> int:
    neutral = read_record("EC_gas")
    smd = read_record("EC_smd")
    cation = read_record("EC_cation")
    anion = read_record("EC_anion")

    energies = {
        name: record["result"]["final_energy_eh"]
        for name, record in (("neutral", neutral), ("smd", smd), ("cation", cation), ("anion", anion))
    }

    vertical_ip_ev = (energies["cation"] - energies["neutral"]) * HARTREE_TO_EV
    electron_affinity_ev = (energies["neutral"] - energies["anion"]) * HARTREE_TO_EV
    solvation_shift_ev = (energies["smd"] - energies["neutral"]) * HARTREE_TO_EV

    measured = anchor_ip("EC")
    xtb = xtb_row("EC") or {}
    koopmans = float(xtb["ip_koopmans_ev"]) if xtb.get("ip_koopmans_ev") else None
    dscf = float(xtb["vertical_ip_ev"]) if xtb.get("vertical_ip_ev") else None

    summary = {
        "status": "pilot (n=1, gas phase, vertical at the neutral geometry)",
        "method": neutral.get("result", {}).get("version"),
        "energies_eh": energies,
        "vertical_ip_ev": vertical_ip_ev,
        "electron_affinity_ev": electron_affinity_ev,
        "smd_acetonitrile_shift_ev": solvation_shift_ev,
        "anchor_ip_ec_ev": measured,
        "absolute_error_vs_anchor_ev": None if measured is None else vertical_ip_ev - measured,
        "cheap_proxies_ev": {"koopmans_p0": koopmans, "dscf_xtb_p1_like": dscf},
        "gas_phase_anion_bound": bool(energies["anion"] < energies["neutral"]),
    "notes": [
            "EA is negative, i.e. the gas-phase radical anion is unbound at this level, as expected "
            "for a compact basis set without diffuse augmentation; the protocol marks it unbound_anion "
            "instead of reporting a number.",
            "one molecule only: this is a sanity check of the P1 layer, not a ranking result",
        ],
    }

    outdir = REPO_ROOT / "outputs" / "week3"
    (outdir / "orca_pilot_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, values, colours = [], [], []
    if measured is not None:
        labels.append("NIST anchor\n(gas-phase IP)")
        values.append(measured)
        colours.append("#111827")
    if koopmans is not None:
        labels.append("GFN2-xTB\nKoopmans -eps_HOMO")
        values.append(koopmans)
        colours.append("#dc2626")
    if dscf is not None:
        labels.append("GFN2-xTB\ndSCF vertical IP")
        values.append(dscf)
        colours.append("#f59e0b")
    labels.append("r2SCAN-3c\nthis run (P1)")
    values.append(vertical_ip_ev)
    colours.append("#1d4ed8")

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    bars = ax.bar(labels, values, color=colours, alpha=0.9)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.12, f"{value:.2f}", ha="center", fontsize=10)
    if measured is not None:
        ax.axhline(measured, color="#111827", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.set_ylabel("EC vertical ionization energy (eV)", fontsize=10)
    ax.set_title("Pilot: the first r2SCAN-3c number vs the cheap proxies and the anchor", fontsize=11)
    ax.set_ylim(0, max(values) * 1.18)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    figure = outdir / "fig4_ec_ionization_pilot.png"
    fig.savefig(figure, dpi=200)
    plt.close(fig)

    print(json.dumps({k: v for k, v in summary.items() if k != "notes"}, indent=2, ensure_ascii=False))
    print("figure ->", figure.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())