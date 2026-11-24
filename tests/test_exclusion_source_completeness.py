"""Plan batch 1 / action item 4: the probe-exclusion set qualifies by SOURCE
COMPLETENESS -- every manifest found by the glob must be read and parsed, with
recorded provenance -- not by "a non-zero number of files exists".

Before the fix, a corrupt or unreadable manifest was silently skipped
(``except (OSError, ValueError): continue``): the guard saw at least one file
and passed while dropping that source's refusals, i.e. exactly the
"数量非零而非来源完整" defect.  These tests pin:

* missing layer              -> REFUSING (wording kept: "REFUSING"/"re-admit");
* one corrupt manifest       -> REFUSING (new; was a silent skip);
* manifest path is a dir     -> REFUSING (new; unreadable source);
* non-object JSON manifest   -> REFUSING (new);
* all sources valid, zero    -> empty set ACCEPTED (no non-zero requirement)
  with provenance recorded for every source read;
* extraction of refused / cancelled keys unchanged.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PROD / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _write_manifest(repo: Path, dirname: str, payload) -> Path:
    work = repo / "work" / dirname
    work.mkdir(parents=True, exist_ok=True)
    p = work / "manifest.json"
    if isinstance(payload, (dict, list)):
        p.write_text(json.dumps(payload), encoding="utf-8")
    else:
        p.write_bytes(payload)          # corrupt fixtures arrive as raw bytes
    return p


def test_missing_layer_still_refuses(tmp_path):
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    with pytest.raises(SystemExit) as exc:
        m._rejected_probe_members()
    assert "REFUSING" in str(exc.value)
    assert "re-admit" in str(exc.value)


def test_a_corrupt_manifest_refuses_instead_of_being_skipped(tmp_path):
    """The core new guard: previously this silently continued."""
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    _write_manifest(tmp_path, "hpc_torsion_probe_v1_good",
                    {"rejected": [{"member_key": "EC|LiM_2plus|tors_x"}]})
    bad = _write_manifest(tmp_path, "hpc_torsion_probe_v2_bad",
                          b'{"rejected": [TRUNCATED')
    with pytest.raises(SystemExit) as exc:
        m._rejected_probe_members()
    msg = str(exc.value)
    assert "REFUSING" in msg
    assert "not parseable JSON" in msg
    assert bad.name in msg or str(bad) in msg


def test_an_unreadable_manifest_refuses(tmp_path):
    """manifest.json as a DIRECTORY: read_bytes raises OSError -> refuse."""
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    blocked = tmp_path / "work" / "hpc_torsion_probe_v3_blocked"
    blocked.mkdir(parents=True)
    (blocked / "manifest.json").mkdir()          # unreadable path
    _write_manifest(tmp_path, "hpc_torsion_probe_v1_good", {"rejected": []})
    with pytest.raises(SystemExit) as exc:
        m._rejected_probe_members()
    assert "REFUSING" in str(exc.value)
    assert "cannot read" in str(exc.value)


def test_a_non_object_manifest_refuses(tmp_path):
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    _write_manifest(tmp_path, "hpc_torsion_probe_v4_list", ["not", "a", "dict"])
    with pytest.raises(SystemExit) as exc:
        m._rejected_probe_members()
    assert "not a manifest object" in str(exc.value)


def test_complete_sources_with_no_refusals_yield_an_empty_set(tmp_path):
    """'No refusals recorded' is a fact when the read was complete: an EMPTY
    set is accepted; no non-zero count is demanded anywhere."""
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    p = _write_manifest(tmp_path, "hpc_torsion_probe_v1_clean",
                        {"rejected": [], "replaces_cancelled_job": None})
    got = m._rejected_probe_members()
    assert got == set()
    prov = m.EXCLUSION_SOURCE_PROVENANCE
    assert len(prov) == 1, prov
    raw = p.read_bytes()
    assert prov[0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert prov[0]["bytes"] == len(raw)
    assert prov[0]["path"].endswith("manifest.json")


def test_provenance_records_every_source_in_glob_order(tmp_path):
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    _write_manifest(tmp_path, "hpc_torsion_probe_v1_a",
                    {"rejected": [{"member_key": "A|B|tors_1"}]})
    _write_manifest(tmp_path, "hpc_torsion_probe_v2_b",
                    {"rejected": [{"member_key": "C|D|tors_2"}]})
    got = m._rejected_probe_members()
    assert got == {"A|B|tors_1", "C|D|tors_2"}
    prov = m.EXCLUSION_SOURCE_PROVENANCE
    assert len(prov) == 2, prov
    assert [e["path"] for e in prov] == sorted(e["path"] for e in prov)
    for entry in prov:
        raw = (tmp_path / entry["path"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
        assert entry["bytes"] == len(raw)


def test_extraction_of_refused_and_cancelled_keys_is_unchanged(tmp_path):
    m = _load("build_coverage_reviews")
    m.REPO = tmp_path
    _write_manifest(tmp_path, "hpc_torsion_probe_v1_batch", {
        "rejected": [{"member_key": "EC|LiM_2plus|tors_1", "reason": "central C=O"}],
        "replaces_cancelled_job": 3747724,
        "requested_tasks": ["tasks/DMC/LiM_2plus__tors_7_0_1_2"],
    })
    got = m._rejected_probe_members()
    assert "EC|LiM_2plus|tors_1" in got
    assert "DMC|LiM_2plus|tors_7_0_1_2" in got


def test_the_real_layer_still_reads_when_present():
    if not (REPO / "work" / "wp2prod").is_dir():
        pytest.skip("machine-local work/ layer absent in this checkout")
    m = _load("build_coverage_reviews")
    got = m._rejected_probe_members()
    assert "DMC|LiM_2plus|tors_7_0_1_2" in got, got
    prov = m.EXCLUSION_SOURCE_PROVENANCE
    assert prov, "a successful read must record its sources"
    for entry in prov:
        raw = (REPO / entry["path"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
