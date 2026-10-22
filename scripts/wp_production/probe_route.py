"""Per-state probe routing for the five limited states (plan v3.1 item 4).

The plan's draft B, verbatim in structure: the route proposes the NEXT PATH
ONLY -- it never submits a job and never raises acceptance.  Zero means "no
executable candidate within THIS preflight", never "physically no other
minimum exists".

Inputs are derived, never hand-filled:
* in_flight            -- any non-pending recovery/audit row of the state;
* identity_verified    -- the evidence table says verified for the state's
                           weighted members;
* unused_starts        -- frozen-pool conformers never run at production;
* eligible_torsions    -- registered free dihedrals (a torsion probe needs a
                           REGISTERED degree of freedom, not an invented one);
* new_li_motifs        -- unregistered coordination motifs from the motif
                           search (independent candidates only);
* independent_reproductions -- computed members that reproduced the known
                           minimum (single-basin review evidence).
"""
from __future__ import annotations


def probe_route(*, in_flight: bool, identity_verified: bool,
                unused_starts: list | None, eligible_torsions: list | None,
                new_li_motifs: list | None,
                independent_reproductions: list) -> str:
    """Propose the next path; submit nothing, raise nothing."""
    if in_flight:
        return "wait_existing_job"
    if not identity_verified:
        return "finish_identity_qc"

    if any(v is None for v in (unused_starts, eligible_torsions, new_li_motifs)):
        return "preflight_required"

    if unused_starts:
        return "draft_direct_dft_multistart"
    if new_li_motifs:
        return "draft_coordination_motif_probe"
    if eligible_torsions:
        return "draft_torsion_probe"
    if independent_reproductions:
        return "review_single_basin_evidence"

    return "limited_no_registered_executable_probe"
