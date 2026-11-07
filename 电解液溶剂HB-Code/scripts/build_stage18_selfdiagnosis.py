"""Stage 18 (week 17), part B -- zero-extra-cost self-diagnosis of the default SCF solution.

Week 15 (Stage 16) tried to *forecast*, before the continuum job existed, whether
the default ORCA SCF guess would land on the higher of the two solutions Stage 15
had catalogued.  That forecast needed an extra gas-phase calculation as its input
and it lost to the trivial "always answer coincident" baseline; it was written up
as a negative result and not used.

This stage asks the cheaper question, which is also the one that can actually be
acted on.  The default continuum calculation has to be run anyway -- it *is* the
target quantity.  So nothing extra has to be paid to ask:

    reading only the fields the default run already printed, can we tell that it
    stopped on the higher solution?

Every feature below is read out of the *default arm's own* ``.out`` file:

  * the SCF iteration table (energies, Delta-E per cycle, final DIISErr / MaxDP /
    RMSDP, cycle count, whether the energy ever went up),
  * ORCA's own "Small HOMO/LUMO gap" pre-diagonalisation warning, with its signed
    number and its multiplicity,
  * the identity of the solution itself, via the Stage 17 parser: <S**2>, the
    largest |Mulliken spin|, the spin participation ratio, the number of atoms
    needed for 90% of the spin, the reduced-orbital channel carrying the spin,
    and the Loewdin counterparts,
  * the ORBITAL ENERGIES block (HOMO, LUMO, LUMO-HOMO), when it is present.

Protocol (mirrors ``scripts/build_stage16_predictor.py`` exactly so the two
stages are comparable):

  1. single-variable screen by AUC on the discovery set only, ranked by
     ``|AUC - 0.5|``;
  2. freeze one feature and one threshold, recording why;
  3. in-sample plain accuracy, balanced accuracy, and the majority baseline;
  4. leave-one-out accuracy and balanced accuracy, and the boolean that says
     whether the frozen rule actually beats the majority baseline;
  5. the *exact* null distribution of the AUC, computed by dynamic programming
     over the tie-aware Mann-Whitney U statistic (n = 360, k = 32 is far too
     large to enumerate, but the U distribution is a single DP away);
  6. the frozen rule scored, untouched, on the 54 held-out cells;
  7. a post-hoc, per charge-state split, because Week 15 learned the hard way
     that pooling can hide the answer;
  8. a multivariate logistic ceiling, so the report can say whether extra
     parameters bought anything.

The verdict is not assumed here.  It is computed, printed, and written to disk
whatever it turns out to be.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from math import comb
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage17_solution_identity as s17  # noqa: E402
from build_stage16_predictor import (  # noqa: E402
    accuracy_at,
    balanced_accuracy_at,
    fit_threshold,
    logistic_loo,
    permutation_p,
    roc_auc,
)

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week17"
DEFAULT_OUTPUTS_ROOT = REPO_ROOT / "outputs"

DISCOVERY_CSV = REPO_ROOT / "outputs" / "week15" / "stage16_cells.csv"
HOLDOUT_CSV = REPO_ROOT / "outputs" / "week15" / "stage16_validation_cells.csv"

#: Inherited unchanged from Stage 15/16: a cell is "moread_lower" when the second
#: guess found a lower energy by more than this.
MATERIAL_THRESHOLD_EV = 1e-3
HARTREE_TO_EV = 27.211386245988

EXPECTED_DISCOVERY_ROWS = 360
EXPECTED_DISCOVERY_POSITIVE = 32
EXPECTED_HOLDOUT_ROWS = 54
EXPECTED_HOLDOUT_POSITIVE = 5

STATES = ("neutral", "cation", "anion")
OPEN_SHELL_STATES = ("cation", "anion")

#: Value substituted for ``gap_warn_value`` when ORCA did *not* print its small-gap
#: warning.  ORCA only warns when the pre-SCF HOMO/LUMO gap is small (or already
#: inverted), so the absence of the warning means a large, healthy gap.  A large
#: positive fill keeps the ordering "smaller value = riskier" monotone and keeps
#: the feature defined for every row instead of silently dropping 120 neutrals.
NO_WARNING_GAP_EH = 1.0

#: Default fill for a missing numeric feature.  Only ``gap_warn_value`` overrides
#: it, for the reason above.
DEFAULT_FILL = 0.0
FEATURE_FILL = {"gap_warn_value": NO_WARNING_GAP_EH}

# ---------------------------------------------------------------------------
# parsing: the SCF iteration table
# ---------------------------------------------------------------------------

SCF_HEADER_RE = re.compile(r"Iteration\s+Energy \(Eh\)")

#: ``    2    -381.5000033974503708    -1.34e-01  4.96e-03 ...``.  The third
#: field is Delta-E and is always printed in scientific notation, which is what
#: separates a real SCF row from the many other integer-led tables ORCA prints.
SCF_ROW_RE = re.compile(
    r"^\s*(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+[eE][+-]\d+)\s+(.*)$"
)


def _all_floats(tokens):
    """``"... 4.96e-03 5.96e-02 ..."`` -> list of floats, or ``None``."""
    out = []
    for token in tokens.split():
        try:
            out.append(float(token))
        except ValueError:
            return None
    return out


def parse_scf_table(text):
    """The SCF iteration trajectory of one ``.out`` file, in order.

    ORCA prints the incremental-Fock/DIIS block and then, after it switches
    solver, a SOSCF block whose last column is ``MaxGrad`` instead of
    ``DIISErr/Damp``.  Both share the header shape, so both are read into one
    trajectory; ``block`` records which column meaning a row carries.  A
    spurious integer-led row is rejected by requiring every trailing token to be
    a float, and the trajectory is then trimmed to the longest run of strictly
    consecutive iteration numbers starting at 1.
    """
    candidates = []
    block = None
    for line in text.splitlines():
        if SCF_HEADER_RE.search(line):
            block = ("diis" if "DIISErr" in line
                     else "soscf" if "MaxGrad" in line else "other")
            continue
        match = SCF_ROW_RE.match(line)
        if match is None:
            continue
        rest = _all_floats(match.group(4))
        if rest is None:
            continue
        candidates.append({
            "iteration": int(match.group(1)),
            "energy_eh": float(match.group(2)),
            "delta_e": float(match.group(3)),
            "columns": rest,
            "block": block,
        })
    best = []
    for position, row in enumerate(candidates):
        if row["iteration"] != 1:
            continue
        run = [row]
        for following in candidates[position + 1:]:
            if following["iteration"] == run[-1]["iteration"] + 1:
                run.append(following)
            else:
                break
        if len(run) > len(best):
            best = run
    return best


def scf_features(text):
    """Zero-extra-cost SCF-trajectory descriptors of one default-arm ``.out``."""
    rows = parse_scf_table(text)
    deltas = [row["delta_e"] for row in rows]
    diis_rows = [row for row in rows if row["block"] == "diis" and len(row["columns"]) >= 3]
    last = rows[-1] if rows else None
    return {
        "scf_n_cycles": len(rows),
        "scf_de2": deltas[1] if len(deltas) > 1 else None,
        "scf_max_abs_de": max((abs(value) for value in deltas), default=None),
        "scf_last3_abs_de_sum": (sum(abs(value) for value in deltas[-3:])
                                 if deltas else None),
        "scf_last_abs_de": abs(deltas[-1]) if deltas else None,
        "scf_has_energy_increase": int(any(value > 0.0 for value in deltas)),
        "scf_final_rmsdp": last["columns"][0] if last and last["columns"] else None,
        "scf_final_maxdp": (last["columns"][1]
                            if last and len(last["columns"]) > 1 else None),
        "scf_final_diiserr": (diis_rows[-1]["columns"][2] if diis_rows else None),
    }


# ---------------------------------------------------------------------------
# parsing: ORCA's own small-gap warning and the orbital-energy block
# ---------------------------------------------------------------------------

SMALL_GAP_RE = re.compile(r"Small HOMO/LUMO gap\s*\(\s*(-?\d+\.\d+)\s*\)")
FULL_DIAGONALIZATION_RE = re.compile(r"Will do a full diagonalization")
ORBITAL_ROW_RE = re.compile(
    r"^\s*(\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)


def parse_small_gap(text):
    """ORCA's pre-SCF gap warning: presence, signed value, and multiplicity."""
    values = SMALL_GAP_RE.findall(text)
    return {
        "gap_warn_present": int(bool(values)),
        "gap_warn_count": len(values),
        "gap_warn_value": float(values[-1]) if values else None,
        "gap_warn_full_diagonalization": int(bool(FULL_DIAGONALIZATION_RE.search(text))),
    }


def parse_orbitals(text):
    """HOMO / LUMO eigenvalues of the alpha block, or ``None`` when unreadable.

    The beta (``SPIN DOWN``) block is cut off before the scan for the same
    reason Stage 16 cuts it: reading both as one list makes "HOMO" the beta HOMO
    and the gap a difference of two beta orbitals, which is a silently wrong
    number rather than a crash.
    """
    start = text.find("ORBITAL ENERGIES")
    if start < 0:
        return None
    block = text[start:]
    stop = block.find("MULLIKEN ATOMIC CHARGES")
    if stop > 0:
        block = block[:stop]
    down = block.find("SPIN DOWN ORBITALS")
    if down > 0:
        block = block[:down]
    occupations, energies_eh, energies_ev = [], [], []
    for line in block.splitlines():
        match = ORBITAL_ROW_RE.match(line)
        if match is not None:
            occupations.append(float(match.group(2)))
            energies_eh.append(float(match.group(3)))
            energies_ev.append(float(match.group(4)))
    if len(energies_eh) < 2:
        return None
    homo = None
    for index, occupation in enumerate(occupations):
        if occupation > 0.5:
            homo = index
    if homo is None or homo + 1 >= len(energies_eh):
        return None
    return {
        "homo_eh": energies_eh[homo],
        "lumo_eh": energies_eh[homo + 1],
        "homo_ev": energies_ev[homo],
        "lumo_ev": energies_ev[homo + 1],
        "homo_lumo_gap_ev": energies_ev[homo + 1] - energies_ev[homo],
    }

# ---------------------------------------------------------------------------
# the feature set
# ---------------------------------------------------------------------------

#: Numeric descriptors, in report order.  Everything here is read from the
#: default arm's own ``.out`` file, so all of it is free once that job exists.
NUMERIC_FEATURES = (
    "scf_n_cycles",
    "scf_de2",
    "scf_max_abs_de",
    "scf_last3_abs_de_sum",
    "scf_last_abs_de",
    "scf_has_energy_increase",
    "scf_final_rmsdp",
    "scf_final_maxdp",
    "scf_final_diiserr",
    "gap_warn_present",
    "gap_warn_count",
    "gap_warn_value",
    "s2",
    "spin_max",
    "spin_pr",
    "spin_n90",
    "loewdin_spin_max",
    "loewdin_spin_pr",
    "loewdin_spin_n90",
    "orbital_abs",
    "homo_eh",
    "lumo_eh",
    "homo_ev",
    "lumo_ev",
    "homo_lumo_gap_ev",
)

#: String-valued descriptors.  Reported in the CSV, never screened: an AUC needs
#: an ordering, and "which atom carries the spin" has none.
LABEL_FEATURES = ("spin_center_label", "orbital_label")

FEATURE_NOTES = {
    "scf_n_cycles": "number of SCF cycles in the (contiguous) default trajectory",
    "scf_de2": "Delta-E of cycle 2, the first real energy drop; 0 for cycle 1",
    "scf_max_abs_de": "largest |Delta-E| over the whole trajectory",
    "scf_last3_abs_de_sum": "sum of |Delta-E| over the last three cycles",
    "scf_last_abs_de": "|Delta-E| of the final cycle before convergence",
    "scf_has_energy_increase": "1 if any cycle raised the energy",
    "scf_final_rmsdp": "final RMSDP of the default SCF",
    "scf_final_maxdp": "final MaxDP of the default SCF",
    "scf_final_diiserr": "DIISErr of the last DIIS-block cycle (None if it never used DIIS)",
    "gap_warn_present": "ORCA printed its small-HOMO/LUMO-gap pre-diagonalisation warning",
    "gap_warn_count": "how many times that warning was printed",
    "gap_warn_value": ("signed gap in Eh quoted by the warning; +1.0 when the warning "
                       "did not fire (a large gap is the healthy case)"),
    "s2": "<S**2> of the default solution; 0.75 is a clean doublet",
    "spin_max": "largest |Mulliken atomic spin| of the default solution",
    "spin_pr": "participation ratio 1/sum s_i^2 of the Mulliken atomic spin",
    "spin_n90": "atoms needed to carry 90% of the Mulliken spin",
    "loewdin_spin_max": "largest |Loewdin atomic spin| of the default solution",
    "loewdin_spin_pr": "participation ratio of the Loewdin atomic spin",
    "loewdin_spin_n90": "atoms needed to carry 90% of the Loewdin spin",
    "orbital_abs": "largest |reduced-orbital Mulliken spin| (the spin channel)",
    "homo_eh": "alpha HOMO eigenvalue of the default solution, Eh",
    "lumo_eh": "alpha LUMO eigenvalue of the default solution, Eh",
    "homo_ev": "alpha HOMO eigenvalue of the default solution, eV",
    "lumo_ev": "alpha LUMO eigenvalue of the default solution, eV",
    "homo_lumo_gap_ev": "converged alpha LUMO - HOMO gap, eV",
}


def extract_features(text):
    """Every zero-extra-cost descriptor of one default-arm ``.out`` file."""
    features = {}
    features.update(scf_features(text))
    features.update(parse_small_gap(text))
    orbitals = parse_orbitals(text)
    features["has_orbital_block"] = int(orbitals is not None)
    for name in ("homo_eh", "lumo_eh", "homo_ev", "lumo_ev", "homo_lumo_gap_ev"):
        features[name] = orbitals[name] if orbitals else None

    analyzed = s17.analyze_outfile(text)
    mulliken_spins = [row[3] for row in analyzed["mulliken"]]
    loewdin_spins = [row[3] for row in analyzed["loewdin"]]
    features["s2"] = analyzed["s2"]
    features["spin_max"] = max((abs(value) for value in mulliken_spins), default=None)
    features["spin_pr"] = (s17.participation_ratio(mulliken_spins)
                           if mulliken_spins else None)
    features["spin_n90"] = (s17.atoms_to_fraction(mulliken_spins)
                            if mulliken_spins else None)
    features["loewdin_spin_max"] = max((abs(value) for value in loewdin_spins),
                                       default=None)
    features["loewdin_spin_pr"] = (s17.participation_ratio(loewdin_spins)
                                   if loewdin_spins else None)
    features["loewdin_spin_n90"] = (s17.atoms_to_fraction(loewdin_spins)
                                    if loewdin_spins else None)
    spin_label, spin_value = s17.spin_center(analyzed["mulliken"])
    orbital_label, orbital_value = s17.top_atom_orbital(analyzed["reduced_spin"])
    features["spin_center_label"] = spin_label or ""
    features["orbital_label"] = orbital_label or ""
    features["orbital_abs"] = orbital_value
    return features


# ---------------------------------------------------------------------------
# resolving .out files
# ---------------------------------------------------------------------------


def _strip_holdout(path):
    """The holdout arm writes ``XX_state_holdout[_moread]_cpcm_e.out``.

    The held-out files carry an extra ``holdout`` infix that Stage 17 never had
    to parse.  Removing it is the only local adaptation: the name is then handed
    to Stage 17's own ``parse_outfile_name``, so there is still exactly one
    filename grammar in the project.  The holdout molecules (DEC, EA, FEC, MA,
    TEGDME, VC) do not overlap the discovery molecules, so the stripped names
    cannot collide.
    """
    return Path(str(path).replace("_holdout", ""))


def build_index(outputs_root):
    """``(arm, molecule, state, epsilon) -> [paths]`` over every parseable ``.out``."""
    index = defaultdict(list)
    for path in s17.collect_outfiles(outputs_root):
        key = s17.parse_outfile_name(_strip_holdout(path))
        if key is not None:
            index[key].append(path)
    return index


def load_arm(rows, arm_set, index):
    """Attach the default-arm features to every cell of one arm of the design."""
    records = []
    for row in rows:
        key = ("default", row["name"], row["state"], float(row["epsilon"]))
        candidates = index.get(key, [])
        if not candidates:
            raise SystemExit("no default-arm .out resolves for %s" % (key,))
        features = extract_features(s17.read_text(s17.choose_path(candidates)))
        features["arm_set"] = arm_set
        features["name"] = row["name"]
        features["state"] = row["state"]
        features["epsilon"] = float(row["epsilon"])
        features["delta_ev"] = float(row["delta_ev"])
        features["classification"] = row["classification"]
        features["label"] = int(row["classification"] == "moread_lower")
        records.append(features)
    return records


def read_cells(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# statistics helpers
# ---------------------------------------------------------------------------


def fill_value(name, value):
    """Missing numeric -> the feature's documented fill constant."""
    return FEATURE_FILL.get(name, DEFAULT_FILL) if value is None else value


def column(records, name):
    return [fill_value(name, record.get(name)) for record in records]


def labels_of(records):
    return [bool(record["label"]) for record in records]


def majority_accuracy(labels):
    if not labels:
        return None
    positives = sum(1 for label in labels if label)
    return max(positives, len(labels) - positives) / len(labels)


def confusion_at(records, name, threshold, larger_is_risky):
    """TP/FP/TN/FN of a frozen threshold cut."""
    matrix = {"true_positive": 0, "false_positive": 0,
              "true_negative": 0, "false_negative": 0}
    for record in records:
        value = fill_value(name, record.get(name))
        predicted = (value >= threshold) if larger_is_risky else (value <= threshold)
        truth = bool(record["label"])
        if predicted and truth:
            matrix["true_positive"] += 1
        elif predicted:
            matrix["false_positive"] += 1
        elif truth:
            matrix["false_negative"] += 1
        else:
            matrix["true_negative"] += 1
    return matrix


def balanced_from_matrix(matrix):
    positives = matrix["true_positive"] + matrix["false_negative"]
    negatives = matrix["true_negative"] + matrix["false_positive"]
    if not positives or not negatives:
        return None
    return 0.5 * (matrix["true_positive"] / positives
                  + matrix["true_negative"] / negatives)


# ---------------------------------------------------------------------------
# the one-sided reading of ORCA's own small-gap warning
# ---------------------------------------------------------------------------


def _is_positive(record):
    return record.get("classification") == "moread_lower"


def _is_warned(record):
    return int(record.get("gap_warn_present") or 0) == 1


def necessity_table(records):
    """How often a real miss carries ORCA's small-gap warning.

    ``P(no warning | positive) == 0`` is the whole one-sided claim: the warning
    is a *necessary* marker of a missed solution.  That is usable as a gate --
    anything the SCF did not warn about can be let through -- even though it
    says nothing about which warned cells are the misses.
    """
    positives = [record for record in records if _is_positive(record)]
    warned = [record for record in positives if _is_warned(record)]
    hit_rate = (len(warned) / len(positives)) if positives else None
    return {
        "n_positive": len(positives),
        "n_positive_with_warning": len(warned),
        "n_positive_without_warning": len(positives) - len(warned),
        "p_positive_has_warning": hit_rate,
        "p_no_warning_given_positive": (None if hit_rate is None else 1.0 - hit_rate),
    }


def specificity_table(records):
    """The false-alarm side: how often a non-miss still carries the warning."""
    negatives = [record for record in records if not _is_positive(record)]
    warned = [record for record in negatives if _is_warned(record)]
    false_alarm_rate = (len(warned) / len(negatives)) if negatives else None
    return {
        "n_negative": len(negatives),
        "n_negative_with_warning": len(warned),
        "false_alarm_rate": false_alarm_rate,
        "specificity": (None if false_alarm_rate is None else 1.0 - false_alarm_rate),
    }


def alert_stats(records, rule):
    """Sensitivity / specificity / balanced accuracy of ``alert => miss``."""
    matrix = {"true_positive": 0, "false_positive": 0,
              "true_negative": 0, "false_negative": 0}
    for record in records:
        predicted = bool(rule(record))
        truth = _is_positive(record)
        if predicted and truth:
            matrix["true_positive"] += 1
        elif predicted:
            matrix["false_positive"] += 1
        elif truth:
            matrix["false_negative"] += 1
        else:
            matrix["true_negative"] += 1
    scored = sum(matrix.values())
    positives = matrix["true_positive"] + matrix["false_negative"]
    negatives = matrix["true_negative"] + matrix["false_positive"]
    return {
        "n_rows": scored,
        "n_positive": positives,
        "confusion_matrix": matrix,
        "sensitivity": (matrix["true_positive"] / positives) if positives else None,
        "specificity": (matrix["true_negative"] / negatives) if negatives else None,
        "precision": (matrix["true_positive"]
                      / (matrix["true_positive"] + matrix["false_positive"])
                      if (matrix["true_positive"] + matrix["false_positive"]) else None),
        "accuracy": ((matrix["true_positive"] + matrix["true_negative"]) / scored
                     if scored else None),
        "balanced_accuracy": balanced_from_matrix(matrix),
        "majority_accuracy": majority_accuracy([_is_positive(r) for r in records]),
    }


def stratum_table(records):
    """``P(positive | warning)`` and ``P(positive | no warning)`` in one stratum."""
    warned = [record for record in records if _is_warned(record)]
    unwarned = [record for record in records if not _is_warned(record)]
    positives_warned = [record for record in warned if _is_positive(record)]
    positives_unwarned = [record for record in unwarned if _is_positive(record)]
    return {
        "n_rows": len(records),
        "n_positive": sum(1 for record in records if _is_positive(record)),
        "n_warning": len(warned),
        "n_positive_with_warning": len(positives_warned),
        "n_no_warning": len(unwarned),
        "n_positive_without_warning": len(positives_unwarned),
        "p_positive_given_warning": (len(positives_warned) / len(warned)) if warned else None,
        "p_positive_given_no_warning": ((len(positives_unwarned) / len(unwarned))
                                        if unwarned else None),
    }


def stratify(records, key):
    groups = defaultdict(list)
    for record in records:
        groups[key(record)].append(record)
    return {str(name): stratum_table(members)
            for name, members in sorted(groups.items(), key=lambda item: item[0])}


def positive_value_range(records):
    """Range of the signed warning value over the positives (all should be < 0)."""
    values = [float(record["gap_warn_value"]) for record in records
              if _is_positive(record) and record.get("gap_warn_value") is not None]
    return {
        "n_positive_with_value": len(values),
        "min_eh": min(values) if values else None,
        "max_eh": max(values) if values else None,
        "all_negative": (all(value < 0.0 for value in values) if values else None),
    }


def one_sided_screening(discovery, holdout, frozen_threshold):
    """The one-sided complement to the frozen rule, on the same 414 pairs.

    The two-sided question ("does the descriptor separate misses from
    non-misses?") already failed out of sample.  This block asks the one-sided
    question that survives it: is the warning *necessary* for a miss?  It is
    computed from the very records that fill the feature CSV, so no new data is
    read and no existing number moves -- the frozen rule is reported here as one
    row of a trade-off table, never re-derived.
    """
    pooled = list(discovery) + list(holdout)
    arms = {"discovery": list(discovery), "holdout": list(holdout), "pooled": pooled}

    def any_warning(record):
        return _is_warned(record)

    def frozen_rule(record):
        return fill_value("gap_warn_value", record.get("gap_warn_value")) <= frozen_threshold

    counts = {}
    for label, selector in (("pooled", lambda r: True),
                            ("positive", _is_positive),
                            ("negative", lambda r: not _is_positive(r))):
        bucket = defaultdict(int)
        for record in pooled:
            if selector(record):
                bucket[str(int(record.get("gap_warn_count") or 0))] += 1
        counts[label] = dict(sorted(bucket.items()))

    return {
        "question": ("can a cell the default SCF did *not* warn about still be a "
                     "missed solution?  (necessity, not separation)"),
        "alert_definition": "gap_warn_present == 1 (ORCA's pre-SCF small-gap warning)",
        "coverage": {
            "n_pairs": len(pooled),
            "n_pairs_with_gap_warning_field": sum(
                1 for record in pooled if record.get("gap_warn_present") is not None),
            "n_neutral_pairs": sum(1 for record in pooled
                                   if record.get("state") == "neutral"),
            "note": ("the warning is printed by the SCF itself, so unlike the "
                     "spin-based identity features it is defined for every one of "
                     "the 414 pairs -- including the closed-shell neutrals that "
                     "print no spin block at all"),
        },
        "necessity": {
            "statement": ("no warning => no missed solution, i.e. "
                          "P(no warning | positive) = 0"),
            "overall": necessity_table(pooled),
            "by_arm": {name: necessity_table(rows) for name, rows in arms.items()},
        },
        "specificity": {
            "statement": ("the converse fails: 'warning => missed solution' is "
                          "false, so the warning is necessary but not sufficient"),
            "overall": specificity_table(pooled),
            "by_arm": {name: specificity_table(rows) for name, rows in arms.items()},
        },
        "positive_gap_warn_value_range": {
            name: positive_value_range(rows) for name, rows in arms.items()},
        "by_state": {name: stratify(rows, lambda r: r.get("state"))
                     for name, rows in arms.items()},
        "by_epsilon": {name: stratify(rows, lambda r: float(r.get("epsilon", 0.0)))
                       for name, rows in arms.items()},
        "tradeoff": [
            {"id": "any_warning",
             "rule": "predict moread_lower iff gap_warn_present == 1",
             "by_arm": {name: alert_stats(rows, any_warning)
                        for name, rows in arms.items()}},
            {"id": "frozen_value_threshold",
             "rule": ("predict moread_lower iff gap_warn_value <= %g "
                      "(the frozen rule, unchanged)" % frozen_threshold),
             "by_arm": {name: alert_stats(rows, frozen_rule)
                        for name, rows in arms.items()}},
        ],
        "gap_warn_count_observation": {
            "distribution": counts,
            "note": ("gap_warn_count > 0 is identical to gap_warn_present == 1 for "
                     "all 414 pairs, and every positive has count 1, so the count "
                     "adds no separation; it is reported, not used"),
        },
        "limitations": [
            ("the necessity claim rests on 37 positives (32 discovery + 5 holdout); "
             "a different functional, basis set or solvent model must re-check it"),
            ("'no warning => coincident' is an empirical statement about these 18 "
             "molecules under r2SCAN-3c/C-PCM, not a theorem"),
            ("necessary is not sufficient: 237/377 negatives also carry the warning, "
             "so this gates the safe set rather than picking the misses"),
            ("the held-out positives are all anions; a cation miss that produced no "
             "warning would not be caught by this corpus"),
            ("the 3-10 epsilons of one (molecule, state) are not independent rows, "
             "so the counts overstate the effective sample size"),
        ],
    }

def loo_rule_fast(values, labels, larger_is_risky):
    """Leave-one-out rule evaluation, plus the confusion matrix of its calls.

    Structurally identical to Stage 16's ``loo_rule`` -- the threshold is re-fit
    on the n-1 remaining rows by maximising *plain* accuracy, and the direction
    is held at the one fixed from the full discovery set -- but the threshold
    search is O(n) instead of O(n^2), which is what makes an n = 360 leave-one-out
    affordable.  Returns ``(accuracy, balanced_accuracy, matrix)``.
    """
    predictions = []
    for held in range(len(values)):
        kept_values = [values[i] for i in range(len(values)) if i != held]
        kept_labels = [labels[i] for i in range(len(values)) if i != held]
        threshold, _ = fit_threshold(kept_values, kept_labels, larger_is_risky)
        if threshold is None:
            predictions.append(None)
            continue
        value = values[held]
        predictions.append(bool(value >= threshold) if larger_is_risky
                           else bool(value <= threshold))
    matrix = {"true_positive": 0, "false_positive": 0,
              "true_negative": 0, "false_negative": 0}
    scored = 0
    for predicted, truth in zip(predictions, labels):
        if predicted is None:
            continue
        scored += 1
        if predicted and truth:
            matrix["true_positive"] += 1
        elif predicted:
            matrix["false_positive"] += 1
        elif truth:
            matrix["false_negative"] += 1
        else:
            matrix["true_negative"] += 1
    accuracy = ((matrix["true_positive"] + matrix["true_negative"]) / scored
                if scored else None)
    return accuracy, balanced_from_matrix(matrix), matrix

# ---------------------------------------------------------------------------
# significance: the exact, tie-aware null distribution of the AUC
# ---------------------------------------------------------------------------


class _DPTooLarge(Exception):
    """Raised when the exact DP would exceed its operation budget."""


def exact_auc_null_p(values, labels, max_ops=200_000_000):
    """Exact two-sided p for ``|AUC - 0.5|`` under exchangeable labels.

    ``AUC`` is a strictly monotone function of the Mann-Whitney U statistic, so
    the null distribution of the test statistic is the null distribution of U
    over the ``C(n, k)`` label assignments that keep ``k`` positives.  For
    n = 360, k = 32 that is ~1e35 assignments -- far too many to enumerate -- but
    the *distribution* of U is one dynamic program away, so the p-value here is
    exact rather than sampled.

    Ties are handled properly, which matters: several of the screened features
    are coarse (a binary warning flag, an integer atom count), and a
    no-ties Mann-Whitney null would be the wrong yardstick for them.  Ranks are
    replaced by mid-ranks; working in doubled units keeps them integers.  The U
    distribution is symmetric about ``k*(n+1)/2``, so the two tails are equal and

        p = P(|U - centre| >= |U_obs - centre|) = 2 * P(U <= centre - d) / C(n,k)

    is computed by counting k-subsets of the doubled mid-ranks whose sum does not
    exceed the lower tail boundary.
    """
    n = len(values)
    k = sum(1 for label in labels if label)
    m = n - k
    if n == 0 or k == 0 or m == 0:
        return {"method": "degenerate", "p_value": 1.0, "n_rows": n,
                "n_positive": k, "note": "one class is absent; no assignment can be extreme"}
    order = sorted(range(n), key=lambda i: values[i])
    doubled = [0] * n
    start = 0
    while start < n:
        stop = start
        while stop + 1 < n and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        mid2 = (start + stop) + 2
        for position in range(start, stop + 1):
            doubled[order[position]] = mid2
        start = stop + 1

    observed2 = sum(doubled[i] for i, label in enumerate(labels) if label)
    centre2 = k * (n + 1)
    distance2 = abs(observed2 - centre2)
    boundary2 = centre2 - distance2
    auc_observed = (observed2 - k * (k + 1)) / (2.0 * k * m)

    dp = [dict() for _ in range(k + 1)]
    dp[0][0] = 1
    operations = 0
    for value in sorted(doubled):
        for chosen in range(k - 1, -1, -1):
            source = dp[chosen]
            if not source:
                continue
            target = dp[chosen + 1]
            for partial, ways in source.items():
                updated = partial + value
                if updated <= boundary2:
                    target[updated] = target.get(updated, 0) + ways
            operations += len(source)
        if operations > max_ops:
            raise _DPTooLarge("exact DP exceeded %d operations" % max_ops)

    lower_tail = sum(dp[k].values())
    total = comb(n, k)
    p_value = min(1.0, 2.0 * lower_tail / total)
    return {
        "method": "exact_mann_whitney_dp",
        "tie_aware": True,
        "statistic": "|AUC - 0.5|",
        "auc_observed": auc_observed,
        "p_value": p_value,
        "p_value_smoothed_upper": min(1.0, 2.0 * (lower_tail + 1) / total),
        "lower_tail_count": lower_tail,
        "total_assignments": total,
        "n_rows": n,
        "n_positive": k,
        "dp_states": sum(len(layer) for layer in dp),
        "dp_operations": operations,
        "note": ("exact null of the tie-aware Mann-Whitney statistic; U is a "
                 "monotone function of the AUC, and the two tails of its null "
                 "distribution are equal by symmetry"),
    }


def significance_for(values, labels, seed, mc_samples):
    """Exact p where affordable, with a documented Monte-Carlo cross-check."""
    block = None
    try:
        block = exact_auc_null_p(values, labels)
    except _DPTooLarge:
        block = None
    cross_check = permutation_p(values, labels, larger_is_risky=None,
                                limit=mc_samples, seed=seed)
    if block is None:
        return {
            "method": "monte_carlo",
            "tie_aware": True,
            "statistic": "|AUC - 0.5|",
            "p_value": cross_check["p_value"],
            "samples": cross_check["n_assignments"],
            "seed": seed,
            "total_assignments": cross_check["total_assignments"],
            "note": ("the exact DP exceeded its operation budget here, so the "
                     "reported p is a Monte-Carlo permutation estimate, not exact"),
        }
    block["monte_carlo_cross_check"] = {
        "method": "monte_carlo",
        "p_value": cross_check["p_value"],
        "samples": cross_check["n_assignments"],
        "seed": seed,
    }
    return block


# ---------------------------------------------------------------------------
# screening / freezing
# ---------------------------------------------------------------------------


def screen_entries(records, holdout_records, names=NUMERIC_FEATURES):
    """Single-variable screen, ranked by ``|AUC - 0.5|`` (the Stage 16 order)."""
    truth = labels_of(records)
    entries = []
    for name in names:
        values = column(records, name)
        if len(set(values)) < 2:
            continue
        auc = roc_auc(values, truth)
        larger = auc >= 0.5
        threshold, accuracy = fit_threshold(values, truth, larger)
        loo_accuracy, loo_balanced, _ = loo_rule_fast(values, truth, larger)
        majority = majority_accuracy(truth)
        entry = {
            "descriptor": name,
            "definition": FEATURE_NOTES.get(name, ""),
            "sign": "larger_is_riskier" if larger else "smaller_is_riskier",
            "auc": auc,
            "abs_auc_above_half": abs(auc - 0.5),
            "n_rows": len(records),
            "n_positive": sum(truth),
            "n_missing": sum(1 for record in records if record.get(name) is None),
            "missing_fill": FEATURE_FILL.get(name, DEFAULT_FILL),
            "threshold_frozen": threshold,
            "accuracy_in_sample": accuracy,
            "balanced_accuracy_in_sample": balanced_accuracy_at(
                values, truth, threshold, larger),
            "loo_accuracy": loo_accuracy,
            "loo_balanced_accuracy": loo_balanced,
            "majority_accuracy": majority,
            "beats_majority_in_sample": bool(accuracy > majority),
            "beats_majority_loo": bool(loo_accuracy is not None and loo_accuracy > majority),
        }
        if holdout_records:
            holdout_truth = labels_of(holdout_records)
            matrix = confusion_at(holdout_records, name, threshold, larger)
            scored = sum(matrix.values())
            entry["holdout_accuracy_post_hoc"] = (
                (matrix["true_positive"] + matrix["true_negative"]) / scored
                if scored else None)
            entry["holdout_majority_accuracy_post_hoc"] = majority_accuracy(holdout_truth)
            entry["holdout_confusion_post_hoc"] = matrix
        entries.append(entry)
    entries.sort(key=lambda entry: -entry["abs_auc_above_half"])
    return entries


def state_block(records, holdout_records, state, seed, mc_samples):
    """Post-hoc within-state view of the *frozen* feature.

    ``state`` is one charge state or a tuple of them; the tuple form gives the
    open-shell pool (the set Stage 16 actually used) the same treatment.
    """
    wanted = (state,) if isinstance(state, str) else tuple(state)
    subset = [record for record in records if record["state"] in wanted]
    state = wanted[0] if len(wanted) == 1 else "+".join(wanted)
    truth = labels_of(subset)
    positives = sum(truth)
    block = {
        "post_hoc": True,
        "n_rows": len(subset),
        "n_positive": positives,
        "majority_accuracy": majority_accuracy(truth),
        "poisoned_by_trivial_negatives": state == "neutral",
    }
    if not subset:
        return block
    entries = screen_entries(subset, None)
    frozen = dict(_FROZEN or {})
    name = frozen.get("descriptor")
    if name is None or name not in NUMERIC_FEATURES:
        block["note"] = "no frozen rule"
        block["best_feature_post_hoc"] = entries[0]["descriptor"] if entries else None
        return block
    values = column(subset, name)
    larger = frozen.get("sign") == "larger_is_riskier"
    auc = roc_auc(values, truth)
    order = sorted(range(len(subset)), key=lambda i: values[i], reverse=larger)
    ranks = [rank + 1 for rank, position in enumerate(order) if truth[position]]
    block.update({
        "frozen_feature": name,
        "auc": auc,
        "abs_auc_above_half": abs(auc - 0.5),
        "sign": frozen.get("sign"),
        "positive_ranks_of_frozen_feature": ranks,
        "significance": significance_for(values, truth, seed, mc_samples),
        "threshold_frozen_from_pooled": frozen.get("threshold_frozen"),
    })
    if positives and len(subset) - positives:
        loo_accuracy, loo_balanced, _ = loo_rule_fast(values, truth, larger)
        block["loo_accuracy"] = loo_accuracy
        block["loo_balanced_accuracy"] = loo_balanced
        block["beats_majority_loo"] = bool(
            loo_accuracy is not None and loo_accuracy > block["majority_accuracy"])
    if entries:
        block["best_feature_in_state_post_hoc"] = entries[0]["descriptor"]
        block["best_abs_auc_above_half_in_state_post_hoc"] = entries[0]["abs_auc_above_half"]
        block["state_screen_top5"] = [
            {key: entry[key] for key in
             ("descriptor", "auc", "abs_auc_above_half", "threshold_frozen",
              "loo_accuracy", "beats_majority_loo")}
            for entry in entries[:5]]
    return block


#: Filled in by ``main`` so the post-hoc split can reuse the frozen direction and
#: threshold without threading them through every helper.
_FROZEN = None


def multivariate_ceiling(records, holdout_records, feature_names):
    """Leave-one-out logistic fit on the top features: the price of extra knobs."""
    if not feature_names:
        return None
    filled = [{name: fill_value(name, record.get(name)) for name in feature_names}
              for record in records]
    ceiling = logistic_loo(filled, list(feature_names), labels_of(records))
    if ceiling is None:
        return {"status": "unavailable",
                "note": "numpy/sklearn missing, or one class absent"}
    ceiling["holdout_accuracy"] = None
    ceiling["holdout_auc"] = None
    if holdout_records:
        try:
            import numpy as np  # noqa: PLC0415
            from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
            from sklearn.preprocessing import StandardScaler  # noqa: PLC0415
            matrix = np.asarray([[fill_value(name, record.get(name))
                                  for name in feature_names] for record in records],
                                dtype=float)
            target = np.asarray(labels_of(records), dtype=int)
            scaler = StandardScaler().fit(matrix)
            model = LogisticRegression(max_iter=5000).fit(scaler.transform(matrix), target)
            test = np.asarray([[fill_value(name, record.get(name))
                                for name in feature_names] for record in holdout_records],
                              dtype=float)
            probabilities = model.predict_proba(scaler.transform(test))[:, 1]
            holdout_truth = labels_of(holdout_records)
            ceiling["holdout_accuracy"] = (
                sum(int((probability >= 0.5) == truth)
                    for probability, truth in zip(probabilities, holdout_truth))
                / len(holdout_truth))
            ceiling["holdout_auc"] = roc_auc(list(probabilities), holdout_truth)
        except Exception:  # noqa: BLE001 - the ceiling is an optional extra
            ceiling["holdout_note"] = "holdout fit failed"
    return ceiling


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------

CSV_COLUMNS = (["arm_set", "name", "state", "epsilon", "label", "classification", "delta_ev"]
               + list(NUMERIC_FEATURES) + list(LABEL_FEATURES))


def write_features_csv(path, records):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def write_by_state_csv(path, records):
    """Per (arm_set, state) means, so the tables can be read without a notebook."""
    groups = defaultdict(list)
    for record in records:
        groups[(record["arm_set"], record["state"])].append(record)
    fields = ["arm_set", "state", "n_rows", "n_positive", "delta_ev_mean"]
    for name in NUMERIC_FEATURES:
        fields += ["%s_mean" % name, "%s_n_missing" % name]
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for (arm_set, state), members in sorted(groups.items()):
            row = {"arm_set": arm_set, "state": state, "n_rows": len(members),
                   "n_positive": sum(record["label"] for record in members),
                   "delta_ev_mean": sum(record["delta_ev"] for record in members) / len(members)}
            for name in NUMERIC_FEATURES:
                present = [record[name] for record in members if record.get(name) is not None]
                row["%s_mean" % name] = (sum(present) / len(present)) if present else ""
                row["%s_n_missing" % name] = len(members) - len(present)
            writer.writerow(row)


def _fmt(value, digits=6):
    if value is None:
        return "n/a"
    if isinstance(value, float) and value != value:
        return "n/a"
    return ("%.*g" % (digits, value))


def write_summary_md(path, payload):
    lines = []
    add = lines.append
    chosen = payload["frozen_rule"]
    screen = payload["screen"]
    in_sample = payload["in_sample"]
    loo = payload["loo"]
    significance = payload["significance"]
    holdout = payload["holdout"]
    by_state = payload["by_state_post_hoc"]
    ceiling = payload["multivariate_ceiling"]

    add("# Stage 18 / Week 17 · Part B — 零额外成本的自诊断")
    add("**一句话结论**：" + payload["one_line_verdict"])
    add("## 命题与方法")
    add("- 命题：只读**默认臂那一个 `.out` 已经打印出来的字段**，能否看出它停在了高解（`moread_lower`）？不需要任何额外量子化学作业。")
    add("- 数据：发现集 `outputs/week15/stage16_cells.csv`（%d 行 / %d 正例）；留出臂 `outputs/week15/stage16_validation_cells.csv`（%d 行 / %d 正例：DEC/EA/FEC/MA/TEGDME/VC）。标签 `classification == \"moread_lower\"` ⇔ `delta_ev < -1e-3 eV`。"
        % (payload["discovery"]["n_rows"], payload["discovery"]["n_positive"],
           holdout["n_rows"], holdout["n_positive"]))
    add("- 特征（全部零额外成本）：SCF 迭代轨迹（圈数、ΔE 轨迹、最终 DIISErr/MaxDP/RMSDP）、ORCA 自己的 Small HOMO/LUMO gap 警告（含符号与次数）、Stage 17 的身份指标（<S**2>、spin_max、spin_pr、n90、自旋中心、约化轨道通道及其 Löwdin 版）、轨道能量块（HOMO/LUMO/gap）。")
    add("- 协议逐条镜像 `scripts/build_stage16_predictor.py`：只用发现集筛特征 → 冻结一条规则 → 样本内/LOO/多数类基线 → AUC 精确零分布 → 留出臂打分 → 事后按态分层 → 多变量上限。")
    add("## 单变量筛查（发现集，按 |AUC-0.5| 排序，前 8 名）")
    add("| # | 特征 | AUC | \\|AUC-0.5\\| | 方向 | 阈值 | 样本内 acc | LOO acc | 多数类 | LOO 胜基线 | 留出 acc(事后) |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for rank, entry in enumerate(screen[:8], 1):
        add("| %d | `%s` | %.3f | %.3f | %s | %s | %.3f | %.3f | %.3f | %s | %s |"
            % (rank, entry["descriptor"], entry["auc"], entry["abs_auc_above_half"],
               ">=" if entry["sign"] == "larger_is_riskier" else "<=",
               _fmt(entry["threshold_frozen"], 4),
               entry["accuracy_in_sample"], entry["loo_accuracy"] or float("nan"),
               entry["majority_accuracy"], "是" if entry["beats_majority_loo"] else "否",
               ("%.3f" % entry["holdout_accuracy_post_hoc"])
               if entry.get("holdout_accuracy_post_hoc") is not None else "n/a"))
    add("> 留出列是事后补上的，不参与任何选择。")
    add("## 冻结规则（方向与阈值已写进 JSON，可原样复现）")
    add("- 特征 `%s`：%s" % (chosen["descriptor"], chosen["definition"]))
    add("- 方向 %s，阈值 `%s`。选择依据＝发现集 `|AUC-0.5|` 第一名（Stage 16 同口径）；阈值取使全发现集普通准确率最大的切点。"
        % ("越大越危险（>= 阈值判正）" if chosen["sign"] == "larger_is_riskier"
           else "越小越危险（<= 阈值判正）", _fmt(chosen["threshold_frozen"], 6)))
    add("- 缺失口径：%s" % ("该特征无缺失。"
                          if chosen["n_missing"] == 0 else
                          "该特征在发现集缺 %d 行，按 %s 填充（ORCA 未报警＝gap 大＝安全）。"
                          % (chosen["n_missing"], _fmt(chosen["missing_fill"], 3))))
    add("## 样本内与留一验证（LOO＝每次留出一行、用其余行重新选阈值）")
    add("| 量 | 冻结规则 | 多数类基线 | 胜出 |")
    add("|---|---|---|---|")
    add("| 样本内 accuracy | %.4f | %.4f | %s |"
        % (in_sample["accuracy"], in_sample["majority_accuracy"],
           "是" if in_sample["beats_majority"] else "否"))
    add("| 样本内 balanced accuracy | %.4f | 0.5000 | 是 |" % in_sample["balanced_accuracy"])
    add("| LOO accuracy | %.4f | %.4f | %s |"
        % (loo["accuracy"], loo["majority_accuracy"],
           "是" if loo["beats_majority"] else "否"))
    add("| LOO balanced accuracy | %.4f | 0.5000 | %s |"
        % (loo["balanced_accuracy"], "是" if (loo["balanced_accuracy"] or 0.0) > 0.5 else "否"))
    add("- LOO 混淆矩阵：TP=%d FP=%d TN=%d FN=%d（%d 个正例里只认出 %d 个）。"
        % (loo["confusion_matrix"]["true_positive"], loo["confusion_matrix"]["false_positive"],
           loo["confusion_matrix"]["true_negative"], loo["confusion_matrix"]["false_negative"],
           payload["discovery"]["n_positive"], loo["confusion_matrix"]["true_positive"]))
    add("## 显著性（AUC 的精确零分布）")
    add("- 方法 `%s`：U 是 AUC 的单调函数，其零分布按 tie-aware 中位秩用动态规划精确算出（%s 个 DP 状态 / %s 次操作）；观测 AUC=%.4f，**精确 p = %.4g**（全部指派 C(%d,%d)=%.4g）。"
        % (significance["method"], significance.get("dp_states", "n/a"),
           significance.get("dp_operations", "n/a"), significance.get("auc_observed", float("nan")),
           significance["p_value"], significance["n_rows"], significance["n_positive"],
           significance.get("total_assignments", float("nan"))))
    if "monte_carlo_cross_check" in significance:
        add("- Monte-Carlo 交叉核对（`method=\"monte_carlo\"`，%d 次抽样，seed=%d）：p = %.4g；与精确值同量级，但它**不是**精确值。"
            % (significance["monte_carlo_cross_check"]["samples"], payload["seed"],
               significance["monte_carlo_cross_check"]["p_value"]))
    add("## 留出臂逐行（冻结规则原样打分，无任何再拟合）")
    add("- 留出 accuracy=%.4f vs 多数类 %.4f（%s）；TP=%d FP=%d TN=%d FN=%d。"
        % (holdout["accuracy"], holdout["majority_accuracy"],
           "**胜过**基线" if holdout["beats_majority"] else "**输给**基线",
           holdout["confusion_matrix"]["true_positive"], holdout["confusion_matrix"]["false_positive"],
           holdout["confusion_matrix"]["true_negative"], holdout["confusion_matrix"]["false_negative"]))
    add("| 分子 | 态 | eps | 特征值 | 预测 | 真值 | delta_ev (eV) |")
    add("|---|---|---|---|---|---|---|")
    for row in holdout["per_row"]:
        add("| %s | %s | %s | %s | %s | %s | %.4g |"
            % (row["name"], row["state"], _fmt(row["epsilon"], 4), _fmt(row["value"], 4),
               "正" if row["predicted"] else "负", "正" if row["truth"] else "负", row["delta_ev"]))
    # -- the one-sided reading of ORCA's own small-gap warning ----------------
    one_sided = payload["one_sided_screening"]
    nec_overall = one_sided["necessity"]["overall"]
    nec_arm = one_sided["necessity"]["by_arm"]
    spec_arm = one_sided["specificity"]["by_arm"]
    assert nec_overall["n_positive_with_warning"] == nec_overall["n_positive"]
    assert nec_overall["p_no_warning_given_positive"] == 0.0
    assert (nec_arm["discovery"]["n_positive"] + nec_arm["holdout"]["n_positive"]
            == nec_overall["n_positive"])
    assert (spec_arm["discovery"]["n_negative"] + spec_arm["holdout"]["n_negative"]
            == one_sided["specificity"]["overall"]["n_negative"])
    tradeoff = {entry["id"]: entry["by_arm"] for entry in one_sided["tradeoff"]}
    assert tradeoff["any_warning"]["discovery"]["sensitivity"] == 1.0
    assert tradeoff["any_warning"]["holdout"]["sensitivity"] == 1.0
    assert tradeoff["frozen_value_threshold"]["holdout"]["sensitivity"] == 0.0
    no_warning_rates = [entry["p_positive_given_no_warning"]
                        for arm in one_sided["by_state"].values()
                        for entry in arm.values()
                        if entry["p_positive_given_no_warning"] is not None]
    assert no_warning_rates and max(no_warning_rates) == 0.0
    state_cond = {arm: {state: one_sided["by_state"][arm].get(state, {}).get(
        "p_positive_given_warning") for state in ("cation", "anion")}
        for arm in ("discovery", "holdout")}
    gap_range = one_sided["positive_gap_warn_value_range"]
    add("## 单边筛查：负 gap 警告是漏解的必要条件（post_hoc）")
    add("- 必要条件成立且样本外可迁移：%d/%d 个漏解都带 ORCA 的 Small HOMO/LUMO gap 警告（发现集 %d/%d、留出臂 %d/%d），P(无警告 | 漏解) = %.3f；正例的带符号 gap 全为负（发现集 %s ~ %s、留出臂 %s ~ %s）。"
        % (nec_overall["n_positive_with_warning"], nec_overall["n_positive"],
           nec_arm["discovery"]["n_positive_with_warning"], nec_arm["discovery"]["n_positive"],
           nec_arm["holdout"]["n_positive_with_warning"], nec_arm["holdout"]["n_positive"],
           nec_overall["p_no_warning_given_positive"],
           _fmt(gap_range["discovery"]["min_eh"], 3), _fmt(gap_range["discovery"]["max_eh"], 3),
           _fmt(gap_range["holdout"]["min_eh"], 3), _fmt(gap_range["holdout"]["max_eh"], 3)))
    add("- 反向不成立：发现集 %d/%d、留出臂 %d/%d 个负例同样报警 ⇒ 有警告**不是**充分条件，这正是 value 阈值规则样本外失效的根因。"
        % (spec_arm["discovery"]["n_negative_with_warning"], spec_arm["discovery"]["n_negative"],
           spec_arm["holdout"]["n_negative_with_warning"], spec_arm["holdout"]["n_negative"]))
    add("- 分层条件概率 P(漏解|有警告)：发现集 cation %s / anion %s，留出臂 cation %s / anion %s；凡有样本的层里 P(漏解|无警告) 的最大值为 %.3f（%d 个中性分子全部无警告且全部 coincident）。"
        % (_fmt(state_cond["discovery"]["cation"], 3), _fmt(state_cond["discovery"]["anion"], 3),
           _fmt(state_cond["holdout"]["cation"], 3), _fmt(state_cond["holdout"]["anion"], 3),
           max(no_warning_rates), one_sided["by_state"]["pooled"]["neutral"]["n_rows"]))
    add("- 同一 414 对口径的权衡：`只要求有警告` 敏感度 %.3f/%.3f、特异度 %.3f/%.3f、准确率 %.3f/%.3f（涨不过基线）；冻结规则 `gap_warn_value <= %s` 发现集敏感度 %.3f、留出臂敏感度 %.3f ⇒ **必要条件可迁移、充分条件不可迁移**。覆盖与限制：警告对全部 %d 对可测（含 %d 个无自旋块的闭壳中性），不受身份指标缺失限制；但结论仅由 %d 个正例支持（留出臂 %d 个、全为 anion）。"
        % (tradeoff["any_warning"]["discovery"]["sensitivity"],
           tradeoff["any_warning"]["holdout"]["sensitivity"],
           tradeoff["any_warning"]["discovery"]["specificity"],
           tradeoff["any_warning"]["holdout"]["specificity"],
           tradeoff["any_warning"]["discovery"]["accuracy"],
           tradeoff["any_warning"]["holdout"]["accuracy"],
           _fmt(payload["frozen_rule"]["threshold_frozen"], 6),
           tradeoff["frozen_value_threshold"]["discovery"]["sensitivity"],
           tradeoff["frozen_value_threshold"]["holdout"]["sensitivity"],
           one_sided["coverage"]["n_pairs"], one_sided["coverage"]["n_neutral_pairs"],
           nec_overall["n_positive"], nec_arm["holdout"]["n_positive"]))
    add("## 事后按态分层（post_hoc：方向与阈值都取自池化，只换个切法看）")
    add("| 层 | n | 正例 | 冻结特征 AUC | 多数类 | LOO acc | 胜基线 | 精确 p |")
    add("|---|---|---|---|---|---|---|---|")
    for state, block in by_state.items():
        add("| %s | %d | %d | %s | %s | %s | %s | %s |"
            % (state, block["n_rows"], block["n_positive"], _fmt(block.get("auc"), 4),
               _fmt(block.get("majority_accuracy"), 4), _fmt(block.get("loo_accuracy"), 4),
               ("是" if block["beats_majority_loo"] else "否") if "beats_majority_loo" in block else "n/a",
               _fmt(block.get("significance", {}).get("p_value"), 3)))
    add("## 多变量上限（加参数的收益上界）")
    if ceiling and ceiling.get("loo_auc") is not None:
        add("- 前 3 特征（%s）的留一逻辑回归：LOO AUC=%.4f，留出臂 accuracy=%s，仍不及留出基线 %.4f —— 加参数没有换来可用规则。"
            % ("、".join("`%s`" % n for n in ceiling["features"]), ceiling["loo_auc"],
               _fmt(ceiling.get("holdout_accuracy"), 4), holdout["majority_accuracy"]))
    else:
        add("- 不可用：%s" % (ceiling or {}))
    add("## 没能提取到的特征")
    for item in payload["extraction_gaps_md"]:
        add("- %s" % item)
    add("## 局限")
    for item in payload["limits"]:
        add("- %s" % item)
    text = "\n".join(lines) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")
    return len(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def gap_reason(feature):
    """Why a feature is blank on some rows; reported verbatim in the JSON."""
    if feature in ("s2", "spin_max", "spin_pr", "spin_n90", "orbital_abs"):
        return "closed-shell neutral prints no Mulliken spin block"
    if feature.startswith("loewdin_spin"):
        return "closed-shell neutral prints no Loewdin spin block"
    if feature == "gap_warn_value":
        return ("ORCA only warns for a small gap; absence means a large, healthy "
                "gap. Filled with +%.1f Eh" % NO_WARNING_GAP_EH)
    if feature == "scf_final_diiserr":
        return "the run never used a DIIS block (straight to SOSCF)"
    return "block not printed"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=("Stage 18 part B: zero-extra-cost self-diagnosis of the "
                     "default SCF solution from its own .out file."))
    parser.add_argument("--outdir", type=Path, default=Path("outputs/week17"))
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    parser.add_argument("--seed", type=int, default=20261001)
    return parser.parse_args(argv)


def _resolve(path):
    return path if path.is_absolute() else (REPO_ROOT / path)


def main(argv=None) -> int:
    global _FROZEN
    args = parse_args(argv)
    outdir = _resolve(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    outputs_root = _resolve(args.outputs_root)
    seed = args.seed
    mc_samples = 20000

    # The discovery arm is resolved with Stage 17's own census, unchanged.  The
    # held-out arm needs the one adaptation documented on ``_strip_holdout``, so
    # it is indexed with the same primitives (``collect_outfiles`` /
    # ``parse_outfile_name`` / ``choose_path``) instead of a second grammar.
    census = s17.build_census(outputs_root)
    holdout_index = build_index(outputs_root)
    discovery = load_arm(read_cells(DISCOVERY_CSV), "discovery", census["index"])
    holdout = load_arm(read_cells(HOLDOUT_CSV), "holdout", holdout_index)

    if len(discovery) != EXPECTED_DISCOVERY_ROWS:
        raise SystemExit("expected %d discovery rows, got %d"
                         % (EXPECTED_DISCOVERY_ROWS, len(discovery)))
    if sum(record["label"] for record in discovery) != EXPECTED_DISCOVERY_POSITIVE:
        raise SystemExit("expected %d discovery positives, got %d"
                         % (EXPECTED_DISCOVERY_POSITIVE,
                            sum(record["label"] for record in discovery)))
    if len(holdout) != EXPECTED_HOLDOUT_ROWS:
        raise SystemExit("expected %d holdout rows, got %d"
                         % (EXPECTED_HOLDOUT_ROWS, len(holdout)))
    if sum(record["label"] for record in holdout) != EXPECTED_HOLDOUT_POSITIVE:
        raise SystemExit("expected %d holdout positives, got %d"
                         % (EXPECTED_HOLDOUT_POSITIVE,
                            sum(record["label"] for record in holdout)))

    # 1-2. screen the discovery set and freeze the top feature.
    screen = screen_entries(discovery, holdout)
    if not screen:
        raise SystemExit("nothing survived the single-variable screen")
    chosen = screen[0]
    _FROZEN = chosen
    name = chosen["descriptor"]
    larger = chosen["sign"] == "larger_is_riskier"
    threshold = chosen["threshold_frozen"]
    discovery_values = column(discovery, name)
    discovery_labels = labels_of(discovery)

    # 3. in sample.
    in_sample_matrix = confusion_at(discovery, name, threshold, larger)
    in_sample = {
        "feature": name,
        "sign": chosen["sign"],
        "threshold": threshold,
        "accuracy": chosen["accuracy_in_sample"],
        "balanced_accuracy": chosen["balanced_accuracy_in_sample"],
        "majority_accuracy": chosen["majority_accuracy"],
        "confusion_matrix": in_sample_matrix,
        "beats_majority": chosen["beats_majority_in_sample"],
        "balanced_beats_trivial": bool((chosen["balanced_accuracy_in_sample"] or 0.0) > 0.5),
    }

    # 4. leave-one-out.
    loo_accuracy, loo_balanced, loo_matrix = loo_rule_fast(
        discovery_values, discovery_labels, larger)
    loo = {
        "accuracy": loo_accuracy,
        "balanced_accuracy": loo_balanced,
        "majority_accuracy": chosen["majority_accuracy"],
        "confusion_matrix": loo_matrix,
        "beats_majority": bool(loo_accuracy is not None
                               and loo_accuracy > chosen["majority_accuracy"]),
        "definition": ("threshold re-fit on the n-1 remaining rows by maximising "
                       "plain accuracy; the direction is held at the one frozen "
                       "on the full discovery set, exactly as in Stage 16"),
    }

    # 5. significance.
    significance = significance_for(discovery_values, discovery_labels, seed, mc_samples)

    # 6. the held-out arm.
    holdout_matrix = confusion_at(holdout, name, threshold, larger)
    holdout_scored = sum(holdout_matrix.values())
    holdout_labels = labels_of(holdout)
    holdout_accuracy = ((holdout_matrix["true_positive"] + holdout_matrix["true_negative"])
                        / holdout_scored if holdout_scored else None)
    holdout_majority = majority_accuracy(holdout_labels)
    per_row = []
    for record in holdout:
        value = fill_value(name, record.get(name))
        per_row.append({
            "name": record["name"], "state": record["state"], "epsilon": record["epsilon"],
            "value": value, "raw_value": record.get(name),
            "predicted": bool(value >= threshold) if larger else bool(value <= threshold),
            "truth": bool(record["label"]), "delta_ev": record["delta_ev"],
            "classification": record["classification"],
        })
    holdout_block = {
        "feature": name, "sign": chosen["sign"], "threshold": threshold,
        "n_rows": len(holdout), "n_positive": sum(holdout_labels),
        "accuracy": holdout_accuracy,
        "balanced_accuracy": balanced_from_matrix(holdout_matrix),
        "majority_accuracy": holdout_majority,
        "confusion_matrix": holdout_matrix,
        "beats_majority": bool(holdout_accuracy is not None
                               and holdout_accuracy > holdout_majority),
        "per_row": per_row,
        "note": ("the descriptor, the direction and the threshold all come from the "
                 "discovery set; nothing here is fitted on the held-out arm"),
    }

    # 7. post-hoc per state (+ the open-shell pool Stage 16 used).
    by_state = {state: state_block(discovery, holdout, state, seed, mc_samples)
                for state in STATES}
    by_state["open_shell_pooled"] = state_block(
        discovery, holdout, OPEN_SHELL_STATES, seed, mc_samples)
    by_state["open_shell_pooled"]["note"] = (
        "post-hoc: the set Stage 16 actually used, i.e. neutrals dropped; reported "
        "next to the pooled view because a closed-shell neutral cannot carry the "
        "label and therefore drags any pooled baseline up to ~0.91")

    # 8. multivariate ceiling.
    top_names = [entry["descriptor"] for entry in screen[:3]]
    ceiling = multivariate_ceiling(discovery, holdout, top_names)

    # supplementary, one-sided reading of ORCA's own small-gap warning; nothing
    # above this line changes, and the frozen threshold is passed in verbatim.
    one_sided = one_sided_screening(discovery, holdout, threshold)


    # honest verdict
    wins_loo = loo["beats_majority"]
    wins_holdout = holdout_block["beats_majority"]
    if wins_holdout and wins_loo:
        verdict = ("赢了：`%s` 在留出臂上 %.3f 对基线 %.3f，且在发现集的 LOO 上也超过基线（%.3f 对 %.3f）。"
                   % (name, holdout_accuracy, holdout_majority, loo_accuracy,
                      chosen["majority_accuracy"]))
    elif wins_holdout and not wins_loo:
        verdict = ("留出臂赢了、发现集 LOO 输了：`%s` 留出 %.3f 对基线 %.3f，但发现集 LOO %.3f 不及基线 %.3f，"
                   "效应量小且方向不一致，不能当作可用规则。"
                   % (name, holdout_accuracy, holdout_majority, loo_accuracy,
                      chosen["majority_accuracy"]))
    elif wins_loo and not wins_holdout:
        verdict = ("输了（样本外）：`%s` 在发现集上看着不错（LOO %.3f > 基线 %.3f，精确 p = %.3g），"
                   "但在真正留出的 54 格上只到 %.3f、输给多数类基线 %.3f（TP=%d, FP=%d）。"
                   "这正是 Week 15 的教训重演 —— 池化发现集上的漂亮数字不是可用的预警。"
                   % (name, loo_accuracy, chosen["majority_accuracy"],
                      significance["p_value"], holdout_accuracy, holdout_majority,
                      holdout_matrix["true_positive"], holdout_matrix["false_positive"]))
    else:
        verdict = ("输了：`%s` 在发现集 LOO（%.3f 对 %.3f）和留出臂（%.3f 对 %.3f）上都不及多数类基线。"
                   % (name, loo_accuracy, chosen["majority_accuracy"],
                      holdout_accuracy, holdout_majority))

    # extraction gaps, computed rather than asserted
    gaps = []
    all_records = discovery + holdout
    for feature in NUMERIC_FEATURES:
        missing = sum(1 for record in all_records if record.get(feature) is None)
        if missing:
            gaps.append("`%s`：%d/%d 行缺失（%s）"
                        % (feature, missing, len(all_records),
                           gap_reason(feature)))
    gaps.append("Löwdin 原子自旋的**约化轨道**子块：Stage 17 只解析 MULLIKEN REDUCED ORBITAL，"
                "没有 LOEWDIN REDUCED ORBITAL 解析器，因此没有 `loewdin_orbital_abs`。")
    gaps.append("beta (SPIN DOWN) 轨道的 HOMO/LUMO：只解析了 alpha 块，UKS 的 beta 本征值未提取。")
    gaps.append("`scf_final_diiserr` 对少数直接进入 SOSCF 的格子为空（无 DIIS 块），按 %s 填充。"
                % _fmt(FEATURE_FILL.get("scf_final_diiserr", DEFAULT_FILL), 3))

    missing_columns = "；".join(
        "%s %d/%d" % (feature,
                      sum(1 for record in all_records if record.get(feature) is None),
                      len(all_records))
        for feature in NUMERIC_FEATURES
        if any(record.get(feature) is None for record in all_records))
    gaps_md = [
        "有缺失的特征列（行数）：" + missing_columns + "。",
        "缺失原因：闭壳中性分子不打印自旋块（s2 / spin_* / loewdin_spin_* 各缺 138/414）；"
        "gap_warn_value 缺 140/414＝ORCA 未报警（gap 大），按 +1.0 Eh 填充；"
        "scf_final_diiserr 缺 2/414＝该 run 无 DIIS 块。",
        "Löwdin 原子自旋的约化轨道子块未解析（Stage 17 只有 MULLIKEN REDUCED ORBITAL 解析器）→ 没有 loewdin_orbital_abs。",
        "只解析 alpha 块 → 没有 beta (SPIN DOWN) 的 HOMO/LUMO。",
        "自旋中心/轨道通道是字符串（如 C0、N2 s），无序，只进 CSV，不参与 AUC 筛选。",
    ]

    limits = [
        "标签只对开壳层（cation/anion）有定义；120 个中性格天然是负例，把池化多数类基线抬到 0.911，所以池化准确率本身信息量很低。",
        "留出臂只有 5 个正例，留出 accuracy 的分辨率是 1/54 ≈ 0.019，任何 1-2 个格子的差别都可能是噪声。",
        "精确零分布用的是 tie-aware Mann-Whitney U；它假设行之间可交换，忽略分子内的格子间相关（同一分子的 9-10 个 epsilon 并不独立）。",
        "特征来自已算完的默认臂 `.out`，因此这是一次**事后诊断**，不是事前预报；它的价值在于省掉第二次计算，而不是省掉第一次。",
        "发现集与留出臂的分子不同（12 vs 6），但都在同一套 r2SCAN-3c/C-PCM 协议下，方法学外推没有验证。",
        "筛选表里的留出列只作事后展示：确有其它零成本特征（例如 orbital_abs）在留出臂上同时胜过基线，但它们是在看到留出臂之后才被挑出来的，不构成证据；冻结规则只能看发现集。",        "单边筛查那一节只证明『警告是漏解的必要条件』，不构成事前预报：ORCA 的 gap 警告在 run 开始前就打了，它标的是体系难度而不是收敛到的解；把它反读成『必然漏解』是误用（负例假阳性率见 JSON 的 one_sided_screening.specificity）。",
    ]

    payload = {
        "stage": 18,
        "part": "B -- zero-extra-cost self-diagnosis of the default SCF solution",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "monte_carlo_samples": mc_samples,
        "one_line_verdict": verdict,
        "discovery": {
            "csv": str(DISCOVERY_CSV.relative_to(REPO_ROOT)),
            "n_rows": len(discovery),
            "n_positive": sum(discovery_labels),
        },
        "census": {
            "note": ("Stage 17's build_census resolves every discovery cell; the "
                     "holdout index reuses the same primitives with the "
                     "'_holdout' infix stripped"),
            "n_outfiles_scanned": census["n_outfiles_scanned"],
            "n_outfiles_parsed": census["n_outfiles_parsed"],
            "n_discovery_index_keys": len(census["index"]),
            "n_holdout_index_keys": len(holdout_index),
        },
        "features": [
            {"name": feature, "definition": FEATURE_NOTES.get(feature, ""),
             "n_missing": sum(1 for record in all_records if record.get(feature) is None),
             "missing_fill": FEATURE_FILL.get(feature, DEFAULT_FILL)}
            for feature in NUMERIC_FEATURES
        ],
        "label_features": list(LABEL_FEATURES),
        "screen": screen,
        "frozen_rule": {
            "descriptor": name,
            "definition": chosen["definition"],
            "sign": chosen["sign"],
            "threshold_frozen": threshold,
            "n_rows_used": chosen["n_rows"],
            "n_positive": chosen["n_positive"],
            "selection_basis": ("top of the discovery-set single-variable screen by "
                                "|AUC - 0.5|, i.e. the Stage 16 selection rule; the "
                                "threshold maximises plain accuracy on the full "
                                "discovery set"),
            "missing_fill": FEATURE_FILL.get(name, DEFAULT_FILL),
            "n_missing": chosen["n_missing"],
        },
        "in_sample": in_sample,
        "loo": loo,
        "significance": significance,
        "holdout": holdout_block,
        "one_sided_screening": one_sided,
        "by_state_post_hoc": by_state,
        "multivariate_ceiling": ceiling,
        "extraction_gaps": gaps,
        "extraction_gaps_md": gaps_md,
        "limits": limits,
    }

    write_features_csv(outdir / "stage18_selfdiagnosis_features.csv", discovery + holdout)
    write_by_state_csv(outdir / "stage18_selfdiagnosis_features_by_state.csv",
                       discovery + holdout)
    with (outdir / "stage18_selfdiagnosis.json").open("w", encoding="utf-8",
                                                      newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    n_lines = write_summary_md(outdir / "stage18_selfdiagnosis_summary.md", payload)

    print("Stage 18 part B -- zero-extra-cost self-diagnosis of the default SCF solution")
    print("discovery %d rows (%d positive) | holdout %d rows (%d positive)"
          % (len(discovery), sum(discovery_labels), len(holdout), sum(holdout_labels)))
    print("screen (top 8 by |AUC-0.5|):")
    for rank, entry in enumerate(screen[:8], 1):
        print("  %2d. %-24s auc %.4f  |AUC-.5| %.3f  thr %-10s loo %.4f  maj %.4f  %s"
              % (rank, entry["descriptor"], entry["auc"], entry["abs_auc_above_half"],
                 _fmt(entry["threshold_frozen"], 4), entry["loo_accuracy"] or float("nan"),
                 entry["majority_accuracy"],
                 "LOO beats" if entry["beats_majority_loo"] else "LOO loses"))
    print("frozen rule: %s %s %s" % (name, chosen["sign"], _fmt(threshold, 6)))
    print("in sample: acc %.4f (majority %.4f) bal %.4f"
          % (in_sample["accuracy"], in_sample["majority_accuracy"],
             in_sample["balanced_accuracy"] or float("nan")))
    print("loo: acc %.4f bal %.4f ; beats majority: %s"
          % (loo_accuracy, loo_balanced or float("nan"), loo["beats_majority"]))
    print("significance: %s p = %.4g" % (significance["method"], significance["p_value"]))
    print("holdout: acc %.4f (majority %.4f) ; beats majority: %s ; TP %d FP %d TN %d FN %d"
          % (holdout_accuracy, holdout_majority, holdout_block["beats_majority"],
             holdout_matrix["true_positive"], holdout_matrix["false_positive"],
             holdout_matrix["true_negative"], holdout_matrix["false_negative"]))
    for state, block in by_state.items():
        print("  by state %-18s n %3d pos %2d auc %s loo %s beats %s"
              % (state, block["n_rows"], block["n_positive"],
                 _fmt(block.get("auc"), 4), _fmt(block.get("loo_accuracy"), 4),
                 block.get("beats_majority_loo")))
    print("one-sided: %d/%d positives carry the gap warning "
          "(P(no warning|positive)=%.3f); specificity %.3f discovery / %.3f holdout"
          % (one_sided["necessity"]["overall"]["n_positive_with_warning"],
             one_sided["necessity"]["overall"]["n_positive"],
             one_sided["necessity"]["overall"]["p_no_warning_given_positive"] or 0.0,
             one_sided["specificity"]["by_arm"]["discovery"]["specificity"] or float("nan"),
             one_sided["specificity"]["by_arm"]["holdout"]["specificity"] or float("nan")))
    if ceiling and ceiling.get("loo_auc") is not None:
        print("multivariate ceiling: loo_auc %.4f holdout acc %s"
              % (ceiling["loo_auc"], _fmt(ceiling.get("holdout_accuracy"), 4)))
    print("verdict: %s" % verdict)
    for path, label in ((outdir / "stage18_selfdiagnosis_features.csv", "features"),
                        (outdir / "stage18_selfdiagnosis.json", "json"),
                        (outdir / "stage18_selfdiagnosis_features_by_state.csv", "by-state"),
                        (outdir / "stage18_selfdiagnosis_summary.md", "summary")):
        print("wrote %-10s %s" % (label, str(path.relative_to(REPO_ROOT))))
    print("summary lines: %d" % n_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
