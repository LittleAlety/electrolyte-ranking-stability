#!/usr/bin/env python
"""Gate 1, ordering-consistency tier (R7): is the within-series ordering reproduced?

Why this script exists
----------------------
``docs/31_plan_revision_expert_review.md`` R7 splits Gate 1 into two levels:

* **absolute-calibration level** -- the 31 solution redox rows of
  ``data/anchors/solution_redox_anchors.csv`` traced to condition-matched primary
  measurements.  That level is *not* reached and is registered as a limitation
  (``data/anchors/solution_anchor_verification.md`` section 4.4).  It is
  deliberately **not** a Gate 1 blocker.
* **ordering-consistency level** -- the within-series relative ordering recorded in
  ``data/anchors/within_series_ordering.csv``, reproduced by the target model.
  This module evaluates that level; it is the only ordering-tier input to
  ``scripts/freeze_gates.py::evaluate_stage1``.

The criterion was pre-registered *before any comparison was run*
(``data/anchors/solution_anchor_verification.md`` sections 1-3, committed on
2026-10-02 ahead of the section 4 verification results).  Verbatim:

1. ``n_pairs >= 18`` -- usable within-series anchor pairs;
2. ``Kendall tau_b >= 0.9`` -- reused from the already-frozen strong tier,
   ``config/prereg.yaml`` section 2
   ``probabilistic_pair_ordering.thresholds.strong_i_gt_j``;
3. same-source -- every pair comes from one series (one paper / one apparatus /
   one criterion).  Cross-paper pooling of absolute values is forbidden here;
   that is the Xu-Ding-Jow 1999 argument (``docs/31`` R7 clue 3).

How the numbers are computed
----------------------------
Pairs are formed *inside* one ``(series_id, property)`` group only, so requirement
3 holds by construction.  A pair counts as usable when the experimental series
strictly orders the two species; pairs tied in the experiment carry no ordering
information and are reported separately (``n_pairs_tied_experiment``) instead of
being counted toward ``n_pairs``.

``tau_b`` is the tie-corrected Kendall coefficient over the pooled pair set,

    tau_b = (C - D) / sqrt((n0 - T_exp) * (n0 - T_model))

with ``n0`` every pair formed, ``C``/``D`` concordant/discordant, ``T_exp`` pairs
tied in the experiment and ``T_model`` pairs tied in the model.

Model values come from the frozen P1 core-set table
``outputs/week4/p1_core_set_derived.csv``: ``p1_ox_ev`` for
``oxidation_potential`` and ``p1_red_ev`` for ``reduction_potential``.  Those are
the ranking keys this project has reported since Week 4 (larger = harder to
oxidise / reduce = more stable), the same orientation as an experimental
potential in V vs Li/Li+.

Honesty note
------------
On 2026-10-02 the section 4 verification found **no retrievable within-series
values**: the Okoshi 2015 table and the Ue 1994/1997 tables sit behind the IOP
paywall, and the only openly available Egashira paper covers PC alone.  The table
shipped with this script therefore carries its header and no rows, ``n_pairs`` is
0, and the ordering tier does not close.  The script reports that outcome; it never
promotes a row to reach a threshold.

Output
------
With ``--json`` the payload below is the *only* thing written to stdout, so the
gate can parse it.  The same payload is always written to
``outputs/week2/series_rel_ordering_check.json``.

Exit status: 0 when the evaluation completed (whatever ``ok`` says), 1 when the
table itself is malformed, 2 on a usage error.

Usage
-----
    python scripts/check_series_rel_ordering.py [--json] [--table PATH] [--model PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TABLE = REPO_ROOT / "data" / "anchors" / "within_series_ordering.csv"
DEFAULT_MODEL = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
DEFAULT_OUT = REPO_ROOT / "outputs" / "week2" / "series_rel_ordering_check.json"

#: Pre-registered criterion -- do not retune after seeing a result.
MIN_PAIRS = 18
MIN_TAU_B = 0.9
THRESHOLD_SOURCE = (
    "config/prereg.yaml section 2 "
    "probabilistic_pair_ordering.thresholds.strong_i_gt_j = 0.9"
)
THRESHOLD_FROZEN_DATE = "2026-10-02"

#: experimental property -> (P1 core-set column, orientation)
PROPERTY_MODEL_COLUMN = {
    "oxidation_potential": "p1_ox_ev",
    "reduction_potential": "p1_red_ev",
}

REQUIRED_COLUMNS = ("series_id", "source_doi", "species", "property", "value_V")

#: Values closer together than this are treated as tied.
TIE_EPSILON = 1e-9


def _float(value):
    text = ("" if value is None else str(value)).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _sign(delta: float) -> int:
    if delta > TIE_EPSILON:
        return 1
    if delta < -TIE_EPSILON:
        return -1
    return 0


def load_table(path: Path):
    """Read the within-series table.  A file with no data rows is not an error."""

    if not path.exists():
        return [], ["within-series table missing: " + str(path)]
    rows = []
    problems = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing:
            return [], ["table header is missing column(s): " + ", ".join(missing)]
        for index, row in enumerate(reader, start=2):
            series = (row.get("series_id") or "").strip()
            species = (row.get("species") or "").strip()
            prop = (row.get("property") or "").strip()
            doi = (row.get("source_doi") or "").strip()
            value = _float(row.get("value_V"))
            if not (series or species or prop or doi or value is not None):
                continue
            if not series or not species or not prop:
                problems.append("row %d: series_id/species/property must all be non-empty" % index)
                continue
            if not doi.startswith("10."):
                problems.append(
                    "row %d: the same-source requirement needs a DOI in source_doi" % index
                )
                continue
            if prop not in PROPERTY_MODEL_COLUMN:
                problems.append(
                    "row %d: property %r is not one of %s"
                    % (index, prop, "/".join(sorted(PROPERTY_MODEL_COLUMN)))
                )
                continue
            if value is None:
                problems.append("row %d: value_V does not parse as a float" % index)
                continue
            rows.append(
                {
                    "series_id": series,
                    "source_doi": doi,
                    "species": species,
                    "property": prop,
                    "value_V": value,
                }
            )
    return rows, problems


def load_model(path: Path) -> dict:
    """Species -> P1 core-set row, keyed by the ``name`` column."""

    model = {}
    if not path.exists():
        return model
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            if name:
                model.setdefault(name, row)
    return model


def evaluate(table_path: Path, model_path: Path) -> dict:
    rows, problems = load_table(table_path)
    model = load_model(model_path)

    groups: dict = {}
    for row in rows:
        groups.setdefault((row["series_id"], row["property"]), []).append(row)

    concordant = discordant = 0
    ties_experiment = ties_model = 0
    n_pairs = n_pairs_total = n_pairs_tied_experiment = 0
    n_series = n_series_with_pairs = 0
    skipped_no_model = 0
    series_detail = []

    for (series, prop), group in sorted(groups.items()):
        n_series += 1
        column = PROPERTY_MODEL_COLUMN[prop]
        usable = []
        for row in group:
            record = model.get(row["species"])
            if record is None:
                skipped_no_model += 1
                continue
            model_value = _float(record.get(column))
            if model_value is None:
                skipped_no_model += 1
                continue
            usable.append((row["species"], row["value_V"], model_value))

        group_concordant = group_discordant = 0
        if len(usable) >= 2:
            n_series_with_pairs += 1
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                (_, exp_i, mod_i) = usable[i]
                (_, exp_j, mod_j) = usable[j]
                sign_exp = _sign(exp_i - exp_j)
                sign_mod = _sign(mod_i - mod_j)
                n_pairs_total += 1
                if sign_exp == 0:
                    n_pairs_tied_experiment += 1
                    ties_experiment += 1
                else:
                    n_pairs += 1
                if sign_mod == 0:
                    ties_model += 1
                if sign_exp == 0 or sign_mod == 0:
                    continue
                if sign_exp == sign_mod:
                    concordant += 1
                    group_concordant += 1
                else:
                    discordant += 1
                    group_discordant += 1
        if len(usable) >= 2:
            series_detail.append(
                {
                    "series_id": series,
                    "property": prop,
                    "source_doi": group[0]["source_doi"],
                    "n_species": len(usable),
                    "n_pairs": len(usable) * (len(usable) - 1) // 2,
                    "concordant": group_concordant,
                    "discordant": group_discordant,
                }
            )

    denominator = math.sqrt(max(n_pairs_total - ties_experiment, 0) * max(n_pairs_total - ties_model, 0))
    tau_b = (concordant - discordant) / denominator if denominator > 0 else None

    if not rows:
        reason = "no_within_series_values"
        detail = (
            "no verified within-series values on file (n_pairs=0); the absolute-calibration "
            "level is recorded as a limitation and this tier stays open"
        )
    elif problems:
        reason = "malformed_table"
        detail = "; ".join(problems[:3])
    elif n_pairs < MIN_PAIRS:
        reason = "insufficient_pairs"
        detail = "n_pairs=%d < %d" % (n_pairs, MIN_PAIRS)
    elif tau_b is None:
        reason = "tau_b_undefined"
        detail = "tau_b undefined: every usable pair is tied in the model or the experiment"
    elif tau_b < MIN_TAU_B:
        reason = "ordering_disagrees"
        detail = "tau_b=%.4f < %.2f over n_pairs=%d" % (tau_b, MIN_TAU_B, n_pairs)
    else:
        reason = "consistent"
        detail = "tau_b=%.4f >= %.2f over n_pairs=%d" % (tau_b, MIN_TAU_B, n_pairs)

    ok = reason == "consistent"
    return {
        "stage": 1,
        "tier": "ordering_consistency",
        "reference": "docs/31 R7; data/anchors/solution_anchor_verification.md 1-3",
        "ok": ok,
        "reason": reason,
        "detail": detail,
        "table": str(table_path.relative_to(REPO_ROOT)) if table_path.is_relative_to(REPO_ROOT) else str(table_path),
        "model": str(model_path.relative_to(REPO_ROOT)) if model_path.is_relative_to(REPO_ROOT) else str(model_path),
        "criterion": {
            "min_pairs": MIN_PAIRS,
            "min_tau_b": MIN_TAU_B,
            "threshold_source": THRESHOLD_SOURCE,
            "frozen_date": THRESHOLD_FROZEN_DATE,
        },
        "n_rows": len(rows),
        "n_series": n_series,
        "n_series_with_pairs": n_series_with_pairs,
        "n_pairs": n_pairs,
        "n_pairs_total": n_pairs_total,
        "n_pairs_tied_experiment": n_pairs_tied_experiment,
        "n_skipped_missing_model_value": skipped_no_model,
        "concordant": concordant,
        "discordant": discordant,
        "tau_b": tau_b,
        "problems": problems,
        "series": series_detail,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true", help="write the payload to stdout and nothing else")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = evaluate(args.table, args.model)

    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
            handle.write("\n")
    except OSError as exc:
        print("could not write %s: %s" % (args.out, exc), file=sys.stderr)
        return 1

    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))
        sys.stdout.write("\n")
    else:
        print("Gate 1 ordering-consistency tier (R7)")
        print("  table           : %s" % payload["table"])
        print("  model           : %s" % payload["model"])
        print("  rows            : %d over %d series" % (payload["n_rows"], payload["n_series"]))
        print("  usable pairs    : %d (min %d)" % (payload["n_pairs"], MIN_PAIRS))
        print("  tau_b           : %s" % ("n/a" if payload["tau_b"] is None else "%.4f" % payload["tau_b"]))
        print("  verdict         : %s (%s)" % ("CLOSED" if payload["ok"] else "OPEN", payload["reason"]))
        print("  detail          : %s" % payload["detail"])
        print("  wrote           : %s" % args.out)
    return 1 if payload["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
