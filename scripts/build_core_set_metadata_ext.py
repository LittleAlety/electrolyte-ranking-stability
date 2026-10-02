#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W25 gap fill: extend the core-set chemical-space metadata to the 13 axes of
``ranking-electrolyte-materials-v2.md`` SS5.2 (L368-388).

This script runs **no electronic-structure calculation**.  It only *extracts*
six fields that earlier stages already produced but never landed in
``data/metadata/core_set.csv`` -- a frozen artifact that is deliberately NOT
touched here.  Contents are written to a separate table::

    data/metadata/core_set_metadata_ext.csv   (exactly 18 data rows)

Field provenance
----------------
    formal_charge         <- outputs/week3/p0_core_set.csv : charge
    conformer_count       <- outputs/week6/t6_conformer_manifest.json : molecules[].n_kept
    Li_motif_count        <- outputs/week5/li_motif_generation.csv : motif_id of rows kept=True
    state_identity_status <- outputs/week5/c1_state_identity.csv : state_identity_label
    reactivity_status     <- outputs/week5/li_motif_generation.csv : qc_flags of rows kept=True
    qc_status             <- status columns of p0 / p1 / p2 (+ c1 where covered)

Discipline
----------
* Any field without a reliable source in this repository is written as the
  literal string ``not_available_in_repo``.  Nothing is interpolated, fitted or
  invented.
* A field that only exists for a subset is filled for that subset and set to
  ``not_available_in_repo`` elsewhere; the coverage (molecules / 18) is stated
  in the per-row ``source_refs`` column and in
  ``docs/42_w25_core_set_metadata_mapping.md``.
* ``--check`` rebuilds the table in memory and compares it byte-for-byte with
  the file on disk, exiting non-zero on any difference.  The script is
  deterministic and idempotent.
"""


from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_CSV = REPO_ROOT / "data" / "metadata" / "core_set.csv"
P0_CSV = REPO_ROOT / "outputs" / "week3" / "p0_core_set.csv"
P1_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
P2_CSV = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
MOTIF_CSV = REPO_ROOT / "outputs" / "week5" / "li_motif_generation.csv"
C1_COORD_CSV = REPO_ROOT / "outputs" / "week5" / "c1_li_coordination.csv"
C1_STATE_CSV = REPO_ROOT / "outputs" / "week5" / "c1_state_identity.csv"
CONF_JSON = REPO_ROOT / "outputs" / "week6" / "t6_conformer_manifest.json"
CONF_CSV = REPO_ROOT / "outputs" / "week6" / "t6_conformer_manifest.csv"
OUT_CSV = REPO_ROOT / "data" / "metadata" / "core_set_metadata_ext.csv"

NA = "not_available_in_repo"

COLUMNS = [
    "mol_id",
    "name",
    "formal_charge",
    "conformer_count",
    "Li_motif_count",
    "state_identity_status",
    "reactivity_status",
    "qc_status",
    "source_refs",
]

# Source descriptors used verbatim inside the per-row source_refs column.
S_FORMAL = "outputs/week3/p0_core_set.csv:charge"
S_CONF = "outputs/week6/t6_conformer_manifest.json:molecules[].n_kept"
S_MOTIF = "outputs/week5/li_motif_generation.csv:motif_id(kept=True)"
S_STATE = "outputs/week5/c1_state_identity.csv:state_identity_label"
S_REACT = "outputs/week5/li_motif_generation.csv:qc_flags(kept=True)"
S_QC = (
    "outputs/week3/p0_core_set.csv:status"
    "+outputs/week4/p1_core_set.csv:status"
    "+outputs/week4/p2_core_set_smd_acetonitrile.csv:status"
    "+outputs/week5/c1_li_coordination.csv:status"
)

REDOX_STATE_ORDER = ("dication", "reduced")


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------
def _read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _unique_join(values, sep="+"):
    seen = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return sep.join(seen)


def _status_by_mol(rows):
    grouped = defaultdict(set)
    for row in rows:
        grouped[row["mol_id"]].add(row["status"].strip())
    return {mol_id: _unique_join(sorted(statuses)) for mol_id, statuses in grouped.items()}


# ---------------------------------------------------------------------------
# Field extraction (literal aggregation of existing values only)
# ---------------------------------------------------------------------------
def build_columns():
    core = _read_csv(CORE_CSV)
    core_ids = [row["mol_id"] for row in core]
    if len(core_ids) != 18:
        raise SystemExit("[FAIL] core_set.csv has %d rows, expected 18" % len(core_ids))

    # 1) formal_charge <- p0_core_set.csv : charge (parent / neutral molecule)
    p0_rows = _read_csv(P0_CSV)
    formal = {}
    for row in p0_rows:
        formal[row["mol_id"]] = row["charge"].strip()
    missing = [mol_id for mol_id in core_ids if mol_id not in formal]
    if missing:
        raise SystemExit("[FAIL] p0_core_set.csv lacks mol_id(s): %s" % ",".join(missing))

    # 2) conformer_count <- t6_conformer_manifest : n_kept per molecule.
    #    Cross-checked against the number of rows in the manifest CSV.
    manifest = json.loads(CONF_JSON.read_text(encoding="utf-8"))
    conformers = {entry["mol_id"]: int(entry["n_kept"]) for entry in manifest["molecules"]}
    manifest_rows = Counter(row["mol_id"] for row in _read_csv(CONF_CSV))
    for mol_id, count in conformers.items():
        if manifest_rows.get(mol_id, 0) != count:
            raise SystemExit(
                "[FAIL] conformer_count mismatch for %s: json=%d csv=%d"
                % (mol_id, count, manifest_rows.get(mol_id, 0))
            )

    # 3) Li_motif_count <- li_motif_generation.csv : kept motif_id per molecule.
    #    Cross-checked against the unique motif_id set in c1_li_coordination.csv.
    kept_rows = [
        row for row in _read_csv(MOTIF_CSV) if row["kept"].strip().lower() == "true"
    ]
    motif_count = Counter(row["mol_id"] for row in kept_rows)
    coord_motifs = defaultdict(set)
    for row in _read_csv(C1_COORD_CSV):
        coord_motifs[row["mol_id"]].add(row["motif_id"].strip())
    for mol_id, count in motif_count.items():
        if len(coord_motifs[mol_id]) != count:
            raise SystemExit(
                "[FAIL] Li_motif_count mismatch for %s: motif csv=%d coordination=%d"
                % (mol_id, count, len(coord_motifs[mol_id]))
            )

    # 4) state_identity_status <- c1_state_identity.csv : state_identity_label,
    #    reported per redox state (multiple motifs collapsed when identical).
    state_labels = defaultdict(lambda: defaultdict(set))
    for row in _read_csv(C1_STATE_CSV):
        state_labels[row["mol_id"]][row["redox_state"].strip()].add(
            row["state_identity_label"].strip()
        )
    state_identity = {}
    for mol_id, states in state_labels.items():
        parts = []
        for state in REDOX_STATE_ORDER:
            if state in states:
                parts.append("%s=%s" % (state, _unique_join(sorted(states[state]))))
        state_identity[mol_id] = ";".join(parts)

    # 5) reactivity_status <- li_motif_generation.csv : qc_flags of kept motifs.
    #    An empty flag set is reported as the spec vocabulary term "intact".
    kept_flags = defaultdict(set)
    for row in kept_rows:
        for flag in row["qc_flags"].split(";"):
            flag = flag.strip()
            if flag:
                kept_flags[row["mol_id"]].add(flag)
    reactivity = {
        mol_id: ("+".join(sorted(kept_flags[mol_id])) or "intact") for mol_id in motif_count
    }

    # 6) qc_status <- status columns of the p0 / p1 / p2 layers (+ c1 when covered).
    p0_status = _status_by_mol(p0_rows)
    p1_status = _status_by_mol(_read_csv(P1_CSV))
    p2_status = _status_by_mol(_read_csv(P2_CSV))
    c1_status = _status_by_mol(_read_csv(C1_COORD_CSV))

    rows = []
    for core_row in core:
        mol_id = core_row["mol_id"]
        name = core_row["name"]

        formal_value = formal[mol_id]
        conf_value = str(conformers[mol_id]) if mol_id in conformers else NA
        motif_value = str(motif_count[mol_id]) if mol_id in motif_count else NA
        state_value = state_identity.get(mol_id, NA)
        react_value = reactivity.get(mol_id, NA)

        qc_parts = [
            "p0=%s" % p0_status[mol_id],
            "p1=%s" % p1_status[mol_id],
            "p2=%s" % p2_status[mol_id],
        ]
        if mol_id in c1_status:
            qc_parts.append("c1=%s" % c1_status[mol_id])
        qc_value = ";".join(qc_parts)

        refs = " | ".join(
            [
                "formal_charge<-%s" % (S_FORMAL if mol_id in formal else NA),
                "conformer_count<-%s" % (S_CONF if mol_id in conformers else NA),
                "Li_motif_count<-%s" % (S_MOTIF if mol_id in motif_count else NA),
                "state_identity_status<-%s" % (S_STATE if mol_id in state_identity else NA),
                "reactivity_status<-%s" % (S_REACT if mol_id in reactivity else NA),
                "qc_status<-%s" % S_QC,
            ]
        )

        rows.append(
            {
                "mol_id": mol_id,
                "name": name,
                "formal_charge": formal_value,
                "conformer_count": conf_value,
                "Li_motif_count": motif_value,
                "state_identity_status": state_value,
                "reactivity_status": react_value,
                "qc_status": qc_value,
                "source_refs": refs,
            }
        )
    return rows


def render_csv(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def coverage_summary(rows):
    covered = {
        "formal_charge": 0,
        "conformer_count": 0,
        "Li_motif_count": 0,
        "state_identity_status": 0,
        "reactivity_status": 0,
    }
    for row in rows:
        for field in covered:
            if row[field] != NA:
                covered[field] += 1
    return covered


def _assert_clean(rendered, rows):
    if "?" in rendered:
        raise SystemExit("[FAIL] output contains the '?' character (possible mojibake)")
    if "\ufffd" in rendered:
        raise SystemExit("[FAIL] output contains U+FFFD replacement characters")
    if len(rows) != 18:
        raise SystemExit("[FAIL] built %d rows, expected 18" % len(rows))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _report_diff(expected, actual):
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    shown = 0
    for index in range(max(len(expected_lines), len(actual_lines))):
        want = expected_lines[index] if index < len(expected_lines) else "<missing>"
        got = actual_lines[index] if index < len(actual_lines) else "<missing>"
        if want != got and shown < 10:
            print("  line %d" % (index + 1))
            print("    expected: %s" % want)
            print("    found   : %s" % got)
            shown += 1


def cmd_check():
    rows = build_columns()
    rendered = render_csv(rows)
    _assert_clean(rendered, rows)
    if not OUT_CSV.exists():
        print("[FAIL] %s is missing" % OUT_CSV)
        return 1
    on_disk = OUT_CSV.read_bytes().decode("utf-8")
    if on_disk == rendered:
        print("[ OK ] %s matches the rebuilt table (18 data rows)" % OUT_CSV.name)
        for field, count in coverage_summary(rows).items():
            print("       %-22s %2d/18" % (field, count))
        return 0
    print("[FAIL] %s differs from the rebuilt table" % OUT_CSV.name)
    _report_diff(rendered, on_disk)
    return 1


def cmd_write():
    rows = build_columns()
    rendered = render_csv(rows)
    _assert_clean(rendered, rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.write_bytes(rendered.encode("utf-8"))
    print("wrote %s (%d data rows)" % (OUT_CSV, len(rows)))
    for field, count in coverage_summary(rows).items():
        print("       %-22s %2d/18" % (field, count))
    return 0


def _configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def main(argv=None):
    _configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; compare the existing CSV with the rebuilt table",
    )
    args = parser.parse_args(argv)
    if args.check:
        return cmd_check()
    return cmd_write()


if __name__ == "__main__":
    raise SystemExit(main())