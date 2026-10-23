"""G0: the formal ``model_v2`` run must not overwrite the ``knn_v1`` control.

Measured gap (independent review, 2026-10-22): ``--acq-version model_v2`` still
wrote to the fixed ``blind_replay/`` paths, so running the new formal version
would silently replace the control products it must be compared against.

The contract these tests pin:

* ``knn_v1`` (the default) resolves to the HISTORICAL directory and filenames,
  so the committed control products stay byte-identical;
* any other version resolves to its own sibling directory;
* an unknown version is refused (never silently treated as the default);
* the committed index states which directory produced it and whether that
  directory is the control one.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BLIND = (REPO / "outputs" / "physics_completion" / "active_learning"
         / "blind_replay")


def _load():
    spec = importlib.util.spec_from_file_location(
        "ab", REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "scripts" / "wp_production"))
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def replay():
    return _load()


def test_default_version_keeps_the_historical_paths(replay):
    """The control's location must not move: it is what the chain checks."""
    paths = replay.output_paths()
    assert paths["candidates"] == replay.OUT_CAND
    assert paths["summary"] == replay.OUT_SUM
    assert paths["endpoints"] == replay.OUT_END
    assert paths["index"] == replay.OUT_INDEX
    assert paths["dir"] == BLIND


def test_model_v2_gets_its_own_directory(replay):
    control = replay.output_paths("knn_v1")
    new = replay.output_paths("model_v2")
    assert new["dir"] != control["dir"]
    assert control["dir"] not in new["dir"].parents
    assert new["dir"].name == "blind_replay_model_v2"
    for key in ("candidates", "summary", "endpoints", "index"):
        assert new[key].parent == new["dir"]


def test_unknown_version_is_refused(replay):
    with pytest.raises(ValueError):
        replay.output_paths("model_v3")


def test_committed_index_declares_its_directory_and_version(replay):
    index = json.loads((BLIND / "AB_index.json").read_text(encoding="utf-8"))
    out = index["outputs"]
    # the index stores a platform-native relative path (like its `inputs` block),
    # so compare normalised parts rather than raw separators
    declared = Path(out["directory"])
    expected = Path("outputs/physics_completion/active_learning/blind_replay")
    assert declared.parts == expected.parts, declared
    assert out["is_control_directory"] is True
    assert out["acquisition_version"] == "knn_v1"
    assert index["contract"]["acquisition_version_in_this_run"] == "knn_v1"


def test_source_does_not_write_the_control_path_unconditionally():
    """A regression guard: the writer must resolve paths per version."""
    src = (REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py"
           ).read_text(encoding="utf-8")
    assert "def output_paths(" in src
    assert 'paths = output_paths(acq_version)' in src
    assert "_write_csv(OUT_CAND, data[" not in src