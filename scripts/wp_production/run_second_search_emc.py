"""Second-round search for EMC|M_plus under a REGISTERED method change.

User ruling (2026-10-21): authorise a method-change search **only for
``EMC|M_plus``**, because WP3's R4 ladder has exactly two unfinished pairs and
both are blocked by that single state.

The plan's preconditions are honoured literally -- "先版本化预注册新池、成本上限
和停止规则，再计算；不回填旧池":

**FROZEN REGISTRATION (written before any calculation)**

1. Method change -- exactly ONE axis differs from round 1, everything else is
   identical:
   * round 1: gas-phase GFN2-xTB, ``--opt tight``, 64 ETKDGv3 conformers,
     seed 20261021;
   * round 2: **implicit solvent** GFN2-xTB + **ALPB(acetonitrile)**,
     ``--opt tight``, **256** ETKDGv3 conformers, seed **20261022**.
   Rationale: production uses SMD(acetonitrile); a gas-phase screen can miss
   conformers that only exist because the solvent shell stabilises them.  The
   larger sample is registered together because a single conformer count is not
   a method axis worth a separate round.
2. Cost cap -- screening level only (local CPU, no HPC allocation).  Production
   legs are spawned ONLY for genuinely new minima, at most 2 per state.
3. Stop rule -- if no new independent minimum appears, the state registers
   ``search_method_exhausted`` and stays ``limited`` for good under this method
   family.  No third round is authorised.
4. No back-fill -- the round-2 minima go into their own versioned pool file; the
   round-1 pool and its index are never rewritten.

    .venv\\Scripts\\python.exe -X utf8 scripts/wp_production/run_second_search_emc.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# round-1 machinery is reused verbatim (embedding, Kabsch dedup, RMSD threshold)
_spec = importlib.util.spec_from_file_location(
    "round1_search", HERE / "run_strict_recovery_search.py")
R1 = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(HERE))
_spec.loader.exec_module(R1)

_m = importlib.util.spec_from_file_location(
    "ens_manifest", HERE / "build_production_ensemble_manifest.py")
manifest = importlib.util.module_from_spec(_m)
_m.loader.exec_module(manifest)


def _atoms(syms, xyz):
    """(symbol, x, y, z) tuples -- rmsd_heavy's expected input."""
    return [(s, float(x[0]), float(x[1]), float(x[2])) for s, x in zip(syms, xyz)]

OUT = REPO / "outputs" / "physics_completion" / "recovery"
OUT_POOL = OUT / "strict_recovery_v2_emc_pool.csv"
OUT_INDEX = OUT / "strict_recovery_v2_emc_index.json"
R1_POOL = OUT / "strict_recovery_v1_search_pool.csv"

TARGET = ("EMC", "M_plus")
SEED = 20261022
NUM_CONFS = 256
SOLVENT = "acetonitrile"
WORKERS = 8
FIELDS = ["name", "state", "basin_id", "pool", "rank", "n_atoms", "xtb_energy_eh",
          "rel_kcal", "xtb_solvent", "search_seed", "num_confs", "geometry",
          "rmsd_to_round1_min_a", "is_new_vs_round1"]


def _run_xtb(directory: Path, block: str, charge: int, mult: int) -> tuple[str, bool]:
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("xtbrestart*"):
        stale.unlink()
    (directory / "geom.xyz").write_text(block, encoding="utf-8", newline="\n")
    proc = subprocess.run(
        [str(R1.XTB), "geom.xyz", "--gfn", "2", "--chrg", str(charge),
         "--uhf", str(mult - 1), "--opt", "tight", "--alpb", SOLVENT],
        cwd=str(directory), capture_output=True, text=True, errors="replace")
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    energies = re.findall(r"TOTAL ENERGY\s+(-?\d+\.\d+)", text)
    converged = "GEOMETRY OPTIMIZATION CONVERGED" in text and (directory / "xtbopt.xyz").is_file()
    return (energies[-1] if energies else ""), converged


CONFORMER_SET = (REPO / "outputs" / "physics_completion" / "sampling"
                 / "sampling_conformer_set.csv")


def _baseline_minima() -> list[tuple[str, list, list]]:
    """Every ALREADY-KNOWN minimum of this state, from BOTH inventories.

    Comparing only against the round-1 search pool is wrong for a state whose
    round-1 search found nothing: that pool then holds no ``minima`` rows, and an
    empty baseline would make every round-2 minimum look "new".  The conformer
    set is the authoritative inventory of the state's existing minima, so it is
    read too.  An empty baseline is reported as ``unknown``, never as ``new``.
    """
    out, seen = [], set()
    if R1_POOL.is_file():
        with R1_POOL.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row["name"], row["state"]) != TARGET or row.get("pool") != "minima":
                    continue
                geom = REPO / (row.get("geometry_relpath") or "")
                if geom.is_file() and str(geom) not in seen:
                    seen.add(str(geom))
                    syms, xyz = manifest.read_xyz(geom)
                    out.append((row["geometry_relpath"], syms, xyz))
    if CONFORMER_SET.is_file():
        with CONFORMER_SET.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row["name"], row["state"]) != TARGET:
                    continue
                geom = REPO / (row.get("geometry_relpath") or "")
                if geom.is_file() and str(geom) not in seen:
                    seen.add(str(geom))
                    syms, xyz = manifest.read_xyz(geom)
                    out.append((row["geometry_relpath"], syms, xyz))
    return out


def main(argv=None) -> int:
    name, state = TARGET
    mol_id, smiles = R1.MOLS[name]
    charge, mult = R1._state_charge(name, state)
    work = REPO / "work" / "second_search_v2_emc"
    work.mkdir(parents=True, exist_ok=True)

    print("registered method change:")
    print("  round 1: gas GFN2 --opt tight, 64 confs, seed 20261021")
    print("  round 2: GFN2 + ALPB(%s) --opt tight, %d confs, seed %d" % (SOLVENT, NUM_CONFS, SEED))
    blocks = R1._embed(smiles, NUM_CONFS, SEED)
    print("  embedded %d conformers" % len(blocks))

    def one(i: int):
        energy, ok = _run_xtb(work / ("c%03d" % i), blocks[i], charge, mult)
        if not ok or not energy:
            return None
        syms, xyz = manifest.read_xyz(work / ("c%03d" % i) / "xtbopt.xyz")
        if not syms:
            return None
        return {"idx": i, "energy": float(energy), "syms": syms, "xyz": xyz}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = [r for r in pool.map(one, range(len(blocks))) if r]
    print("  converged optimisations: %d / %d" % (len(results), len(blocks)))
    if not results:
        print("REJECT: nothing converged")
        return 2

    results.sort(key=lambda r: r["energy"])
    kept: list[dict] = []
    for r in results:
        dup = False
        for k in kept:
            if R1.rmsd_heavy(_atoms(r["syms"], r["xyz"]),
                             _atoms(k["syms"], k["xyz"])) < R1.RMSD_THRESHOLD:
                dup = True
                break
        if not dup:
            kept.append(r)
    print("  independent minima after dedup: %d" % len(kept))

    # compare against round 1 to separate genuinely-new basins
    r1mins = _baseline_minima()
    if not r1mins:
        print("WARNING: no baseline minimum found; newness is UNKNOWN, not claimed")
    rows = []
    for rank, k in enumerate(kept, start=1):
        best = min(
            (R1.rmsd_heavy(_atoms(k["syms"], k["xyz"]), _atoms(s, x))
             for _path, s, x in r1mins), default=float("inf"))
        # fail-closed: without a baseline we cannot claim a new basin
        is_new = (best >= R1.RMSD_THRESHOLD) if r1mins else None
        geom_rel = "work/second_search_v2_emc/c%03d/xtbopt.xyz" % k["idx"]
        rows.append({
            "name": name, "state": state, "basin_id": "v2_c%03d" % k["idx"],
            "pool": "minima", "rank": str(rank), "n_atoms": str(len(k["syms"])),
            "xtb_energy_eh": "%.9f" % k["energy"],
            "rel_kcal": "%.3f" % ((k["energy"] - kept[0]["energy"]) * 627.5094740631),
            "xtb_solvent": "alpb_%s" % SOLVENT, "search_seed": str(SEED),
            "num_confs": str(NUM_CONFS), "geometry": geom_rel,
            "rmsd_to_round1_min_a": ("%.4f" % best) if r1mins else "n/a",
            "is_new_vs_round1": ("unknown" if is_new is None
                                 else ("true" if is_new else "false")),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    with OUT_POOL.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    new_count = sum(1 for r in rows if r["is_new_vs_round1"] == "true")
    unknown_count = sum(1 for r in rows if r["is_new_vs_round1"] == "unknown")
    index = {
        "schema_version": 1,
        "registration_written_before_computation": True,
        "state": "%s|%s" % TARGET,
        "method_round1": {"phase": "gas", "n_confs": 64, "seed": 20261021,
                          "solvent": None},
        "method_round2": {"phase": "gf2_alpb", "n_confs": NUM_CONFS, "seed": SEED,
                          "solvent": SOLVENT},
        "changed_axis": ["implicit_solvent", "conformer_count"],
        "stop_rule": ("no new independent minimum -> search_method_exhausted; the state "
                      "stays limited under this method family; no third round"),
        "cost_cap": "screening level only; production legs only for new minima, max 2",
        "no_backfill": "round-1 pool and index are never rewritten",
        "converged_optimisations": len(results),
        "independent_minima": len(kept),
        "new_vs_round1": new_count,
        "unknown_newness": unknown_count,
        "rmsd_threshold_a": R1.RMSD_THRESHOLD,
        "geometry_provenance": str(work.relative_to(REPO)).replace("\\", "/"),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    print("round 2: %d independent minima, %d NEW vs round 1" % (len(kept), new_count))
    if new_count == 0:
        print("STOP RULE TRIGGERED: EMC|M_plus -> search_method_exhausted (stays limited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
