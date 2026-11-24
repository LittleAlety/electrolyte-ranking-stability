import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("metadata_corrections", ROOT / "scripts/wp_production/source_metadata_corrections.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_correction_retains_legacy_value_and_c3_gate(tmp_path):
    path = tmp_path / "corrections.jsonl"
    path.write_text(json.dumps({"candidate": "3928500_0", "source_sha256": "a"*64,
                              "old_value": "old protocol (TightSCF)",
                              "new_value": "VeryTightSCF SlowConv", "correction_id": "fact-1"})+"\n")
    result = mod.effective_protocol("3928500_0", "old protocol (TightSCF)", "a"*64, path)
    assert result["original"] == "old protocol (TightSCF)"
    assert result["effective"] == "VeryTightSCF SlowConv"
    assert result["c3_i"] == "CLOSED_UNAPPROVED_EQUIVALENCE_RULE"
    with pytest.raises(ValueError, match="does not match"):
        mod.effective_protocol("3928500_0", "old protocol (TightSCF)", "b"*64, path)
