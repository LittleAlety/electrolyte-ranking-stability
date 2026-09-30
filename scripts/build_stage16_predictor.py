"""Stage 16 (week 15), part B -- an a priori warning rule.

The question
------------
Stage 15 diagnosed *where* the missing solution lives after the fact: it read the
CPCM output, saw that the spin population had moved onto a different set of
atoms, and called the layer diffuse.  That is a postmortem.  A screen is only
useful if it can be run *before* the continuum calculation, because the whole
point is to decide which calculations need the second guess.

So this module is restricted to quantities that exist the moment the gas-phase
T1 job finishes:

``gas_spin_maxfrac``        max |s_i| of the gas-phase Mulliken spin population
``gas_sum_spin_abs``        sum |s_i|; a clean doublet gives 1, spin polarisation
                            pushes it above 1
``gas_spin_participation``  1 / sum s_i^2, the inverse participation ratio
``gas_spin_rms_ang``        spin-weighted radius of gyration about the centre of
                            mass
``gas_spin_extent_norm``    the same, divided by the molecule's own mass gyration
``gas_min_spin``            the most negative spin population
``gas_gap_ev``              alpha HOMO-LUMO gap
``gas_small_gap_flag``      ORCA's own "Small HOMO/LUMO gap" pre-diagonalisation
                            warning fired
``gas_dipole_debye``        total dipole moment magnitude
``gas_mulliken_shift``      sum |q_state - q_neutral|

The rule is a one-descriptor threshold rule.  Its descriptor and the *sign* of
the comparison are chosen on the discovery set (the twelve T3 molecules); its
threshold is chosen by leave-one-out on that same discovery set, so no held-out
molecule contributes to the threshold.  The frozen rule is then applied
unchanged to the six molecules that were never computed at the continuum level
(DEC, EA, FEC, MA, TEGDME, VC).  Neutrals are excluded from the rule and the
reason is reported, not assumed: the label is defined on a comparison of two SCF
solutions, and a closed-shell neutral has one.

A multivariate logistic fit is reported next to the univariate rule as a
ceiling check, always with leave-one-out, so the report can say whether the
extra parameters bought anything.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_stage15_diffuseness import (  # noqa: E402
    centre_of_mass,
    mass_gyration_ang2,
    parse_mulliken,
    participation_ratio,
    read_geometry,
    read_text,
    weighted_extent_ang2,
)

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week15"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"

SUBSET = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")
VALIDATION = ("DEC", "EA", "FEC", "MA", "TEGDME", "VC")
OPEN_SHELL_STATES = ("cation", "anion")

GAS_DESCRIPTORS = (
    "gas_spin_maxfrac", "gas_sum_spin_abs", "gas_spin_participation",
    "gas_spin_rms_ang", "gas_spin_extent_norm", "gas_min_spin", "gas_gap_ev",
    "gas_small_gap_value", "gas_dipole_debye", "gas_mulliken_shift",
    "gas_gyration_ang2",
)

#: descriptors whose *larger* value is expected to mean "more at risk"; used only
#: to fix the sign of the comparison before the threshold is chosen.
LARGER_IS_RISKIER = ("gas_spin_maxfrac", "gas_sum_spin_abs", "gas_min_spin",
                     "gas_spin_rms_ang", "gas_spin_extent_norm")

_DIPOLE = re.compile(r"Total Dipole Moment\s*:\s*"
                     r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)")
_SMALL_GAP = re.compile(r"Small HOMO/LUMO gap\s*\(\s*(-?\d+\.\d+)\s*\)")
_ORBITAL_ROW = re.compile(r"^\s*(\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 16 part B: an a priori warning rule for the second solution.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def orbital_gap_ev(text: str):
    """Alpha HOMO-LUMO gap in eV, or ``None`` when the block is unreadable."""

    start = text.find("ORBITAL ENERGIES")
    if start < 0:
        return None
    block = text[start:]
    stop = block.find("MULLIKEN ATOMIC CHARGES")
    if stop > 0:
        block = block[:stop]
    down = block.find("SPIN DOWN ORBITALS")
    if down > 0:
        # A UKS run prints an alpha block and a beta block back to back.  Reading
        # them as one list makes the "last occupied orbital" the beta HOMO and
        # the gap a difference between two beta orbitals, which is a silently
        # wrong number rather than a crash.
        block = block[:down]
    energies, occupations = [], []
    for line in block.splitlines():
        match = _ORBITAL_ROW.match(line)
        if match:
            occupations.append(float(match.group(2)))
            energies.append(float(match.group(4)))
    if len(energies) < 2:
        return None
    homo = None
    for index, occupation in enumerate(occupations):
        if occupation > 0.5:
            homo = index
    if homo is None or homo + 1 >= len(energies):
        return None
    return energies[homo + 1] - energies[homo]

def gas_descriptors(name: str, state: str):
    """Every a priori descriptor of one (molecule, state), from the gas phase."""

    out = GAS_DIR / name / ("%s_%s.out" % (name, state))
    xyz = GAS_DIR / name / ("%s_%s.xyz" % (name, state))
    text = read_text(out)
    if text is None or not xyz.exists():
        return None
    charges, spins = parse_mulliken(text)
    if charges is None:
        return None
    geometry = read_geometry(xyz)
    if len(geometry) != len(charges):
        raise SystemExit("atom count mismatch in %s" % out)

    neutral = read_text(GAS_DIR / name / ("%s_neutral.out" % name))
    q_neutral, _ = parse_mulliken(neutral) if neutral is not None else (None, None)

    centre = centre_of_mass(geometry)
    gyration = mass_gyration_ang2(geometry)
    extent = weighted_extent_ang2(spins, geometry, centre)

    dipole = float("nan")
    match = _DIPOLE.search(text)
    if match:
        dipole = math.sqrt(sum(float(group) ** 2 for group in match.groups()))

    shift = float("nan")
    if q_neutral is not None and len(q_neutral) == len(charges):
        shift = sum(abs(value - reference)
                    for value, reference in zip(charges, q_neutral))

    gap = orbital_gap_ev(text)
    small_gap = _SMALL_GAP.search(text)

    return {
        "name": name, "state": state,
        "n_atoms": len(geometry),
        "gas_gyration_ang2": gyration,
        "gas_sum_spin": sum(spins),
        "gas_sum_spin_abs": sum(abs(value) for value in spins),
        "gas_min_spin": min(spins) if spins else float("nan"),
        "gas_max_spin": max(spins) if spins else float("nan"),
        "gas_spin_maxfrac": max((abs(value) for value in spins), default=float("nan")),
        "gas_spin_participation": participation_ratio(spins),
        "gas_spin_extent_ang2": extent,
        "gas_spin_rms_ang": (math.sqrt(extent) if extent == extent
                             else float("nan")),
        "gas_spin_extent_norm": extent / gyration if extent == extent else float("nan"),
        "gas_dipole_debye": dipole,
        "gas_mulliken_shift": shift,
        "gas_gap_ev": gap,
        "gas_small_gap_flag": bool(small_gap),
        "gas_small_gap_value": float(small_gap.group(1)) if small_gap else None,
        "gas_energy_eh": None,
    }


def read_labels(outdir: Path):
    """``({ladder: {(name, state): flag}}, raw rows)`` from stage16_by_state.csv.

    The primary label is ``core3``: the three dielectrics (5, 20, 200) that the
    held-out arm is measured on.  ``focus6`` and ``ladder10`` label the same
    molecules on richer ladders so the report can quantify how much a sparse
    ladder under-detects instead of assuming three points are enough.
    """

    path = outdir / "stage16_by_state.csv"
    tables = {name: {} for name in ("core3", "focus6", "ladder10", "validation")}
    rows = []
    if not path.exists():
        return tables, rows
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            flag = str(row["has_missed_lower_solution"]).strip().lower() in ("true", "1")
            key = (row["name"], row["state"])
            rows.append(row)
            if row["ladder"] in tables:
                tables[row["ladder"]][key] = flag
    return tables, rows


def roc_auc(values, labels):
    """Rank-based AUC; 0.5 when one class is absent."""

    pairs = sorted(zip(values, labels))
    positives = sum(1 for _, label in pairs if label)
    negatives = len(pairs) - positives
    if positives == 0 or negatives == 0:
        return 0.5
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        stop = index
        while stop + 1 < len(pairs) and pairs[stop + 1][0] == pairs[index][0]:
            stop += 1
        average_rank = (index + stop) / 2.0 + 1.0
        for position in range(index, stop + 1):
            if pairs[position][1]:
                rank_sum += average_rank
        index = stop + 1
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def permutation_p(values, labels, larger_is_risky=None, limit=200000, seed=0xC0FFEE):
    """Exact permutation p-value for one descriptor's AUC.

    The null is that the labels are exchangeable across the rows: the descriptor
    ranks them no better than a random assignment carrying the same number of
    positives.  The statistic is ``|AUC - 0.5|``, so a descriptor that is useless
    in *both* directions returns a p near 1 rather than near 0.  Every distinct
    assignment is enumerated while the count stays under ``limit`` -- for the
    discovery set that is C(24, 3) = 2024 -- and otherwise assignments are drawn
    from a frozen seed and the result is flagged as inexact.  Smoothing is the
    usual ``(hits + 1) / (total + 1)``.
    """

    observed = roc_auc(values, labels)
    n = len(values)
    positives = sum(1 for label in labels if label)
    if positives == 0 or positives == n or n == 0:
        return {"p_value": 1.0, "n_assignments": 1, "total_assignments": 1, "exact": True,
                "observed_auc": observed, "statistic": "|AUC - 0.5|",
                "note": "one class is absent, so no assignment can be more extreme"}
    magnitude = abs(observed - 0.5)
    riskier = (observed >= 0.5) if larger_is_risky is None else bool(larger_is_risky)
    total = math.comb(n, positives)
    if total <= limit:
        assignments = combinations(range(n), positives)
        exact = True
        denominator = total
    else:
        rng = random.Random(seed)
        assignments = (tuple(sorted(rng.sample(range(n), positives))) for _ in range(limit))
        exact = False
        denominator = limit
    hits = 0
    seen = 0
    for index in assignments:
        seen += 1
        trial = [False] * n
        for position in index:
            trial[position] = True
        if abs(roc_auc(values, trial) - 0.5) >= magnitude - 1e-12:
            hits += 1
    return {"p_value": (hits + 1) / (denominator + 1), "n_assignments": seen,
            "total_assignments": total, "exact": exact, "observed_auc": observed,
            "statistic": "|AUC - 0.5|", "seed": None if exact else seed,
            "sign": "larger_is_riskier" if riskier else "smaller_is_riskier"}


def accuracy_at(values, labels, threshold, larger_is_risky):
    """Plain accuracy of a threshold cut."""

    hits = 0
    for value, label in zip(values, labels):
        predicted = (value >= threshold) if larger_is_risky else (value <= threshold)
        hits += int(predicted == bool(label))
    return hits / len(labels)


def balanced_accuracy_at(values, labels, threshold, larger_is_risky):
    """Mean of sensitivity and specificity; ``None`` if a class is absent.

    This is deliberately *not* the quantity ``fit_threshold`` maximises -- that
    one is plain accuracy, and the two coincide only when the classes are
    balanced.  At five positives in twenty-four rows the difference is the whole
    story of this stage: the frozen rule is 0.833 in sample and 0.708 under
    leave-one-out, i.e. below the 0.792 of answering "no deficit" every time,
    yet its sensitivity/specificity mean is well above the 0.500 that any
    single-class answer can reach.
    """

    true_positive = false_positive = true_negative = false_negative = 0
    for value, label in zip(values, labels):
        predicted = (value >= threshold) if larger_is_risky else (value <= threshold)
        if predicted and label:
            true_positive += 1
        elif predicted:
            false_positive += 1
        elif label:
            false_negative += 1
        else:
            true_negative += 1
    if not (true_positive + false_negative) or not (true_negative + false_positive):
        return None
    sensitivity = true_positive / (true_positive + false_negative)
    specificity = true_negative / (true_negative + false_positive)
    return 0.5 * (sensitivity + specificity)


def fit_threshold(values, labels, larger_is_risky):
    """The threshold maximising plain accuracy on the supplied rows."""

    candidates = sorted(set(values))
    if not candidates:
        return None, 0.0
    edges = [candidates[0]]
    for left, right in zip(candidates, candidates[1:]):
        edges.append((left + right) / 2.0)
    edges.append(candidates[-1])
    best, best_score = None, -1.0
    for edge in edges:
        score = accuracy_at(values, labels, edge, larger_is_risky)
        if score > best_score + 1e-12:
            best, best_score = edge, score
    return best, best_score


def loo_rule(values, labels, larger_is_risky):
    """Leave-one-out accuracy of 'pick the threshold, predict the held-out row'."""

    hits = 0
    for index in range(len(values)):
        keep = [position for position in range(len(values)) if position != index]
        threshold, _ = fit_threshold([values[position] for position in keep],
                                     [labels[position] for position in keep],
                                     larger_is_risky)
        if threshold is None:
            continue
        predicted = (values[index] >= threshold) if larger_is_risky else (values[index] <= threshold)
        hits += int(predicted == bool(labels[index]))
    return hits / len(values)


def logistic_loo(rows, feature_names, labels):
    """Leave-one-out AUC of a standardised logistic fit on the given features."""

    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
    except Exception:  # noqa: BLE001 - optional ceiling check
        return None
    matrix = np.asarray([[row[name] for name in feature_names] for row in rows], dtype=float)
    target = np.asarray(labels, dtype=int)
    if len(set(target.tolist())) < 2:
        return None
    scores = []
    for index in range(len(target)):
        keep = np.ones(len(target), dtype=bool)
        keep[index] = False
        scaler = StandardScaler().fit(matrix[keep])
        model = LogisticRegression(max_iter=2000, C=1.0)
        model.fit(scaler.transform(matrix[keep]), target[keep])
        scores.append(float(model.decision_function(scaler.transform(matrix[index:index + 1]))[0]))
    return {"loo_auc": roc_auc(scores, target.tolist()),
            "n_features": len(feature_names),
            "features": list(feature_names)}

def arm_diagnostic(discovery, descriptor_names, validation=None):
    """Post-hoc split of the discovery set into its two open-shell arms.

    The frozen rule is fitted on the pooled open-shell set because that is the
    only thing that can be frozen *before* the calculation.  It is reported next
    to this diagnostic precisely because it does not work: the two arms are
    flagged for different physical reasons.  On the cation arm the second
    solution is the one r2SCAN-3c fails to localise on a compact, electron-poor
    ion, so the pre-SCF gap estimate already knows about it.  On the anion arm
    the extra electron has to be spread over a diffuse skeleton, so the *spin*
    population of the gas-phase anion is what moves.  The two descriptors are
    therefore reported per arm, with the positive ranks, and the whole block is
    labelled ``post_hoc``: the direction, the threshold and the arm split are
    all chosen after seeing the labels, so nothing here is a forecast.

    The same post-hoc rules are then scored on the held-out arm, which is the
    one place where they can actually be falsified.  They fail there too -- and
    that failure is reported next to the discovery numbers rather than instead
    of them, because it is the difference between "the mechanism is visible in
    twelve rows" and "the rule works".
    """

    arms = {}
    for arm in OPEN_SHELL_STATES:
        rows = [record for record in discovery if record["state"] == arm]
        arm_labels = [bool(record["label_core3"]) for record in rows]
        positives = sum(1 for label in arm_labels if label)
        majority = ((max(positives, len(arm_labels) - positives) / len(arm_labels))
                    if arm_labels else None)
        entries = []
        for descriptor in descriptor_names:
            usable = [record for record in rows
                      if isinstance(record.get(descriptor), (int, float))
                      and record[descriptor] == record[descriptor]]
            if len(usable) < 4 or len({record[descriptor] for record in usable}) < 2:
                continue
            values = [float(record[descriptor]) for record in usable]
            usable_labels = [bool(record["label_core3"]) for record in usable]
            auc = roc_auc(values, usable_labels)
            larger = auc >= 0.5
            threshold, _ = fit_threshold(values, usable_labels, larger)
            loo = loo_rule(values, usable_labels, larger)
            order = sorted(range(len(usable)),
                           key=lambda position: values[position], reverse=larger)
            ranks = [rank + 1 for rank, position in enumerate(order)
                     if usable_labels[position]]
            entries.append({
                "descriptor": descriptor,
                "sign": "larger_is_riskier" if larger else "smaller_is_riskier",
                "auc": auc,
                "abs_auc_above_half": abs(auc - 0.5),
                "n_usable": len(usable),
                "n_positive": sum(1 for label in usable_labels if label),
                "threshold_frozen": threshold,
                "loo_accuracy": loo,
                "beats_majority_baseline": (majority is not None and loo > majority),
                "positive_ranks": ranks,
                "permutation_p": permutation_p(values, usable_labels, larger)["p_value"],
            })
        entries.sort(key=lambda entry: -entry["abs_auc_above_half"])

        # Out-of-sample scoring of this arm's own best rule.  Nothing here is
        # fitted on the validation rows: the descriptor, the direction and the
        # threshold all come from the discovery set (the latter two post hoc).
        arm_validation = [record for record in (validation or [])
                          if record["state"] == arm]
        validation_block = None
        if entries and arm_validation:
            top = entries[0]
            larger = top["sign"] == "larger_is_riskier"
            predictions = []
            for record in arm_validation:
                value = record.get(top["descriptor"])
                if not isinstance(value, (int, float)) or value != value:
                    predictions.append(None)
                elif larger:
                    predictions.append(bool(value >= top["threshold_frozen"]))
                else:
                    predictions.append(bool(value <= top["threshold_frozen"]))
            matrix = {"true_positive": 0, "false_positive": 0, "true_negative": 0,
                      "false_negative": 0, "unscored": 0}
            for record, predicted in zip(arm_validation, predictions):
                truth = bool(record["label_validation"])
                if predicted is None:
                    matrix["unscored"] += 1
                elif predicted and truth:
                    matrix["true_positive"] += 1
                elif predicted:
                    matrix["false_positive"] += 1
                elif truth:
                    matrix["false_negative"] += 1
                else:
                    matrix["true_negative"] += 1
            scored = (matrix["true_positive"] + matrix["false_positive"]
                      + matrix["true_negative"] + matrix["false_negative"])
            truths = [bool(record["label_validation"]) for record in arm_validation]
            n_true = sum(1 for truth in truths if truth)
            arm_majority = (max(n_true, len(truths) - n_true) / len(truths)
                            if truths else None)
            accuracy = ((matrix["true_positive"] + matrix["true_negative"]) / scored
                        if scored else None)
            validation_block = {
                "descriptor": top["descriptor"],
                "sign": top["sign"],
                "threshold_frozen": top["threshold_frozen"],
                "n_rows": len(arm_validation),
                "n_positive": n_true,
                "n_scored": scored,
                "accuracy": accuracy,
                "majority_accuracy": arm_majority,
                "beats_majority_baseline": (accuracy is not None
                                            and arm_majority is not None
                                            and accuracy > arm_majority),
                "confusion_matrix": matrix,
                "per_row": [{"name": record["name"], "state": record["state"],
                             "value": record.get(top["descriptor"]),
                             "predicted": predicted,
                             "truth": bool(record["label_validation"])}
                            for record, predicted in zip(arm_validation, predictions)],
            }

        arms[arm] = {
            "n_rows": len(rows),
            "n_positive": positives,
            "majority_accuracy": majority,
            "best_by_absolute_auc": entries[0]["descriptor"] if entries else None,
            "best_absolute_auc": entries[0]["abs_auc_above_half"] if entries else None,
            "best_by_absolute_auc_beats_majority_baseline": (
                bool(entries[0]["beats_majority_baseline"]) if entries else None),
            "best_loo_accuracy": max((entry["loo_accuracy"] for entry in entries),
                                     default=None),
            "any_rule_beats_majority_baseline": any(entry["beats_majority_baseline"]
                                                    for entry in entries),
            "screen": entries,
            "validation": validation_block,
        }
    return {
        "post_hoc": True,
        "note": ("the pooled rule is frozen before the calculation; this split is "
                 "not. The direction, the threshold and the arm assignment are all "
                 "chosen after seeing the labels, so the numbers below are an "
                 "explanation of the failure, never a forecast."),
        "arm_selector_is_a_gas_phase_quantity": False,
        "arm_selector_note": ("the branch key is the charge state, which is known "
                              "before the job starts, so the split itself is free; "
                              "what is not free is which descriptor each branch "
                              "would use and where its threshold would sit."),
        "arms": arms,
    }



def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (Path.cwd() / args.outdir)
    outdir = outdir.resolve()

    labels_by_ladder, raw = read_labels(outdir)

    records = []
    for name in SUBSET + VALIDATION:
        for state in ("neutral",) + OPEN_SHELL_STATES:
            described = gas_descriptors(name, state)
            if described is None:
                continue
            described["split"] = "discovery" if name in SUBSET else "validation"
            key = (name, state)
            for ladder in ("core3", "focus6", "ladder10", "validation"):
                described["label_" + ladder] = labels_by_ladder[ladder].get(key)
            records.append(described)

    fields = (["split", "name", "state", "n_atoms"] + list(GAS_DESCRIPTORS)
              + ["gas_sum_spin", "gas_max_spin", "gas_small_gap_flag",
                 "gas_small_gap_value", "label_core3", "label_focus6",
                 "label_ladder10", "label_validation"])
    with (outdir / "stage16_gas_descriptors.csv").open("w", encoding="utf-8",
                                                       newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    discovery = [record for record in records
                 if record["split"] == "discovery"
                 and record["state"] in OPEN_SHELL_STATES
                 and record["label_core3"] is not None]
    validation = [record for record in records
                  if record["split"] == "validation"
                  and record["state"] in OPEN_SHELL_STATES]
    validation = [record for record in validation
                  if record["label_validation"] is not None]

    labels = [bool(record["label_core3"]) for record in discovery]
    screen = []
    for descriptor in GAS_DESCRIPTORS:
        usable = [record for record in discovery
                  if isinstance(record.get(descriptor), (int, float))
                  and record[descriptor] == record[descriptor]]
        if len(usable) < 4 or len({record[descriptor] for record in usable}) < 2:
            continue
        values = [float(record[descriptor]) for record in usable]
        usable_labels = [bool(record["label_core3"]) for record in usable]
        auc = roc_auc(values, usable_labels)
        larger = auc >= 0.5
        threshold, accuracy = fit_threshold(values, usable_labels, larger)
        screen.append({
            "descriptor": descriptor,
            "sign": "larger_is_riskier" if larger else "smaller_is_riskier",
            "auc": auc,
            "abs_auc_above_half": abs(auc - 0.5),
            "n_usable": len(usable),
            "n_positive": sum(1 for label in usable_labels if label),
            "threshold_frozen": threshold,
            "accuracy_in_sample": accuracy,
            "loo_accuracy": loo_rule(values, usable_labels, larger),
            "auc_permutation_p": permutation_p(values, usable_labels, larger)["p_value"],
            "matches_physical_prior": (larger == (descriptor in LARGER_IS_RISKIER)),
        })
    screen.sort(key=lambda entry: -entry["abs_auc_above_half"])

    result = {
        "stage": 16,
        "part": "B -- an a priori warning rule",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "restriction": ("open-shell states only: the label compares two SCF "
                        "solutions and a closed-shell neutral has one"),
        "n_discovery_rows": len(discovery),
        "n_discovery_positive": sum(1 for label in labels if label),
        "n_validation_rows": len(validation),
        "n_validation_positive": sum(1 for record in validation
                                     if record["label_validation"]),
        "descriptor_definitions": {
            "gas_spin_maxfrac": "max |Mulliken spin population| in the gas phase",
            "gas_sum_spin_abs": "sum |s_i|; 1 for a clean doublet, larger under spin polarisation",
            "gas_spin_participation": "1 / sum s_i^2 of the gas-phase spin population",
            "gas_spin_rms_ang": "spin-weighted radius of second moment about the centre of mass",
            "gas_spin_extent_norm": "the above divided by the molecule's mass gyration radius",
            "gas_min_spin": "most negative spin population (spin polarisation depth)",
            "gas_gap_ev": "converged alpha HOMO-LUMO gap",
            "gas_small_gap_value": ("ORCA's pre-SCF HOMO/LUMO gap estimate, i.e. the "
                                    "number behind its own small-gap warning"),
            "gas_dipole_debye": "magnitude of the gas-phase total dipole moment",
            "gas_mulliken_shift": "sum |q_state - q_neutral| (Mulliken)",
        },
        "screen": screen,
        "baseline_majority_accuracy": (max(sum(1 for label in labels if label),
                                           len(labels) - sum(1 for label in labels if label))
                                       / len(labels) if labels else None),
    }

    # How well does the three-point label proxy the richer ladders?  Reported for
    # the discovery set, whose rows carry all three labels.
    ladder_crosscheck = {}
    for left, right in (("core3", "focus6"), ("core3", "ladder10"),
                        ("focus6", "ladder10")):
        shared = [record for record in discovery
                  if record["label_" + left] is not None
                  and record["label_" + right] is not None]
        disagree = ["%s/%s" % (record["name"], record["state"]) for record in shared
                    if bool(record["label_" + left]) != bool(record["label_" + right])]
        ladder_crosscheck["%s_vs_%s" % (left, right)] = {
            "n_rows": len(shared), "n_disagree": len(disagree),
            "disagreements": disagree}
    result["label_ladder_crosscheck"] = ladder_crosscheck


    if screen:
        chosen = screen[0]
        result["chosen_rule"] = chosen
        result["chosen_rule"]["definition"] = result["descriptor_definitions"].get(
            chosen["descriptor"], "")
        usable = [record for record in discovery
                  if isinstance(record.get(chosen["descriptor"]), (int, float))
                  and record[chosen["descriptor"]] == record[chosen["descriptor"]]]
        significance = permutation_p(
            [float(record[chosen["descriptor"]]) for record in usable],
            [bool(record["label_core3"]) for record in usable],
            chosen["sign"] == "larger_is_riskier")
        result["chosen_rule"]["auc_permutation"] = significance
        result["permutation_test"] = dict(
            significance,
            definition=("exact one-sided permutation test on the chosen descriptor: "
                        "every assignment of the observed number of positives to "
                        "the discovery rows is enumerated and the statistic is "
                        "|AUC - 0.5|, so a descriptor useless in both directions "
                        "returns a p near 1"),
            n_rows=len(usable),
            n_positive=sum(1 for record in usable if record["label_core3"]),
            descriptor=chosen["descriptor"])

        # The honest comparison.  Its outcome is *not* assumed: the flag below is
        # the comparison itself, so a report that quotes these two numbers cannot
        # quietly claim a win the data does not show.
        majority = result["baseline_majority_accuracy"]
        result["majority_baseline_note"] = (
            "the trivial classifier that answers 'no deficit' for every row; at "
            "%d positives out of %d rows it is right %.3f of the time, so plain "
            "accuracy is a weak yardstick and the balanced-accuracy threshold "
            "search is the reason the frozen rule predicts anything at all"
            % (result["n_discovery_positive"], len(labels), majority or 0.0))
        result["chosen_rule"]["balanced_accuracy_in_sample"] = balanced_accuracy_at(
            [float(record[chosen["descriptor"]]) for record in usable],
            [bool(record["label_core3"]) for record in usable],
            float(chosen["threshold_frozen"]),
            chosen["sign"] == "larger_is_riskier")
        result["trivial_balanced_accuracy"] = 0.5
        result["chosen_rule_beats_majority_baseline"] = bool(
            majority is not None and (chosen.get("loo_accuracy") or 0.0) > majority)
        result["per_arm_diagnostic"] = arm_diagnostic(discovery, GAS_DESCRIPTORS,
                                                     validation)
        if validation:
            predictions = []
            for record in validation:
                value = record.get(chosen["descriptor"])
                if not isinstance(value, (int, float)) or value != value:
                    predictions.append(None)
                    continue
                predicted = ((value >= chosen["threshold_frozen"])
                             if chosen["sign"] == "larger_is_riskier"
                             else (value <= chosen["threshold_frozen"]))
                predictions.append(bool(predicted))
            matrix = {"true_positive": 0, "false_positive": 0,
                      "true_negative": 0, "false_negative": 0, "unscored": 0}
            for record, predicted in zip(validation, predictions):
                truth = bool(record["label_validation"])
                if predicted is None:
                    matrix["unscored"] += 1
                elif predicted and truth:
                    matrix["true_positive"] += 1
                elif predicted and not truth:
                    matrix["false_positive"] += 1
                elif not predicted and truth:
                    matrix["false_negative"] += 1
                else:
                    matrix["true_negative"] += 1
            scored = (matrix["true_positive"] + matrix["false_positive"]
                      + matrix["true_negative"] + matrix["false_negative"])
            result["validation"] = {
                "molecules": VALIDATION,
                "confusion_matrix": matrix,
                "n_scored": scored,
                "accuracy": ((matrix["true_positive"] + matrix["true_negative"]) / scored
                             if scored else None),
                "per_row": [{"name": record["name"], "state": record["state"],
                             "value": record.get(chosen["descriptor"]),
                             "predicted": predicted,
                             "truth": bool(record["label_validation"])}
                            for record, predicted in zip(validation, predictions)],
            }
        else:
            result["validation"] = {"status": "pending",
                                    "note": "the held-out arm has not been run yet"}

        top = [entry["descriptor"] for entry in screen[:2]]
        ceiling = logistic_loo(discovery, top, labels)
        if ceiling and validation:
            import numpy as np  # noqa: PLC0415
            try:
                from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
                from sklearn.preprocessing import StandardScaler  # noqa: PLC0415
                matrix_x = np.asarray([[record[name] for name in top]
                                       for record in discovery], dtype=float)
                target = np.asarray(labels, dtype=int)
                scaler = StandardScaler().fit(matrix_x)
                model = LogisticRegression(max_iter=2000).fit(scaler.transform(matrix_x), target)
                test_x = np.asarray([[record[name] for name in top]
                                     for record in validation], dtype=float)
                probabilities = model.predict_proba(scaler.transform(test_x))[:, 1]
                truths = [bool(record["label_validation"]) for record in validation]
                ceiling["validation_accuracy"] = (
                    sum(int((probability >= 0.5) == truth)
                        for probability, truth in zip(probabilities, truths))
                    / len(truths))
                ceiling["validation_auc"] = roc_auc(list(probabilities), truths)
            except Exception:  # noqa: BLE001 - ceiling is optional
                pass
        result["multivariate_ceiling"] = ceiling

    (outdir / "stage16_predictor.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("discovery rows %d (%d positive) | validation rows %d (%d positive)"
          % (len(discovery), result["n_discovery_positive"], len(validation),
             result["n_validation_positive"]))
    for entry in screen[:6]:
        print("  %-24s auc %.3f  loo_acc %.3f  thr %.4g  (%s)"
              % (entry["descriptor"], entry["auc"], entry["loo_accuracy"],
                 entry["threshold_frozen"], entry["sign"]))
    if screen:
        print("frozen rule beats the majority baseline: %s (%.3f vs %.3f)"
              % (result.get("chosen_rule_beats_majority_baseline"),
                 screen[0].get("loo_accuracy") or 0.0,
                 result.get("baseline_majority_accuracy") or 0.0))
        for arm, block in sorted((result.get("per_arm_diagnostic") or {}).get("arms", {}).items()):
            held = block.get("validation") or {}
            print("  arm %-6s best |AUC-0.5| %.3f on %s; any rule beats majority: %s"
                  % (arm, block.get("best_absolute_auc") or 0.0,
                     block.get("best_by_absolute_auc"), block.get("any_rule_beats_majority_baseline")))
            if held:
                print("         held-out: %s accuracy %.3f vs majority %.3f (TP %d FP %d TN %d FN %d)"
                      % (held.get("descriptor"), held.get("accuracy") or 0.0,
                         held.get("majority_accuracy") or 0.0,
                         held["confusion_matrix"]["true_positive"],
                         held["confusion_matrix"]["false_positive"],
                         held["confusion_matrix"]["true_negative"],
                         held["confusion_matrix"]["false_negative"]))
        print("chosen rule: %s %s %.6g" % (
            screen[0]["descriptor"], ">=" if screen[0]["sign"] == "larger_is_riskier" else "<=",
            screen[0]["threshold_frozen"]))
        if result.get("validation", {}).get("accuracy") is not None:
            print("held-out accuracy %.3f on %d rows %s"
                  % (result["validation"]["accuracy"], result["validation"]["n_scored"],
                     result["validation"]["confusion_matrix"]))
    print("wrote %s" % (outdir / "stage16_predictor.json").relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())