"""Step 3 acceptance: a NEW member must be recognised by the CONSUMERS.

The user's requirement: "新 campaign/member/attempt 必须被候选注册、导入器、
去重器、覆盖复核、成本和下游消费者完整识别。不依赖目录前缀猜测成员角色。
合成端到端测试先通过，再生成与提交实际任务。"

The identity/role half is pinned by ``test_recovery_identity_wiring.py``.  This
file drives the REAL downstream code over a synthetic member injected into a
temporary copy of the ledger, and pins the strongest scientific guarantee the
project has: **a duplicate minimum adds coverage evidence, never degeneracy.**

Method: the module's input/output path constants point at a tmp copy, while
``REPO`` stays the real checkout so ``member_geometry`` can resolve the real
``run/job.xyz`` files.  That means the aggregator runs its genuine topology +
Kabsch-RMSD + torsion dedup, not a stub.
"""
import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
AGG = REPO / "scripts" / "wp_production" / "build_production_ensemble_aggregator.py"
COST = REPO / "scripts" / "wp_production" / "build_ensemble_cost_by_family.py"
ENS = REPO / "outputs" / "physics_completion" / "ensembles"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def agg():
    return _load("agg", AGG)


def _rows(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def _write(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


@pytest.fixture
def staged(agg, tmp_path, monkeypatch):
    """A tmp ledger copy the aggregator reads/writes; REPO stays real."""
    work = tmp_path / "ens"
    work.mkdir()
    for name in ("production_ensemble_structures.csv",
                 "production_ensemble_candidates.csv",
                 "production_ensemble_dispositions.csv"):
        shutil.copy2(ENS / name, work / name)
    monkeypatch.setattr(agg, "STRUCTURES", work / "production_ensemble_structures.csv")
    monkeypatch.setattr(agg, "CANDIDATES", work / "production_ensemble_candidates.csv")
    monkeypatch.setattr(agg, "DISPOSITIONS", work / "production_ensemble_dispositions.csv")
    monkeypatch.setattr(agg, "OUT", work)
    return work


def _donor_and_fields(agg):
    """A real COMPUTED extra member: geometry exists, so dedup is exercised."""
    structures = _rows(agg.STRUCTURES)
    for r in structures:
        if (r.get("member_role") in ("round1_extra", "recovery_v1_start")
                and r.get("status") == "computed"
                and (REPO / r["task_relpath"] / "run" / "job.xyz").is_file()):
            return r, list(structures[0].keys())
    pytest.skip("no computed extra with resolvable geometry in this checkout")


def _inject(agg, work, donor, fields, *, seed, keep_geometry_hash):
    """Register + stage one synthetic member that reuses the donor's geometry."""
    structures = _rows(agg.STRUCTURES)
    synth = dict(donor)
    synth.update({
        "member_key": "%s|%s|%s" % (donor["name"], donor["slot"], seed),
        "seed": seed,
        "member_role": "recovery_v1_start",   # declared, first-class member
        "attempt": "0",
        "status": "computed",
        "final_geometry_sha256": (donor["final_geometry_sha256"] if keep_geometry_hash
                                  else "0" * 64),
    })
    _write(agg.STRUCTURES, fields, structures + [synth])

    cands = _rows(ENS / "production_ensemble_candidates.csv")
    cfields = list(cands[0].keys())
    cands.append({"slot": donor["slot"], "mol_id": donor["mol_id"],
                  "name": donor["name"], "member_role": "recovery_v1_start",
                  "seed": seed, "source_kind": "synthetic_campaign",
                  "geometry": "", "sha256": donor.get("final_geometry_sha256", ""),
                  "rel_kcal": "0", "denticity": "", "duplicate_of": "",
                  "probe_class": "synthetic_test", "charge": donor["charge"],
                  "multiplicity": donor["multiplicity"], "status": "planned",
                  "note": "synthetic end-to-end wiring test"})
    _write(work / "production_ensemble_candidates.csv", cfields, cands)
    return synth["member_key"]


def test_duplicate_member_cannot_inflate_the_ensemble(agg, staged):
    """Same geometry -> recognised as a duplicate, labels unchanged."""
    donor, fields = _donor_and_fields(agg)
    key = _inject(agg, staged, donor, fields, seed="synth_dup1",
                  keep_geometry_hash=True)
    assert agg.main([]) == 0, "the aggregator rejected the synthetic member"

    dedup = {r["member_key"] + "|" + r["attempt"]: r
             for r in _rows(staged / "production_ensemble_dedup.csv")}
    assert any(k.startswith(key + "|") for k in dedup), \
        "the new member never reached the dedup table"

    # exactly one of the pair is kept; the other names it (identical geometry)
    pair = [v for k, v in dedup.items()
            if k.startswith(key + "|") or k.startswith(donor["member_key"] + "|")]
    kept = [r for r in pair if r["kept"] == "true"]
    assert len(kept) == 1, kept
    dropped = [r for r in pair if r["kept"] == "false"]
    # `duplicate_of` carries the bare member_key of the kept representative
    assert dropped, pair
    assert dropped[0]["duplicate_of"] == kept[0]["member_key"], dropped[0]

    # the strongest guarantee: n_unique / acceptance cannot move
    new = {(r["name"], r["state"]): r
           for r in _rows(staged / "production_ensemble_labels.csv")}
    real = {(r["name"], r["state"]): r
            for r in _rows(ENS / "production_ensemble_labels.csv")}
    assert set(new) == set(real)
    for k in real:
        assert new[k]["n_unique"] == real[k]["n_unique"], k
        assert new[k]["acceptance_status"] == real[k]["acceptance_status"], k

    # a duplicate must not enter the Boltzmann pool
    weights = {r["member_key"] for r in _rows(staged / "production_ensemble_weights.csv")}
    assert key not in weights


def test_unverifiable_geometry_is_blocked_not_unique(agg, staged):
    """A hash that does not match the bytes on disk is dedup_blocked (fail-closed)."""
    donor, fields = _donor_and_fields(agg)
    key = _inject(agg, staged, donor, fields, seed="synth_badhash",
                  keep_geometry_hash=False)
    assert agg.main([]) == 0

    rows = {r["member_key"] + "|" + r["attempt"]: r
            for r in _rows(staged / "production_ensemble_dedup.csv")}
    mine = [r for k, r in rows.items() if k.startswith(key + "|")]
    assert mine, "the synthetic member never reached the dedup table"
    assert mine[0]["kept"] == "false"
    assert "dedup_blocked" in mine[0]["reason"]

    new = {(r["name"], r["state"]): r
           for r in _rows(staged / "production_ensemble_labels.csv")}
    real = {(r["name"], r["state"]): r
            for r in _rows(ENS / "production_ensemble_labels.csv")}
    for k in real:
        assert new[k]["n_unique"] == real[k]["n_unique"], k


def test_new_campaign_package_is_seen_by_the_cost_family_ledger(tmp_path, monkeypatch):
    """触发/成本层也必须由清单与快照发现新族，而不是靠名字白名单。"""
    cost = _load("cost", COST)
    pkg = tmp_path / "work" / "hpc_synthetic_campaign_2099"
    snap = pkg / "tasks" / "DMC" / "M_plus__s9" / "snapshots" / "424242_0"
    snap.mkdir(parents=True)
    (snap / "started.utc").write_text("2026-10-23T00:00:00Z\n", encoding="utf-8")
    (snap / "normal_termination.utc").write_text("2026-10-23T01:00:00Z\n",
                                                 encoding="utf-8")
    monkeypatch.setattr(cost, "REPO", tmp_path)
    rows = cost.build_rows()
    assert rows, "the synthetic campaign was not discovered at all"
    mine = [r for r in rows if r["package"] == "hpc_synthetic_campaign_2099"]
    assert len(mine) == 1, mine
    assert mine[0]["job_identity"].startswith("hpc_synthetic_campaign_2099|")
    # one hour on the frozen 4 cores
    assert float(mine[0]["core_hours"]) == pytest.approx(4.0)


def test_cost_family_keeps_a_failure_instead_of_dropping_it(tmp_path, monkeypatch):
    """A started-but-unterminated attempt is a DECLARED unknown, never dropped."""
    cost = _load("cost", COST)
    pkg = tmp_path / "work" / "hpc_synthetic_campaign_fail"
    snap = pkg / "tasks" / "DMC" / "M_plus__s1" / "snapshots" / "5_0"
    snap.mkdir(parents=True)
    (snap / "started.utc").write_text("2026-10-23T00:00:00Z\n", encoding="utf-8")
    monkeypatch.setattr(cost, "REPO", tmp_path)
    rows = cost.build_rows()
    mine = [r for r in rows if r["package"] == "hpc_synthetic_campaign_fail"]
    assert len(mine) == 1, "an unterminated attempt must stay in the ledger"
    # measured behaviour: no terminal marker -> cost is UNKNOWN, never zero
    assert mine[0]["terminal"] == "no"
    assert mine[0]["core_hours"] == ""
    assert mine[0]["accounting"] == "in_flight_cost_unknown"