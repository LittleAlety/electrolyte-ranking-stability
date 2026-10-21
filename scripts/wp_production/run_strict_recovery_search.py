"""strict_recovery_v1 independent basin search (local GFN2 screen).

The recovery batch needs INDEPENDENT starts for the 14 limited states.  This
runner produces them the only honest way: a fresh, versioned conformer search
(round ``r3``) that never back-fills or perturbs an old basin.

Protocol (registered before running; frozen in the output index):

* search level = gas-phase GFN2-xTB ``--opt tight`` -- the cheap screening
  layer, NOT production.  A GFN2 minimum is a *candidate start*, never a label;
* one registered seed (``SEED = 20261021``) and one conformer count per state,
  so the run is reproducible;
* every optimised conformer is deduplicated against the FROZEN pool basins of
  that state **and** against the other new conformers, by heavy-atom RMSD
  under the identity atom mapping (same molecule, same SMILES) with the frozen
  ``RMSD_THRESHOLD = 0.35 A``;
* only genuinely new minima are registered, with geometry sha256, GFN2 energy
  and the RMSD to the nearest already-known basin;
* charge/multiplicity come from the frozen pool row for the state (M_plus =
  +1, multiplicity 2), never guessed.

Outputs (new):

    outputs/physics_completion/recovery/strict_recovery_v1_search_pool.csv
    outputs/physics_completion/recovery/strict_recovery_v1_search_index.json

The search caches raw work under ``work/recovery_search/<name>/<state>/<basin>``
(gitignored) exactly like the older sampling layers.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

OUT = REPO / "outputs" / "physics_completion" / "recovery"
WORK = REPO / "work" / "recovery_search"
POOL_CSV = REPO / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"
COST_LEDGER = REPO / "outputs" / "physics_completion" / "cost" / "production_cost_ledger.csv"

OUT_CSV = OUT / "strict_recovery_v1_search_pool.csv"
OUT_INDEX = OUT / "strict_recovery_v1_search_index.json"

XTB = REPO / ".toolchain" / "xtb" / "xtb-6.7.1" / "bin" / "xtb.exe"
SEED = 20261021
NUM_CONFS = 64
RMSD_THRESHOLD = 0.35
ROUND_TAG = "r3"
BATCH_ID = "strict_recovery_v1"

#: the four P0 states (full-pool Top-3 boundary).  The rest of the 14 are
#: registered for later batches; P0 goes first per the plan.
P0_STATES = [("AN", "M_plus"), ("DMC", "M_plus"), ("EMC", "M_plus"), ("TMP", "M_plus")]

MOLS = {
    "DMC": ("C01", "COC(=O)OC"), "EMC": ("C02", "CCOC(=O)OC"),
    "DEC": ("C03", "CCOC(=O)OCC"), "EC": ("C04", "C1COC(=O)O1"),
    "PC": ("C05", "CC1COC(=O)O1"), "DME": ("C08", "COCCOC"),
    "DOL": ("C09", "C1COCO1"), "GBL": ("C13", "O=C1CCCO1"),
    "SL": ("C14", "O=S1(=O)CCCC1"), "DMSO": ("C15", "CS(C)=O"),
    "AN": ("C16", "CC#N"), "TMP": ("C17", "COP(=O)(OC)OC"),
}

FIELDS = ["batch_id", "mol_id", "name", "state", "charge", "multiplicity",
          "basin_id", "pool", "rank", "n_atoms", "xtb_energy_eh", "rel_kcal",
          "geometry_relpath", "geometry_sha256", "rmsd_to_nearest_known_a",
          "nearest_known_basin", "source_kind", "search_seed", "num_confs",
          "status", "note"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _pool_rows(name: str, state: str) -> list[dict]:
    return [r for r in _rows(POOL_CSV)
            if r.get("name") == name and r.get("state") == state]


def _state_charge(name: str, state: str) -> tuple[int, int]:
    rows = _pool_rows(name, state)
    if not rows:
        raise SystemExit("no frozen pool row for %s/%s -- cannot derive charge" % (name, state))
    return int(rows[0]["charge"]), int(rows[0]["multiplicity"])


def _coords(path: Path) -> list[tuple[str, float, float, float]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    out = []
    for line in lines[2:2 + n]:
        parts = line.split()
        out.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    return out


def rmsd_heavy(a: list[tuple[str, float, float, float]],
               b: list[tuple[str, float, float, float]]) -> float:
    """Heavy-atom RMSD under the identity atom mapping (optimal superposition).

    Horn's quaternion method: for centred coordinate sets with equal atom
    count the squared RMSD at the optimal rotation is

        RMSD^2 = (sum|a|^2 + sum|b|^2 - 2*lambda_max) / n

    where ``lambda_max`` is the largest eigenvalue of the 4x4 key matrix built
    from the 3x3 covariance.  We get ``lambda_max`` by power iteration (no
    numpy in this repo's offline path).
    """
    pa = [(x, y, z) for s, x, y, z in a if s != "H"]
    pb = [(x, y, z) for s, x, y, z in b if s != "H"]
    if len(pa) != len(pb) or not pa:
        raise ValueError("atom count mismatch or empty heavy-atom set")
    n = len(pa)
    ca = [sum(p[i] for p in pa) / n for i in range(3)]
    cb = [sum(p[i] for p in pb) / n for i in range(3)]
    a0 = [[p[i] - ca[i] for i in range(3)] for p in pa]
    b0 = [[p[i] - cb[i] for i in range(3)] for p in pb]
    sxx = sum(x[0] * y[0] for x, y in zip(a0, b0))
    sxy = sum(x[0] * y[1] for x, y in zip(a0, b0))
    sxz = sum(x[0] * y[2] for x, y in zip(a0, b0))
    syx = sum(x[1] * y[0] for x, y in zip(a0, b0))
    syy = sum(x[1] * y[1] for x, y in zip(a0, b0))
    syz = sum(x[1] * y[2] for x, y in zip(a0, b0))
    szx = sum(x[2] * y[0] for x, y in zip(a0, b0))
    szy = sum(x[2] * y[1] for x, y in zip(a0, b0))
    szz = sum(x[2] * y[2] for x, y in zip(a0, b0))
    key = [
        [sxx + syy + szz, syz - szy, szx - sxz, sxy - syx],
        [syz - szy, sxx - syy - szz, sxy + syx, szx + sxz],
        [szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy],
        [sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz],
    ]
    # power iteration for the dominant eigenvalue (key is symmetric)
    q = [0.5, 0.5, 0.5, 0.5]
    lam = 0.0
    for _ in range(200):
        nq = [sum(key[i][j] * q[j] for j in range(4)) for i in range(4)]
        norm = math.sqrt(sum(v * v for v in nq))
        if norm < 1e-15:
            break
        q = [v / norm for v in nq]
        lam = norm
    sum_a = sum(x * x + y * y + z * z for x, y, z in a0)
    sum_b = sum(x * x + y * y + z * z for x, y, z in b0)
    val = (sum_a + sum_b - 2.0 * lam) / n
    return math.sqrt(max(val, 0.0))


def _embed(smiles: str, count: int, seed: int) -> list[str]:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.pruneRmsThresh = -1.0
    ids = AllChem.EmbedMultipleConfs(mol, numConfs=count, params=params)
    AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=2000)
    out = []
    for cid in ids:
        block = Chem.MolToXYZBlock(mol, confId=cid)
        if block:
            out.append(block)
    return out


def _run_xtb(directory: Path, block: str, charge: int, mult: int) -> tuple[str, bool]:
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("xtbrestart*"):
        stale.unlink()
    (directory / "geom.xyz").write_text(block, encoding="utf-8", newline="\n")
    proc = subprocess.run(
        [str(XTB), "geom.xyz", "--gfn", "2", "--chrg", str(charge),
         "--uhf", str(mult - 1), "--opt", "tight"],
        cwd=str(directory), capture_output=True, text=True, errors="replace")
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    import re as _re
    energies = _re.findall(r"TOTAL ENERGY\s+(-?\d+\.\d+)", text)
    converged = "GEOMETRY OPTIMIZATION CONVERGED" in text and (directory / "xtbopt.xyz").is_file()
    return (energies[-1] if energies else ""), converged


def search_state(name: str, state: str) -> list[dict]:
    mol_id, smiles = MOLS[name]
    charge, mult = _state_charge(name, state)
    if not XTB.is_file():
        raise SystemExit("bundled xTB missing at %s" % XTB)
    known = [(r.get("geometry_relpath", ""), r) for r in _pool_rows(name, state)]
    known_coords = []
    for rel, row in known:
        p = REPO / rel
        if p.is_file():
            known_coords.append((rel, row, _coords(p)))

    blocks = _embed(smiles, NUM_CONFS, SEED)
    results = []
    root = WORK / name / state
    if root.is_dir():
        shutil.rmtree(root)
    for i, block in enumerate(blocks):
        directory = root / ("%s_c%02d" % (ROUND_TAG, i))
        energy, ok = _run_xtb(directory, block, charge, mult)
        if not ok or not energy:
            continue
        geom = directory / "xtbopt.xyz"
        results.append({"index": i, "energy": float(energy), "geom": geom,
                        "dir": directory})
    if not results:
        return []

    # dedup: energy order, keep only minima far from every known basin and from
    # each already-kept new minimum
    results.sort(key=lambda r: r["energy"])
    kept = []
    for r in results:
        coords = _coords(r["geom"])
        nearest, nearest_rel = 9.99, ""
        for rel, row, kc in known_coords:
            d = rmsd_heavy(_coords(Path(rel)) if (REPO / rel).is_file() else kc, coords) \
                if False else rmsd_heavy([(s, x, y, z) for s, x, y, z in kc], coords)
            if d < nearest:
                nearest, nearest_rel = d, rel
        for other in kept:
            d = rmsd_heavy([(s, x, y, z) for s, x, y, z in other["coords"]], coords)
            if d < nearest:
                nearest, nearest_rel = d, other["basin"]
        if nearest <= RMSD_THRESHOLD:
            continue
        basin = "%s_c%02d" % (ROUND_TAG, r["index"])
        kept.append({"basin": basin, "energy": r["energy"], "geom": r["geom"],
                     "coords": coords, "rmsd": nearest, "nearest": nearest_rel})
    if not kept:
        return []

    emin = min(k["energy"] for k in kept)
    rows = []
    for rank, k in enumerate(kept, 1):
        rel = str(k["geom"].relative_to(REPO)).replace("\\", "/")
        rows.append({
            "batch_id": BATCH_ID, "mol_id": mol_id, "name": name, "state": state,
            "charge": str(charge), "multiplicity": str(mult),
            "basin_id": k["basin"], "pool": "union_round1_round3", "rank": str(rank),
            "n_atoms": str(len(k["coords"])),
            "xtb_energy_eh": "%.9f" % k["energy"],
            "rel_kcal": "%.3f" % ((k["energy"] - emin) * 627.5094740631),
            "geometry_relpath": rel, "geometry_sha256": _sha256(k["geom"]),
            "rmsd_to_nearest_known_a": "%.3f" % k["rmsd"],
            "nearest_known_basin": k["nearest"],
            "source_kind": "recovery_search_%s" % ROUND_TAG,
            "search_seed": str(SEED), "num_confs": str(NUM_CONFS),
            "status": "candidate_start",
            "note": ("gas-phase GFN2 minimum, independent of the frozen pool; "
                     "running it at production level is a registered strict_recovery_v1 leg"),
        })
    return rows


def build(states: list[tuple[str, str]]) -> list[dict]:
    rows: list[dict] = []
    for name, state in states:
        rows.extend(search_state(name, state))
    return rows


def write_outputs(rows: list[dict], searched: list[tuple[str, str]] | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    per_state: dict[str, int] = {}
    for r in rows:
        key = "%s|%s" % (r["name"], r["state"])
        per_state[key] = per_state.get(key, 0) + 1
    index = {
        "schema_version": "1.0",
        "batch_id": BATCH_ID,
        "generator": "scripts/wp_production/run_strict_recovery_search.py",
        "protocol": {
            "level": "gas-phase GFN2-xTB --opt tight (screening only, NOT production)",
            "seed": SEED, "num_confs_per_state": NUM_CONFS,
            "dedup": "heavy-atom Kabsch RMSD vs frozen pool + already-kept minima",
            "rmsd_threshold_a": RMSD_THRESHOLD,
            "charge_source": "frozen pool row per state (never guessed)",
        },
        "inputs": {str(POOL_CSV.relative_to(REPO)): _sha256(POOL_CSV)},
        "per_state_new_minima": per_state,
        # every state the search actually visited -- including those where all
        # conformers collapsed onto an existing minimum (a real finding, not a
        # missing run).  Without this a zero-result state looks "not searched".
        "states_searched": ["%s|%s" % (n, s) for n, s in sorted(searched or [])],
        "n_rows": len(rows),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    if not OUT_CSV.is_file():
        print("CHECK FAILED -- search pool missing (run the search first)")
        return 1
    rows = _rows(OUT_CSV)
    bad = []
    for r in rows:
        p = REPO / r["geometry_relpath"]
        if not p.is_file():
            bad.append("%s: missing geometry" % r["basin_id"])
        elif _sha256(p) != r["geometry_sha256"]:
            bad.append("%s: sha256 mismatch" % r["basin_id"])
        if float(r["rmsd_to_nearest_known_a"]) <= RMSD_THRESHOLD:
            bad.append("%s: not independent (rmsd<=%.2f)" % (r["basin_id"], RMSD_THRESHOLD))
    if bad:
        for b in bad:
            print("STALE: " + b)
        return 1
    print("CHECK OK -- %d recovery search minima verified independent" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--states", default="",
                    help="comma list name:state (default: the four P0 M_plus states)")
    ap.add_argument("--check", action="store_true",
                    help="verify registered minima are still independent + hashed")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    if args.states:
        states = [tuple(s.split(":")) for s in args.states.split(",") if s.strip()]
    else:
        states = list(P0_STATES)
    rows = build(states)
    write_outputs(rows, searched=states)
    print("recovery search: %d new independent minima across %d state(s)"
          % (len(rows), len(states)))
    for r in rows:
        print("  %-5s %-9s %-8s rmsd=%.2f A  rel=%.2f kcal"
              % (r["name"], r["state"], r["basin_id"],
                 float(r["rmsd_to_nearest_known_a"]), float(r["rel_kcal"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
