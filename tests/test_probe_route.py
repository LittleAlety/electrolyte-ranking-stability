"""probe_route: pure-function tests for the five-state router (plan draft B)."""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "probe_route.py"


def _m():
    spec = importlib.util.spec_from_file_location("probe_route", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _base(**over):
    kw = dict(in_flight=False, identity_verified=True,
              unused_starts=None, eligible_torsions=None,
              new_li_motifs=None, independent_reproductions=[])
    kw.update(over)
    return kw


def test_in_flight_waits_for_existing_job():
    assert _m().probe_route(**_base(in_flight=True)) == "wait_existing_job"


def test_identity_gate_comes_before_everything():
    """No probe is drafted while a member still lacks identity evidence."""
    assert _m().probe_route(**_base(identity_verified=False,
                                    unused_starts=["c09"])) == "finish_identity_qc"


def test_unknown_preflight_is_refused():
    """None means 'not preflighted yet' -- the route demands the preflight."""
    assert _m().probe_route(**_base()) == "preflight_required"


def test_unused_starts_beat_torsions():
    """Direct DFT multi-start is preferred when real candidates exist."""
    assert _m().probe_route(**_base(unused_starts=["c05"], new_li_motifs=[],
                                    eligible_torsions=["dihedral_3"])) \
        == "draft_direct_dft_multistart"


def test_li_motifs_beat_torsions():
    assert _m().probe_route(**_base(unused_starts=[], new_li_motifs=["m12"],
                                    eligible_torsions=["dihedral_3"])) \
        == "draft_coordination_motif_probe"


def test_torsions_when_no_other_candidate():
    assert _m().probe_route(**_base(unused_starts=[], new_li_motifs=[],
                                    eligible_torsions=["dihedral_1"])) \
        == "draft_torsion_probe"


def test_reproductions_route_to_single_basin_review():
    assert _m().probe_route(**_base(unused_starts=[], new_li_motifs=[],
                                    eligible_torsions=[],
                                    independent_reproductions=["r2_c23"])) \
        == "review_single_basin_evidence"


def test_empty_preflight_reports_limited():
    """All-zero preflight = no executable candidate IN SCOPE, not physics."""
    assert _m().probe_route(**_base(unused_starts=[], eligible_torsions=[],
                                    new_li_motifs=[])) \
        == "limited_no_registered_executable_probe"
