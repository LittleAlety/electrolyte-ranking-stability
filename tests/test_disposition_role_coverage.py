"""Every extra member role needs a disposition row, not just round1_extra.

The aggregator decides "is a remedy actually in flight?" from the dispositions
table.  A member with NO disposition row falls through to ``n_rescue`` --
"remedy in flight" -- even after its attempt budget is exhausted.  Reporting work
in flight when there is none is precisely the factual misstatement the D7 review
flagged, and it also leaves the state reading ``provisional`` (sampling still in
progress) instead of ``limited`` (bounded coverage).

``recovery_v1_start`` was missing from the disposition loop, so every recovery
leg looked like it still had a rescue queued.
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
STRUCTURES = ENS / "production_ensemble_structures.csv"
DISPOSITIONS = ENS / "production_ensemble_dispositions.csv"
IMP = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_source_builds_dispositions_from_every_extra_role():
    src = IMP.read_text(encoding="utf-8")
    assert "disposition_keys" in src
    assert "ROUND2_LEDGER_ROLE, 'recovery_v1_start'" in src or \
           'ROUND2_LEDGER_ROLE, "recovery_v1_start"' in src


def test_every_accounted_recovery_member_has_a_disposition():
    """A member with a real log must carry a disposition row."""
    struct = [r for r in _rows(STRUCTURES)
              if r.get("member_role") == "recovery_v1_start" and r.get("log_sha256")]
    if not struct:
        return
    dispositions = {r["member_key"] for r in _rows(DISPOSITIONS)}
    missing = sorted({r["member_key"] for r in struct} - dispositions)
    assert not missing, "recovery members without a disposition: %s" % missing


def test_exhausted_budget_reads_as_limited_not_provisional():
    """A state whose only remedy used up both attempts is bounded, not pending."""
    dispositions = {r["member_key"]: r for r in _rows(DISPOSITIONS)}
    labels = {(r["name"], r["state"]): r for r in _rows(
        ENS / "production_ensemble_labels.csv")}
    if not dispositions or not labels:
        return
    for key, d in dispositions.items():
        if d.get("disposition") != "rescue_budget_exhausted":
            continue
        try:
            calcs = int(d.get("attempted_calculations") or 0)
        except ValueError:
            continue
        if calcs < 2:
            continue
        name, slot, _seed = key.split("|")
        label = labels.get((name, slot))
        if label is None or label.get("acceptance_status") == "accepted":
            continue
        # a state whose ONLY exhausted member is this one must be bounded;
        # if another member still has work in flight, provisional is correct
        siblings = [k for k in dispositions
                    if k.startswith("%s|%s|" % (name, slot)) and k != key
                    and (dispositions[k].get("disposition")
                         not in ("rescue_budget_exhausted", "computed", "species_drift_unrecoverable"))]
        if siblings:
            continue
        assert label["acceptance_status"] == "limited", (
            "%s/%s has an exhausted budget but reads %s"
            % (name, slot, label["acceptance_status"]))
