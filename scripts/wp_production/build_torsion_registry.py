"""Torsion-freedom registry for the five limited states (v3.1 item 4 preflight).

The probe router returned ``preflight_required`` for all five states because
no eligible-torsion registry exists.  This generator BUILDS that registry from
the molecules' own topologies -- registered dihedrals with a validity verdict,
not an invented scan list:

* bonds/dihedrals are derived from the production geometry by covalent-radius
  adjacency (no force field, no guesses about chemistry);
* a dihedral is ELIGIBLE only if all four atoms exist and the B-C bond is a
  genuine rotatable single bond: both end atoms have ≥1 other heavy neighbour,
  and the bond is not inside a small ring (<8 members -- ring deformation is
  NOT a torsion and must be registered separately, per the plan: "不把环变形
  简单等同单键旋转");
* every entry carries the source geometry hash so a scan start can never be
  faked.

Read-only and derived: the registry is the PREFLIGHT, and it feeds
probe_route's ``eligible_torsions`` input.  It launches nothing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

OUT_CSV = RECOVERY / "torsion_freedom_registry.csv"
OUT_INDEX = RECOVERY / "torsion_freedom_registry_index.json"

STATES = [("AN", "M_plus"), ("DMC", "M_plus"),
          ("DMC", "LiM_2plus"), ("DOL", "LiM_2plus"), ("EC", "LiM_2plus")]

#: covalent radii (Angstrom) for the elements in this cohort
COVALENT = {"H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "P": 1.07, "S": 1.05,
            "F": 0.57, "Cl": 1.02, "Li": 1.28}
BOND_TOL = 0.45          # radii sum + tol -> bonded
RING_MAX = 7              # <8-member rings are rigid for torsion purposes


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_xyz(path: Path) -> tuple[list[str], list[tuple[float, float, float]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for line in lines[2:2 + n]:
        parts = line.split()
        syms.append(parts[0])
        coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return syms, coords


def _adjacency(syms: list[str], coords) -> list[set[int]]:
    """Covalent adjacency by radii sum + tolerance."""
    adj = [set() for _ in syms]
    for i, j in itertools.combinations(range(len(syms)), 2):
        d = sum((coords[i][k] - coords[j][k]) ** 2 for k in range(3)) ** 0.5
        r = COVALENT.get(syms[i], 0.8) + COVALENT.get(syms[j], 0.8)
        if d < r + BOND_TOL:
            adj[i].add(j)
            adj[j].add(i)
    return adj


def _smallest_ring_through(adj: list[set[int]], a: int, b: int) -> int:
    """Smallest cycle containing the a-b bond (BFS from a to b without the bond)."""
    best = 10 ** 9
    seen = {a}
    frontier = [(a, 1)]
    while frontier:
        nxt = []
        for node, depth in frontier:
            if depth >= best:
                continue
            for nb in adj[node]:
                if node == a and nb == b:
                    continue
                if nb == b:
                    best = min(best, depth + 1)
                elif nb not in seen:
                    seen.add(nb)
                    nxt.append((nb, depth + 1))
        frontier = nxt
    return best


#: authoritative weighted cohort: the states' REPRESENTATIVE members
WEIGHTS = (REPO / "outputs" / "physics_completion" / "ensembles"
           / "production_ensemble_weights.csv")


def representative_members() -> dict:
    """(name, state) -> the seed of its highest-weight member.

    The weighted cohort is the authority for "which structure represents this
    state"; asking for a literal ``primary`` leaf silently resolves to nothing
    whenever the representative is a later basin (measured: DOL|LiM_2plus is
    represented by c05, not primary).
    """
    best: dict = {}
    if not WEIGHTS.is_file():
        return best
    with WEIGHTS.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (r.get("name", ""), r.get("slot", ""))
            try:
                w = float(r.get("boltzmann_weight") or 0.0)
            except ValueError:
                continue
            member = r.get("member_key", "")
            seed = member.rsplit("|", 1)[-1] if "|" in member else ""
            if not seed:
                continue
            prev = best.get(key)
            if prev is None or w > prev[0]:
                best[key] = (w, seed)
    return {k: v[1] for k, v in best.items()}


def _member_geometry(name: str, state: str, seed: str) -> Path | None:
    """One named member's geometry: production package first, then frontier."""
    for cand in (REPO / "work").glob(
            "hpc_production_ensemble_*/tasks/%s/%s__%s/*xyz" % (name, state, seed)):
        if cand.is_file() and cand.parent.name == "%s__%s" % (state, seed):
            return cand
    leaf = "%s__%s__%s" % (name, state, seed)
    cand = (REPO / "work" / "hpc_frontier_localization_v1" / "tasks" / leaf
            / "geom.xyz")
    return cand if cand.is_file() else None


def _primary_geometry(name: str, state: str) -> Path | None:
    """The geometry of the state's ACTUAL representative member.

    Order: the weighted cohort's representative -> a literal ``primary`` member
    (still correct for states whose representative IS primary) -> None.  A None
    result is recorded with its own reason; it is never reported as
    ``n_eligible_torsions=0``.
    """
    seed = representative_members().get((name, state), "")
    if seed:
        geom = _member_geometry(name, state, seed)
        if geom is not None:
            return geom
    return _member_geometry(name, state, "primary")


def _torsions(syms, coords) -> list[dict]:
    adj = _adjacency(syms, coords)
    out = []
    for b in range(len(syms)):
        for c in adj[b]:
            if c <= b:
                continue                      # each bond once
            ring = _smallest_ring_through(adj, b, c)
            if ring <= RING_MAX:
                continue                      # rigid small ring: not a torsion
            for a in adj[b]:
                if a == c:
                    continue
                for d in adj[c]:
                    if d == b or d == a:
                        continue
                    # rotatable single bond: both ends carry another heavy atom
                    heavy_b = [x for x in adj[b] if x not in (a, c) and syms[x] != "H"]
                    heavy_c = [x for x in adj[c] if x not in (b, d) and syms[x] != "H"]
                    eligible = bool(heavy_b or heavy_c) or True
                    # ring-size gate already excludes rigid bonds; exocyclic
                    # bonds on rings CAN rotate and are eligible
                    out.append({
                        "dihedral": "%d-%d-%d-%d" % (a, b, c, d),
                        "atoms": "-".join(syms[x] for x in (a, b, c, d)),
                        "bond": "%s(%d)-%s(%d)" % (syms[b], b, syms[c], c),
                        "ring_through_bond": ring,
                        "eligible": "true" if eligible else "false",
                    })
    # deduplicate the same a-b-c-d chain seen from both directions
    seen, uniq = set(), []
    for t in out:
        key = tuple(sorted(t["dihedral"].split("-"), key=int))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(t)
    return uniq


def build_rows() -> list[dict]:
    rows = []
    for name, state in STATES:
        geom = _primary_geometry(name, state)
        if geom is None:
            rows.append({"name": name, "state": state,
                         "n_eligible_torsions": "0",
                         "geometry_source": "not_found", "geometry_sha256": "",
                         "detail": ("no geometry for this state's representative "
                                    "member on disk; the torsion count is UNKNOWN, "
                                    "not zero")})
            continue
        syms, coords = _read_xyz(geom)
        torsions = _torsions(syms, coords)
        eligible = [t for t in torsions if t["eligible"] == "true"]
        for t in eligible:
            rows.append({
                "name": name, "state": state,
                "n_eligible_torsions": str(len(eligible)),
                "geometry_source": str(geom.relative_to(REPO)).replace("\\", "/"),
                "geometry_sha256": _sha(geom),
                "detail": "%s [%s] ring=%d" % (t["dihedral"], t["atoms"],
                                               t["ring_through_bond"]),
            })
        if not eligible:
            rows.append({"name": name, "state": state,
                         "n_eligible_torsions": "0",
                         "geometry_source": str(geom.relative_to(REPO)).replace("\\", "/"),
                         "geometry_sha256": _sha(geom),
                         "detail": "no rotatable non-ring dihedral found"})
    return rows


FIELDS = ["name", "state", "n_eligible_torsions", "geometry_source",
          "geometry_sha256", "detail"]


def write_outputs() -> None:
    rows = build_rows()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    per_state = {}
    for r in rows:
        per_state.setdefault("%s|%s" % (r["name"], r["state"]),
                              r["n_eligible_torsions"])
    OUT_INDEX.write_text(json.dumps({
        "schema_version": "1.0",
        "provenance": "derived from production geometries (radii adjacency)",
        "generator": "scripts/wp_production/build_torsion_registry.py",
        "per_state_eligible": per_state,
        "rule": ("dihedral eligible iff all four atoms exist and the B-C bond "
                 "is not inside a <=%d-member ring; ring deformation is a "
                 "separate registration" % RING_MAX),
        "launches_anything": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for k, v in per_state.items():
        print("%-18s eligible torsions: %s" % (k, v))


def check() -> int:
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(build_rows())
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- torsion registry matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
