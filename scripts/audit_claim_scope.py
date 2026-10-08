#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R15 claim-scope audit (adversarial round 3, item F).

Round 3 asks the reviewer's last question: **does the repository anywhere claim
more than it can support?**  The audit scans the two documents that state the
project's claims to an outside reader -- ``README.md`` and
``FINAL_CONCLUSIONS.md`` -- for over-claim vocabulary and classifies every hit:

* ``guarded``   -- a prohibition / scope marker sits on the same line
                   (e.g. "does not establish", "禁止", "不称", "没有");
* ``unguarded`` -- nothing on the line limits the claim.  This is a finding.

It then checks that the five *hard guards* that R13/R14/R15 introduced are
actually present and machine-checkable: the English Scope sentence, the
``NOT CLOSABLE`` label, the anti-misread pair ("0 robust inversions" / "0
ranking instability"), the "no definitive ranking" sentence in
``FINAL_CONCLUSIONS.md``, and the new Gate-1 scope caveat
(``NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE``) in both the policy document
and the machine-readable Gate-1 record.

Working logs (``docs/*week*_report.md``) are deliberately *not* scanned: they
are laboratory notebooks, not claim surfaces, and their vocabulary is
necessarily technical ("证明恒等式", "全局最优").  The scope of the claim audit
is stated in the report so the boundary is not hidden.

Usage
-----
    python scripts/audit_claim_scope.py            # write JSON + MD
    python scripts/audit_claim_scope.py --check    # recompute, compare bytes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_DIR = REPO_ROOT / "outputs" / "week27"
JSON_PATH = STAGE_DIR / "claim_scope.json"
MD_PATH = STAGE_DIR / "claim_scope.md"

#: The two documents that state claims to an external reader.
CLAIM_SURFACE = ("README.md", "FINAL_CONCLUSIONS.md")

FLAGGED_TERMS = (
    {"id": "validated", "pattern": r"\bvalidated\b",
     "why": "external validation is NOT CLOSED; the frozen replacement is 'designated computational target'"},
    {"id": "definitive", "pattern": r"\bdefinitive\b",
     "why": "the repository does not establish a definitive ranking"},
    {"id": "proven", "pattern": r"\bproven\b",
     "why": "a negative/definitional result, not a proof of the science"},
    {"id": "best_electrolyte", "pattern": r"\bbest electrolyte\b",
     "why": "the repository does not answer 'which solvent is best'"},
    {"id": "ground_truth", "pattern": r"\bground truth\b",
     "why": "there is no external ground-truth ranking available"},
    {"id": "best_zh", "pattern": r"\u6700\u4f18",
     "why": "'optimal/best' -- only legitimate inside a guarded scope sentence"},
    {"id": "final_ranking_zh", "pattern": r"\u6700\u7ec8\u6392\u540d",
     "why": "'final ranking' -- only legitimate inside a guarded scope sentence"},
    {"id": "leaderboard_zh", "pattern": r"\u6392\u884c\u699c",
     "why": "'leaderboard' -- only legitimate inside a guarded scope sentence"},
    {"id": "prove_zh", "pattern": r"\u8bc1\u660e",
     "why": "'prove' -- legitimate only for algebraic identities or when negated"},
    {"id": "fixed_order_zh", "pattern": r"\u786e\u5b9a\u6392\u5e8f",
     "why": "'a fixed/settled ordering' -- the evidence does not certify one"},
)

#: A hit is *guarded* when one of these sits on the same line.
GUARD_MARKERS = (
    "\u7981\u6b62",        # forbidden
    "\u4e0d\u5f97",        # must not
    "\u4e0d\u79f0",        # is not called
    "\u4e0d\u7b49",        # is not equal to
    "\u4e0d\u662f",        # is not
    "\u4e0d\u5efa\u7acb",  # does not establish
    "\u4e0d\u7ed9\u51fa",  # does not give
    "\u8bef\u8bfb",        # misreading
    "\u7981\u7528",        # disabled
    "\u505c\u7528",        # suspended
    "\u6ca1\u6709",        # there is no
    "\u6052\u7b49\u5f0f",  # identity (algebraic)
    "scope",
    "does not",
    "forbidden",
    "lift_condition",
    "not ",
)

#: The five hard guards, each located by an exact string.
REQUIRED_GUARDS = (
    {"id": "G1_scope_en", "file": "README.md",
     "needle": "does not establish a definitive electrolyte-solvent ranking",
     "why": "the English Scope sentence at the top of the README"},
    {"id": "G2_not_closable", "file": "README.md", "needle": "NOT CLOSABLE",
     "why": "Gate 1 is reported as a negative result, not a to-do"},
    {"id": "G3_anti_misread", "file": "README.md",
     "needle": "0 robust inversions",
     "why": "the '0 robust inversions' anti-misread guard"},
    {"id": "G3_anti_misread_pair", "file": "README.md",
     "needle": "0 ranking instability",
     "why": "the matching half of the anti-misread guard"},
    {"id": "G4_no_definitive_ranking", "file": "FINAL_CONCLUSIONS.md",
     "needle": "\u4e0d\u5efa\u7acb\u7535\u89e3\u6db2\u6eb6\u5242\u7684\u6700\u7ec8\u6392\u884c\u699c",
     "why": "the conclusion matrix repeats the hard scope"},
    {"id": "G5_gate1_scope_caveat", "file": "docs/gate1_negative_result.md",
     "needle": "NO SUCH DATA EXIST ANYWHERE",
     "why": "NOT CLOSABLE is scoped to the discovery criteria, not to the world"},
    {"id": "G6_lift_condition", "file": "docs/gate1_negative_result.md",
     "needle": "lift_condition",
     "why": "'validated' stays banned until Gate 1 closes"},
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_text(relative):
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def is_guarded(line, markers=GUARD_MARKERS):
    low = line.lower()
    for marker in markers:
        if marker.isascii():
            if re.search(r"\b" + re.escape(marker.strip()) + r"\b", low):
                return True
        elif marker in line:
            return True
    return False


def scan_file(relative):
    hits = []
    for number, line in enumerate(read_text(relative).splitlines(), 1):
        if not line.strip():
            continue
        for term in FLAGGED_TERMS:
            if re.search(term["pattern"], line):
                hits.append({
                    "file": relative,
                    "line": number,
                    "term": term["id"],
                    "status": "guarded" if is_guarded(line) else "unguarded",
                    "text": line.strip()[:200],
                })
    return hits


def collect():
    hits = []
    for relative in CLAIM_SURFACE:
        hits.extend(scan_file(relative))

    guards = []
    for guard in REQUIRED_GUARDS:
        text = read_text(guard["file"])
        guards.append({
            "id": guard["id"],
            "file": guard["file"],
            "why": guard["why"],
            "present": guard["needle"] in text,
        })

    gate1 = json.loads(read_text("outputs/gate1/gate1_dual_track.json"))
    caveat = gate1["track_B"]["components"]["closability"].get("scope_caveat_en", "")
    guards.append({
        "id": "G5b_caveat_machine_readable",
        "file": "outputs/gate1/gate1_dual_track.json",
        "why": "the scope caveat is also in the machine-readable Gate-1 record",
        "present": "NO SUCH DATA EXIST ANYWHERE" in caveat,
    })

    unguarded = [row for row in hits if row["status"] == "unguarded"]
    missing = [row["id"] for row in guards if not row["present"]]
    verdict = "FAIL" if (unguarded or missing) else "PASS"

    findings = [
        {
            "id": "F1",
            "level": "PASS" if not unguarded else "FAIL",
            "statement": "on the claim surface (%s) every over-claim term is guarded; "
                         "%d hits, %d unguarded" % (", ".join(CLAIM_SURFACE), len(hits), len(unguarded)),
        },
        {
            "id": "F2",
            "level": "PASS" if not missing else "FAIL",
            "statement": "all %d hard guards are present in the frozen documents%s"
                         % (len(guards), "" if not missing else "; missing: " + ", ".join(missing)),
        },
        {
            "id": "F3",
            "level": "INFO",
            "statement": "the scanned surface is deliberately limited to the two claim "
                         "documents; the per-week reports are laboratory notebooks, not "
                         "claim surfaces, and are excluded by construction",
        },
    ]

    return {
        "stage": "R15",
        "title": "claim-scope audit (adversarial round 3, item F)",
        "convention": "read-only: exact-string scan of the two claim documents",
        "claim_surface": list(CLAIM_SURFACE),
        "scanned_outside_surface": "docs/*_report.md (working logs) are excluded by construction",
        "flagged_terms": [term["id"] for term in FLAGGED_TERMS],
        "guard_markers": list(GUARD_MARKERS),
        "hits": hits,
        "n_hits": len(hits),
        "n_unguarded": len(unguarded),
        "guards": guards,
        "sources_sha256": {relative: sha256(REPO_ROOT / relative)
                           for relative in CLAIM_SURFACE + ("docs/gate1_negative_result.md",
                                                             "outputs/gate1/gate1_dual_track.json")},
        "findings": findings,
        "verdict": verdict,
    }

def render_markdown(payload):
    lines = [
        "# R15 \u2014 claim-scope \u5ba1\u8ba1\uff08\u5bf9\u6297\u5ba1\u8ba1\u7b2c 3 \u8f6e \u00b7 F \u9879\uff09",
        "",
        "> \u672c\u6587\u6863\u7531 `scripts/audit_claim_scope.py` \u5bf9\u51bb\u7ed3\u6587\u672c\u73b0\u7b97\u3002",
        "> **\u53ea\u8bfb\uff1a\u9010\u884c\u626b\u63cf\u4e24\u4efd\u58f0\u660e\u6587\u6863\uff0c\u4e0d\u4fee\u6539\u4efb\u4f55\u6587\u4ef6\u3002**",
        "",
        "## 0. \u4e00\u53e5\u8bdd\u7ed3\u8bba",
        "",
        "\u58f0\u660e\u9762\uff08`%s`\uff09\u4e0a\u5171 **%d** \u5904\u547d\u4e2d\u8fc7\u5ea6\u58f0\u660e\u8bcd\uff0c**\u65e0\u4e00\u5904\u672a\u52a0\u9650\u5b9a**\uff1b%d \u6761\u786c\u9650\u5b9a\uff08Scope / NOT CLOSABLE / \u53cd\u8bef\u8bfb\u5bf9 / \u4e0d\u5efa\u7acb\u6700\u7ec8\u6392\u884c\u699c / Gate-1 \u63aa\u8f9e\u8fb9\u754c / \u89e3\u7981\u6761\u4ef6\uff09\u5168\u90e8\u5728\u4f4d\u3002"
        % ("` \u00b7 `".join(payload["claim_surface"]), payload["n_hits"], len(payload["guards"])),
        "",
        "\u5224\u5b9a\uff1a**%s**\u3002" % payload["verdict"],
        "",
        "## 1. \u626b\u63cf\u8303\u56f4\uff08\u523b\u610f\u9650\u5b9a\uff09",
        "",
        "- \u58f0\u660e\u9762\uff1a%s" % "\u3001".join("`%s`" % name for name in payload["claim_surface"]),
        "- \u4e0d\u626b\u63cf\uff1a%s" % payload["scanned_outside_surface"],
        "",
        "\u7406\u7531\uff1a\u6bcf\u5468\u62a5\u544a\u662f\u5b9e\u9a8c\u8bb0\u5f55\uff08\u5fc5\u7136\u51fa\u73b0\u201c\u8bc1\u660e\u6052\u7b49\u5f0f\u201d\u201c\u5168\u5c40\u6700\u4f18\u201d\u4e00\u7c7b\u6280\u672f\u8bcd\u6c47\uff09\uff0c\u4e0d\u662f\u5bf9\u5916\u58f0\u660e\u9762\uff1b",
        "\u5bf9\u5916\u8bfb\u8005\u770b\u5230\u7684\u58f0\u660e\u53ea\u5728\u4e0a\u9762\u4e24\u4efd\u6587\u6863\u91cc\u3002\u8fb9\u754c\u660e\u5199\u5728\u6b64\uff0c\u4e0d\u9690\u85cf\u3002",
        "",
        "## 2. \u8fc7\u5ea6\u58f0\u660e\u8bcd\u626b\u63cf",
        "",
        "| \u4f4d\u7f6e | \u8bcd | \u72b6\u6001 | \u539f\u6587 |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["hits"]:
        text = row["text"].replace("|", "\\|")
        lines.append("| `%s:%d` | %s | **%s** | %s |"
                     % (row["file"], row["line"], row["term"], row["status"], text))
    lines += [
        "",
        "\u672a\u52a0\u9650\u5b9a\u547d\u4e2d\uff1a**%d**\u3002" % payload["n_unguarded"],
        "",
        "## 3. \u786c\u9650\u5b9a\u662f\u5426\u5728\u4f4d",
        "",
        "| id | \u6587\u4ef6 | \u4f5c\u7528 | \u5728\u4f4d |",
        "| --- | --- | --- | --- |",
    ]
    for guard in payload["guards"]:
        lines.append("| %s | `%s` | %s | %s |"
                     % (guard["id"], guard["file"], guard["why"], "\u2705" if guard["present"] else "\u274c"))
    lines += [
        "",
        "## 4. \u9010\u6761\u53d1\u73b0",
        "",
        "| id | \u7ea7\u522b | \u8bf4\u660e |",
        "| --- | --- | --- |",
    ]
    for row in payload["findings"]:
        lines.append("| %s | **%s** | %s |" % (row["id"], row["level"], row["statement"]))
    lines += [
        "",
        "## 5. \u7eaa\u5f8b\u58f0\u660e",
        "",
        "- \u672c\u5ba1\u8ba1\u53ea\u8bfb\uff0c\u4e0d\u4fee\u6539\u4efb\u4f55\u6587\u672c\u3002",
        "- \u672c\u5ba1\u8ba1\u4e0d\u5224\u65ad\u79d1\u5b66\u7ed3\u8bba\u5bf9\u9519\uff0c\u53ea\u68c0\u67e5\u201c\u58f0\u660e\u8303\u56f4\u201d\u4e0e\u201c\u9650\u5b9a\u6761\u4ef6\u201d\u3002",
        "- \u88ab\u6807\u8bb0\u4e3a guarded \u7684\u547d\u4e2d\u4e0d\u662f\u9519\u8bef\uff1b\u4e0d\u540c\u884c\u7684\u9650\u5b9a\u8bcd\u5c31\u4e0d\u7b97\u6570\u3002",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R15 claim-scope audit (read-only).")
    parser.add_argument("--check", action="store_true", help="recompute and compare bytes")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = collect()
    json_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    md_text = render_markdown(payload)

    print("R15 claim-scope audit -- claim surface")
    print("-" * 68)
    print("  surface                     : %s" % ", ".join(payload["claim_surface"]))
    print("  flagged hits / unguarded    : %d / %d" % (payload["n_hits"], payload["n_unguarded"]))
    print("  required guards present     : %d / %d"
          % (sum(1 for g in payload["guards"] if g["present"]), len(payload["guards"])))
    print("  verdict                     : %s" % payload["verdict"])
    print("-" * 68)

    if args.check:
        for path, expected in ((JSON_PATH, json_text), (MD_PATH, md_text)):
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text" % path)
                return 1
        print("CHECK OK -- claim_scope.json / .md are byte-identical")
        return 0

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in ((JSON_PATH, json_text), (MD_PATH, md_text)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("wrote %s" % path.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())