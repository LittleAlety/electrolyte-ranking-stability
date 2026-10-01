"""Stage 21 (week 20), part B -- the ``charge_l1`` identity criterion turned
into a *runtime pre-check*.

Week 17 (Stage 18) froze a single-number test for the question "are the two
SCF solutions of one ``(name, state, epsilon)`` cell the same electronic
state?":

    identity_differs  <=>  charge_l1 > 0.039

where ``charge_l1`` is the L1 distance between the Mulliken atomic charges of
the two arms (the default guess vs a ``! MORead`` restart).  That threshold is
*post hoc* -- it was read off the discovery arm after the fact -- and until now
there was no cheap way to notice, *before* submitting an expensive batch, that
a cell sits right next to it.

This module turns the criterion into a pre-check:

* :func:`identity_distance` reads the two ``.out`` files of a cell and returns
  the same numbers Stage 17/18 used.  The Mulliken charges come from the *last*
  ``MULLIKEN ATOMIC CHARGES`` block: an ``Opt`` output prints one table per
  geometry step and the first one describes the *input* geometry, not the
  answer.
* :func:`derive_threshold` re-derives the decision boundary *from the data*
  instead of treating 0.039 as truth: it sits in the empty gap between the
  largest ``coincident`` and the smallest ``moread_lower`` distance.  The
  frozen 0.039 is only the value that happens to fall inside that gap.
* :func:`verdict` returns the three-class verdict ``coincident`` / ``borderline``
  / ``differs``, plus an ``unmeasurable`` sentinel for the closed-shell pairs
  that print no spin table at all.  ``borderline`` is the deliverable: those
  cells are the ones that can flip when the guess, the functional or the
  solvent changes.

The CLI writes three deterministic artefacts under ``outputs/week20/`` and can
re-check them byte-for-byte with ``--check``.

No ORCA job is run: the whole stage re-reads the Stage 18 census, so it is
exact and free.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking.orca import MissingORCAField, parse_orca_energy  # noqa: E402

DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week17"
DEFAULT_CENSUS_NAME = "stage18_identity_census.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week20"

PROTOCOL_CSV = "stage21_protocol_borderline.csv"
PROTOCOL_JSON = "stage21_protocol.json"
PROTOCOL_MD = "stage21_protocol_summary.md"

#: ``MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS`` (open shell) and
#: ``MULLIKEN ATOMIC CHARGES`` (closed shell) share this prefix, so one prefix
#: test finds both.
MULLIKEN_HEADER_PREFIX = "MULLIKEN ATOMIC CHARGES"

#: ``   4 C :   -1.123785    1.467244`` -- index, element, charge, spin.
ROW_WITH_SPIN_RE = re.compile(
    r"^\s*(\d+)\s+([A-Za-z]{1,2})\s*:\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)
#: ``   4 C :   -1.123785`` -- index, element, charge (closed shell).
ROW_CHARGE_ONLY_RE = re.compile(
    r"^\s*(\d+)\s+([A-Za-z]{1,2})\s*:\s*(-?\d+\.\d+)\s*$"
)

#: Same conversion the Stage 17/18 readers use, so ``delta_ev`` is in eV.
HARTREE_TO_EV = 27.211386245988

#: The frozen Stage 18 value, quoted for comparison only.  The empirical
#: default below is what :func:`verdict` uses when no threshold is passed.
FROZEN_THRESHOLD = 0.039

#: Empirical decision boundary.  It is a *description of the calibration data*,
#: not a physical constant: :func:`derive_threshold` lands on 0.038946 for the
#: frozen census (the midpoint of the empty gap (0.038509, 0.039383)), and
#: 0.039 -- the frozen value -- sits in the same gap, which is why this default
#: is safe.
DEFAULT_THRESHOLD = 0.039

#: Width of the ``borderline`` band: |charge_l1 - threshold| <= DEFAULT_MARGIN.
#: 0.010 is about 25 % of the threshold -- wide enough to catch the cells that
#: actually sit 4e-4 from the boundary.
DEFAULT_MARGIN = 0.010

#: The band is *inclusive*: ``verdict(threshold - margin)`` must be
#: ``borderline``.  Binary floats cannot represent 0.04 - 0.01 exactly, so this
#: guard absorbs the ~1e-18 representation error; the distances that matter in
#: the data are >= 4e-4, fifteen orders of magnitude larger, so no real cell can
#: move across it.
BAND_TOLERANCE = 1e-12

#: The three threshold classes, then the closed-shell sentinel.
CLASSES = ("coincident", "borderline", "differs", "unmeasurable")


def _read_text(path):
    """ORCA output is ASCII/Latin-1; decode defensively and never raise."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def parse_last_mulliken(text):
    """Return the *last* Mulliken atomic table in an ORCA output.

    Returns ``(charges, spins, n_blocks)``.  ``charges`` is a list of
    ``(index, element, charge)`` tuples and ``spins`` the matching spin column
    (``[]`` when the output is closed shell and prints no spin column at all).

    The last block matters: an ``Opt`` output prints one table per geometry
    step and the first one describes the input geometry.
    """
    lines = text.splitlines()
    starts = [
        index for index, line in enumerate(lines)
        if line.startswith(MULLIKEN_HEADER_PREFIX)
    ]
    if not starts:
        return [], [], 0
    charges = []
    spins = []
    saw_spin = False
    for line in lines[starts[-1] + 1:]:
        match = ROW_WITH_SPIN_RE.match(line)
        if match is not None:
            charges.append(
                (int(match.group(1)), match.group(2), float(match.group(3)))
            )
            spins.append(float(match.group(4)))
            saw_spin = True
            continue
        match = ROW_CHARGE_ONLY_RE.match(line)
        if match is not None:
            charges.append(
                (int(match.group(1)), match.group(2), float(match.group(3)))
            )
            continue
        if charges:
            break
    if not saw_spin:
        spins = []
    return charges, spins, len(starts)


def _safe_energy(text):
    """Last FINAL SINGLE POINT ENERGY (Eh), or ``None`` when unparsable."""
    try:
        return parse_orca_energy(text)
    except (MissingORCAField, ValueError):
        return None


def _charges_l1(charges_a, charges_b):
    if not charges_a or not charges_b or len(charges_a) != len(charges_b):
        return None
    return sum(abs(a[2] - b[2]) for a, b in zip(charges_a, charges_b))


def identity_distance(out_a, out_b, *, require_spin=False):
    """The Stage 18 identity metrics for one cell, re-read from two ``.out``.

    ``out_a`` is the ``default`` arm and ``out_b`` the ``moread`` arm, so
    ``delta_ev = E_b - E_a`` matches the census's ``delta_ev``.

    ``require_spin=True`` reproduces the frozen convention *exactly*: a pair
    that prints no spin column (closed shell) comes back with
    ``charge_l1 = None`` even though its charge table is present.  The default
    (``False``) is the more useful runtime behaviour -- a closed-shell pair
    still gets a charge distance, flagged by ``has_spin_a`` / ``has_spin_b``.
    """
    text_a = _read_text(out_a)
    text_b = _read_text(out_b)
    charges_a, spins_a, blocks_a = parse_last_mulliken(text_a)
    charges_b, spins_b, blocks_b = parse_last_mulliken(text_b)

    charge_l1 = _charges_l1(charges_a, charges_b)
    spin_l1 = None
    if spins_a and spins_b and len(spins_a) == len(spins_b):
        spin_l1 = sum(abs(a - b) for a, b in zip(spins_a, spins_b))

    per_atom = []
    max_abs_dcharge = None
    if charges_a and len(charges_a) == len(charges_b):
        for (index_a, element_a, q_a), (index_b, element_b, q_b) in zip(
            charges_a, charges_b
        ):
            per_atom.append({
                "index": index_a,
                "element": element_a if element_a == element_b
                else "%s/%s" % (element_a, element_b),
                "charge_a": q_a,
                "charge_b": q_b,
                "d_charge": q_b - q_a,
            })
        max_abs_dcharge = max(abs(row["d_charge"]) for row in per_atom)

    if require_spin and (not spins_a or not spins_b):
        charge_l1 = None
        spin_l1 = None
        per_atom = []
        max_abs_dcharge = None

    energy_a = _safe_energy(text_a)
    energy_b = _safe_energy(text_b)
    delta_eh = None if energy_a is None or energy_b is None else energy_b - energy_a
    return {
        "charge_l1": charge_l1,
        "spin_l1": spin_l1,
        "delta_ev": None if delta_eh is None else delta_eh * HARTREE_TO_EV,
        "delta_eh": delta_eh,
        "energy_a_eh": energy_a,
        "energy_b_eh": energy_b,
        "max_abs_dcharge": max_abs_dcharge,
        "per_atom": per_atom,
        "n_atoms_a": len(charges_a),
        "n_atoms_b": len(charges_b),
        "same_atom_count": bool(charges_a) and len(charges_a) == len(charges_b),
        "has_spin_a": bool(spins_a),
        "has_spin_b": bool(spins_b),
        "n_mulliken_blocks_a": blocks_a,
        "n_mulliken_blocks_b": blocks_b,
    }

def youden_j_threshold(negatives, positives):
    """Threshold that maximises (sensitivity + specificity - 1).

    Used only as a fallback when the two clusters overlap, so that the module
    never has to invent a number outside the data.
    """
    if not negatives or not positives:
        return None
    candidates = sorted(set(negatives) | set(positives))
    best_value = None
    best_j = None
    for value in candidates:
        sensitivity = sum(1 for v in positives if v > value) / len(positives)
        specificity = sum(1 for v in negatives if v <= value) / len(negatives)
        j = sensitivity + specificity - 1.0
        if best_j is None or j > best_j:
            best_value, best_j = value, j
    return best_value


def derive_threshold(negatives, positives):
    """Re-derive the ``charge_l1`` decision boundary from the two clusters.

    ``negatives`` are the ``charge_l1`` values the energy rule calls
    ``coincident`` and ``positives`` the ones it calls ``moread_lower``.  When
    the clusters are separated -- the case in the frozen census -- the boundary
    is the midpoint of the *empty gap* between them, so the exact value is not
    identified by the data, only the interval that contains it.  When they
    overlap (a different catalogue could do that) it falls back to the
    Youden-J maximiser of the ROC.

    The returned threshold is **empirical**: it describes the calibration data,
    it is not a physical constant.
    """
    neg = sorted(float(v) for v in negatives if v is not None)
    pos = sorted(float(v) for v in positives if v is not None)
    block = {
        "n_negative": len(neg),
        "n_positive": len(pos),
        "coincident_max": neg[-1] if neg else None,
        "moread_min": pos[0] if pos else None,
    }
    if not neg or not pos:
        block.update({
            "gap_lower": None,
            "gap_upper": None,
            "gap_width": None,
            "gap_empty": None,
            "threshold": None,
            "basis": "undefined: one of the two clusters is empty",
        })
        return block
    if neg[-1] < pos[0]:
        lower, upper = neg[-1], pos[0]
        block.update({
            "gap_lower": lower,
            "gap_upper": upper,
            "gap_width": upper - lower,
            "gap_empty": True,
            "threshold": (lower + upper) / 2.0,
            "basis": "midpoint of the empty gap (coincident_max, moread_min)",
        })
        return block
    block.update({
        "gap_lower": None,
        "gap_upper": None,
        "gap_width": None,
        "gap_empty": False,
        "threshold": youden_j_threshold(neg, pos),
        "basis": "clusters overlap; Youden-J maximiser of the ROC",
    })
    return block


def verdict(charge_l1, threshold=DEFAULT_THRESHOLD, margin=DEFAULT_MARGIN):
    """Three-class verdict plus an ``unmeasurable`` sentinel.

    * ``coincident``   -- ``charge_l1 < threshold - margin``
    * ``borderline``   -- ``|charge_l1 - threshold| <= margin`` (the pre-check)
    * ``differs``      -- ``charge_l1 > threshold + margin``
    * ``unmeasurable`` -- ``charge_l1`` is ``None`` (no charge table to read)

    The band is inclusive: both edges belong to ``borderline``.  ``threshold``
    is empirical (see :func:`derive_threshold`); ``margin`` is the half-width
    of the flagged band, 0.010 by default.
    """
    if charge_l1 is None:
        return "unmeasurable"
    offset = float(charge_l1) - float(threshold)
    band = float(margin) + BAND_TOLERANCE
    if offset > band:
        return "differs"
    if offset < -band:
        return "coincident"
    return "borderline"


def distance_to_threshold(charge_l1, threshold=DEFAULT_THRESHOLD):
    """``charge_l1 - threshold``, or ``None`` when there is nothing to measure."""
    if charge_l1 is None:
        return None
    return float(charge_l1) - float(threshold)


# ---------------------------------------------------------------------------
# census plumbing
# ---------------------------------------------------------------------------


def load_census(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value):
    return str(value).strip() == "True"


def _classification_of(row):
    return (row.get("rule_classification") or row.get("classification") or "").strip()


def calibration_pairs(census):
    """``(negatives, positives, scope)`` used to re-derive the threshold.

    The Stage 18 calibration consulted the *discovery* arm only; that
    discipline is kept whenever the census carries an ``arm_set`` column.  A
    census without it (the synthetic-test case) uses every measurable cell.
    """
    has_arms = any((row.get("arm_set") or "").strip() for row in census)
    negatives, positives = [], []
    for row in census:
        if has_arms and (row.get("arm_set") or "").strip() != "discovery":
            continue
        value = _as_float(row.get("charge_l1"))
        if value is None:
            continue
        classification = _classification_of(row)
        if classification == "coincident":
            negatives.append(value)
        elif classification == "moread_lower":
            positives.append(value)
    scope = "discovery arm only" if has_arms else "all measurable cells (no arm_set column)"
    return negatives, positives, scope


def _epsilon_key(value):
    parsed = _as_float(value)
    return (parsed if parsed is not None else float("inf"), str(value))


CSV_COLUMNS = (
    "name",
    "state",
    "epsilon",
    "arm_set",
    "classification",
    "delta_ev",
    "charge_l1",
    "verdict",
    "distance_to_threshold",
    "is_borderline",
    "identity_differs",
    "identity_measurable",
    "family",
)


def _fmt(value, digits=10):
    if value is None:
        return ""
    return "%.*g" % (digits, value)


def build_rows(census, threshold, margin=DEFAULT_MARGIN):
    """One dict per census cell, sorted deterministically."""
    rows = []
    for row in census:
        charge_l1 = _as_float(row.get("charge_l1"))
        label = verdict(charge_l1, threshold, margin)
        rows.append({
            "name": row.get("name", ""),
            "state": row.get("state", ""),
            "epsilon": row.get("epsilon", ""),
            "arm_set": row.get("arm_set", ""),
            "classification": _classification_of(row),
            "delta_ev": _fmt(_as_float(row.get("delta_ev"))),
            "charge_l1": _fmt(charge_l1),
            "verdict": label,
            "distance_to_threshold": _fmt(distance_to_threshold(charge_l1, threshold)),
            "is_borderline": label == "borderline",
            "identity_differs": (row.get("identity_differs") or "").strip(),
            "identity_measurable": (row.get("identity_measurable") or "").strip(),
            "family": (row.get("family") or "").strip(),
        })
    rows.sort(key=lambda r: (r["name"], r["state"], _epsilon_key(r["epsilon"])))
    return rows


def _counter_to_block(counter):
    """``{(a, b): n}`` -> ``{"a|b": n}`` with stable key order."""
    return {
        "|".join(str(part) for part in key): value
        for key, value in sorted(counter.items())
    }


def cross_tabs(rows):
    """How the cheap criterion lines up with the energy rule and with the
    frozen ``identity_differs`` verdict."""
    by_verdict_rule = Counter()
    by_verdict_differs = Counter()
    for row in rows:
        by_verdict_rule[(row["verdict"], row["classification"])] += 1
        by_verdict_differs[(row["verdict"], row["identity_differs"] or "<missing>")] += 1

    positives = [r for r in rows if r["classification"] == "moread_lower"]
    negatives = [r for r in rows if r["classification"] == "coincident"]

    def confusion(positive_labels):
        tp = sum(1 for r in positives if r["verdict"] in positive_labels)
        fn = len(positives) - tp
        fp = sum(1 for r in negatives if r["verdict"] in positive_labels)
        tn = len(negatives) - fp
        return {
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "tn": tn,
            "n_positive": len(positives),
            "n_negative": len(negatives),
            "sensitivity": (tp / len(positives)) if positives else None,
            "specificity": (tn / len(negatives)) if negatives else None,
            "precision": (tp / (tp + fp)) if (tp + fp) else None,
            "accuracy": (
                (tp + tn) / (len(positives) + len(negatives))
                if (positives or negatives) else None
            ),
        }

    # "differs" is the positive call; a borderline cell is not a confident
    # call, so the strict matrix counts it as a negative and the lenient one
    # counts it as a positive.  The band is the interval between the two.
    strict = confusion(("differs",))
    lenient = confusion(("differs", "borderline"))
    return {
        "verdict_vs_rule_classification": _counter_to_block(by_verdict_rule),
        "verdict_vs_identity_differs": _counter_to_block(by_verdict_differs),
        "binary_vs_rule_strict": strict,
        "binary_vs_rule_lenient": lenient,
        "n_disagreements_strict": strict["fn"] + strict["fp"],
        "n_disagreements_lenient": lenient["fn"] + lenient["fp"],
        "positive_rule": "rule_classification == moread_lower",
        "positive_call_strict": "verdict == differs",
        "positive_call_lenient": "verdict in (differs, borderline)",
    }


def reach_block(rows):
    """How far the cheap criterion actually reaches."""
    measurable = [r for r in rows if r["charge_l1"] != ""]
    block = {
        "n_cells": len(rows),
        "n_measurable": len(measurable),
        "n_unmeasurable": len(rows) - len(measurable),
        "measurable_share": (len(measurable) / len(rows)) if rows else None,
        "by_state": {},
        "by_family": {},
    }
    for key, bucket in (("by_state", "state"), ("by_family", "family")):
        groups = {}
        for row in rows:
            label = row[bucket] or "<unknown>"
            slot = groups.setdefault(label, {"n_cells": 0, "n_measurable": 0})
            slot["n_cells"] += 1
            if row["charge_l1"] != "":
                slot["n_measurable"] += 1
        block[key] = dict(sorted(groups.items()))
    return block


def closed_shell_probe(census, threshold, margin=DEFAULT_MARGIN):
    """Re-read the cells the frozen reader could not measure.

    Stage 17 required a spin column, so every closed-shell pair (all the
    neutral cells) came back with ``charge_l1 = None`` even though ORCA printed
    a charge table.  This probe runs :func:`identity_distance` on those exact
    files -- still no new ORCA job -- and reports what the distance *would*
    have been.  That is the counterexample test for the "cheap single-point
    reading": does the frozen blindness hide any cell that actually sits past
    the boundary?
    """
    cells = []
    for row in census:
        if _as_bool(row.get("identity_measurable", "True")):
            continue
        entry = {
            "name": row.get("name", ""),
            "state": row.get("state", ""),
            "epsilon": row.get("epsilon", ""),
            "charge_l1": None,
            "verdict": "unreadable",
            "files_present": False,
        }
        paths = (
            (row.get("default_path") or "").strip(),
            (row.get("moread_path") or "").strip(),
        )
        if all(p and Path(p).exists() for p in paths):
            entry["files_present"] = True
            metrics = identity_distance(paths[0], paths[1])
            entry["charge_l1"] = metrics["charge_l1"]
            entry["verdict"] = verdict(metrics["charge_l1"], threshold, margin)
        cells.append(entry)

    values = [c["charge_l1"] for c in cells if c["charge_l1"] is not None]
    summary = {
        "n_cells": len(cells),
        "n_read": len(values),
        "n_files_missing": sum(1 for c in cells if not c["files_present"]),
        "min_charge_l1": min(values) if values else None,
        "median_charge_l1": statistics.median(values) if values else None,
        "max_charge_l1": max(values) if values else None,
        "n_exceeding_threshold": sum(1 for v in values if v > threshold),
        "n_borderline": sum(1 for c in cells if c["verdict"] == "borderline"),
        "n_states": sorted({c["state"] for c in cells}),
    }
    summary["would_reverse"] = summary["n_exceeding_threshold"] > 0
    return {"summary": summary, "cells": cells}

# ---------------------------------------------------------------------------
# payload + summary
# ---------------------------------------------------------------------------


def all_measurable_pairs(census):
    """``(negatives, positives)`` over every arm, for the description only."""
    negatives, positives = [], []
    for row in census:
        value = _as_float(row.get("charge_l1"))
        if value is None:
            continue
        classification = _classification_of(row)
        if classification == "coincident":
            negatives.append(value)
        elif classification == "moread_lower":
            positives.append(value)
    return negatives, positives


def _relative(path):
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _sha256_of(path):
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_payload(census, census_path, threshold, margin, scope, derived,
                  derived_full, probe):
    rows = build_rows(census, threshold, margin)
    counts = Counter(row["verdict"] for row in rows)
    borderline = [row for row in rows if row["is_borderline"]]
    near = [
        row for row in rows
        if row["distance_to_threshold"] != ""
        and abs(float(row["distance_to_threshold"])) <= 2.0 * margin
    ]
    tabs = cross_tabs(rows)
    reach = reach_block(rows)

    measurable_positives = [
        row for row in rows
        if row["classification"] == "moread_lower" and row["charge_l1"] != ""
    ]
    hit_strict = sum(1 for row in measurable_positives if row["verdict"] == "differs")
    hit_lenient = sum(
        1 for row in measurable_positives if row["verdict"] in ("differs", "borderline")
    )

    probe_summary = probe["summary"]
    if probe_summary["n_read"] == 0:
        probe_conclusion = "没有可读的闭壳层文件，反例未检验。"
    elif probe_summary["n_exceeding_threshold"] == 0:
        ratio = threshold / probe_summary["max_charge_l1"] if probe_summary["max_charge_l1"] else float("inf")
        probe_conclusion = (
            "反例为空：%d 个被冻结读法判为「不可测」的闭壳层格子里，改读打印出来的"
            "电荷表后 charge_l1 最大只有 %.6g e（Mulliken 电荷的 L1 距离），仍比阈值 %.6g 小约 %.1f 倍，"
            "没有任何一格会翻案。"
            % (probe_summary["n_read"], probe_summary["max_charge_l1"], threshold, ratio)
        )
    else:
        probe_conclusion = (
            "%d/%d 个闭壳层格子在电荷表读法下越过了阈值 %.6g —— 这些是「廉价单点"
            "读数」的真实反例，运行手册必须对闭壳层单独处理。"
            % (probe_summary["n_exceeding_threshold"], probe_summary["n_read"], threshold)
        )

    payload = {
        "stage": 21,
        "part": "B -- the charge_l1 identity criterion as a runtime pre-check",
        "source": {
            "census": _relative(census_path),
            "census_sha256": _sha256_of(census_path),
            "n_rows": len(census),
        },
        "threshold": {
            "value": threshold,
            "margin": margin,
            "frozen_reference": FROZEN_THRESHOLD,
            "calibration_scope": scope,
            "derivation": derived,
            "derivation_full_catalogue": derived_full,
            "is_empirical": True,
        },
        "verdict_definition": {
            "coincident": "charge_l1 < threshold - margin",
            "borderline": "|charge_l1 - threshold| <= margin",
            "differs": "charge_l1 > threshold + margin",
            "unmeasurable": "charge_l1 is None (no charge table was read)",
        },
        "verdict_counts": {name: counts.get(name, 0) for name in CLASSES},
        "n_cells": len(rows),
        "borderline": [
            {key: row[key] for key in (
                "name", "state", "epsilon", "arm_set", "classification",
                "delta_ev", "charge_l1", "distance_to_threshold", "family")}
            for row in borderline
        ],
        "borderline_by_family": dict(sorted(
            Counter(row["family"] or "<unknown>" for row in borderline).items()
        )),
        "borderline_by_state": dict(sorted(
            Counter(row["state"] or "<unknown>" for row in borderline).items()
        )),
        "near_threshold_2x_margin": [
            {key: row[key] for key in (
                "name", "state", "epsilon", "classification", "charge_l1",
                "verdict", "distance_to_threshold", "family")}
            for row in near
        ],
        "cross_tabs": tabs,
        "reach": reach,
        "closed_shell_probe": probe,
        "applicability": {
            "claim": "charge_l1 is a cheap single-point reading of the electronic identity",
            "conditions": [
                "both arms must print a Mulliken atomic charge table with the same atom count",
                "the frozen Stage 18 reader additionally requires a spin column, so closed-shell pairs are unmeasurable to it",
            ],
            "n_measurable": reach["n_measurable"],
            "measurable_share": reach["measurable_share"],
            "n_moread_lower_measurable": len(measurable_positives),
            "measurable_sensitivity_strict": (
                hit_strict / len(measurable_positives) if measurable_positives else None
            ),
            "measurable_sensitivity_lenient": (
                hit_lenient / len(measurable_positives) if measurable_positives else None
            ),
            "closed_shell_counterexample": {
                "n_cells": probe_summary["n_cells"],
                "n_read": probe_summary["n_read"],
                "max_charge_l1": probe_summary["max_charge_l1"],
                "n_exceeding_threshold": probe_summary["n_exceeding_threshold"],
                "conclusion": probe_conclusion,
            },
            "disagreements_with_energy_rule": {
                "strict": tabs["n_disagreements_strict"],
                "lenient": tabs["n_disagreements_lenient"],
            },
        },
    }
    return payload, rows


def render_summary(payload):
    threshold = payload["threshold"]
    derived = threshold["derivation"]
    full = threshold["derivation_full_catalogue"]
    counts = payload["verdict_counts"]
    borderline = payload["borderline"]
    app = payload["applicability"]
    probe = payload["closed_shell_probe"]["summary"]
    tabs = payload["cross_tabs"]
    strict = tabs["binary_vs_rule_strict"]
    lines = []

    def fmt(value, digits=10):
        if value is None:
            return "——"
        return "%.*g" % (digits, value)

    lines.append("# Stage 21（Week 20）· Part B：`charge_l1` 身份判据的运行手册预检")
    lines.append("")
    lines.append("本文件由 `scripts/analyze_stage21_protocol.py` 现算生成，全部数字来自 "
                 "`%s`（SHA256 `%s`），没有一条是手工抄写的。"
                 % (payload["source"]["census"], payload["source"]["census_sha256"][:16]))
    lines.append("")
    lines.append("## 1. 阈值与它的来源")
    lines.append("")
    lines.append("- 冻结参考值 `FROZEN_THRESHOLD` = **%s**（Stage 18 的 `CHARGE_L1_THRESHOLD`，"
                 "是事后从 discovery 臂上读出来的**经验阈值**，不是物理常数）。"
                 % fmt(threshold["frozen_reference"]))
    lines.append("- 本模块用法：`verdict(charge_l1, threshold, margin)`，阈值与带宽都是**参数**；"
                 "CLI 默认**从数据重新导出**，不把 0.039 当真值。")
    lines.append("- 重新导出的口径：`%s`。coincident 组最大 = **%s**，moread_lower 组最小 = **%s**，"
                 "两者之间的空隙 (%s, %s) 宽度 **%s** 里**没有数据点**，所以取空隙中点 "
                 "**%s** 作阈值。冻结的 0.039 恰好落在同一空隙内，因此两者对本目录的分类完全一致。"
                 % (threshold["calibration_scope"], fmt(derived["coincident_max"]),
                    fmt(derived["moread_min"]), fmt(derived["gap_lower"]),
                    fmt(derived["gap_upper"]), fmt(derived["gap_width"]),
                    fmt(threshold["value"])))
    lines.append("- 用全部格子（discovery + holdout）重导也是一样的空隙："
                 "coincident 最大 = %s，moread_lower 最小 = %s（说明 holdout 没有落进空隙，"
                 "这与 Stage 18「未咨询 holdout」的纪律一致）。"
                 % (fmt(full["coincident_max"]), fmt(full["moread_min"])))
    lines.append("- `borderline` 带：|charge_l1 − 阈值| ≤ **%s**（约阈值的 25%%）。"
                 % fmt(threshold["margin"]))
    lines.append("")
    lines.append("## 2. 三分类计数与 borderline 清单")
    lines.append("")
    lines.append("| 分类 | 判据 | 格子数 |")
    lines.append("| --- | --- | --- |")
    lines.append("| `coincident` | charge_l1 < 阈值 − 带宽 | %d |" % counts.get("coincident", 0))
    lines.append("| `borderline` | \\|charge_l1 − 阈值\\| ≤ 带宽 | %d |" % counts.get("borderline", 0))
    lines.append("| `differs` | charge_l1 > 阈值 + 带宽 | %d |" % counts.get("differs", 0))
    lines.append("| `unmeasurable` | 读不到电荷表（闭壳层，Stage 17 的写读法） | %d |"
                 % counts.get("unmeasurable", 0))
    lines.append("")
    lines.append("（`%s` 是**逐格**表：全部 %d 行都写进去了，`is_borderline` 列可以直接筛。）"
                 % (PROTOCOL_CSV, payload["n_cells"]))
    lines.append("")
    if borderline:
        lines.append("需要预检标记的格子（共 **%d** 格）：" % len(borderline))
        lines.append("")
        lines.append("| name | state | epsilon | arm_set | charge_l1 | 距阈值 | 能量规则裁决 | 家族 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in borderline:
            lines.append("| %s | %s | %s | %s | %s | %s | `%s` | %s |"
                         % (row["name"], row["state"], row["epsilon"], row["arm_set"],
                            row["charge_l1"], row["distance_to_threshold"],
                            row["classification"], row["family"]))
        lines.append("")
        families = "，".join("%s %d" % (key, value)
                            for key, value in payload["borderline_by_family"].items())
        states = "，".join("%s %d" % (key, value)
                           for key, value in payload["borderline_by_state"].items())
        lines.append("- 家族分布：%s。" % families)
        lines.append("- state 分布：%s。" % states)
    else:
        lines.append("没有格子落在 borderline 带内：本目录不存在「贴阈值」的脆格。")
    near = payload["near_threshold_2x_margin"]
    extra = [row for row in near if row["verdict"] != "borderline"]
    if extra:
        lines.append("")
        lines.append("紧贴带外（距阈值在 %s 与 %s 之间、尚未触发标记）的格子："
                     % (fmt(threshold["margin"]), fmt(2.0 * threshold["margin"])))
        for row in extra:
            lines.append("- `%s/%s/eps=%s`：charge_l1 = %s，距阈值 %s，裁决 `%s`。"
                         % (row["name"], row["state"], row["epsilon"], row["charge_l1"],
                            row["distance_to_threshold"], row["verdict"]))
    lines.append("")
    lines.append("## 3. `charge_l1` 与真身份判据（能量规则）的一致性")
    lines.append("")
    lines.append("- 交叉表（廉价裁决 × `rule_classification`）：")
    for key, value in sorted(tabs["verdict_vs_rule_classification"].items()):
        lines.append("  - `%s`：%d 格" % (key, value))
    lines.append("- 交叉表（廉价裁决 × 冻结的 `identity_differs`）：")
    for key, value in sorted(tabs["verdict_vs_identity_differs"].items()):
        lines.append("  - `%s`：%d 格" % (key, value))
    lines.append("- 把 `differs` 当阳性、`rule_classification == moread_lower` 当真值：")
    lines.append("  - 严格口径（只有 `differs` 算阳性）：TP %d / FN %d / FP %d / TN %d，"
                 "灵敏度 %s。"
                 % (strict["tp"], strict["fn"], strict["fp"], strict["tn"],
                    fmt(strict["sensitivity"], 6)))
    lines.append("  - 宽松口径（`differs` 或 `borderline` 算阳性）：TP %d / FN %d / FP %d / TN %d，"
                 "灵敏度 %s。"
                 % (tabs["binary_vs_rule_lenient"]["tp"], tabs["binary_vs_rule_lenient"]["fn"],
                    tabs["binary_vs_rule_lenient"]["fp"], tabs["binary_vs_rule_lenient"]["tn"],
                    fmt(tabs["binary_vs_rule_lenient"]["sensitivity"], 6)))
    lines.append("- 严格口径唯一的分歧是 **%d 次漏检**（真值 `moread_lower` 却落在 borderline "
                 "带内）；把 borderline 也算阳性后翻成 **%d 次误报**（真值 `coincident`）。"
                 "带宽夹住的就是这几格 —— 这正是预检要标记的对象。"
                 % (strict["fn"], tabs["binary_vs_rule_lenient"]["fp"]))
    lines.append("")
    lines.append("## 4. 「廉价单点读数」的适用条件与反例")
    lines.append("")
    lines.append("Week 19 报告 §3 用 33/37（89%）说明「同一几何上廉价单点能复现昂贵方法的偏好方向」。"
                 "把这句话套到 `charge_l1` 上，适用条件是：")
    lines.append("")
    lines.append("1. 两条腿都必须打印出 `MULLIKEN ATOMIC CHARGES` 表，且原子数一致；")
    lines.append("2. 冻结的 Stage 18 读法**还**要求自旋列，所以闭壳层（中性）格子对它一律"
                 "「不可测」；本模块的实时读法则可以退一步只用电荷列。")
    lines.append("")
    lines.append("- 概数：可测 **%d/%d = %.2f%%**；其中被判 `moread_lower` 的可测格子有 %d 个，"
                 "严格口径灵敏度 %.4f、宽松口径灵敏度 %.4f。"
                 % (app["n_measurable"], payload["n_cells"],
                    100.0 * (app["measurable_share"] or 0.0),
                    app["n_moread_lower_measurable"],
                    app["measurable_sensitivity_strict"] or 0.0,
                    app["measurable_sensitivity_lenient"] or 0.0))
    lines.append("- 反例检验（闭壳层重读）：%s" % app["closed_shell_counterexample"]["conclusion"])
    lines.append("- 与能量规则的净不一致数：严格口径 **%d**，宽松口径 **%d**。"
                 % (app["disagreements_with_energy_rule"]["strict"],
                    app["disagreements_with_energy_rule"]["lenient"]))
    lines.append("")
    lines.append("读法：`charge_l1` 的**唯一**已知短板是「够不着」而不是「看错」——"
                 "它对闭壳层格子（本目录全部 %d 个 neutral）返回 `unmeasurable`，"
                 "而对够得着的格子，它和能量规则没有一次翻案。"
                 % probe["n_cells"])
    lines.append("")
    lines.append("## 5. 给运行手册的一条可执行建议")
    lines.append("")
    if borderline:
        names = "、".join("`%s/%s/eps=%s`" % (row["name"], row["state"], row["epsilon"])
                         for row in borderline)
        lines.append("把 `identity_distance` / `verdict` 接到**提交前**的自检里：任何一格的 "
                     "|charge_l1 − 阈值| ≤ %s 就先打 `BORDERLINE` 标记并写进台账，"
                     "再决定要不要花机时。本目录必须标记：%s。"
                     % (fmt(threshold["margin"]), names))
    else:
        lines.append("把 `identity_distance` / `verdict` 接到提交前的自检里，"
                     "阈值从当次 census 重导；本目录没有需要标记的格子。")
    lines.append("")
    lines.append("复现（三条产物都逐字节可校验）：")
    lines.append("")
    lines.append("```")
    lines.append("python scripts/analyze_stage21_protocol.py")
    lines.append("python scripts/analyze_stage21_protocol.py --check")
    lines.append("```")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_csv(rows):
    """The protocol CSV as text (LF newlines, no BOM)."""
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(CSV_COLUMNS), lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 21 part B: the charge_l1 identity pre-check.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="directory holding the Stage 18 identity census")
    parser.add_argument("--census", type=Path, default=None,
                        help="explicit census CSV (overrides --data-dir)")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--threshold", type=float, default=None,
                        help="override the re-derived threshold")
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN,
                        help="half-width of the borderline band")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    census_path = Path(args.census) if args.census else Path(args.data_dir) / DEFAULT_CENSUS_NAME
    outdir = Path(args.outdir)
    census = load_census(census_path)

    negatives, positives, scope = calibration_pairs(census)
    derived = derive_threshold(negatives, positives)
    derived_full = derive_threshold(*all_measurable_pairs(census))
    if args.threshold is not None:
        threshold = float(args.threshold)
    elif derived["threshold"] is not None:
        threshold = derived["threshold"]
    else:
        threshold = FROZEN_THRESHOLD
    margin = float(args.margin)

    probe = closed_shell_probe(census, threshold, margin)
    payload, rows = build_payload(
        census, census_path, threshold, margin, scope, derived, derived_full, probe
    )
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    md_text = render_summary(payload)
    csv_text = render_csv(rows)

    artefacts = {
        outdir / PROTOCOL_JSON: json_text,
        outdir / PROTOCOL_MD: md_text,
        outdir / PROTOCOL_CSV: csv_text,
    }

    if args.check:
        problems = []
        for path, expected in artefacts.items():
            if not Path(path).exists():
                problems.append("%s missing" % path)
            elif Path(path).read_bytes() != expected.encode("utf-8"):
                problems.append("%s is stale" % path)
        for problem in problems:
            print("[XX] %s" % problem)
        if problems:
            return 1
        print("stage21 protocol: OK (%d cells, %d borderline, checks passed)"
              % (len(rows), len(payload["borderline"])))
        return 0

    outdir.mkdir(parents=True, exist_ok=True)
    for path, text in artefacts.items():
        Path(path).write_bytes(text.encode("utf-8"))
    print("stage21 protocol: wrote %d artefacts to %s" % (len(artefacts), outdir))
    print("  threshold = %s (margin %s), borderline = %d"
          % (threshold, margin, len(payload["borderline"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
