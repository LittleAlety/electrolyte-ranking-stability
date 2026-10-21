import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/wp_production'))
import build_plan_compliance as compliance


def test_same_status_duplicate_rejected():
    rows = [{'mol_id': 'C01', 'state': 'M', 'acceptance_status': 'accepted'}] * 2
    assert compliance.ensemble_key_errors(rows, {('C01', 'M')})


def test_blocked_is_not_a_duplicate():
    rows = [{'mol_id': 'C01', 'state': 'M', 'acceptance_status': 'blocked'}]
    assert not compliance.ensemble_key_errors(rows, {('C01', 'M')})


def test_wrong_or_missing_key_rejected():
    assert compliance.ensemble_key_errors([], {('C01', 'M')})
