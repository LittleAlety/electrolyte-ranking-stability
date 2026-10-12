"""Targeted WP2 state restart: snapshot, strict args, and real-run provenance.

These tests exercise the actual ``main`` -> ``run_state`` path (with a stubbed
ORCA process, never a real ORCA run), not just isolated helpers: the snapshot,
the SHA-256 bookkeeping and the machine-readable provenance record are checked
against the bytes that land on disk inside the leg directory.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "run_wp2_production.py"

FAKE_ORCA_LOG = """\
Program Version 6.1.1
VIBRATIONAL FREQUENCIES
-----------------------
   0:       0.00 cm**-1
   6:     123.45 cm**-1
NORMAL MODES
------------
Electronic energy                ...     -10.00000000 Eh
Zero point energy                ...       0.01000000 Eh
Total Enthalpy                   ...      -9.90000000 Eh
Total entropy correction         ...      -0.00100000 Eh
G-E(el)                          ...       0.02000000 Eh
Final Gibbs free energy          ...      -9.98000000 Eh
Quasi RRHO                       ...      True
Temperature                      ...     298.15 K
Pressure                         ...       1.00 atm
Cut-Off Frequency                ...       1.00 cm
THE OPTIMIZATION HAS CONVERGED
ORCA TERMINATED NORMALLY
"""


def _load():
    script_dir = str(SCRIPT.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("wp2_targeted_restart_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stub_orca(monkeypatch, module, calls):
    def fake_capture_run(argv, directory, log_path):
        calls.append({"argv": list(argv), "directory": Path(directory), "log": Path(log_path)})
        produced = Path(directory) / (Path(argv[1]).stem + ".xyz")
        produced.write_text("1\noptimised\nH 0 0 0\n", encoding="utf-8")
        return 0, FAKE_ORCA_LOG, 12.5

    monkeypatch.setattr(module.rb, "capture_run", fake_capture_run)


def test_restart_run_snapshots_source_and_records_provenance(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "OUT", tmp_path)
    monkeypatch.setitem(module.rb.MOL_LOOKUP, "C13", ("unused", "GBL"))
    restart = tmp_path / "GBL" / "M" / "GBL_M_opt.xyz"
    restart.parent.mkdir(parents=True)
    source_bytes = b"3\nrestart source\nC 0.0 0.0 0.0\nH 1.0 0.0 0.0\nH 0.0 1.0 0.0\n"
    restart.write_bytes(source_bytes)
    calls = []
    _stub_orca(monkeypatch, module, calls)

    assert module.main(["C13", "--state", "M", "--restart-from-opt", "--force"]) == 0
    assert len(calls) == 1

    leg = tmp_path / "GBL" / "M"
    snapshot = leg / "GBL_M_restart_source.xyz"
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    # 1. immutable snapshot keeps the exact source bytes and a matching SHA-256
    assert snapshot.read_bytes() == source_bytes
    assert (leg / "geom.xyz").read_bytes() == snapshot.read_bytes()

    provenance = json.loads((leg / "GBL_M_restart_provenance.json").read_text(encoding="utf-8"))
    assert provenance["restart_source"].endswith("GBL_M_opt.xyz")
    # the recorded source hash is the pre-run hash of the restart source
    assert provenance["restart_source_sha256"] == source_sha
    assert provenance["snapshot_sha256"] == source_sha
    assert provenance["snapshot_bytes"] == len(source_bytes)
    # --restart-from-opt reads the leg's own ``*_opt.xyz`` output slot, so the new
    # run replaces it; the immutable snapshot is what preserves the pre-run geometry.
    assert provenance["restart_source_replaced_by_run"] is True
    assert provenance["restart_source_sha256_after_run"] != source_sha
    assert provenance["snapshot_path"].endswith("GBL_M_restart_source.xyz")
    assert provenance["restart_kind"] == "restart_from_opt"
    assert provenance["invocation_intent"]["restart_from_opt"] is True
    assert provenance["invocation_intent"]["force"] is True
    assert provenance["invocation_intent"]["state"] == "M"
    assert provenance["invocation_intent"]["molecules"] == ["C13"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", provenance["utc_timestamp"])
    assert "immutable copy" in provenance["source_output_relationship"]
    assert provenance["result"]["status"] == "computed"
    assert provenance["result"]["imaginary_modes"] == "0"

    # 2. the ledger row points back at the restart evidence
    row = json.loads((leg / "GBL_M.json").read_text(encoding="utf-8"))
    assert row["status"] == "computed" and row["g_single_eh"] == "-9.98000000"
    assert row["restart_source_sha256"] == source_sha
    assert row["restart_provenance"].endswith("GBL_M_restart_provenance.json")
    assert row["geometry_start"].endswith("GBL_M_restart_source.xyz")


def test_restart_refuses_to_overwrite_a_different_snapshot(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "OUT", tmp_path)
    monkeypatch.setitem(module.rb.MOL_LOOKUP, "C13", ("unused", "GBL"))
    restart = tmp_path / "GBL" / "M" / "GBL_M_opt.xyz"
    restart.parent.mkdir(parents=True)
    restart.write_bytes(b"2\nfirst\nH 0 0 0\nH 1 0 0\n")
    _stub_orca(monkeypatch, module, [])
    assert module.main(["C13", "--state", "M", "--restart-from-opt", "--force"]) == 0
    restart.write_bytes(b"2\nchanged\nH 0 0 0\nH 2 0 0\n")
    with pytest.raises(SystemExit) as exc:
        module.main(["C13", "--state", "M", "--restart-from-opt", "--force"])
    assert "immutable restart snapshot" in str(exc.value)


def test_non_restart_run_does_not_fabricate_restart_evidence(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "OUT", tmp_path)
    monkeypatch.setitem(module.rb.MOL_LOOKUP, "C01", ("unused", "DMC"))
    _stub_orca(monkeypatch, module, [])
    assert module.main(["C01", "--state", "M"]) == 0
    leg = tmp_path / "DMC" / "M"
    assert not (leg / "DMC_M_restart_source.xyz").exists()
    assert not (leg / "DMC_M_restart_provenance.json").exists()
    row = json.loads((leg / "DMC_M.json").read_text(encoding="utf-8"))
    assert "restart_provenance" not in row


@pytest.mark.parametrize("argv, fragment", [
    (["C13", "--state", "M", "--restart-from-opt"], "requires --force"),
    (["C13", "--restart-from-opt", "--force"], "exactly one explicit --state"),
    (["C13", "--state", "M", "--state", "M_plus", "--restart-from-opt", "--force"],
     "exactly one explicit --state"),
    (["C13", "C14", "--state", "M", "--restart-from-opt", "--force"],
     "exactly one molecule"),
    (["C13", "--state", "not-a-state"], "invalid choice"),
    (["C99", "--state", "M"], "unknown molecule id"),
    (["C13", "--nonsense"], "unrecognized arguments"),
    (["C13", "--state"], "expected one argument"),
])
def test_strict_argument_validation_rejects_bad_invocations(argv, fragment, capsys):
    module = _load()
    with pytest.raises(SystemExit) as exc:
        module.main(argv)
    assert exc.value.code == 2
    assert fragment in capsys.readouterr().err
