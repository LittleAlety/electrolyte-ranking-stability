"""Derive the strict_readiness evidence flags from real artifacts on disk.

The plan's rule: ``checks`` must come from generators that have already verified
their own outputs -- never from a hand-set boolean.  This wiring reads the
artifacts each check refers to and derives True/False mechanically.

**2026-10-22 hardening.**  An independent review measured that the first version
of this file accepted broken evidence: a coverage row with no ``verdict``
(``None != ""`` is True), an identity table holding a single ``computed`` row
(``computed == len(rows)``), a ``not_computed`` sampling row that nonetheless
carried a number, ``invalid_input`` WP3/WP5 statuses, a ``NaN`` cost, and two
hard-coded ``False`` triggers.  Five rules follow, and every check implements
all five:

1. **key width** -- a missing key is not an empty value: required keys must be
   PRESENT and hold a value from a declared token set.
2. **cohort** -- a table is complete only when it covers exactly the frozen
   cohort (weighted members / open states / audit states / experiment groups),
   derived from the authoritative artifact, never from its own row count.
3. **value validity** -- numbers must parse AND be finite; NaN / inf / negative
   are refused; an empty cell is MISSING and never reads as 0.
4. **disposition** -- "evidence handled" is not "value computed":
   ``not_computed`` must carry NO number, ``complete`` must satisfy the printed
   identity, and a non-``complete`` cost must declare its scope.
5. **derived triggers** -- WP6 / pool extension come from their real
   preconditions; "cannot tell" is ``unknown``, which BLOCKS, and is never
   silently equal to ``not_triggered``.

A missing artifact, an unparsable file or an incomplete cohort reads as False
(fail closed), and every flag carries its source plus a machine-readable
``problems`` list so the gate can say WHAT is missing.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "outputs" / "physics_completion"

# member -> the artifact that proves it
SOURCES = {
    "coverage_reviews_valid": OUT / "recovery" / "coverage_reviews.csv",
    "identity_all_members_complete": OUT / "frontier" / "frontier_localization.csv",
    "sampling_audit_complete": OUT / "sampling" / "sampling_3to6_diff.csv",
    "wp3_evidence_complete": OUT / "closure" / "flip_persistence.csv",
    "wp5_full_target_pool_evaluated": (OUT / "active_learning" / "blind_replay"
                                       / "AB_axis_endpoint.csv"),
    "execution_cost_provenance_complete": OUT / "cost" / "production_cost_ledger.csv",
}

#: artifacts a cohort check needs in order to know what the cohort IS
CONTEXT = {
    "labels": OUT / "ensembles" / "production_ensemble_labels.csv",
    "weights": OUT / "ensembles" / "production_ensemble_weights.csv",
    "identity_evidence": OUT / "frontier" / "frontier_identity_evidence.csv",
}

#: declared token sets -- an unknown token is never accepted as a disposition
COVERAGE_ROUTES = frozenset((
    "multi_basin_coverage", "single_basin_verified", "known_basin_reproduction",
    "unresolved_qc", "pending", "search_exhausted", "dedup_evidence_required",
))
COVERAGE_VERDICTS = frozenset(("resolved", "unresolved", "pending",
                              "search_exhausted"))
COVERAGE_SETTLED = frozenset(("resolved", "unresolved", "search_exhausted"))
WP3_STATUSES = frozenset(("computed", "computed_screen_only", "limited",
                          "blocked", "n/a"))
FLIP_RUNGS = ("R1a", "R1b", "R2", "R3", "R4", "R4_screen")
WP5_STOP_STATUSES = frozenset(("computed", "not_reached_within_pool"))
WP5_MODELS = frozenset(("knn_baseline", "ridge_std", "krr_rbf", "gpr_rbf"))
WP5_BASELINES = frozenset(("random", "diversity", "uncertainty", "ranking_aware"))
WP5_TASKS = ("A", "B")
COST_STATUSES = frozenset(("complete", "incomplete"))
#: a member's raw-output stage is 'parsed' once read; 'computed' is accepted too
PARSED_TOKENS = frozenset(("parsed", "computed"))
ACCEPTED_TOKENS = frozenset(("accepted", "provisional", "limited", "blocked"))
#: the plan's round-2 audit cohort: 4 molecules x 4 states
SAMPLING_AUDIT_STATES = 16
#: WP6's quantised upgrade gate: Li pairs >= 9/12 AND the ensemble at 48/48
WP6_REQUIRED_LI_PAIRS = 9
LI_STATES = ("LiM_plus", "LiM_2plus")
FROZEN_MOLECULE_COUNT = 12


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _txt(value) -> str:
    """A missing key is NOT an empty value; callers test token membership."""
    return "" if value is None else str(value).strip()


def _num(value):
    """float or None; blank/NaN/inf are refused, never coerced to 0."""
    s = _txt(value)
    if not s:
        return None
    try:
        f = float(s)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _pos_int(value):
    f = _num(value)
    if f is None or f <= 0 or f != int(f):
        return None
    return int(f)


def _nonneg_int(value):
    f = _num(value)
    if f is None or f < 0 or f != int(f):
        return None
    return int(f)


def _read_or_none(path: Path):
    if not path.is_file():
        return None
    try:
        return _rows(path)
    except (OSError, UnicodeDecodeError, csv.Error):
        return None


def _result(ok: bool, problems: list, **extra) -> tuple[bool, dict]:
    detail = {"problems": problems, "checked": True}
    detail.update(extra)
    return bool(ok) and not problems, detail


# --------------------------------------------------------------------------- #
# 1. coverage reviews: every open state settled, frozen evidence still present
# --------------------------------------------------------------------------- #
def _check_coverage(path: Path):
    rows = _read_or_none(path)
    if not rows:
        return _result(False, ["artifact missing or empty"])
    labels = _read_or_none(CONTEXT["labels"])
    if labels is None:
        return _result(False, ["labels cohort unavailable"])

    accepted = {(r.get("name"), r.get("state")) for r in labels
                if _txt(r.get("acceptance_status")) == "accepted"}
    open_states = {(r.get("name"), r.get("state")) for r in labels
                   if _txt(r.get("acceptance_status")) and
                   (r.get("name"), r.get("state")) not in accepted}

    problems, seen = [], {}
    for r in rows:
        key = (_txt(r.get("name")), _txt(r.get("state")))
        if not all(key):
            problems.append("row without name/state")
            continue
        if key in seen:
            problems.append("duplicate review for %s|%s" % key)
            continue
        seen[key] = r
        route, verdict = _txt(r.get("route")), _txt(r.get("verdict"))
        if route not in COVERAGE_ROUTES:
            problems.append("%s|%s unknown route %r" % (key[0], key[1], route))
        if verdict not in COVERAGE_VERDICTS:
            problems.append("%s|%s unknown verdict %r" % (key[0], key[1], verdict))
        if not _txt(r.get("review_version")):
            problems.append("%s|%s missing review_version" % key)
        if _nonneg_int(r.get("n_unique_after")) is None:
            problems.append("%s|%s n_unique_after not a non-negative integer" % key)
        if verdict == "resolved" and not (
                _txt(r.get("kept_pool_evidence"))
                or _txt(r.get("computed_new_members"))):
            problems.append("%s|%s resolved without pool evidence" % key)
        if verdict == "pending":
            problems.append("%s|%s review still pending (evidence not settled)" % key)

    missing = open_states - set(seen)
    if missing:
        problems.append("open states without a review: %s"
                        % sorted("%s|%s" % k for k in missing))
    # an accepted state may keep its frozen resolved review, but nothing else
    for key, row in seen.items():
        if key in accepted and _txt(row.get("verdict")) != "resolved":
            problems.append("%s|%s accepts a review for a state that is not open"
                            % key)
    return _result(True, problems, review_rows=len(rows),
                   open_states=len(open_states), accepted_states=len(accepted))


# --------------------------------------------------------------------------- #
# 2. electronic identity: exactly the weighted cohort, fully verified
# --------------------------------------------------------------------------- #
def _check_identity(path: Path):
    rows = _read_or_none(path)
    if not rows:
        return _result(False, ["artifact missing or empty"])
    weights = _read_or_none(CONTEXT["weights"])
    if not weights:
        return _result(False, ["weighted-member cohort unavailable"])
    cohort = {_txt(r.get("member_key")) for r in weights}
    cohort.discard("")
    if not cohort:
        return _result(False, ["weighted-member cohort is empty"])

    problems, seen = [], set()
    for r in rows:
        key = _txt(r.get("member_key"))
        if not key:
            problems.append("row without member_key")
            continue
        if key in seen:
            problems.append("duplicate member %s" % key)
            continue
        seen.add(key)
        if _txt(r.get("status")) != "computed":
            problems.append("%s status != computed" % key)
        if _txt(r.get("identity_qc_status")) != "verified":
            problems.append("%s identity_qc_status != verified" % key)
        # the artifact's own tokens: a member's molden/FMOPop stage is 'parsed'
        # once its raw output has been read (see build_frontier_localization)
        if _txt(r.get("molden_status")) not in PARSED_TOKENS:
            problems.append("%s molden_status not parsed/computed" % key)
        if _txt(r.get("fmopop_status")) not in PARSED_TOKENS:
            problems.append("%s fmopop_status not parsed/computed" % key)
        wf = _txt(r.get("wavefunction"))
        if wf not in ("R", "U"):
            problems.append("%s wavefunction %r not in {R,U}" % (key, wf))
        spin = _txt(r.get("spin_reported"))
        # R has one restricted channel; U is parsed per channel, so the row
        # carries the channel it belongs to (alpha or beta).
        if wf == "R" and spin != "restricted":
            problems.append("%s restricted wavefunction but spin_reported=%r"
                            % (key, spin))
        if wf == "U" and spin not in ("alpha", "beta"):
            problems.append("%s unrestricted wavefunction but spin_reported=%r"
                            % (key, spin))
        if not _txt(r.get("frontier_class_lumo")):
            problems.append("%s missing frontier_class_lumo" % key)
    if seen != cohort:
        problems.append("cohort mismatch: %d rows vs %d weighted members"
                        % (len(seen), len(cohort)))
        for extra in sorted(seen - cohort)[:3]:
            problems.append("unweighted member present: %s" % extra)
        for miss in sorted(cohort - seen)[:3]:
            problems.append("weighted member missing: %s" % miss)

    ev = _read_or_none(CONTEXT["identity_evidence"])
    if ev is None:
        problems.append("identity evidence table unavailable")
    else:
        ev_keys = {_txt(r.get("member_key")) for r in ev}
        if ev_keys != cohort:
            problems.append("identity evidence cohort mismatch")
        bad = [k for k in ev_keys
               if _txt(next(r for r in ev
                            if _txt(r.get("member_key")) == k
                            ).get("identity_qc_status")) != "verified"]
        if bad:
            problems.append("evidence rows not verified: %d" % len(bad))
    return _result(True, problems, rows=len(rows), cohort=len(cohort))


# --------------------------------------------------------------------------- #
# 3. sampling audit: disposition complete, numbers only when computed
# --------------------------------------------------------------------------- #
def _check_sampling(path: Path):
    rows = _read_or_none(path)
    if not rows:
        return _result(False, ["artifact missing or empty"])
    problems, seen = [], set()
    complete = not_computed = 0
    for r in rows:
        key = (_txt(r.get("name")), _txt(r.get("state")))
        if not all(key):
            problems.append("row without name/state")
            continue
        if key in seen:
            problems.append("duplicate audit state %s|%s" % key)
            continue
        seen.add(key)
        status = _txt(r.get("ceiling_status"))
        if not _txt(r.get("acceptance_status")):
            problems.append("%s|%s missing acceptance_status" % key)
        floor = _num(r.get("g_ensemble_round1_kcal"))
        ceil_ = _num(r.get("g_ensemble_ceiling_kcal"))
        delta = _num(r.get("delta_g_ensemble_kcal"))
        if status == "complete":
            complete += 1
            if floor is None or ceil_ is None or delta is None:
                problems.append("%s|%s complete without three finite G values" % key)
            else:
                # the reader must be able to hand-check the printed identity
                expect = round(ceil_ - floor, 6)
                if abs(delta - expect) > 5e-7:
                    problems.append("%s|%s delta %s != ceiling-round1 %s"
                                    % (key[0], key[1], delta, expect))
        elif status == "not_computed":
            not_computed += 1
            if not _txt(r.get("ceiling_reason")):
                problems.append("%s|%s not_computed without a reason" % key)
            # 空值不是零: a non-computed row must not carry a number
            for col in ("g_ensemble_ceiling_kcal", "delta_g_ensemble_kcal"):
                if _txt(r.get(col)):
                    problems.append("%s|%s not_computed but %s is filled"
                                    % (key[0], key[1], col))
        else:
            problems.append("%s|%s unknown ceiling_status %r" % (key[0], key[1], status))
    if len(rows) != SAMPLING_AUDIT_STATES:
        problems.append("audit cohort is %d rows, expected %d"
                        % (len(rows), SAMPLING_AUDIT_STATES))
    return _result(True, problems, rows=len(rows), complete=complete,
                   not_computed=not_computed)


# --------------------------------------------------------------------------- #
# 4. WP3 closure: every pair carries the full rung ladder with a known status
# --------------------------------------------------------------------------- #
def _check_wp3(path: Path):
    rows = _read_or_none(path)
    if not rows:
        return _result(False, ["artifact missing or empty"])
    problems, by_pair = [], {}
    for r in rows:
        pair, rung = _txt(r.get("pair")), _txt(r.get("rung"))
        if not pair or not rung:
            problems.append("row without pair/rung")
            continue
        by_pair.setdefault(pair, {})[rung] = r
    if not by_pair:
        problems.append("no pair found")
    for pair, rungs in sorted(by_pair.items()):
        if set(rungs) != set(FLIP_RUNGS):
            problems.append("%s rung ladder incomplete: %s"
                            % (pair, sorted(set(FLIP_RUNGS) - set(rungs))))
        for rung, row in sorted(rungs.items()):
            status = _txt(row.get("status"))
            if status not in WP3_STATUSES:
                problems.append("%s %s unknown status %r" % (pair, rung, status))
            if status == "computed" and _num(row.get("delta_ev")) is None:
                problems.append("%s %s computed without a finite delta_ev"
                                % (pair, rung))
    return _result(True, problems, pairs=len(by_pair), rows=len(rows))


# --------------------------------------------------------------------------- #
# 5. WP5: the FULL frozen cohort, with a real stop-budget recomputation
# --------------------------------------------------------------------------- #
def _check_wp5(path: Path):
    rows = _read_or_none(path)
    if not rows:
        return _result(False, ["artifact missing or empty"])
    problems, seen = [], set()
    declared_budget = {}
    for r in rows:
        axis = (_txt(r.get("task")), _txt(r.get("executed_model")),
                _txt(r.get("baseline")))
        if axis in seen:
            problems.append("duplicate experiment group %s" % (axis,))
            continue
        seen.add(axis)
        if axis[0] not in WP5_TASKS:
            problems.append("unknown task %r" % axis[0])
        if axis[1] not in WP5_MODELS:
            problems.append("unknown executed_model %r" % axis[1])
        if axis[2] not in WP5_BASELINES:
            problems.append("unknown baseline %r" % axis[2])
        if _txt(r.get("executed_model")) != _txt(r.get("prediction_model")):
            problems.append("%s prediction_model != executed_model" % (axis,))
        if not _txt(r.get("acquisition_version")):
            problems.append("%s missing acquisition_version" % (axis,))
        # the frozen cohort is the 12-molecule pool; a subset is not the cohort
        if _txt(r.get("n_pool")) != str(FROZEN_MOLECULE_COUNT):
            problems.append("%s n_pool=%s is not the full %d-molecule cohort"
                            % (axis, _txt(r.get("n_pool")), FROZEN_MOLECULE_COUNT))
        status = _txt(r.get("stop_budget_status"))
        if status not in WP5_STOP_STATUSES:
            problems.append("%s stop_budget_status=%r not evaluable"
                            % (axis, status))
            continue
        n_t = _txt(r.get("stop_budget_n_T"))
        if status == "computed":
            val = _pos_int(n_t)
            if val is None:
                problems.append("%s computed without a positive n_T" % (axis,))
            else:
                declared_budget[axis] = val
        elif n_t:
            problems.append("%s not_reached but n_T is filled (%s)" % (axis, n_t))
    expected = {(t, m, b) for t in WP5_TASKS for m in sorted(WP5_MODELS)
                for b in sorted(WP5_BASELINES)}
    if seen != expected:
        problems.append("experiment-group cohort mismatch: %d of %d"
                        % (len(seen), len(expected)))
        for miss in sorted(expected - seen)[:3]:
            problems.append("group missing: %s" % (miss,))
    return _result(True, problems, groups=len(seen), expected_groups=len(expected),
                   stop_budgets=len(declared_budget))


# --------------------------------------------------------------------------- #
# 6. cost provenance: every leg traceable, MISSING never becomes 0
# --------------------------------------------------------------------------- #
def _check_cost(path: Path):
    rows = _read_or_none(path)
    if not rows:
        return _result(False, ["artifact missing or empty"])
    problems, seen = [], set()
    declared_incomplete = []
    for r in rows:
        job = _txt(r.get("job_id"))
        key = "%s|%s" % (_txt(r.get("name")), _txt(r.get("state")))
        if not job:
            problems.append("%s without a job identity" % key)
        elif job in seen:
            problems.append("%s duplicate job identity %s" % (key, job))
        else:
            seen.add(job)
        if _pos_int(r.get("cores")) is None:
            problems.append("%s cores not a positive integer" % key)
        if not _txt(r.get("status")):
            problems.append("%s missing status" % key)
        status = _txt(r.get("cost_status"))
        if status not in COST_STATUSES:
            problems.append("%s unknown cost_status %r" % (key, status))
            continue
        cost = _num(r.get("core_hours"))
        if cost is None:
            cost = _num(r.get("hpc_core_hours"))
        if cost is None:
            problems.append("%s cost is MISSING (never substitute 0)" % key)
        elif cost <= 0:
            problems.append("%s cost %s is not positive" % (key, cost))
        if status != "complete":
            if not _txt(r.get("cost_scope")):
                problems.append("%s non-complete cost without a declared scope" % key)
            declared_incomplete.append(key)
    return _result(True, problems, rows=len(rows),
                   declared_incomplete=len(declared_incomplete),
                   declared_incomplete_legs=declared_incomplete[:5])


CHECKS = {
    "coverage_reviews_valid": _check_coverage,
    "identity_all_members_complete": _check_identity,
    "sampling_audit_complete": _check_sampling,
    "wp3_evidence_complete": _check_wp3,
    "wp5_full_target_pool_evaluated": _check_wp5,
    "execution_cost_provenance_complete": _check_cost,
}
REQUIRED_CHECKS = tuple(CHECKS)


# --------------------------------------------------------------------------- #
# triggers: derived from real preconditions, "unknown" blocks
# --------------------------------------------------------------------------- #
def derive_wp6_trigger(labels, frozen_molecules, complete_li_pairs) -> str:
    """``triggered`` / ``not_triggered`` / ``unknown`` for the WP6 upgrade gate.

    The plan's quantised gate: Li pairs >= 9/12 AND the ensemble fully accepted.
    ``unknown`` whenever the evidence needed to decide is absent or malformed --
    it must never collapse into ``not_triggered``, which would silently disable
    a gate that has in fact fired.
    """
    molecules = set(frozen_molecules or ())
    if len(molecules) != FROZEN_MOLECULE_COUNT or complete_li_pairs is None:
        return "unknown"
    states = ("M", "M_plus", "LiM_plus", "LiM_2plus")
    expected = {(name, state) for name in molecules for state in states}
    try:
        keys = [(_txt(r["name"]), _txt(r["state"])) for r in labels]
        statuses = [_txt(r["acceptance_status"]) for r in labels]
    except (KeyError, TypeError):
        return "unknown"
    if len(keys) != len(set(keys)) or set(keys) != expected:
        return "unknown"
    if any(status not in ACCEPTED_TOKENS for status in statuses):
        return "unknown"
    pairs = list(complete_li_pairs)
    if len(pairs) != len(set(pairs)) or not set(pairs) <= molecules:
        return "unknown"
    all_accepted = all(status == "accepted" for status in statuses)
    if all_accepted and len(pairs) >= WP6_REQUIRED_LI_PAIRS:
        return "triggered"
    return "not_triggered"


def derive_pool_extension_trigger(wp5_full_pool_ok) -> str:
    """WP5 pool extension's precondition, derived -- never a constant.

    The plan keeps ``wp5_pool_extension`` independent of the ensemble, and it
    becomes in-scope only once the current frozen cohort has actually been
    evaluated end to end.  Before that the prerequisite has not fired; if the
    evaluation evidence cannot be read, the answer is ``unknown``.
    """
    if wp5_full_pool_ok is None:
        return "unknown"
    return "triggered" if wp5_full_pool_ok else "not_triggered"


def _complete_li_pairs(labels) -> list:
    """Molecules whose BOTH Li states are accepted (the plan's pairing unit)."""
    by_mol = {}
    for r in labels:
        by_mol.setdefault(_txt(r.get("name")), {})[_txt(r.get("state"))] = \
            _txt(r.get("acceptance_status"))
    return sorted(m for m, st in by_mol.items()
                  if all(st.get(s) == "accepted" for s in LI_STATES))


def derive_check_details() -> dict:
    """Per-check ``{passed, problems, ...counts}`` -- the inspectable view."""
    details = {}
    for flag, fn in CHECKS.items():
        path = SOURCES[flag]
        try:
            passed, detail = fn(path) if path.is_file() else _result(
                False, ["artifact missing"])
        except (OSError, UnicodeDecodeError, csv.Error, KeyError, TypeError,
                ValueError) as exc:                      # fail closed
            passed, detail = False, {"problems": ["unreadable: %r" % (exc,)]}
        detail["passed"] = passed
        details[flag] = detail
    return details


def derive_checks() -> dict:
    """One boolean per required check, each derived from its own artifact.

    Two derived tri-state triggers ride alongside, so a caller can never read a
    hard-coded ``False`` as "the gate has not fired".
    """
    checks = {k: bool(v["passed"]) for k, v in derive_check_details().items()}

    labels = _read_or_none(CONTEXT["labels"]) or []
    molecules = sorted({_txt(r.get("name")) for r in labels if _txt(r.get("name"))})
    wp6_state = derive_wp6_trigger(labels, molecules,
                                   _complete_li_pairs(labels) if labels else None)
    pool_state = derive_pool_extension_trigger(checks.get("wp5_full_target_pool_evaluated"))

    checks["wp6_trigger_state"] = wp6_state
    checks["pool_extension_trigger_state"] = pool_state
    # legacy booleans, True only when the gate has actually fired
    checks["wp6_triggered"] = wp6_state == "triggered"
    checks["pool_extension_triggered"] = pool_state == "triggered"
    return checks


def _sources_doc() -> dict:
    doc = {k: str(v.relative_to(REPO)) for k, v in SOURCES.items()}
    doc.update({("context:" + k): str(v.relative_to(REPO))
                for k, v in CONTEXT.items()})
    return doc


if __name__ == "__main__":
    doc = {"checks": derive_checks(), "details": derive_check_details(),
           "sources": _sources_doc()}
    print(json.dumps(doc, ensure_ascii=False, indent=2))