"""Independent challenge probe: candidate-start gate order + P3 generators.

READ-ONLY.  Exit code 0 = every re-derived claim reproduced; 1 = at least one
claim mismatched, was not reproducible, or an attack found a gate/generator
defect that the shipped tests do not pin.  Every check prints its measured
value so the report can quote raw output.

Nothing here modifies any existing file; the probe writes nothing outside its
own stdout.  It imports the shipped module read-only and re-derives every
number in ROUTE_DECISIONS_P2.md / P3_CANDIDATES_20261023.md from the named
inputs (registry CSV, real task geometries, the P3 JSON).

Run:  .venv/Scripts/python.exe -B -X utf8 docs/handoffs/four_state_recovery_20261023/audit_gate_20261023/probe.py
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent          # .../audit_gate_20261023
REPO = HERE.parents[3]                           # .../电解液溶剂HB-Code
PROD = REPO / "scripts" / "wp_production"
BLIND_GEOM = REPO / "work" / "hpc_frontier_localization_v1" / "tasks"
REGISTRY = REPO / "outputs" / "physics_completion" / "recovery" / "torsion_freedom_registry.csv"
P3_JSON = REPO / "docs" / "handoffs" / "four_state_recovery_20261023" / "P3_CANDIDATES_20261023.json"

sys.path.insert(0, str(PROD))
sys.dont_write_bytecode = True

RESULTS: list[tuple[str, bool, str]] = []


def check(cid: str, ok: bool, detail: str) -> None:
    RESULTS.append((cid, bool(ok), detail))
    print("%-4s %-6s %s" % (cid, "PASS" if ok else "FAIL", detail))


def _load():
    spec = importlib.util.spec_from_file_location(
        "btp_audit_target", PROD / "build_torsion_probe_package.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for line in lines[2:2 + n]:
        p = line.split()
        syms.append(p[0])
        coords.append([float(p[1]), float(p[2]), float(p[3])])
    return syms, np.asarray(coords, dtype=float)


def _state(btp, name: str, state: str, leaf: str):
    geom = BLIND_GEOM / ("%s__%s__%s" % (name, state, leaf)) / "geom.xyz"
    syms, coords = _read_xyz(geom)
    adj, singles = btp._topology_for_member(name, syms)
    return syms, coords, adj, singles, geom


def _registry_rows(name: str, state: str) -> list[dict]:
    with REGISTRY.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["name"] == name and r["state"] == state]
    out = []
    for r in rows:
        head = r["detail"].split(" ")[0]
        if head.count("-") != 3:
            continue
        out.append(tuple(int(v) for v in head.split("-")))
    return out


# ---------------------------------------------------------------------------
# Part 1: claims vs re-derivation (ROUTE_DECISIONS_P2.md + P3_CANDIDATES_20261023.md)
# ---------------------------------------------------------------------------

def audit_claims(btp, p3: dict) -> None:
    print("\n== Part 1: re-derived claims ==")

    # --- geometry sha256 of the four representative geometries -------------
    # NOTE (finding): for DOL|LiM_2plus the handoff names the FRONTIER tree
    # (work/hpc_frontier_localization_v1/tasks/DOL__LiM_2plus__c05/geom.xyz),
    # but the generator's own resolver (_state_geometry) reads the ENSEMBLE
    # package file (work/hpc_production_ensemble_r1_036-053/...), and the
    # claimed sha f0b2558e... matches the ENSEMBLE file, not the frontier one
    # (079dd8b3...).  Both files are measured here.
    frontier_dol = BLIND_GEOM / "DOL__LiM_2plus__c05" / "geom.xyz"
    ensemble_dol = (REPO / "work" / "hpc_production_ensemble_r1_036-053"
                    / "tasks" / "DOL" / "LiM_2plus__c05" / "geom.xyz")
    check("geo.DOL_frontier_vs_claim",
          _sha(frontier_dol).startswith("079dd8b35c5839c0"),
          "frontier geom.xyz sha=%s... -- the sha claimed in ROUTE_DECISIONS "
          "(f0b2558e...) does NOT match this file" % _sha(frontier_dol)[:16])
    check("geo.DOL_resolver_source",
          _sha(ensemble_dol).startswith("f0b2558e0cf2cf9b"),
          "ensemble-package geom.xyz sha=%s... -- this is what the generator "
          "actually reads and what the claim matches" % _sha(ensemble_dol)[:16])
    for key, name, state, leaf, want in (
            ("DMC|M_plus", "DMC", "M_plus", "primary", "5b9e93e0146333f7c851e2f0176675a9"),
            ("DMC|LiM_2plus", "DMC", "LiM_2plus", "primary", "f619c13234e5455fe0651b7444728e42"),
            ("EC|LiM_2plus", "EC", "LiM_2plus", "primary", "16774e2151551a5e69ff867c6deea686")):
        geom = BLIND_GEOM / ("%s__%s__%s" % (name, state, leaf)) / "geom.xyz"
        got = _sha(geom)
        check("geo.%s" % key.replace("|", "_"), got.startswith(want),
              "sha256=%s... (claimed %s)" % (got[:16], want[:16]))

    # --- DMC|M_plus: 10 registered torsions; 3 probed in v1; 7 unprobed ----
    reg_rows = _registry_rows("DMC", "M_plus")
    check("reg.DMC_M_plus", len(reg_rows) == 10,
          "registry rows with 4-atom dihedral = %d (claimed 10)" % len(reg_rows))
    v1_probed = {"6-0-1-2", "7-0-1-2", "8-0-1-2"}
    unprobed = [t for t in reg_rows if "-".join(str(v) for v in t) not in v1_probed]
    check("reg.DMC_M_plus.unprobed", len(unprobed) == 7,
          "unprobed registered dihedrals = %d (claimed 7)" % len(unprobed))

    syms, coords, adj, singles, geom = _state(btp, "DMC", "M_plus", "primary")
    # rerun the gate on the 7 unprobed ones in BOTH dedup modes, because the
    # two handoff documents DISAGREE (the finding):
    #   ROUTE_DECISIONS_P2.md line 21 claims "7 accepted, 4 heavy + 3 rotor"
    #   -- that is the NO-prior_starts measurement;
    #   P3 (md+json) records 3 accepted + 4 equivalent_start -- the WITH-
    #   prior_starts measurement, which is what the frozen dedup rule
    #   ("prior_starts") requires.  Both are re-derived and pinned here.
    acc_noprior, reasons_noprior = [], []
    for dih in unprobed:
        a, b, c, d = dih
        rotated, _ = btp.rotate_fragment(coords, dih, adj,
                                          single_bonds=singles, degrees=60.0)
        verdict = btp.validate_candidate_start(
            syms, coords, rotated, adj,
            registered_single_bonds=singles, rotated_bond=(b, c))
        acc_noprior.append(verdict)
        reasons_noprior.append(verdict["reason"])
    heavy_np = sum(1 for r in reasons_noprior if r == "ok_heavy_fragment")
    rotor_np = sum(1 for r in reasons_noprior if r == "ok_methyl_rotor")
    check("gate.DMC_M_plus.noprior", (heavy_np, rotor_np) == (4, 3),
          "NO prior_starts: heavy=%d rotor=%d (ROUTE_DECISIONS line 21 claims 4+3, "
          "this reproduces its numbers)" % (heavy_np, rotor_np))
    check("gate.DMC_M_plus.discrepancy",
          (heavy_np, rotor_np) != (2, 1),
          "ROUTE_DECISIONS '7 all accepted' is a NO-dedup measurement and "
          "contradicts P3's 3-accepted-with-dedup on the same 7 torsions; "
          "both reproduce, so the two documents state different experiments")
    acc_prior, ref_prior, acc_prior_coords = [], [], []
    for dih in unprobed:
        a, b, c, d = dih
        rotated, _ = btp.rotate_fragment(coords, dih, adj,
                                          single_bonds=singles, degrees=60.0)
        verdict = btp.validate_candidate_start(
            syms, coords, rotated, adj, prior_starts=acc_prior_coords,
            registered_single_bonds=singles, rotated_bond=(b, c))
        if verdict["accepted"]:
            acc_prior.append(verdict)
            acc_prior_coords.append(rotated)
        else:
            ref_prior.append(verdict)
    heavy_p = [v for v in acc_prior if v["reason"] == "ok_heavy_fragment"]
    rotor_p = [v for v in acc_prior if v["reason"] == "ok_methyl_rotor"]
    check("gate.DMC_M_plus.withprior",
          (len(heavy_p), len(rotor_p), len(ref_prior)) == (2, 1, 4)
          and all(v["reason"] == "equivalent_start" for v in ref_prior),
          "WITH prior_starts: heavy=%d rotor=%d refused=%d (P3 claims 3 accepted "
          "+ 4 equivalent_start -- reproduced)"
          % (len(heavy_p), len(rotor_p), len(ref_prior)))
    hv = sorted(v["detail"]["heavy_pair_change_a"] for v in heavy_p)
    check("gate.DMC_M_plus.heavyvals",
          any(abs(x - 0.2743) < 5e-4 for x in hv)
          and any(abs(x - 0.2432) < 5e-4 for x in hv),
          "heavy pair-change values %s (both claimed 0.2743 & 0.2432 present)"
          % ["%.4f" % x for x in hv])

    # --- DMC|LiM_2plus ------------------------------------------------------
    syms2, coords2, adj2, singles2, _ = _state(btp, "DMC", "LiM_2plus", "primary")
    reg_rows2 = _registry_rows("DMC", "LiM_2plus")
    check("reg.DMC_LiM2", len(reg_rows2) == 10,
          "registry rows = %d (claimed 10)" % len(reg_rows2))
    unprobed2 = [t for t in reg_rows2 if "-".join(str(v) for v in t) not in v1_probed]
    acc2, ref2, acc2_coords = [], [], []
    for dih in unprobed2:
        a, b, c, d = dih
        try:
            rotated, _ = btp.rotate_fragment(coords2, dih, adj2,
                                              single_bonds=singles2, degrees=60.0)
            verdict = btp.validate_candidate_start(
                syms2, coords2, rotated, adj2, prior_starts=acc2_coords,
                registered_single_bonds=singles2, rotated_bond=(b, c))
        except ValueError as exc:
            ref2.append((dih, "raise:" + str(exc)[:60]))
            continue
        if verdict["accepted"]:
            acc2.append((dih, verdict["reason"]))
            acc2_coords.append(rotated)
        else:
            ref2.append((dih, verdict["reason"]))
    check("gate.DMC_LiM2.accept", len(acc2) == 1,
          "undeclared gate accepted %d (claimed 1)" % len(acc2))
    li_changed = [x for x in ref2 if x[1] == "li_coordination_changed"]
    check("gate.DMC_LiM2.li5", len(li_changed) == 5,
          "li_coordination_changed refusals = %d (claimed 5)" % len(li_changed))
    # declared=True flips exactly those 5
    ok_declared = []
    for dih, reason in li_changed:
        a, b, c, d = dih
        rotated, _ = btp.rotate_fragment(coords2, dih, adj2,
                                         single_bonds=singles2, degrees=60.0)
        verdict = btp.validate_candidate_start(
            syms2, coords2, rotated, adj2, declared_li_change=True)
        ok_declared.append(verdict["reason"] == "ok_li_coordination_change")
    check("gate.DMC_LiM2.declared", all(ok_declared) and ok_declared,
          "declared=True flips all %d refusals to ok_li_coordination_change"
          % len(ok_declared))

    # --- P3 JSON: table counts and heavy values -----------------------------
    for sk, want_g1, want_g2 in (
            ("DMC|M_plus", (7, 3, 4), (0, 0, 0)),
            ("DMC|LiM_2plus", (7, 1, 6), (6, 3, 3)),
            ("DOL|LiM_2plus", (0, 0, 0), (30, 9, 21)),
            ("EC|LiM_2plus", (0, 0, 0), (30, 9, 21))):
        sv = p3["states"][sk]
        g1 = sv["group_1_registered_torsions"]
        g2 = sv["group_2_new_degrees_of_freedom"]
        got_g1 = (g1["raw"], g1["accepted"], g1["refused"])
        got_g2 = (g2["raw"], g2["accepted"], g2["refused"])
        ok = (got_g1 == want_g1) and (got_g2 == want_g2)
        check("p3.%s.counts" % sk.replace("|", "_"), ok,
              "g1 raw/acc/ref=%s (claim %s); g2 raw/acc/ref=%s (claim %s)"
              % (got_g1, want_g1, got_g2, want_g2))

    # ring sets
    check("p3.DOL.ring", p3["states"]["DOL|LiM_2plus"]["ring_atoms"] == [[0, 1, 2, 3, 4]],
          "DOL ring = %s (claimed [0,1,2,3,4])" % p3["states"]["DOL|LiM_2plus"]["ring_atoms"])
    check("p3.EC.ring", p3["states"]["EC|LiM_2plus"]["ring_atoms"] == [[0, 1, 2, 3, 5]],
          "EC ring = %s (claimed [0,1,2,3,5])" % p3["states"]["EC|LiM_2plus"]["ring_atoms"])
    check("p3.DMC.noring", (p3["states"]["DMC|M_plus"]["ring_atoms"] == []
                            and p3["states"]["DMC|LiM_2plus"]["ring_atoms"] == []),
          "DMC rings both empty (claimed none)")

    # re-derive DOL/EC rings from the geometry the GENERATOR actually reads
    # (the resolver path), so the JSON comparison is like-for-like
    for name in ("DOL", "EC"):
        resolved = btp._state_geometry(name, "LiM_2plus")
        symsR, coordsR = _read_xyz(resolved)
        adjR, _singlesR = btp._topology_for_member(name, symsR)
        rings = btp.ring_atoms(adjR)
        check("ring.%s.resolver" % name,
              rings == p3["states"]["%s|LiM_2plus" % name]["ring_atoms"],
              "ring_atoms(resolver geometry %s) = %s vs JSON %s"
              % (resolved.name, rings,
                 p3["states"]["%s|LiM_2plus" % name]["ring_atoms"]))

    # refusal-reason distributions
    dmc2 = p3["states"]["DMC|LiM_2plus"]["group_1_registered_torsions"]["refused_reasons"]
    dist = {}
    for r in dmc2:
        dist[r["reason"]] = dist.get(r["reason"], 0) + 1
    check("p3.DMC_LiM2.refdist", dist == {"equivalent_start": 1, "li_coordination_changed": 5},
          "DMC|LiM2plus g1 refusal dist = %s (claimed 1 equiv + 5 li)" % dist)
    for name in ("DOL", "EC"):
        rs = p3["states"]["%s|LiM_2plus" % name]["group_2_new_degrees_of_freedom"]["refused_reasons"]
        amps = sorted({abs(r["detail"].get("amplitude_a", 0) if isinstance(r.get("detail"), dict) else 0)
                       for r in rs})
        check("p3.%s.bigamp" % name, set(rs[0].keys()) >= {"reason"}
              and all(r["reason"] == "ring_broken" for r in rs) and len(rs) == 12,
              "%s g2 refused=%d all ring_broken (claimed 12)" % (name, len(rs)))

    # pucker heavy range claim: 0.0375-0.0771 (DOL), 0.0199-0.0549 (EC)
    for name, lo, hi in (("DOL", 0.0375, 0.0771), ("EC", 0.0199, 0.0549)):
        recs = [r for r in p3["states"]["%s|LiM_2plus" % name]
                ["group_2_new_degrees_of_freedom"]["accepted_records"]
                if r["kind"] == "ring_pucker"]
        hv = sorted(r["heavy_pair_change_a"] for r in recs)
        ok = (abs(hv[0] - lo) < 5e-4 and abs(hv[-1] - hi) < 5e-4 and len(recs) == 6)
        check("p3.%s.pucker" % name, ok,
              "pucker heavy values %s (claimed range %.4f-%.4f, 6 records)"
              % (["%.4f" % v for v in hv], lo, hi))


# ---------------------------------------------------------------------------
# Part 2: attack the gate order (the 8 required attack classes)
# ---------------------------------------------------------------------------

def _ideal_ethane():
    half = np.radians(109.47)
    z = 1.09 * np.cos(half)
    rho = 1.09 * np.sin(half)
    syms = ["C", "C"]
    coords = [[0.0, 0.0, 0.0], [0.0, 0.0, 1.53]]
    for az in (0.0, 120.0, 240.0):
        t = np.radians(az)
        coords.append([rho * np.cos(t), rho * np.sin(t), z])
        syms.append("H")
    for az in (60.0, 180.0, 300.0):
        t = np.radians(az)
        coords.append([rho * np.cos(t), rho * np.sin(t), 1.53 - z])
        syms.append("H")
    return syms, np.asarray(coords, dtype=float)


def _adjacency(syms, coords, *, cutoff=1.9):
    adj = [set() for _ in syms]
    xyz = np.asarray(coords, dtype=float)
    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            if np.linalg.norm(xyz[i] - xyz[j]) <= cutoff:
                adj[i].add(j)
                adj[j].add(i)
    return adj


def _rotate_methyl(coords, degrees, *, methyl=(2, 3, 4), axis_atoms=(0, 1)):
    xyz = np.asarray(coords, dtype=float).copy()
    a = xyz[axis_atoms[1]] - xyz[axis_atoms[0]]
    a = a / np.linalg.norm(a)
    th = np.radians(degrees)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    rot = np.eye(3) + np.sin(th) * k + (1 - np.cos(th)) * (k @ k)
    for i in methyl:
        xyz[i] = xyz[axis_atoms[0]] + rot @ (xyz[i] - xyz[axis_atoms[0]])
    return xyz


def _rigid_rotate_all(coords, degrees, axis="z"):
    xyz = np.asarray(coords, dtype=float).copy()
    th = np.radians(degrees)
    c, s = np.cos(th), np.sin(th)
    if axis == "z":
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    else:
        R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return xyz @ R.T


def attack_gate_order(btp) -> None:
    print("\n== Part 2: gate-order attacks ==")
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)

    # A1: equivalent 120 deg methyl rotation must be refused as equivalent_start
    rot120 = _rotate_methyl(xyz, 120.0)
    v = btp.validate_candidate_start(syms, xyz, rot120, adj)
    check("atk.120methyl", (not v["accepted"]) and v["reason"] == "equivalent_start",
          "120deg methyl -> %s (want refused equivalent_start)" % v["reason"])

    # A2: H displaced 100 A must be refused (ring_broken), NOT classified
    broken = xyz.copy()
    broken[2] = broken[2] + np.array([100.0, 0.0, 0.0])
    v = btp.validate_candidate_start(syms, xyz, broken, adj)
    check("atk.H100A", (not v["accepted"]) and v["reason"] == "ring_broken",
          "H+100A -> %s (want refused ring_broken, never ok_methyl_rotor)" % v["reason"])

    # A3: pure rigid rotation of the whole molecule -> rigid_transformation
    rigid = _rigid_rotate_all(xyz, 37.5)
    v = btp.validate_candidate_start(syms, xyz, rigid, adj)
    check("atk.rigid", (not v["accepted"]) and v["reason"] == "rigid_transformation",
          "rigid 37.5deg -> %s (want rigid_transformation)" % v["reason"])

    # A3b: rigid + translation -> also rigid
    rigid2 = _rigid_rotate_all(xyz, 90.0) + np.array([10.0, -4.0, 2.0])
    v = btp.validate_candidate_start(syms, xyz, rigid2, adj)
    check("atk.rigid+trans", (not v["accepted"]) and v["reason"] == "rigid_transformation",
          "rigid 90deg + shift -> %s" % v["reason"])

    # A4: broken ring (5-ring, stretch one bond beyond the cut)
    rsyms = ["C", "C", "O", "C", "O"]
    rcoords = np.array([[1.50, 0.0, 0.0], [0.47, 1.42, 0.0], [-0.95, 0.88, 0.0],
                        [-0.95, -0.88, 0.0], [0.47, -1.42, 0.0]])
    radj = _adjacency(rsyms, rcoords, cutoff=1.8)
    moved = rcoords.copy()
    moved[3] = moved[3] + np.array([3.0, 0.0, 0.0])
    v = btp.validate_candidate_start(rsyms, rcoords, moved, radj)
    check("atk.brokenring", (not v["accepted"]) and v["reason"] == "ring_broken",
          "stretched ring bond -> %s (want ring_broken)" % v["reason"])

    # A5: C=O pseudo-torsion (axis present in adjacency, absent from singles)
    singles_all = {tuple(sorted((i, j))) for i in range(len(syms))
                   for j in adj[i] if i < j}
    rot60 = _rotate_methyl(xyz, 60.0)
    v = btp.validate_candidate_start(
        syms, xyz, rot60, adj,
        registered_single_bonds=singles_all - {tuple(sorted((0, 1)))},
        rotated_bond=(0, 1))
    check("atk.COpseudo", (not v["accepted"]) and v["reason"] == "not_a_single_bond_rotor",
          "C=O axis -> %s (want not_a_single_bond_rotor)" % v["reason"])
    # A5b: axis declared but registry omitted entirely
    v = btp.validate_candidate_start(syms, xyz, rot60, adj, rotated_bond=(0, 1))
    check("atk.noRegistry", (not v["accepted"]) and v["reason"] == "missing_single_bond_registry",
          "no registry -> %s (want missing_single_bond_registry)" % v["reason"])

    # A6: Li first-shell change, undeclared vs declared
    lsyms = ["O", "O", "Li", "H"]
    lcoords = np.array([[2.0, 0.0, 0.0], [0.0, 2.4, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 3.5]])
    ladj = _adjacency(lsyms, lcoords, cutoff=1.9)
    lmoved = lcoords.copy()
    lmoved[0] = lmoved[0] + np.array([2.0, 0.0, 0.0])
    v = btp.validate_candidate_start(lsyms, lcoords, lmoved, ladj)
    check("atk.Lishell.undeclared", (not v["accepted"]) and v["reason"] == "li_coordination_changed",
          "undeclared shell change -> %s (want li_coordination_changed)" % v["reason"])
    v = btp.validate_candidate_start(lsyms, lcoords, lmoved, ladj, declared_li_change=True)
    check("atk.Lishell.declared", v["accepted"] and v["reason"] == "ok_li_coordination_change"
          and v["detail"]["probe_class"] == "li_coordination_change",
          "declared -> %s class=%s (want ok_li_coordination_change / its own class)"
          % (v["reason"], v["detail"].get("probe_class")))

    # A7: LEGAL ring pucker must be accepted as ok_heavy_fragment
    pucker = rcoords.copy()
    pucker[3] = pucker[3] + np.array([0.0, 0.0, 0.25])
    v = btp.validate_candidate_start(rsyms, rcoords, pucker, radj)
    check("atk.legalpucker", v["accepted"] and v["reason"] == "ok_heavy_fragment"
          and v["detail"]["heavy_pair_change_a"] > 1e-5,
          "legal pucker -> %s heavy=%.4f (want ok_heavy_fragment)" 
          % (v["reason"], v["detail"].get("heavy_pair_change_a", -1)))

    # A8: threshold-band probe: move one H by ~1e-5 A-scale on pair distances.
    # A displacement just ABOVE the threshold must move on; just BELOW must be
    # refused as rigid.  The threshold is on max |pair-distance change|.
    delta_above = xyz.copy()
    # moving one H by d changes its distance to the 5 non-bonded atoms by ~d;
    # distance to its own C changes by ~d/2.  Use d=6e-5 so max change > 1e-5.
    delta_above[2] = delta_above[2] + np.array([6e-5, 0.0, 0.0])
    v_above = btp.validate_candidate_start(syms, xyz, delta_above, adj)
    delta_below = xyz.copy()
    delta_below[2] = delta_below[2] + np.array([2e-6, 0.0, 0.0])
    v_below = btp.validate_candidate_start(syms, xyz, delta_below, adj)
    check("atk.threshold",
          (v_above["reason"] != "rigid_transformation"
           and v_below["reason"] == "rigid_transformation"),
          "above-threshold -> %s; below-threshold -> %s (want non-rigid / rigid)"
          % (v_above["reason"], v_below["reason"]))
    # and measure the actual crossing point
    measured = []
    for d in (2e-6, 6e-6, 1.01e-5, 2e-5):
        probe = xyz.copy()
        probe[2] = probe[2] + np.array([d, 0.0, 0.0])
        vv = btp.validate_candidate_start(syms, xyz, probe, adj)
        measured.append((d, vv["reason"]))
    print("        threshold scan: %s" % measured)

    # A9: symmetry-equivalent rotation with prior_starts (duplicate injection)
    first = _rotate_methyl(xyz, 60.0)
    dup = _rotate_methyl(xyz, 60.0)  # identical bytes
    v = btp.validate_candidate_start(syms, xyz, dup, adj, prior_starts=[first])
    check("atk.duplicate", (not v["accepted"]) and v["reason"] == "equivalent_start"
          and v["detail"].get("against") == "prior_start_0",
          "byte-identical duplicate -> %s against=%s" % (v["reason"], v["detail"].get("against")))

    # A10: malformed shapes must fail closed, not raise
    for label, args in (
            ("2D", (syms, xyz.reshape(-1, 6), xyz, adj)),
            ("nan", (syms, xyz, np.where(np.arange(xyz.size).reshape(xyz.shape) == 0,
                                          np.nan, xyz), adj)),
            ("short", (syms, xyz, xyz[:-1], adj)),
            ("badadj", (syms, xyz, xyz, adj[:-1]))):
        try:
            v = btp.validate_candidate_start(*args)
            ok = (not v["accepted"]) and v["reason"] == "malformed_input"
            check("atk.malformed.%s" % label, ok, "-> %s" % v["reason"])
        except Exception as exc:
            check("atk.malformed.%s" % label, False,
                  "RAISED %s: %s (gate must return a verdict, not raise)"
                  % (type(exc).__name__, str(exc)[:80]))


# ---------------------------------------------------------------------------
# Part 3: attack the generators
# ---------------------------------------------------------------------------

def attack_generators(btp) -> None:
    print("\n== Part 3: generator attacks ==")

    # G1: ring_pucker_candidates on an ACYCLIC molecule -> [] and no crash
    syms, coords, adj, singles, _ = _state(btp, "DMC", "M_plus", "primary")
    try:
        cands = btp.ring_pucker_candidates(syms, coords, adj)
        check("gen.pucker.acyclic", cands == [],
              "DMC|M_plus (acyclic) pucker candidates = %d (want 0, no crash)" % len(cands))
    except Exception as exc:
        check("gen.pucker.acyclic", False, "RAISED %s: %s" % (type(exc).__name__, str(exc)[:80]))

    # G2: li_coordination_candidates on a NO-Li state -> [] and no crash
    try:
        cands = btp.li_coordination_candidates(syms, coords, adj)
        check("gen.li.noLi", cands == [],
              "DMC|M_plus (no Li) coordination candidates = %d (want 0, no crash)" % len(cands))
    except Exception as exc:
        check("gen.li.noLi", False, "RAISED %s: %s" % (type(exc).__name__, str(exc)[:80]))

    # G3: over-large pucker amplitude must be REFUSED AS ring_broken by the
    # selector (a refusal record, never a silent drop)
    symsD, coordsD, adjD, singlesD, _ = _state(btp, "DOL", "LiM_2plus", "c05")
    big = [c for c in btp.ring_pucker_candidates(symsD, coordsD, adjD)
           if abs(c["amplitude_a"]) >= 0.60]
    out = btp.select_candidates(symsD, coordsD, adjD, big,
                                registered_single_bonds=singlesD, source_sha256="probe")
    reasons = {r["reason"] for r in out["refused"]}
    check("gen.pucker.brokenrefused",
          out["accepted"] == [] and reasons == {"ring_broken"} and len(out["refused"]) == len(big),
          "selector on >=0.60 amplitudes: accepted=%d refused=%d reasons=%s (want 0/%d/ring_broken)"
          % (len(out["accepted"]), len(out["refused"]), reasons, len(big)))
    # every refusal must carry evidence, not be silently dropped
    evidenced = all(r["detail"].get("lost_bonds") or r["detail"].get("pair_distance_change_a") is not None
                    for r in out["refused"])
    check("gen.pucker.refevidence", evidenced,
          "every ring_broken refusal carries detail evidence: %s" % evidenced)

    # G4: raw candidate counts of the generators match the P3 claims
    pucker_all = btp.ring_pucker_candidates(symsD, coordsD, adjD)
    li_all = btp.li_coordination_candidates(symsD, coordsD, adjD)
    check("gen.DOL.rawcounts", len(pucker_all) == 24 and len(li_all) == 6,
          "DOL raw pucker=%d (want 24: 3 modes x 8 amps) li=%d (want 6: 2 dirs x 3 offs)"
          % (len(pucker_all), len(li_all)))

    # G5: selector dedup against prior: 3 geometrically identical candidates
    tri = [dict(c) for c in pucker_all[:1]] * 3
    tri = [dict(c) for c in pucker_all[:1]]
    copies = []
    for k in range(3):
        c = dict(pucker_all[0])
        c["coords"] = np.array(pucker_all[0]["coords"], dtype=float).copy()
        copies.append(c)
    out = btp.select_candidates(symsD, coordsD, adjD, copies,
                                registered_single_bonds=singlesD, source_sha256="probe")
    check("gen.selector.tri", len(out["accepted"]) == 1 and len(out["refused"]) == 2
          and all(r["reason"] == "equivalent_start" for r in out["refused"]),
          "3 identical candidates -> accepted=%d refused=%d (want 1/2 equivalent_start)"
          % (len(out["accepted"]), len(out["refused"])))

    # G6: _distance_fingerprint invariance: rotation + translation
    probe = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.4, 0.2], [0.3, 0.3, 0.9]])
    th = np.radians(41.7)
    R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    moved = probe @ R.T + np.array([8.0, -2.0, 3.5])
    fp0, fp1 = btp._distance_fingerprint(probe), btp._distance_fingerprint(moved)
    deformed = probe.copy()
    deformed[3] = deformed[3] + np.array([0.0, 0.0, 0.5])
    fp2 = btp._distance_fingerprint(deformed)
    check("gen.fingerprint", fp0 == fp1 and fp0 != fp2,
          "rigid motion: same hash (%s); deformation: different (%s)"
          % (fp0[:12], fp2[:12]))

    # G7b: pucker normal sign canonicalization -- flipping the SVD input order
    # must not change the generated coordinates (the claimed cross-LAPACK
    # byte-determinism of the preregistered amplitudes).
    gen_a = btp.ring_pucker_candidates(symsD, coordsD, adjD)
    flipped = np.asarray(coordsD, dtype=float).copy()
    flipped[0], flipped[4] = flipped[4].copy(), flipped[0].copy()  # permute rows
    # (the permutation is NOT a symmetry op; instead test repeatability)
    gen_b = btp.ring_pucker_candidates(symsD, coordsD, adjD)
    same = all(np.array_equal(a["coords"], b["coords"]) for a, b in zip(gen_a, gen_b))
    check("gen.pucker.deterministic", same and len(gen_a) == len(gen_b),
          "ring_pucker_candidates repeatable byte-for-byte: %s (%d candidates)"
          % (same, len(gen_a)))

    # G7c: selector max_keep caps acceptance but must still gate everything.
    # MEASURED DEFECT: the loop breaks at the cap and the remaining raw
    # candidates appear in NEITHER list -- 5 of 6 vanish without a trace.
    # Latent (P4 passes max_keep=None today), but it breaks the project's own
    # "no silent drop" discipline the moment any caller sets the cap.
    small = [dict(c) for c in gen_a[:6]]
    out_cap = btp.select_candidates(symsD, coordsD, adjD, small,
                                    registered_single_bonds=singlesD,
                                    source_sha256="probe", max_keep=1)
    accounted = len(out_cap["accepted"]) + len(out_cap["refused"])
    check("gen.selector.maxkeep", accounted == len(small),
          "DEFECT: max_keep=1 on 6 raw -> accepted=%d refused=%d, %d candidates "
          "silently dropped (accounted %d/6)"
          % (len(out_cap["accepted"]), len(out_cap["refused"]),
             len(small) - accounted, accounted))

    # G7d: P4 seed reconstruction uniqueness (the --check path relies on it)
    p3_doc = json.loads(P3_JSON.read_text(encoding="utf-8"))
    ok_recon, n_recon = True, 0
    for sk, sv in p3_doc["states"].items():
        g2 = sv["group_2_new_degrees_of_freedom"]
        if not g2.get("accepted_records"):
            continue
        resolved = btp._state_geometry(sk.split("|")[0], sk.split("|")[1])
        symsP, coordsP = _read_xyz(resolved)
        adjP, singlesP = btp._topology_for_member(sk.split("|")[0], symsP)
        for rec in g2["accepted_records"]:
            seed = {"kind": rec["kind"], "label": rec["label"],
                    "amplitude_a": rec.get("amplitude_a"),
                    "offset_a": rec.get("offset_a"),
                    "result_distance_fingerprint": rec["result_distance_fingerprint"]}
            try:
                cand = btp._p4_candidate_from_seed(symsP, coordsP, adjP, singlesP, seed)
                n_recon += 1
                if btp._distance_fingerprint(cand["coords"]) != rec["result_distance_fingerprint"]:
                    ok_recon = False
            except ValueError:
                ok_recon = False
    check("gen.p4seed.reconstruct", ok_recon and n_recon == 21,
          "P4 seed reconstruction unique + fingerprint-consistent for %d/21 "
          "accepted records" % n_recon)

    # G7e: malformed rotated_bond indices (negative / out of range) must be
    # malformed_input, never an IndexError.
    # MEASURED DEFECT: NEGATIVE indices are not range-checked (only
    # axis[1] >= len(symbols) is), so (-1, 1) falls through to the registry
    # gates (missing_single_bond_registry without a registry,
    # not_a_single_bond_rotor with one) instead of malformed_input.
    # Fail-closed in practice (no real registry contains negatives), but the
    # malformed_input branch does not catch them.
    for label, rb in (("neg", (-1, 1)), ("oob", (0, 99)), ("self", (2, 2))):
        try:
            v = btp.validate_candidate_start(symsD, coordsD, coordsD.copy(), adjD,
                                             rotated_bond=rb)
            check("atk.badrotbond.%s" % label, v["reason"] == "malformed_input",
                  "-> %s%s" % (v["reason"],
                               "  [DEFECT: negative index not range-checked]"
                               if label == "neg" and v["reason"] != "malformed_input"
                               else ""))
        except Exception as exc:
            check("atk.badrotbond.%s" % label, False,
                  "RAISED %s: %s" % (type(exc).__name__, str(exc)[:80]))


# ---------------------------------------------------------------------------
# Part 4: every refusal branch must be provably reachable ("dead judge" hunt)
# ---------------------------------------------------------------------------

def hunt_dead_branches(btp) -> None:
    print("\n== Part 4: dead-branch hunt (can each refusal reason fire?) ==")
    reachable = {}

    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    singles_all = {tuple(sorted((i, j))) for i in range(len(syms))
                   for j in adj[i] if i < j}

    # malformed_input
    try:
        v = btp.validate_candidate_start(syms, xyz.reshape(-1, 6), xyz, adj)
        reachable["malformed_input"] = v["reason"] == "malformed_input"
    except Exception:
        reachable["malformed_input"] = False
    # malformed via bad rotated_bond
    v = btp.validate_candidate_start(syms, xyz, _rotate_methyl(xyz, 60.0), adj,
                                     rotated_bond=(0, 0))
    reachable["malformed_input"] = reachable["malformed_input"] or v["reason"] == "malformed_input"

    # missing_single_bond_registry
    v = btp.validate_candidate_start(syms, xyz, _rotate_methyl(xyz, 60.0), adj,
                                     rotated_bond=(0, 1))
    reachable["missing_single_bond_registry"] = v["reason"] == "missing_single_bond_registry"

    # not_a_single_bond_rotor
    v = btp.validate_candidate_start(syms, xyz, _rotate_methyl(xyz, 60.0), adj,
                                     registered_single_bonds=singles_all - {(0, 1)},
                                     rotated_bond=(0, 1))
    reachable["not_a_single_bond_rotor"] = v["reason"] == "not_a_single_bond_rotor"

    # rigid_transformation
    v = btp.validate_candidate_start(syms, xyz, xyz.copy(), adj)
    reachable["rigid_transformation"] = v["reason"] == "rigid_transformation"

    # ring_broken
    broken = xyz.copy()
    broken[2] = broken[2] + np.array([100.0, 0.0, 0.0])
    v = btp.validate_candidate_start(syms, xyz, broken, adj)
    reachable["ring_broken"] = v["reason"] == "ring_broken"

    # collision_or_new_bond: swing one H to 0.70 A from a SAME-CARBON sibling H.
    # Keeping |H2-C0| = 1.09 preserves its own bond; 0.70 A < the 0.81 A H-H
    # 1.3x covalent cut, so the bond_graph GAINS edge (2,3) -> added>lost=empty.
    # (A first attempt that moved H2 100 A or toward the OTHER methyl fired
    # ring_broken first -- a bad-attack construction, not a dead branch.)
    import math as _math
    c0 = xyz[0]
    h3 = xyz[3]
    r1, r2 = 1.09, 0.70
    d0 = float(np.linalg.norm(h3 - c0))
    a = (r1 * r1 - r2 * r2 + d0 * d0) / (2 * d0)
    hh = _math.sqrt(max(r1 * r1 - a * a, 0.0))
    base_pt = c0 + a * (h3 - c0) / d0
    w = np.cross(h3 - c0, np.array([1.0, 0.4, 0.2]))
    w = w / np.linalg.norm(w)
    swung = xyz.copy()
    swung[2] = base_pt + hh * w
    assert abs(np.linalg.norm(swung[2] - c0) - 1.09) < 1e-9
    assert abs(np.linalg.norm(swung[2] - h3) - 0.70) < 1e-9
    v = btp.validate_candidate_start(syms, xyz, swung, adj)
    reachable["collision_or_new_bond"] = v["reason"] == "collision_or_new_bond"
    print("        collision probe (H swung to 0.70A of sibling) -> %s %s"
          % (v["reason"], str(v["detail"])[:100]))

    # li_coordination_changed
    lsyms = ["O", "O", "Li", "H"]
    lcoords = np.array([[2.0, 0.0, 0.0], [0.0, 2.4, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 3.5]])
    ladj = _adjacency(lsyms, lcoords, cutoff=1.9)
    lmoved = lcoords.copy()
    lmoved[0] = lmoved[0] + np.array([2.0, 0.0, 0.0])
    v = btp.validate_candidate_start(lsyms, lcoords, lmoved, ladj)
    reachable["li_coordination_changed"] = v["reason"] == "li_coordination_changed"

    # mapping_unresolved: equivalent_start raises ValueError -> mapping_unresolved
    # Force the node cap (100000) with a pathological symmetric input?  Instead:
    # directly raise from equivalent_start via a shape-consistent but unsolvable
    # mapping: feed a candidate whose colours cannot map -- use monkey-level
    # injection: call validate with a prior that has a different shape.
    bad_prior = np.zeros((len(syms), 4))
    try:
        v = btp.validate_candidate_start(syms, xyz, _rotate_methyl(xyz, 60.0), adj,
                                         prior_starts=[bad_prior])
        reachable["mapping_unresolved"] = v["reason"] == "mapping_unresolved"
        print("        mapping probe (bad prior shape) -> %s" % v["reason"])
    except Exception as exc:
        reachable["mapping_unresolved"] = False
        print("        mapping probe RAISED %s" % type(exc).__name__)

    # equivalent_start
    v = btp.validate_candidate_start(syms, xyz, _rotate_methyl(xyz, 120.0), adj)
    reachable["equivalent_start"] = v["reason"] == "equivalent_start"

    # accepted classes
    v = btp.validate_candidate_start(syms, xyz, _rotate_methyl(xyz, 60.0), adj)
    reachable["ok_methyl_rotor"] = v["reason"] == "ok_methyl_rotor"
    hv = xyz.copy()
    hv = _rotate_methyl(hv, 60.0, methyl=(5, 6, 7))
    hv[1] = hv[1] + np.array([0.4, 0.0, 0.0])
    v = btp.validate_candidate_start(syms, xyz, hv, adj)
    reachable["ok_heavy_fragment"] = v["reason"] == "ok_heavy_fragment"
    v = btp.validate_candidate_start(lsyms, lcoords, lmoved, ladj,
                                     declared_li_change=True)
    reachable["ok_li_coordination_change"] = v["reason"] == "ok_li_coordination_change"

    for reason in ("malformed_input", "missing_single_bond_registry",
                   "not_a_single_bond_rotor", "rigid_transformation", "ring_broken",
                   "collision_or_new_bond", "li_coordination_changed",
                   "mapping_unresolved", "equivalent_start",
                   "ok_methyl_rotor", "ok_heavy_fragment", "ok_li_coordination_change"):
        check("branch.%s" % reason, reachable.get(reason, False),
              "reachable=%s" % reachable.get(reason, False))


def main() -> int:
    btp = _load()
    p3 = json.loads(P3_JSON.read_text(encoding="utf-8"))
    audit_claims(btp, p3)
    attack_gate_order(btp)
    attack_generators(btp)
    hunt_dead_branches(btp)

    failed = [(c, d) for c, ok, d in RESULTS if not ok]
    print("\n== SUMMARY: %d checks, %d pass, %d fail ==" % (
        len(RESULTS), len(RESULTS) - len(failed), len(failed)))
    for cid, detail in failed:
        print("  FAIL %s: %s" % (cid, detail))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
