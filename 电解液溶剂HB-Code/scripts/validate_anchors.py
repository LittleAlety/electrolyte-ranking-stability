#!/usr/bin/env python
"""Validate the external reference anchor CSVs (v2 Axis C, stage 1).

Checks performed
----------------
1. schema          : exact header, required non-empty fields, enum values
2. unit suffixes   : numeric columns must carry an explicit unit suffix (*_eV / *_V / *_K)
3. numeric types   : every populated numeric cell must parse as float
4. plausibility    : IP 5-15 eV, EA -3..5 eV, potentials plausible vs the labelled
                     reference electrode, temperature_K 200-400, uncertainty >= 0
5. DOI format      : ^10.\d{4,9}/\S+$ for every populated doi cell
6. missing values  : empty cells are only allowed where the provenance allows them
7. duplicates      : no duplicate (species, property, <condition key>) rows

Exit status is 0 when no problem is found and 1 otherwise (2 for a usage error).

Only the Python standard library is used.

Usage
-----
    python scripts/validate_anchors.py [gas_csv] [solution_csv]
"""

from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GAS = os.path.join(REPO_ROOT, "data", "anchors", "gas_phase_anchors.csv")
DEFAULT_SOLUTION = os.path.join(REPO_ROOT, "data", "anchors", "solution_redox_anchors.csv")

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

GAS_HEADER = [
    "species", "smiles", "property", "value_eV", "uncertainty_eV",
    "method", "source_type", "doi", "source_note", "curated_by",
]
SOLUTION_HEADER = [
    "species", "smiles", "property", "value_V", "reference_electrode",
    "solvent", "electrolyte_note", "temperature_K", "method",
    "uncertainty_V", "doi", "source_note",
]

GAS_PROPERTY = {"IP", "EA"}
GAS_METHOD = {"exp", "calc", "est", "na"}
GAS_SOURCE_TYPE = {
    "nist_webbook", "high_level_calc", "experimental_literature",
    "literature_estimate", "unbound_anion", "not_curated", "reference_list",
}
GAS_VALUE_OPTIONAL = {"unbound_anion", "not_curated"}

SOLUTION_PROPERTY = {"oxidation_potential", "reduction_potential"}
#: ``est``            -- a literature-informed estimate with no verified source of
#:                      *this* value; the DOI column must stay empty.
#: ``series_rel``     -- a within-series relative anchor: the number is only
#:                      comparable to the other rows of the same source series, so
#:                      the DOI must name that series (R7, ``docs/31``).
#: ``verified_abs``   -- an absolute value traced to a primary source whose
#:                      conditions match this row; DOI required.
SOLUTION_METHOD = {"exp", "calc", "est", "series_rel", "verified_abs"}
SOURCE_BACKED_SOLUTION_METHODS = {"series_rel", "verified_abs"}
SOLUTION_ELECTRODE = {"Li/Li+", "Fc/Fc+", "SCE", "Ag/Ag+"}

POTENTIAL_WINDOW = {
    ("Li/Li+", "reduction_potential"): (-0.50, 3.00),
    ("Li/Li+", "oxidation_potential"): (2.50, 6.50),
    ("Fc/Fc+", "reduction_potential"): (-3.00, 3.50),
    ("Fc/Fc+", "oxidation_potential"): (-3.00, 3.50),
    ("SCE", "reduction_potential"): (-3.00, 3.50),
    ("SCE", "oxidation_potential"): (-3.00, 3.50),
    ("Ag/Ag+", "reduction_potential"): (-3.00, 3.50),
    ("Ag/Ag+", "oxidation_potential"): (-3.00, 3.50),
}

IP_RANGE = (5.0, 15.0)
EA_RANGE = (-3.0, 5.0)
TEMPERATURE_RANGE = (200.0, 400.0)
UNITS_IN_NUMERIC_COLUMNS = {
    "value_eV": "eV", "uncertainty_eV": "eV",
    "value_V": "V", "uncertainty_V": "V", "temperature_K": "K",
}


class Report:
    def __init__(self, path):
        self.path = path
        self.errors = []
        self.warnings = []
        self.rows = []

    def error(self, where, message):
        self.errors.append("[ERROR] %s: %s" % (where, message))

    def warn(self, where, message):
        self.warnings.append("[WARN ] %s: %s" % (where, message))


def read_csv(report, header):
    if not os.path.isfile(report.path):
        report.error("file", "not found: %s" % report.path)
        return
    with open(report.path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            got_header = next(reader)
        except StopIteration:
            report.error("file", "empty file (no header row)")
            return
        got_header = [cell.lstrip(chr(0xFEFF)).strip() for cell in got_header]
        if got_header != header:
            report.error("header", "unexpected header.\n    expected: %s\n    found   : %s"
                         % (header, got_header))
            return
        for index, raw in enumerate(reader, start=2):
            if not raw or all(cell.strip() == "" for cell in raw):
                report.warn("line %d" % index, "blank row skipped")
                continue
            if len(raw) != len(header):
                report.error("line %d" % index,
                             "expected %d fields, found %d" % (len(header), len(raw)))
                continue
            report.rows.append(dict(zip(header, (cell.strip() for cell in raw))))


def check_unit_suffixes(report):
    for column, unit in UNITS_IN_NUMERIC_COLUMNS.items():
        if not column.endswith("_" + unit):
            report.error("schema", "column %r does not carry unit suffix '_%s'" % (column, unit))


def parse_number(report, where, column, text):
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        report.error(where, "column %r is not numeric: %r" % (column, text))
        return None


def check_doi(report, where, doi):
    if doi == "":
        return
    if not DOI_RE.match(doi):
        report.error(where, "malformed DOI: %r (expected 10.xxxx/...)" % doi)


def check_required(report, where, row, columns):
    for column in columns:
        if row.get(column, "") == "":
            report.error(where, "required column %r is empty" % column)


def check_smiles(report, where, smiles):
    if smiles == "":
        return
    if " " in smiles or "\t" in smiles:
        report.error(where, "SMILES contains whitespace: %r" % smiles)
    if not re.search(r"[A-Za-z]", smiles):
        report.error(where, "SMILES has no atom tokens: %r" % smiles)


def validate_gas(report):
    check_unit_suffixes(report)
    seen = Counter()
    for index, row in enumerate(report.rows, start=2):
        where = "line %d (%s)" % (index, row.get("species", "?"))
        check_required(report, where, row,
                       ["species", "smiles", "property", "method",
                        "source_type", "source_note", "curated_by"])
        check_smiles(report, where, row.get("smiles", ""))

        prop = row.get("property", "")
        if prop not in GAS_PROPERTY:
            report.error(where, "property %r not in %s" % (prop, sorted(GAS_PROPERTY)))
        method = row.get("method", "")
        if method not in GAS_METHOD:
            report.error(where, "method %r not in %s" % (method, sorted(GAS_METHOD)))
        source_type = row.get("source_type", "")
        if source_type not in GAS_SOURCE_TYPE:
            report.error(where, "source_type %r not in %s" % (source_type, sorted(GAS_SOURCE_TYPE)))

        value = parse_number(report, where, "value_eV", row.get("value_eV", ""))
        unc = parse_number(report, where, "uncertainty_eV", row.get("uncertainty_eV", ""))

        if value is None:
            if source_type not in GAS_VALUE_OPTIONAL:
                report.error(where, "value_eV is empty but source_type=%r is not one of %s"
                             % (source_type, sorted(GAS_VALUE_OPTIONAL)))
            if unc is not None:
                report.error(where, "uncertainty_eV present while value_eV is empty")
            if method != "na":
                report.warn(where, "empty value with method=%r (expected 'na')" % method)
        else:
            if prop == "IP" and not (IP_RANGE[0] <= value <= IP_RANGE[1]):
                report.error(where, "IP %.4g eV outside plausible range %s" % (value, IP_RANGE))
            if prop == "EA" and not (EA_RANGE[0] <= value <= EA_RANGE[1]):
                report.error(where, "EA %.4g eV outside plausible range %s" % (value, EA_RANGE))
            if method == "na":
                report.warn(where, "method='na' but a value is present")

        if unc is not None and unc < 0:
            report.error(where, "uncertainty_eV is negative: %s" % unc)

        check_doi(report, where, row.get("doi", ""))
        if row.get("doi", "") == "" and source_type in {"nist_webbook", "high_level_calc"}:
            report.warn(where, "curated row without a DOI")

        seen[(row.get("species", ""), prop, source_type, method)] += 1
    for key, count in seen.items():
        if count > 1:
            report.warn("duplicate",
                        "%d rows share (species=%r, property=%r, source_type=%r, method=%r)"
                        % (count, key[0], key[1], key[2], key[3]))


def validate_solution(report):
    check_unit_suffixes(report)
    seen = Counter()
    for index, row in enumerate(report.rows, start=2):
        where = "line %d (%s)" % (index, row.get("species", "?"))
        check_required(report, where, row,
                       ["species", "smiles", "property", "reference_electrode",
                        "solvent", "temperature_K", "method", "source_note"])
        check_smiles(report, where, row.get("smiles", ""))

        prop = row.get("property", "")
        if prop not in SOLUTION_PROPERTY:
            report.error(where, "property %r not in %s" % (prop, sorted(SOLUTION_PROPERTY)))
        method = row.get("method", "")
        if method not in SOLUTION_METHOD:
            report.error(where, "method %r not in %s" % (method, sorted(SOLUTION_METHOD)))
        electrode = row.get("reference_electrode", "")
        if electrode not in SOLUTION_ELECTRODE:
            report.error(where, "reference_electrode %r not in %s"
                         % (electrode, sorted(SOLUTION_ELECTRODE)))

        value = parse_number(report, where, "value_V", row.get("value_V", ""))
        if value is None:
            report.error(where, "value_V is required and must not be empty")
        else:
            window = POTENTIAL_WINDOW.get((electrode, prop))
            if window is None:
                report.warn(where, "no plausibility window for (%r, %r)" % (electrode, prop))
            elif not (window[0] <= value <= window[1]):
                report.error(where, "%s %.4g V outside plausible %s window %s"
                             % (prop, value, electrode, window))

        unc = parse_number(report, where, "uncertainty_V", row.get("uncertainty_V", ""))
        if unc is None:
            report.warn(where, "uncertainty_V is empty")
        elif unc < 0:
            report.error(where, "uncertainty_V is negative: %s" % unc)
        elif unc == 0:
            report.warn(where, "uncertainty_V is exactly 0")

        temperature = parse_number(report, where, "temperature_K", row.get("temperature_K", ""))
        if temperature is not None and not (TEMPERATURE_RANGE[0] <= temperature <= TEMPERATURE_RANGE[1]):
            report.error(where, "temperature_K %.4g outside %s" % (temperature, TEMPERATURE_RANGE))

        doi = row.get("doi", "")
        check_doi(report, where, doi)
        if method == "est" and doi != "":
            report.error(where, "method='est' rows must leave doi empty "
                                "(doi means 'the source of THIS value')")
        if method in SOURCE_BACKED_SOLUTION_METHODS and doi == "":
            report.error(where, "method=%r rows must carry the DOI of the source "
                                "they were read from" % method)

        seen[(row.get("species", ""), prop, electrode, row.get("solvent", ""))] += 1
    for key, count in seen.items():
        if count > 1:
            report.warn("duplicate",
                        "%d rows share (species=%r, property=%r, electrode=%r, solvent=%r)"
                        % (count, key[0], key[1], key[2], key[3]))


def summarize_gas(report):
    rows = report.rows
    if not rows:
        return
    print("  rows                 : %d" % len(rows))
    print("  distinct species     : %d" % len({r["species"] for r in rows}))
    print("  property breakdown   : %s" % dict(Counter(r["property"] for r in rows)))
    print("  source_type          : %s" % dict(Counter(r["source_type"] for r in rows)))
    print("  method               : %s" % dict(Counter(r["method"] for r in rows)))
    print("  rows with a value    : %d" % sum(1 for r in rows if r.get("value_eV", "") != ""))
    print("  curated-literature   : %d" % sum(1 for r in rows
                                            if r.get("source_type") in {"nist_webbook", "high_level_calc"}))
    print("  rows with empty value: %d" % sum(1 for r in rows if r.get("value_eV", "") == ""))
    print("  rows with a DOI      : %d" % sum(1 for r in rows if r.get("doi", "")))


def summarize_solution(report):
    rows = report.rows
    if not rows:
        return
    print("  rows                 : %d" % len(rows))
    print("  distinct species     : %d" % len({r["species"] for r in rows}))
    print("  property breakdown   : %s" % dict(Counter(r["property"] for r in rows)))
    print("  method               : %s" % dict(Counter(r["method"] for r in rows)))
    print("  reference electrode  : %s" % dict(Counter(r["reference_electrode"] for r in rows)))
    print("  curated-literature   : %d" % sum(1 for r in rows if r.get("method") in {"exp", "calc"}))
    print("  estimated (est)      : %d" % sum(1 for r in rows if r.get("method") == "est"))
    print("  within-series (rel)  : %d" % sum(1 for r in rows if r.get("method") == "series_rel"))
    print("  verified absolute    : %d" % sum(1 for r in rows if r.get("method") == "verified_abs"))
    print("  rows with a DOI      : %d" % sum(1 for r in rows if r.get("doi", "")))


def main(argv):
    if len(argv) > 3:
        sys.stderr.write("usage: validate_anchors.py [gas_csv] [solution_csv]\n")
        return 2
    gas_path = argv[1] if len(argv) > 1 else DEFAULT_GAS
    solution_path = argv[2] if len(argv) > 2 else DEFAULT_SOLUTION

    gas = Report(gas_path)
    solution = Report(solution_path)

    read_csv(gas, GAS_HEADER)
    if not gas.errors:
        validate_gas(gas)

    read_csv(solution, SOLUTION_HEADER)
    if not solution.errors:
        validate_solution(solution)

    for report, title, summarizer in (
        (gas, "gas_phase_anchors.csv", summarize_gas),
        (solution, "solution_redox_anchors.csv", summarize_solution),
    ):
        print("=" * 62)
        print(title)
        print("-" * 62)
        summarizer(report)
        for message in report.warnings:
            print(message)
        for message in report.errors:
            print(message)
        print("  result               : %s" % ("OK" if not report.errors else "FAILED"))

    total_errors = len(gas.errors) + len(solution.errors)
    total_warnings = len(gas.warnings) + len(solution.warnings)
    print("=" * 62)
    print("TOTAL: %d error(s), %d warning(s)" % (total_errors, total_warnings))
    if total_errors:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
