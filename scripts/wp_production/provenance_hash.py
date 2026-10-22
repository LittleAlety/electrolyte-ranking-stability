"""Explicit provenance-hash contract: text artifacts are LF-normalised.

**The measured defect (2026-10-22).** ``sha256_file`` hashed RAW BYTES.  Of the
726 text artifacts under the frontier/torsion work trees, **34 carried CRLF**
and 692 carried LF -- so the same logical geometry hashed two different ways
depending on which generator wrote it, and any re-checkout (git stores LF per
``.gitattributes: * text=auto eol=lf``) silently invalidated the recorded
provenance.  The repair had to patch hashes by hand.

**The contract, stated once and enforced here:**

* a TEXT artifact (known text suffix) is hashed over its bytes with every
  ````\\r\\n```` collapsed to ````\\n```` -- the form git stores, so the digest is
  identical before/after checkout and across platforms;
* a BINARY artifact (or an unknown suffix) is hashed over its raw bytes --
  never normalised, because a byte change there is a real content change;
* every generator that records provenance uses :func:`sha256_artifact`, and the
  registries stay comparable because the normalisation is a no-op for the 692
  already-LF files.

Callers never pass ``normalise=`` themselves: the dispatch is by artifact kind,
so a future call site cannot quietly pick the wrong side of the contract.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

#: suffixes treated as TEXT (normalised).  Everything else is raw bytes.
TEXT_SUFFIXES = frozenset({
    ".xyz", ".inp", ".log", ".input", ".out", ".txt", ".csv", ".tsv",
    ".json", ".md", ".py", ".ps1", ".sh", ".sbatch", ".html", ".css",
    ".js", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".smi", ".mol",
})

#: the contract, quoted verbatim into every registry index that uses it
CONTRACT = (
    "text artifacts: sha256 over CRLF->LF normalised bytes "
    "(git-stable, platform-stable); binary/unknown suffixes: sha256 over raw "
    "bytes; dispatch by suffix via sha256_artifact -- never by caller choice"
)


def sha256_raw(path: Path) -> str:
    """Digest of the file's raw bytes (binary caliber)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(path: Path) -> str:
    """Digest of the file's LF-normalised bytes (text caliber)."""
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def is_text(path: Path) -> bool:
    return Path(path).suffix.lower() in TEXT_SUFFIXES


def sha256_artifact(path: Path) -> str:
    """The contract: normalise text, keep binary raw."""
    p = Path(path)
    return sha256_text(p) if is_text(p) else sha256_raw(p)
