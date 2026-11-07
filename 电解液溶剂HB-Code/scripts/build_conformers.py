"""Stage 6 / T6: build the conformer ensemble that ``delta_m`` has been missing.

Why this module exists
----------------------
``config/prereg.yaml`` defines ``delta_m`` as a fixed pair tolerance whose value
must come from the *first available* of

    (1) the experimental dispersion of the external anchors themselves,
    (2) the dispersion of the target quantity for one molecule across methods or
        conformers (the Stage 1 / Gate 1 method audit),

and the execution plan spells that out for the conformer half as

    delta_m = max(conformer-ensemble 90th-percentile spread, inter-method spread,
                  0.05 eV floor).

Neither half exists in the repository: every geometry so far is a *single*
RDKit ETKDG embed (seed 0xC0FFEE) relaxed with GFN2-xTB, so nothing has ever
measured how much the target quantity moves when the molecule changes
conformation.  This script produces the ensemble; ``run_t6_conformer_spread.py``
measures the spread on it.

What it does, per molecule
--------------------------
1. RDKit ETKDGv3 embeds ``--n-confs`` conformers of the SAME molecule (same atom
   ordering, same seed as the historical single embed) and pre-optimises them
   with MMFF.
2. Each conformer is relaxed with the frozen GFN2-xTB protocol in its own
   directory, single-threaded for determinism; the parallel fan-out is over
   conformers, not over threads.
3. Conformers are ranked by the xTB energy and thinned by a pre-declared rule
   (see ``RULES``): a conformer survives only if it lies inside the energy
   window AND its heavy-atom RMSD to every already-kept conformer exceeds the
   RMSD threshold.  The rule is written down here, before any spread is
   computed, so it cannot be tuned after seeing the answer.
4. The surviving geometries are written to ``structures/conformers/<NAME>/``,
   mirroring how the Li+ motifs live in ``structures/li_motifs/``.

The historical single conformer is looked up in the ensemble: for every kept
conformer the heavy-atom RMSD to ``outputs/_week3_scratch/<mol_id>/xtbopt.xyz``
is recorded, so a later reader can see whether the ensemble even contains the
geometry the existing P0/P1/C1 tables were measured on.  If it does not, the
conformer spread is measuring a different part of the surface than the ranking
does, and that has to be said out loud rather than averaged away.

Outputs
-------
structures/conformers/<NAME>/conf_<k>.xyz      xTB-relaxed geometries, k by energy
outputs/week6/t6_conformer_manifest.json       full record incl. dropped conformers
outputs/week6/t6_conformer_manifest.csv        one row per kept conformer
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from electrolyte_ranking import toolchain, xtb  # noqa: E402

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
G1_SCRATCH = REPO_ROOT / "outputs" / "_week3_scratch"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week6"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week6_scratch" / "conformers"
DEFAULT_GEOMETRY_DIR = REPO_ROOT / "structures" / "conformers"

#: The twelve molecules T2/T3 already audited.  Keeping the conformer audit on
#: the same subset means sigma_conf, sigma_geom and sigma_env are measured on one
#: set of molecules and can be compared without re-opening the subset question.
AUDIT_SUBSET = ("EC", "PC", "DMC", "EMC", "DME", "DOL",
                "GBL", "AN", "SN", "DMSO", "SL", "TMP")

#: The historical single-conformer embed seed (scripts/run_xtb_job.py default).
#: Reusing it means the existing G1 geometry is inside the sampled set.
HISTORICAL_SEED = 0xC0FFEE

RULES = (
    "reference first: the historical single-conformer G1 geometry "
    "(outputs/_week3_scratch/<mol_id>/xtbopt.xyz) is always part of the ensemble, "
    "because every P0/P1/C1 number in the repository was measured on it -- a "
    "conformer spread that silently excluded it would be measuring a different "
    "part of the surface than the ranking does; the reference counts as conf_0 and "
    "is exempt from the cap; "
    "energy window: an additional conformer survives only within --window-kj "
    "(12.0 kJ/mol) of the lowest xTB energy in the whole ensemble; "
    "RMSD separation: an additional conformer survives only if its heavy-atom RMSD "
    "(Kabsch-aligned, hydrogens excluded) to every already-kept conformer is at "
    "least --rmsd-thresh (0.35 A); "
    "cap: at most --keep (4) additional conformers per molecule, taken in increasing "
    "energy; "
    "floor: if the window admits fewer than 2 conformers in total, the second-lowest "
    "distinct conformer is kept anyway so the spread is at least defined."
)

HARTREE_TO_KJ = 2625.4996394799
COLUMNS = ["name", "mol_id", "conf_id", "path", "energy_eh", "rel_kj", "g1_rmsd_a",
           "matches_g1", "is_g1_reference", "outside_window"]


def load_core_set(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle)]


def select_molecules(spec: str | None, rows: list[dict]) -> list[dict]:
    """Resolve ``--molecules`` (names or mol_ids) against the core set."""

    if spec is None or not spec.strip():
        wanted = {name.upper() for name in AUDIT_SUBSET}
    else:
        wanted = {item.strip().upper() for item in spec.split(",") if item.strip()}
    by_name = {row["name"].upper(): row for row in rows}
    by_id = {row["mol_id"].upper(): row for row in rows}
    selected, unknown = [], []
    for token in sorted(wanted):
        row = by_name.get(token) or by_id.get(token)
        if row is None:
            unknown.append(token)
        else:
            selected.append(row)
    if unknown:
        raise SystemExit("unknown molecule(s) %s; core set has %s"
                         % (unknown, [row["name"] for row in rows]))
    return selected


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------
def read_xyz(path: Path) -> tuple[list[str], np.ndarray]:
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].split()[0])
    symbols, coords = [], []
    for line in lines[2:2 + count]:
        parts = line.split()
        symbols.append(parts[0])
        coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
    if len(symbols) != count:
        raise ValueError("%s: expected %d atoms, parsed %d" % (path, count, len(symbols)))
    return symbols, np.asarray(coords, dtype=float)


def write_xyz(symbols, coords, path: Path, comment: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["%d" % len(symbols), comment]
    lines += ["%-2s % .8f % .8f % .8f" % (symbol, *position)
              for symbol, position in zip(symbols, coords)]
    path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8", newline=chr(10))


def heavy_indices(symbols) -> list[int]:
    return [index for index, symbol in enumerate(symbols) if symbol.upper() != "H"]


def kabsch_rmsd(first: np.ndarray, second: np.ndarray) -> float:
    """Heavy-atom RMSD after optimal rigid superposition (no reflection)."""

    reference = first - first.mean(axis=0)
    moving = second - second.mean(axis=0)
    covariance = moving.T @ reference
    left, _, right = np.linalg.svd(covariance)
    correction = np.eye(3)
    if np.linalg.det(left @ right) < 0:
        correction[2, 2] = -1.0
    rotation = left @ correction @ right
    aligned = moving @ rotation
    return float(math.sqrt(((aligned - reference) ** 2).sum() / len(first)))


def heavy_rmsd(symbols, first: np.ndarray, second: np.ndarray) -> float:
    indices = heavy_indices(symbols)
    return kabsch_rmsd(first[indices], second[indices])

# ---------------------------------------------------------------------------
# conformer generation (RDKit) and relaxation (frozen GFN2-xTB)
# ---------------------------------------------------------------------------
def embed_conformers(row: dict, *, n_confs: int, seed: int, scratch: Path, prune_rmsd: float):
    """ETKDGv3-embed ``n_confs`` conformers and MMFF-pre-optimise them.

    Returns ``(symbols, [(conformer_index, xyz_path, mmff_energy)])``.
    """

    from rdkit import Chem
    from rdkit.Chem import AllChem

    molecule = Chem.MolFromSmiles(row["smiles"])
    if molecule is None:
        raise ValueError("RDKit could not parse SMILES %r" % row["smiles"])
    molecule = Chem.AddHs(molecule)

    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.pruneRmsThresh = prune_rmsd
    params.numThreads = 0
    conformer_ids = list(AllChem.EmbedMultipleConfs(molecule, numConfs=n_confs, params=params))
    if not conformer_ids:
        raise RuntimeError("%s: RDKit embedded no conformer" % row["name"])
    mmff = AllChem.MMFFOptimizeMoleculeConfs(molecule, numThreads=0, maxIters=500)

    symbols = [atom.GetSymbol() for atom in molecule.GetAtoms()]
    embed_dir = scratch / row["name"] / "embed"
    embed_dir.mkdir(parents=True, exist_ok=True)
    produced = []
    for order, conformer_id in enumerate(conformer_ids):
        positions = molecule.GetConformer(conformer_id).GetPositions()
        path = embed_dir / ("c%03d.xyz" % order)
        write_xyz(symbols, positions, path,
                  "%s ETKDGv3 embed #%d seed=%d" % (row["name"], order, seed))
        energy = mmff[conformer_id][1] if conformer_id < len(mmff) else None
        produced.append((order, path, energy))
    return symbols, produced


def relax_conformer(executable: str, source: Path, workdir: Path, *, timeout: float) -> dict:
    """One frozen GFN2-xTB ``--opt`` on a single conformer."""

    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / "conf.xyz"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline=chr(10))
    record = {"source": str(source), "status": "ok", "energy_eh": None,
              "xtbopt": None, "qc_flags": [], "seconds": None, "error": ""}
    started = time.time()
    try:
        result = xtb.run_xtb(
            executable, xtb.JOB_OPTIMIZE, input_name=target.name,
            charge=0, multiplicity=1, cwd=workdir,
            timeout_seconds=timeout, raise_on_failure=False,
        )
    except Exception as error:                      # noqa: BLE001 - recorded, not hidden
        record.update(status="execution_failed", error="%s: %s" % (type(error).__name__, error))
        record["seconds"] = round(time.time() - started, 2)
        return record
    record["seconds"] = round(time.time() - started, 2)
    record["qc_flags"] = list(result.qc_flags)
    record["energy_eh"] = result.total_energy_eh
    optimized = workdir / "xtbopt.xyz"
    if optimized.exists() and optimized.stat().st_size > 0:
        record["xtbopt"] = str(optimized)
    else:
        record["status"] = "geometry_failed"
        record["error"] = "xTB produced no xtbopt.xyz"
    if result.total_energy_eh is None:
        record["status"] = "geometry_failed"
        record["error"] = record["error"] or "xTB printed no total energy"
    return record


def select_conformers(symbols, candidates, *, window_kj: float, rmsd_thresh: float, keep: int):
    """Apply the pre-declared thinning rule; return ``(kept, dropped)``.

    ``candidates`` is a list of dicts with ``energy_eh`` and ``coords``; at most
    one of them may carry ``is_reference`` (the historical G1 geometry).  The
    reference is placed first and survives the cap, so ``conf_0`` is always the
    geometry the rest of the repository was measured on.  ``rel_kj`` is always
    relative to the lowest energy in the whole ensemble, reference included.
    """

    ordered = sorted(candidates, key=lambda item: item["energy_eh"])
    lowest = ordered[0]["energy_eh"]
    reference = [item for item in ordered if item.get("is_reference")]
    others = [item for item in ordered if not item.get("is_reference")]
    kept, dropped = [], []
    for candidate in reference + others:
        rel_kj = (candidate["energy_eh"] - lowest) * HARTREE_TO_KJ
        candidate["rel_kj"] = rel_kj
        is_reference = bool(candidate.get("is_reference"))
        if rel_kj > window_kj:
            candidate["reason"] = "outside the %.1f kJ/mol window (%.2f kJ/mol)" % (window_kj, rel_kj)
            if is_reference:
                candidate["outside_window"] = True
                kept.append(candidate)
            else:
                dropped.append(candidate)
            continue
        distances = [heavy_rmsd(symbols, candidate["coords"], other["coords"]) for other in kept]
        candidate["rmsd_to_kept"] = [round(value, 4) for value in distances]
        if is_reference:
            if distances and min(distances) < rmsd_thresh:
                candidate["reason"] = ("the reference geometry is the same minimum as an "
                                       "already-kept conformer (min heavy-atom RMSD %.3f A)"
                                       % min(distances))
                dropped.append(candidate)
                continue
            kept.append(candidate)
            continue
        if len([item for item in kept if not item.get("is_reference")]) >= keep:
            candidate["reason"] = "cap of %d additional conformers reached" % keep
            dropped.append(candidate)
            continue
        if distances and min(distances) < rmsd_thresh:
            candidate["reason"] = ("duplicate of an already-kept conformer "
                                   "(min heavy-atom RMSD %.3f A < %.2f A)"
                                   % (min(distances), rmsd_thresh))
            dropped.append(candidate)
            continue
        kept.append(candidate)
    if len(kept) < 2:
        for candidate in others:
            if candidate in kept:
                continue
            candidate["forced"] = True
            candidate["rmsd_to_kept"] = [round(heavy_rmsd(symbols, candidate["coords"], other["coords"]), 4)
                                         for other in kept]
            kept.append(candidate)
            if candidate in dropped:
                dropped.remove(candidate)
            break
    return kept, dropped

# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--molecules", default=None,
                        help="comma-separated names or mol_ids (default: the 12-molecule T2/T3 audit subset)")
    parser.add_argument("--n-confs", type=int, default=24, help="ETKDG conformers to embed per molecule")
    parser.add_argument("--prune-rmsd", type=float, default=0.3,
                        help="ETKDG pre-prune threshold in A (generation parameter, not a selection rule)")
    parser.add_argument("--keep", type=int, default=4, help="maximum conformers kept per molecule")
    parser.add_argument("--window-kj", type=float, default=12.0, help="energy window above the lowest, kJ/mol")
    parser.add_argument("--rmsd-thresh", type=float, default=0.35, help="heavy-atom RMSD below which two conformers count as one, A")
    parser.add_argument("--jobs", type=int, default=8, help="parallel xTB processes")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=HISTORICAL_SEED)
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds per xTB relaxation")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--geometry-dir", type=Path, default=DEFAULT_GEOMETRY_DIR)
    parser.add_argument("--no-g1-anchor", action="store_true",
                        help="do NOT force the historical G1 geometry into the ensemble (not recommended)")
    parser.add_argument("--force", action="store_true", help="recompute even when a cached manifest entry exists")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit("xTB not found; cannot build the conformer ensemble")
    rows = select_molecules(args.molecules, load_core_set(CORE_SET))

    manifest_path = args.outdir / "t6_conformer_manifest.json"
    previous = {}
    if manifest_path.exists() and not args.force:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("seed") == args.seed and payload.get("rules") == RULES:
            previous = {entry["name"]: entry for entry in payload.get("molecules", [])}

    entries = []
    for row in rows:
        name, mol_id = row["name"], row["mol_id"]
        if name in previous and not args.force:
            if all((REPO_ROOT / item["path"]).exists() for item in previous[name]["conformers"]):
                print("%-6s cached (%d conformers)" % (name, len(previous[name]["conformers"])))
                entries.append(previous[name])
                continue
        started = time.time()
        symbols, embedded = embed_conformers(
            row, n_confs=args.n_confs, seed=args.seed, scratch=args.scratch,
            prune_rmsd=args.prune_rmsd,
        )
        print("%-6s embedded %d conformers; relaxing with %d parallel xTB jobs"
              % (name, len(embedded), args.jobs))

        def relax(item):
            order, path, _ = item
            workdir = args.scratch / name / ("relax_c%03d" % order)
            record = relax_conformer(located.path, path, workdir, timeout=args.timeout)
            record["order"] = order
            return record

        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            relaxed = list(pool.map(relax, embedded))

        candidates, failures = [], []
        for record in relaxed:
            if record["status"] != "ok" or not record["xtbopt"]:
                failures.append({"candidate": record["order"], "status": record["status"],
                                 "error": record["error"]})
                continue
            xyz_symbols, coords = read_xyz(Path(record["xtbopt"]))
            if xyz_symbols != symbols:
                failures.append({"candidate": record["order"], "status": "atom_order_mismatch",
                                 "error": "xTBopt atom order differs from the embedded molecule"})
                continue
            candidates.append({"candidate": record["order"], "energy_eh": record["energy_eh"],
                               "coords": coords, "xtbopt": record["xtbopt"],
                               "seconds": record["seconds"], "qc_flags": record["qc_flags"]})
        if not candidates:
            raise SystemExit("%s: no conformer survived the xTB relaxation" % name)

        # The historical G1 geometry is relaxed already, so one frozen single point
        # gives its energy on the same footing as the freshly relaxed conformers.
        g1_anchor = None
        anchor_source = G1_SCRATCH / mol_id / "xtbopt.xyz"
        if not args.no_g1_anchor and anchor_source.exists():
            anchor_symbols, anchor_coords = read_xyz(anchor_source)
            if anchor_symbols != symbols:
                failures.append({"candidate": "g1_reference", "status": "atom_order_mismatch",
                                 "error": "cached G1 atom order differs from the embedded molecule"})
            else:
                anchor_dir = args.scratch / name / "g1_anchor"
                anchor_dir.mkdir(parents=True, exist_ok=True)
                anchor_xyz = anchor_dir / "g1.xyz"
                anchor_xyz.write_text(anchor_source.read_text(encoding="utf-8"),
                                      encoding="utf-8", newline=chr(10))
                anchor = xtb.run_xtb(located.path, xtb.JOB_SINGLE_POINT, input_name=anchor_xyz.name,
                                     charge=0, multiplicity=1, cwd=anchor_dir,
                                     timeout_seconds=args.timeout, raise_on_failure=False)
                if anchor.total_energy_eh is not None:
                    g1_anchor = {"candidate": "g1_reference", "is_reference": True,
                                 "energy_eh": anchor.total_energy_eh, "coords": anchor_coords,
                                 "xtbopt": str(anchor_source), "seconds": 0.0,
                                 "qc_flags": list(anchor.qc_flags)}
                else:
                    failures.append({"candidate": "g1_reference", "status": "single_point_failed",
                                     "error": "xTB could not re-evaluate the G1 geometry"})
        if g1_anchor is not None:
            candidates.append(g1_anchor)

        kept, dropped = select_conformers(
            symbols, candidates, window_kj=args.window_kj,
            rmsd_thresh=args.rmsd_thresh, keep=args.keep,
        )

        g1_path = G1_SCRATCH / mol_id / "xtbopt.xyz"
        g1_coords = None
        if g1_path.exists():
            g1_symbols, g1_coords = read_xyz(g1_path)
            if g1_symbols != symbols:
                g1_coords = None

        conformers = []
        for rank, item in enumerate(kept):
            target = args.geometry_dir / name / ("conf_%d.xyz" % rank)
            comment = ("%s conformer %d/%d rel=%+.2f kJ/mol from %s; "
                       "GFN2-xTB opt; T6 conformer ensemble"
                       % (name, rank, len(kept), item["rel_kj"], item["candidate"]))
            write_xyz(symbols, item["coords"], target, comment)
            g1_rmsd = None if g1_coords is None else round(
                heavy_rmsd(symbols, item["coords"], g1_coords), 4)
            conformers.append({
                "conf_id": "conf_%d" % rank,
                "path": str(target.relative_to(REPO_ROOT)),
                "source_candidate": item["candidate"],
                "energy_eh": item["energy_eh"],
                "rel_kj": round(item["rel_kj"], 4),
                "rmsd_to_kept_a": item.get("rmsd_to_kept", []),
                "g1_rmsd_a": g1_rmsd,
                "matches_g1": None if g1_rmsd is None else bool(g1_rmsd <= 0.15),
                "forced": bool(item.get("forced")),
                "is_g1_reference": bool(item.get("is_reference")),
                "outside_window": bool(item.get("outside_window")),
            })

        entries.append({
            "name": name, "mol_id": mol_id, "smiles": row["smiles"], "family": row["family"],
            "n_conformers_embedded": len(embedded),
            "n_relax_ok": len(candidates), "n_kept": len(conformers),
            "n_failed": len(failures),
            "seconds": round(time.time() - started, 2),
            "conformers": conformers,
            "dropped": [{"candidate": item["candidate"], "rel_kj": round(item["rel_kj"], 4),
                         "reason": item["reason"]} for item in dropped],
            "failures": failures,
        })
        print("%-6s kept %d/%d (window %.1f kJ/mol, RMSD >= %.2f A); G1 match: %s"
              % (name, len(conformers), len(candidates), args.window_kj, args.rmsd_thresh,
                 [item["matches_g1"] for item in conformers]))

    payload = {
        "stage": "T6 (Stage 6 input)",
        "title": "conformer ensemble for the delta_m conformer half",
        "engine": "RDKit ETKDGv3 + MMFF (embedding), GFN2-xTB (relaxation)",
        "xtb_executable": located.path,
        "seed": args.seed,
        "subset": [entry["name"] for entry in entries],
        "rules": RULES,
        "parameters": {
            "n_confs": args.n_confs, "keep": args.keep, "window_kj": args.window_kj,
            "prune_rmsd_a": args.prune_rmsd,
            "rmsd_thresh_a": args.rmsd_thresh, "jobs": args.jobs, "timeout_s": args.timeout,
        },
        "g1_reference": "outputs/_week3_scratch/<mol_id>/xtbopt.xyz (the single conformer every earlier table used)",
        "molecules": entries,
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + chr(10),
                            encoding="utf-8", newline=chr(10))
    csv_path = args.outdir / "t6_conformer_manifest.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for entry in entries:
            for conformer in entry["conformers"]:
                writer.writerow({
                    "name": entry["name"], "mol_id": entry["mol_id"],
                    "conf_id": conformer["conf_id"], "path": conformer["path"],
                    "energy_eh": conformer["energy_eh"], "rel_kj": conformer["rel_kj"],
                    "g1_rmsd_a": conformer["g1_rmsd_a"], "matches_g1": conformer["matches_g1"],
                    "is_g1_reference": conformer["is_g1_reference"],
                    "outside_window": conformer["outside_window"],
                })
    total = sum(entry["n_kept"] for entry in entries)
    print("wrote %s (%d molecules, %d kept conformers)" % (manifest_path, len(entries), total))
    print("wrote %s" % csv_path)
    missing_g1 = [entry["name"] for entry in entries
                  if not any(item["matches_g1"] for item in entry["conformers"])]
    if missing_g1:
        print("NOTE: the historical G1 geometry is NOT reproduced within 0.15 A for %s" % missing_g1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())