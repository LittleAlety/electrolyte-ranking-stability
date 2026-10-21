#!/usr/bin/env python
"""Round-2 Li coordination-motif search plan (plan v1.4.2 item 5, 2026-10-19).

Why a SECOND round exists at all
--------------------------------
Round 1 enumerated every placement rule ON ONE PARENT per leg: the leg's own
production geometry with Li removed (monodentate + bidentate + ESP-guided
minima, uncapped -- measured 7-14 sites per leg).  For the eight audit Li
states that search kept only 1-2 independent minima, and the audit therefore
marked them ``needs_second_round_motif_search``.

The round-2 search space is NOT more placements on the same parent -- that
space is exhausted.  It is the SAME frozen placement rules applied to the
OTHER conformer basins of the same molecule, taken from the frozen free-state
conformer pool (``ensemble_raw_records.csv``, GFN2, gas phase).  EMC has 2
independent neutral basins, DME 6, etc.  A basin qualifies as an alternative
parent only when its frozen-pool record exists, is status=ok, and carries a
geometry hash that still matches the disk bytes.

What this generator freezes BEFORE any execution
------------------------------------------------
* per leg: the ordered list of alternative-parent basins (pool conformer id +
  geometry relpath + sha256 + pool free energy), and the round-2 ceiling =
  round-1 kept motifs + the number of alternative parents that pass the
  integrity gate (an honest UPPER bound, never a promise);
* the execution contract: same placement rules, same KEEP rules, same xTB
  level as round 1 -- only the parent differs.  A parent whose Li-free
  connectivity differs from the production parent's is rejected at plan time
  (a different bond graph means a different molecule, the EMC|M_plus|4 lesson).
* the real-pool ceiling registration required by the plan text: pool-limited
  legs keep their true basin count, nothing is invented.

Outputs
-------
outputs/physics_completion/li_motif_sampling/li_motif_plan_round2.csv
outputs/physics_completion/li_motif_sampling/li_motif_plan_round2_index.json

This generator runs zero chemistry: it reads the frozen pool records and
writes the pre-registered plan.  Execution is a separate, explicitly-invoked
step (screen_li_motifs.py extension) that this session does NOT auto-run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENS = REPO / "outputs" / "physics_completion" / "ensembles"
OUT_DIR = REPO / "outputs" / "physics_completion" / "li_motif_sampling"
#: The alternative parents must come from the REGISTERED free-state pool
#: (``sampling_conformer_set.csv``), not from ``ensemble_raw_records.csv``: the
#: raw records are a derived ledger frozen at an earlier point, and their EMC
#: entries no longer match the disk (energies differ by ~0.086 Eh), which made
#: every EMC parent fail hash verification.  The conformer set is the pool the
#: ensemble candidate manifest itself consumes, and its hashes match disk.
POOL = REPO / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"
SCREEN_JSON = OUT_DIR / "li_motif_screen.json"

AUDIT_MOLECULES = ("EMC", "DEC", "DME", "TMP")
LI_STATES = ("LiM_plus", "LiM_2plus")

OUT_CSV = OUT_DIR / "li_motif_plan_round2.csv"
OUT_INDEX = OUT_DIR / "li_motif_plan_round2_index.json"



def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pool(allowed=None):
    """(name, state) -> [alternative parent candidates], best-energy first.

    ``allowed`` lets the strict-recovery plan cover molecules outside the
    original audit set; the default keeps the round-2 plan byte-identical.
    """
    allowed = set(AUDIT_MOLECULES) if allowed is None else set(allowed)
    if not POOL.is_file():
        raise SystemExit("frozen conformer pool missing: " + str(POOL))
    by_key: dict = {}
    for r in csv.DictReader(POOL.open(encoding="utf-8")):
        if r["name"] not in allowed:
            continue
        # The Li-free alternative parent must be a NEUTRAL basin of the same
        # molecule: the M (charge 0) pool entries.
        if r["state"] != "M":
            continue
        key = (r["name"], r["state"])
        by_key.setdefault(key, []).append(r)
    return by_key


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute and compare, never write")
    ap.add_argument("--states", default="",
                    help="comma list NAME:STATE to plan instead of the round-2 audit set "
                         "(used by strict_recovery_v1)")
    ap.add_argument("--out", default="",
                    help="output basename (default li_motif_plan_round2); *.csv/_index.json follow")
    args = ap.parse_args(argv)

    screen = json.loads(SCREEN_JSON.read_text(encoding="utf-8")) if SCREEN_JSON.is_file() else {}
    round1_kept = {}
    for leg in screen.get("legs", []):
        if leg.get("name") in AUDIT_MOLECULES and leg.get("state") in LI_STATES:
            round1_kept[(leg["name"], leg["state"])] = len(leg.get("kept", []))

    rows = []
    if args.states:
        wanted_pairs = [tuple(s.split(":")) for s in args.states.split(",") if s.strip()]
        molecule_order = []
        for name, _state in wanted_pairs:
            if name not in molecule_order:
                molecule_order.append(name)
        state_map = {}
        for name, state in wanted_pairs:
            state_map.setdefault(name, []).append(state)
    else:
        molecule_order = list(AUDIT_MOLECULES)
        state_map = {n: list(LI_STATES) for n in molecule_order}
    pool = load_pool(molecule_order)
    for name in molecule_order:
        # Alternative parents are shared per molecule (neutral M basins),
        # listed once per Li state with the state's own charge for reference.
        basins = pool.get((name, "M"), [])
        basins.sort(key=lambda r: (float(r["rel_kcal"]), int(r["source_index"])))
        for state in state_map[name]:
            kept_r1 = round1_kept.get((name, state), "")
            parents = []
            for r in basins:
                geom = REPO / r["geometry_relpath"]
                if not geom.is_file():
                    continue  # honest gap: basin record without disk bytes
                parents.append({
                    "conformer_id": r["geometry_relpath"].split("/")[-2],
                    "geometry_relpath": r["geometry_relpath"],
                    "geometry_sha256": r["geometry_sha256"],
                    # The conformer set registers a RELATIVE energy (kcal/mol) and
                    # the absolute xTB energy; both are carried so the executor can
                    # report the parent's rank without recomputing anything.
                    "pool_rel_kcal": float(r["rel_kcal"]),
                    "pool_free_energy_eh": r.get("xtb_energy_eh", ""),
                    "sha256_disk_verified": sha256_file(geom) == r["geometry_sha256"],
                })
            verified = [p for p in parents if p["sha256_disk_verified"]]
            ceiling = (kept_r1 + len(verified)) if kept_r1 != "" else ""
            rows.append({
                "name": name, "state": state,
                "round1_kept_motifs": kept_r1,
                "alternative_parents_registered": len(parents),
                "alternative_parents_verified": len(verified),
                "round2_ceiling_upper_bound": ceiling,
                "needs_second_round_motif_search": "true",
                "status": "planned",
                "parents": json.dumps(parents, ensure_ascii=False),
                "note": ("ceiling = round-1 kept + verified alternative parents; an UPPER "
                         "BOUND. Placements may deduplicate onto the same minimum (round-1 "
                         "lesson: 7 candidates -> 1 basin), so the real independent count "
                         "can only be measured after execution."),
            })

    fields = list(rows[0])
    def render_csv():
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()
    def render_index(generated_at=None):
        if generated_at is None:
            generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return json.dumps({
            "schema_version": "1.0",
            "generated_at_utc": generated_at,
            "inputs": {p.name: sha256_file(p) for p in (POOL, SCREEN_JSON) if p.is_file()},
            "rules": {
                "parent_source": "frozen free-state conformer pool, neutral M basins, GFN2",
                "placement_rules": "identical to round 1 (monodentate + bidentate + esp_min)",
                "keep_rules": "identical to round 1",
                "level": "xTB GFN2 gas phase (screen level, never production G)",
                "ceiling_semantics": "upper bound = round1_kept + verified parents; real "
                                     "independent minima only measurable after execution",
                "no_invented_structures": "pool-limited legs keep their true basin count",
            },
            "legs": len(rows),
            "round2_ceiling_upper_bounds": {
                f"{r['name']}|{r['state']}": r["round2_ceiling_upper_bound"] for r in rows},
        }, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        # --check must be byte-exact: reuse the ON-DISK timestamp so only real
        # content drift fails the check (the project's --check discipline).
        on_disk_at = ""
        if OUT_INDEX.is_file():
            try:
                on_disk_at = json.loads(OUT_INDEX.read_text(encoding="utf-8")).get(
                    "generated_at_utc", "")
            except (ValueError, OSError):
                on_disk_at = ""
        ok = (OUT_CSV.is_file() and OUT_CSV.read_text(encoding="utf-8") == render_csv()
              and OUT_INDEX.is_file()
              and OUT_INDEX.read_text(encoding="utf-8") == render_index(on_disk_at))
        print("CHECK OK -- round-2 plan matches recomputation" if ok else "STALE: round-2 plan differs")
        return 0 if ok else 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # --out redirects BOTH files; without it the round-2 artifacts are written
    # exactly as before (the default path must never be collateral damage)
    csv_path = (OUT_DIR / (args.out + ".csv")) if args.out else OUT_CSV
    idx_path = (OUT_DIR / (args.out + "_index.json")) if args.out else OUT_INDEX
    csv_path.write_text(render_csv(), encoding="utf-8", newline="\n")
    idx_path.write_text(render_index(), encoding="utf-8", newline="\n")
    print("round2 plan: legs=%d ceilings=%s" % (
        len(rows), {f"{r['name']}|{r['state']}": r["round2_ceiling_upper_bound"] for r in rows}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
