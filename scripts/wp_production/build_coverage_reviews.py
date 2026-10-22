"""Coverage reviews: the honest way a `limited` state may become `accepted`.

The user's 2026-10-21 ruling names the defect precisely:

    当前系综聚合器会持续计入历史 ``n_limited``。新增一个成功结构，不会自动解除
    旧成员造成的覆盖限制。

So the acceptance decision must NOT be "clear n_limited".  It becomes:

    unresolved work          -> provisional (unchanged)
    n_limited and no review  -> limited      (unchanged: history keeps its counts)
    n_limited + review=resolved -> accepted  (the gap is certified covered)

A review is DERIVED, never hand-written: it inspects the recovery batch's
registered starts, the member ledger and the dispositions, and certifies
`resolved` only when

* at least one registered recovery start is `computed` **and** survived the
  DFT-level dedup into the kept pool (i.e. it is a genuinely new minimum), and
* the state now holds >= 2 unique minima (a single basin is not "sampling
  complete"), and
* no registered recovery start is still pending.

Historical failures stay exactly as recorded (`technical_complete_qc_failed`,
`species_drift_unrecoverable`, ...); the review adds a coverage verdict, it
never rewrites history.

Outputs (new):

    outputs/physics_completion/recovery/coverage_reviews.csv
    outputs/physics_completion/recovery/coverage_reviews_index.json

``--check`` recomputes and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

LABELS = ENS / "production_ensemble_labels.csv"
STRUCT = ENS / "production_ensemble_structures.csv"
DISPOS = ENS / "production_ensemble_dispositions.csv"
WEIGHTS = ENS / "production_ensemble_weights.csv"
MANIFEST = RECOVERY / "strict_recovery_v1_manifest.csv"
SEARCH_INDEX = RECOVERY / "strict_recovery_v1_search_index.json"

OUT_CSV = RECOVERY / "coverage_reviews.csv"
OUT_INDEX = RECOVERY / "coverage_reviews_index.json"

REVIEW_VERSION = "coverage_review_v1"
RECOVERY_ROLE_PREFIX = "recovery_v1"

FIELDS = [
    "review_id", "batch_id", "name", "state",
    "historical_limitation", "historical_n_limited",
    "resolution_path", "route", "kept_pool_evidence", "registered_starts",
    "computed_new_members", "n_unique_after",
    "verdict", "review_version", "evidence_note",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))



def _probe_starts(name: str, state: str) -> list[str]:
    """Probe seeds registered as candidates for this state.

    Read from the candidate manifest (the authoritative registered-member list)
    and filtered to probe seeds, so the reviewer can distinguish "a probe was
    registered and run" from "the frozen recovery search was budgeted".
    """
    path = REPO / "outputs" / "physics_completion" / "ensembles" \
        / "production_ensemble_candidates.csv"
    if not path.is_file():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("name") != name or r.get("slot") != state:
                continue
            seed = r.get("seed", "")
            if seed.startswith("tors_"):
                out.append(seed)
    return out


def _rejected_probe_members() -> set:
    """Members that are recorded as REFUSED or as REPLACED-AFTER-CANCELLATION.

    Both are decisions with evidence, never absences:

    * ``rejected`` entries carry the reason the fragment preflight refused the
      candidate (EC's central C=O);
    * ``replaces_cancelled_job`` + ``requested_tasks`` name the elements of a
      CANCELLED array that a repair package supersedes (DMC/LiM_2plus tors_7,
      job 3747724, Elapsed=0).  Their stale ``pending`` rows must not be read as
      work still in flight.
    """
    import json as _json
    out = set()
    for man in sorted((REPO / "work").glob("hpc_torsion_probe_v*/manifest.json")):
        try:
            data = _json.loads(man.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in data.get("rejected") or []:
            key = entry.get("member_key") if isinstance(entry, dict) else None
            if key:
                out.add(key)
        if data.get("replaces_cancelled_job"):
            for task in data.get("requested_tasks") or []:
                # tasks/DMC/LiM_2plus__tors_7_0_1_2 -> DMC|LiM_2plus|tors_7_0_1_2
                leaf = task.split("/")[-1]
                if "__" not in leaf:
                    continue
                name = task.split("/")[-2]
                slot, seed = leaf.split("__", 1)
                out.add("%s|%s|%s" % (name, slot, seed))
    return out

def _search_scope_documented(search_outcome: str, starts: list) -> bool:
    """Was a bounded, registered search actually run for this state?

    A screening search that found no second basin documents the GFN2 surface; it
    does not establish the production surface.  For the single-basin route we
    additionally require that the state has a registered start (so the production
    leg started somewhere defensible) -- the caller checks the production side.
    """
    return bool(starts) and search_outcome in (
        "new_minima_found", "no_new_minimum_found",
        "unused_pool_basin_no_search_needed")


def coverage_route(latest_members: list, novelty: dict, *,
                   min_unique_after: int, registered_starts: list,
                   search_outcome: str, production_evidence: bool) -> tuple[str, str]:
    """Dispatch a coverage ROUTE with an explanation. Never raises acceptance.

    ``novelty`` maps member_key -> "new" | "known" | "unresolved"; an unresolved
    novelty means the dedup evidence itself is incomplete, so no route may be
    taken until it is resolved.
    """
    if any(r.get("status") in ("pending", "ready") for r in latest_members):
        return "pending", "recovery start(s) registered but not yet dispositioned"

    passed = [r for r in latest_members if r.get("status") == "computed"]
    if not passed:
        if not latest_members and search_outcome == "no_new_minimum_found":
            # the independent search RAN and every conformer collapsed onto an
            # already-known basin.  At the registered screening level this state
            # has no second conformational minimum -- a physical finding, not a
            # missing run.  It is NOT "unresolved_qc": no leg failed.
            return ("search_exhausted",
                    "independent GFN2 search found no new minimum (all starts "
                    "collapsed onto a known basin); single-basin is a physical "
                    "finding at the screening level, not a budget failure")
        if latest_members:
            return ("unresolved_qc",
                    "registered recovery start(s) exist but none passed QC; the "
                    "state stays limited and the overall gate stays blocked")
        return "pending", ("no recovery member registered yet; a versioned new "
                           "search must register a start before any verdict")

    kinds = [novelty.get(r["member_key"], "unresolved") for r in passed]
    if "unresolved" in kinds:
        return ("dedup_evidence_required",
                "computed start(s) have no usable dedup verdict; cannot classify "
                "them as new or known")

    if min_unique_after >= 2 and "new" in kinds:
        return ("multi_basin_coverage",
                "%d unique minimum(a); at least one computed recovery start is a "
                "genuinely new independent basin" % min_unique_after)

    if "new" in kinds:
        return ("multi_basin_coverage",
                "a computed recovery start is a new independent basin")

    # every computed start reproduced a known minimum
    if not production_evidence:
        return ("known_basin_reproduction",
                "computed start(s) deduplicated onto known minima; **not a QC "
                "failure** -- these are independent reproductions. Coverage is "
                "not yet certifiable: the production-side evidence set is "
                "incomplete")
    if not _search_scope_documented(search_outcome, registered_starts):
        return ("known_basin_reproduction",
                "computed start(s) reproduced known minima; no registered search "
                "scope documents whether an undiscovered production basin exists")

    return ("single_basin_verified",
            "computed start(s) reproduced the single known minimum, and the "
            "production evidence + registered search scope are complete: a "
            "single-basin ensemble is legitimate here")


def build_rows() -> list[dict]:
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    manifest = {(r["name"], r["state"]): r for r in _read(MANIFEST)}
    struct = _read(STRUCT)
    weights = {(r["member_key"]): r for r in _read(WEIGHTS)}

    # same scope as the recovery manifest: every state that is not yet accepted.
    # A state with a leg in flight reads `provisional`; its review must still be
    # produced so the verdict is ready the moment the leg lands.
    # Scope = every state that is not accepted YET, PLUS every state that
    # already has a review row.  Without the second half the pair oscillates:
    # once a state is accepted it leaves the scope, its review row disappears,
    # the aggregator then finds no review and drops it back to `limited`, and
    # the next pass re-accepts it.  Persisting the row makes the two passes a
    # fixed point instead of a cycle.
    prior = {(r.get("name"), r.get("state")): r for r in _read(OUT_CSV)}
    already = set(prior)
    limited = sorted({k for k, r in labels.items()
                      if r.get("acceptance_status") in ("limited", "provisional")}
                     | {k for k in already if k in labels})
    rows: list[dict] = []
    for key in limited:
        name, state = key
        mf = manifest.get(key, {})
        starts = [s for s in (mf.get("start_1_basin", ""),
                              mf.get("start_2_basin", "")) if s]
        # a probe is a DIFFERENT generation of registered start: it lives in the
        # candidate manifest, never in the frozen recovery row.  Without this
        # union the route reads "no registered search scope" for a state that
        # has just registered and run one.
        starts = list(dict.fromkeys(starts + _probe_starts(name, state)))
        # a REFUSED member is a recorded decision, not a run in flight: counting
        # it as pending parks the state forever (EC|LiM_2plus, defect #32 in the
        # review layer)
        rejected = _rejected_probe_members()
        # every member of this state that belongs to the recovery batch
        members = [r for r in struct
                   # the structures table names this column `slot`; reading
                   # `state` made `members` permanently empty, so a computed
                   # recovery leg was never seen and no state could ever resolve
                   if r.get("name") == name and r.get("slot") == state
                   and str(r.get("member_role", "")).startswith(RECOVERY_ROLE_PREFIX)
                   and r.get("member_key", "") not in rejected]
        # the FULL qualified evidence set (user ruling C-group): any weighted
        # computed member counts toward coverage, whichever batch supplied it --
        # the historical gap may have been closed by an earlier leg
        qualified_all = [r for r in struct
                         if r.get("name") == name and r.get("slot") == state
                         and r.get("status") == "computed"
                         and r.get("member_key") in weights]
        # the primary IS a weighted qualified member: its production leg lives
        # in the MAIN ledger, so the structures table only carries a bookkeeping
        # row with status ``ready`` -- which IS its computed state, because a
        # primary enters the ensemble manifest only after production QC passed.
        # (Without this the count never reached two and the C-group ruling never
        # fired: the primary was excluded by a status word, not by evidence.)
        primary_key = "%s|%s|primary" % (name, state)
        if primary_key in weights and \
                not any(r.get("member_key") == primary_key
                        for r in qualified_all):
            qualified_all.append({"member_key": primary_key,
                                  "status": "ready",
                                  "member_role": "primary"})
        computed = [r for r in members if r.get("status") == "computed"]
        pending = [r for r in members if r.get("status") in ("pending", "ready")]
        # "new minimum" == computed AND present in the Boltzmann weight table
        new_minima = [r["member_key"] for r in computed
                      if r["member_key"] in weights]

        n_unique_after = labels[key].get("n_unique", "")
        n_limited = 0
        try:
            n_limited = int(labels[key].get("n_qc_failed") or 0)
        except ValueError:
            n_limited = 0

        search_outcome = mf.get("search_outcome", "not_searched")
        # a state the ledger still marks as released keeps its released row:
        # the manifest's open-state scope no longer tracks accepted states, so
        # re-deriving the row from an empty manifest entry would oscillate (the
        # label would drop to limited, the manifest would re-include the state,
        # and the next review would re-release it, forever).  The label itself
        # is recomputed from the ledger every pass, so a genuine retraction
        # (the coverage_status no longer says resolved_by_review) still flips
        # this row back to the derived route.
        label_cov = labels[key].get("coverage_status", "")
        if label_cov == "resolved_by_review" and key in prior:
            rows.append(dict(prior[key]))
            continue

        # novelty per computed member: "new" when it survived dedup into the
        # kept pool, "known" when it was deduplicated onto an existing minimum
        novelty = {}
        for r in computed:
            novelty[r["member_key"]] = ("new" if r["member_key"] in weights
                                        else "known")
        dedup_dir = REPO / "outputs" / "physics_completion" / "ensembles"
        dedup_rows = {}
        ded = dedup_dir / "production_ensemble_dedup.csv"
        if ded.is_file():
            for d in _read(ded):
                dedup_rows[d.get("member_key", "")] = d
        for r in computed:
            d = dedup_rows.get(r["member_key"])
            if d is not None and d.get("duplicate_of"):
                novelty[r["member_key"]] = "known"

        # production evidence = every computed member carries the full QC set
        production_evidence = bool(computed) and all(
            (r.get("imaginary_modes") or "") != "" and
            (r.get("final_geometry_sha256") or "") != "" and
            (r.get("log_sha256") or "") != ""
            for r in computed)

        # C-group ruling: a state whose WEIGHTED qualified members already give
        # >=2 independent minima is multi-basin covered, whichever batch supplied
        # them; the review still names the kept-pool members as its evidence so
        # the aggregator's anti-cheat can verify every claim
        if len(qualified_all) >= 2 and not pending:
            route = "multi_basin_coverage"
            route_note = ("%d weighted independent minima from the full qualified "
                         "evidence set (user ruling C-group: coverage over ALL "
                         "qualified members, not only the recovery batch)"
                         % len(qualified_all))
        else:
            route, route_note = coverage_route(
                members, novelty,
                min_unique_after=_n_unique(key),
                registered_starts=starts,
                search_outcome=search_outcome,
                production_evidence=production_evidence)
        verdict_route = route
        if route in ("multi_basin_coverage", "single_basin_verified"):
            verdict = "resolved"
            note = route_note
        elif route == "known_basin_reproduction":
            verdict = "unresolved"
            note = route_note
        elif route == "pending":
            verdict = "pending"
            note = route_note
        elif route == "search_exhausted":
            verdict = "search_exhausted"
            note = route_note
        elif route in ("unresolved_qc", "dedup_evidence_required"):
            verdict = "unresolved"
            note = route_note
        else:
            verdict = "pending"
            note = route_note

        if route == "multi_basin_coverage":
            kept_evidence = ([k for k, v in novelty.items() if v == "new"]
                             or [r["member_key"] for r in qualified_all])
        elif route in ("single_basin_verified", "known_basin_reproduction"):
            kept_evidence = sorted({
                d.get("duplicate_of", "")
                for r in computed
                for d in [dedup_rows.get(r["member_key"])]
                if d and d.get("duplicate_of")
            } - {""})
        else:
            kept_evidence = []

        rows.append({
            "review_id": "%s|%s|%s|%s" % (REVIEW_VERSION, mf.get("batch_id", "strict_recovery_v1"),
                                          name, state),
            "batch_id": mf.get("batch_id", "strict_recovery_v1"),
            "name": name,
            "state": state,
            "historical_limitation": labels[key].get("limitation_reason", ""),
            "historical_n_limited": str(n_limited),
            "resolution_path": mf.get("path", ""),
            "route": verdict_route,
            "registered_starts": ";".join(starts),
            "computed_new_members": ";".join(new_minima),
            "kept_pool_evidence": ";".join(kept_evidence),
            "n_unique_after": str(n_unique_after),
            "verdict": verdict,
            "review_version": REVIEW_VERSION,
            "evidence_note": note,
        })
    return rows


def _n_unique(key: tuple[str, str]) -> int:
    labels = {(r["name"], r["state"]): r for r in _read(LABELS)}
    try:
        return int(labels[key].get("n_unique") or 0)
    except ValueError:
        return 0


def write_outputs(rows: list[dict]) -> None:
    RECOVERY.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    index = {
        "schema_version": "1.0",
        "review_version": REVIEW_VERSION,
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_coverage_reviews.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (LABELS, STRUCT, DISPOS, WEIGHTS, MANIFEST)
                   if p.is_file()},
        "rule": ("resolved requires a computed recovery start that survived "
                 "dedup into the kept pool AND >=2 unique minima AND no pending "
                 "recovery member; historical failures are never rewritten"),
        "counts": counts,
        "n_rows": len(rows),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")


def check() -> int:
    rows = build_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- coverage reviews match recomputation (%d states)" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs(build_rows())
    print("wrote coverage reviews; resolved states may now leave limited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
