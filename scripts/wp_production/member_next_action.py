"""Next-action dispositions for ensemble members: the frozen decision contract.

The rules here are the plan's three unmixable branches, written once as a pure
function and pinned by tests BEFORE being consumed by the importer:

* a technical segfault is NOT a science failure (no budget charge);
* species drift is never continued from the drifted frame (identity cannot be
  restored by retrying);
* an exhausted rescue budget is reported as ``limited`` with the reason, never
  phrased as "no minimum exists".

No QC threshold is read or relaxed here; the function only routes a QC verdict
that the importer has already produced.
"""
from __future__ import annotations

#: Flags that mean the optimised geometry is a DIFFERENT species than the
#: registered candidate.  Identity cannot be restored by any restart.
SPECIES_DRIFT_FLAGS = frozenset({
    "candidate_bond_graph_changed",
    "candidate_species_changed",
    "candidate_atom_order_changed",
})

#: Failure classes whose remedy is one strict re-optimisation from the leg's
#: OWN converged final geometry (the 2026-10-17 ruling).
STRICT_REOPT_CLASSES = frozenset({"strict_reopt_required", "verytight_convergence"})

#: Bounded rescue budget: at most 2 real calculation attempts per member lineage.
MAX_REAL_ATTEMPTS = 2


def next_action(row: dict, attempts: list[dict]) -> str:
    """Return the disposition for one member; never change a QC threshold.

    ``row`` is the member's newest ledger row (``status`` / ``failure_class`` /
    ``qc_flags``), ``attempts`` the lineage's real-calculation records (the
    importer passes ``[(attempt, log_sha256), ...]``-style dicts; only the
    count of DISTINCT pairs matters).
    """
    flags = set(filter(None, (row.get("qc_flags") or "").split(";")))
    failure = row.get("failure_class") or ""

    # The budget counts DISTINCT (attempt, log) pairs: a re-imported identical
    # log is one real calculation, never two (duplicate-submission safety).
    real = {(a.get("attempt"), a.get("log_sha256")) for a in attempts
            if a.get("log_sha256")}

    # Identity first: drift is never a budget question and never restartable.
    if flags & SPECIES_DRIFT_FLAGS:
        return "stop_species_drift"

    if row.get("status") == "computed":
        return "accept_for_dedup"

    # Technical faults (segfault / abnormal termination / scheduler death)
    # happen BEFORE any science: they are not charged to the rescue budget.
    if failure == "abnormal_termination":
        return "technical_retry_after_diagnosis"

    # Bounded budget on real calculation attempts, regardless of failure class.
    if len(real) >= MAX_REAL_ATTEMPTS:
        return "limited_rescue_budget_exhausted"

    if failure in STRICT_REOPT_CLASSES:
        return "reopt_from_own_converged_geometry"

    if failure == "max_cycles_exhausted":
        # A continuation is admissible ONLY after the restart-identity gate
        # (atom order + frozen bond graph) has been passed at package build
        # time; the routing here merely names the remedy.
        return "continuation_only_if_restart_identity_matches"

    return "manual_review"
