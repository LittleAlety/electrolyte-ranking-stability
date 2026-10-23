"""Torsion-probe preregistration + package build for the 4 authorised states.

The probe router returned ``draft_torsion_probe`` for four states; the user's
blanket authorisation (2026-10-22) covers executing them.  This generator does
exactly what the plan's shared gate requires BEFORE any calculation:

* candidates      -- one scan point per registered eligible torsion, taken
                     from the torsion registry (hashed source geometry);
* identity        -- each start geometry is the state's own converged primary
                     minimum rotated about ONE dihedral by a fixed offset;
* dedup           -- a rotated start that is symmetrically equivalent to
                     another start of the same state is dropped (C-H threefold
                     rotations of a methyl are one probe, not three);
* budget          -- scan points x ~12 core-hours, capped per state;
* stop rule       -- only qualified, submitted points may run at production
                     level. Completed points still require scientific QC and
                     production dedup before entering coverage review. Rejected
                     or rigid-equivalent starts cannot establish exhaustion;
                     this builder does not upgrade scientific acceptance.

The scan geometry rotates one covalently connected fragment by a FIXED +60
degrees about a verified single b-c bond. This is a bounded starting-geometry
probe, not proof of another basin or of exhaustive sampling. Preflight rejects
rigid and symmetry-equivalent starts; downstream QC must still verify identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

#: the same covalent-graph comparison the importer uses, so a conformer and an
#: imported attempt can never disagree about what "the same molecule" means.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_ensemble_structures import bond_graph  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

REGISTRY = RECOVERY / "torsion_freedom_registry.csv"
OUT_PKG = REPO / "work" / "hpc_torsion_probe_v1"

#: fixed rotation applied to every eligible dihedral (degrees)
SCAN_OFFSET_DEG = 60.0
#: per-state cap on scan points (the plan's bounded-probe discipline)
MAX_POINTS_PER_STATE = 3
#: budget note per production leg (M_plus/LiM_2plus measured average)
COST_BASIS_CORE_HOURS = 12.0

STATES = [("AN", "M_plus"), ("DMC", "M_plus"),
          ("DMC", "LiM_2plus"), ("EC", "LiM_2plus")]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    syms = []
    coords = []
    for line in lines[2:2 + n]:
        parts = line.split()
        syms.append(parts[0])
        coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return syms, coords, lines[1]


def _rotate_about_axis(coords, b_idx: int, c_idx: int, deg: float, *, moving_indices):
    """Rotate the b-side fragment about the b->c axis by `deg` degrees."""
    out = [list(p) for p in coords]
    # axis unit vector
    axis = [coords[c_idx][k] - coords[b_idx][k] for k in range(3)]
    norm = math.sqrt(sum(a * a for a in axis))
    if norm < 1e-10:
        raise ValueError("degenerate rotation axis")
    axis = [a / norm for a in axis]
    th = math.radians(deg)
    cos_t, sin_t = math.cos(th), math.sin(th)
    # Rodrigues rotation about the axis through atom b
    bx, by, bz = coords[b_idx]
    for i, p in enumerate(out):
        if i not in moving_indices:
            continue
        # translate so b is origin
        x, y, z = p[0] - bx, p[1] - by, p[2] - bz
        # rotate
        dot = x * axis[0] + y * axis[1] + z * axis[2]
        cx = axis[1] * z - axis[2] * y
        cy = axis[2] * x - axis[0] * z
        cz = axis[0] * y - axis[1] * x
        out[i] = [
            x * cos_t + cx * sin_t + axis[0] * dot * (1 - cos_t) + bx,
            y * cos_t + cy * sin_t + axis[1] * dot * (1 - cos_t) + by,
            z * cos_t + cz * sin_t + axis[2] * dot * (1 - cos_t) + bz,
        ]
    return out


def validate_batch_partition(tasks, chunks):
    flat = [task for chunk in chunks for task in chunk]
    if (not tasks or any(not chunk for chunk in chunks)
            or len(tasks) != len(set(tasks)) or Counter(flat) != Counter(tasks)):
        raise ValueError("batch tasks overlap, are missing, or are duplicated")


def render_batch_script(template, batch, count):
    if type(batch) is not int or batch < 1 or type(count) is not int or not 1 <= count <= 8:
        raise ValueError("invalid batch index/count")
    script = template % (count - 1)
    token = 'p" tasks.txt)'
    if script.count(token) != 1:
        raise ValueError("batch template task lookup is unknown")
    return script.replace(token, 'p" batch_%d.txt)' % batch)


def _topology_for_member(name, symbols):
    """Use registered bond orders, not distance-only guesses (C=O is not a rotor).

    Explicit-H SMILES atom order must match the source geometry exactly. Li is
    a separate coordination partner, never silently added as a covalent bond.
    """
    from rdkit import Chem
    import run_batch as rb
    matches = [entry for entry in rb.MOLS if entry[1] == name]
    if len(matches) != 1:
        raise ValueError("unknown registered molecule")
    mol = Chem.AddHs(Chem.MolFromSmiles(matches[0][2]))
    expected = [atom.GetSymbol() for atom in mol.GetAtoms()]
    if list(symbols) not in (expected, expected + ["Li"]):
        raise ValueError("registered SMILES/geometry atom order mismatch")
    adj = [set() for _ in symbols]
    singles = set()
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        adj[i].add(j)
        adj[j].add(i)
        if bond.GetBondType() == Chem.BondType.SINGLE and not bond.GetIsAromatic():
            singles.add(tuple(sorted((i, j))))
    return adj, singles


def rotate_fragment(coords, dihedral, adjacency, *, single_bonds, degrees):
    """Rotate ONLY the a/b-side of a verified single bridge bond.

    Reject rings, a linear/undefined dihedral, accidental rigid transformations,
    bond distortion and obvious new clashes. No geometry optimization is run.
    """
    xyz = np.asarray(coords, dtype=float)
    a, b, c, d = dihedral
    n = len(xyz)
    if (xyz.shape != (n, 3) or not np.isfinite(xyz).all()
            or len(adjacency) != n or len(set(dihedral)) != 4
            or any(type(i) is not int or not 0 <= i < n for i in dihedral)
            or not math.isfinite(degrees)):
        raise ValueError("invalid dihedral/coordinates")
    if tuple(sorted((b, c))) not in single_bonds:
        raise ValueError("central bond is not a verified single bond")
    if any(j not in adjacency[i] for i, j in ((a, b), (b, c))):
        raise ValueError("dihedral is not connected on the moving side")
    # d may be a registered Li coordination partner; it must remain outside
    # the covalent moving component, not be invented as a covalent bond.
    moving, stack = {b}, [b]
    while stack:
        i = stack.pop()
        for j in adjacency[i]:
            if {i, j} == {b, c}:
                continue
            if j not in moving:
                moving.add(j)
                stack.append(j)
    if c in moving:
        raise ValueError("central bond belongs to a ring")
    if a not in moving or d in moving:
        raise ValueError("dihedral endpoints do not straddle the cut")
    axis = xyz[c] - xyz[b]
    if np.linalg.norm(axis) < 1e-10:
        raise ValueError("degenerate axis")
    for flank in (xyz[a] - xyz[b], xyz[d] - xyz[c]):
        scale = np.linalg.norm(axis) * np.linalg.norm(flank)
        if scale < 1e-12 or np.linalg.norm(np.cross(axis, flank)) / scale < 1e-4:
            raise ValueError("degenerate/linear dihedral")
    rotated = np.asarray(_rotate_about_axis(xyz, b, c, degrees, moving_indices=moving))
    before = np.linalg.norm(xyz[:, None] - xyz[None, :], axis=2)
    after = np.linalg.norm(rotated[:, None] - rotated[None, :], axis=2)
    change = float(np.max(np.abs(before - after)))
    if change <= 1e-5:
        raise ValueError("probe is only a rigid transformation")
    for i in range(n):
        for j in range(i + 1, n):
            if j in adjacency[i] and abs(before[i, j] - after[i, j]) > 1e-8:
                raise ValueError("covalent bond length changed")
            if j not in adjacency[i] and after[i, j] < 0.6:
                raise ValueError("probe has an obvious atomic clash")
    return rotated, {"moving_indices": sorted(moving), "pair_distance_change_a": change,
                     "rotation_degrees": degrees, "contract": "fragment_bridge_v1"}


def _edge_set(bond_graph_result) -> set:
    """Undirected edge set.

    ``bond_graph`` already returns a SET of ``(i, j)`` index pairs, but an
    adjacency-list form is accepted too, so the helper cannot misread its input
    (measured: treating that set as an adjacency list raises
    "'set' object is not subscriptable").
    """
    if isinstance(bond_graph_result, (set, frozenset)):
        return {tuple(sorted((int(a), int(b)))) for a, b in bond_graph_result}
    return {tuple(sorted((i, j)))
            for i in range(len(bond_graph_result))
            for j in bond_graph_result[i] if i < j}


def _li_first_shell(symbols, coords, *, cutoff=2.6):
    """Which atoms sit in each Li's first coordination shell.

    A torsion probe must not silently change the coordination environment: that
    is a different probe kind, registered separately, not a side effect.
    """
    xyz = np.asarray(coords, dtype=float)
    shells = {}
    for li in range(len(symbols)):
        if symbols[li] != "Li":
            continue
        d = np.linalg.norm(xyz - xyz[li], axis=1)
        shells[li] = frozenset(int(k) for k in np.where((d > 0) & (d <= cutoff))[0])
    return shells


def validate_candidate_start(symbols, source_coords, candidate_coords, adjacency,
                            *, prior_starts=(), min_pair_change_a=1e-5,
                            registered_single_bonds=None, rotated_bond=None,
                            check_li_shell=True):
    """One gate every candidate start must pass, whatever generated it.

    Returns ``{"accepted": bool, "reason": str, "detail": {...}}`` -- a verdict,
    never an exception, so a caller can register the refusal with its reason
    (the project's rule: an invalid start is kept as history, not silently
    dropped, and never counted as coverage evidence).

    **Order matters and is the point of this function.**  Every REJECTION is
    evaluated before the candidate is CLASSIFIED.  An earlier version classified
    first ("heavy atoms barely moved, so it is a methyl rotor") and returned
    immediately, which accepted two kinds of bad geometry:

    * a hydrogen displaced 100 A (its bond is gone) -- ``heavy_change`` is 0 when
      only H moves, so it looked like a clean methyl rotor;
    * a symmetry-equivalent rotation -- equivalence was only checked after that
      return.

    Refusal reasons, in evaluation order:

    ``malformed_input``            shape/finiteness/composition unusable;
    ``not_a_single_bond_rotor``    the rotated bond is not a registered single
                                   bond (C=O / aromatic) -- a pseudo-torsion;
    ``rigid_transformation``       no pair distance moved: the same structure;
    ``ring_broken``                a covalent bond disappeared (broken ring or
                                   detached atom != conformer);
    ``collision_or_new_bond``      a new covalent contact appeared;
    ``li_coordination_changed``    a Li first shell gained/lost a partner;
    ``mapping_unresolved``         equivalence could not be decided -> fail closed;
    ``equivalent_start``           a topology-preserving proper rotation of the
                                   source or of an already registered start.

    Accepted classes: ``ok_methyl_rotor`` (the heavy skeleton did not move; a
    legitimate independent start on THAT rotor coordinate only) and
    ``ok_heavy_fragment`` (the heavy skeleton moved -- a real fragment torsion).
    """
    xyz_s = np.asarray(source_coords, dtype=float)
    xyz_c = np.asarray(candidate_coords, dtype=float)

    # 0. shape / finiteness / composition
    if (xyz_s.ndim != 2 or xyz_c.ndim != 2 or xyz_s.shape != xyz_c.shape
            or xyz_s.shape[1] != 3
            or len(symbols) != xyz_s.shape[0]
            or len(adjacency) != xyz_s.shape[0]
            or not np.isfinite(xyz_s).all() or not np.isfinite(xyz_c).all()):
        return {"accepted": False, "reason": "malformed_input",
                "detail": {"source_atoms": int(xyz_s.shape[0]) if xyz_s.ndim == 2 else 0,
                           "candidate_atoms": int(xyz_c.shape[0]) if xyz_c.ndim == 2 else 0}}

    before = np.linalg.norm(xyz_s[:, None] - xyz_s[None, :], axis=2)
    after = np.linalg.norm(xyz_c[:, None] - xyz_c[None, :], axis=2)
    change = float(np.max(np.abs(before - after)))
    heavy = [i for i, s in enumerate(symbols) if s != "H"]
    heavy_change = (float(np.max(np.abs(
        before[np.ix_(heavy, heavy)] - after[np.ix_(heavy, heavy)])))
        if len(heavy) > 1 else 0.0)

    # 1. the rotation axis itself must be a registered SINGLE bond
    if rotated_bond is not None:
        axis = tuple(sorted((int(rotated_bond[0]), int(rotated_bond[1]))))
        if axis[0] == axis[1] or axis[1] >= len(symbols):
            return {"accepted": False, "reason": "malformed_input",
                    "detail": {"rotated_bond": list(rotated_bond)}}
        if registered_single_bonds is not None and axis not in registered_single_bonds:
            return {"accepted": False, "reason": "not_a_single_bond_rotor",
                    "detail": {"rotated_bond": list(axis),
                               "note": "C=O / aromatic bonds are not free rotors"}}

    # 2. it must actually move
    if change <= min_pair_change_a:
        return {"accepted": False, "reason": "rigid_transformation",
                "detail": {"pair_distance_change_a": change}}

    # 3. a Li first shell must not change silently -- evaluated BEFORE the covalent
    #    graph, because bond_graph's 1.3x radius cut counts a 2.0 A Li-O contact as
    #    a "bond", so a coordination change would always be reported as
    #    ring_broken and THIS check could never fire (a guard that cannot fire is
    #    worse than none).
    if check_li_shell and any(s == "Li" for s in symbols):
        s_shell = _li_first_shell(symbols, xyz_s)
        c_shell = _li_first_shell(symbols, xyz_c)
        if s_shell != c_shell:
            return {"accepted": False, "reason": "li_coordination_changed",
                    "detail": {"source_shells": {str(k): sorted(v) for k, v in s_shell.items()},
                               "candidate_shells": {str(k): sorted(v) for k, v in c_shell.items()}}}

    # 4. covalent topology must be intact -- BEFORE any classification
    try:
        ref = _edge_set(bond_graph(symbols, xyz_s))
        got = _edge_set(bond_graph(symbols, xyz_c))
    except (ValueError, IndexError):
        return {"accepted": False, "reason": "malformed_input",
                "detail": {"note": "bond graph could not be built"}}
    lost = sorted(ref - got)
    added = sorted(got - ref)
    if lost:
        return {"accepted": False, "reason": "ring_broken",
                "detail": {"pair_distance_change_a": change,
                           "lost_bonds": lost}}
    if added:
        return {"accepted": False, "reason": "collision_or_new_bond",
                "detail": {"pair_distance_change_a": change,
                           "new_bonds": added}}

    # 5. must not be an equivalent copy of the source or of a prior start
    for label, reference in [("source", xyz_s)] + [
            ("prior_start_%d" % i, np.asarray(prior, dtype=float))
            for i, prior in enumerate(prior_starts)]:
        try:
            equivalent = equivalent_start(symbols, reference, xyz_c, adjacency)
        except ValueError:
            # an unresolved mapping is a MISSING decision, not an approval
            return {"accepted": False, "reason": "mapping_unresolved",
                    "detail": {"against": label, "pair_distance_change_a": change}}
        if equivalent:
            return {"accepted": False, "reason": "equivalent_start",
                    "detail": {"pair_distance_change_a": change, "against": label}}

    # 6. only now classify what KIND of independent start this is
    if heavy_change <= min_pair_change_a:
        return {"accepted": True, "reason": "ok_methyl_rotor",
                "detail": {"pair_distance_change_a": change,
                           "heavy_pair_change_a": heavy_change,
                           "probe_class": "methyl_rotor"}}
    return {"accepted": True, "reason": "ok_heavy_fragment",
            "detail": {"pair_distance_change_a": change,
                       "heavy_pair_change_a": heavy_change,
                       "probe_class": "heavy_fragment_torsion"}}


def equivalent_start(symbols, first, second, adjacency):
    """All-atom, topology-preserving proper-rotation duplicate test for starts.

    This 1e-4 A identity tolerance is NOT the production-minimum 0.35 A rule.
    No claim about optimized basins is made before DFT/QC.
    """
    x = np.asarray(first, dtype=float)
    y = np.asarray(second, dtype=float)
    n = len(symbols)
    if (x.shape != (n, 3) or y.shape != (n, 3) or len(adjacency) != n
            or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError("invalid all-atom duplicate input")
    x = x - x.mean(axis=0)
    # The production heavy-atom matcher deliberately prunes terminal-H
    # permutations. That is NOT valid for this all-atom start comparison.
    colours = [(symbols[i], len(adjacency[i]),
                tuple(sorted(symbols[j] for j in adjacency[i]))) for i in range(n)]
    candidates = [[j for j in range(n) if colours[i] == colours[j]] for i in range(n)]
    order = sorted(range(n), key=lambda i: (len(candidates[i]), -len(adjacency[i]), i))
    mapping, used = {}, set()
    nodes = 0

    def search(depth):
        nonlocal nodes
        nodes += 1
        if nodes > 100000:
            raise ValueError("all-atom start mapping unresolved")
        if depth < n:
            i = order[depth]
            for j in candidates[i]:
                if j in used or any((k in adjacency[i]) != (v in adjacency[j])
                                    for k, v in mapping.items()):
                    continue
                mapping[i] = j
                used.add(j)
                if search(depth + 1):
                    return True
                used.remove(j)
                del mapping[i]
            return False
        target = y[[mapping[i] for i in range(n)]]
        target = target - target.mean(axis=0)
        u, _, vt = np.linalg.svd(x.T @ target)
        correction = np.eye(3)
        correction[-1, -1] = 1 if np.linalg.det(u @ vt) >= 0 else -1
        rotation = u @ correction @ vt
        rmsd = float(np.sqrt(np.mean(np.sum((x @ rotation - target) ** 2, axis=1))))
        return rmsd <= 1e-4

    return search(0)


def _repair_member(source_package, member, kept):
    from orca_derivative_policy import require_analytic_gradient, require_frequency_keyword
    source = REPO / member["source_geometry"]
    if _sha(source.read_bytes()) != member["source_sha256"]:
        raise ValueError("registered source geometry hash changed")
    symbols, coords, _ = _read_xyz(source)
    adjacency, singles = _topology_for_member(member["name"], symbols)
    dihedral = tuple(int(v) for v in member["dihedral"].split("-"))
    rotated, audit = rotate_fragment(coords, dihedral, adjacency,
                                     single_bonds=singles, degrees=member["scan_offset_deg"])
    # P0: the SAME gate every candidate start must pass, called HERE so a bad
    # geometry cannot reach the manifest.  It used to be an uncalled helper while
    # this function re-implemented only part of it (no topology check), which
    # accepted a hydrogen displaced 100 A as a clean methyl rotor.
    verdict = validate_candidate_start(
        symbols, coords, rotated, adjacency,
        prior_starts=[p["coords"] for p in kept
                      if (p["member"]["name"], p["member"]["slot"])
                      == (member["name"], member["slot"])],
        registered_single_bonds=singles,
        rotated_bond=(dihedral[1], dihedral[2]))
    if not verdict["accepted"]:
        raise ValueError("candidate start refused: %s %s"
                         % (verdict["reason"], verdict["detail"]))
    audit.update(gate_reason=verdict["reason"])
    audit.update(verdict["detail"])
    old_task = source_package / "tasks" / member["name"] / (member["slot"] + "__" + member["seed"])
    inp = (old_task / "job.inp").read_text(encoding="utf-8")
    require_analytic_gradient(inp, minimum_optimization_tier="verytight")
    require_frequency_keyword(inp)
    geometry = "%d\nfragmentfix %s\n" % (len(symbols), member["member_key"]) + "".join(
        "%-2s %14.9f %14.9f %14.9f\n" % (s, p[0], p[1], p[2])
        for s, p in zip(symbols, rotated))
    audit.update(source_geometry_sha256=member["source_sha256"],
                 previous_probe_sha256=_sha((old_task / "geom.xyz").read_bytes()))
    return {"member": dict(member), "geometry": geometry, "input": inp,
            "audit": audit, "coords": rotated}


def build_repair_package(source_package, output_package, *, batch=2):
    """Immutable new package, limited to the user-approved original batch."""
    source_package, output_package = Path(source_package), Path(output_package)
    if output_package.exists():
        raise ValueError("repair output already exists; refusing overwrite/retry")
    manifest_bytes = (source_package / "manifest.json").read_bytes()
    original = json.loads(manifest_bytes)
    requested = (source_package / ("batch_%d.txt" % batch)).read_text(encoding="utf-8").splitlines()
    lookup = {"tasks/%s/%s__%s" % (m["name"], m["slot"], m["seed"]): m
              for m in original["members"]}
    if not requested or len(set(requested)) != len(requested) or any(p not in lookup for p in requested):
        raise ValueError("original batch list is missing, duplicated or unregistered")
    kept, rejected = [], []
    for path in requested:
        member = lookup[path]
        try:
            kept.append(_repair_member(source_package, member, kept))
        except ValueError as exc:
            rejected.append({"member_key": member["member_key"], "reason": str(exc)})
    output_package.mkdir(parents=True)
    task_lines = []
    for record in kept:
        member = record["member"]
        line = "tasks/%s/%s__%s" % (member["name"], member["slot"], member["seed"])
        task = output_package / line
        task.mkdir(parents=True)
        (task / "geom.xyz").write_text(record["geometry"], encoding="utf-8", newline="\n")
        (task / "job.inp").write_text(record["input"], encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n" % (_sha((task / "geom.xyz").read_bytes()),
                                              _sha((task / "job.inp").read_bytes())),
            encoding="utf-8", newline="\n")
        record["audit"]["repaired_geometry_sha256"] = _sha((task / "geom.xyz").read_bytes())
        task_lines.append(line)
    manifest = {"package": output_package.name, "purpose": "approved batch mapping/fragment repair",
                "source_manifest_sha256": _sha(manifest_bytes), "source_batch": batch,
                "replaces_cancelled_job": "3747724", "requested_tasks": requested,
                "tasks": len(kept), "batches": [], "members": [r["member"] for r in kept],
                "preflight": [r["audit"] for r in kept], "rejected": rejected}
    if kept:
        from import_ensemble_structures import manifest as ens_manifest
        validate_batch_partition(task_lines, [task_lines])
        for name in ("tasks.txt", "batch_1.txt"):
            (output_package / name).write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
        (output_package / "batch_1.sbatch").write_text(
            render_batch_script(ens_manifest._SBATCH, 1, len(kept)), encoding="utf-8", newline="\n")
        manifest["batches"] = [{"batch": 1, "count": len(kept)}]
    (output_package / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8", newline="\n")
    return manifest


def _registry_torsions(name: str, state: str) -> list[dict]:
    rows = []
    with REGISTRY.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("name") == name and r.get("state") == state:
                rows.append(r)
    # collapse duplicates from the registry (one row per dihedral direction)
    seen = set()
    uniq = []
    for r in rows:
        key = tuple(sorted(r["detail"].split(" ")[0].split("-"), key=int))
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq[:MAX_POINTS_PER_STATE]


def _state_geometry(name: str, state: str) -> Path | None:
    """The state's REPRESENTATIVE member geometry.

    A hardcoded ``__primary`` leaf resolves to nothing whenever the state's
    weighted member is a later basin (measured: DOL|LiM_2plus is represented by
    ``c05``), which is the "missing file read as a result" defect this project has
    hit before.  Reuse the registry's resolver -- do not re-implement it -- and
    keep the literal ``primary`` only as a fallback.
    """
    try:
        from build_torsion_registry import _member_geometry, representative_members
        seed = representative_members().get((name, state), "")
        if seed:
            geom = _member_geometry(name, state, seed)
            if geom is not None:
                return geom
    except Exception:
        pass                                    # fall through to the literal leaf
    leaf = "%s__%s__primary" % (name, state)
    cand = REPO / "work" / "hpc_frontier_localization_v1" / "tasks" / leaf / "geom.xyz"
    return cand if cand.is_file() else None


def _build_state(name: str, state: str, charge: int, mult: int) -> list[dict]:
    geom_path = _state_geometry(name, state)
    if geom_path is None:
        print("SKIP %s|%s: no primary geometry" % (name, state))
        return []
    torsions = _registry_torsions(name, state)
    if not torsions:
        print("SKIP %s|%s: no registered torsions" % (name, state))
        return []
    syms, coords, comment = _read_xyz(geom_path)
    members = []
    adjacency, singles = _topology_for_member(name, syms)
    selected = []
    for t in torsions:
        a, b, c, d = (int(x) for x in t["detail"].split(" ")[0].split("-"))
        try:
            rotated, _ = rotate_fragment(coords, (a, b, c, d), adjacency,
                                          single_bonds=singles, degrees=SCAN_OFFSET_DEG)
            verdict = validate_candidate_start(
                syms, coords, rotated, adjacency, prior_starts=selected,
                registered_single_bonds=singles,
                rotated_bond=(b, c))
            if not verdict["accepted"]:
                print("REJECT %s|%s: %s %s" % (name, state, verdict["reason"],
                                               verdict["detail"]))
                continue
        except ValueError as exc:
            print("REJECT %s|%s: %s" % (name, state, exc))
            continue
        selected.append(rotated)
        seed = "tors_%d_%d_%d_%d" % (a, b, c, d)
        task = OUT_PKG / "tasks" / name / ("%s__%s" % (state, seed))
        task.mkdir(parents=True, exist_ok=True)
        xyz = "%d\n%s\n" % (len(syms), seed) + "".join(
            "%-2s %14.9f %14.9f %14.9f\n" % (s, p[0], p[1], p[2])
            for s, p in zip(syms, rotated))
        (task / "geom.xyz").write_text(xyz, encoding="utf-8", newline="\n")
        # frozen production template (the same v1.3 grammar the whole cohort
        # uses).  No %-formatting on the ORCA text: %maxcore/%pal/%scf would
        # be eaten by the format engine (the batch-1 lesson, forever).
        inp = ("! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt "
               "TightSCF SlowConv\n%maxcore 2000\n%pal nprocs 4 end\n"
               "%scf MaxIter 300 end\n* xyzfile "
               + str(charge) + " " + str(mult) + " geom.xyz\n")
        (task / "job.inp").write_text(inp, encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (_sha((task / "geom.xyz").read_bytes()),
               _sha((task / "job.inp").read_bytes())),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "torsion_probe_from_primary_minimum_offset_%d\n" % int(SCAN_OFFSET_DEG),
            encoding="utf-8", newline="\n")
        members.append({
            "member_key": "%s|%s|%s" % (name, state, seed),
            "name": name, "slot": state, "seed": seed,
            "member_role": "recovery_v1_start",
            "source_geometry": str(geom_path.relative_to(REPO)).replace("\\", "/"),
            "source_sha256": _sha(geom_path.read_bytes()),
            "charge": charge, "multiplicity": mult,
            "dihedral": t["detail"].split(" ")[0],
            "scan_offset_deg": SCAN_OFFSET_DEG,
        })
        print("  %s|%s %s (+%.0f deg)" % (name, state, seed, SCAN_OFFSET_DEG))
    return members


def main(argv=None) -> int:
    import sys
    sys.path.insert(0, str(HERE))
    from import_ensemble_structures import manifest as ens_manifest

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repair-original-batch", type=int)
    ap.add_argument("--source-package", type=Path, default=OUT_PKG)
    ap.add_argument("--out-package", type=Path)
    args = ap.parse_args(argv)
    if args.repair_original_batch is not None:
        if args.out_package is None:
            ap.error("repair requires a new --out-package")
        result = build_repair_package(args.source_package, args.out_package, batch=args.repair_original_batch)
        print(json.dumps({"tasks": result["tasks"], "rejected": result["rejected"]}, ensure_ascii=False))
        return 0
    if OUT_PKG.exists():
        raise ValueError("package already exists; preserve submitted inputs and use an explicit repair package")

    all_members = []
    task_lines = []
    for name, state in STATES:
        charge, mult = ens_manifest.SLOT_QM[state]
        ms = _build_state(name, state, charge, mult)
        for m in ms:
            all_members.append(m)
            task_lines.append("tasks/%s/%s__%s" % (name, m["slot"], m["seed"]))
    if not task_lines:
        print("REJECT: nothing packaged")
        return 2
    OUT_PKG.mkdir(parents=True, exist_ok=True)
    (OUT_PKG / "tasks.txt").write_text("\n".join(task_lines) + "\n",
                                       encoding="utf-8", newline="\n")
    # one batch per <=8 tasks (frozen queue discipline)
    n_batches = (len(task_lines) + 7) // 8
    validate_batch_partition(task_lines, [task_lines[i * 8:(i + 1) * 8] for i in range(n_batches)])
    for i in range(n_batches):
        chunk = task_lines[i * 8:(i + 1) * 8]
        (OUT_PKG / ("batch_%d.txt" % (i + 1))).write_text(
            "\n".join(chunk) + "\n", encoding="utf-8", newline="\n")
        (OUT_PKG / ("batch_%d.sbatch" % (i + 1))).write_text(
            render_batch_script(ens_manifest._SBATCH, i + 1, len(chunk)),
            encoding="utf-8", newline="\n")
    (OUT_PKG / "manifest.json").write_text(json.dumps({
        "package": OUT_PKG.name,
        "batches": [{"batch": i + 1,
                     "count": len(task_lines[i * 8:(i + 1) * 8])}
                    for i in range(n_batches)],
        "purpose": "torsion_probe_v1: bounded dihedral scans for 4 limited states",
        "rule": ("one +%.0f-degree rotation about each REGISTERED eligible "
                 "dihedral; full production Opt+AnFreq; zero new basins after "
                 "dedup upgrades the finding to production_torsion_scan_exhausted"
                 % SCAN_OFFSET_DEG),
        "budget_note_core_hours": COST_BASIS_CORE_HOURS * len(task_lines),
        "stop_rule": ("every point runs once; a new basin enters the coverage "
                      "review; no automatic retries"),
        "tasks": len(task_lines), "members": all_members,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("torsion probe package: %s tasks=%d batches=%d" % (
        OUT_PKG.name, len(task_lines), n_batches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
