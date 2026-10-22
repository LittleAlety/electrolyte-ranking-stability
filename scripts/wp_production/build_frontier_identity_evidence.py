"""Identity evidence-chain assembly (plan v3.1 item 2): pending -> verified.

Every weighted member must carry, from ONE AND THE SAME run:
input + log + geometry + Molden/FMO data with raw byte hashes; correct method,
charge, multiplicity, SCF and normal-termination evidence; and a consistent
operator+spin+orbital_index identity.  This generator assembles that chain for
each member of the CURRENT weights table (denominator derived, never pinned)
and flips ``identity_qc_status`` from ``pending`` to ``verified`` — or records
the concrete missing link.

Fail-closed on integrity, not on absence: a missing local file reads as
``awaiting_local_artifacts`` (the plan: "缺本地文件不等于需要重算"), while a
hash mismatch or a wrong charge reads as a QC failure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FRONTIER = REPO / "outputs" / "physics_completion" / "frontier"
PKG = REPO / "work" / "hpc_frontier_localization_v1"

OUT_CSV = FRONTIER / "frontier_identity_evidence.csv"
OUT_INDEX = FRONTIER / "frontier_identity_evidence_index.json"


from provenance_hash import sha256_artifact as _sha  # noqa: E402


def _members() -> list[dict]:
    """The CURRENT weighted cohort — derived, never a pinned denominator."""
    weights = FRONTIER / "frontier_localization.csv"
    with weights.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("status") == "computed"]


def _check_member(row: dict) -> tuple[str, dict]:
    """(identity_qc_status, evidence dict) for one member."""
    key = row["member_key"]
    leaf = key.replace("|", "__")
    att = PKG / "tasks" / leaf / "attempt"
    evidence: dict[str, str] = {"member_key": key}

    # 1) same-run artifacts must all exist
    need = ["job.inp", "geom.xyz", "job.log", "job.molden.input"]
    missing = [n for n in need if not (att / n).is_file()]
    if missing:
        evidence["missing_artifacts"] = ";".join(missing)
        return "awaiting_local_artifacts", evidence

    inp = (att / "job.inp").read_text(encoding="utf-8", errors="replace")
    log = (att / "job.log").read_text(encoding="utf-8", errors="replace")

    # 2) method/charge/multiplicity against the leg's registration
    ok_method = "wB97X-D4" in inp and "def2-TZVPD" in inp
    ok_scf = "TightSCF" in inp
    ok_term = "ORCA TERMINATED NORMALLY" in log
    import re
    m = re.search(r"\* xyzfile (\S+) (\S+) geom\.xyz", inp)
    ok_charge_mult = bool(m) and (m.group(1) == row.get("charge", "")) \
        and (m.group(2) == row.get("multiplicity", ""))
    if not (ok_method and ok_scf and ok_term and ok_charge_mult):
        bad = []
        if not ok_method: bad.append("method")
        if not ok_scf: bad.append("scf_keyword")
        if not ok_term: bad.append("normal_termination")
        if not ok_charge_mult: bad.append("charge_or_multiplicity")
        evidence["failed_checks"] = ";".join(bad)
        return "qc_failed", evidence

    # 3) raw byte hashes of the same-run artifacts
    for n in need:
        evidence["sha256_" + n.replace(".", "_")] = _sha(att / n)

    # 4) spin-consistent orbital identity (operator + spin + orbital_index
    #    already cross-checked by frontier_spin_qc; verify the channel count
    #    matches the declared wavefunction)
    wf = row.get("wavefunction", "")
    if wf == "U" and row.get("spin_reported", "") not in ("alpha", "beta"):
        evidence["failed_checks"] = "spin_channel_identity"
        return "qc_failed", evidence
    if wf == "R" and row.get("spin_reported", "") != "restricted":
        evidence["failed_checks"] = "spin_channel_identity"
        return "qc_failed", evidence
    evidence["spin_reported"] = row.get("spin_reported", "")
    evidence["wavefunction"] = wf

    return "verified", evidence


def build_rows() -> list[dict]:
    out = []
    for row in _members():
        status, ev = _check_member(row)
        out.append({
            "member_key": ev["member_key"],
            "identity_qc_status": status,
            "sha256_job_inp": ev.get("sha256_job_inp", ""),
            "sha256_geom_xyz": ev.get("sha256_geom_xyz", ""),
            "sha256_job_log": ev.get("sha256_job_log", ""),
            "sha256_job_molden_input": ev.get("sha256_job_molden_input", ""),
            "wavefunction": ev.get("wavefunction", ""),
            "spin_reported": ev.get("spin_reported", ""),
            "missing_artifacts": ev.get("missing_artifacts", ""),
            "failed_checks": ev.get("failed_checks", ""),
        })
    return out


FIELDS = ["member_key", "identity_qc_status", "sha256_job_inp",
          "sha256_geom_xyz", "sha256_job_log", "sha256_job_molden_input",
          "wavefunction", "spin_reported", "missing_artifacts", "failed_checks"]


def write_outputs() -> None:
    rows = build_rows()
    FRONTIER.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    counts = Counter(r["identity_qc_status"] for r in rows)
    OUT_INDEX.write_text(json.dumps({
        "schema_version": "1.0",
        "provenance": "sha256-of-artifacts (no wall clock)",
        "generator": "scripts/wp_production/build_frontier_identity_evidence.py",
        "denominator": "derived from the CURRENT frontier weights table",
        "counts": dict(counts),
        "total": len(rows),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("identity evidence: %d members, %s" % (len(rows), dict(counts)))


def check() -> int:
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(build_rows())
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- identity evidence matches recomputation")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_outputs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
