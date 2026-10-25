#!/usr/bin/env python
# INDEPENDENT Stage-1 recomputation (read-only). Does NOT import the repo script.
# Replicates the documented logic from scripts/wp_production/build_sampling_audit_3to6.py
# using csv.DictReader / json, then compares against the on-disk products.
from __future__ import annotations
import csv, json, hashlib
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
SAMPLING = REPO / "outputs" / "physics_completion" / "sampling"
LI_SCREEN = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
LI_ROUND2 = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_round2_exec_index.json"
CONFORMERS = SAMPLING / "sampling_conformer_set.csv"
STRUCTURES = ENS / "production_ensemble_structures.csv"
EXEC_CSV = LI_ROUND2.parent / "li_motif_round2_exec.csv"
OUT_CSV = SAMPLING / "sampling_audit_3to6.csv"
OUT_MD = SAMPLING / "sampling_audit_3to6.md"
OUT_INDEX = SAMPLING / "sampling_audit_index.json"

AUDIT_MOLECULES = ("EMC", "DEC", "DME", "TMP")
STATES = ("M", "M_plus", "LiM_plus", "LiM_2plus")
LI_STATES = ("LiM_plus", "LiM_2plus")
WINDOW_KCAL = 6.0
KJ_PER_KCAL = 4.184
ROUND2_CEILING = 6
ROUND1_CAP = 3

def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def free_pool_counts():
    counts = {}
    if not CONFORMERS.is_file():
        return counts
    rows = list(csv.DictReader(CONFORMERS.open(encoding="utf-8")))
    for r in rows:
        name = r.get("name", "")
        if name not in AUDIT_MOLECULES:
            continue
        rel = num(r.get("rel_kcal"))
        if rel is None or rel > WINDOW_KCAL:
            continue
        key = (name, r.get("state", ""))
        window, round1 = counts.get(key, (0, 0))
        counts[key] = (window + 1, round1 + (1 if str(r.get("selected_round1", "")).strip().lower() == "true" else 0))
    return counts

def li_pool_counts():
    counts = {}
    if not LI_SCREEN.is_file():
        return counts
    doc = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
    window_kj = WINDOW_KCAL * KJ_PER_KCAL
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        if name not in AUDIT_MOLECULES:
            continue
        kept = leg.get("kept") or []
        inside = [k for k in kept
                  if num(k.get("energy_rel_kj")) is not None
                  and num(k.get("energy_rel_kj")) <= window_kj
                  and k.get("status") == "ok"
                  and k.get("_intact", True)]
        counts[(name, leg.get("state", ""))] = len(inside)
    return counts

def li_round2_counts():
    out = {}
    if not LI_ROUND2.is_file():
        return out
    doc = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
    want = doc.get("exec_csv_sha256")
    exec_csv = LI_ROUND2.parent / str(doc.get("exec_csv", "")).split("/")[-1]
    hash_ok = None
    if want:
        if not exec_csv.is_file():
            hash_ok = ("MISSING", str(exec_csv))
        else:
            hash_ok = ("MATCH" if sha256_file(exec_csv) == want else "MISMATCH", want)
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        if name not in AUDIT_MOLECULES:
            continue
        out[(name, leg.get("state", ""))] = {
            "status": leg.get("status", ""),
            "round1_kept": int(leg.get("round1_kept_motifs") or 0),
            "measured_ceiling": int(leg.get("measured_ceiling") or 0),
            "new_basins": int(leg.get("new_independent_basins") or 0),
            "registered_bound": int(leg.get("round2_ceiling_upper_bound") or 0),
            "parents_used": len(leg.get("parents_used") or []),
            "parents_registered": int(leg.get("parents_registered") or 0),
            "collapsed": int(leg.get("collapsed_onto_round1") or 0),
        }
    return out, hash_ok

def production_members():
    counts = {}
    if not STRUCTURES.is_file():
        return counts
    for r in csv.DictReader(STRUCTURES.open(encoding="utf-8")):
        if r["member_role"] != "primary":
            continue
        counts[(r["name"], r["slot"])] = 1
    return counts

def compute_rows():
    free = free_pool_counts()
    li = li_pool_counts()
    li2, hash_ok = li_round2_counts()
    primaries = production_members()
    rows = []
    for name in AUDIT_MOLECULES:
        for state in STATES:
            measured = li2.get((name, state)) if state in LI_STATES else None
            measured_note = ""
            if state in LI_STATES:
                pool = li.get((name, state), 0)
                pool_kind = "li_motif"
                needs_motif_search = pool < ROUND2_CEILING
                if measured is not None and measured["status"] == "executed":
                    pool = max(pool, measured["measured_ceiling"])
                    pool_kind = "li_motif_round2_measured"
                    needs_motif_search = False
                    measured_note = ("; round-2 search measured %d independent minima "
                                     "(%d new, %d collapsed onto round-1, %d/%d parents verified)"
                                     % (measured["measured_ceiling"], measured["new_basins"],
                                        measured["collapsed"], measured["parents_used"],
                                        measured["parents_registered"]))
                elif measured is not None:
                    needs_motif_search = False
                    measured_note = ("; round-2 search could not run: 0 of %d registered parents "
                                     "passed hash verification, so the pool stays at the round-1 "
                                     "count (not padded, not replaced)"
                                     % measured["parents_registered"])
            else:
                pool = free.get((name, state), (0, 0))[0]
                pool_kind = "free_conformer"
                needs_motif_search = False
            if state not in LI_STATES:
                round1 = free.get((name, state), (0, 0))[1]
            elif measured is not None and measured["status"] == "executed":
                round1 = min(measured["round1_kept"], pool)
            else:
                round1 = min(ROUND1_CAP, pool)
            ceiling = min(ROUND2_CEILING, pool)
            have_primary = 1 if (name, state) in primaries else 0
            executable = ceiling > round1 or (ceiling >= ROUND2_CEILING)
            if pool >= ROUND2_CEILING:
                status = "executable"
            elif executable:
                status = "executable_partial"
            else:
                status = "sampling_limited"
            rows.append({
                "name": name, "state": state, "pool_kind": pool_kind,
                "round1_structures": str(round1),
                "pool_independent_minima": str(pool),
                "round2_ceiling": str(ceiling),
                "has_primary": str(have_primary),
                "extension_available": "true" if ceiling > round1 else "false",
                "needs_second_round_motif_search": "true" if needs_motif_search else "false",
                "status": status,
            })
    return rows, hash_ok, li2

def read_product_csv():
    return list(csv.DictReader(OUT_CSV.open(encoding="utf-8")))

def main():
    print("=" * 70)
    print("SECTION A: exec CSV hash check (script raises SystemExit if mismatch)")
    rows, hash_ok, li2 = compute_rows()
    print("exec_csv =", EXEC_CSV)
    print("exec_csv exists =", EXEC_CSV.is_file())
    print("hash check =", hash_ok)

    print("=" * 70)
    print("SECTION B: my independent recomputation of the 16 rows")
    hdr = ["name","state","pool_kind","round1","pool","ceiling","ext_avail","needs2nd","status"]
    print(" | ".join(hdr))
    for r in rows:
        print(" | ".join([r["name"], r["state"], r["pool_kind"], r["round1_structures"],
                          r["pool_independent_minima"], r["round2_ceiling"],
                          r["extension_available"], r["needs_second_round_motif_search"], r["status"]]))

    print("=" * 70)
    print("SECTION C: my by_status tally")
    tally = {}
    for r in rows:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print(tally)
    print("total states =", len(rows))

    print("=" * 70)
    print("SECTION D: my Li pool (pool_independent_minima) per leg + round2 detail")
    for (name, state) in sorted(li2.keys()):
        m = li2[(name, state)]
        row = next(r for r in rows if r["name"] == name and r["state"] == state)
        print(f"{name}|{state}: pool={row['pool_independent_minima']} round1={row['round1_structures']} "
              f"pool_kind={row['pool_kind']} status={row['status']} || round2: leg_status={m['status']} "
              f"round1_kept={m['round1_kept']} measured_ceiling={m['measured_ceiling']} "
              f"new={m['new_basins']} collapsed={m['collapsed']} parents={m['parents_used']}/{m['parents_registered']}")

    print("=" * 70)
    print("SECTION E: any leg NOT executed (parent-hash-fail / held-at-round1)?")
    not_exec = [(k, v["status"]) for k, v in li2.items() if v["status"] != "executed"]
    print("non-executed legs:", not_exec if not_exec else "NONE (all 8 executed)")

    print("=" * 70)
    print("SECTION F: product CSV (on disk) tally + field-by-field vs my recompute")
    prod = read_product_csv()
    ptally = {}
    for r in prod:
        ptally[r["status"]] = ptally.get(r["status"], 0) + 1
    print("product by_status =", ptally, " total =", len(prod))
    cmp_fields = ["pool_kind","round1_structures","pool_independent_minima","round2_ceiling",
                  "has_primary","extension_available","needs_second_round_motif_search","status"]
    diffs = 0
    for mine, pr in zip(rows, prod):
        for f in cmp_fields:
            if mine[f] != pr.get(f, ""):
                diffs += 1
                print(f"DIFF {mine['name']}|{mine['state']} field={f}: mine={mine[f]!r} product={pr.get(f)!r}")
    print("total field diffs (mine vs product) =", diffs)

    print("=" * 70)
    print("SECTION G: product index.json by_status")
    idx = json.loads(OUT_INDEX.read_text(encoding="utf-8"))
    print("index states =", idx.get("states"), " index by_status =", idx.get("by_status"))
    print("index generated_at_utc =", idx.get("generated_at_utc"))

if __name__ == "__main__":
    main()
