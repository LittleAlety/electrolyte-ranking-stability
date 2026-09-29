"""Run the xTB arm of the Stage 1 method audit against the gas-phase anchors.

Why this module exists
----------------------
Stage 1 freezes a production protocol only after the cheap engine has been
compared with an external reference. ORCA (the r2SCAN-3c engine) is not
installed, but GFN2-xTB is, so the xTB arm can be measured now: the gas-phase
ionisation energies of the audit set are computed with Delta-SCF and set against
the curated NIST / high-level values in data/anchors/gas_phase_anchors.csv.

Two quantities are produced per molecule:

* vertical IP/EA   -- Delta-SCF at the *neutral* (IP) or *anion* (EA) geometry,
  which is what a photoelectron experiment measures and therefore what the
  curated anchor values should be compared against;
* adiabatic IP/EA -- both states relaxed, the thermodynamic quantity that the
  P1 target in v2 section 3.1 is defined on.

The gap between the two is itself a result: it is the geometric relaxation the
Koopmans-like P0 proxy cannot see.

An anion that is not bound in the gas phase is reported as unbound_anion rather
than given a fictitious electron affinity (v2 section 7.3).
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import ranking, toolchain, xtb  # noqa: E402
from run_xtb_job import build_geometry  # noqa: E402

HARTREE_TO_EV = 27.211386245988

#: Audit set: closed-shell solvents that have at least one curated gas-phase
#: anchor, chosen to span the core-set families (v2 section 7.1).
AUDIT_SET: tuple[tuple[str, str], ...] = (
    ("EC", "O=C1OCCO1"),
    ("PC", "CC1COC(=O)O1"),
    ("DMC", "COC(=O)OC"),
    ("DEC", "CCOC(=O)OCC"),
    ("DME", "COCCOC"),
    ("DOL", "C1COCO1"),
    ("EA", "CCOC(=O)C"),
    ("GBL", "O=C1CCCO1"),
    ("SL", "C1CCS(=O)(=O)C1"),
    ("DMSO", "CS(C)=O"),
    ("AN", "CC#N"),
    ("TMP", "COP(=O)(OC)OC"),
)


def _load_anchors(path: Path) -> dict[tuple[str, str], list[dict]]:
    """Group anchor rows by (species, property); several determinations may exist."""

    grouped: dict[tuple[str, str], list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if not (row.get("value_eV") or "").strip():
                continue
            grouped.setdefault((row["species"], row["property"]), []).append(row)
    return grouped


def _energy(result: xtb.XTBResult) -> float:
    if result.total_energy_eh is None:
        raise RuntimeError("xTB run produced no total energy")
    return result.total_energy_eh


def audit_molecule(
    name: str,
    smiles: str,
    *,
    executable: str,
    outdir: Path,
    seed: int = 0xC0FFEE,
) -> dict:
    """Delta-SCF ionisation energy and electron affinity at the GFN2 level."""

    work = outdir / name
    work.mkdir(parents=True, exist_ok=True)

    neutral_start = work / "neutral_start.xyz"
    build_geometry(smiles, seed=seed, out_xyz=neutral_start)

    def run(job: str, charge: int, multiplicity: int, input_name: str) -> xtb.XTBResult:
        return xtb.run_xtb(
            executable,
            job,
            input_name=input_name,
            charge=charge,
            multiplicity=multiplicity,
            cwd=work,
            timeout_seconds=900.0,
            required=(),
        )

    def keep_optimised(target: str) -> None:
        produced = work / "xtbopt.xyz"
        if not produced.exists():
            raise RuntimeError(f"{name}: xTB produced no optimised geometry")
        shutil.copyfile(produced, work / target)

    record: dict[str, object] = {"mol_id": name, "smiles": smiles}

    # Neutral reference.
    neutral_opt = run(xtb.JOB_OPTIMIZE, 0, 1, neutral_start.name)
    keep_optimised("neutral_opt.xyz")
    e_neutral = _energy(neutral_opt)

    # Cation: vertical (fixed neutral geometry) then adiabatic.
    cation_vert = run(xtb.JOB_SINGLE_POINT, 1, 2, "neutral_opt.xyz")
    cation_opt = run(xtb.JOB_OPTIMIZE, 1, 2, "neutral_opt.xyz")
    keep_optimised("cation_opt.xyz")
    e_cation_vert = _energy(cation_vert)
    e_cation_adiabatic = _energy(cation_opt)

    # Anion: vertical (neutral single point at the anion geometry) then adiabatic.
    anion_opt = run(xtb.JOB_OPTIMIZE, -1, 2, "neutral_opt.xyz")
    keep_optimised("anion_opt.xyz")
    e_anion_adiabatic = _energy(anion_opt)
    neutral_at_anion = run(xtb.JOB_SINGLE_POINT, 0, 1, "anion_opt.xyz")
    e_neutral_at_anion = _energy(neutral_at_anion)

    unbound = xtb.detect_unbound_anion(anion_opt.homo_ev, -1)

    record.update(
        {
            "neutral_energy_eh": e_neutral,
            "vertical_ip_ev": (e_cation_vert - e_neutral) * HARTREE_TO_EV,
            "adiabatic_ip_ev": (e_cation_adiabatic - e_neutral) * HARTREE_TO_EV,
            "vertical_ea_ev": (e_neutral_at_anion - e_anion_adiabatic) * HARTREE_TO_EV,
            "adiabatic_ea_ev": (e_neutral - e_anion_adiabatic) * HARTREE_TO_EV,
            "relaxation_ip_ev": (e_cation_vert - e_cation_adiabatic) * HARTREE_TO_EV,
            # The P0 proxy of v2 section 3.1: a Koopmans-like orbital energy, not a
            # Delta-SCF thermodynamic difference. Both are compared to the anchors
            # below, because they do not have to agree with each other.
            "ip_koopmans_ev": -neutral_opt.homo_ev if neutral_opt.homo_ev is not None else None,
            "ea_koopmans_ev": -neutral_opt.lumo_ev if neutral_opt.lumo_ev is not None else None,
            "homo_ev": neutral_opt.homo_ev,
            "lumo_ev": neutral_opt.lumo_ev,
            "hl_gap_ev": neutral_opt.hl_gap_ev,
            "anion_homo_ev": anion_opt.homo_ev,
            "anion_qc_flags": list(anion_opt.qc_flags),
            "unbound_anion": unbound,
        }
    )
    return record


def compare(records: list[dict], anchors: dict[tuple[str, str], list[dict]]) -> dict:
    """Absolute error and rank agreement of the GFN2 ion energetics vs the anchors."""

    ip_pairs: list[tuple[str, float, float, float]] = []
    ea_pairs: list[tuple[str, float, float, float]] = []
    ip_koopmans_pairs: list[tuple[str, float, float, float]] = []
    ea_koopmans_pairs: list[tuple[str, float, float, float]] = []
    for record in records:
        name = record["mol_id"]
        for property_name, computed_key, bucket in (
            ("IP", "vertical_ip_ev", ip_pairs),
            ("IP", "ip_koopmans_ev", ip_koopmans_pairs),
            ("EA", "vertical_ea_ev", ea_pairs),
            ("EA", "ea_koopmans_ev", ea_koopmans_pairs),
        ):
            rows = anchors.get((name, property_name), [])
            value = record.get(computed_key)
            if not rows or value is None:
                continue
            # Several determinations may exist (e.g. DME has 9.3 and 9.8 eV); use the
            # mean and keep the spread as the anchor's own dispersion.
            values = [float(row["value_eV"]) for row in rows]
            reference = sum(values) / len(values)
            spread = (max(values) - min(values)) / 2.0 if len(values) > 1 else 0.0
            bucket.append((name, float(value), reference, spread))

    def summarise(pairs: list[tuple[str, float, float, float]]) -> dict:
        if not pairs:
            return {"n": 0}
        errors = [computed - reference for _, computed, reference, _ in pairs]
        absolute = [abs(error) for error in errors]
        computed_values = [computed for _, computed, _, _ in pairs]
        reference_values = [reference for _, _, reference, _ in pairs]
        # A large MAE with tau_b near 1 is the v2 section 22.2 case: the proxy is
        # offset, not re-ordered, so it still supports the same material decision.
        # Rank statistics need at least two paired observations; a single molecule
        # with an anchor is still a usable absolute error, so report it as such
        # rather than letting the rank helper raise.
        agreement = {
            "kendall_tau_b": None,
            "spearman_rho": None,
        }
        if len(pairs) >= 2:
            agreement = {
                "kendall_tau_b": ranking.kendall_tau_b(computed_values, reference_values),
                "spearman_rho": ranking.spearman_rho(computed_values, reference_values),
            }
        return {
            "n": len(pairs),
            "mae_ev": sum(absolute) / len(absolute),
            "max_abs_error_ev": max(absolute),
            "bias_ev": sum(errors) / len(errors),
            "error_std_ev": (
                sum((error - sum(errors) / len(errors)) ** 2 for error in errors) / len(errors)
            ) ** 0.5,
            "anchor_spread_ev": max((spread for *_, spread in pairs), default=0.0),
            **agreement,
            "pairs": [
                {
                    "mol_id": name,
                    "computed_ev": computed,
                    "anchor_ev": reference,
                    "error_ev": computed - reference,
                    "anchor_spread_ev": spread,
                }
                for name, computed, reference, spread in pairs
            ],
        }

    return {
        "IP_dscf_vertical": summarise(ip_pairs),
        "IP_koopmans_p0": summarise(ip_koopmans_pairs),
        "EA_dscf_vertical": summarise(ea_pairs),
        "EA_koopmans_p0": summarise(ea_koopmans_pairs),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the xTB arm of the method audit.")
    parser.add_argument("--outdir", type=Path, default=REPO_ROOT / "outputs" / "week2")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N molecules")
    arguments = parser.parse_args(argv)

    located = toolchain.find_executable("xtb")
    if located is None:
        print("xtb not found; run scripts/activate_toolchain.ps1 first", file=sys.stderr)
        return 2

    anchors = _load_anchors(REPO_ROOT / "data" / "anchors" / "gas_phase_anchors.csv")
    audit_dir = arguments.outdir / "method_audit_xtb"
    molecules = AUDIT_SET if arguments.limit is None else AUDIT_SET[: arguments.limit]

    records: list[dict] = []
    for name, smiles in molecules:
        try:
            record = audit_molecule(name, smiles, executable=located.path, outdir=audit_dir)
        except Exception as exc:  # noqa: BLE001 - a failed molecule is a result, not a crash
            record = {"mol_id": name, "smiles": smiles, "status": "failed", "error": repr(exc)}
        else:
            record["status"] = "ok"
        records.append(record)
        print(f"{name:6s} {record['status']}")

    table_path = arguments.outdir / "method_audit_xtb.csv"
    columns = [
        "mol_id",
        "smiles",
        "status",
        "neutral_energy_eh",
        "homo_ev",
        "lumo_ev",
        "hl_gap_ev",
        "vertical_ip_ev",
        "adiabatic_ip_ev",
        "relaxation_ip_ev",
        "ip_koopmans_ev",
        "ea_koopmans_ev",
        "vertical_ea_ev",
        "adiabatic_ea_ev",
        "anion_homo_ev",
        "unbound_anion",
        "anion_qc_flags",
    ]
    with table_path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    summary = {
        "engine": "GFN2-xTB",
        "engine_version": toolchain.read_version(located.path, "xtb"),
        "n_molecules": len(records),
        "n_unbound_anion": sum(1 for r in records if r.get("unbound_anion")),
        "comparison": compare(records, anchors),
    }
    summary_path = arguments.outdir / "method_audit_xtb_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8", newline=chr(10)
    )

    print(json.dumps(summary["comparison"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
