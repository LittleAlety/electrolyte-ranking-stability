"""P0: the candidate-start gate must reject BEFORE it classifies, and be CALLED.

The user's P0 blocking item, reproduced before the fix:

* ``AN|M_plus|tors_3_0_1_2`` with ONE hydrogen moved 100 A -> the gate returned
  ``ok_methyl_rotor`` and ACCEPTED it (``heavy_change`` is 0 when only H moves and
  the function returned before any topology check);
* an equivalent 120 deg methyl rotation -> likewise accepted, because the
  equivalence test also sat after that early return;
* and ``validate_candidate_start`` had **zero call sites** -- a helper that looked
  like a production gate while the real packaging path re-implemented only part of
  it.

After the reorder the evaluation order is: malformed -> rotated_bond is a
registered single bond -> actually moved -> covalent topology intact -> Li first
shell unchanged -> not equivalent -> ONLY THEN classify methyl-rotor vs
heavy-fragment.  Both packaging paths (``_repair_member`` and ``_build_state``)
now call it.

Fixtures: an EXACT C3v ethane for the symmetry cases (the real AN methyl is
distorted -- a 120 deg rotation is 0.257 A from congruent, so it cannot show the
symmetry case) and the real v2 real-fragment package for the measured cases.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))

V2 = REPO / "work" / "hpc_torsion_probe_v2_realfragment"


def _load():
    spec = importlib.util.spec_from_file_location(
        "btp", PROD / "build_torsion_probe_package.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def btp():
    return _load()


# ---- fixtures -------------------------------------------------------------

def _ideal_ethane():
    """CH3-CH3 with exact geometry: 1.53 A C-C, 1.09 A C-H, 109.47 deg angles."""
    half = np.radians(109.47)
    z = 1.09 * np.cos(half)
    rho = 1.09 * np.sin(half)
    syms = ["C", "C"]
    coords = [[0.0, 0.0, 0.0], [0.0, 0.0, 1.53]]
    for az in (0.0, 120.0, 240.0):                     # methyl on C0
        t = np.radians(az)
        coords.append([rho * np.cos(t), rho * np.sin(t), z])
        syms.append("H")
    for az in (60.0, 180.0, 300.0):                    # staggered methyl on C1
        t = np.radians(az)
        coords.append([rho * np.cos(t), rho * np.sin(t), 1.53 - z])
        syms.append("H")
    return syms, np.asarray(coords, dtype=float)


def _rotate_methyl(coords, degrees, *, methyl=(2, 3, 4), axis_atoms=(0, 1)):
    """Rigidly rotate one methyl about the C0-C1 axis."""
    xyz = np.asarray(coords, dtype=float).copy()
    a = xyz[axis_atoms[1]] - xyz[axis_atoms[0]]
    a = a / np.linalg.norm(a)
    th = np.radians(degrees)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    rot = np.eye(3) + np.sin(th) * k + (1 - np.cos(th)) * (k @ k)
    for i in methyl:
        xyz[i] = xyz[axis_atoms[0]] + rot @ (xyz[i] - xyz[axis_atoms[0]])
    return xyz


def _adjacency(syms, coords, *, cutoff=1.9):
    adj = [set() for _ in syms]
    xyz = np.asarray(coords, dtype=float)
    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            if np.linalg.norm(xyz[i] - xyz[j]) <= cutoff:
                adj[i].add(j)
                adj[j].add(i)
    return adj


def _real_v2(btp, member_key="AN|M_plus|tors_3_0_1_2"):
    man = json.loads((V2 / "manifest.json").read_text(encoding="utf-8"))
    mem = next(m for m in man["members"] if m["member_key"] == member_key)
    src = REPO / mem["source_geometry"]
    syms, coords, _ = btp._read_xyz(src)
    adj, singles = btp._topology_for_member(mem["name"], syms)
    return syms, np.asarray(coords, dtype=float), adj, singles, mem


# ---- the two reproduced false acceptances ---------------------------------

def test_an_equivalent_120_deg_methyl_rotation_is_refused(btp):
    """THE user-reported case 1: a symmetry rotation is not an independent start."""
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    rot = _rotate_methyl(xyz, 120.0)
    assert btp.equivalent_start(syms, xyz, rot, adj) is True, \
        "the fixture must actually be a symmetry operation"
    verdict = btp.validate_candidate_start(syms, xyz, rot, adj)
    assert verdict["accepted"] is False
    assert verdict["reason"] == "equivalent_start", verdict


def test_a_legal_60_deg_methyl_rotor_is_accepted(btp):
    """The complementary positive: 60 deg is NOT a symmetry, so it is a start.

    This is also what the two real v2 probes actually used (offset 60), so the
    reorder must not break them.
    """
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    rot = _rotate_methyl(xyz, 60.0)
    verdict = btp.validate_candidate_start(syms, xyz, rot, adj)
    assert verdict["accepted"] is True, verdict
    assert verdict["reason"] == "ok_methyl_rotor", verdict
    assert verdict["detail"]["probe_class"] == "methyl_rotor"


def test_one_hydrogen_moved_100a_is_refused_as_ring_broken(btp):
    """THE user-reported case 2, on the real fixture that exposed it."""
    syms, xyz, adj, _singles, _mem = _real_v2(btp)
    broken = xyz.copy()
    h = next(i for i, s in enumerate(syms) if s == "H")
    broken[h] = broken[h] + np.array([100.0, 0.0, 0.0])
    verdict = btp.validate_candidate_start(syms, xyz, broken, adj)
    assert verdict["accepted"] is False, verdict
    assert verdict["reason"] == "ring_broken", verdict
    assert verdict["detail"]["lost_bonds"], verdict


def test_the_real_60_deg_probe_still_passes_the_reordered_gate(btp):
    """No regression: the two registered real-fragment probes stay accepted."""
    for key in ("AN|M_plus|tors_3_0_1_2", "DMC|M_plus|tors_8_0_1_2"):
        syms, xyz, adj, singles, mem = _real_v2(btp, key)
        dih = tuple(int(v) for v in mem["dihedral"].split("-"))
        rot, _audit = btp.rotate_fragment(xyz, dih, adj, single_bonds=singles,
                                         degrees=mem["scan_offset_deg"])
        verdict = btp.validate_candidate_start(
            syms, xyz, rot, adj, registered_single_bonds=singles,
            rotated_bond=(dih[1], dih[2]))
        assert verdict["accepted"] is True, (key, verdict)
        assert verdict["reason"] == "ok_methyl_rotor", (key, verdict)


# ---- the rest of the required rejection classes ---------------------------

def test_rigid_transformation_is_refused(btp):
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    verdict = btp.validate_candidate_start(syms, xyz, xyz.copy(), adj)
    assert verdict["reason"] == "rigid_transformation", verdict


def test_a_broken_ring_is_refused(btp):
    """Stretch a ring bond until the covalent graph loses it."""
    syms = ["C", "C", "O", "C", "C", "O"]
    coords = np.array([[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [1.5, 1.4, 0.0],
                       [0.0, 1.4, 0.0], [-0.9, 0.7, 0.0], [0.0, -0.9, 0.0]])
    adj = _adjacency(syms, coords)
    moved = coords.copy()
    moved[3] = moved[3] + np.array([3.0, 0.0, 0.0])   # ring bond C2-C3 broken
    verdict = btp.validate_candidate_start(syms, coords, moved, adj)
    assert verdict["accepted"] is False
    assert verdict["reason"] == "ring_broken", verdict


def test_a_carbonyl_bond_is_not_a_rotor(btp):
    """'C=O pseudo-torsion' -- the axis must be a REGISTERED SINGLE bond.

    The fixture must EXCLUDE the axis from the single-bond set: passing the full
    single-bond set would (correctly) accept it, since C0-C1 really is single in
    ethane.  This is how a carbonyl is represented: present in the adjacency,
    absent from the single-bond set.
    """
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    singles = {tuple(sorted((i, j))) for i in range(len(syms))
               for j in adj[i] if i < j}
    assert tuple(sorted((0, 1))) in singles, "ethe fixture's C-C must be single"
    rot = _rotate_methyl(xyz, 60.0)
    verdict = btp.validate_candidate_start(
        syms, xyz, rot, adj, registered_single_bonds=singles - {tuple(sorted((0, 1)))},
        rotated_bond=(0, 1))
    assert verdict["accepted"] is False
    assert verdict["reason"] == "not_a_single_bond_rotor", verdict


def test_a_declared_torsion_without_single_bond_registry_is_refused(btp):
    """A caller may not omit bond-order evidence and thereby bypass the C=O gate."""
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    verdict = btp.validate_candidate_start(
        syms, xyz, _rotate_methyl(xyz, 60.0), adj,
        rotated_bond=(0, 1))
    assert verdict["accepted"] is False, verdict
    assert verdict["reason"] == "missing_single_bond_registry", verdict


@pytest.mark.parametrize(
    ("rotated_bond", "registered_single_bonds"),
    [
        (None, {(0, 1)}),
        ((0, 1), None),
    ],
)
def test_torsion_selector_requires_axis_and_single_bond_registry(
        btp, rotated_bond, registered_single_bonds):
    """The generic P3 selector must fail closed before a manifest can be built."""
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    candidate = {"kind": "torsion", "mode": "missing-axis-and-registry",
                 "coords": _rotate_methyl(xyz, 60.0)}
    if rotated_bond is not None:
        candidate["rotated_bond"] = rotated_bond
    selected = btp.select_candidates(
        syms, xyz, adj, [candidate],
        registered_single_bonds=registered_single_bonds)
    assert selected["accepted"] == [], selected
    assert selected["refused"][0]["reason"] == "missing_single_bond_registry", selected


def test_a_new_covalent_contact_is_refused(btp):
    """A collision that creates a bond is not a conformer."""
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    moved = xyz.copy()
    moved[2] = moved[6] + np.array([0.1, 0.0, 0.0])   # H on C0 onto H on C1
    verdict = btp.validate_candidate_start(syms, xyz, moved, adj)
    assert verdict["accepted"] is False
    assert verdict["reason"] in ("collision_or_new_bond", "ring_broken"), verdict


def test_a_changed_li_first_shell_is_refused(btp):
    """A probe must not silently alter Li's coordination environment.

    Fixture note (first version was wrong): with a 2.6 A cutoff every atom of the
    original fixture sat inside the shell, so nudging one of them kept the shell
    identical and the gate rightly accepted.  Put the partners at 2.0/2.4 A and
    push one OUT of the shell.
    """
    syms = ["O", "O", "Li", "H"]
    coords = np.array([[2.0, 0.0, 0.0], [0.0, 2.4, 0.0], [0.0, 0.0, 0.0],
                       [0.0, 0.0, 3.5]])
    adj = _adjacency(syms, coords, cutoff=1.9)      # no covalent edges at all
    assert not any(adj), "the fixture must have no covalent bonds"
    moved = coords.copy()
    moved[0] = moved[0] + np.array([2.0, 0.0, 0.0])  # O0 leaves (2.0 -> 4.0 A)
    verdict = btp.validate_candidate_start(syms, coords, moved, adj)
    assert verdict["accepted"] is False, verdict
    assert verdict["reason"] == "li_coordination_changed", verdict


def test_a_declared_li_coordination_probe_is_accepted_as_its_own_kind(btp):
    """The declared counterpart: the change IS the purpose, so it is classified.

    Without this, the legal Li-coordination search the plan names for
    DMC|LiM_2plus / DOL / EC could not be executed at all -- 5 of
    DMC|LiM_2plus's 7 registered torsions change Li's shell.
    """
    syms = ["O", "O", "Li", "H"]
    coords = np.array([[2.0, 0.0, 0.0], [0.0, 2.4, 0.0], [0.0, 0.0, 0.0],
                       [0.0, 0.0, 3.5]])
    adj = _adjacency(syms, coords, cutoff=1.9)
    moved = coords.copy()
    moved[0] = moved[0] + np.array([2.0, 0.0, 0.0])
    verdict = btp.validate_candidate_start(
        syms, coords, moved, adj, declared_li_change=True)
    assert verdict["accepted"] is True, verdict
    assert verdict["reason"] == "ok_li_coordination_change", verdict
    assert verdict["detail"]["probe_class"] == "li_coordination_change", verdict
    # and the change itself must be recorded, not hidden
    assert verdict["detail"]["source_shells"] != verdict["detail"]["candidate_shells"]


def test_an_undeclared_li_change_is_never_labelled_a_torsion(btp):
    """Regression on the reason: it must stay a refusal, not a silent torsion."""
    syms = ["O", "O", "Li", "H"]
    coords = np.array([[2.0, 0.0, 0.0], [0.0, 2.4, 0.0], [0.0, 0.0, 0.0],
                       [0.0, 0.0, 3.5]])
    adj = _adjacency(syms, coords, cutoff=1.9)
    moved = coords.copy()
    moved[0] = moved[0] + np.array([2.0, 0.0, 0.0])
    for kwargs in ({}, {"check_li_shell": True}):
        v = btp.validate_candidate_start(syms, coords, moved, adj, **kwargs)
        assert v["accepted"] is False and v["reason"] == "li_coordination_changed", v


def test_a_legal_heavy_fragment_change_is_accepted(btp):
    """Positive: the heavy skeleton moved and the topology held."""
    syms, xyz = _ideal_ethane()
    adj = _adjacency(syms, xyz)
    moved = xyz.copy()
    # rotate the whole C1 methyl about the C-C axis: a methyl rotor, then tilt the
    # heavy frame slightly so the HEAVY skeleton moves too
    moved = _rotate_methyl(moved, 60.0, methyl=(5, 6, 7))
    moved[1] = moved[1] + np.array([0.4, 0.0, 0.0])
    verdict = btp.validate_candidate_start(syms, xyz, moved, adj)
    assert verdict["accepted"] is True, verdict
    assert verdict["reason"] == "ok_heavy_fragment", verdict


# ---- the call chain: a bad geometry must not reach a package ---------------

def test_a_legal_non_rigid_ring_change_is_accepted(btp):
    """Positive, explicitly named by the plan: a ring PUCKER is a real start.

    A pucker moves heavy atoms (>1e-5 A) while every bond survives, so it must be
    accepted as a heavy-fragment change -- the case that distinguishes "ring
    conformational search" from "ring broken".
    """
    # a 5-membered ring: C0-C1-O2-C3-O4-C0
    syms = ["C", "C", "O", "C", "O"]
    coords = np.array([[1.50, 0.0, 0.0], [0.47, 1.42, 0.0], [-0.95, 0.88, 0.0],
                       [-0.95, -0.88, 0.0], [0.47, -1.42, 0.0]])
    adj = _adjacency(syms, coords, cutoff=1.8)
    assert len(adj[0]) == 2 and len(adj[2]) == 2, "the ring must be a closed 5-cycle"
    pucker = coords.copy()
    pucker[3] = pucker[3] + np.array([0.0, 0.0, 0.25])   # C3 out of plane
    verdict = btp.validate_candidate_start(syms, coords, pucker, adj)
    assert verdict["accepted"] is True, verdict
    assert verdict["reason"] == "ok_heavy_fragment", verdict
    assert verdict["detail"]["heavy_pair_change_a"] > 1e-5


def _staged_package(member):
    """A tmp source package holding just that member's task (job.inp + geom.xyz).

    ``_repair_member`` reads the previous task's ``job.inp`` (derivative policy)
    and ``geom.xyz`` (previous hash), so a real task directory must be present.
    """
    import shutil
    import tempfile
    root = Path(tempfile.mkdtemp())
    pkg = root / "hpc_torsion_probe_v2_realfragment"
    (pkg / "tasks" / member["name"]).mkdir(parents=True)
    src_task = (V2 / "tasks" / member["name"]
                / ("%s__%s" % (member["slot"], member["seed"])))
    shutil.copytree(src_task, pkg / "tasks" / member["name"] / src_task.name)
    return pkg


def test_the_repair_path_calls_the_gate(btp, monkeypatch):
    """A spy proves production packaging actually invokes the gate."""
    called = []
    real = btp.validate_candidate_start

    def spy(*a, **kw):
        called.append(kw.get("rotated_bond"))
        return real(*a, **kw)

    monkeypatch.setattr(btp, "validate_candidate_start", spy)
    _syms, _xyz, _adj, _singles, mem = _real_v2(btp)
    record = btp._repair_member(_staged_package(mem), dict(mem), [])
    assert called, "the packaging path must call the gate"
    assert record["audit"]["gate_reason"] == "ok_methyl_rotor"


def test_a_bad_rotation_cannot_reach_the_manifest(btp, monkeypatch):
    """Stub the rotation to move one H 100 A: the path must refuse it."""
    syms, _xyz, _adj, _singles, mem = _real_v2(btp)

    def bad_rotation(coords, dihedral, adjacency, *, single_bonds, degrees):
        out = np.asarray(coords, dtype=float).copy()
        h = next(i for i, s in enumerate(syms) if s == "H")
        out[h] = out[h] + np.array([100.0, 0.0, 0.0])
        return out, {"moving_indices": [h], "pair_distance_change_a": 100.0}

    monkeypatch.setattr(btp, "rotate_fragment", bad_rotation)
    with pytest.raises(ValueError) as exc:
        btp._repair_member(_staged_package(mem), dict(mem), [])
    assert "ring_broken" in str(exc.value), str(exc.value)


def test_the_second_packaging_path_also_calls_the_gate(btp, monkeypatch, tmp_path):
    """_build_state is the other place candidate geometry reaches disk."""
    called = []
    real = btp.validate_candidate_start

    def spy(*a, **kw):
        called.append(1)
        return real(*a, **kw)

    monkeypatch.setattr(btp, "validate_candidate_start", spy)
    monkeypatch.setattr(btp, "OUT_PKG", tmp_path / "pkg")
    (tmp_path / "pkg").mkdir()
    rows = btp._build_state("AN", "M_plus", 1, 1)
    assert called, "the second path must call the gate for a state with torsions"
    assert called.count(1) >= len(rows)
