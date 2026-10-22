"""Provenance-hash contract tests (the CRLF/LF defect, pinned).

The measured failure: 34 of 726 text artifacts carried CRLF, so raw-byte
provenance hashes were unstable across generators, platforms and re-checkouts.
These tests pin the contract so that failure cannot come back silently.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "provenance_hash.py"


def _m():
    spec = importlib.util.spec_from_file_location("provenance_hash", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def test_crlf_and_lf_copies_of_the_same_text_hash_identically(tmp_path):
    """The whole point: line endings are not content."""
    m = _m()
    lf = tmp_path / "a.xyz"
    crlf = tmp_path / "b.xyz"
    body = "3\ncomment\nC 0.0 0.0 0.0\nH 1.0 0.0 0.0\nH 0.0 1.0 0.0\n"
    lf.write_bytes(body.replace("\n", "\n").encode())
    crlf.write_bytes(body.replace("\n", "\r\n").encode())
    assert m.sha256_text(lf) == m.sha256_text(crlf)
    assert m.sha256_artifact(lf) == m.sha256_artifact(crlf)


def test_raw_caliber_still_distinguishes_them(tmp_path):
    """The raw caliber must NOT hide a real byte difference."""
    m = _m()
    lf = tmp_path / "a.log"
    crlf = tmp_path / "b.log"
    lf.write_bytes(b"line1\nline2\n")
    crlf.write_bytes(b"line1\r\nline2\r\n")
    assert m.sha256_raw(lf) != m.sha256_raw(crlf)


def test_binary_is_never_normalised(tmp_path):
    """A binary artifact keeps its raw digest even if it contains CRLF bytes."""
    m = _m()
    blob = tmp_path / "x.bin"
    data = b"\x00\x01\r\n\x02\xff"
    blob.write_bytes(data)
    assert m.sha256_artifact(blob) == m.sha256_raw(blob) == m.sha256_raw(blob)
    assert m.is_text(blob) is False


def test_dispatch_is_by_suffix_not_by_caller(tmp_path):
    """Same bytes, different suffix -> different caliber (the contract is explicit)."""
    m = _m()
    payload = b"alpha\r\nbeta\r\n"
    as_text = tmp_path / "payload.csv"
    as_bin = tmp_path / "payload.dat"
    as_text.write_bytes(payload)
    as_bin.write_bytes(payload)
    assert m.sha256_artifact(as_text) != m.sha256_artifact(as_bin)
    assert m.sha256_artifact(as_text) == m.sha256_text(as_text)


def test_normalisation_is_a_noop_for_lf_files(tmp_path):
    """748 of the real artifacts are already LF, so their digests must not move."""
    m = _m()
    p = tmp_path / "already.xyz"
    p.write_bytes(b"2\nc\nH 0 0 0\nH 1 0 0\n")
    assert m.sha256_text(p) == m.sha256_raw(p)


def test_contract_string_is_published():
    m = _m()
    assert "CRLF->LF" in m.CONTRACT
    assert "raw" in m.CONTRACT
    assert "never by caller choice" in m.CONTRACT
