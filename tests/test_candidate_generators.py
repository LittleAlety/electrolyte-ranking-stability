"""P3: the two legal generators and the gate-first selector.

Design rules pinned here:

* every generated candidate goes through ``validate_candidate_start`` -- the
  generators never bypass the gate;
* dedup uses ``prior_starts`` (measured: the 7 registered torsions collapse to 2-3
  distinct operations, so the duplicates must be refused as ``equivalent_start``);
* an over-large ring pucker that would break a bond is REFUSED, not silently kept;
* a Li-position probe is only legal when DECLARED, and is classified as its own
  kind (never as a heavy-fragment torsion);
* every accepted record carries the evidence P3 demands.

Regression: ``_shortest_cycle_through`` must not put its None sentinel into the
path (measured TypeError: None vs int).
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

import pytest

# --- declared dependency on the gitignored `work/` layer (step 12) -----------
# A clean clone has no `work/`: raw ledgers, logs and geometries live there and
# are 12 GB, so they are not tracked.  The builders REFUSE loudly when it is
# missing (pinned by test_clean_clone_dependencies.py); a test that consumes a
# dev-tree fixture therefore declares the need and skips WITH A REASON instead
# of failing -- and never silently passes.
pytestmark = pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "work" / "wp2prod").is_dir(),
    reason="the machine-local work/wp2prod evidence layer (gitignored) is absent in this checkout; "
           "the builders' loud refusal is pinned by test_clean_clone_dependencies.py",
)
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PROD / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def btp():
    return _load("build_torsion_probe_package")


@pytest.fixture(scope="module")
def reg():
    return _load("build_torsion_registry")


def _state(btp, reg, name, state):
    geom = reg._primary_geometry(name, state)
    syms, coords = reg._read_xyz(geom)
    adj, singles = btp._topology_for_member(name, syms)
    return syms, np.asarray(coords, dtype=float), adj, singles, reg._sha(geom)


# ---- ring finding ---------------------------------------------------------

def test_ring_atoms_finds_the_five_ring_for_dol_and_ec(btp, reg):
    for name in ("DOL", "EC"):
        _s, _c, adj, _sg, _sha = _state(btp, reg, name, "LiM_2plus")
        rings = btp.ring_atoms(adj)
        assert rings, name
        assert any(len(r) == 5 for r in rings), (name, rings)


def test_ring_atoms_is_empty_for_the_acyclic_dmc_states(btp, reg):
    for state in ("M_plus", "LiM_2plus"):
        _s, _c, adj, _sg, _sha = _state(btp, reg, "DMC", state)
        assert btp.ring_atoms(adj) == [], state


def test_the_cycle_path_never_contains_the_none_sentinel(btp, reg):
    """Regression: the sentinel leaked into the path and made sorted() raise."""
    _s, _c, adj, _sg, _sha = _state(btp, reg, "DOL", "LiM_2plus")
    ring = btp.ring_atoms(adj)[0]
    assert all(isinstance(i, int) for i in ring), ring


# ---- ring pucker ---------------------------------------------------------

def test_a_small_ring_pucker_is_accepted_as_a_heavy_change(btp, reg):
    syms, coords, adj, singles, sha = _state(btp, reg, "DOL", "LiM_2plus")
    cands = [c for c in btp.ring_pucker_candidates(syms, coords, adj)
             if abs(c["amplitude_a"]) <= 0.40]
    out = btp.select_candidates(syms, coords, adj, cands,
                                registered_single_bonds=singles, source_sha256=sha)
    assert out["accepted"], out["refused"][:3]
    for rec in out["accepted"]:
        assert rec["probe_class"] == "heavy_fragment_torsion", rec
        assert rec["heavy_pair_change_a"] > 1e-5


def test_an_over_large_pucker_is_refused_as_ring_broken(btp, reg):
    """A deformation that breaks a bond is NOT a conformer."""
    syms, coords, adj, singles, sha = _state(btp, reg, "DOL", "LiM_2plus")
    big = [c for c in btp.ring_pucker_candidates(syms, coords, adj)
           if abs(c["amplitude_a"]) >= 0.80]
    assert big, "the fixture must contain over-large amplitudes"
    out = btp.select_candidates(syms, coords, adj, big,
                                registered_single_bonds=singles, source_sha256=sha)
    assert out["accepted"] == []
    assert {r["reason"] for r in out["refused"]} == {"ring_broken"}


# ---- Li coordination -----------------------------------------------------

def test_a_declared_li_probe_is_accepted_and_separately_classified(btp, reg):
    syms, coords, adj, singles, sha = _state(btp, reg, "DMC", "LiM_2plus")
    cands = btp.li_coordination_candidates(syms, coords, adj)
    assert cands, "the state must have a Li first shell"
    out = btp.select_candidates(syms, coords, adj, cands,
                                registered_single_bonds=singles, source_sha256=sha)
    assert out["accepted"], out["refused"][:3]
    for rec in out["accepted"]:
        assert rec["probe_class"] == "li_coordination_change", rec
        assert rec["source_shells"] is not None
    # and the selector must dedupe its own duplicates
    assert any(r["reason"] == "equivalent_start" for r in out["refused"])


def test_a_li_probe_needs_declaration_only_when_the_shell_changes(btp, reg):
    """Both directions, on the real state.

    A small Li shift that keeps the first-shell membership is NOT a coordination
    change (so it is accepted undeclared, as a Li position change).  A shift that
    DOES change the membership must be refused unless declared -- my first version
    of this test assumed every generated candidate changes the shell, which is
    false for the 0.15 A offset.
    """
    syms, coords, adj, singles, _sha = _state(btp, reg, "DMC", "LiM_2plus")
    cands = btp.li_coordination_candidates(syms, coords, adj)
    assert cands
    needs_declaration = []
    for c in cands:
        undeclared = btp.validate_candidate_start(syms, coords, c["coords"], adj,
                                                  declared_li_change=False)
        if undeclared["accepted"]:
            continue
        assert undeclared["reason"] == "li_coordination_changed", undeclared
        declared = btp.validate_candidate_start(syms, coords, c["coords"], adj,
                                                declared_li_change=True)
        assert declared["accepted"] is True, declared
        assert declared["reason"] == "ok_li_coordination_change", declared
        needs_declaration.append(c["offset_a"])
    assert needs_declaration, "some offset must actually change the first shell"


# ---- the selector --------------------------------------------------------

def test_the_selector_dedupes_the_registered_torsions(btp, reg):
    """7 registered torsions collapse to 2 distinct heavy operations + 1 rotor."""
    syms, coords, adj, singles, sha = _state(btp, reg, "DMC", "M_plus")
    import csv
    rows = list(csv.DictReader(
        (REPO / "outputs" / "physics_completion" / "recovery"
         / "torsion_freedom_registry.csv").open(encoding="utf-8")))
    cands = []
    for r in rows:
        if r["name"] != "DMC" or r["state"] != "M_plus" or r["detail"].count("-") < 3:
            continue
        dih = tuple(int(v) for v in r["detail"].split(" ")[0].split("-"))
        seed = "tors_" + "_".join(str(v) for v in dih)
        if seed in ("tors_6_0_1_2", "tors_7_0_1_2", "tors_8_0_1_2"):
            continue
        rot, _ = btp.rotate_fragment(coords, dih, adj, single_bonds=singles, degrees=60.0)
        cands.append({"kind": "torsion", "mode": seed, "coords": rot,
                      "moved_atoms": [], "rotated_bond": (dih[1], dih[2])})
    out = btp.select_candidates(syms, coords, adj, cands,
                                registered_single_bonds=singles, source_sha256=sha)
    heavy = [r for r in out["accepted"] if r["probe_class"] == "heavy_fragment_torsion"]
    rotors = [r for r in out["accepted"] if r["probe_class"] == "methyl_rotor"]
    assert len(heavy) == 2, [r["label"] for r in out["accepted"]]
    assert len(rotors) == 1
    assert any(r["reason"] == "equivalent_start" for r in out["refused"])


def test_every_accepted_record_carries_the_p3_evidence(btp, reg):
    syms, coords, adj, singles, sha = _state(btp, reg, "EC", "LiM_2plus")
    cands = btp.ring_pucker_candidates(syms, coords, adj)[:4]
    out = btp.select_candidates(syms, coords, adj, cands,
                                registered_single_bonds=singles, source_sha256=sha)
    assert out["accepted"]
    for rec in out["accepted"]:
        assert rec["source_geometry_sha256"] == sha
        assert rec["source_distance_fingerprint"]
        assert rec["result_distance_fingerprint"]
        assert rec["result_distance_fingerprint"] != rec["source_distance_fingerprint"]
        assert rec["moved_atoms"], rec
        assert rec["gate_reason"] == "ok_heavy_fragment"


def test_the_distance_fingerprint_is_rigid_motion_invariant(btp):
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.4, 0.2]])
    rotated = coords @ np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    shifted = rotated + np.array([9.0, -3.0, 2.0])
    assert (btp._distance_fingerprint(coords)
            == btp._distance_fingerprint(shifted))
    deformed = coords.copy()
    deformed[2] = deformed[2] + np.array([0.0, 0.0, 0.5])
    assert btp._distance_fingerprint(deformed) != btp._distance_fingerprint(coords)


def test_the_selection_cap_refuses_instead_of_dropping(btp, reg):
    """A cap may stop accepting, but no candidate may leave unaccounted.

    Regression: the loop used to ``break`` at the cap, so the remaining
    candidates appeared in NEITHER ``accepted`` nor ``refused`` and the
    selection ledger under-counted (measured 2026-10-24 by the independent
    challenger probe: max_keep=1 over 6 raw candidates gave accepted=1,
    refused=0 -- accountable 1/6).
    """
    syms, coords, adj, singles, sha = _state(btp, reg, "DOL", "LiM_2plus")
    cands = [c for c in btp.ring_pucker_candidates(syms, coords, adj)
             if abs(c["amplitude_a"]) <= 0.40]
    assert len(cands) > 1, "the fixture must offer more than one candidate"

    unbounded = btp.select_candidates(syms, coords, adj, cands,
                                      registered_single_bonds=singles, source_sha256=sha)
    assert len(unbounded["accepted"]) > 1, "the cap cannot bind on this fixture"

    capped = btp.select_candidates(syms, coords, adj, cands,
                                   registered_single_bonds=singles,
                                   source_sha256=sha, max_keep=1)
    assert len(capped["accepted"]) == 1
    accounted = len(capped["accepted"]) + len(capped["refused"])
    assert accounted == len(cands), (
        "the cap dropped %d of %d candidates without accounting"
        % (len(cands) - accounted, len(cands)))
    assert "max_keep_reached" in {r["reason"] for r in capped["refused"]}


def test_a_negative_rotation_axis_index_is_malformed_input(btp, reg):
    """A negative index would silently read an atom from the end of the list.

    Regression: only ``axis[1] >= len(symbols)`` was range-checked, so
    ``(-1, 1)`` fell through to the bond-registry gates instead of being
    refused as malformed (measured 2026-10-24 by the independent challenger
    probe: (-1, 1) returned missing_single_bond_registry).
    """
    syms, coords, adj, singles, sha = _state(btp, reg, "DMC", "LiM_2plus")
    for bad in ((-1, 1), (0, 99), (2, 2)):
        verdict = btp.validate_candidate_start(
            syms, coords, coords.copy(), adj, rotated_bond=bad)
        assert verdict["accepted"] is False, (bad, verdict)
        assert verdict["reason"] == "malformed_input", (bad, verdict)

    out = btp.select_candidates(
        syms, coords, adj,
        [{"kind": "torsion", "mode": "tors_0_1_2_3", "rotated_bond": (-1, 1),
          "coords": coords.copy(), "moved_atoms": []}],
        registered_single_bonds=singles, source_sha256=sha)
    assert out["accepted"] == []
    assert [r["reason"] for r in out["refused"]] == ["malformed_input"]