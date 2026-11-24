"""Actual isolated entry: raw Opt qualification precedes the production deduper."""
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/wp_production/rebuild_strict_isolated.py"


def _load():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("strict_isolated_entry", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log(with_energy):
    rows = [
        "          ----------------------|Geometry convergence|-------------------------",
        "          Item                value                   Tolerance       Converged",
    ]
    if with_energy:
        rows.append("          Energy change       0.0000001000            0.0000002000      YES")
    rows.extend((
        "          RMS gradient        0.0000040000            0.0000080000      YES",
        "          MAX gradient        0.0000200000            0.0000300000      YES",
        "          RMS step            0.0000500000            0.0001000000      YES",
        "          MAX step            0.0001000000            0.0002000000      YES",
    ))
    return "\n".join(rows) + "\n"


def test_entry_promotes_qualified_old_follower_after_head_fails_five_items(tmp_path, monkeypatch):
    replay = _load()
    monkeypatch.setattr(replay, "ROOT", tmp_path)
    monkeypatch.setattr(replay.agg, "member_geometry", lambda row, repo: (
        ["C", "O"], [(0.0, 0.0, 0.0), (1.2, 0.0, 0.0)]))

    def member(seed, energy, with_energy):
        folder = tmp_path / seed
        folder.mkdir()
        log = folder / "job.log"
        log.write_text(_log(with_energy), encoding="utf-8")
        (folder / "job.inp").write_text(
            "! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv\n",
            encoding="utf-8")
        return dict(member_key=f"AN|M_plus|{seed}", name="AN", slot="M_plus", seed=seed,
                    member_role="round1_extra", status="computed", attempt="1",
                    log_path=f"{seed}/job.log", log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
                    method="wB97X-D4 def2-TZVPD", protocol_version="1.3",
                    frequency_hessian="analytical_hessian", qrrho="true", temp_k="298.15",
                    imaginary_modes="0", connectivity_ok="true", candidate_species_ok="true",
                    candidate_bond_graph_ok="true", charge="1", multiplicity="2",
                    g_single_eh=str(energy))

    head = member("head", -100.001, False)
    follower = member("follower", -100.000, True)
    old_kept, old_decisions = replay.agg.dedup_members([head, follower], tmp_path)
    assert [m["member_key"] for m in old_kept] == [head["member_key"]]
    assert next(d for d in old_decisions if d["member_key"] == follower["member_key"])["duplicate_of"] == head["member_key"]

    audits = {m["member_key"]: replay.assess_member(m) for m in (head, follower)}
    assert not audits[head["member_key"]]["eligible"]
    assert "FIVE_ITEM_MISSING:energy_change_Eh" in audits[head["member_key"]]["reasons"]
    assert audits[follower["member_key"]]["eligible"]

    state = replay.rebuild_state("AN|M_plus", [head, follower], audits,
                                 {head["member_key"]}, None,
                                 {"acceptance_status": "accepted", "n_pending": "0", "n_unresolved": "0"})
    assert state["strict_kept"] == [follower["member_key"]]
    assert state["new_representatives_from_old_nonkept"] == [follower["member_key"]]
    assert state["weights"][0]["weight"] == pytest.approx(1.0)
