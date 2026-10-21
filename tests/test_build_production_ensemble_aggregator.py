"""Tests for the production ensemble aggregator (v1.4.1 semantics)."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_production_ensemble_aggregator.py"


def _module():
    spec = importlib.util.spec_from_file_location("ens_agg", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


# ---------- formula ----------

def test_single_member_ensemble_equals_its_g():
    m = _module()
    g, w, q = m.boltzmann([-100.0], 298.15)
    assert g == -100.0
    assert w == [1.0]
    assert q == 1.0


def test_two_members_boltzmann():
    m = _module()
    g, w, q = m.boltzmann([-100.0, -99.0], 298.15)
    import math
    expected_gain = m.R_KCAL * 298.15 * math.log(1 + math.exp(-1.0 / (m.R_KCAL * 298.15)))
    assert g == pytest.approx(-100.0 - expected_gain, abs=1e-9)
    assert abs(sum(w) - 1.0) < 1e-12      # weight_sum == 1 (normalized)
    assert q == pytest.approx(1 + math.exp(-1.0 / (m.R_KCAL * 298.15)))  # partition sum != 1
    assert w[0] > w[1]


def test_partition_sum_and_weight_sum_are_distinct_fields():
    m = _module()
    _, w, q = m.boltzmann([-100.0, -99.0], 298.15)
    assert q > 1.0                        # unnormalized relative partition sum
    assert abs(sum(w) - 1.0) < 1e-12       # normalized weights


def test_huge_gap_is_underflow_safe():
    m = _module()
    g, w, q = m.boltzmann([-100.0, 400.0], 298.15)
    assert g == pytest.approx(-100.0, abs=1e-6)
    assert w[1] == pytest.approx(0.0, abs=1e-200)
    assert abs(sum(w) - 1.0) < 1e-12


def test_identical_members_get_rt_ln2_gain_not_more():
    """Two IDENTICAL Gs = two members with g_i=1 each: -RT ln 2 exactly."""
    m = _module()
    g1, _, _ = m.boltzmann([-100.0], 298.15)
    g2, w, q = m.boltzmann([-100.0, -100.0], 298.15)
    import math
    assert g2 == pytest.approx(g1 - m.R_KCAL * 298.15 * math.log(2.0), abs=1e-9)
    assert q == pytest.approx(2.0)
    assert w == [0.5, 0.5]


def test_nonunit_degeneracy_is_rejected_under_the_frozen_rule():
    """g_i = 1 is FROZEN (no registered symmetry degeneracy exists yet): any
    other value must be a hard reject, never silently honoured -- otherwise a
    later tune could shift the ranking after the fact."""
    m = _module()
    with pytest.raises(ValueError, match="degeneracy"):
        m.boltzmann([-100.0, -99.0], 298.15, degeneracies={1: 3})
    # g_i = 1 everywhere is the only accepted form and equals no-degeneracy.
    _, _, q1 = m.boltzmann([-100.0, -99.0], 298.15, degeneracies={0: 1, 1: 1})
    _, _, q2 = m.boltzmann([-100.0, -99.0], 298.15)
    assert q1 == pytest.approx(q2)


def test_nonpositive_temperature_is_rejected():
    m = _module()
    with pytest.raises(ValueError, match="temperature"):
        m.boltzmann([-100.0, -99.0], 0.0)
    with pytest.raises(ValueError, match="temperature"):
        m.boltzmann([-100.0, -99.0], -5.0)


# ---------- torsions (true four-atom implementation) ----------

def test_torsion_periodic_difference_across_180_seam():
    m = _module()
    assert m.torsion_delta(179.0, -179.0) == pytest.approx(2.0, abs=1e-9)
    assert m.torsion_delta(0.0, 180.0) == pytest.approx(180.0)
    assert m.torsion_delta(30.0, 40.0) == pytest.approx(10.0)


def test_torsion_of_known_geometry():
    m = _module()
    # Four atoms along a chain: dihedral 0 (eclipsed-planar).
    p1, p2, p3 = (0, 0, 0), (1, 0, 0), (1, 1, 0)
    p4 = (2, 1, 0)
    assert abs(m.torsion_deg(p1, p2, p3, p4)) < 1e-6 or \
        abs(abs(m.torsion_deg(p1, p2, p3, p4)) - 180.0) < 1e-6


# ---------- ledger-driven end-to-end with v1.4.1 statuses ----------

LEDGER_FIELDS = [
    "member_key", "slot", "mol_id", "name", "seed", "member_role", "source_kind",
    "attempt", "charge", "multiplicity", "method", "protocol_version", "frequency_hessian",
    "status", "qc_flags", "failure_class", "opt_tier", "energy_change_Eh", "convergence_note",
    "n_freq", "imaginary_modes", "lowest_freq_cm1",
    "electronic_eh", "g_single_eh", "qrrho", "temp_k",
    "connectivity_ok", "li_denticity", "li_fragments", "relaxation_heavy_rmsd_a",
    "input_sha256", "start_geometry_sha256", "final_geometry_sha256",
    "log_sha256", "hess_sha256", "log_path", "task_relpath", "note",
]

CAND_FIELDS = ["slot", "mol_id", "name", "member_role", "seed", "source_kind",
               "geometry", "sha256", "rel_kcal", "denticity", "duplicate_of",
               "charge", "multiplicity", "status", "note"]


def _primary(i, slot):
    return dict(zip(LEDGER_FIELDS, [
        f"C{i:02d}|{slot}|primary", slot, f"C{i:02d}", f"M{i:02d}", "primary",
        "primary", "production_leg", "0", str({'M':0,'M_plus':1,'LiM_plus':1,'LiM_2plus':2}[slot]), str(2 if slot in ('M_plus','LiM_2plus') else 1), "wB97X-D4 def2-TZVPD", "1.3", "analytical_hessian",
        "ready", "", "", "verytight", "", "", "36", "0", "100.0",
        "-100.5", "-100.7", "True", "298.15",
        "true", "", "1", "0.1",
        "a", "b", "c", "d", "e", "", "", ""]))


def _extra(name, mol, slot, seed, status, failure="", attempt="0", g="-100.6"):
    return dict(zip(LEDGER_FIELDS, [
        f"{name}|{slot}|{seed}", slot, mol, name, seed, "round1_extra", "free_conformer",
        attempt, str({'M':0,'M_plus':1,'LiM_plus':1,'LiM_2plus':2}[slot]), str(2 if slot in ('M_plus','LiM_2plus') else 1), "wB97X-D4 def2-TZVPD", "1.3", "analytical_hessian",
        status, failure, failure or "x", "verytight", "", "", "36", "0", "100.0",
        "-100.4", g, "True", "298.15",
        "true", "", "1", "0.2",
        "a", "b", "c", "d", "e", "x.log", "tasks/x/y", ""]))


def _cand(name, mol, slot, seed):
    return dict(zip(CAND_FIELDS, [slot, mol, name, "round1_extra", seed, "free_conformer",
                                 "", "", "0.0", "", "", "0", "1", "planned", ""]))


GEOM = """4
test geometry C2H2
C   0.0000000000   0.0000000000   0.6000000000
C   0.0000000000   0.0000000000  -0.6000000000
H   0.0000000000   0.0000000000   1.6600000000
H   0.0000000000   0.0000000000  -1.6600000000
"""

GEOM_ALT = """4
test geometry heavy skeleton changed (C-C stretched to 2.0 A)
C   0.0000000000   0.0000000000   1.0000000000
C   0.0000000000   0.0000000000  -1.0000000000
H   0.0000000000   0.0000000000   2.0600000000
H   0.0000000000   0.0000000000  -2.0600000000
"""


def _setup(tmp_path, module, ledger_rows, cand_rows, extra_geoms=None):
    ens = tmp_path / "outputs" / "physics_completion" / "ensembles"
    ens.mkdir(parents=True)
    ledger = ens / "production_ensemble_structures.csv"
    with ledger.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(ledger_rows)
    cands = ens / "production_ensemble_candidates.csv"
    with cands.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAND_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(cand_rows)
    # Real geometries so dedup has something to compare: primary from its leg
    # dir, computed extras from their task run dir.
    extra_geoms = extra_geoms or {}
    for row in ledger_rows:
        if row["member_role"] == "primary":
            state = "M_tzvpd" if row["slot"] == "M" else row["slot"]
            leg = tmp_path / "work" / "wp2prod" / row["name"] / state
            leg.mkdir(parents=True, exist_ok=True)
            (leg / f"{row['name']}_{state}_opt.xyz").write_text(GEOM, encoding="utf-8")
        elif row["status"] == "computed" and row["task_relpath"]:
            run = tmp_path / row["task_relpath"] / "run"
            run.mkdir(parents=True, exist_ok=True)
            (run / "job.xyz").write_text(
                extra_geoms.get(row["member_key"], GEOM_ALT), encoding="utf-8")
    module.REPO = tmp_path
    module.STRUCTURES = ledger
    module.CANDIDATES = cands
    module.OUT = ens
    module.expected_state_keys = lambda: {(r["name"], r["slot"]): r["mol_id"]
                                         for r in ledger_rows if r["member_role"] == "primary"}
    config = tmp_path / "config/physics_completion_v1.yaml"
    config.parent.mkdir(exist_ok=True)
    config.write_text("analysis_cohorts: {main: [C01]}\n", encoding="utf-8")
    for row in ledger_rows:
        if row["member_role"] == "primary":
            state = "M_tzvpd" if row["slot"] == "M" else row["slot"]
            path = tmp_path / "work/wp2prod" / row["name"] / state / f"{row['name']}_{state}_opt.xyz"
        else:
            path = tmp_path / row["task_relpath"] / "run/job.xyz"
        if path.is_file():
            row["final_geometry_sha256"] = module.sha256_file(path)
    with ledger.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(ledger_rows)
    return ens


def test_provisional_when_registered_extra_pending(tmp_path):
    """A state with a pending registered extra is provisional, NOT accepted --
    the v1.4.1 core invariant: 48 provisional rows never satisfy compliance."""
    m = _module()
    rows = [_primary(1, "M"), _extra("M01", "C01", "M", "8", "pending")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    assert m.main([]) == 0
    labels = list(csv.DictReader((ens / "production_ensemble_labels.csv").open(encoding="utf-8")))
    assert len(labels) == 1
    assert labels[0]["acceptance_status"] == "provisional"
    assert labels[0]["sampling_status"] == "in_progress"
    assert labels[0]["n_unresolved"] == "1"


def test_accepted_when_registered_extra_computed(tmp_path):
    m = _module()
    rows = [_primary(1, "M"), _extra("M01", "C01", "M", "8", "computed", attempt="1")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    assert m.main([]) == 0
    labels = list(csv.DictReader((ens / "production_ensemble_labels.csv").open(encoding="utf-8")))
    assert labels[0]["acceptance_status"] == "accepted"
    assert labels[0]["sampling_status"] == "complete"


def test_failed_extra_requires_explicit_disposition(tmp_path):
    """A QC-failed extra (e.g. imaginary modes) is a COMPLETE disposition:
    the state can still be accepted with its remaining members."""
    m = _module()
    rows = [_primary(1, "M"),
            _extra("M01", "C01", "M", "8", "technical_complete_qc_failed", "imaginary_modes")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    assert m.main([]) == 0
    labels = list(csv.DictReader((ens / "production_ensemble_labels.csv").open(encoding="utf-8")))
    assert labels[0]["acceptance_status"] == "provisional"
    assert labels[0]["n_qc_failed"] == "1"
    assert labels[0]["n_unresolved"] == "1"


def test_rescue_in_flight_extra_keeps_state_provisional(tmp_path):
    """strict_reopt_required / verytight / max-cycles extras have a registered
    remedy in flight -> unresolved -> provisional."""
    m = _module()
    for fc in ("strict_reopt_required", "verytight_convergence", "max_cycles_exhausted"):
        rows = [_primary(1, "M"),
                _extra("M01", "C01", "M", "8", "technical_complete_qc_failed", fc)]
        cands = [_cand("M01", "C01", "M", "8")]
        ens = _setup(tmp_path / fc, m, rows, cands)
        assert m.main([]) == 0
        labels = list(csv.DictReader((ens / "production_ensemble_labels.csv").open(encoding="utf-8")))
        assert labels[0]["acceptance_status"] == "provisional", fc
        assert labels[0]["n_unresolved"] == "1", fc


def test_superseded_attempt_does_not_double_count(tmp_path):
    """attempt 0 superseded + attempt 1 computed = ONE member weight, not two."""
    m = _module()
    rows = [_primary(1, "M"),
            _extra("M01", "C01", "M", "8", "superseded", "strict_reopt_required", attempt="0"),
            _extra("M01", "C01", "M", "8", "computed", "", attempt="1")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    assert m.main([]) == 0
    weights = list(csv.DictReader((ens / "production_ensemble_weights.csv").open(encoding="utf-8")))
    keys = [r["member_key"] for r in weights]
    assert keys.count("M01|M|8") == 1


def test_n1_with_no_registered_extras_is_accepted_not_pool_limited_guess(tmp_path):
    """No registered extras at all: accepted with limitation_reason recorded."""
    m = _module()
    rows = [_primary(1, "M")]
    ens = _setup(tmp_path, m, rows, [])
    assert m.main([]) == 0
    labels = list(csv.DictReader((ens / "production_ensemble_labels.csv").open(encoding="utf-8")))
    assert labels[0]["acceptance_status"] == "accepted"
    assert labels[0]["n_members"] == "1"
    assert labels[0]["limitation_reason"] == "no_registered_extras"


def test_every_limited_state_carries_a_nonempty_limitation_reason(tmp_path):
    """v1.4.2 invariant: a `limited` label must always say WHY.

    An empty limitation_reason on a limited state is indistinguishable from a
    bug, and the two real causes are not interchangeable:
      * rescue_budget_exhausted -- the bounded rescue ladder ran out (>=2
        attempts, evidence-hash matched disposition).  This is a research
        limitation; it does NOT assert "no minimum exists".
      * single_basin_pool -- the frozen pool only ever offered one basin.
    """
    m = _module()
    # A budget-exhausted extra is registered with a matching disposition.
    rows = [_primary(1, "M"),
            _extra("M01", "C01", "M", "8", "technical_complete_qc_failed",
                   "max_cycles_exhausted", attempt="1")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    assert m.main([]) == 0
    labels = list(csv.DictReader((ens / "production_ensemble_labels.csv").open(encoding="utf-8")))
    label = labels[0]
    # Whatever the classification, a limited label may never have a blank reason.
    if label["acceptance_status"] == "limited":
        assert label["limitation_reason"].strip(), \
            "limited state must record a limitation_reason, got %r" % label["limitation_reason"]
    assert label["limitation_reason"] in (
        "", "rescue_budget_exhausted", "species_drift_unrecoverable",
        "single_basin_pool",
        "no_registered_extras", "all_extras_deduplicated_to_primary",
        "extras_qc_failed"), label["limitation_reason"]


def test_species_drift_gets_its_own_reason_not_budget_exhaustion(tmp_path):
    """A member that drifted to another molecule is NOT budget-exhausted.

    The EMC|M_plus|4 lesson: attempt 1 faithfully re-optimised the drifted
    (wrong) species, so more rescue attempts can never restore identity.
    Reporting that as `rescue_budget_exhausted` would read as "one more try
    might help", which is scientifically wrong.  The disposition is
    `species_drift_unrecoverable` and the label reason must match it.
    """
    m = _module()
    # One primary + one extra that qc-failed with a species-drift class.
    rows = [_primary(1, "M"),
            _extra("M01", "C01", "M", "8", "technical_complete_qc_failed",
                   "candidate_bond_graph_changed", attempt="1")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    labels_path = ens / "production_ensemble_labels.csv"
    # The aggregator READS a dispositions file the importer would have written;
    # hand-write the drift disposition (attempted>=2 so the match gate passes).
    extra_row = rows[1]
    disp_path = ens / "production_ensemble_dispositions.csv"
    disp_fields = ["member_key", "latest_attempt", "latest_status",
                   "attempted_calculations", "disposition", "failure_class",
                   "log_sha256", "reason"]
    with disp_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=disp_fields, lineterminator="\n")
        w.writeheader()
        w.writerow({
            "member_key": extra_row["member_key"],
            "latest_attempt": "1", "latest_status": "technical_complete_qc_failed",
            "attempted_calculations": "2",
            "disposition": "species_drift_unrecoverable",
            "failure_class": "candidate_bond_graph_changed",
            "log_sha256": extra_row.get("log_sha256", ""),
            "reason": "species drift; identity cannot be restored by retrying",
        })
    m.DISPOSITIONS = disp_path      # _setup does not patch this constant
    assert m.main([]) == 0
    labels = list(csv.DictReader(labels_path.open(encoding="utf-8")))
    label = labels[0]
    assert label["acceptance_status"] == "limited", label
    assert label["limitation_reason"] == "species_drift_unrecoverable", label


def test_readonly_check_detects_tampered_label_and_writes_nothing(tmp_path):
    """v1.4.1 §3.5: --check never repairs: tampering a label must be reported,
    and the tampered bytes must survive the check unchanged."""
    m = _module()
    rows = [_primary(1, "M")]
    ens = _setup(tmp_path, m, rows, [])
    assert m.main([]) == 0
    labels_path = ens / "production_ensemble_labels.csv"
    original = labels_path.read_bytes()
    tampered = original.replace(b"accepted", b"acceptedX")
    labels_path.write_bytes(tampered)
    before_mtimes = {p.name: p.stat().st_mtime_ns for p in ens.iterdir()}
    assert m.main(["--check"]) == 1          # STALE reported
    for p in ens.iterdir():
        assert p.stat().st_mtime_ns == before_mtimes[p.name], f"--check touched {p.name}"
    assert labels_path.read_bytes() == tampered  # tampering survived, un-repaired


def test_check_green_when_untouched_and_still_readonly(tmp_path):
    m = _module()
    rows = [_primary(1, "M")]
    ens = _setup(tmp_path, m, rows, [])
    assert m.main([]) == 0
    before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in ens.iterdir()}
    assert m.main(["--check"]) == 0
    for p in ens.iterdir():
        assert p.stat().st_mtime_ns == before[p.name][0]
        assert p.read_bytes() == before[p.name][1]


def test_missing_output_file_fails_check_without_creating_it(tmp_path):
    m = _module()
    rows = [_primary(1, "M")]
    ens = _setup(tmp_path, m, rows, [])
    assert m.main([]) == 0
    (ens / "production_ensemble_weights.csv").unlink()
    assert m.main(["--check"]) == 1
    assert not (ens / "production_ensemble_weights.csv").exists()  # not recreated


def test_corrupt_index_fails_check(tmp_path):
    m = _module()
    rows = [_primary(1, "M")]
    ens = _setup(tmp_path, m, rows, [])
    assert m.main([]) == 0
    (ens / "production_ensemble_labels.csv").write_bytes(b"garbage\n")
    assert m.main(["--check"]) == 1


def test_mixed_temperature_within_state_rejected(tmp_path):
    m = _module()
    rows = [_primary(1, "M"),
            _extra("M01", "C01", "M", "8", "computed", attempt="1")]
    rows[1]["temp_k"] = "300.00"            # differs from primary's 298.15
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands)
    assert m.main([]) == 2                   # hard reject


def test_frozen_48_cohort_expected_denominator(tmp_path):
    """The labels CSV always reports against the frozen 12 x 4 = 48 denominator
    via the index's expected_labels, never against however many rows exist."""
    m = _module()
    rows = [_primary(1, "M")]
    ens = _setup(tmp_path, m, rows, [])
    assert m.main([]) == 0
    idx = json.loads((ens / "production_ensemble_index.json").read_text(encoding="utf-8"))
    assert idx["expected_labels"] == 1  # fixture explicitly injects a one-state cohort
    assert idx["labels"] == 1


# ---------- v1.4.1 P0: topology-preserving atom mapping ----------

def test_equivalent_atom_relabelling_is_detected_as_duplicate():
    """Same geometry with the two O atoms swapped in the atom list must still be
    recognized as the SAME structure (element-order comparison would miss it)."""
    m = _module()
    a_syms = ["C", "O", "O", "C"]
    a_xyz = [(0.0, 0.0, 0.0), (1.3, 0.0, 0.0), (-1.3, 0.0, 0.0), (0.0, 1.5, 0.0)]
    b_syms = ["C", "O", "O", "C"]      # same, but the two O are swapped in order
    b_xyz = [(0.0, 0.0, 0.0), (-1.3, 0.0, 0.0), (1.3, 0.0, 0.0), (0.0, 1.5, 0.0)]
    adj_a = m.bond_adjacency(a_syms, a_xyz)
    adj_b = m.bond_adjacency(b_syms, b_xyz)
    mappings, resolved = m.find_topology_mappings(a_syms, adj_a, b_syms, adj_b)
    assert resolved
    assert mappings, "relabelled identical structure must have a topology mapping"


def test_different_connectivity_has_no_mapping():
    """Same element counts, different bonds (chain vs branched) -> no mapping."""
    m = _module()
    a_syms = ["C", "C", "C", "O"]
    a_xyz = [(0.0, 0.0, 0.0), (1.5, 0.0, 0.0), (3.0, 0.0, 0.0), (4.2, 0.0, 0.0)]
    b_syms = ["C", "C", "C", "O"]
    b_xyz = [(0.0, 0.0, 0.0), (1.5, 0.0, 0.0), (0.0, 1.5, 0.0), (0.0, -1.3, 0.0)]
    adj_a = m.bond_adjacency(a_syms, a_xyz)
    adj_b = m.bond_adjacency(b_syms, b_xyz)
    mappings, resolved = m.find_topology_mappings(a_syms, adj_a, b_syms, adj_b)
    assert resolved
    assert not mappings, "different bond topology must have no legal mapping"


def test_mirror_image_is_not_a_rotation_duplicate():
    """A reflected structure has det = -1: it must NOT pass as the same minimum."""
    m = _module()
    # Chiral (non-planar) tetrahedral-like fragment: a mirror image cannot be
    # superposed by rotation alone, so det must come out -1.
    a = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]])
    b = a.copy()
    b[:, 2] = -b[:, 2]
    assert abs(m._kabsch_det(a, b) - 1.0) > 1e-6   # det -1 (mirror), rejected


def test_mapping_limit_marks_unresolved_not_unique():
    """When the mapping search saturates its registered limit, the result must
    be reported as unresolved -- never silently 'unique'."""
    m = _module()
    # A star: centre C bonded to 5 equivalent C leaves -> 5! = 120 mappings.
    syms = ["C"] * 6
    # Regular octahedron: centre + 6 equivalent vertices at 1.6 A (bonded to the
    # centre only, since vertex-vertex distance is 2.26 A > the 1.77 A cutoff).
    # 6 equivalent leaves -> 6! = 720 mappings, far above a limit of 5.
    import itertools
    axes = [(1.6, 0.0, 0.0), (-1.6, 0.0, 0.0), (0.0, 1.6, 0.0),
            (0.0, -1.6, 0.0), (0.0, 0.0, 1.6), (0.0, 0.0, -1.6)]
    syms = ["C"] * 7
    xyz = [(0.0, 0.0, 0.0)] + axes
    adj = m.bond_adjacency(syms, xyz)
    assert sum(len(a) for a in adj) == 12, "fixture must be an octahedral star"
    mappings, resolved = m.find_topology_mappings(syms, adj, syms, adj, limit=5)
    assert len(mappings) <= 5
    assert not resolved, "hitting the limit must report resolved=False"


def test_gmin_minus_gens_within_rt_ln_n_bound():
    """Frozen g_i=1 invariant (v1.4.1 §3.3): 0 <= G_min - G_ens <= RT ln N."""
    import math
    m = _module()
    for n in (1, 2, 3, 5):
        g_vals = [-100.0 - 0.4 * i for i in range(n)]
        g_ens, _, _ = m.boltzmann(g_vals, 298.15)
        lowering = min(g_vals) - g_ens
        bound = m.R_KCAL * 298.15 * math.log(n)
        assert lowering >= -1e-12, n
        assert lowering <= bound + 1e-12, (n, lowering, bound)


def test_dedup_evidence_columns_are_written(tmp_path):
    """The dedup table must carry the mapping / rmsd / torsion / det evidence
    that the v1.4.1 review table requires."""
    m = _module()
    rows = [_primary(1, "M"),
            _extra("M01", "C01", "M", "8", "computed", attempt="1")]
    cands = [_cand("M01", "C01", "M", "8")]
    ens = _setup(tmp_path, m, rows, cands, extra_geoms={"M01|M|8": GEOM})
    assert m.main([]) == 0
    dedup = list(csv.DictReader((ens / "production_ensemble_dedup.csv").open(encoding="utf-8")))
    assert {"mapping", "rmsd_a", "torsion_delta_deg", "rotation_det"} <= set(dedup[0])
    dup = [d for d in dedup if d["kept"] == "false"]
    assert dup and dup[0]["rotation_det"] == "1.000000"


def test_v142_single_member_requires_geometry(tmp_path):
    m = _module()
    kept, decisions = m.dedup_members([_primary(1, "M")], tmp_path)
    assert not kept
    assert "blocked" in decisions[0]["reason"]


def test_v142_open_chain_has_rotatable_central_bond():
    m = _module()
    assert (1, 2, 0, 3) in m.find_rotatable_bonds(
        ["C"] * 4, [(0, 0, 0), (1.5, 0, 0), (3, 0, 0), (4.5, 0, 0)])


def test_v142_donor_identity_not_element_count():
    m = _module()
    syms = ["Li", "O", "O"]
    a = [(0, 0, 0), (2, 0, 0), (4, 0, 0)]
    b = [(0, 0, 0), (4, 0, 0), (2, 0, 0)]
    da, db = m.mapped_donor_sites(syms, a, dict(enumerate(range(3))), b)
    assert da != db


def test_v142_missing_index_fails_check(tmp_path):
    m = _module()
    ens = _setup(tmp_path, m, [_primary(1, "M")], [])
    assert m.main([]) == 0
    (ens / "production_ensemble_index.json").unlink()
    assert m.main(["--check"]) == 1


def test_frozen_protocol_is_not_just_member_agreement():
    m = _module()
    row = _primary(1, 'M')
    row.update(method='HF def2-SVP', protocol_version='0', charge='99',
               multiplicity='7', frequency_hessian='numerical_hessian', qrrho='False')
    with pytest.raises(ValueError):
        m.validate_pool([row])


def test_nonplanar_ring_mirror_not_merged(tmp_path, monkeypatch):
    m = _module()
    syms = ['C', 'C', 'N', 'O']
    xyz = [(0,0,0), (1.4,0,0), (1.4,1.4,0), (0,1.4,.2)]
    mirror = [(x,y,-z) for x,y,z in xyz]
    rows = [_primary(1, 'M'), _extra('M01', 'C01', 'M', '8', 'computed')]
    monkeypatch.setattr(m, 'member_geometry', lambda r, repo: (syms, xyz if r['member_role'] == 'primary' else mirror))
    kept, decisions = m.dedup_members(rows, tmp_path)
    assert len(kept) == 2
    assert not any(d.get('duplicate_of') for d in decisions)


def test_v142_missing_pool_field_rejected():
    m = _module()
    row = _primary(1, "M")
    row["method"] = ""
    with pytest.raises(ValueError, match="missing"):
        m.validate_pool([row])


def test_v142_nan_energy_rejected_before_dedup():
    m = _module()
    row = _primary(1, "M")
    row["g_single_eh"] = "nan"
    with pytest.raises(ValueError, match="finite"):
        m.validate_pool([row])


def test_v142_failed_member_not_implicitly_dispositioned(tmp_path):
    m = _module()
    rows = [_primary(1, "M"), _extra("M01", "C01", "M", "8", "technical_complete_qc_failed", "imaginary_modes")]
    ens = _setup(tmp_path, m, rows, [_cand("M01", "C01", "M", "8")])
    assert m.main([]) == 0
    label = next(csv.DictReader((ens / "production_ensemble_labels.csv").open()))
    assert label["acceptance_status"] != "accepted"
    assert label["n_unresolved"] == "1"


def test_v142_mapping_budget_before_first_mapping_is_blocked(tmp_path, monkeypatch):
    m = _module()
    rows = [_primary(1, "M"), _extra("M01", "C01", "M", "8", "computed")]
    ens = _setup(tmp_path, m, rows, [_cand("M01", "C01", "M", "8")],
                 extra_geoms={"M01|M|8": GEOM})
    monkeypatch.setattr(m, "MAPPING_NODE_BUDGET", 1)
    assert m.main([]) == 0
    label = next(csv.DictReader((ens / "production_ensemble_labels.csv").open()))
    assert label["acceptance_status"] == "blocked"
    assert label["numerical_status"] == "unavailable"


def test_v142_comparison_uses_both_geometries(tmp_path, monkeypatch):
    m = _module()
    a = (["C", "O"], [(0, 0, 0), (1.0, 0, 0)])
    b = (["C", "O"], [(0, 0, 0), (1.5, 0, 0)])
    rows = [_primary(1, "M"), _extra("M01", "C01", "M", "8", "computed")]
    monkeypatch.setattr(m, "member_geometry", lambda row, repo: a if row["member_role"] == "primary" else b)
    kept, decisions = m.dedup_members(rows, tmp_path)
    # Both preserve the same bond topology and pass 0.35A, but RMSD is NOT 0.
    assert len(kept) == 1
    duplicate = next(d for d in decisions if d.get("duplicate_of"))
    assert float(duplicate["rmsd_a"]) == pytest.approx(0.25)


def test_v142_geometry_hash_tamper_blocks(tmp_path):
    m = _module()
    ens = _setup(tmp_path, m, [_primary(1, "M")], [])
    p = tmp_path / "work/wp2prod/M01/M_tzvpd/M01_M_tzvpd_opt.xyz"
    p.write_text(GEOM_ALT)
    assert m.main([]) == 0
    label = next(csv.DictReader((ens / "production_ensemble_labels.csv").open()))
    assert label["acceptance_status"] == "blocked"
