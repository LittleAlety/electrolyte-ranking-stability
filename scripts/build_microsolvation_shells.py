#!/usr/bin/env python
"""Stage 9 / T10 step 1 -- explicit first-shell microsolvation shells [Li(M)2]+.

Why this module exists
----------------------
Week 5 measured the C1 conditional state as a 1:1 complex, [Li M]+, in a
continuum of acetonitrile (``scripts/run_c1_li_coordination.py``).  The v2 plan
(section 17.1) asks for one *targeted* sensitivity check: build a small number
of local clusters with a **fixed stoichiometry** and ask whether the 1:1 Li+
coordination conclusion survives when the first solvation shell is made more
realistic.  This module builds the starting point of that check, the homoleptic
1:2 cluster ``[Li(M)2]+``.

Rule (written down so it is reproducible, like every other builder here)
------------------------------------------------------------------------
For every frozen motif of ``outputs/week5/li_motif_generation.json``:

1. take the r2SCAN-3c optimised ``[Li M]+`` geometry as the *anchored* frame
   (the parent molecule is never re-optimised);
2. take the shared G1 (GFN2-xTB) geometry of the free molecule M as the second
   ligand -- the same parent structure the whole project is anchored on;
3. place one donor atom of the second ligand at the frozen Li-donor distance
   of ``build_li_motifs.PLACEMENT_DISTANCE`` along a direction of a Fibonacci
   sphere around Li, with the ligand body pointing away from Li and rolled
   about that axis;
4. keep the placements whose closest cross contact is not a clash, score the
   best few with one GFN2-xTB single point each, and pre-optimise the winner;
5. never drop a candidate: every generated placement is written to the CSV,
   including the ones that were not selected and the ones that failed.

Geometry convention
-------------------
All distances are Angstrom.  The second ligand keeps its G1 internal geometry;
only its rigid-body placement is sampled here, and the GFN2-xTB pre-optimisation
then relaxes the whole cluster.  The DFT refinement is a separate stage
(``scripts/run_stage9_microsolvation.py``).

Outputs
-------
``structures/microsolvation/<NAME>_<motif>_shell2.xyz``  xtb pre-optimised shell
``outputs/week8/ms_shell_generation.csv``                 one row per placement
``outputs/week8/ms_shell_generation.json``                run record
``outputs/week8/ms_shell_generation.md``                  human-readable table
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import toolchain, xtb  # noqa: E402
from build_li_motifs import (  # noqa: E402
    BOND_INTACT_FACTOR,
    COVALENT_RADIUS,
    PLACEMENT_DISTANCE,
    heavy_graph,
    read_xyz,
    unit,
    write_xyz,
)
from run_core_set_p1 import cached_geometries  # noqa: E402

WEEK5 = REPO_ROOT / "outputs" / "week5"
MOTIF_JSON = WEEK5 / "li_motif_generation.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week8"
DEFAULT_STRUCTDIR = REPO_ROOT / "structures" / "microsolvation"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week8_scratch" / "shells"

EH_TO_KJ = 2625.4996394799

#: The shell stoichiometry this stage adds: Li + 2 M.
N_SHELL = 2

#: Fibonacci-sphere directions and in-plane rolls sampled around Li+.
N_DIRECTIONS = 96
N_ROLLS = 12

#: A cross contact closer than this fraction of the covalent-radius sum is a clash.
CLASH_RATIO = 0.85

#: How many clash-free placements are scored with GFN2-xTB before the pre-opt.
N_SCORED = 4

#: A heavy atom counts as coordinated to Li when it is inside this radius.
CONTACT_CUTOFF = 2.60

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "motif_id",
    "donor_index",
    "donor_symbol",
    "direction_index",
    "roll_index",
    "min_clearance",
    "placement_status",
    "sp_status",
    "sp_energy_eh",
    "sp_energy_rel_kj",
    "opt_status",
    "opt_energy_eh",
    "opt_energy_rel_kj",
    "n_li_contacts",
    "li_contacts",
    "li_min_distance_a",
    "second_ligand_intact",
    "selected",
    "qc_flags",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def rotation_matrix(axis, angle: float) -> np.ndarray:
    """Rodrigues rotation about ``axis`` by ``angle``."""

    direction = unit(np.asarray(axis, dtype=float))
    if direction is None:
        return np.eye(3)
    x, y, z = (float(value) for value in direction)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return np.array(
        [
            [cosine + x * x * (1 - cosine), x * y * (1 - cosine) - z * sine, x * z * (1 - cosine) + y * sine],
            [y * x * (1 - cosine) + z * sine, cosine + y * y * (1 - cosine), y * z * (1 - cosine) - x * sine],
            [z * x * (1 - cosine) - y * sine, z * y * (1 - cosine) + x * sine, cosine + z * z * (1 - cosine)],
        ]
    )


def align_rotation(source, target) -> np.ndarray:
    """Rotation taking unit vector ``source`` onto unit vector ``target``."""

    first = unit(np.asarray(source, dtype=float))
    second = unit(np.asarray(target, dtype=float))
    if first is None or second is None:
        return np.eye(3)
    cross = np.cross(first, second)
    sine = float(np.linalg.norm(cross))
    cosine = float(np.dot(first, second))
    if sine < 1e-9:
        if cosine > 0:
            return np.eye(3)
        helper = np.array([1.0, 0.0, 0.0])
        if abs(first[0]) > 0.9:
            helper = np.array([0.0, 1.0, 0.0])
        return rotation_matrix(np.cross(first, helper), math.pi)
    return rotation_matrix(cross / sine, math.atan2(sine, cosine))


def fibonacci_directions(count: int) -> list:
    golden = math.pi * (3.0 - math.sqrt(5.0))
    out = []
    for index in range(count):
        z = 1.0 - 2.0 * (index + 0.5) / count
        radius = math.sqrt(max(0.0, 1.0 - z * z))
        theta = golden * index
        out.append(np.array([radius * math.cos(theta), radius * math.sin(theta), z]))
    return out

def covalent_radii(symbols) -> np.ndarray:
    return np.array([COVALENT_RADIUS.get(symbol, 0.8) for symbol in symbols], dtype=float)


def minimal_clearance(ligand_coords, anchor_coords, ligand_radii, anchor_radii) -> float:
    """Smallest cross (distance / covalent-radius sum) between ligand and anchor."""

    distances = np.linalg.norm(ligand_coords[:, None, :] - anchor_coords[None, :, :], axis=2)
    limits = ligand_radii[:, None] + anchor_radii[None, :]
    return float(np.min(distances / limits))


def place_second_ligand(
    li_position, anchor_symbols, anchor_coords, ligand_symbols, ligand_coords, donors
):
    """Every rigid-body placement of the second ligand on the Li+ sphere."""

    ligand_radii = covalent_radii(ligand_symbols)
    anchor_radii = covalent_radii(anchor_symbols)
    placements = []
    for donor in donors:
        symbol = ligand_symbols[donor]
        radius = PLACEMENT_DISTANCE.get(symbol, 2.00)
        centre = ligand_coords[donor]
        local = ligand_coords - centre
        body = unit(np.mean(np.delete(local, donor, axis=0), axis=0))
        if body is None:
            continue
        for direction_index, direction in enumerate(fibonacci_directions(N_DIRECTIONS)):
            for roll_index in range(N_ROLLS):
                roll = 2.0 * math.pi * roll_index / N_ROLLS
                rotation = rotation_matrix(direction, roll) @ align_rotation(body, direction)
                placed = local @ rotation.T + (li_position + radius * direction)
                placements.append(
                    {
                        "donor_index": donor,
                        "donor_symbol": symbol,
                        "direction_index": direction_index,
                        "roll_index": roll_index,
                        "coords": placed,
                        "min_clearance": minimal_clearance(
                            placed, anchor_coords, ligand_radii, anchor_radii
                        ),
                    }
                )
    return placements


def ligand_bonds_intact(symbols_h, neighbours, coords) -> bool:
    for index in range(len(symbols_h)):
        for other, _ in neighbours[index]:
            if other <= index:
                continue
            limit = BOND_INTACT_FACTOR * (
                COVALENT_RADIUS.get(symbols_h[index], 0.8)
                + COVALENT_RADIUS.get(symbols_h[other], 0.8)
            )
            if float(np.linalg.norm(coords[index] - coords[other])) > limit:
                return False
    return True


def li_contacts(li_position, symbols, coords, donors) -> tuple:
    contacts = []
    for index in donors:
        distance = float(np.linalg.norm(coords[index] - li_position))
        if distance <= CONTACT_CUTOFF:
            contacts.append((index, symbols[index], distance))
    contacts.sort(key=lambda item: item[2])
    return contacts


def run_xtb_job(executable, job, xyz_path, workdir, charge, multiplicity, timeout):
    workdir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    result = xtb.run_xtb(
        executable,
        job,
        input_name=xyz_path.name,
        charge=charge,
        multiplicity=multiplicity,
        cwd=workdir,
        timeout_seconds=timeout,
        required=(),
    )
    seconds = round(time.perf_counter() - started, 2)
    raw_path = workdir / (xyz_path.stem + "_" + job.replace("+", "_") + ".out")
    raw_path.write_text(result.raw_output, encoding="utf-8", newline=chr(10))
    optimized = None
    optimized_path = workdir / "xtbopt.xyz"
    if optimized_path.exists():
        _, optimized = read_xyz(optimized_path)
    return {
        "status": "ok" if result.normal_termination else "abnormal_termination",
        "energy_eh": result.total_energy_eh,
        "optimized": optimized,
        "seconds": seconds,
    }

def load_motifs(path: Path = MOTIF_JSON) -> list:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["motifs"])


def core_rows() -> dict:
    import csv as _csv

    path = REPO_ROOT / "data" / "metadata" / "core_set.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in _csv.DictReader(handle)}


def build_motif(motif, row, args, executable) -> list:
    name = motif["name"]
    stem = name + "_" + motif["motif_id"]
    li_path = WEEK5 / "c1" / name / (stem + "_G2Li.xyz")
    if not li_path.exists():
        li_path = REPO_ROOT / motif["path"]
    anchor_symbols, anchor_coords = read_xyz(li_path)
    li_index = len(anchor_symbols) - 1
    if anchor_symbols[li_index] != "Li":
        raise RuntimeError("the anchored [Li M]+ geometry does not end in Li: " + str(li_path))
    li_position = anchor_coords[li_index]

    g1_path = None
    for path, label in cached_geometries(row["mol_id"], name):
        if path.exists() and path.stat().st_size > 0:
            g1_path = path
            break
    if g1_path is None:
        raise RuntimeError("no cached G1 geometry for " + name)
    ligand_symbols, ligand_coords = read_xyz(g1_path)
    _, neighbours = heavy_graph(row["smiles"])

    donors = list(motif["donors"])
    placements = place_second_ligand(
        li_position, anchor_symbols, anchor_coords, ligand_symbols, ligand_coords, donors
    )
    placements.sort(key=lambda item: item["min_clearance"], reverse=True)

    clash_free = [item for item in placements if item["min_clearance"] >= CLASH_RATIO]
    # A tight bidentate 1:1 motif (DMC m2, TMP m2) can fill the whole Li+ sphere
    # by itself, so no rigid-body placement of a second ligand is clash free.
    # The rule stays written down: the fallback is the best few placements by
    # clearance, the rows keep placement_status = clash, and the winner carries
    # the placement_clash_start QC flag.  A clean drop would be the error.
    fallback = not clash_free
    scored = (clash_free if clash_free else placements)[:N_SCORED]
    scored_ids = {(item["donor_index"], item["direction_index"], item["roll_index"]) for item in scored}

    workdir_root = Path(args.scratch) / stem
    records = []

    def base_record(item) -> dict:
        return {
            "mol_id": motif["mol_id"],
            "name": name,
            "family": motif["family"],
            "motif_id": motif["motif_id"],
            "donor_index": item["donor_index"],
            "donor_symbol": item["donor_symbol"],
            "direction_index": item["direction_index"],
            "roll_index": item["roll_index"],
            "min_clearance": round(item["min_clearance"], 4),
            "placement_status": "clash_free" if item["min_clearance"] >= CLASH_RATIO else "clash",
            "sp_status": "",
            "sp_energy_eh": "",
            "sp_energy_rel_kj": "",
            "opt_status": "",
            "opt_energy_eh": "",
            "opt_energy_rel_kj": "",
            "n_li_contacts": "",
            "li_contacts": "",
            "li_min_distance_a": "",
            "second_ligand_intact": "",
            "selected": False,
            "qc_flags": "",
        }

    for item in placements:
        key = (item["donor_index"], item["direction_index"], item["roll_index"])
        record = base_record(item)
        if key not in scored_ids:
            records.append(record)
            continue
        label = "d%02d_dir%03d_r%02d" % key
        workdir = workdir_root / label
        workdir.mkdir(parents=True, exist_ok=True)
        xyz_path = workdir / (stem + "_" + label + ".xyz")
        write_xyz(
            xyz_path,
            list(anchor_symbols) + list(ligand_symbols),
            np.vstack([anchor_coords, item["coords"]]),
            stem + " shell2 " + label,
        )
        if args.dry_run:
            record["sp_status"] = "dry_run"
            records.append(record)
            continue
        try:
            sp = run_xtb_job(
                executable, xtb.JOB_SINGLE_POINT, xyz_path, workdir, 1, 1, args.timeout
            )
        except Exception as exc:  # noqa: BLE001
            record["sp_status"] = "execution_failed"
            record["qc_flags"] = "scf_failed"
            record["sp_energy_eh"] = repr(exc)
            records.append(record)
            continue
        record["sp_status"] = sp["status"]
        record["sp_energy_eh"] = sp["energy_eh"]
        records.append(record)

    scored_records = [r for r in records if r["sp_status"] == "ok" and isinstance(r["sp_energy_eh"], float)]
    if scored_records:
        lowest = min(scored_records, key=lambda r: r["sp_energy_eh"])
        for record in scored_records:
            record["sp_energy_rel_kj"] = round(
                (record["sp_energy_eh"] - lowest["sp_energy_eh"]) * EH_TO_KJ, 4
            )
        winner_key = (lowest["donor_index"], lowest["direction_index"], lowest["roll_index"])
        winner = next(
            item
            for item in placements
            if (item["donor_index"], item["direction_index"], item["roll_index"]) == winner_key
        )
        wdir = workdir_root / ("opt_%s" % lowest["direction_index"])
        wdir.mkdir(parents=True, exist_ok=True)
        wxyz = wdir / (stem + "_shell2_start.xyz")
        write_xyz(
            wxyz,
            list(anchor_symbols) + list(ligand_symbols),
            np.vstack([anchor_coords, winner["coords"]]),
            stem + " shell2 pre-opt start",
        )
        try:
            opt = run_xtb_job(
                executable, xtb.JOB_OPTIMIZE, wxyz, wdir, 1, 1, args.timeout
            )
        except Exception as exc:  # noqa: BLE001
            lowest["opt_status"] = "execution_failed"
            lowest["qc_flags"] = "geometry_failed"
            lowest["opt_energy_eh"] = repr(exc)
            return records
        lowest["opt_status"] = opt["status"]
        lowest["opt_energy_eh"] = opt["energy_eh"]
        lowest["opt_energy_rel_kj"] = 0.0
        lowest["selected"] = True
        if opt["optimized"] is not None:
            coords = opt["optimized"]
            if len(coords) != len(anchor_symbols) + len(ligand_symbols):
                raise RuntimeError("xtb opt changed the atom count for " + stem)
            li_here = coords[li_index]
            contacts = []
            for offset, symbol in enumerate(ligand_symbols):
                if symbol not in ("O", "N", "S", "P"):
                    continue
                distance = float(np.linalg.norm(coords[len(anchor_symbols) + offset] - li_here))
                if distance <= CONTACT_CUTOFF:
                    contacts.append((len(anchor_symbols) + offset, symbol, distance))
            for index in range(li_index):
                if anchor_symbols[index] not in ("O", "N", "S", "P"):
                    continue
                distance = float(np.linalg.norm(coords[index] - li_here))
                if distance <= CONTACT_CUTOFF:
                    contacts.append((index, anchor_symbols[index], distance))
            contacts.sort(key=lambda item: item[2])
            lowest["n_li_contacts"] = len(contacts)
            lowest["li_contacts"] = ";".join(
                "%d:%s:%.3f" % item for item in contacts
            )
            lowest["li_min_distance_a"] = round(contacts[0][2], 4) if contacts else ""
            lowest["second_ligand_intact"] = ligand_bonds_intact(
                ligand_symbols, neighbours, coords[len(anchor_symbols):]
            )
            flags = []
            if fallback:
                flags.append("placement_clash_start")
            if not lowest["li_contacts"]:
                flags.append("no_intact_minimum_found")
            if lowest["second_ligand_intact"] is False:
                flags.append("dissociated_optimized_product")
            lowest["qc_flags"] = ";".join(flags)
            structure = Path(args.structdir) / (stem + "_shell2.xyz")
            write_xyz(
                structure,
                list(anchor_symbols) + list(ligand_symbols),
                coords,
                stem + " [Li(M)2]+ GFN2-xTB pre-opt from " + relative(li_path),
            )
    return records

def write_csv(path: Path, records) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in COLUMNS})
    return path


def write_markdown(path: Path, records, motifs) -> Path:
    selected = [record for record in records if record["selected"]]
    lines = [
        "# Stage 9 / T10 -- explicit first-shell microsolvation shells [Li(M)2]+",
        "",
        "One row per rigid-body placement of the second ligand on the Li+ sphere.",
        "``placement_status = clash`` rows were generated and discarded by the",
        "written-down rule, never silently: they stay in ``ms_shell_generation.csv``.",
        "",
        "## Selected shells (lowest GFN2-xTB energy among the scored placements)",
        "",
        "| mol | motif | Li contacts | Li-min (A) | 2nd ligand intact | opt status | QC |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in selected:
        lines.append(
            "| %s %s | %s | %s | %s | %s | %s | %s |"
            % (
                record["mol_id"],
                record["name"],
                record["motif_id"],
                record["n_li_contacts"],
                record["li_min_distance_a"],
                record["second_ligand_intact"],
                record["opt_status"],
                record["qc_flags"] or "-",
            )
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(chr(10).join(lines), encoding="utf-8", newline=chr(10))
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--structdir", default=str(DEFAULT_STRUCTDIR))
    parser.add_argument("--scratch", default=str(DEFAULT_SCRATCH))
    parser.add_argument("--only", default=None, help="comma separated mol_id or name filter")
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--motif-json", default=str(MOTIF_JSON))
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit("xtb not found; see scripts/check_environment.py")
    executable = str(located.path)
    version = toolchain.read_version(located.path, "xtb")

    motifs = load_motifs(Path(args.motif_json))
    rows = core_rows()
    if args.only:
        wanted = {token.strip() for token in args.only.split(",") if token.strip()}
        motifs = [
            motif
            for motif in motifs
            if motif["mol_id"] in wanted or motif["name"] in wanted
        ]

    started = time.perf_counter()
    records = []
    for motif in motifs:
        print("shell generation:", motif["mol_id"], motif["name"], motif["motif_id"], flush=True)
        records.extend(build_motif(motif, rows[motif["name"]], args, executable))

    outdir = Path(args.outdir)
    csv_path = write_csv(outdir / "ms_shell_generation.csv", records)
    md_path = write_markdown(outdir / "ms_shell_generation.md", records, motifs)
    selected = [record for record in records if record["selected"]]
    summary = {
        "stage": "T10-step1-explicit-microsolvation-shells",
        "rule": "v2 section 17.1 targeted sensitivity check; homoleptic [Li(M)2]+",
        "xtb_version": version,
        "n_shell": N_SHELL,
        "n_directions": N_DIRECTIONS,
        "n_rolls": N_ROLLS,
        "clash_ratio": CLASH_RATIO,
        "molecules": ["%s/%s" % (motif["name"], motif["motif_id"]) for motif in motifs],
        "n_placements": len(records),
        "n_clash_free": sum(1 for record in records if record["placement_status"] == "clash_free"),
        "n_scored": sum(1 for record in records if record["sp_status"]),
        "n_selected": len(selected),
        "qc_flag_counts": {
            flag: sum(1 for record in records if flag in (record["qc_flags"] or ""))
            for flag in (
                "geometry_failed",
                "no_intact_minimum_found",
                "dissociated_optimized_product",
                "scf_failed",
            )
        },
        "seconds": round(time.perf_counter() - started, 2),
        "command": "scripts/build_microsolvation_shells.py " + " ".join(sys.argv[1:]),
        "csv": relative(csv_path),
        "markdown": relative(md_path),
        "shells": [
            {
                "mol_id": record["mol_id"],
                "name": record["name"],
                "family": record["family"],
                "motif_id": record["motif_id"],
                "li_contacts": record["li_contacts"],
                "li_min_distance_a": record["li_min_distance_a"],
                "second_ligand_intact": record["second_ligand_intact"],
                "qc_flags": record["qc_flags"],
                "path": "structures/microsolvation/%s_%s_shell2.xyz"
                % (record["name"], record["motif_id"]),
            }
            for record in selected
        ],
    }
    json_path = outdir / "ms_shell_generation.json"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    print("placements", len(records), "selected", len(selected), "->", relative(csv_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())