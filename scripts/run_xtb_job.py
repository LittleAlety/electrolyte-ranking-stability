"""Run one GFN2-xTB job from a SMILES string and persist a traceable record.

Why this module exists
----------------------
Stage 2-3 need a single, boring entry point that turns a candidate into
(a) a starting geometry, (b) one frozen xTB job, and (c) a JSON record whose
every number can be traced back to the exact input and method.  Doing that in a
shell one-liner is how silent inconsistencies creep in, so the chain lives here:

    SMILES --RDKit embed/MMFF--> .xyz --xtb (frozen GFN2)--> parsed result
           --> <name>_xtb.json (result + provenance + QC flags + raw output)

The record deliberately keeps *failed* runs (unbound anions, missing fields)
rather than dropping them, matching the v2 section 20 rule that an abnormal
termination is a result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import provenance, toolchain, xtb  # noqa: E402

JOB_ALIASES = {
    "opt": xtb.JOB_OPTIMIZE,
    "sp": xtb.JOB_SINGLE_POINT,
    "freq": xtb.JOB_FREQUENCY,
}


def write_xyz(molecule, path: Path) -> None:
    """Write an RDKit molecule to an XYZ file.

    RDKit's own MolToXYZFile narrows the path to ANSI on Windows, which fails
    for any non-ASCII workspace (this project lives under a Chinese path), so
    the three-line XYZ format is emitted directly instead.
    """

    conformer = molecule.GetConformer()
    lines = [str(molecule.GetNumAtoms()), ""]
    for atom in molecule.GetAtoms():
        position = conformer.GetAtomPosition(atom.GetIdx())
        lines.append(
            f"{atom.GetSymbol():<2s} {position.x: .8f} {position.y: .8f} {position.z: .8f}"
        )
    path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8", newline=chr(10))

def build_geometry(smiles: str, *, seed: int, out_xyz: Path) -> int:
    """Embed and MMFF-optimise `smiles`; return the atom count."""

    from rdkit import Chem
    from rdkit.Chem import AllChem

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"RDKit could not parse SMILES {smiles!r}")
    molecule = Chem.AddHs(molecule)
    if AllChem.EmbedMolecule(molecule, randomSeed=seed) != 0:
        raise RuntimeError(f"RDKit embedding failed for {smiles!r}")
    AllChem.MMFFOptimizeMolecule(molecule)
    write_xyz(molecule, out_xyz)
    return molecule.GetNumAtoms()


def run_job(
    *,
    name: str,
    smiles: str,
    charge: int,
    multiplicity: int,
    job: str,
    outdir: Path,
    seed: int = 0xC0FFEE,
    timeout_seconds: float | None = 600.0,
) -> dict:
    """Run the full chain and return the persisted record."""

    outdir.mkdir(parents=True, exist_ok=True)
    xyz_path = outdir / f"{name}.xyz"

    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit(
            "xtb not found; set ELECTROLYTE_XTB or put xtb on PATH "
            "(scripts/check_environment.py reports what it sees)"
        )

    atom_count = build_geometry(smiles, seed=seed, out_xyz=xyz_path)
    version = toolchain.read_version(located.path, "xtb")

    record: dict[str, object] = {
        "mol_id": name,
        "smiles": smiles,
        "charge": charge,
        "multiplicity": multiplicity,
        "job": job,
        "atom_count": atom_count,
        "geometry": xyz_path.name,
    }

    try:
        result = xtb.run_xtb(
            located.path,
            job,
            input_name=xyz_path.name,
            charge=charge,
            multiplicity=multiplicity,
            cwd=outdir,
            timeout_seconds=timeout_seconds,
            required=(),
        )
    except xtb.XTBExecutionError as exc:
        record["status"] = "execution_failed"
        record["error"] = str(exc)
    else:
        raw_path = outdir / f"{name}_{job}.out"
        raw_path.write_text(result.raw_output, encoding="utf-8", newline="\n")
        record["status"] = "ok" if result.normal_termination else "abnormal_termination"
        record["result"] = result.as_dict()
        record["raw_output"] = raw_path.name
        record["qc_flags"] = sorted(
            set(result.qc_flags)
            | (
                {"unbound_anion"}
                if xtb.detect_unbound_anion(result.homo_ev, charge)
                else set()
            )
        )

    record["provenance"] = provenance.ProvenanceRecord(
        molecule_id=name,
        conformer_id="rdkit-embed-seed-" + str(seed),
        geometry_reference=xyz_path.name,
        raw_output_reference=str(record.get("raw_output", "")),
        qc_state="geometry_converged" if record["status"] == "ok" else "generated",
        software="xtb",
        software_version=version or "",
        functional="GFN2-xTB",
        basis="GFN2 minimal",
        charge=charge,
        multiplicity=multiplicity,
        qc_flags=tuple(record.get("qc_flags", [])),
    ).as_dict()

    record_path = outdir / f"{name}_xtb.json"
    record_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline="\n",
    )
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one frozen GFN2-xTB job from a SMILES.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--smiles", required=True)
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument("--multiplicity", type=int, default=1)
    parser.add_argument("--job", choices=sorted(JOB_ALIASES), default="opt")
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    arguments = parser.parse_args(argv)

    record = run_job(
        name=arguments.name,
        smiles=arguments.smiles,
        charge=arguments.charge,
        multiplicity=arguments.multiplicity,
        job=JOB_ALIASES[arguments.job],
        outdir=arguments.outdir,
        seed=arguments.seed,
    )
    summary = {
        "mol_id": record["mol_id"],
        "status": record["status"],
        "charge": record["charge"],
        "qc_flags": record.get("qc_flags", []),
    }
    result = record.get("result")
    if isinstance(result, dict):
        for key in ("total_energy_eh", "homo_ev", "lumo_ev", "hl_gap_ev", "dipole_debye"):
            summary[key] = result.get(key)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
