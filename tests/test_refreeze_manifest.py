"""refreeze_manifest: the registry must be reproducible, and drift must be typed.

Pinned invariants:
* a re-frozen manifest verifies under the contract (``--check`` returns 0);
* an EOL-only difference is classified ``eol_recalibration``, NOT
  ``content_change`` -- bookkeeping must never be confused with science;
* a real content edit is classified ``content_change`` and lands in the
  record verbatim;
* ``--check`` writes nothing (a gate must not mutate the artifact it gates).
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "refreeze_manifest.py"


def _m():
    spec = importlib.util.spec_from_file_location("refreeze_manifest", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _manifest(tmp_path, rows):
    p = tmp_path / "SHA256SUMS"
    p.write_text("".join("%s  %s\n" % (d, n) for d, n in rows),
                 encoding="utf-8", newline="\n")
    return p


def _row(name, digest=None):
    """One (digest, path) pair; a wrong digest by default so drift is the case."""
    return [digest or ("0" * 64), name]


def test_eol_only_difference_is_recalibration_not_content(tmp_path, monkeypatch):
    m = _m()
    from provenance_hash import sha256_raw
    target = tmp_path / "geom.xyz"
    target.write_bytes(b"2\r\ncomment\r\nH 0 0 0\r\nH 1 0 0\r\n")
    man = _manifest(tmp_path, [(sha256_raw(target), "geom.xyz")])
    monkeypatch.setattr(m, "REPO", tmp_path)
    res = m.classify(man)
    assert res["changed"]["eol_recalibration"] == ["geom.xyz"]
    assert res["changed"]["content_change"] == []


def test_real_edit_is_content_change(tmp_path, monkeypatch):
    m = _m()
    target = tmp_path / "geom.xyz"
    target.write_bytes(b"3\nother content entirely\nH 0 0 0\n")
    man = _manifest(tmp_path, [_row("geom.xyz")])
    monkeypatch.setattr(m, "REPO", tmp_path)
    res = m.classify(man)
    assert res["changed"]["content_change"] == ["geom.xyz"]


def test_check_is_read_only(tmp_path, monkeypatch):
    m = _m()
    target = tmp_path / "a.csv"
    target.write_bytes(b"x\n")
    man = _manifest(tmp_path, [_row("a.csv")])
    monkeypatch.setattr(m, "REPO", tmp_path)
    before = man.read_bytes()
    rc = m.main(["--manifest", str(man.relative_to(tmp_path)), "--check"])
    assert man.read_bytes() == before
    assert rc == 1        # a drift must FAIL the gate


def test_missing_registered_path_fails_the_gate(tmp_path, monkeypatch):
    m = _m()
    man = _manifest(tmp_path, [_row("gone.csv")])
    monkeypatch.setattr(m, "REPO", tmp_path)
    assert m.main(["--manifest", "SHA256SUMS", "--check"]) == 1


def test_repository_manifests_all_verify():
    """The real registries must satisfy the real contract (this is the fix)."""
    m = _m()
    for week in ("week1", "week2", "week3"):
        rc = m.main(["--manifest", "outputs/%s/SHA256SUMS" % week, "--check"])
        assert rc == 0, week
