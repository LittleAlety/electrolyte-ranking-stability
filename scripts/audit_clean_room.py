#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Clean-room reproduction audit (R14, round-2 review item 6).

The review's item 6 asks for one thing the repository could not previously answer:
*from a fresh clone, with no local ORCA install and no ``..\\成果输出`` /
``..\\核心文件`` / ``..\\论文`` delivery layer, does the whole verifiable surface
still reproduce?*

This script answers it by inspecting the repository itself -- zero new electronic
structure, zero network access:

  C1  the in-repo reproducibility surface exists
  C2  every verification entry point named in README.md exists
  C3  which scripts reach outside the repository (delivery layer / historical
      week-24 audits), and the explicit fact that no *verification* entry point
      does
  C4  the test suite never reaches outside the repository
  C5  whether the external binaries (ORCA / xTB) are present, and the statement
      that their absence only blocks *new* electronic structure
  C6  every frozen manifest (week1/week2/week3 SHA256SUMS) recomputes
  C7  the close-out documents exist and say what the products say

Exit code is 0 when no check FAILs; INFO findings are expected and reported.

Usage
-----
    python scripts/audit_clean_room.py            # write the JSON + MD report
    python scripts/audit_clean_room.py --check    # compare, never write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTDIR = REPO_ROOT / "outputs" / "week26"
JSON_PATH = OUTDIR / "clean_room_audit.json"
MD_PATH = OUTDIR / "clean_room_audit.md"

REQUIRED_SURFACE = [
    "config", "data", "docs", "outputs", "scripts", "src", "structures", "tests",
    "README.md", "FINAL_CONCLUSIONS.md", "pyproject.toml", ".gitattributes",
]

VERIFICATION_ENTRY_POINTS = [
    "scripts/build_metadata.py",
    "scripts/build_github_readme.py",
    "scripts/build_final_conclusions.py",
    "scripts/analyze_r13_summary_figure.py",
    "scripts/build_terminal_site.py",
    "scripts/freeze_gates.py",
    "tests",
]

#: Names of the out-of-repo delivery layer (see README "reproduction boundary").
EXTERNAL_LAYER_NAMES = ("\u6210\u679c\u8f93\u51fa", "\u6838\u5fc3\u6587\u4ef6", "\u8bba\u6587")
PARENT_PATTERN = re.compile(r"\.parent\b")


def is_external_line(line: str) -> bool:
    """Heuristic: does this source line walk *up* out of the repository?

    A bare ``Path(__file__).resolve().parent / "fixtures"`` stays inside the
    repository and must not be flagged, so the line has to name one of the
    delivery-layer directories or walk up from a repository-root object.
    """

    if not PARENT_PATTERN.search(line):
        return False
    if "REPO_ROOT.parent" in line or "REPO.parent" in line or ".parent.resolve(" in line:
        return True
    return any(name in line for name in EXTERNAL_LAYER_NAMES)

MANIFESTS = [
    "outputs/week1/SHA256SUMS",
    "outputs/week2/SHA256SUMS",
    "outputs/week3/SHA256SUMS",
]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_external(rel: str) -> "list[str]":
    path = REPO_ROOT / rel
    if path.is_dir():
        hits = []
        for child in sorted(path.rglob("*.py")):
            hits += scan_external(child.relative_to(REPO_ROOT).as_posix())
        return hits
    if not path.is_file() or path.suffix != ".py":
        return []
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if is_external_line(line):
            found.append("%s:%d: %s" % (rel, number, line.strip()[:110]))
    return found


def verify_manifest(rel: str) -> dict:
    path = REPO_ROOT / rel
    if not path.exists():
        return {"manifest": rel, "exists": False, "rows": 0, "ok": 0, "mismatch": [], "missing": []}
    rows = 0
    ok = 0
    mismatch = []
    missing = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        if not name:
            continue
        rows += 1
        target = REPO_ROOT / name
        if not target.exists():
            missing.append(name)
            continue
        if sha256_of(target) == digest:
            ok += 1
        else:
            mismatch.append(name)
    return {"manifest": rel, "exists": True, "rows": rows, "ok": ok,
            "mismatch": mismatch[:20], "missing": missing[:20],
            "n_mismatch": len(mismatch), "n_missing": len(missing)}


def audit() -> dict:
    findings = []

    def add(check, level, title, detail):
        findings.append({"check": check, "level": level, "title": title, "detail": detail})

    # ---------------------------------------------------------------- C1 ----
    absent = [name for name in REQUIRED_SURFACE if not (REPO_ROOT / name).exists()]
    add("C1", "FAIL" if absent else "PASS",
        "in-repo reproducibility surface",
        "missing: " + ", ".join(absent) if absent
        else "%d/%d top-level entries present" % (len(REQUIRED_SURFACE), len(REQUIRED_SURFACE)))

    # ---------------------------------------------------------------- C2 ----
    missing_entry = [name for name in VERIFICATION_ENTRY_POINTS if not (REPO_ROOT / name).exists()]
    add("C2", "FAIL" if missing_entry else "PASS",
        "verification entry points",
        "missing: " + ", ".join(missing_entry) if missing_entry
        else "%d/%d present" % (len(VERIFICATION_ENTRY_POINTS), len(VERIFICATION_ENTRY_POINTS)))

    # ---------------------------------------------------------------- C3 ----
    external_scripts = {}
    for rel in sorted((REPO_ROOT / "scripts").glob("*.py")):
        if rel.name == Path(__file__).name:
            # The auditor names the delivery layer on purpose (it is the definition
            # of the heuristic), so it must not report itself as a finding.
            continue
        hits = scan_external("scripts/" + rel.name)
        if hits:
            external_scripts[rel.name] = hits
    entry_point_hits = {
        name: external_scripts[name] for name in external_scripts
        if name in {Path(p).name for p in VERIFICATION_ENTRY_POINTS}
    }
    detail = ("%d script(s) reference the out-of-repo delivery layer (the auditor itself is "
              "excluded by construction); none of them is a verification entry point. "
              % len(external_scripts))
    detail += "; ".join(sorted(external_scripts)) if external_scripts else "none"
    add("C3", "FAIL" if entry_point_hits else "INFO",
        "scripts reaching outside the repository",
        detail)

    # ---------------------------------------------------------------- C4 ----
    test_hits = scan_external("tests")
    add("C4", "FAIL" if test_hits else "PASS",
        "tests never reach outside the repository",
        "%d reference(s)" % len(test_hits) if test_hits else "0 references")

    # ---------------------------------------------------------------- C5 ----
    sys.path.insert(0, str(REPO_ROOT / "src"))
    presence = {}
    try:
        from electrolyte_ranking.toolchain import find_executable  # noqa: E402

        for name in ("orca", "xtb"):
            try:
                presence[name] = find_executable(name)
            except Exception:  # pragma: no cover - reported, not raised
                presence[name] = None
    except Exception:  # pragma: no cover
        presence = {}
    print("external binaries (machine-specific, deliberately NOT recorded): %s"
          % (", ".join("%s=%s" % (key, value or "not found")
                       for key, value in sorted(presence.items())) or "probe unavailable"))
    add("C5", "INFO",
        "external binaries are optional for verification",
        "no verification entry point needs ORCA or xTB; they are required only for NEW "
        "electronic structure. Their presence is printed to stdout, not written into this "
        "report, so the report stays machine-independent and --check works in a clean clone.")

    # ---------------------------------------------------------------- C6 ----
    manifests = [verify_manifest(rel) for rel in MANIFESTS]
    total_rows = sum(m["rows"] for m in manifests)
    total_ok = sum(m["ok"] for m in manifests)
    broken = [m["manifest"] for m in manifests
              if not m["exists"] or m.get("n_mismatch") or m.get("n_missing")]
    add("C6", "FAIL" if broken else "PASS",
        "frozen manifests recompute",
        "%d/%d rows match; broken: %s" % (total_ok, total_rows, ", ".join(broken) or "none"))

    # ---------------------------------------------------------------- C7 ----
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8") if (REPO_ROOT / "README.md").exists() else ""
    final = (REPO_ROOT / "FINAL_CONCLUSIONS.md").read_text(encoding="utf-8") if (REPO_ROOT / "FINAL_CONCLUSIONS.md").exists() else ""
    questions = len(re.findall(r"^## Q\d+\.", final, flags=re.MULTILINE))
    problems = []
    for token in ("NOT CLOSABLE", "not establish a definitive electrolyte-solvent ranking"):
        if token not in readme:
            problems.append("README.md lacks %r" % token)
    if questions != 10:
        problems.append("FINAL_CONCLUSIONS.md answers %d questions, expected 10" % questions)
    add("C7", "FAIL" if problems else "PASS",
        "close-out documents match the products",
        "; ".join(problems) if problems else
        "README Scope + NOT CLOSABLE present; FINAL_CONCLUSIONS.md answers 10 questions")

    verdict = "FAIL" if any(item["level"] == "FAIL" for item in findings) else "OK"
    return {
        "stage": "R14 clean-room reproduction audit",
        "definition": (
            "Static, offline audit of what a fresh clone can reproduce without the local ORCA/xTB "
            "install and without the out-of-repo delivery layer."
        ),
        "required_surface": REQUIRED_SURFACE,
        "verification_entry_points": VERIFICATION_ENTRY_POINTS,
        "findings": findings,
        "external_layer_scripts": external_scripts,
        "manifests": manifests,
        "verdict": verdict,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Clean-room \u590d\u73b0\u5ba1\u8ba1\uff08R14\uff09",
        "",
        "> \u7531 `scripts/audit_clean_room.py` \u751f\u6210\uff1a\u5b98\u65b9\u79bb\u7ebf\u9759\u6001\u5ba1\u8ba1\uff0c"
        "\u4e0d\u8dd1\u65b0\u7535\u5b50\u7ed3\u6784\u3001\u4e0d\u8054\u7f51\u3002",
        "",
        "**\u5b9a\u4e49**\uff1a%s" % report["definition"],
        "",
        "**\u88c1\u51b3**\uff1a**%s**" % report["verdict"],
        "",
        "| \u68c0\u67e5 | \u7ea7\u522b | \u9879\u76ee | \u8be6\u60c5 |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["findings"]:
        lines.append("| %s | %s | %s | %s |"
                     % (item["check"], item["level"], item["title"],
                        item["detail"].replace("|", "\\|")))
    lines += [
        "",
        "## \u51bb\u7ed3\u6e05\u5355\u590d\u7b97",
        "",
        "| manifest | \u884c\u6570 | \u5339\u914d | \u4e0d\u5339\u914d | \u7f3a\u6587\u4ef6 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for manifest in report["manifests"]:
        lines.append("| `%s` | %d | %d | %d | %d |"
                     % (manifest["manifest"], manifest["rows"], manifest["ok"],
                        manifest.get("n_mismatch", 0), manifest.get("n_missing", 0)))
    lines += [
        "",
        "## \u4ed3\u5e93\u5916\u4f9d\u8d56\uff08\u975e\u9a8c\u8bc1\u8def\u5f84\uff09",
        "",
        "\u4ee5\u4e0b\u811a\u672c\u4f1a\u8bfb / \u5199\u4ed3\u5e93\u5916\u7684\u4ea4\u4ed8\u5c42"
        "\uff08`..\\\u6210\u679c\u8f93\u51fa\\`\u3001`..\\\u6838\u5fc3\u6587\u4ef6\\`\u3001`..\\\u8bba\u6587\\`\uff09\uff0c"
        "\u5b83\u4eec**\u4e0d\u662f** README \u91cc\u7684\u9a8c\u8bc1\u5165\u53e3\uff1a",
        "",
    ]
    if report["external_layer_scripts"]:
        for name in sorted(report["external_layer_scripts"]):
            lines.append("- `scripts/%s`\uff08%d \u5904\uff09" % (name, len(report["external_layer_scripts"][name])))
    else:
        lines.append("- \u65e0")
    lines += [
        "",
        "## \u7eaa\u5f8b\u58f0\u660e",
        "",
        "- \u672c\u5ba1\u8ba1\u53ea\u8bfb\u672c\u4ed3\u5e93\uff1b\u672a\u8dd1\u65b0\u7535\u5b50\u7ed3\u6784\uff0c"
        "\u672a\u8bbf\u95ee\u7f51\u7edc\uff0c\u672a\u4fee\u6539\u4efb\u4f55\u51bb\u7ed3\u4ea7\u7269\u3002",
        "- \u672c\u673a\u7684 ORCA / xTB \u5b89\u88c5\u76ee\u5f55\u53ea\u5f71\u54cd**\u65b0\u589e**"
        "\u7535\u5b50\u7ed3\u6784\u8ba1\u7b97\uff0c\u4e0d\u5f71\u54cd\u672c\u4ed3\u5e93\u4efb\u4f55 `--check`\u3001"
        "manifest \u590d\u7b97\u6216\u6d4b\u8bd5\u3002",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Clean-room reproduction audit (R14).")
    parser.add_argument("--check", action="store_true", help="compare, never write")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    report = audit()
    json_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    md_text = render_markdown(report)

    for item in report["findings"]:
        print("[%s] %s -- %s" % (item["level"], item["check"], item["title"]))
        print("      " + item["detail"])
    print("verdict: %s" % report["verdict"])

    if args.check:
        for path, expected in ((JSON_PATH, json_text), (MD_PATH, md_text)):
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path.relative_to(REPO_ROOT).as_posix())
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text"
                      % path.relative_to(REPO_ROOT).as_posix())
                return 1
        print("CHECK OK -- clean-room audit JSON/MD are byte-identical")
        return 0 if report["verdict"] == "OK" else 1

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json_text)
    with open(MD_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(md_text)
    print("wrote %s" % JSON_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % MD_PATH.relative_to(REPO_ROOT).as_posix())
    return 0 if report["verdict"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
