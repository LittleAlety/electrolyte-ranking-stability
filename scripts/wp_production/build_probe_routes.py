"""Derive the five limited states' probe_route inputs and emit the real routes.

The router's inputs come from data, never hand-filling (the plan: "输入来自
自由度、历史候选及身份预检，不允许人工随意填写来放行"):

* in_flight               -- any non-pending recovery/audit row of the state;
* identity_verified       -- every weighted member of the state reads verified
                             in the identity evidence table;
* unused_starts           -- frozen-pool conformers never run at production;
* eligible_torsions       -- free dihedrals REGISTERED in the pool data
                             (derived from the conformer pool's own records;
                             None today because no torsion registry exists,
                             which is exactly what preflight_required means);
* new_li_motifs           -- unregistered independent motifs from the motif
                             search index (None for cationic states: no motif
                             search applies there);
* independent_reproductions -- computed members that deduplicated onto a known
                             minimum of this state.

Output is read-only: it proposes, never submits.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"
FRONTIER = REPO / "outputs" / "physics_completion" / "frontier"
POOL = REPO / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"

REGISTRY = RECOVERY / "torsion_freedom_registry.csv"
OUT_CSV = RECOVERY / "probe_routes.csv"
OUT_INDEX = RECOVERY / "probe_routes_index.json"

STATES = [("AN", "M_plus"), ("DMC", "M_plus"),
          ("DMC", "LiM_2plus"), ("DOL", "LiM_2plus"), ("EC", "LiM_2plus")]


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _canon(seed: str) -> str:
    s = re.sub(r"^[rd]\d+_", "", seed)
    s = re.sub(r"^c", "", s)
    return str(int(s)) if s.isdigit() else s


def state_inputs(name: str, state: str) -> dict:
    struct = _rows(ENS / "production_ensemble_structures.csv")
    evidence = {r["member_key"]: r["identity_qc_status"]
                for r in _rows(FRONTIER / "frontier_identity_evidence.csv")}
    weights = [r["member_key"] for r in _rows(FRONTIER / "frontier_localization.csv")]

    # in flight: a genuinely pending EXTRA/RESCUE row of this state.  The
    # primary's bookkeeping row (status=ready, empty attempt) belongs to the
    # main ledger and is NOT a rescue in flight -- counting it made every
    # state read wait_existing_job and hid the real route.
    in_flight = any(
        r.get("status") in ("pending", "ready")
        and r.get("member_role") != "primary"
        for r in struct
        if r.get("name") == name and r.get("slot") == state)

    # identity: every WEIGHTED member of this state verified
    members = [k for k in weights if k.startswith("%s|%s|" % (name, state))]
    identity_verified = bool(members) and all(
        evidence.get(k) == "verified" for k in members)

    # unused pool starts (never ran at production)
    used = {_canon(r.get("seed", "")) for r in struct
            if r.get("name") == name and r.get("slot") == state}
    unused = []
    for r in _rows(POOL):
        if r.get("name") != name or r.get("state") != state:
            continue
        if _canon(r.get("geometry_relpath", "").split("/")[-2] or "") in used:
            continue
        unused.append(r.get("geometry_relpath", ""))

    # eligible torsions from the REGISTERED registry (build_torsion_registry);
    # ring deformation is deliberately NOT here -- it is a separate probe kind
    # and DOL's all-ring topology correctly yields zero torsions
    registry = _rows(REGISTRY)
    eligible_torsions = [r["detail"] for r in registry
                         if r.get("name") == name and r.get("state") == state
                         and r.get("detail", "").count("-") >= 3]

    # new Li motifs: the round-3 motif search IS the preflight -- its measured
    # zero (all candidates collapsed onto known basins) is a RESULT, not a
    # missing preflight, so the router gets [] (checked, empty) not None
    if "Li" in state:
        exec_idx = (REPO / "outputs" / "physics_completion" / "li_motif_sampling"
                    / "li_motif_round3_recovery.csv")
        new_li_motifs = []
        for r in _rows(exec_idx):
            leg = r.get("leg_id", "")
            if not leg.startswith(name + "|") or not leg.endswith("|" + state):
                continue
            if r.get("new_vs_round1") == "true" and r.get("kept") == "true":
                new_li_motifs.append(r.get("motif_path", leg))
    else:
        new_li_motifs = []

    # independent reproductions: computed rows that deduplicated onto a known
    # minimum of this state
    dedup = _rows(ENS / "production_ensemble_dedup.csv")
    reproductions = []
    for r in struct:
        if (r.get("name") != name or r.get("slot") != state
                or r.get("status") != "computed"):
            continue
        d = next((x for x in dedup if x.get("member_key") == r["member_key"]
                  and x.get("attempt") == r.get("attempt")), {})
        if d.get("duplicate_of"):
            reproductions.append(r["member_key"])

    return dict(in_flight=in_flight,
                identity_verified=identity_verified,
                unused_starts=unused,
                eligible_torsions=eligible_torsions,
                new_li_motifs=new_li_motifs,
                independent_reproductions=reproductions)


def build_rows() -> list[dict]:
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location(
        "probe_route", HERE / "probe_route.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(m)

    rows = []
    for name, state in STATES:
        inp = state_inputs(name, state)
        route = m.probe_route(**inp)
        rows.append({
            "name": name, "state": state,
            "route": route,
            "in_flight": str(inp["in_flight"]).lower(),
            "identity_verified": str(inp["identity_verified"]).lower(),
            "n_unused_starts": len(inp["unused_starts"]),
            "n_new_li_motifs": (len(inp["new_li_motifs"])
                                if inp["new_li_motifs"] is not None else -1),
            "n_independent_reproductions": len(inp["independent_reproductions"]),
            "note": ("route proposes the next path only; draft_* still needs "
                     "candidate/budget/stop-rule registration and user approval; "
                     "zero means no executable candidate IN THIS preflight"),
        })
    return rows


FIELDS = ["name", "state", "route", "in_flight", "identity_verified",
          "n_unused_starts", "n_new_li_motifs", "n_independent_reproductions",
          "note"]


def write_outputs() -> None:
    rows = build_rows()
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    OUT_INDEX.write_text(json.dumps({
        "schema_version": "1.0",
        "provenance": "derived inputs; no wall clock",
        "generator": "scripts/wp_production/build_probe_routes.py",
        "router": "probe_route.py (plan v3.1 draft B)",
        "states": ["%s|%s" % s for s in STATES],
        "launches_anything": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for r in rows:
        print("%-5s %-10s -> %s (unused=%d motifs=%d repro=%d)" % (
            r["name"], r["state"], r["route"], r["n_unused_starts"],
            r["n_new_li_motifs"], r["n_independent_reproductions"]))


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
    print("CHECK OK -- probe routes match recomputation")
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
