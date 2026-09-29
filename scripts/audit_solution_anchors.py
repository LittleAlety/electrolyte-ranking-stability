#!/usr/bin/env python
"""Deterministic, offline audit of the solution-phase redox anchors.

Why this script exists
----------------------
``data/anchors/solution_redox_anchors.csv`` labels every row ``method=est``:
the values are literature-informed midpoints, not verbatim quotes from a single
primary measurement.  Gate 1 (``scripts/freeze_gates.py::evaluate_stage1``)
counts those rows, and stays NOT CLOSED while any of them remain.

A curator walked the cited sources on 2026-09-29 (network lookups: Crossref,
OpenAlex, Unpaywall, one full text pulled from a repository).  The outcome of
that review is frozen here as an *evidence registry*, so this script can
re-derive, offline and deterministically, for every row:

  * the decision (``exp`` / ``calc`` / ``est``),
  * the category of evidence that backs the decision,
  * whether the experimental conditions are complete AND matched, and
  * which fields are missing,

plus a set of internal-consistency checks (unit conventions, oxidation vs
reduction ordering, per-row plausibility windows, and a gas-phase vs
solution-phase magnitude sanity check).

The script never promotes a row just to satisfy a gate: a row becomes
``exp`` / ``calc`` only when its evidence record says the cited source provides
a *quotable* value obtained *under the row's own conditions*.  Everything else
honestly stays ``est``.

The network review itself is written up in
``data/anchors/solution_anchor_verification.md`` and
``docs/06_stage1_solution_anchor_audit.md``; this module only replays its
conclusions and adds the offline checks.

Usage
-----
    python scripts/audit_solution_anchors.py [--csv PATH] [--outdir DIR]

Exit status is 0 when no internal inconsistency is found and 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SOLUTION_CSV = REPO_ROOT / "data" / "anchors" / "solution_redox_anchors.csv"
GAS_CSV = REPO_ROOT / "data" / "anchors" / "gas_phase_anchors.csv"
CORE_SET_CSV = REPO_ROOT / "data" / "metadata" / "core_set.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week2"

AUDIT_DATE = "2026-09-29"

ALLOWED_ELECTRODES = {"Li/Li+", "Fc/Fc+", "SCE", "Ag/Ag+"}

#: Condition fields required by config/scientific_definitions.yaml
#: -> axis_C_external_reference -> R_sol -> condition_fields.
R_SOL_CONDITION_FIELDS = (
    "solvent",
    "supporting_salt",
    "concentration",
    "scan_conditions",
    "temperature",
    "reference_electrode",
)

# Plausibility windows for this project's Li/Li+ convention (see
# scripts/validate_anchors.py, which uses the same numbers).
REDUCTION_WINDOW = (-0.5, 3.0)
OXIDATION_WINDOW = (2.5, 6.5)
MIN_ECHEM_WINDOW = 1.0
MAX_ECHEM_WINDOW = 6.5
GAS_WINDOW_MARGIN = 0.5

# Uncertainty is widened for rows that stay ``est`` to reflect the unverified
# condition / reference-electrode spread.  Oxidation rows carry an extra
# penalty because a real electrolyte oxidises through a solvent-anion complex,
# so an isolated-solvent number is structurally only a guideline.
UNCERTAINTY_PENALTY = 0.2
OXIDATION_EXTRA_PENALTY = 0.1
UNCERTAINTY_CAP = 0.8

NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


# ---------------------------------------------------------------------------
# Evidence registry (frozen results of the 2026-09-29 network review)
# ---------------------------------------------------------------------------
SOURCES = {
    "10.1149/1.1415547": {
        "short": "Zhang & Kostecki, J. Electrochem. Soc. 2001",
        "title": "Electrochemical and Infrared Studies of the Reduction of Organic Carbonates",
        "resolved": True,
        "checked_via": "Crossref metadata (title/journal/year) + OpenAlex abstract",
        "kind": "experimental_literature",
        "covers": ["EC", "PC", "DMC", "DEC", "VC"],
        "note": ("CV reduction potentials of five carbonates (EC, PC, DEC, DMC, VC) on inert "
                 "(Au / glassy carbon) electrodes in THF with a supporting electrolyte - NOT the "
                 "neat solvent / 1 M LiPF6 / LSV conditions of the CSV rows. The abstract only "
                 "states the five values are 'above 1 V'; exact tabulated potentials were not "
                 "retrievable (publisher bot-block)."),
    },
    "10.1088/0957-4484/26/35/354003": {
        "short": "Borodin et al., Nanotechnology 2015",
        "title": "Towards high throughput screening of electrochemical stability of battery electrolytes",
        "resolved": True,
        "checked_via": "Crossref metadata + OpenAlex abstract",
        "kind": "computational",
        "covers": ["carbonates", "phosphates", "ethers", "esters"],
        "note": ("DFT screening of ISOLATED solvents surrounded by an implicit solvent; reports "
                 "first/second reduction and oxidation stability. A calc-type source, not an "
                 "experiment; exact per-solvent numbers were not retrievable (publisher bot-block)."),
    },
    "10.1021/acs.chemmater.6b02282": {
        "short": "Michan et al., Chem. Mater. 2016",
        "title": ("Fluoroethylene Carbonate and Vinylene Carbonate Reduction: Understanding "
                  "Lithium-Ion Battery Electrolyte Additives and Solid Electrolyte Interphase Formation"),
        "resolved": True,
        "checked_via": "Crossref/OpenAlex + full text from the Cambridge repository (PDF)",
        "kind": "experimental_products",
        "covers": ["FEC", "VC"],
        "note": ("Characterises FEC/VC reduction PRODUCTS obtained by chemical reduction with "
                 "lithium naphthalenide (XPS/NMR) plus DFT; the retrieved full text reports no "
                 "electrochemical reduction potential vs Li/Li+ (no 'V vs Li' value occurs)."),
    },
    "10.1016/j.jpowsour.2006.07.074": {
        "short": "Zhang, J. Power Sources 2006",
        "title": "A review on electrolyte additives for lithium-ion batteries",
        "resolved": True,
        "checked_via": "Crossref metadata + OpenAlex",
        "kind": "review",
        "covers": ["additives", "AN"],
        "note": "Secondary review of additives; no condition-controlled per-solvent potential table.",
    },
    "10.1016/j.coelec.2018.10.015": {
        "short": "Borodin, Curr. Opin. Electrochem. 2019",
        "title": ("Challenges with prediction of battery electrolyte electrochemical stability window "
                  "and guiding the electrode-electrolyte stabilization"),
        "resolved": True,
        "checked_via": "Crossref metadata + OpenAlex",
        "kind": "review",
        "covers": ["solvents"],
        "note": ("Discussion/review of the pitfalls of predicting stability windows; gives trends "
                 "rather than a single quotable per-solvent value."),
    },
    "10.1038/s41467-019-11317-3": {
        "short": "Fadel et al., Nat. Commun. 2019",
        "title": "Role of solvent-anion charge transfer in oxidative degradation of battery electrolytes",
        "resolved": True,
        "checked_via": "Crossref metadata + OpenAlex abstract",
        "kind": "computational",
        "covers": ["solvent-anion complexes"],
        "note": ("Shows electrolyte oxidation is a solvent-anion charge-transfer process; the "
                 "oxidation potential of the ISOLATED solvent is only an upper-bound-like "
                 "guideline, not a directly measured quantity."),
    },
    "10.1149/1.1838419": {
        "short": "Xu & Angell, J. Electrochem. Soc. 1998",
        "title": "High Anodic Stability of a New Electrolyte Solvent: Unsymmetric Noncyclic Aliphatic Sulfone",
        "resolved": True,
        "checked_via": "Crossref metadata + OpenAlex abstract",
        "kind": "experimental_literature",
        "covers": ["ethyl methyl sulfone (unsymmetric noncyclic sulfone)"],
        "note": ("Concerns an UNSYMMETRIC NONCYCLIC aliphatic sulfone, not the cyclic sulfone "
                 "sulfolane; reports a 5.8 V anodic limit for that other solvent, so it does not "
                 "support a sulfolane reduction or oxidation value."),
    },
}


def _ev(kind, strength, refs, missing, reason, quotable=False, conditions_match=False):
    return {
        "evidence_kind": kind,
        "strength": strength,
        "provides_quotable_value": quotable,
        "conditions_match": conditions_match,
        "refs": list(refs),
        "missing_fields": list(missing),
        "reason": reason,
    }


_CARB_RED_REASON = (
    "Cited primary source measured reduction of DILUTE carbonate in THF with a supporting "
    "electrolyte on inert electrodes by CV, not neat solvent + 1 M LiPF6 by LSV; its abstract "
    "reports the values only as 'above 1 V', so no exact value can be quoted under this row's "
    "conditions."
)
_ETHER_ESTER_RED_REASON = (
    "Only pointer is a DFT screening of ISOLATED solvents with implicit solvation (a calc-type "
    "source); its exact numbers were not retrievable, so this row is not a verbatim copy of a "
    "computed value either."
)
_REVIEW_RED_REASON = (
    "Only pointer is a review/discussion of stability-window prediction; it reports trends, not a "
    "condition-controlled per-solvent reduction potential."
)
_NO_REF_REASON = (
    "source_note names no verification target at all; no traceable reference was identified."
)
_SL_REASON = (
    "Cited paper is about an UNSYMMETRIC NONCYCLIC aliphatic sulfone (ethyl methyl sulfone), not "
    "the cyclic sulfone sulfolane; it reports a 5.8 V anodic limit for that other solvent and does "
    "not give a sulfolane reduction or oxidation value."
)
_OX_COUPLING_REASON = (
    "Fadel et al. show electrolyte oxidation is a solvent-anion charge-transfer process, so the "
    "oxidation potential of the ISOLATED solvent is only an upper-bound-like guideline and is not "
    "the quantity measured in a real cell; the secondary pointer is a review."
)

ROW_EVIDENCE = {
    ("EC", "reduction_potential"): _ev(
        "condition_mismatch", "exp", ["10.1149/1.1415547", "10.1088/0957-4484/26/35/354003"],
        ["quotable_primary_value", "condition_match:neat_LiPF6_LSV"],
        _CARB_RED_REASON + " (0.9 V for EC would even conflict with the source's '>1 V'.)"),
    ("PC", "reduction_potential"): _ev(
        "condition_mismatch", "exp", ["10.1149/1.1415547", "10.1088/0957-4484/26/35/354003"],
        ["quotable_primary_value", "condition_match:neat_LiPF6_LSV"], _CARB_RED_REASON),
    ("DMC", "reduction_potential"): _ev(
        "condition_mismatch", "exp", ["10.1149/1.1415547", "10.1088/0957-4484/26/35/354003"],
        ["quotable_primary_value", "condition_match:neat_LiPF6_LSV"], _CARB_RED_REASON),
    ("DEC", "reduction_potential"): _ev(
        "condition_mismatch", "exp", ["10.1149/1.1415547", "10.1088/0957-4484/26/35/354003"],
        ["quotable_primary_value", "condition_match:neat_LiPF6_LSV"], _CARB_RED_REASON),
    ("VC", "reduction_potential"): _ev(
        "condition_mismatch", "exp", ["10.1149/1.1415547", "10.1021/acs.chemmater.6b02282"],
        ["quotable_primary_value", "condition_match:neat_LiPF6_LSV"], _CARB_RED_REASON),
    ("EMC", "reduction_potential"): _ev(
        "source_does_not_cover_species", "exp",
        ["10.1149/1.1415547", "10.1088/0957-4484/26/35/354003"],
        ["quotable_primary_value"],
        "The five carbonates measured by the cited primary are EC, PC, DEC, DMC and VC; EMC is not "
        "among them, so the citation does not support an EMC value. The secondary pointer is a DFT "
        "screening, not a measurement."),
    ("FEC", "reduction_potential"): _ev(
        "source_does_not_provide_value", "exp",
        ["10.1021/acs.chemmater.6b02282", "10.1016/j.jpowsour.2006.07.074"],
        ["quotable_primary_value"],
        "Cited source characterises FEC/VC reduction products from chemical (lithium naphthalenide) "
        "reduction and reports no electrochemical reduction potential vs Li/Li+; the full text was "
        "retrieved and searched. The secondary pointer is a review."),
    ("DME", "reduction_potential"): _ev(
        "computational_not_retrieved", "calc", ["10.1088/0957-4484/26/35/354003"],
        ["quotable_computed_value", "condition_match:isolated_vs_neat"], _ETHER_ESTER_RED_REASON),
    ("DOL", "reduction_potential"): _ev(
        "computational_not_retrieved", "calc", ["10.1088/0957-4484/26/35/354003"],
        ["quotable_computed_value", "condition_match:isolated_vs_neat"], _ETHER_ESTER_RED_REASON),
    ("EA", "reduction_potential"): _ev(
        "computational_not_retrieved", "calc", ["10.1088/0957-4484/26/35/354003"],
        ["quotable_computed_value", "condition_match:isolated_vs_neat"], _ETHER_ESTER_RED_REASON),
    ("MA", "reduction_potential"): _ev(
        "computational_not_retrieved", "calc", ["10.1088/0957-4484/26/35/354003"],
        ["quotable_computed_value", "condition_match:isolated_vs_neat"], _ETHER_ESTER_RED_REASON),
    ("GBL", "reduction_potential"): _ev(
        "computational_not_retrieved", "calc", ["10.1088/0957-4484/26/35/354003"],
        ["quotable_computed_value", "condition_match:isolated_vs_neat"], _ETHER_ESTER_RED_REASON),
    ("DMSO", "reduction_potential"): _ev(
        "review_trend_only", "none", ["10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value"], _REVIEW_RED_REASON),
    ("AN", "reduction_potential"): _ev(
        "review_trend_only", "none", ["10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value"], _REVIEW_RED_REASON),
    ("TMP", "reduction_potential"): _ev(
        "no_reference", "none", [], ["quotable_primary_value"], _NO_REF_REASON),
    ("SL", "reduction_potential"): _ev(
        "mis_citation", "none", ["10.1149/1.1838419"], ["quotable_primary_value"], _SL_REASON),
    ("EC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("PC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("DMC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("EMC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("DEC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("FEC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("VC", "oxidation_potential"): _ev(
        "solvent_anion_coupling", "calc", ["10.1038/s41467-019-11317-3", "10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value", "condition_match:isolated_vs_coupled"], _OX_COUPLING_REASON),
    ("DME", "oxidation_potential"): _ev(
        "review_trend_only", "none", ["10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value"],
        "Only pointer is a review; it gives ether-vs-carbonate trends, not a quotable per-solvent "
        "oxidation potential."),
    ("DOL", "oxidation_potential"): _ev(
        "review_trend_only", "none", ["10.1016/j.coelec.2018.10.015"],
        ["quotable_primary_value"],
        "Only pointer is a review; it gives ether-vs-carbonate trends, not a quotable per-solvent "
        "oxidation potential."),
    ("EA", "oxidation_potential"): _ev(
        "no_reference", "none", [], ["quotable_primary_value"], _NO_REF_REASON),
    ("GBL", "oxidation_potential"): _ev(
        "no_reference", "none", [], ["quotable_primary_value"], _NO_REF_REASON),
    ("SL", "oxidation_potential"): _ev(
        "mis_citation", "none", ["10.1149/1.1838419"], ["quotable_primary_value"], _SL_REASON),
    ("DMSO", "oxidation_potential"): _ev(
        "no_reference", "none", [], ["quotable_primary_value"], _NO_REF_REASON),
    ("AN", "oxidation_potential"): _ev(
        "review_trend_only", "none", ["10.1016/j.jpowsour.2006.07.074"],
        ["quotable_primary_value"],
        "Only pointer is a review of electrolyte additives; no condition-controlled per-solvent "
        "oxidation potential."),
    ("TMP", "oxidation_potential"): _ev(
        "no_reference", "none", [], ["quotable_primary_value"], _NO_REF_REASON),
}


#: Original (pre-audit) uncertainty of the literature-informed estimates.  The
#: widening policy is applied to THESE values, not to whatever is currently in
#: the CSV, so the audit is idempotent: re-running it on the already-updated
#: file reproduces the same numbers.
BASE_UNCERTAINTY = {
    ("EC", "reduction_potential"): 0.3,
    ("PC", "reduction_potential"): 0.3,
    ("DMC", "reduction_potential"): 0.3,
    ("EMC", "reduction_potential"): 0.3,
    ("DEC", "reduction_potential"): 0.3,
    ("FEC", "reduction_potential"): 0.4,
    ("VC", "reduction_potential"): 0.4,
    ("DME", "reduction_potential"): 0.3,
    ("DOL", "reduction_potential"): 0.3,
    ("EA", "reduction_potential"): 0.4,
    ("MA", "reduction_potential"): 0.4,
    ("GBL", "reduction_potential"): 0.3,
    ("SL", "reduction_potential"): 0.3,
    ("DMSO", "reduction_potential"): 0.5,
    ("AN", "reduction_potential"): 0.5,
    ("TMP", "reduction_potential"): 0.4,
    ("EC", "oxidation_potential"): 0.5,
    ("PC", "oxidation_potential"): 0.5,
    ("DMC", "oxidation_potential"): 0.5,
    ("EMC", "oxidation_potential"): 0.5,
    ("DEC", "oxidation_potential"): 0.5,
    ("FEC", "oxidation_potential"): 0.5,
    ("VC", "oxidation_potential"): 0.5,
    ("DME", "oxidation_potential"): 0.5,
    ("DOL", "oxidation_potential"): 0.5,
    ("EA", "oxidation_potential"): 0.5,
    ("GBL", "oxidation_potential"): 0.5,
    ("SL", "oxidation_potential"): 0.5,
    ("DMSO", "oxidation_potential"): 0.4,
    ("AN", "oxidation_potential"): 0.5,
    ("TMP", "oxidation_potential"): 0.5,
}


# ---------------------------------------------------------------------------
# Core decision / scoring logic
# ---------------------------------------------------------------------------
def decide(evidence):
    """Return ``exp`` / ``calc`` / ``est`` for a single evidence record.

    A row is promoted only when the source provides a quotable value AND that
    value was obtained under the row's own conditions.
    """
    if not evidence:
        return "est"
    if not evidence.get("provides_quotable_value") or not evidence.get("conditions_match"):
        return "est"
    return {"exp": "exp", "calc": "calc"}.get(evidence.get("strength", ""), "est")


def parse_float(text):
    text = (text or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_electrolyte_note(note):
    fields = {}
    for part in (note or "").split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            fields[key.strip()] = value.strip()
    return fields


def structural_conditions(row):
    """Return ``(present, missing)`` for the R_sol condition fields of a row."""
    note = parse_electrolyte_note(row.get("electrolyte_note", ""))
    values = {
        "solvent": row.get("solvent", "").strip(),
        "supporting_salt": note.get("supporting_salt", ""),
        "concentration": note.get("concentration", ""),
        "scan_conditions": note.get("scan_conditions", ""),
        "temperature": row.get("temperature_K", "").strip(),
        "reference_electrode": row.get("reference_electrode", "").strip(),
    }
    missing = [field for field in R_SOL_CONDITION_FIELDS if not values.get(field)]
    return (not missing), missing


def recommended_uncertainty(base_uncertainty, property_name, decision):
    """Widened uncertainty for retained ``est`` rows (documented rule).

    Applied to the ORIGINAL base uncertainty, so the result is idempotent and
    re-running the audit on the already-updated CSV reproduces the same number.
    """
    base = float(base_uncertainty or 0.0)
    if decision != "est":
        return round(base, 2)
    penalty = UNCERTAINTY_PENALTY
    if property_name == "oxidation_potential":
        penalty += OXIDATION_EXTRA_PENALTY
    return round(min(base + penalty, UNCERTAINTY_CAP), 2)


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------
def _read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_solution_rows(path=SOLUTION_CSV):
    return _read_csv(path)


def load_gas_rows(path=GAS_CSV):
    return _read_csv(path)


def load_mol_ids(path=CORE_SET_CSV):
    mapping = {}
    for row in _read_csv(path):
        name = (row.get("name") or "").strip()
        mol_id = (row.get("mol_id") or "").strip()
        if name and mol_id:
            mapping[name] = mol_id
    return mapping


def load_gas_ion_energies(gas_rows):
    """``{species: {"IP": float, "EA": float}}`` for populated gas entries."""
    energies = defaultdict(dict)
    for row in gas_rows:
        value = parse_float(row.get("value_eV", ""))
        if value is not None and row.get("property") in {"IP", "EA"}:
            energies[row["species"]][row["property"]] = value
    return dict(energies)


# ---------------------------------------------------------------------------
# Internal-consistency checks
# ---------------------------------------------------------------------------
def check_row_consistency(row, index):
    issues = []
    where = "row %d (%s / %s)" % (index, row.get("species", "?"), row.get("property", "?"))

    electrode = (row.get("reference_electrode") or "").strip()
    if electrode not in ALLOWED_ELECTRODES:
        issues.append({"where": where, "check": "electrode",
                       "detail": "reference_electrode %r not in %s" % (electrode, sorted(ALLOWED_ELECTRODES))})

    raw = (row.get("value_V") or "").strip()
    value = parse_float(raw)
    if raw == "":
        issues.append({"where": where, "check": "value_present", "detail": "value_V is empty"})
    elif value is None:
        issues.append({"where": where, "check": "value_numeric",
                       "detail": "value_V %r is not a bare number (unit must live in the column suffix)" % raw})

    if value is not None:
        prop = row.get("property")
        if prop == "reduction_potential" and not (REDUCTION_WINDOW[0] <= value <= REDUCTION_WINDOW[1]):
            issues.append({"where": where, "check": "window",
                           "detail": "reduction %.4g V outside %s" % (value, REDUCTION_WINDOW)})
        if prop == "oxidation_potential" and not (OXIDATION_WINDOW[0] <= value <= OXIDATION_WINDOW[1]):
            issues.append({"where": where, "check": "window",
                           "detail": "oxidation %.4g V outside %s" % (value, OXIDATION_WINDOW)})

    uncertainty = parse_float(row.get("uncertainty_V", ""))
    if uncertainty is None:
        issues.append({"where": where, "check": "uncertainty_present", "detail": "uncertainty_V is empty"})
    elif uncertainty < 0:
        issues.append({"where": where, "check": "uncertainty_sign",
                       "detail": "uncertainty_V is negative: %s" % uncertainty})

    if electrode not in ("", "Li/Li+") and value is not None:
        note = row.get("source_note", "")
        if "convert" not in note.lower() and "vs" not in note.lower():
            issues.append({"where": where, "check": "conversion_documented",
                           "detail": "non-Li/Li+ electrode %r without a documented conversion" % electrode})
    return issues


def check_species_consistency(rows):
    """Oxidation must sit above reduction, with a physically sane window."""
    issues = []
    by_species = defaultdict(dict)
    for index, row in enumerate(rows, start=2):
        by_species[row.get("species")][row.get("property")] = (index, row)
    for species, props in by_species.items():
        if "oxidation_potential" not in props or "reduction_potential" not in props:
            continue
        _, ox_row = props["oxidation_potential"]
        _, red_row = props["reduction_potential"]
        ox = parse_float(ox_row.get("value_V", ""))
        red = parse_float(red_row.get("value_V", ""))
        if ox is None or red is None:
            continue
        window = ox - red
        if window <= 0:
            issues.append({"where": species, "check": "ox_above_red",
                           "detail": "oxidation %.4g V <= reduction %.4g V" % (ox, red)})
        elif not (MIN_ECHEM_WINDOW <= window <= MAX_ECHEM_WINDOW):
            issues.append({"where": species, "check": "window_range",
                           "detail": "electrochemical window %.4g V outside [%.1f, %.1f]"
                                     % (window, MIN_ECHEM_WINDOW, MAX_ECHEM_WINDOW)})
    return issues


def check_gas_solution_consistency(rows, gas_energies):
    """Solution window must not exceed the gas-phase IP - EA gap (solvation narrows it)."""
    issues = []
    by_species = defaultdict(dict)
    for row in rows:
        by_species[row.get("species")][row.get("property")] = row
    for species, props in by_species.items():
        gas = gas_energies.get(species)
        if not gas or "IP" not in gas or "EA" not in gas:
            continue
        if "oxidation_potential" not in props or "reduction_potential" not in props:
            continue
        ox = parse_float(props["oxidation_potential"].get("value_V", ""))
        red = parse_float(props["reduction_potential"].get("value_V", ""))
        if ox is None or red is None:
            continue
        gap = gas["IP"] - gas["EA"]
        window = ox - red
        if window > gap + GAS_WINDOW_MARGIN:
            issues.append({
                "where": species, "check": "gas_solution_magnitude",
                "detail": ("solution window %.4g V exceeds gas-phase IP-EA gap %.4g eV (+margin %.1f)"
                           % (window, gap, GAS_WINDOW_MARGIN)),
            })
    return issues


def check_registry_alignment(records):
    """The CSV on disk must already match the registry (idempotent replay).

    If a curator edits the CSV (promotes a row, changes an uncertainty) without
    updating the evidence registry, the audit must notice.
    """
    issues = []
    for record in records:
        if not record["matches_rule"]:
            issues.append({
                "where": "row %d (%s / %s)" % (record["row_id"], record["species"], record["property"]),
                "check": "csv_matches_registry",
                "detail": ("CSV has method=%r uncertainty=%r but the registry implies method=%r "
                           "uncertainty=%r" % (record["method_before"], record["uncertainty_csv_V"],
                                               record["decision"], record["uncertainty_recommended_V"])),
            })
    return issues


def check_consistency(rows, gas_energies, records=None):
    issues = []
    for index, row in enumerate(rows, start=2):
        issues.extend(check_row_consistency(row, index))
    issues.extend(check_species_consistency(rows))
    issues.extend(check_gas_solution_consistency(rows, gas_energies))
    if records is not None:
        issues.extend(check_registry_alignment(records))
    return issues


# ---------------------------------------------------------------------------
# Record building / summary
# ---------------------------------------------------------------------------
def build_records(rows, mol_ids, evidence=None):
    evidence = ROW_EVIDENCE if evidence is None else evidence
    records = []
    for index, row in enumerate(rows, start=1):
        key = (row.get("species"), row.get("property"))
        record = evidence.get(key)
        decision = decide(record)
        _, structural_missing = structural_conditions(row)
        missing = list(structural_missing)
        for item in (record or {}).get("missing_fields", ["evidence_record"]):
            if item not in missing:
                missing.append(item)
        conditions_complete = (not missing) and decision in {"exp", "calc"}
        method_in_csv = (row.get("method") or "").strip()
        uncertainty_csv = (row.get("uncertainty_V") or "").strip()
        base = BASE_UNCERTAINTY.get(key)
        if base is None:
            base = parse_float(uncertainty_csv) or 0.0
        uncertainty_recommended = recommended_uncertainty(base, row.get("property"), decision)
        matches_rule = (
            method_in_csv == decision
            and parse_float(uncertainty_csv) == parse_float(str(uncertainty_recommended))
        )
        records.append({
            "row_id": index,
            "mol_id": mol_ids.get(row.get("species"), ""),
            "species": row.get("species", ""),
            "property": row.get("property", ""),
            "method_before": method_in_csv,
            "decision": decision,
            "evidence_kind": (record or {}).get("evidence_kind", "unclassified"),
            "evidence_reference": "; ".join((record or {}).get("refs", [])),
            "conditions_complete": conditions_complete,
            "missing_fields": "; ".join(missing),
            "value_V": (row.get("value_V") or "").strip(),
            "uncertainty_base_V": base,
            "uncertainty_csv_V": uncertainty_csv,
            "uncertainty_recommended_V": uncertainty_recommended,
            "matches_rule": matches_rule,
            "notes": (record or {}).get("reason", "no evidence record on file"),
        })
    return records


def summarize(rows, records, consistency_issues):
    before = Counter((r.get("method") or "").strip() for r in rows)
    decisions = Counter(record["decision"] for record in records)
    kinds = Counter(record["evidence_kind"] for record in records)
    promoted = [{"row_id": rec["row_id"], "species": rec["species"], "property": rec["property"],
                 "to": rec["decision"]}
                for rec in records if rec["decision"] != "est"]
    still_est = [{"row_id": rec["row_id"], "species": rec["species"], "property": rec["property"],
                  "evidence_kind": rec["evidence_kind"]}
                 for rec in records if rec["decision"] == "est"]
    return {
        "audit_date": AUDIT_DATE,
        "rows_total": len(rows),
        "method_before": dict(before),
        "decisions": {"exp": decisions.get("exp", 0), "calc": decisions.get("calc", 0),
                      "est": decisions.get("est", 0)},
        "upgraded": promoted,
        "still_est_count": len(still_est),
        "still_est": still_est,
        "evidence_kinds": dict(kinds),
        "consistency_issues": consistency_issues,
        "consistency_ok": not consistency_issues,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
AUDIT_COLUMNS = [
    "row_id", "mol_id", "species", "property", "method_before", "decision",
    "evidence_kind", "evidence_reference", "conditions_complete", "missing_fields",
    "value_V", "uncertainty_base_V", "uncertainty_csv_V", "uncertainty_recommended_V",
    "matches_rule", "notes",
]


def write_outputs(records, summary, outdir=DEFAULT_OUTDIR):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "solution_anchor_audit.csv"
    json_path = outdir / "solution_anchor_audit.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in AUDIT_COLUMNS})
    payload = {"summary": summary, "rows": records, "sources": SOURCES}
    with json_path.open("w", encoding="utf-8", newline="") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")
    return csv_path, json_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=str(SOLUTION_CSV))
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = parser.parse_args(argv)

    rows = load_solution_rows(args.csv)
    gas_energies = load_gas_ion_energies(load_gas_rows())
    mol_ids = load_mol_ids()

    records = build_records(rows, mol_ids)
    consistency = check_consistency(rows, gas_energies, records)
    summary = summarize(rows, records, consistency)
    csv_path, json_path = write_outputs(records, summary, args.outdir)

    print("solution anchor audit (%s)" % AUDIT_DATE)
    print("  rows            : %d" % summary["rows_total"])
    print("  method (before) : %s" % summary["method_before"])
    print("  decision        : %s" % summary["decisions"])
    print("  evidence kinds  : %s" % summary["evidence_kinds"])
    print("  consistency     : %s" % ("OK" if summary["consistency_ok"] else "%d issue(s)" % len(consistency)))
    print("  wrote           : %s" % csv_path)
    print("  wrote           : %s" % json_path)
    return 0 if not consistency else 1


if __name__ == "__main__":
    raise SystemExit(main())
