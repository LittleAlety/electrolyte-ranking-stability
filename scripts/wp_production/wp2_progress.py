#!/usr/bin/env python
"""Read-only WP2 runtime/scientific progress snapshot.

Runtime progress counts only payloads whose explicit ``status`` is ``computed``.
Scientific acceptance is deliberately stricter and is limited to the four main
states: normal termination, converged optimization, and zero imaginary modes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus", "M_tzvpd")
MAIN_STATES = STATES[:4]
METADATA = Path("data/metadata/physics_completion_set.csv")
FROZEN_LEDGER = Path("outputs/physics_completion/free_states/production_ledger.csv")


def _read_csv(path: Path):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main_molecules(repo: Path):
    rows = _read_csv(repo / METADATA)
    return [(row["mol_id"], row["name"]) for row in rows
            if row.get("cohort") == "main" and row.get("mol_id") and row.get("name")]


def _strict(row):
    return (row.get("status") == "computed"
            and str(row.get("terminated", "")).lower() == "true"
            and str(row.get("opt_converged", "")).lower() == "true"
            and str(row.get("imaginary_modes", "")) == "0")


def _frozen_accepted(row):
    """The generated production ledger contains only already-QC-filtered rows.

    Older ledger schemas do not repeat ``terminated``/``opt_converged``; require
    their explicit values when present, while always requiring computed/zero-imag.
    """
    if row.get("status") != "computed" or str(row.get("imaginary_modes", "")) != "0":
        return False
    return (row.get("terminated", "true").lower() == "true"
            and row.get("opt_converged", "true").lower() == "true")


def _aggregate_hash(items):
    digest = hashlib.sha256()
    for label, data in items:
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def build_snapshot(repo: Path):
    repo = Path(repo)
    molecules = main_molecules(repo)
    if len(molecules) != 12:
        raise ValueError("WP2 main cohort must contain exactly 12 molecules, got %d" % len(molecules))

    runtime_legs = []
    main_runtime_legs = []
    scientific_legs = []
    hash_items = []
    metadata_path = repo / METADATA
    hash_items.append((METADATA.as_posix(), metadata_path.read_bytes()))
    for mol_id, name in molecules:
        for state in STATES:
            rel = Path("work/wp2prod") / name / state / ("%s_%s.json" % (name, state))
            path = repo / rel
            data = path.read_bytes() if path.is_file() else b"<missing>"
            hash_items.append((rel.as_posix(), data))
            if not path.is_file():
                continue
            try:
                row = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            leg_id = "%s|%s" % (mol_id, state)
            if row.get("status") == "computed":
                runtime_legs.append(leg_id)
                if state in MAIN_STATES:
                    main_runtime_legs.append(leg_id)
            if state in MAIN_STATES and _strict(row):
                scientific_legs.append(leg_id)

    ledger_path = repo / FROZEN_LEDGER
    ledger_data = ledger_path.read_bytes() if ledger_path.is_file() else b"<missing>"
    frozen_legs = []
    for row in _read_csv(ledger_path):
        if row.get("state") in MAIN_STATES and _frozen_accepted(row):
            frozen_legs.append(row.get("record_id") or "%s|%s" % (row.get("mol_id", ""), row["state"]))

    scientific_set = sorted(set(scientific_legs))
    frozen_set = sorted(set(frozen_legs))
    return {
        "runtime": {"computed": len(set(runtime_legs)), "total": len(molecules) * len(STATES),
                    "computed_legs": sorted(set(runtime_legs))},
        "main_runtime": {"computed": len(set(main_runtime_legs)),
                         "total": len(molecules) * len(MAIN_STATES),
                         "computed_legs": sorted(set(main_runtime_legs))},
        "scientific": {"accepted": len(scientific_set),
                       "total": len(molecules) * len(MAIN_STATES),
                       "accepted_legs": scientific_set},
        "frozen": {"accepted": len(frozen_set), "total": len(molecules) * len(MAIN_STATES),
                   "accepted_legs": frozen_set},
        "runtime_input_sha256": _aggregate_hash(hash_items),
        "scientific_ledger_sha256": hashlib.sha256(ledger_data).hexdigest(),
        "stale": scientific_set != frozen_set,
        "input_paths": [METADATA.as_posix(), "work/wp2prod/**/<name>_<state>.json",
                        FROZEN_LEDGER.as_posix()],
    }
