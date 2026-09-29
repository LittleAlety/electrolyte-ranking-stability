"""Unit tests for scripts/audit_p1_core_set.py.

The tests build synthetic ORCA `.out` text and JSON sidecars under `tmp_path`
and pin the audit's behaviour: energy cross-checking, missing-output detection,
spin-contamination flagging, the molecule-level unbound-anion rule, and the
graceful empty-directory path.  The real `outputs/week4` T1 artifacts are never
touched.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from audit_p1_core_set import (
    CSV_COLUMNS,
    apply_unbound_anion,
    build_record,
    main,
)


def _out_text(
    energy: float,
    *,
    scf: bool = True,
    cycles: int = 10,
    spin: "float | None" = None,
    terminated: bool = True,
    version: str = "6.1.1",
) -> str:
    lines = ["                    Program Version %s  -  RELEASE   -" % version]
    if scf:
        lines.append(
            "        *           SCF CONVERGED AFTER  %d CYCLES          *" % cycles
        )
    else:
        lines.append("        *           SCF NOT CONVERGED          *")
    if spin is not None:
        lines.append("Expectation value of <S**2>     :     %.6f" % spin)
    lines.append("FINAL SINGLE POINT ENERGY      %.12f" % energy)
    if terminated:
        lines.append("           ****ORCA TERMINATED NORMALLY****")
    return "\n".join(lines) + "\n"


def _payload(name, state, energy, charge, multiplicity, status="ok"):
    return {
        "mol_id": "%s_%s" % (name, state),
        "charge": charge,
        "multiplicity": multiplicity,
        "job": "sp",
        "status": status,
        "result": {
            "final_energy_eh": energy,
            "scf_converged": True,
            "n_scf_cycles": 10,
            "normal_termination": True,
            "version": "6.1.1",
            "qc_flags": [],
        },
        "qc_flags": [],
        "raw_output": "%s_%s.out" % (name, state),
        "provenance": {},
    }


def _make(
    tmp_path: Path,
    name: str,
    state: str,
    *,
    energy_json: float,
    energy_out: "float | None" = None,
    charge: int = 0,
    multiplicity: int = 1,
    spin: "float | None" = None,
    scf: bool = True,
    terminated: bool = True,
    status: str = "ok",
    write_out: bool = True,
) -> Path:
    orca_dir = tmp_path / "orca"
    orca_dir.mkdir(parents=True, exist_ok=True)
    json_path = orca_dir / ("%s_%s_orca.json" % (name, state))
    json_path.write_text(
        json.dumps(_payload(name, state, energy_json, charge, multiplicity, status)),
        encoding="utf-8",
        newline="\n",
    )
    if write_out:
        out_path = orca_dir / ("%s_%s.out" % (name, state))
        out_path.write_text(
            _out_text(
                energy_json if energy_out is None else energy_out,
                scf=scf,
                spin=spin,
                terminated=terminated,
            ),
            encoding="utf-8",
            newline="\n",
        )
    return json_path


# ---------------------------------------------------------------------------
# 1. consistent record
# ---------------------------------------------------------------------------
def test_consistent_record_has_no_flags(tmp_path: Path) -> None:
    json_path = _make(tmp_path, "EC", "neutral", energy_json=-100.0)
    record = build_record(json_path)
    assert record["name"] == "EC"
    assert record["state"] == "neutral"
    assert record["mol_id"] == "EC_neutral"
    assert record["energy_eh_out"] == pytest.approx(-100.0)
    assert record["energy_eh_json"] == pytest.approx(-100.0)
    assert record["scf_converged"] is True
    assert record["terminated_normally"] is True
    assert record["spin_s2"] is None
    assert not record["qc_flags"]


# ---------------------------------------------------------------------------
# 2. energy mismatch
# ---------------------------------------------------------------------------
def test_energy_mismatch_is_flagged(tmp_path: Path) -> None:
    json_path = _make(tmp_path, "EC", "neutral", energy_json=-100.0, energy_out=-101.0)
    record = build_record(json_path)
    assert "energy_mismatch" in record["qc_flags"]
    assert record["delta_eh"] == pytest.approx(-1.0)


def test_energy_within_tolerance_is_not_flagged(tmp_path: Path) -> None:
    json_path = _make(
        tmp_path, "EC", "neutral", energy_json=-100.0, energy_out=-100.0000004
    )
    record = build_record(json_path)
    assert "energy_mismatch" not in record["qc_flags"]


# ---------------------------------------------------------------------------
# 3. missing .out
# ---------------------------------------------------------------------------
def test_missing_out_is_flagged(tmp_path: Path) -> None:
    json_path = _make(tmp_path, "EC", "cation", energy_json=-99.5, write_out=False)
    record = build_record(json_path)
    assert "missing_output" in record["qc_flags"]
    assert record["energy_eh_out"] is None
    assert record["scf_converged"] is None


# ---------------------------------------------------------------------------
# 4. spin contamination
# ---------------------------------------------------------------------------
def test_spin_contamination_is_flagged(tmp_path: Path) -> None:
    json_path = _make(
        tmp_path,
        "EC",
        "anion",
        energy_json=-99.0,
        charge=-1,
        multiplicity=2,
        spin=0.900000,
    )
    record = build_record(json_path)
    assert "spin_contamination_flag" in record["qc_flags"]


def test_spin_at_doublet_is_not_flagged(tmp_path: Path) -> None:
    json_path = _make(
        tmp_path,
        "EC",
        "anion",
        energy_json=-99.0,
        charge=-1,
        multiplicity=2,
        spin=0.754910,
    )
    record = build_record(json_path)
    assert "spin_contamination_flag" not in record["qc_flags"]


def test_closed_shell_without_spin_block_is_not_flagged(tmp_path: Path) -> None:
    json_path = _make(tmp_path, "EC", "neutral", energy_json=-99.0, spin=None)
    record = build_record(json_path)
    assert record["spin_s2"] is None
    assert not record["qc_flags"]


# ---------------------------------------------------------------------------
# 5. unbound anion (molecule-level)
# ---------------------------------------------------------------------------
def test_unbound_anion_is_flagged_at_molecule_level(tmp_path: Path) -> None:
    neutral_path = _make(tmp_path, "SN", "neutral", energy_json=-200.0)
    anion_path = _make(
        tmp_path, "SN", "anion", energy_json=-199.0, charge=-1, multiplicity=2
    )
    records = [build_record(neutral_path), build_record(anion_path)]
    apply_unbound_anion(records)
    by_state = {record["state"]: record for record in records}
    assert "unbound_anion" in by_state["anion"]["qc_flags"]
    assert "unbound_anion" not in by_state["neutral"]["qc_flags"]


def test_bound_anion_is_not_flagged(tmp_path: Path) -> None:
    neutral_path = _make(tmp_path, "SN", "neutral", energy_json=-200.0)
    anion_path = _make(
        tmp_path, "SN", "anion", energy_json=-201.0, charge=-1, multiplicity=2
    )
    records = [build_record(neutral_path), build_record(anion_path)]
    apply_unbound_anion(records)
    assert all("unbound_anion" not in record["qc_flags"] for record in records)


# ---------------------------------------------------------------------------
# 6. empty directory is not an error
# ---------------------------------------------------------------------------
def test_empty_orca_dir_returns_zero(tmp_path: Path) -> None:
    outdir = tmp_path / "week4"
    orca_dir = tmp_path / "nothing_here"
    rc = main(["--outdir", str(outdir), "--orca-dir", str(orca_dir)])
    assert rc == 0

    csv_path = outdir / "p1_core_set_audit.csv"
    json_path = outdir / "p1_core_set_audit.json"
    md_path = outdir / "p1_core_set_audit.md"
    assert csv_path.exists()
    assert json_path.exists()
    assert md_path.exists()

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines == [",".join(CSV_COLUMNS)]

    summary = json.loads(json_path.read_text(encoding="utf-8"))
    assert summary["n_records"] == 0
    assert summary["n_molecules"] == 0
    assert summary["n_complete_molecules"] == 0
    assert summary["n_ok"] == 0
    assert summary["molecules"] == {}
    assert "尚无 T1 产物" in md_path.read_text(encoding="utf-8")


def test_existing_but_empty_orca_dir_returns_zero(tmp_path: Path) -> None:
    outdir = tmp_path / "week4"
    orca_dir = tmp_path / "week4" / "orca"
    orca_dir.mkdir(parents=True, exist_ok=True)
    rc = main(["--outdir", str(outdir), "--orca-dir", str(orca_dir)])
    assert rc == 0
    assert (outdir / "p1_core_set_audit.csv").exists()


# ---------------------------------------------------------------------------
# 7. end-to-end through main()
# ---------------------------------------------------------------------------
def test_main_end_to_end(tmp_path: Path) -> None:
    outdir = tmp_path / "week4"
    _make(outdir, "EC", "neutral", energy_json=-100.0)
    _make(
        outdir,
        "EC",
        "cation",
        energy_json=-99.5,
        charge=1,
        multiplicity=2,
        spin=0.754910,
    )
    _make(
        outdir,
        "EC",
        "anion",
        energy_json=-100.5,
        charge=-1,
        multiplicity=2,
        spin=0.755100,
    )

    rc = main(["--outdir", str(outdir)])
    assert rc == 0

    summary = json.loads((outdir / "p1_core_set_audit.json").read_text(encoding="utf-8"))
    assert summary["n_records"] == 3
    assert summary["n_molecules"] == 1
    assert summary["n_complete_molecules"] == 1
    assert summary["n_ok"] == 3
    assert summary["molecules"]["EC"]["states_present"] == [
        "neutral",
        "cation",
        "anion",
    ]
    assert summary["flag_counts"]["energy_mismatch"] == 0

    rows = list(
        csv.DictReader(
            (outdir / "p1_core_set_audit.csv").read_text(encoding="utf-8").splitlines()
        )
    )
    assert [row["state"] for row in rows] == ["neutral", "cation", "anion"]
    assert all(row["qc_flags"] == "" for row in rows)

    md = (outdir / "p1_core_set_audit.md").read_text(encoding="utf-8")
    assert "## 结论" in md
    assert "阴离子" in md


def test_unreadable_json_does_not_crash(tmp_path: Path) -> None:
    outdir = tmp_path / "week4"
    orca_dir = outdir / "orca"
    orca_dir.mkdir(parents=True, exist_ok=True)
    (orca_dir / "EC_neutral_orca.json").write_text("{ not valid json", encoding="utf-8")
    rc = main(["--outdir", str(outdir)])
    assert rc == 0
    rows = list(
        csv.DictReader(
            (outdir / "p1_core_set_audit.csv").read_text(encoding="utf-8").splitlines()
        )
    )
    assert len(rows) == 1
    assert rows[0]["json_status"] == "unreadable"
    assert "energy_mismatch" in rows[0]["qc_flags"]
