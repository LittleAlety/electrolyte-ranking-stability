#!/usr/bin/env python
"""Read-only evidence gate for the dol_ec_recovery_v1 batch (2026-10-27 ruling).

Given ALREADY-VERIFIED evidence about the batch, this module names the ONE next
action.  It never submits, never edits scientific labels, and never guesses:
every ``Evidence`` field is filled by a real-evidence adapter upstream, never
by a human typing ``True``.

Design points from the ruling:
  * once a submission attempt exists, the gate RECONCILEs -- it can never fall
    back to the auto-submit branch;
  * ``qc_results_complete`` means "every leg has an explicit verdict", NOT
    "every leg passed" -- two failed legs still move on to settlement and the
    limitation report, never to retry;
  * mixing DMC / a third task / a reserve start into the batch is a HOLD-level
    refusal BEFORE submission.

2026-10-27 audit fixes (gate-code-auditor REPORT.md, adopted in full):
  F-1  unknown sacct states are now NON-terminal (white-list, fail-closed)
  F-2  the terminal white-list REUSES submit_hpc_batch.TERMINAL_STATES (single
       source of truth; CANCELLED is terminal, matching Slurm and the project's
       own 3747724 settlement) and states are normalised (split " by ",
       rstrip "+") before matching
  F-3  the activation key now includes the SLOT (tasks/<NAME>/<SLOT>__<seed>):
       a wrong slot means the wrong chemical system, so slot-blindness was a
       real hole; malformed tasks.txt rows return False instead of raising
  F-4  ``batch_tasks_exactly_activated`` defaults to False (fail-closed): a
       forgotten field HOLDS, never silently claims "exactly activated"
  F-9  malformed tasks.txt (no "/" or no "__") returns False, not IndexError
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACTIVATION = REPO / "config" / "recovery_start_activation_v1.json"
CANDIDATES = (REPO / "outputs" / "physics_completion" / "ensembles"
              / "production_ensemble_candidates.csv")
#: the batch's own remote-dir name (ensemble_hpc_io binds sacct WorkDir against
#: REMOTE_ROOT/<local package dir name>, so the two must match exactly)
PACKAGE_NAME = "dol_ec_recovery_v1"

#: single source of truth for terminal scheduler states (audit F-2): reusing
#: the submitter's list kills the second, drifting copy.  Slurm semantics AND
#: the project's own history (3747724 settled as a 0-CH terminal CANCELLED)
#: both treat CANCELLED as terminal.
from submit_hpc_batch import TERMINAL_STATES  # noqa: E402  (same package)


def _normalise_state(state: str) -> str:
    """sacct prints 'CANCELLED by <uid>' and may append '+' when truncated."""
    return state.split(" by ")[0].strip().rstrip("+")


class NextAction(str, Enum):
    HOLD = "hold"
    SUBMIT_ONCE = "submit_once"
    RECONCILE = "reconcile_submission"
    WAIT = "wait"
    FETCH = "fetch_and_verify"
    QC = "run_existing_qc"
    SETTLE = "settle_actual_cost"
    REBUILD = "rebuild_downstream"
    REPORT = "publish_stage_report"


@dataclass(frozen=True)
class Evidence:
    preflight_ok: bool
    authorization_bound: bool
    package_verified: bool
    budget_reserved: bool
    # absent / submitting / submitted / submit_failed / unknown
    submission_status: str
    job_mapping_verified: bool
    terminal_states_verified: bool
    artifacts_verified: bool
    qc_results_complete: bool
    cost_settled: bool
    downstream_checks_ok: bool
    # 2026-10-27 ruling: the batch may ONLY carry the two activated tasks.
    # NO optimistic default (audit F-4): a forgotten field must fail CLOSED
    # (HOLD), never silently claim "exactly activated".
    batch_tasks_exactly_activated: bool = False


def next_action(e: Evidence) -> NextAction:
    if not e.batch_tasks_exactly_activated:
        # DMC / a third task / a reserve start in the batch: refuse BEFORE
        # anything else, even before reconciliation of an in-flight attempt.
        return NextAction.HOLD
    # once a submission attempt exists, verify the real state first -- never
    # fall back to the auto-submit branch.
    if e.submission_status in ("submitting", "submit_failed", "unknown"):
        return NextAction.RECONCILE
    if e.submission_status == "absent":
        ready = (e.preflight_ok and e.authorization_bound
                 and e.package_verified and e.budget_reserved)
        return NextAction.SUBMIT_ONCE if ready else NextAction.HOLD
    if e.submission_status != "submitted":
        return NextAction.HOLD
    if not e.job_mapping_verified:
        return NextAction.RECONCILE
    if not e.terminal_states_verified:
        return NextAction.WAIT
    if not e.artifacts_verified:
        return NextAction.FETCH
    if not e.qc_results_complete:
        return NextAction.QC
    if not e.cost_settled:
        return NextAction.SETTLE
    if not e.downstream_checks_ok:
        return NextAction.REBUILD
    return NextAction.REPORT


def activation_member_keys() -> set[tuple[str, str, str]]:
    """(name, slot, seed) triples authorised by the activation registry.

    The SLOT participates (audit F-3): tasks/<NAME>/<SLOT>__<seed> carries the
    solvent environment -- a wrong slot means the wrong chemical system, and
    dropping it from the key made the three-way check blind to that.
    """
    doc = json.loads(ACTIVATION.read_text(encoding="utf-8"))
    out = set()
    for entry in doc.get("activated", []):
        name, slot = str(entry["state_key"]).split("|")
        out.add((name, slot, str(entry["leaf"])))
    return out


def candidates_matching(source_kind: str) -> list[tuple[str, str, str]]:
    rows = []
    with CANDIDATES.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r.get("source_kind") == source_kind:
                rows.append((r["name"], r["slot"], r["seed"]))
    return rows


def _task_row_keys(rel: str) -> tuple[str, str, str] | None:
    """(name, slot, seed) from 'tasks/<NAME>/<SLOT>__<seed>'; None if malformed."""
    parts = rel.split("/")
    if len(parts) < 3 or "__" not in parts[-1]:
        return None
    slot_seed = parts[-1].split("__", 1)
    if not slot_seed[0] or not slot_seed[1]:
        return None
    return (parts[1], slot_seed[0], slot_seed[1])


def batch_is_exactly_activated(package_dir: Path,
                                source_kind: str = "p4v2_screening_v1_start",
                                ) -> bool:
    """The batch carries EXACTLY the two activated tasks.

    Checks all three registries the ruling names (activation registry, the
    candidates table, and the package's own tasks.txt) -- a DMC task, a third
    task, a reserve start, or a WRONG SLOT sneaking into any one of them fails
    the check.  Malformed rows fail closed (False), never raise.
    """
    act = activation_member_keys()
    cand = set(candidates_matching(source_kind))
    if act != cand or len(act) != 2:
        return False
    if package_dir.name != PACKAGE_NAME:
        return False
    tasks = (package_dir / "tasks.txt").read_text(encoding="utf-8").split()
    if len(tasks) != 2:
        return False
    pkg_keys = set()
    for rel in tasks:
        key = _task_row_keys(rel)
        if key is None:
            return False
        pkg_keys.add(key)
    return pkg_keys == act


def sacct_terminal_states(rows, expected_job_ids) -> dict[str, str]:
    """Map each expected raw job id -> its scheduler state, verifying terminal.

    ``rows`` are parsed sacct lines (dicts with at least JobIDRaw/State).
    States are normalised (``'CANCELLED by 59540'`` -> ``CANCELLED``; trailing
    ``+`` stripped) and matched against the submitter's TERMINAL_STATES
    white-list (audit F-1/F-2): anything unknown, empty or genuinely
    non-terminal returns {} (callers read that as "wait") -- a fabricated
    terminal verdict is impossible in either direction.
    """
    expected = set(expected_job_ids)
    seen: dict[str, str] = {}
    for row in rows:
        jid = str(row.get("JobIDRaw", row.get("JobID", "")))
        if jid not in expected:
            continue
        state = _normalise_state(str(row.get("State", "")))
        if jid in seen and seen[jid] != state:
            return {}
        seen[jid] = state
    if set(seen) != expected:
        return {}
    if any(s not in TERMINAL_STATES for s in seen.values()):
        return {}
    return seen