"""契约测试：WP2 6.3 态身份 QC 必须从原始日志现算，不能写死。

台账里每一个已产出态都要能对回一份带 sha256 的原始 ORCA 日志，且全体原子的电荷/自旋求和要
等于登记的总量（不是靠 fragment=总量-Li 这种定义凑出来的恒等式）。另外钉住两类早先出过错的
语义：Mayer 键级列里不能混进 Angstrom 键长；不含 Li 的母态不能冒充 intact。
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QC = REPO_ROOT / "outputs" / "physics_completion" / "state_identity" / "state_identity_qc.csv"
LEDGER = REPO_ROOT / "outputs" / "physics_completion" / "free_states" / "production_ledger.csv"
IDENTITY_CLASSES = {"intact", "Li_centered", "mixed", "ambiguous", "fragmented", "no_li"}


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_produced_state_has_exactly_one_identity_row() -> None:
    produced = [r["record_id"] for r in _rows(LEDGER) if r.get("status") == "computed"]
    rows = _rows(QC)
    assert produced, "production ledger has no computed state"
    assert sorted(r["record_id"] for r in rows) == sorted(produced), "6.3 coverage drifted from the ledger"
    assert all(r["identity_class"] in IDENTITY_CLASSES for r in rows), "identity vocabulary drift"


def test_parsed_rows_hash_a_real_raw_log() -> None:
    """行里登记的 sha256 必须等于磁盘上那份原始日志的 sha256（证明是读出来的，不是写死的）。"""
    parsed = [r for r in _rows(QC) if r["status"] == "computed"]
    assert parsed, "no state could be parsed from the raw logs"
    for row in parsed:
        path = REPO_ROOT / row["raw_log_path"]
        assert path.is_file(), "raw log missing: %s" % row["raw_log_path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == row["raw_log_sha256"], row["record_id"]


def test_whole_atom_sums_and_li_quantities_are_physical() -> None:
    """全体原子求和是真检查；Mayer 列只能放键级；无 Li 的态必须是 no_li。"""
    for row in _rows(QC):
        if row["status"] != "computed":
            continue
        for key in ("charge_sum_mulliken", "charge_sum_loewdin"):
            if row[key]:
                assert abs(float(row[key]) - float(row["charge"])) < 1e-3, row["record_id"]
        if row["spin_sum_mulliken"]:
            two_s = float(row["multiplicity"]) - 1.0
            assert abs(float(row["spin_sum_mulliken"]) - two_s) < 1e-3, row["record_id"]
        if row["li_index"]:
            assert row["li_bond_valence_total"], row["record_id"]
            for item in (row["li_donor_mayer_bonds"].split(";") if row["li_donor_mayer_bonds"] else []):
                assert float(item.split(":")[1]) <= 1.0, "a distance leaked into the Mayer column: " + row["record_id"]
            if row["li_donor_min_contact_ang"]:
                assert 0.5 <= float(row["li_donor_min_contact_ang"]) <= 4.0, row["record_id"]
        else:
            assert row["identity_class"] == "no_li", row["record_id"]
        assert row["frontier_localization_status"] == "not_computed", row["record_id"]
