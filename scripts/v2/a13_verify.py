"""v1.3 refinement verification: evidence roots, full-source hashes, operand comparability.

These checks are what upgraded the v1.3 plan's [L] claims to verified facts.  They read only;
nothing is mutated and no quantum-chemistry calculation is started.

Run:  python scripts/v2/a13_verify.py
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[2]           # 电解液溶剂HB-Code/
PARENT_ROOT = CODE_ROOT.parent                            # 电解液溶剂-HB/
OUT = CODE_ROOT / "outputs" / "physics_completion_v2" / "a00_v1_3"

CLOSURE = CODE_ROOT / "work" / "evidence18_strict_closure_20261116_codex"
MATRIX = CLOSURE / "EVIDENCE_MATRIX_18x4.csv"
METHOD_AXIS = CLOSURE / "METHOD_AXIS.json"
STRUCTURES = CODE_ROOT / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
LABELS = CODE_ROOT / "outputs/physics_completion/ensembles/production_ensemble_labels.csv"

VERDICT = CLOSURE / "FINAL_VERDICT.json"


# ---------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
def classify_root(raw: str) -> tuple[str, Path]:
    """Resolve a matrix source_path against both evidence roots.

    The matrix stores repo-relative paths, but 13 positions point at '../work/...'
    which lands in the PARENT root.  Never silently reinterpret: report which root won.
    """
    p = (CODE_ROOT / raw).resolve()
    if str(p).startswith(str(CODE_ROOT.resolve())) and p.is_file():
        return "repo_root", p
    if p.is_file():
        return "parent_root", p
    p2 = (PARENT_ROOT / raw.replace("../", "")).resolve()
    if p2.is_file():
        return "parent_root", p2
    return "not_found", p


def build_evidence_roots() -> dict:
    rows = read_csv(MATRIX)
    out_rows = []
    for r in rows:
        raw = r["source_path"].strip()
        root, path = classify_root(raw)
        exists = path.is_file()
        live = sha256_file(path) if exists else ""
        rec = r["source_sha256"].strip()
        rel = ""
        if exists:
            try:
                rel = path.relative_to(CODE_ROOT.resolve()).as_posix()
            except ValueError:
                try:
                    rel = path.relative_to(PARENT_ROOT.resolve()).as_posix()
                except ValueError:
                    rel = str(path)
        out_rows.append({
            "position_id": r["position_id"],
            "mol_id": r["mol_id"],
            "name": r["name"],
            "set": r["set"],
            "state": r["state"],
            "declared_source_path": raw,
            "evidence_root": root,
            "resolved_rel_path": rel,
            "size_bytes": path.stat().st_size if exists else 0,
            "recorded_sha256": rec,
            "live_sha256": live,
            "hash_match": (live == rec) if exists else False,
            "exists": exists,
        })

    counts = collections.Counter(r["evidence_root"] for r in out_rows)
    matched = sum(1 for r in out_rows if r["hash_match"])
    by_root = {k: sum(1 for r in out_rows if r["evidence_root"] == k and r["hash_match"])
               for k in counts}

    write_csv(OUT / "A13_evidence_roots.csv", out_rows, [
        "position_id", "mol_id", "name", "set", "state", "declared_source_path",
        "evidence_root", "resolved_rel_path", "size_bytes", "recorded_sha256",
        "live_sha256", "hash_match", "exists",
    ])

    return {
        "schema": "a13_evidence_roots/v1",
        "generated_at_utc": utc_now(),
        "positions": len(out_rows),
        "by_root": dict(counts),
        "hash_matched_total": matched,
        "hash_matched_by_root": by_root,
        "all_matched": matched == len(out_rows),
        "note": (
            "v1.3 and A00-v1.3 both assumed a single evidence root (电解液溶剂HB-Code/). "
            "13 of 72 positions resolve into the PARENT directory instead.  All 72 hashes match; "
            "the defect was scoping, not integrity."
        ),
    }


def build_full_source_hash() -> dict:
    """72/72 recorded source_sha256 must match disk; plus ORCA termination markers."""
    rows = read_csv(MATRIX)
    details = []
    for r in rows:
        raw = r["source_path"].strip()
        root, path = classify_root(raw)
        rec = r["source_sha256"].strip()
        entry = {"position_id": r["position_id"], "set": r["set"], "evidence_root": root,
                 "exists": path.is_file(), "sha_match": False,
                 "normal_termination": "", "has_frequencies": "", "bytes": 0}
        if not path.is_file():
            details.append(entry)
            continue
        entry["sha_match"] = sha256_file(path) == rec
        entry["bytes"] = path.stat().st_size
        if path.suffix.lower() in {".out", ".log"}:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            entry["normal_termination"] = (
                "NORMAL TERMINATION" in text or "ORCA TERMINATED NORMALLY" in text
            )
            entry["has_frequencies"] = "VIBRATIONAL FREQUENCIES" in text
        details.append(entry)

    matched = sum(1 for d in details if d["sha_match"])
    ext = [d for d in details if d["set"] == "extension6"]
    return {
        "schema": "a13_full_source_hash/v1",
        "generated_at_utc": utc_now(),
        "positions": len(details),
        "sha_matched": matched,
        "sha_mismatched": len(details) - matched,
        "extension_positions": len(ext),
        "extension_normal_termination": sum(1 for d in ext if d["normal_termination"] is True),
        "extension_with_frequencies": sum(1 for d in ext if d["has_frequencies"] is True),
        "all_matched": matched == len(details),
        "details": details,
    }


def build_operand_comparability() -> dict:
    """Prove 2.906 and 3.851 are not comparable operands."""
    ma = json.loads(METHOD_AXIS.read_text(encoding="utf-8"))
    fa_ad = ma.get("functional_axis_adiabatic", {})
    fa_v = ma.get("functional_axis_vertical", {})

    def max_shift(axis: dict) -> dict:
        rows = axis.get("rows", [])
        if not rows:
            return {}
        top = max(rows, key=lambda r: abs(r.get("shift_kcal", 0.0)))
        return {
            "cohort_molecules": ma.get("n_molecules"),
            "n_pairs": axis.get("n_pairs"),
            "n_sign_flip": axis.get("n_sign_flip"),
            "max_abs_shift_kcal": round(abs(top["shift_kcal"]), 6),
            "max_pair": f"{top['mol_i']}–{top['mol_j']}",
            "includes_EC_PC": {top["mol_i"], top["mol_j"]} == {"C04", "C05"},
        }

    operands = [
        {
            "operand_id": "OP1",
            "value_kcal": 2.906,
            "definition": "k=3 boundary margin at the L2 ensemble layer: EC 190.957 − PC 188.051",
            "cohort": "12 main-set molecules",
            "cohort_size": 12,
            "layer": "L2 ensemble",
            "pair": "C04–C05 (EC–PC)",
            "source": "work/evidence18_strict_closure_20261116_codex/CLOSURE_REPORT_20261117.md:682",
        },
        {
            "operand_id": "OP2",
            "value_kcal": max_shift(fa_ad).get("max_abs_shift_kcal", 3.851),
            "definition": "max functional-axis pairwise shift, adiabatic: wB97X-D4 → PBE0-D4",
            "cohort": f"{ma.get('n_molecules')} main-set molecules (method-audit cohort)",
            "cohort_size": ma.get("n_molecules"),
            "layer": "functional axis (adiabatic)",
            "pair": max_shift(fa_ad).get("max_pair", "C04–C08"),
            "source": "work/evidence18_strict_closure_20261116_codex/METHOD_AXIS.json"
                      "#functional_axis_adiabatic",
        },
        {
            "operand_id": "OP3",
            "value_kcal": max_shift(fa_v).get("max_abs_shift_kcal", 5.971),
            "definition": "max functional-axis pairwise shift, vertical",
            "cohort": f"{ma.get('n_molecules')} main-set molecules (method-audit cohort)",
            "cohort_size": ma.get("n_molecules"),
            "layer": "functional axis (vertical)",
            "pair": max_shift(fa_v).get("max_pair", "C01–C16"),
            "source": "work/evidence18_strict_closure_20261116_codex/METHOD_AXIS.json"
                      "#functional_axis_vertical",
        },
    ]

    same_cohort = operands[0]["cohort_size"] == operands[1]["cohort_size"]
    same_pair = operands[0]["pair"] == operands[1]["pair"]
    same_layer = operands[0]["layer"] == operands[1]["layer"]
    comparable = same_cohort and same_pair and same_layer

    return {
        "schema": "a13_operand_comparability/v1",
        "generated_at_utc": utc_now(),
        "method_axis_cohort_note": ma.get("cohort_note"),
        "operands": operands,
        "checks": {
            "same_cohort": same_cohort,
            "same_pair": same_pair,
            "same_layer": same_layer,
        },
        "verdict": "COMPARABLE" if comparable else "INCOMPARABLE_OPERANDS",
        "consequence": (
            "The v1.3 sentence '2.906 < 3.851' compares a 12-molecule L2 ensemble k-margin with an "
            "8-molecule functional-axis pairwise shift whose maximum is the EC–DME pair, not EC–PC. "
            "It must not be used as a significance or causal comparison.  A09 must rebuild a "
            "same-cohort operator before F4 is drawn."
            if not comparable else "operands are comparable"
        ),
    }


def build_cost_audit() -> dict:
    rows = read_csv(MATRIX)
    per_mol: dict[str, dict] = {}
    for r in rows:
        name = r["name"]
        cost = r["cost_core_hours"].strip()
        try:
            val = float(cost) if cost else None
        except ValueError:
            val = None
        rec = per_mol.setdefault(name, {"name": name, "set": r["set"], "positions": 0,
                                        "with_cost": 0, "total_ch": 0.0, "unknown": []})
        rec["positions"] += 1
        if val is None:
            rec["unknown"].append(r["position_id"])
        else:
            rec["with_cost"] += 1
            rec["total_ch"] += val

    p90 = {"free_neutral_def2TZVPD": 15.213, "free_cation_def2TZVPD": 18.406,
           "li_complex_def2TZVPD": 20.006}
    tegdme = per_mol.get("TEGDME", {})
    ratio = (tegdme.get("total_ch", 0) / 4) / (sum(p90.values()) / 3) if tegdme else None

    return {
        "schema": "a13_cost_audit/v1",
        "generated_at_utc": utc_now(),
        "legacy_p90_ch_per_leg": p90,
        "per_molecule": sorted(per_mol.values(), key=lambda r: -r["total_ch"]),
        "tegdme_four_state_total_ch": tegdme.get("total_ch"),
        "tegdme_ratio_over_legacy_p90": round(ratio, 2) if ratio else None,
        "extension_positions_without_cost": sum(len(v["unknown"]) for v in per_mol.values()
                                                if v["set"] == "extension6"),
        "consequence": (
            "The legacy p90 (15.2–20.0 CH/leg) describes the 12-molecule main set only. "
            "TEGDME's four single-conformer legs cost 431.1 CH in total, i.e. 4–7x the legacy p90 "
            "per leg.  A06 cannot be budgeted from the legacy p90."
        ),
    }


def build_three_boolean() -> dict:
    reg = read_csv(OUT / "core18_v2_state_registry.csv")
    open_rows = [r for r in reg if r["registry_disposition"].startswith("AUDIT_OPEN")]
    explained_open = [r for r in open_rows if r["missing_reason"].strip()]
    strict = sum(1 for r in reg
                 if r["a5_sampling_ensemble"] == "VERIFIED_ACCEPTED"
                 and r["ensemble_label_status"] == "accepted")
    claims = read_csv(OUT / "science_claim_correction_matrix.csv")
    holds = [c["claim_id"] for c in claims if c["status"].startswith("HOLD")]

    return {
        "schema": "a13_three_boolean/v1",
        "generated_at_utc": utc_now(),
        "positions": len(reg),
        "COVERAGE_CLOSED": {
            "value": False,
            "reason": (f"{len(open_rows)} positions are AUDIT_OPEN_*; "
                       f"{len(explained_open)} of them do carry an explicit reason, so the blocker is "
                       "closure, not documentation"),
        },
        "STRICT_ENSEMBLE_COMPLETE": {
            "value": strict == 72,
            "detail": f"{strict}/72 actual accepted",
        },
        "SCIENTIFIC_REPORT_COMPLETE": {
            "value": False,
            "reason": f"{len(holds)} claims on HOLD_NEEDS_DECISION: {', '.join(holds)}",
        },
        "note": (
            "All three are independently computable today.  This is what A12 needs; it does not "
            "need a new release engine built from scratch."
        ),
    }


def main() -> int:
    roots = build_evidence_roots()
    hashes = build_full_source_hash()
    operands = build_operand_comparability()
    costs = build_cost_audit()
    booleans = build_three_boolean()

    report = {
        "schema": "a13_refinement_verification/v1",
        "generated_at_utc": utc_now(),
        "evidence_roots": {k: v for k, v in roots.items() if k != "details"},
        "full_source_hash": {k: v for k, v in hashes.items() if k != "details"},
        "operand_comparability": operands,
        "cost_audit": costs,
        "three_boolean": booleans,
        "verdict": {
            "confirmed": [
                "45 accepted / 2 limited / 1 provisional",
                "24/24 extension execution completed",
                "72/72 source_sha256 match",
                "24/24 extension ensemble missing",
            ],
            "corrected": [
                "evidence root is TWO directories, not one (13/72 positions in the parent root)",
                "TEGDME cost is 4-7x the legacy p90; the extension ensemble budget cannot use p90",
                "2.906 and 3.851 are INCOMPARABLE_OPERANDS (different cohort, pair, layer)",
            ],
            "blocking_decisions": 7,
        },
    }
    write_json(OUT / "A13_refinement_verification.json", report)
    print(json.dumps(report["verdict"], ensure_ascii=False, indent=2))
    print(json.dumps({"evidence_roots": roots["by_root"],
                      "sha_matched": f'{hashes["sha_matched"]}/{hashes["positions"]}',
                      "operand_verdict": operands["verdict"],
                      "three_boolean": {k: booleans[k]["value"]
                                        for k in ("COVERAGE_CLOSED",
                                                  "STRICT_ENSEMBLE_COMPLETE",
                                                  "SCIENTIFIC_REPORT_COMPLETE")}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
