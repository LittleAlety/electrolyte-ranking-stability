"""P4 · 五态隔离绑定器（Plan 首批第 4 项后半：五态覆盖隔离绑定）。

只读输入、隔离输出；仅消费冻结/审定谱系：
  * freeze.json 列出的 4 个输入逐个 SHA256 复核（不符即拒）
  * coverage_recheck.json（五态状态原文，逐字保留）
  * sampling_conformer_set.csv / sampling_index.json（范围证据，记哈希）
  * production_ensemble_structures.csv（原候选登记，须与冻结哈希一致）
显式排除 sampling_audit_index.json：其记录的结构账本哈希已过期
（recorded 3f2c692d… vs actual 3a795ce8…），只做"过期自检"，绝不消费其状态结论。

输出仅写本目录 binding_package.json：
  * 无 resolved 键（自检断言）、不改 coverage_status、不写任何正式路径
  * 每态 binding_status=ISOLATED_CANDIDATE_BINDING；身份核验仍
    PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW → 交数据分析

用法：python p4_five_state_binding.py [--negative-selftest]
"""
import csv
import hashlib
import io
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent                 # evidence/p4_five_state_binding/
REPO = Path(__file__).resolve().parents[5]             # .../电解液溶剂HB-Code
FREEZE = REPO / "docs/handoffs/strict_rebuild_20261103/verification_20261103/freeze.json"
RECHECK = REPO / "docs/handoffs/strict_rebuild_20261103/verification_20261103/coverage_recheck.json"
SAMPLING_DIR = REPO / "outputs/physics_completion/sampling"
CONFORMER_SET = SAMPLING_DIR / "sampling_conformer_set.csv"
SAMPLING_INDEX = SAMPLING_DIR / "sampling_index.json"
AUDIT_INDEX = SAMPLING_DIR / "sampling_audit_index.json"
ENSEMBLES = REPO / "outputs/physics_completion/ensembles/production_ensemble_structures.csv"
OUT = HERE / "binding_package.json"

FIVE = ["DEC|LiM_2plus", "DEC|M_plus", "GBL|LiM_plus", "PC|M_plus", "TMP|M"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refuse(msg: str):
    raise SystemExit("P4 REFUSING: " + msg)


def load_sources():
    """Read + hash-verify every adjudicated source; refuse on any drift."""
    if not FREEZE.is_file():
        refuse("freeze.json missing; no adjudicated baseline to bind against")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    verified = {}
    for rel, expect in freeze["input_sha256"].items():
        p = REPO / rel
        if not p.is_file():
            refuse("frozen input missing: %s" % rel)
        actual = sha256(p)
        if actual != expect:
            refuse("frozen input drifted: %s expected %s got %s" % (rel, expect[:16], actual[:16]))
        verified[rel] = {"sha256": actual, "bytes": p.stat().st_size, "role": "frozen_input"}
    for rel, p, role in [
        ("verification_20261103/coverage_recheck.json", RECHECK, "adjudicated_recheck"),
        ("sampling/sampling_conformer_set.csv", CONFORMER_SET, "range_evidence"),
        ("sampling/sampling_index.json", SAMPLING_INDEX, "range_evidence"),
    ]:
        if not p.is_file():
            refuse("required source missing: %s" % p)
        verified[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size, "role": role}
    return freeze, verified


def stale_audit_selfcheck(verified: dict) -> dict:
    """sampling_audit_index: prove it is STILL stale, then exclude it.

    We read only its recorded input hash -- never its status conclusions.
    If the premise (stale) no longer holds, refuse instead of silently proceeding.
    """
    if not AUDIT_INDEX.is_file():
        entry = {"path": str(AUDIT_INDEX.relative_to(REPO)), "reason": "absent"}
        verified["sampling/sampling_audit_index.json"] = {"sha256": None, "bytes": None, "role": "EXCLUDED_absent"}
        return entry
    doc = json.loads(AUDIT_INDEX.read_text(encoding="utf-8"))
    recorded = (doc.get("inputs") or {}).get("production_ensemble_structures.csv")
    actual = sha256(ENSEMBLES)
    if recorded is None:
        refuse("sampling_audit_index has no recorded ensemble hash; cannot prove staleness, "
               "and must not be consumed unverified")
    if recorded == actual:
        refuse("sampling_audit_index staleness premise broken (recorded hash now matches); "
               "re-adjudication required before this source may be used or excluded")
    verified["sampling/sampling_audit_index.json"] = {
        "sha256": sha256(AUDIT_INDEX), "bytes": AUDIT_INDEX.stat().st_size,
        "role": "EXCLUDED_stale", "recorded_ensemble_hash": recorded, "actual_ensemble_hash": actual,
    }
    return {"path": str(AUDIT_INDEX.relative_to(REPO)),
            "reason": "stale structure-ledger hash (remote_closure README:43); "
                      "status conclusions NOT consumed; staleness re-proven this run",
            "recorded_production_ensemble_structures_csv": recorded,
            "actual_production_ensemble_structures_csv": actual}


def bind_states(verified: dict) -> list:
    recheck = json.loads(RECHECK.read_text(encoding="utf-8"))
    by_key = {e["state_key"]: e for e in recheck}
    missing = [s for s in FIVE if s not in by_key]
    if missing:
        refuse("coverage_recheck lacks states: %s" % missing)

    ens = list(csv.DictReader(ENSEMBLES.open(encoding="utf-8-sig")))
    conf = list(csv.DictReader(CONFORMER_SET.open(encoding="utf-8-sig")))
    sidx = json.loads(SAMPLING_INDEX.read_text(encoding="utf-8"))
    motif = [e for e in sidx.get("li_motif_sampling", []) if isinstance(e, dict)]

    out = []
    for key in FIVE:
        entry = by_key[key]
        reps = entry.get("qualified_representatives") or []
        if len(reps) != 1:
            refuse("%s has %d qualified representatives; binding needs exactly the adjudicated one"
                   % (key, len(reps)))
        rep_key = reps[0]
        rep_rows = [r for r in ens if r["member_key"] == rep_key]
        if not rep_rows:
            refuse("%s representative %s absent from the frozen ensemble registry" % (key, rep_key))
        rep = rep_rows[0]
        name, slot = key.split("|", 1)

        # range evidence: free conformer pool vs Li-motif screening
        if slot in ("M", "M_plus"):
            rows = [r for r in conf if r["name"] == name and r["state"] == slot]
            kind = "free_conformer_pool"
        else:
            rows = [e for e in motif if e.get("name") == name and e.get("state") == slot]
            kind = "li_motif_screening"
        if not rows:
            refuse("%s: no range evidence rows in adjudicated sources (kind=%s)" % (key, kind))
        scope = sidx.get("scope")

        start_ref = None
        if kind == "li_motif_screening":
            note = rows[0].get("note", "")
            start_ref = note  # carries "parent sha256 …" = 原起点几何指针
        else:
            start_ref = "source_index=%s (conformer_set row provenance)" % rows[0].get("source_index")

        out.append({
            "state_key": key,
            "status_verbatim": entry.get("status"),
            "zero_compute_action_verbatim": entry.get("zero_compute_action"),
            "reason_verbatim": entry.get("reason"),
            "old_claim_verbatim": entry.get("old_claim"),
            "qualified_representative": {
                "member_key": rep_key, "slot": rep.get("slot"), "mol_id": rep.get("mol_id"),
                "seed": rep.get("seed"), "member_role": rep.get("member_role"),
                "source_kind": rep.get("source_kind"), "attempt": rep.get("attempt"),
                "charge": rep.get("charge"), "multiplicity": rep.get("multiplicity"),
            },
            "membership_rows_in_registry": sum(1 for r in ens if r["member_key"].startswith(key + "|")),
            "range_binding": {
                "kind": kind, "source_rows": len(rows), "scope_ref": scope,
                "start_geometry_ref": start_ref,
                "verdict": rows[0].get("verdict") or rows[0].get("status"),
            },
            "identity_review": "PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW",
            "binding_status": "ISOLATED_CANDIDATE_BINDING",
            "coverage_status": "NOT_TOUCHED",
            "production_written": False,
            "missing": ["independent identity & coverage adjudication (hand to data analysis)",
                        "registered_starts / coverage_review_id not bound in production by this run"],
        })
    return out


def build_package() -> dict:
    freeze, verified = load_sources()
    excluded = stale_audit_selfcheck(verified)
    states = bind_states(verified)
    return {
        "schema": "five_state_isolated_binding/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "ISOLATED_READ_ONLY",
        "plan_authority": "plan batch1 item4 isolation exercise; NO production write, "
                          "NO new computation, NO resolved fill",
        "sources": verified,
        "excluded_sources": [excluded],
        "states": states,
        "handovers": [
            "identity & coverage adjudication for all five states -> data analysis",
            "registered_starts/coverage_review_id production binding -> requires approval, not done here",
        ],
    }


def selfcheck(pkg: dict):
    txt = json.dumps(pkg, ensure_ascii=False)
    assert '"resolved"' not in txt, "resolved key must never be written"
    assert pkg["mode"] == "ISOLATED_READ_ONLY"
    assert len(pkg["states"]) == 5
    assert all(s["binding_status"] == "ISOLATED_CANDIDATE_BINDING" for s in pkg["states"])
    assert all(s["production_written"] is False for s in pkg["states"])
    assert all(s["coverage_status"] == "NOT_TOUCHED" for s in pkg["states"])
    assert pkg["excluded_sources"] and "stale" in pkg["excluded_sources"][0]["reason"]


def negative_selftest():
    """Refusal paths, exercised in a temp copy -- never against the real repo."""
    global REPO, FREEZE, RECHECK, CONFORMER_SET, SAMPLING_INDEX, AUDIT_INDEX, ENSEMBLES
    real = (REPO, FREEZE, RECHECK, CONFORMER_SET, SAMPLING_INDEX, AUDIT_INDEX, ENSEMBLES)
    try:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            # case 1: missing freeze -> refuse
            REPO, FREEZE = t, t / "freeze.json"
            try:
                load_sources(); raise AssertionError("should have refused")
            except SystemExit as e:
                assert "P4 REFUSING" in str(e), e
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            # case 2: frozen input drift -> refuse
            (t / "a.json").write_text("{}", encoding="utf-8")
            fz = {"input_sha256": {"a.json": "0" * 64}}
            (t / "freeze.json").write_text(json.dumps(fz), encoding="utf-8")
            for name in ("b.json", "c.csv", "d.json"):
                (t / name).write_text("x", encoding="utf-8")
            REPO, FREEZE = t, t / "freeze.json"
            RECHECK, CONFORMER_SET = t / "b.json", t / "c.csv"
            SAMPLING_INDEX, AUDIT_INDEX, ENSEMBLES = t / "d.json", t / "nope.json", t / "c.csv"
            try:
                load_sources(); raise AssertionError("should have refused")
            except SystemExit as e:
                assert "drifted" in str(e), e
        print("negative_selftest: OK (missing freeze + drifted frozen input both refused)")
    finally:
        REPO, FREEZE, RECHECK, CONFORMER_SET, SAMPLING_INDEX, AUDIT_INDEX, ENSEMBLES = real


def main():
    if "--negative-selftest" in sys.argv:
        negative_selftest()
        return 0
    pkg = build_package()
    selfcheck(pkg)
    OUT.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selfcheck(json.loads(OUT.read_text(encoding="utf-8")))
    print("wrote", OUT)
    print("states =", len(pkg["states"]), "| sources =", len(pkg["sources"]),
          "| excluded =", len(pkg["excluded_sources"]))
    for s in pkg["states"]:
        print("  ", s["state_key"], "|", s["qualified_representative"]["member_key"],
              "|", s["range_binding"]["kind"], "rows=", s["range_binding"]["source_rows"],
              "|", s["binding_status"])
    print("selfcheck OK (no resolved key, isolation intact)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
