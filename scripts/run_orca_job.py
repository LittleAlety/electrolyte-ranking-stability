"""Run one ORCA r2SCAN-3c job from a SMILES (or an existing .xyz) and persist a record.

Why this module exists
----------------------
This is the ORCA-side twin of ``scripts/run_xtb_job.py``. The production chain
takes an xTB geometry and evaluates its electronic energy with one frozen
r2SCAN-3c single point in ORCA, so the entry point has to do exactly three
boring things and nothing else:

    SMILES --RDKit embed/MMFF--> .xyz --ORCA (frozen r2SCAN-3c)--> parsed result
           --> <name>_orca.json (result + provenance + QC + input + command line)

The ORCA binary is not installed on the development machine (it is a Gate 1
blocker), so the whole chain up to and including the input file is runnable
now with ``--dry-run``: it writes <name>.inp and a ``status="not_run"`` record,
which is enough to check that the input is well-formed before the download
finishes. Without ``--dry-run`` and without an ORCA on the machine the script
stops with a message about ELECTROLYTE_ORCA / .toolchain instead of a traceback.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, provenance, toolchain  # noqa: E402
from run_xtb_job import build_geometry  # noqa: E402

class MissingORCAExecutable(RuntimeError):
    """ORCA is not on this machine and --dry-run was not requested."""


JOB_ALIASES = {
    "sp": orca.JOB_SINGLE_POINT,
    "opt": orca.JOB_OPTIMIZE,
    "freq": orca.JOB_FREQUENCY,
    "opt+freq": orca.JOB_OPTIMIZE_FREQUENCY,
}

MISSING_ORCA_MESSAGE = (
    "未找到 ORCA 可执行文件（orca.exe）。请任选其一：\n"
    "  1) 设置环境变量 ELECTROLYTE_ORCA 指向 orca.exe，例如\n"
    '     $env:ELECTROLYTE_ORCA = "E:...\\.toolchain\\orca\\orca_6_0_1\\orca.exe"\n'
    "  2) 把 ORCA 解压到仓库下的 .toolchain\\orca\\（find_executable 会在 PATH 之外查找，\n"
    "     scripts/freeze_gates.py 也会在 .toolchain 下自动搜到它）。\n"
    "安装步骤见 docs/07_orca_setup_and_runner.md。\n"
    "如果只是想在装上 ORCA 之前检查输入文件，请加 --dry-run。"
)


def read_xyz_coordinates(path: Path) -> tuple[str, int]:
    """Return (coordinate_block, atom_count) from an XYZ file.

    Only the geometry is kept; the two XYZ header lines (count, comment) are
    dropped because ``build_orca_input`` writes its own ``* xyz`` header.
    """

    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        raise ValueError(f"{path}: xyz file is empty")
    try:
        count = int(lines[index].strip())
    except ValueError as exc:
        raise ValueError(
            f"{path}: first xyz line is not an atom count: {lines[index]!r}"
        ) from exc
    coordinates = [line.rstrip() for line in lines[index + 2 : index + 2 + count]]
    if len(coordinates) != count:
        raise ValueError(
            f"{path}: expected {count} coordinate lines, found {len(coordinates)}"
        )
    return "\n".join(coordinates), count


def resolve_geometry(
    name: str,
    *,
    smiles: str | None,
    xyz: Path | None,
    outdir: Path,
    seed: int,
) -> tuple[str, int, Path]:
    """Materialise <outdir>/<name>.xyz and return its coordinate block + atom count."""

    xyz_path = outdir / f"{name}.xyz"
    if smiles is not None:
        build_geometry(smiles, seed=seed, out_xyz=xyz_path)
    else:
        assert xyz is not None
        coordinates, count = read_xyz_coordinates(xyz)
        xyz_path.write_text(
            f"{count}\n{name}\n{coordinates}\n", encoding="utf-8", newline="\n"
        )
    coordinates, count = read_xyz_coordinates(xyz_path)
    return coordinates, count, xyz_path


def solvent_model_label(solvent: str | None, epsilon: float | None) -> str:
    """The provenance string describing the continuum model actually used."""

    if solvent is not None:
        return f"CPCM(SMD, {solvent})"
    if epsilon is not None:
        return f"CPCM(epsilon={epsilon})"
    return "gas-phase"


def build_provenance(
    *,
    name: str,
    charge: int,
    multiplicity: int,
    job: str,
    solvent: str | None,
    epsilon: float | None,
    version: str | None,
    seed: int,
    geometry_reference: str,
    raw_output_reference: str,
    qc_state: str,
    qc_flags: tuple[str, ...],
) -> provenance.ProvenanceRecord:
    """A single-point record, with the geometry threshold corrected for Opt jobs."""

    threshold = (
        "not applicable (single point)"
        if job == orca.JOB_SINGLE_POINT
        else f"ORCA default ({job})"
    )
    return provenance.make_single_point_record(
        molecule_id=name,
        conformer_id="rdkit-embed-seed-" + str(seed),
        geometry_reference=geometry_reference,
        raw_output_reference=raw_output_reference,
        qc_state=qc_state,
        software_version=version or "",
        functional="r2SCAN",
        geometry_threshold=threshold,
        charge=charge,
        multiplicity=multiplicity,
        solvent_model=solvent_model_label(solvent, epsilon),
        qc_flags=qc_flags,
    )


def run_job(
    *,
    name: str,
    smiles: str | None,
    xyz: Path | None,
    charge: int,
    multiplicity: int,
    job: str,
    outdir: Path,
    solvent: str | None = None,
    epsilon: float | None = None,
    seed: int = 0xC0FFEE,
    timeout_seconds: float | None = 3600.0,
    nprocs: int | None = None,
    maxcore_mb: int | None = None,
    moinp: Path | None = None,
    dry_run: bool = False,
    scratch_root: Path | None = None,
) -> dict:
    """Run the full chain and return the persisted record."""

    outdir.mkdir(parents=True, exist_ok=True)

    located = toolchain.find_executable("orca")
    if not dry_run and located is None:
        raise MissingORCAExecutable(MISSING_ORCA_MESSAGE)

    coordinates, atom_count, xyz_path = resolve_geometry(
        name, smiles=smiles, xyz=xyz, outdir=outdir, seed=seed
    )
    resolved_nprocs = orca.resolve_nprocs(nprocs)
    parallel_note = ""
    if located is not None and resolved_nprocs > 1 and not orca.is_ascii_safe(located.path):
        # The msmpi build cannot launch helpers from a non-ASCII path; record why
        # this run will be serial instead of silently losing the parallelism.
        resolved_nprocs = 1
        parallel_note = orca.NON_ASCII_PARALLEL_NOTE
    input_text = orca.build_orca_input(
        charge=charge,
        multiplicity=multiplicity,
        geometry=coordinates,
        job=job,
        solvent=solvent,
        epsilon=epsilon,
        nprocs=resolved_nprocs,
        maxcore_mb=maxcore_mb,
        moinp=None if moinp is None else str(moinp),
    )
    input_name = f"{name}.inp"
    (outdir / input_name).write_text(input_text, encoding="utf-8", newline="\n")

    record: dict[str, object] = {
        "mol_id": name,
        "smiles": smiles,
        "xyz_source": None if xyz is None else str(xyz),
        "charge": charge,
        "multiplicity": multiplicity,
        "job": job,
        "solvent": solvent,
        "epsilon": epsilon,
        "atom_count": atom_count,
        "geometry": xyz_path.name,
        "input_file": input_name,
        "input": input_text,
        "nprocs": resolved_nprocs,
        "parallel_note": parallel_note,
        "maxcore_mb": maxcore_mb,
        "moinp": None if moinp is None else str(moinp),
        "orca_path": None if located is None else located.path,
        "command": [str(located.path) if located is not None else "orca", input_name],
    }

    version: str | None = None
    if located is not None:
        version = toolchain.read_version(located.path, "orca")

    if dry_run:
        record["status"] = "not_run"
        record["note"] = (
            "--dry-run: 只生成了输入文件与记录，未运行 ORCA。"
            "装好 orca.exe 后去掉 --dry-run 重跑即可得到能量。"
        )
        record["qc_flags"] = []
        raw_output_name = ""
        qc_state = "generated"
    else:
        try:
            result = orca.run_orca(
                located.path,
                job,
                input_name=input_name,
                charge=charge,
                multiplicity=multiplicity,
                geometry=coordinates,
                cwd=outdir,
                solvent=solvent,
                epsilon=epsilon,
                nprocs=nprocs,
                maxcore_mb=maxcore_mb,
                moinp=moinp,
                timeout_seconds=timeout_seconds,
                required=(),
                scratch_root=scratch_root,
            )
        except orca.ORCAExecutionError as exc:
            record["status"] = "execution_failed"
            record["error"] = str(exc)
            record["qc_flags"] = [
                "geometry_failed" if job != orca.JOB_SINGLE_POINT else "scf_failed"
            ]
            raw_output_name = f"{name}.out"
            qc_state = "generated"
        else:
            raw_output_name = f"{name}.out"
            record["status"] = "ok" if result.normal_termination else "abnormal_termination"
            record["result"] = result.as_dict()
            record["parallel_note"] = result.parallel_note or parallel_note
            record["qc_flags"] = sorted(result.qc_flags)
            record["raw_output"] = raw_output_name
            if result.version:
                version = result.version
            qc_state = "scf_converged" if record["status"] == "ok" else "generated"

    record["provenance"] = build_provenance(
        name=name,
        charge=charge,
        multiplicity=multiplicity,
        job=job,
        solvent=solvent,
        epsilon=epsilon,
        version=version,
        seed=seed,
        geometry_reference=xyz_path.name,
        raw_output_reference=raw_output_name,
        qc_state=qc_state,
        qc_flags=tuple(record.get("qc_flags", [])),
    ).as_dict()

    record_path = outdir / f"{name}_orca.json"
    record_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one frozen ORCA r2SCAN-3c job from a SMILES or an XYZ file."
    )
    parser.add_argument("--name", required=True)
    geometry = parser.add_mutually_exclusive_group(required=True)
    geometry.add_argument("--smiles", help="build the geometry with RDKit from this SMILES")
    geometry.add_argument("--xyz", type=Path, help="use this existing .xyz geometry")
    parser.add_argument("--charge", type=int, default=0)
    parser.add_argument("--multiplicity", type=int, default=1)
    parser.add_argument("--job", choices=sorted(JOB_ALIASES), default="sp")
    environment = parser.add_mutually_exclusive_group()
    environment.add_argument("--solvent", default=None, help="SMD solvent name (e.g. acetonitrile)")
    environment.add_argument("--epsilon", type=float, default=None, help="bare CPCM dielectric")
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=3600.0, help="seconds (default 3600)")
    parser.add_argument("--nprocs", type=int, default=None, help="%pal nprocs (default: auto, capped)")
    parser.add_argument("--maxcore", type=int, default=None, help="%maxcore in MB per core")
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=None,
        help=(
            "directory ORCA runs in; needed only when the output directory is not "
            "ASCII-safe (this repository lives under a Chinese name, so the default "
            "falls back to %%TEMP%%\\electrolyte_orca_scratch)"
        ),
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only write the input file and a status=not_run record; no ORCA needed",
    )
    arguments = parser.parse_args(argv)

    try:
        record = run_job(
            name=arguments.name,
            smiles=arguments.smiles,
            xyz=arguments.xyz,
            charge=arguments.charge,
            multiplicity=arguments.multiplicity,
            job=JOB_ALIASES[arguments.job],
            outdir=arguments.outdir,
            solvent=arguments.solvent,
            epsilon=arguments.epsilon,
            seed=arguments.seed,
            timeout_seconds=arguments.timeout,
            nprocs=arguments.nprocs,
            maxcore_mb=arguments.maxcore,
            dry_run=arguments.dry_run,
            scratch_root=arguments.scratch_root,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    summary = {
        "mol_id": record["mol_id"],
        "status": record["status"],
        "job": record["job"],
        "charge": record["charge"],
        "multiplicity": record["multiplicity"],
        "nprocs": record["nprocs"],
        "qc_flags": record.get("qc_flags", []),
    }
    result = record.get("result")
    if isinstance(result, dict):
        for key in ("final_energy_eh", "scf_converged", "n_scf_cycles", "normal_termination", "version"):
            summary[key] = result.get(key)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if record["status"] in ("ok", "not_run") else 1


if __name__ == "__main__":
    raise SystemExit(main())
