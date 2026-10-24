"""Re-freeze a frozen provenance manifest under the explicit hash contract.

Why this exists
---------------
The week1/week2/week3 `SHA256SUMS` registries were produced by a one-off script
that no longer exists in the tree, and `audit_clean_room` only VERIFIES them.
That left exactly one way to keep them true: hand-patching lines -- which is
how a registry silently rots.  The 2026-10-22 provenance repair had to do that
by hand for two rows.

This generator makes the registry reproducible again, and it classifies every
changed row so a reviewer can tell bookkeeping from science:

* ``eol_recalibration`` -- the recorded digest was taken over CRLF bytes; the
  contract's LF digest is recomputed.  Same logical content, new caliber.
* ``content_change``    -- the file's content really differs from the freeze;
  this is listed VERBATIM in the record so a changed file is never mistaken
  for an EOL artifact.

``--check`` recomputes and compares without writing (read-only), so the same
contract can gate the chain.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from provenance_hash import CONTRACT, sha256_artifact, sha256_raw  # noqa: E402

RECORD = REPO / "outputs" / "week26" / "provenance_refreeze_record.json"


def _rows(manifest: Path) -> list[tuple[str, str]]:
    out = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        if not name:
            continue
        out.append((digest, name))
    return out


def is_deliberately_ignored(rel: str) -> bool:
    """True when rel is **excluded on purpose** (matched by .gitignore).

    A frozen registry may legitimately name machine-local artifacts that are
    deliberately not shipped (measured 2026-10-23: outputs/week3/SHA256SUMS
    lists 18 *.cpcm / *.property.txt ORCA demo files excluded by
    .gitignore:45).  Their absence in a clean clone is **not drift**.

    The distinction that matters is *ignored* vs *merely absent*: a path that a
    repository is supposed to ship but no longer has is real drift and must
    still fail.  git check-ignore answers exactly that.  Anything git cannot
    answer (not a repository, git missing) counts as NOT ignored, so the gate
    keeps failing loudly.
    """
    try:
        out = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", rel],
                             capture_output=True, check=False)
    except OSError:
        return False
    return out.returncode == 0


def classify(manifest: Path, drop: set[str] | None = None) -> dict:
    drop = drop or set()
    changed = {"eol_recalibration": [], "content_change": [], "missing": [],
               "external_machine_local": [], "dropped": sorted(drop)}
    lines = []
    for old, rel in _rows(manifest):
        if rel in drop:
            continue          # self-referential: cannot be frozen here
        target = REPO / rel
        if not target.is_file():
            # Never shipped => absent by construction, not "gone".  When git
            # cannot answer (no repo), fall back to counting it as missing so
            # the gate still fails loudly.
            if is_deliberately_ignored(rel):
                changed["external_machine_local"].append(rel)
            else:
                changed["missing"].append(rel)
            lines.append("%s  %s" % (old, rel))
            continue
        new = sha256_artifact(target)
        lines.append("%s  %s" % (new, rel))
        if new == old:
            continue
        if sha256_raw(target) == old:
            changed["eol_recalibration"].append(rel)
        else:
            changed["content_change"].append(rel)
    return {"rendered": "\n".join(lines) + "\n", "changed": changed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default="outputs/week3/SHA256SUMS")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--drop", action="append", default=[],
                    help="registry row to remove (self-referential artifact); "
                         "repeatable, recorded with --reason")
    ap.add_argument("--reason", default="",
                    help="why the dropped rows cannot be frozen here")
    args = ap.parse_args(argv)

    manifest = REPO / args.manifest
    drop = set(args.drop)
    result = classify(manifest, drop)
    changed = result["changed"]
    n_eol = len(changed["eol_recalibration"])
    n_content = len(changed["content_change"])
    n_missing = len(changed["missing"])
    n_external = len(changed["external_machine_local"])
    n_dropped = len(changed["dropped"])

    print("%s: eol=%d content=%d missing=%d dropped=%d external=%d"
          % (args.manifest, n_eol, n_content, n_missing, n_dropped, n_external))
    for rel in changed["content_change"][:20]:
        print("   content_change: %s" % rel)
    for rel in changed["missing"][:20]:
        print("   missing       : %s" % rel)
    for rel in changed["external_machine_local"][:5]:
        print("   not shipped   : %s (gitignored: absent in a clean clone by design)" % rel)

    if args.check:
        if n_missing:
            print("CHECK FAILED -- %d registered paths are gone" % n_missing)
            return 1
        if n_eol:
            print("CHECK FAILED -- %d rows still carry the old caliber" % n_eol)
            return 1
        if n_content:
            # a stale manifest is a provenance failure: the frozen record no
            # longer describes the tree.  Re-freeze deliberately, with --write,
            # so the change lands in the record instead of passing silently.
            print("CHECK FAILED -- %d rows drifted from the freeze" % n_content)
            return 1
        print("CHECK OK -- every registered digest matches the contract")
        return 0

    if not args.write:
        print("(read-only; pass --write to re-freeze)")
        return 0

    manifest.write_text(result["rendered"], encoding="utf-8", newline="\n")
    existing = {}
    if RECORD.is_file():
        existing = json.loads(RECORD.read_text(encoding="utf-8"))
    existing.setdefault("schema_version", "1.1")
    existing["contract"] = CONTRACT
    existing["generator"] = "scripts/wp_production/refreeze_manifest.py"
    per = existing.setdefault("manifests", {})
    per[args.manifest] = {
        "eol_recalibration": sorted(changed["eol_recalibration"]),
        "content_change": sorted(changed["content_change"]),
        "missing": sorted(changed["missing"]),
        "dropped": sorted(changed["dropped"]),
        "drop_reason": args.reason or (
            "self-referential artifact: cannot be frozen inside the registry "
            "its own audit verifies"),
    }
    RECORD.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print("re-frozen %s; record -> %s"
          % (args.manifest, RECORD.relative_to(REPO).as_posix()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
