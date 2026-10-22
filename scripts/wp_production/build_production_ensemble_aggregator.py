#!/usr/bin/env python
"""Production 48-state ensemble aggregator (plan §6.1/§6.2, closure plan v1.4.1).

Reads the QC'd structure ledger (``import_ensemble_structures.py`` output) and
the registered candidate manifest -- never scattered logs.  Per molecule x slot:

* only ``computed`` members enter (latest attempt per logical member; failed /
  pending / superseded attempts never contribute a second weight);
* REAL geometry dedup: primary participates, bond-connectivity signature with
  per-atom mapping, Li donor-set identity, heavy-atom Kabsch RMSD (0.35 A),
  and true four-atom torsion comparison across the +-180 degree seam;
* numerically stable log-sum-exp:
      G_ensemble = G_min - RT ln sum_i [ g_i exp(-(G_i - G_min)/RT) ]
  at the frozen 298.15 K, g_i = 1 unless REGISTERED (never tuned afterwards);
* temperature must be uniform within a state; weights sum to 1 (asserted);
* `partition_sum_relative` (Q relative to G_min) is kept DISTINCT from
  `weight_sum` (the normalized Sigma w_i == 1).

v1.4.1 acceptance semantics -- a label row alone is NOT acceptance:

* ``numerical_status``: available / unavailable  (can a value be computed?)
* ``sampling_status``: pending / in_progress / complete / sampling_limited
  (is the REGISTERED sampling work fully dispositioned?)
* ``acceptance_status``: provisional / accepted / limited / blocked
  (may the value enter downstream formal acceptance?)

A state is ``accepted`` only when every registered candidate has a disposition
(computed, deduplicated, excluded-with-reason, or resolved via a stop rule) and
at least one QC-clean member exists.  While any registered extra is still
pending/rescue-in-flight, the state stays ``provisional`` -- 48 provisional rows
MUST NOT satisfy compliance's 48/48.

Outputs (outputs/physics_completion/ensembles/):
  production_ensemble_weights.csv      member-level Boltzmann weights
  production_ensemble_dedup.csv        dedup decisions (kept vs duplicate-of)
  production_ensemble_labels.csv       48 rows with the three status axes
  production_ensemble_index.json       input hashes, stale flag, read-only check
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import numpy as np                                    # noqa: E402
import yaml

import run_batch as rb                                # noqa: E402
import build_production_ensemble_manifest as manifest  # noqa: E402
sys.path.insert(0, str(REPO / "scripts"))
from build_li_motifs import kabsch_rmsd              # noqa: E402

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
STRUCTURES = ENS / "production_ensemble_structures.csv"
CANDIDATES = ENS / "production_ensemble_candidates.csv"
DISPOSITIONS = ENS / 'production_ensemble_dispositions.csv'
OUT = ENS
SLOTS = ("M", "M_plus", "LiM_plus", "LiM_2plus")
MAIN_MOLECULES = 12
TEMP_K = 298.15
R_KCAL = 1.98720425864083e-3          # kcal/(mol K), CODATA
DUP_RMSD_A = 0.35
TORSION_TOL_DEG = 10.0
HARTREE_TO_KCAL = 627.509474
MAPPING_NODE_BUDGET = 100000
ALGORITHM_VERSION = "1.4.2"


def expected_state_keys():
    cfg = yaml.safe_load((REPO / "config/physics_completion_v1.yaml").read_text(encoding="utf-8"))
    return {(rb.MOL_LOOKUP[mid][1], slot): mid
            for mid in cfg["analysis_cohorts"]["main"] for slot in SLOTS}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_xyz_bytes(data: bytes):
    lines = data.decode("utf-8", errors="replace").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for line in lines[2:2 + n]:
        p = line.split()
        syms.append(p[0])
        coords.append((float(p[1]), float(p[2]), float(p[3])))
    return syms, coords


def bond_adjacency(syms, coords):
    """Project convention: 1.3x covalent radii (run_batch.RADII) -> adjacency."""
    n = len(syms)
    adj = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            cut = 1.3 * (rb.RADII.get(syms[i], 0.8) + rb.RADII.get(syms[j], 0.8))
            if rb.dist(coords[i], coords[j]) <= cut:
                adj[i].add(j)
                adj[j].add(i)
    return adj


def canonical_bond_signature(syms, coords):
    """Fragment composition PLUS the sorted multiset of element-pair bonds.

    Distinguishes same-composition different-connectivity isomers that the
    fragment-composition-only signature could not (v1.4.1 §3.1.3).
    """
    adj = bond_adjacency(syms, coords)
    parent = list(range(len(syms)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    bonds = []
    for i in range(len(syms)):
        for j in adj[i]:
            if i < j:
                bonds.append(tuple(sorted((syms[i], syms[j]))))
    for i in range(len(syms)):
        for j in adj[i]:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj
    frags = {}
    for i in range(len(syms)):
        frags.setdefault(find(i), []).append(syms[i])
    composition = tuple(sorted(tuple(sorted(v)) for v in frags.values()))
    return composition, tuple(sorted(bonds))


def _refine_partition(syms, adj, partition):
    """Weisfeiler-Lehman colour refinement: split classes by neighbour colours."""
    changed = True
    while changed:
        changed = False
        index = {}
        for k, cls in enumerate(partition):
            for i in cls:
                index[i] = k
        new_partition = []
        for cls in partition:
            buckets = {}
            for i in cls:
                key = (syms[i], len(adj[i]), tuple(sorted(index[j] for j in adj[i])))
                buckets.setdefault(key, []).append(i)
            new_partition.extend(buckets.values())
            if len(buckets) > 1:
                changed = True
        partition = new_partition
    return partition


def find_topology_mappings(syms_a, adj_a, syms_b, adj_b, limit=None, *, stats=None):
    """All element- and bond-preserving atom mappings a->b, up to ``limit``.

    Two structures are the SAME chemical species iff such a mapping exists; two
    conformers are the same minimum iff SOME mapping makes their heavy-atom
    geometry coincide (RMSD) AND their torsions agree.  Mapping by element order
    alone (the previous approach) silently misses relabelled-but-identical
    structures and can also pair non-equivalent atoms of the same element.

    Returns (mappings, resolved); resolved=False means the search hit ``limit``
    and the caller must mark ``mapping_unresolved`` -- never 'unique'.
    """
    n = len(syms_a)
    if n != len(syms_b) or sorted(syms_a) != sorted(syms_b):
        return [], True
    stats = stats if stats is not None else {}
    stats.update(nodes=0, exhaustive=True)
    deg_a = [len(a) for a in adj_a]
    deg_b = [len(b) for b in adj_b]
    if sorted(deg_a) != sorted(deg_b):
        return [], True

    # Joint colour refinement gives directly comparable colours across graphs.
    colours = [(s, len(a)) for s, a in zip(syms_a + syms_b, adj_a + adj_b)]
    combined = adj_a + [{n + j for j in x} for x in adj_b]
    for _ in range(n):
        keys = [(colours[i], tuple(sorted(colours[j] for j in combined[i])))
                for i in range(2 * n)]
        palette = {key: k for k, key in enumerate(sorted(set(keys)))}
        new = [palette[key] for key in keys]
        if new == colours:
            break
        colours = new
    cand = {}
    for i in range(n):
        cand[i] = [j for j in range(n)
                   if syms_a[i] == syms_b[j] and colours[i] == colours[n + j]]
    order = sorted(range(n), key=lambda i: (syms_a[i] == "H", len(cand[i]), -deg_a[i], i))

    mappings, assignment = [], {}

    def consistent(i, j):
        for a, b in assignment.items():
            if (a in adj_a[i]) != (b in adj_b[j]):
                return False
        return True

    def backtrack(k):
        if stats["nodes"] >= MAPPING_NODE_BUDGET or (limit is not None and len(mappings) >= limit):
            stats["exhaustive"] = False
            return
        if k == len(order):
            mappings.append(dict(assignment))
            return
        i = order[k]
        used = set(assignment.values())
        for j in cand[i]:
            # Terminal H permutations cannot change heavy RMSD, heavy torsions
            # or donor identity. Keep one deterministic representative per
            # equivalent neighbour set; non-terminal H remain fully searched.
            if syms_a[i] == "H" and deg_a[i] == 1:
                equivalents = [k for k in cand[i] if k not in used and adj_b[k] == adj_b[j]]
                if equivalents and j != min(equivalents):
                    continue
            if j in used or not consistent(i, j):
                continue
            if stats["nodes"] >= MAPPING_NODE_BUDGET:
                stats["exhaustive"] = False
                return
            stats["nodes"] += 1
            assignment[i] = j
            backtrack(k + 1)
            del assignment[i]
            if not stats["exhaustive"]:
                return

    backtrack(0)
    return mappings, stats["exhaustive"]


def mapped_heavy_array(syms_a, coords_a, mapping, coords_b):
    """Heavy-atom coords of A expressed in B's atom order via the mapping."""
    return np.array([coords_b[mapping[i]] for i, s in enumerate(syms_a) if s != "H"])


def heavy_array(syms, coords):
    return np.array([c for s, c in zip(syms, coords) if s != "H"])


def mapped_torsion_worst(syms_a, coords_a, coords_b, mapping, rot):
    """Worst torsion delta (deg) over rotatable bonds, under the mapping."""
    worst = 0.0
    for (a, b, na, nb) in rot:
        if any(x not in mapping for x in (a, b, na, nb)):
            continue
        t_a = torsion_deg(coords_a[na], coords_a[a], coords_a[b], coords_a[nb])
        t_b = torsion_deg(coords_b[mapping[na]], coords_b[mapping[a]],
                          coords_b[mapping[b]], coords_b[mapping[nb]])
        worst = max(worst, torsion_delta(t_a, t_b))
    return worst


def mapped_donor_sites(syms, coords, mapping, coords_b, syms_b=None):
    """Li donor SITES compared under the mapping (identity, not just counts)."""
    if "Li" not in syms:
        return None, None
    syms_b = syms_b or [syms[next(i for i, j in mapping.items() if j == k)]
                        for k in range(len(syms))]
    a, b = [], []
    for li, element in enumerate(syms):
        if element != "Li":
            continue
        a.extend((mapping[li], mapping[i]) for i, s in enumerate(syms)
                 if s in ("O", "N") and rb.dist(coords[i], coords[li]) <= 3.0)
        b.extend((mapping[li], j) for j, s in enumerate(syms_b)
                 if s in ("O", "N") and rb.dist(coords_b[j], coords_b[mapping[li]]) <= 3.0)
    return tuple(sorted(a)), tuple(sorted(b))


def li_donor_set(syms, coords):
    """Identity of the donors contacting Li (not just the count)."""
    if "Li" not in syms:
        return None
    li = syms.index("Li")
    donors = []
    for i, s in enumerate(syms):
        if s in ("O", "N") and rb.dist(coords[i], coords[li]) <= 3.0:
            donors.append(s)
    return tuple(sorted(donors))


def torsion_deg(p1, p2, p3, p4):
    """True four-atom dihedral in degrees via the standard projection formula."""
    b1 = np.array(p2) - np.array(p1)
    b2 = np.array(p3) - np.array(p2)
    b3 = np.array(p4) - np.array(p3)
    n1 = np.cross(b1, b2)
    n2 = np.cross(b2, b3)
    m = np.cross(n1, b2 / np.linalg.norm(b2))
    x = float(np.dot(n1, n2))
    y = float(np.dot(m, n2))
    return math.degrees(math.atan2(y, x))


def torsion_delta(a_deg, b_deg):
    """Periodic torsion difference in [0, 180]."""
    return abs((a_deg - b_deg + 180.0) % 360.0 - 180.0)


def find_rotatable_bonds(syms, coords):
    """Indices of rotatable heavy-atom bonds: heavy-heavy, >=2 heavy neighbors
    on each side, NOT in a small ring (rings are rigid; EC/PC/DOL etc. have
    none by construction).  Returns list of (i, j, neighbor_a, neighbor_b)."""
    adj = bond_adjacency(syms, coords)
    n = len(syms)
    # ring detection via BFS depth <=6
    def in_ring(a, b):
        seen = {a}
        frontier = [a]
        for _ in range(5):
            nxt = []
            for x in frontier:
                for y in adj[x]:
                    if (x, y) in ((a, b), (b, a)):
                        continue
                    if y == b:
                        return True
                    if y not in seen:
                        seen.add(y)
                        nxt.append(y)
            frontier = nxt
        return False

    rotatable = []
    heavy = [i for i in range(n) if syms[i] != "H"]
    for i in heavy:
        for j in adj[i]:
            if i >= j or syms[j] == "H":
                continue
            if in_ring(i, j):
                continue
            ia = sorted(k for k in adj[i] if k != j and syms[k] != "H")
            jb = sorted(k for k in adj[j] if k != i and syms[k] != "H")
            if ia and jb:
                rotatable.append((i, j, ia[0], jb[0]))
    return rotatable


def member_geometry(row: dict, repo: Path):
    """Final geometry of a member: run/job.xyz for extras, the frozen *_opt.xyz
    for primaries.  Returns (syms, coords) or None (dedup_blocked then)."""
    def checked(path):
        digest = row.get("final_geometry_sha256", "")
        if not digest or sha256_file(path) != digest:
            return None
        data = read_xyz_bytes(path.read_bytes())
        if not data[0] or not np.isfinite(np.asarray(data[1])).all():
            return None
        return data
    if row["member_role"] == "primary":
        state = "M_tzvpd" if row["slot"] == "M" else row["slot"]
        leg = repo / "work" / "wp2prod" / row["name"] / state
        for name in (f"{row['name']}_{state}_opt.xyz", f"{row['name']}_{state}.xyz"):
            p = leg / name
            if p.is_file():
                return checked(p)
    else:
        p = geometry_path(row, repo)
        if not p.is_file():
            p = repo / row["task_relpath"] / "run" / "job.xyz"
        if p.is_file():
            return checked(p)
        log = repo / row["log_path"] if row.get("log_path") else None
        if log and log.is_file() and row.get("log_sha256") == sha256_file(log):
            # Fall back to the log's final ANGSTROEM block (frame-consistent
            # with what the frequencies were computed on).
            from import_ensemble_structures import last_geometry
            text = log.read_text(encoding="utf-8", errors="replace")
            syms, coords = last_geometry(text)
            # A log alone cannot substantiate the registered XYZ byte hash.
            # Importer must materialise and register the canonical geometry.
    return None


def geometry_path(row, repo):
    if row['member_role'] == 'primary':
        state = 'M_tzvpd' if row['slot'] == 'M' else row['slot']
        return repo / 'work/wp2prod' / row['name'] / state / f"{row['name']}_{state}_opt.xyz"
    if row.get('log_path'):
        return (repo / row['log_path']).parent / 'job.xyz'
    return repo / row['task_relpath'] / 'run' / 'job.xyz'


def geometry_source_hashes(rows, repo):
    hashes = {}
    for row in rows:
        if row.get("status") not in ("computed", "ready"):
            continue
        path = geometry_path(row, repo)
        hashes[path.relative_to(repo).as_posix()] = sha256_file(path) if path.is_file() else "MISSING"
    return hashes


def boltzmann(g_kcal: list, temp_k: float, degeneracies=None):
    """Stable G_ensemble via log-sum-exp; normalized weights sum to 1."""
    if not g_kcal or not all(math.isfinite(g) for g in g_kcal):
        raise ValueError("finite nonempty energies required")
    if not math.isfinite(temp_k) or temp_k <= 0:
        raise ValueError("positive finite temperature required")
    if degeneracies and any(v != 1 for v in degeneracies.values()):
        raise ValueError("frozen degeneracy g_i=1 required")
    gmin = min(g_kcal)
    rel = [math.exp(-(g - gmin) / (R_KCAL * temp_k)) * ((degeneracies or {}).get(i, 1))
           for i, g in enumerate(g_kcal)]
    q_total = sum(rel)                     # partition sum relative to exp(-G_min/RT)
    weights = [w / q_total for w in rel]   # normalized: sum == 1
    g_ens = gmin - R_KCAL * temp_k * math.log(q_total)
    tolerance = max(1e-10, 8 * math.ulp(gmin))
    if not (abs(sum(weights) - 1) <= 1e-12 and
            -tolerance <= gmin - g_ens <= R_KCAL * temp_k * math.log(len(g_kcal)) + tolerance):
        raise ValueError("ensemble normalization / RT ln N invariant failed")
    return g_ens, weights, q_total


def dedup_members(members, repo: Path, pair_sink=None):
    """REAL geometry dedup over the FULL member set (primary included).

    Gate order per v1.4.1 §3.1: fragment composition + bond signature ->
    Li donor identity/denticity -> heavy-atom Kabsch RMSD -> torsions.
    Representative = lowest G, tie-broken by stable member key (reproducible).
    Missing geometry => dedup_blocked (never silently 'unique') -- but a
    SINGLE-member set cannot contain duplicates, so geometry is only required
    when at least two members are in the pool.
    """
    # Load geometries and topology.
    prepared = []
    for m in members:
        geom = member_geometry(m, repo)
        if geom is None:
            prepared.append((m, None, None))
            continue
        syms, coords = geom
        adj = bond_adjacency(syms, coords)
        prepared.append((m, (syms, coords), adj))

    kept, decisions = [], []
    # Deterministic order: G ascending, then member_key (reproducible rule).
    order = sorted(range(len(prepared)),
                    key=lambda i: (float(prepared[i][0]["g_single_eh"] or "0"),
                                   prepared[i][0]["member_key"]))
    for i in order:
        m, geom, adj = prepared[i]
        if geom is None:
            decisions.append({"member_key": m["member_key"],
                              "attempt": m.get("attempt", "0"),
                              "kept": "false", "duplicate_of": "",
                              "reason": "dedup_blocked: no final geometry",
                              "mapping": "", "rmsd_a": "", "torsion_delta_deg": "",
                              "rotation_det": ""})
            continue
        duplicate_of, why = "", "unique"
        evidence = {"mapping": "", "rmsd_a": "", "torsion_delta_deg": "",
                    "rotation_det": ""}
        for j in kept:
            w, wgeom, wadj = prepared[j]
            # 1. TOPOLOGY: an element- AND bond-preserving mapping must exist.
            search_stats = {}
            mappings, resolved = find_topology_mappings(geom[0], adj, wgeom[0], wadj,
                                                        stats=search_stats)
            if not mappings and resolved:
                if pair_sink is not None:
                    pair_sink.append(dict(member_key=m['member_key'], reference_key=w['member_key'],
                                          member_geometry_sha256=m.get('final_geometry_sha256', ''),
                                          reference_geometry_sha256=w.get('final_geometry_sha256', ''),
                                          mapping='', rmsd_a='', torsion_delta_deg='', rotation_det='',
                                          search_nodes=str(search_stats.get('nodes', 0)),
                                          search_exhaustive='true', verdict='different_topology'))
                continue        # different species/connectivity: not a duplicate
            # 2. Under each legal mapping, require RMSD AND torsions together.
            best = None
            rot = find_rotatable_bonds(geom[0], geom[1])
            for mapping in mappings:
                heavy = mapped_heavy_array(geom[0], geom[1], mapping, wgeom[1])
                ref = heavy_array(geom[0], geom[1])
                if heavy.shape != ref.shape:
                    continue
                rmsd = kabsch_rmsd(heavy, ref)
                if rmsd >= DUP_RMSD_A:
                    continue
                tdelta = mapped_torsion_worst(geom[0], geom[1], wgeom[1], mapping, rot)
                if tdelta > TORSION_TOL_DEG:
                    continue
                # Li donor sites under the same mapping (identity, not counts).
                donors_a, donors_b = mapped_donor_sites(geom[0], geom[1], mapping, wgeom[1], wgeom[0])
                if donors_a is not None and donors_b is not None and donors_a != donors_b:
                    continue
                # Proper rotation only: reject mirror fits (det must be +1).
                det = 1.0  # kabsch_rmsd uses an explicitly proper rotation.
                if reflection_preferred(heavy, ref, rmsd):
                    continue
                if not mapped_chirality_matches(geom[0], geom[1], wgeom[1], mapping, adj):
                    continue
                if best is None or rmsd < best[0]:
                    best = (rmsd, tdelta, mapping, det)
            if best is not None:
                rmsd, tdelta, mapping, det = best
                duplicate_of = w["member_key"]
                why = "same minimum: topology mapping + rmsd %.3f A + torsion %.1f deg" % (
                    rmsd, tdelta)
                evidence = {"mapping": " ".join("%d->%d" % (a, b) for a, b in sorted(mapping.items())),
                            "rmsd_a": "%.4f" % rmsd,
                            "torsion_delta_deg": "%.2f" % tdelta,
                            "rotation_det": "%.6f" % det}
                if pair_sink is not None:
                    pair_sink.append(dict(member_key=m['member_key'], reference_key=w['member_key'],
                                          member_geometry_sha256=m.get('final_geometry_sha256', ''),
                                          reference_geometry_sha256=w.get('final_geometry_sha256', ''),
                                          **evidence, search_nodes=str(search_stats.get('nodes', 0)),
                                          search_exhaustive=str(resolved).lower(), verdict='same_minimum'))
                break
            if not resolved:
                why = "mapping_unresolved: mapping search exhausted budget"
                evidence["mapping"] = "unresolved"
                verdict = 'mapping_unresolved'
            else:
                verdict = 'different_geometry_or_coordination'
            if pair_sink is not None:
                pair_sink.append(dict(member_key=m['member_key'], reference_key=w['member_key'],
                                      member_geometry_sha256=m.get('final_geometry_sha256', ''),
                                      reference_geometry_sha256=w.get('final_geometry_sha256', ''),
                                      **evidence, search_nodes=str(search_stats.get('nodes', 0)),
                                      search_exhaustive=str(resolved).lower(), verdict=verdict))
            if not resolved:
                break
        entry_decision = {"member_key": m["member_key"],
                          "attempt": m.get("attempt", "0"),
                          "kept": "false" if duplicate_of or why.startswith("mapping_unresolved") else "true",
                          "duplicate_of": duplicate_of, "reason": why}
        entry_decision.update(evidence)
        decisions.append(entry_decision)
        if not duplicate_of and not why.startswith("mapping_unresolved"):
            kept.append(i)
    return [prepared[i][0] for i in kept], decisions


def mapped_chirality_matches(syms, coords_a, coords_b, mapping, adj):
    """Reject inversion at nonplanar heavy-atom centres; planar centres are safe."""
    import itertools
    for centre, neighbours in enumerate(adj):
        heavy = sorted(i for i in neighbours if syms[i] != "H")
        for triple in itertools.combinations(heavy, 3):
            a = np.array([np.array(coords_a[i]) - coords_a[centre] for i in triple])
            b = np.array([np.array(coords_b[mapping[i]]) - coords_b[mapping[centre]] for i in triple])
            va, vb = np.linalg.det(a), np.linalg.det(b)
            if abs(va) > 1e-8 and abs(vb) > 1e-8 and va * vb < 0:
                return False
    return True


def _kabsch_det(first, second):
    """Sign of the optimal superposition: +1 proper rotation, -1 mirror.

    The determinant must be taken from the RAW SVD product (U @ Vt).  Building
    the corrected matrix with a forced sign would always return +1 and would
    silently let mirror images pass as the same minimum.
    """
    a = first - first.mean(axis=0)
    b = second - second.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    return float(np.linalg.det(u @ vt))


def reflection_preferred(first, second, proper_rmsd):
    """Reject an actually better improper 3D fit, not a rank-deficient SVD sign.

    Planar/linear fits have no well-defined normal orientation. For full-rank
    geometry, a better reflected fit is conservative evidence against merging;
    the frozen proper-rotation RMSD cutoff alone would merge shallow mirrors.
    """
    a = first - first.mean(axis=0)
    b = second - second.mean(axis=0)
    u, singular, vt = np.linalg.svd(a.T @ b)
    if singular[0] == 0 or singular[-1] <= singular[0] * 1e-8:
        return False
    rotation = u @ vt
    if np.linalg.det(rotation) >= 0:
        return False
    reflected = float(np.sqrt(np.mean(np.sum((a @ rotation - b) ** 2, axis=1))))
    return reflected + 1e-8 < proper_rmsd


def load_candidates():
    """Registered logical members per (name, slot) from the manifest."""
    regs = {}
    if not CANDIDATES.is_file():
        raise ValueError("registered candidate manifest missing")
    for r in csv.DictReader(CANDIDATES.open(encoding="utf-8")):
        # round1_extra  = the original round-1 extras (and their rescues)
        # recovery_v1_start = a NEW independent minimum from the 2026-10-21
        #   strict_recovery_v1 batch.  It is a first-class member: it counts
        #   toward the state's acceptance AND toward the 3->6 ceiling
        #   extension.  (Contrast round2_audit_extra, which is ceiling-only.)
        if r["member_role"] in ("round1_extra", "recovery_v1_start"):
            regs.setdefault((r["name"], r["slot"]), []).append(r)
    return regs


COVERAGE_REVIEWS = (REPO / "outputs" / "physics_completion" / "recovery"
                    / "coverage_reviews.csv")


def acceptance_decision(*, unresolved: int, n_limited: int, cov, kept_keys) -> tuple:
    """(acceptance_status, sampling_status, cov_resolved, cov_id).

    Pure function so the coverage-review mechanism is unit-testable without
    building a whole ledger.  Semantics (2026-10-21 strict-recovery ruling):

    * any unresolved work            -> provisional (nothing else matters);
    * n_limited without a *resolved* -> limited (history keeps its counts);
    * n_limited WITH resolved review -> accepted, but ONLY when the review's
      evidence checks out against the kept pool (anti-cheat).  The evidence
      shape depends on the route:

      - ``multi_basin_coverage``: the claimed NEW minima must themselves be in
        the kept pool (they survived dedup);
      - ``single_basin_verified``: the claimed members are independent
        REPRODUCTIONS of known minima, so they are exactly the rows dedup
        excluded; the check falls to ``kept_pool_evidence``, the dedup targets
        they reproduced (a reproduction of a non-kept structure certifies
        nothing).

    In both cases the review hands us kept-pool member keys, so the check stays
    a single set-membership test.
    """
    cov_resolved = False
    cov_id = ""
    if cov and cov.get("verdict") == "resolved" and not unresolved:
        # whichever column carries the review's evidence, the anti-cheat is the
        # same: every claimed member must be in the kept pool.  The C-group
        # multi-basin route names its members in kept_pool_evidence (they may
        # come from earlier batches, so computed_new_members is empty).
        claimed = ([m for m in (cov.get("computed_new_members") or "").split(";") if m]
                   or [m for m in (cov.get("kept_pool_evidence") or "").split(";") if m])
        cov_resolved = bool(claimed) and all(c in kept_keys for c in claimed)
        cov_id = cov.get("review_id", "") if cov_resolved else ""
    if unresolved:
        return "provisional", "in_progress", False, ""
    if n_limited and not cov_resolved:
        return "limited", "sampling_limited", False, ""
    return "accepted", "complete", cov_resolved, cov_id


def load_coverage_reviews():
    """Coverage reviews (2026-10-21 strict-recovery ruling).

    The ONLY sanctioned path from `limited` to `accepted`: a review that
    certifies the historical gap is covered by a NEW independent minimum.
    History keeps its counts -- we never clear n_limited.
    """
    out = {}
    if not COVERAGE_REVIEWS.is_file():
        return out
    import csv as _csv
    with COVERAGE_REVIEWS.open(encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            out[(row.get("name"), row.get("state"))] = row
    return out


def load_dispositions():
    if not DISPOSITIONS.is_file():
        return {}
    rows = list(csv.DictReader(DISPOSITIONS.open(encoding='utf-8', newline='')))
    if len({r.get('member_key') for r in rows}) != len(rows):
        raise ValueError('duplicate member disposition')
    return {r['member_key']: r for r in rows}


def latest_attempt_per_member(rows):
    """One row per logical extra member: the latest attempt (by attempt no.),
    superseded evidence never contributes a second weight."""
    best = {}
    for r in rows:
        # EVERY first-class member role must be listed here.  A missing role is
        # not a cosmetic omission: the member then never enters `latest`, the
        # aggregator reads it as "registered but no result yet" (n_pending) and
        # the state can never leave `limited` -- recovery_v1_start was missing
        # exactly so, which silently blocked the whole acceptance path.
        if r["member_role"] not in ("round1_extra", "recovery_v1_start"):
            continue
        key = r["member_key"]
        cur = best.get(key)
        if cur is None or int(r["attempt"] or 0) > int(cur["attempt"] or 0):
            best[key] = r
    return best


def validate_pool(pool) -> None:
    """Same-state member consistency (v1.4.1 §3.2).

    A state's ensemble may only combine members that share the frozen state
    definition: method+basis, charge/multiplicity, temperature, protocol
    version and frequency method.  A mismatch means the members describe
    DIFFERENT physical states -- mixing them would silently average unrelated
    quantities, so this is a hard reject (ValueError), never a warning.
    """
    if not pool:
        return
    for row in pool:
        for field in ('slot', 'charge', 'multiplicity', 'method', 'protocol_version', 'frequency_hessian', 'qrrho'):
            if not str(row.get(field, '')).strip():
                raise ValueError(f'missing {field}')
        qm = manifest.SLOT_QM.get(row.get('slot'))
        if qm is None or (str(row.get('charge')), str(row.get('multiplicity'))) != tuple(map(str, qm)):
            raise ValueError('frozen slot charge/multiplicity mismatch')
        method = ' '.join(str(row.get('method', '')).replace('SMD(acetonitrile)', '').split())
        if method != 'wB97X-D4 def2-TZVPD':
            raise ValueError('frozen method/basis mismatch')
        if row.get('protocol_version') != '1.3' or row.get('frequency_hessian') != 'analytical_hessian':
            raise ValueError('frozen AnFreq protocol mismatch')
        if str(row.get('qrrho', '')).lower() != 'true':
            raise ValueError('frozen qRRHO required')
    for row in pool:
        for field in ("method", "protocol_version", "charge", "multiplicity", "temp_k",
                      "frequency_hessian", "qrrho", "g_single_eh"):
            if not str(row.get(field, "")).strip():
                raise ValueError(f"missing {field}: {row.get('member_key')}")
        if not math.isfinite(float(row["g_single_eh"])):
            raise ValueError("finite G required")
        if float(row["temp_k"]) != TEMP_K:
            raise ValueError("temperature differs from frozen 298.15 K")
        if float(row.get("degeneracy") or 1) != 1:
            raise ValueError("frozen g_i=1 required")
    def distinct(field):
        return {str(m.get(field, "")).strip() for m in pool}
    for field, label in (("protocol_version", "protocol_version"),
                         ("charge", "charge"),
                         ("multiplicity", "multiplicity"),
                         ("temp_k", "temperature"),
                         ("qrrho", "qrrho"),
                         ("frequency_hessian", "frequency_hessian")):
        values = distinct(field) - {""}
        if len(values) > 1:
            raise ValueError("mixed %s across members: %s" % (label, sorted(values)))
    methods = distinct("method") - {""}
    # The method string is recorded in two equivalent spellings: production legs
    # store "wB97X-D4 def2-TZVPD" (solvent is implied by the frozen protocol and
    # carried in the level field), while ensemble extras carry the explicit
    # "... SMD(acetonitrile)".  Normalise the solvent suffix away before
    # comparing, otherwise every state would look like a method mismatch.
    def normalise(text):
        return " ".join(text.replace("SMD(acetonitrile)", "").split()).strip()
    normalised = {normalise(m) for m in methods}
    if len(normalised) > 1:
        raise ValueError("mixed method/basis across members: %s" % sorted(methods))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY check: recompute in memory, compare to disk, "
                         "never write (v1.4.1 §3.5)")
    args = ap.parse_args(argv)

    if not STRUCTURES.is_file():
        print("REJECT: structure ledger missing; run import_ensemble_structures first")
        return 2
    ledger_bytes = STRUCTURES.read_bytes()
    rows = list(csv.DictReader(io.StringIO(ledger_bytes.decode("utf-8"))))

    computed_primary = {}
    for r in rows:
        if r["member_role"] == "primary" and r["status"] == "ready":
            if (r["name"], r["slot"]) in computed_primary:
                print("REJECT: duplicate primary key")
                return 2
            computed_primary[(r["name"], r["slot"])] = r
    try:
        expected = expected_state_keys()
        if set(computed_primary) != set(expected) or any(
                r["mol_id"] != expected[k] for k, r in computed_primary.items()):
            raise ValueError("primary cohort keys/identities differ from frozen main cohort")
    except (ValueError, KeyError, OSError) as exc:
        print(f"REJECT: {exc}")
        return 2
    latest = latest_attempt_per_member(rows)
    try:
        registered = load_candidates()
        dispositions = load_dispositions()
        coverage = load_coverage_reviews()
    except ValueError as exc:
        print(f"REJECT: {exc}")
        return 2

    weight_rows, dedup_rows, label_rows, pair_rows = [], [], [], []
    for slot in SLOTS:
        for (name, s), primary in sorted(computed_primary.items()):
            if s != slot:
                continue
            reg = registered.get((name, slot), [])
            members = [dict(primary)]
            n_pending = n_failed = n_rescue = n_limited = n_drift = 0
            extras_pool = []
            for r in reg:
                mem = latest.get("%s|%s|%s" % (r["name"], r["slot"], r["seed"]))
                if mem is None:
                    n_pending += 1          # registered, no result yet
                    continue
                st = mem["status"]
                if st == "computed":
                    extras_pool.append(mem)
                elif st == "pending":
                    n_pending += 1
                elif st == "superseded":
                    n_pending += 1          # superseded attempts still have a live
                                            # successor in flight: treat as pending
                elif st == "technical_complete_qc_failed":
                    d = dispositions.get(mem['member_key'], {})
                    # v3.0 discipline: species drift is TERMINAL from the first
                    # attempt -- the >=2 budget gate exists only for
                    # rescue_budget_exhausted (a budget needs two real
                    # calculations to be "exhausted").  A drift verdict never
                    # recovers by retrying, so it must not linger as
                    # "rescue in flight" (D7 review: the follow-up queue is
                    # empty; n_rescue was a factual misstatement).
                    _drift_final = (d.get('disposition') == 'species_drift_unrecoverable'
                                    and d.get('latest_attempt') == mem.get('attempt')
                                    and d.get('log_sha256') == mem.get('log_sha256')
                                    and d.get('failure_class') == mem.get('failure_class'))
                    _budget_final = (d.get('disposition') == 'rescue_budget_exhausted'
                                     and d.get('latest_attempt') == mem.get('attempt')
                                     and d.get('log_sha256') == mem.get('log_sha256')
                                     and d.get('failure_class') == mem.get('failure_class')
                                     and int(d.get('attempted_calculations') or 0) >= 2)
                    if _drift_final or _budget_final:
                        n_limited += 1
                        if d.get('disposition') == 'species_drift_unrecoverable':
                            n_drift += 1
                        continue
                    fc = mem.get("failure_class", "")
                    if fc in ("strict_reopt_required", "verytight_convergence",
                              "max_cycles_exhausted"):
                        n_rescue += 1       # has a registered remedy in flight
                    else:
                        n_failed += 1       # science-level failure (imag etc.)
                else:
                    n_failed += 1
            n_registered = len(reg)

            pool = members + extras_pool
            try:
                validate_pool(pool)
            except ValueError as exc:
                print(f"REJECT {name}/{slot}: {exc}")
                return 2
            kept, decisions = dedup_members(pool, REPO, pair_rows)
            dedup_rows.extend(decisions)
            # primary is members[0]; kept preserves its identity when unique.
            n_dedup = sum(bool(d.get("duplicate_of")) for d in decisions)
            n_geometry_blocked = sum(d["kept"] == "false" and not d.get("duplicate_of") for d in decisions)

            g_vals, temps = [], []
            ok = True
            for m in kept:
                g = m.get("g_single_eh")
                t = m.get("temp_k")
                if not g or not t:
                    ok = False
                    break
                g_vals.append(float(g) * HARTREE_TO_KCAL)
                temps.append(float(t))
            if not ok or not g_vals or n_geometry_blocked:
                label_rows.append({
                    "mol_id": primary["mol_id"], "name": name, "state": slot,
                    "numerical_status": "unavailable",
                    "sampling_status": "pending" if (n_pending + n_rescue) else "complete",
                    "acceptance_status": "blocked",
                    "n_registered": str(n_registered), "n_pending": str(n_pending),
                    "n_qc_passed": str(len(kept)), "n_qc_failed": str(n_failed + n_limited),
                    "n_deduplicated": str(n_dedup), "n_unique": str(len(kept)),
                    "n_unresolved": str(n_pending + n_rescue + n_geometry_blocked),
                    "n_members": "0", "pool_limited": "", "limitation_reason": "",
                    "g_min_kcal": "", "g_ensemble_kcal": "", "g_ensemble_eh": "",
                    "partition_sum_relative": "", "weight_sum": "",
                    "temp_k": "", "protocol": primary.get("method", ""),
                    "protocol_version": "1.3",
                })
                continue
            temps_set = set(temps)
            if len(temps_set) > 1:
                print(f"REJECT {name}/{slot}: mixed temperatures {sorted(temps_set)}")
                return 2
            g_ens, weights, q_total = boltzmann(g_vals, temps[0])
            g_ens_eh = g_ens / HARTREE_TO_KCAL
            for m, w, g in zip(kept, weights, g_vals):
                weight_rows.append({
                    "member_key": m["member_key"],
                    "attempt": m.get("attempt", "0") if m["member_role"] != "primary" else "primary",
                    "mol_id": m["mol_id"], "name": m["name"], "slot": m["slot"],
                    "g_single_kcal": "%.6f" % g, "boltzmann_weight": "%.9f" % w,
                    "temp_k": "%.2f" % temps[0], "degeneracy": m.get("degeneracy", "1"),
                })

            # v1.4.1 §3.4: only genuinely UNDISPOSITIONED work keeps a state
            # provisional.  A QC-failed extra (imaginary modes, connectivity
            # change, ...) is a COMPLETE disposition -- the state may be
            # accepted with its remaining members.  Geometry-blocked members
            # (missing final geometry) are NOT dispositioned: we cannot prove
            # they are unique, so they block acceptance.
            unresolved = n_pending + n_rescue + n_failed + n_geometry_blocked
            # 2026-10-21 strict-recovery ruling: a historical limitation is
            # cleared ONLY by an explicit coverage review that certifies a new
            # independent minimum -- never by emptying n_limited.  The review
            # must name recovered members that are actually in `kept`.
            cov = coverage.get((name, slot)) if coverage else None
            acceptance_status, sampling_status, cov_resolved, cov_id = acceptance_decision(
                unresolved=unresolved, n_limited=n_limited, cov=cov,
                kept_keys={m["member_key"] for m in kept})
            limit_reason = ""
            # v1.4.2: a `limited` state must always say WHY it is limited --
            # an empty reason on a limited label is indistinguishable from a
            # bug.  Three distinct causes exist and they are NOT interchangeable:
            #   rescue_budget_exhausted   -> the bounded rescue ladder ran out
            #                                (attempted>=2); a research
            #                                limitation, NOT "no minimum exists";
            #   species_drift_unrecoverable -> the optimised geometry IS another
            #                                molecule; retrying cannot restore
            #                                identity (EMC|M_plus|4 lesson);
            #   single_basin_pool         -> the frozen pool never offered
            #                                enough independent basins.
            if n_limited and not cov_resolved:
                limit_reason = ("species_drift_unrecoverable" if n_drift
                                else "rescue_budget_exhausted")
            elif len(kept) == 1:
                if n_registered == 0:
                    limit_reason = "no_registered_extras"
                elif n_dedup == n_registered and n_registered > 0:
                    limit_reason = "all_extras_deduplicated_to_primary"
                elif n_failed and not unresolved:
                    limit_reason = "extras_qc_failed"
                elif unresolved == 0:
                    limit_reason = "single_basin_pool"
            label_rows.append({
                "mol_id": primary["mol_id"], "name": name, "state": slot,
                "numerical_status": "available",
                "sampling_status": sampling_status,
                "acceptance_status": acceptance_status,
                "n_registered": str(n_registered), "n_pending": str(n_pending),
                "n_qc_passed": str(len(kept)), "n_qc_failed": str(n_failed + n_limited),
                "n_deduplicated": str(n_dedup), "n_unique": str(len(kept)),
                "n_unresolved": str(unresolved),
                "n_members": str(len(kept)),
                "pool_limited": "true" if len(kept) < 2 else "false",
                "limitation_reason": limit_reason,
                "g_min_kcal": "%.6f" % min(g_vals),
                "g_ensemble_kcal": "%.6f" % g_ens,
                "g_ensemble_eh": "%.12f" % g_ens_eh,
                # Frozen g_i=1 bound (v1.4.1 §3.3): 0 <= G_min - G_ens <= RT ln N.
                # Asserted here so a broken aggregate can never be published.
                "lowering_kcal": "%.6f" % (min(g_vals) - g_ens),
                "lowering_bound_rt_ln_n_kcal": "%.6f" % (R_KCAL * temps[0] * math.log(len(kept))),
                "coverage_status": ("resolved_by_review" if cov_resolved
                                    else ("review_" + str(cov.get("verdict"))
                                          if cov else "not_reviewed")),
                "coverage_review_id": cov_id,
                "partition_sum_relative": "%.12f" % q_total,
                "weight_sum": "%.12f" % sum(weights),
                "temp_k": "%.2f" % temps[0],
                "protocol": primary.get("method", ""),
                "protocol_version": "1.3",
            })

    def render_outputs():
        def dump_text(path_name, fieldnames, rws):
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rws)
            return buf.getvalue()

        weights_csv = dump_text("weights", [
            "member_key", "attempt", "mol_id", "name", "slot",
            "g_single_kcal", "boltzmann_weight", "temp_k", "degeneracy"], weight_rows)
        dedup_csv = dump_text("dedup", [
            "member_key", "attempt", "kept", "duplicate_of", "reason",
            "mapping", "rmsd_a", "torsion_delta_deg", "rotation_det"], dedup_rows)
        pairs_csv = dump_text('pairs', [
            'member_key', 'reference_key', 'member_geometry_sha256',
            'reference_geometry_sha256', 'mapping', 'rmsd_a',
            'torsion_delta_deg', 'rotation_det', 'search_nodes',
            'search_exhaustive', 'verdict'], pair_rows)
        labels_csv = dump_text("labels", [
            "mol_id", "name", "state", "numerical_status", "sampling_status",
            "acceptance_status", "n_registered", "n_pending", "n_qc_passed",
            "n_qc_failed", "n_deduplicated", "n_unique", "n_unresolved",
            "n_members", "pool_limited", "limitation_reason",
            "g_min_kcal", "g_ensemble_kcal", "g_ensemble_eh",
            "lowering_kcal", "lowering_bound_rt_ln_n_kcal",
            "coverage_status", "coverage_review_id",
            "partition_sum_relative", "weight_sum",
            "temp_k", "protocol", "protocol_version"], label_rows)
        index_obj = {
            "schema_version": "1.1",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": {"production_ensemble_structures.csv": hashlib.sha256(ledger_bytes).hexdigest(),
                       "production_ensemble_candidates.csv": (sha256_file(CANDIDATES)
                                                               if CANDIDATES.is_file() else ""),
                       'production_ensemble_dispositions.csv': (sha256_file(DISPOSITIONS)
                                                                if DISPOSITIONS.is_file() else 'MISSING'),
                       "aggregator_code": sha256_file(Path(__file__)),
                       "config": sha256_file(REPO / "config/physics_completion_v1.yaml"),
                       "geometry_sources": geometry_source_hashes(rows, REPO)},
            "outputs": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                        for name, text in (
                            ("production_ensemble_weights.csv", weights_csv),
                            ("production_ensemble_dedup.csv", dedup_csv),
                            ("production_ensemble_labels.csv", labels_csv),
                            ('production_ensemble_dedup_pairs.csv', pairs_csv))},
            "rules": {
                "temperature_k": TEMP_K, "gas_constant_kcal_mol_k": R_KCAL,
                "dedup_rmsd_a": DUP_RMSD_A, "torsion_tol_deg": TORSION_TOL_DEG,
                "degeneracy_default": 1,
                "algorithm_version": ALGORITHM_VERSION,
                "mapping_node_budget": MAPPING_NODE_BUDGET,
                "formula": "G_ensemble = G_min - RT ln sum_i g_i exp(-(G_i-G_min)/RT)",
                "dedup_gates": "fragment composition + bond signature -> Li donor "
                               "identity -> heavy-atom Kabsch RMSD 0.35 A -> torsions",
            },
            "stale": False,
            "labels": len(label_rows),
            "expected_labels": len(expected),
        }
        index_text = json.dumps(index_obj, indent=2, ensure_ascii=False) + "\n"
        return ((OUT / "production_ensemble_weights.csv", weights_csv),
                (OUT / "production_ensemble_dedup.csv", dedup_csv),
                (OUT / "production_ensemble_labels.csv", labels_csv),
                (OUT / 'production_ensemble_dedup_pairs.csv', pairs_csv),
                (OUT / "production_ensemble_index.json", index_text))

    rendered = render_outputs()

    if args.check:
        # v1.4.1 §3.5: READ-ONLY.  Compare in memory; on ANY path (success or
        # failure) no byte on disk is written and no mtime is touched.  The
        # index's generated_at_utc is a recording timestamp, not content, so
        # the CONTENT comparison covers the three CSVs; the index itself is
        # compared on its content-bearing fields (inputs/outputs hashes).
        failures = []
        for path, expected in rendered[:4]:
            if not path.is_file():
                failures.append(f"missing: {path.name}")
                continue
            if path.read_bytes() != expected.encode("utf-8"):
                failures.append(f"differs: {path.name}")
        index_path = OUT / "production_ensemble_index.json"
        if index_path.is_file():
            try:
                on_disk = json.loads(index_path.read_text(encoding="utf-8"))
                recomputed = json.loads(rendered[4][1])
                for key in ("inputs", "outputs", "rules", "labels", "expected_labels"):
                    if on_disk.get(key) != recomputed.get(key):
                        failures.append(f"differs: production_ensemble_index.json[{key}]")
            except (ValueError, OSError):
                failures.append("differs: production_ensemble_index.json (unreadable)")
        else:
            failures.append("missing: production_ensemble_index.json")
        if failures:
            for f in failures:
                print(f"STALE: {f}")
            return 1
        print("CHECK OK -- all production-ensemble outputs match recomputation")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for path, text in rendered:
        path.write_text(text, encoding="utf-8", newline="\n")

    accepted = sum(1 for r in label_rows if r["acceptance_status"] == "accepted")
    provisional = sum(1 for r in label_rows if r["acceptance_status"] == "provisional")
    print("labels=%d/48 accepted=%d provisional=%d weights=%d dedup_decisions=%d" % (
        len(label_rows), accepted, provisional, len(weight_rows), len(dedup_rows)))
    by_state = {}
    for r in label_rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    print("  per state:", dict(sorted(by_state.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
