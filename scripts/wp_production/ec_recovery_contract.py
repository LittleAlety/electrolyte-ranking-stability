"""EC next-round machine contract (L02, 2026-10-29).

Fixes the executable shape of the *proposed* EC campaign before any calculation
authorisation exists: candidate order ``p4 -> p7``, one element in flight, at most
two real submissions, 16 core-hours per element, 32 core-hours total, ledger
required.

Design-only: this module authorises nothing.  It only refuses contract shapes that
the preregistration draft forbids, so a future package builder (L03) and the
protected submitter agree on one machine-readable definition instead of prose.
"""
from __future__ import annotations

EC_CANDIDATES = ("ec_v2_p4", "ec_v2_p7")
EC_PROFILE = "orca_production_4h_v1"
EC_CORES = 4
EC_WALL_HOURS = 4
EC_ELEMENT_CORE_HOURS = EC_CORES * EC_WALL_HOURS  # 16 CH per submitted element
EC_CAP_CORE_HOURS = 32
EC_MAX_SUBMITTED_ELEMENTS = 2


class ContractViolation(ValueError):
    """A submission shape the EC campaign contract refuses (fail-closed)."""


def next_candidate(history):
    """Return the only submittable candidate, or ``None`` when the campaign stops.

    ``history`` is an ordered list of campaign records with keys ``candidate``
    (str), ``submitted`` (bool), ``terminal`` (bool), ``accepted`` (bool or None)
    and ``evidence_complete`` (bool or None).  Rules:

    * nothing submitted yet -> ``ec_v2_p4``;
    * p4 submitted but not terminal -> ``None`` (one element in flight);
    * p4 accepted -> ``None`` (coverage passed, campaign ends);
    * p4 terminal but ``accepted`` is missing/None -> ``None`` (an unknown result
      must never be read as a proven failure, so p7 is NOT opened);
    * p4 terminal, not accepted, but evidence incomplete -> ``None``;
    * p4 terminal, not accepted, evidence complete -> ``ec_v2_p7``;
    * p7 already submitted -> ``None`` (never a third leg).
    """
    submitted = [entry for entry in history if entry.get("submitted")]
    p4_entries = [e for e in submitted if e["candidate"] == EC_CANDIDATES[0]]
    if not p4_entries:
        return EC_CANDIDATES[0]
    last_p4 = p4_entries[-1]
    if not last_p4.get("terminal"):
        return None
    accepted = last_p4.get("accepted")
    if accepted is None:
        return None
    if accepted:
        return None
    if last_p4.get("evidence_complete") is not True:
        return None
    p7_entries = [e for e in submitted if e["candidate"] == EC_CANDIDATES[1]]
    if not p7_entries:
        return EC_CANDIDATES[1]
    return None


def check_campaign_contract(
    *,
    candidate,
    profile,
    cores,
    wall_hours,
    element_count,
    declared_reservation_core_hours,
    settled_core_hours=0.0,
    unsettled_reserved_core_hours=0.0,
    ec_active_pending=0,
    ec_submitted_elements=0,
    history=(),
):
    """Validate one prospective EC submission; return the accepted numbers.

    Every refusal is a :class:`ContractViolation` so a caller cannot silently
    downgrade a rejection into a warning.
    """
    if candidate not in EC_CANDIDATES:
        raise ContractViolation(
            "candidate %r is not registered for this campaign (allowed: %s)"
            % (candidate, ", ".join(EC_CANDIDATES))
        )

    expected = next_candidate(list(history))
    if candidate != expected:
        raise ContractViolation(
            "candidate %r is not the next campaign step (expected %r)"
            % (candidate, expected)
        )

    if int(ec_submitted_elements) + int(element_count) > EC_MAX_SUBMITTED_ELEMENTS:
        raise ContractViolation(
            "third leg refused: %d element(s) already submitted, at most %d allowed"
            % (ec_submitted_elements, EC_MAX_SUBMITTED_ELEMENTS)
        )

    # The caller may not lie about the campaign history: the two derived counts
    # must agree with the records they claim to summarise, otherwise "no element
    # in flight" could be asserted while a submission is still unresolved.
    submitted_count = sum(1 for e in history if e.get("submitted"))
    pending_count = sum(1 for e in history
                        if e.get("submitted") and not e.get("terminal"))
    if int(ec_submitted_elements) != submitted_count:
        raise ContractViolation(
            "submitted-element count %r disagrees with the campaign history (%d)"
            % (ec_submitted_elements, submitted_count)
        )
    if int(ec_active_pending) != pending_count:
        raise ContractViolation(
            "active/pending count %r disagrees with the campaign history (%d)"
            % (ec_active_pending, pending_count)
        )

    if profile != EC_PROFILE:
        raise ContractViolation(
            "profile %r is not the authorised EC profile %r" % (profile, EC_PROFILE)
        )

    if int(cores) != EC_CORES:
        raise ContractViolation(
            "cores %r != %d (resource shape is fixed by the profile)"
            % (cores, EC_CORES)
        )

    if abs(float(wall_hours) - EC_WALL_HOURS) > 1e-9:
        raise ContractViolation(
            "wall_hours %r != %s (resource shape is fixed by the profile)"
            % (wall_hours, EC_WALL_HOURS)
        )

    if int(element_count) != 1:
        raise ContractViolation(
            "exactly one element may be in flight per submission, got %r"
            % (element_count,)
        )

    new_reservation = EC_ELEMENT_CORE_HOURS * int(element_count)
    if abs(float(declared_reservation_core_hours) - new_reservation) > 1e-9:
        raise ContractViolation(
            "low-reported reservation: declared %r CH but this element reserves %d CH"
            % (declared_reservation_core_hours, new_reservation)
        )

    committed = float(settled_core_hours) + float(unsettled_reserved_core_hours)
    if committed + new_reservation > EC_CAP_CORE_HOURS + 1e-9:
        raise ContractViolation(
            "campaign budget exceeded: settled %.6f + unsettled %.6f + new %d > cap %d"
            % (
                float(settled_core_hours),
                float(unsettled_reserved_core_hours),
                new_reservation,
                EC_CAP_CORE_HOURS,
            )
        )

    if int(ec_active_pending) != 0:
        raise ContractViolation(
            "EC has %d active/pending element(s); wait for a terminal state first"
            % (ec_active_pending,)
        )

    return {
        "candidate": candidate,
        "profile": profile,
        "cores": EC_CORES,
        "wall_hours": EC_WALL_HOURS,
        "element_count": 1,
        "new_reservation_core_hours": new_reservation,
        "campaign_cap_core_hours": EC_CAP_CORE_HOURS,
        "remaining_after_this_core_hours": EC_CAP_CORE_HOURS
        - committed
        - new_reservation,
    }
