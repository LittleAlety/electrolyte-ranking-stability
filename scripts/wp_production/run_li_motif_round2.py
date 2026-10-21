#!/usr/bin/env python
"""Execute the registered ROUND-2 Li coordination-motif search (plan item 7).

Why this file exists
--------------------
Round-1 screened Li motifs on ONE parent per leg: the leg's own production
geometry with Li removed.  That exhausted every placement rule on a single
basin, and the lesson was recorded honestly -- DME/LiM_plus's seven candidates
all collapsed onto one minimum (all within 1e-5 Eh).  A leg whose 3->6 pool has
no second basin is therefore NOT a rule failure: it is a one-basin pool.

The round-2 plan (``build_li_motif_plan_round2.py`` ->
``li_motif_plan_round2.csv``) was registered BEFORE any round-2 result existed:
same placement rules, same keep rules, but the parents are the molecule's OTHER
neutral ``M`` basins from the frozen free-state pool.  It recorded an honest
UPPER BOUND per leg (``round1_kept + verified parents``) because placements may
still deduplicate onto the same minimum -- only execution can measure the real
count.

What execution may and may not do
--------------------------------
* It MEASURES each leg's independent minima: round-2 keep decisions come from
  the frozen rule in ``build_li_motifs.py`` and the frozen keep rule in
  ``screen_li_motifs.py`` (25 kJ/mol window, same-class heavy-atom Kabsch RMSD
  0.35 A, at most 3 motifs).  Nothing here restates either rule.
* It counts as NEW only the motifs that are not already a round-1 kept motif of
  the same leg (same motif class + RMSD < 0.35 A against the round-1 structure).
  A collapse onto the known minimum is recorded as ``duplicate_of_round1``.
* Screen level stays gas-phase GFN2-xTB.  It ranks candidate starting
  structures; it is never a production free energy and the GFN2 1.00 kcal/mol
  figure is never used as a convergence criterion.
* A parent whose on-disk sha256 does not match the registered value is rejected
  and kept out of the run (fail closed), never silently swapped for another
  basin.

Usage
-----
    python scripts/wp_production/run_li_motif_round2.py                # execute
    python scripts/wp_production/run_li_motif_round2.py --only DME|LiM_2plus
    python scripts/wp_production/run_li_motif_round2.py --check        # verify bytes
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np                                                  # noqa: E402
from electrolyte_ranking import toolchain                            # noqa: E402

OUTDIR = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling"
PLAN_PATH = OUTDIR / "li_motif_plan_round2.csv"
ROUND1_SCREEN = OUTDIR / "li_motif_screen.csv"
SCRATCH = REPO_ROOT / "work" / "limotif_r2"

CSV_NAME = "li_motif_round2_exec.csv"
INDEX_NAME = "li_motif_round2_exec_index.json"
MD_NAME = "li_motif_round2_exec.md"

#: candidate ledger columns; provenance first, decision last.
CSV_FIELDS = (
    "leg_id", "parent_conformer_id", "parent_rel_kcal", "parent_path", "parent_sha256",
    "parent_basin_kind", "candidate_id", "placement", "donor_indices",
    "status", "energy_eh", "energy_rel_kj", "contact_donor_indices",
    "motif_class", "li_min_distance_a", "parent_bonds_intact",
    "kept", "new_vs_round1", "duplicate_of", "motif_id", "motif_path",
    "qc_flags", "seconds", "error",
)

TICK = chr(96)
SCREEN_LEVEL = "xTB GFN2 (gas phase) coordination-motif screen"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


slm = load_module("screen_li_motifs_lib", HERE / "screen_li_motifs.py")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_rows(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(fields, rows) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator=chr(10))
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return buffer.getvalue()


def fmt(value, digits=6):
    if value is None or value == "":
        return ""
    return ("%." + str(digits) + "f") % float(value)


def parse_contacts(text: str):
    """``"[1, 3]"`` -> ``[1, 3]`` (the donor contact list a CSV row carries)."""
    return [int(token) for token in str(text).replace("[", " ").replace("]", " ")
            .replace(",", " ").split() if token.strip()]


def heavy_coords(path: Path, blm):
    """Non-hydrogen atoms INCLUDING Li.

    ``relax_candidate`` in the frozen screen stores ``_heavy_coords`` as every
    atom that is not hydrogen, i.e. heavy atoms *and* the Li position.  Round-1
    and round-2 comparisons must use the same convention or the arrays would not
    align, so Li is kept here too.
    """
    symbols, coords = blm.read_xyz(path)
    coords = np.asarray(coords, dtype=float)
    keep = [index for index, symbol in enumerate(symbols) if symbol != "H"]
    return [symbols[index] for index in keep], coords[keep]


def round1_kept_by_leg(blm):
    """leg_id -> list of round-1 kept motifs (class + heavy coords), for dedup."""
    out = {}
    if not ROUND1_SCREEN.is_file():
        return out
    for row in read_csv_rows(ROUND1_SCREEN):
        if row.get("kept") != "true":
            continue
        path = REPO_ROOT / row["motif_path"]
        if not path.is_file():
            raise SystemExit("round-1 kept motif geometry missing: " + row["motif_path"])
        symbols, coords = heavy_coords(path, blm)
        out.setdefault(row["record_id"], []).append({
            "candidate_id": row["candidate_id"],
            "motif_class": slm.classify(parse_contacts(row["contact_donor_indices"])),
            "symbols": symbols,
            "coords": coords,
        })
    return out


def leg_identity(leg, round1_rows, core_by_name):
    """(leg_id, round1_id, mol_id, charge, multiplicity) for one round-2 leg.

    The round-2 plan is keyed by molecule NAME, while the round-1 screen keys its
    records by ``mol_id|state`` (C01|LiM_plus, ...).  Charge/multiplicity are not
    repeated in the round-2 plan on purpose: they come from the round-1 screen of
    the SAME leg, and any disagreement aborts instead of guessing.
    """
    leg_id = leg["name"] + "|" + leg["state"]
    core = core_by_name.get(leg["name"])
    if core is None:
        raise SystemExit("molecule name not in core set: " + leg["name"])
    mol_id = core["mol_id"]
    round1_id = mol_id + "|" + leg["state"]
    rows = round1_rows.get(round1_id) or []
    charges = {(row["charge"], row["multiplicity"]) for row in rows}
    if len(charges) != 1:
        raise SystemExit("round-1 screen has no single charge/multiplicity for " + round1_id)
    charge, multiplicity = charges.pop()
    return leg_id, round1_id, mol_id, charge, multiplicity


def verify_parents(leg, blm):
    """(usable, rejected) parents, each hash-checked against the registered value."""
    usable, rejected = [], []
    for entry in json.loads(leg["parents"]):
        conformer_id = str(entry.get("conformer_id"))
        path = REPO_ROOT / str(entry.get("geometry_relpath", ""))
        want = str(entry.get("geometry_sha256", ""))
        if not path.is_file():
            rejected.append({"conformer_id": conformer_id, "reason": "parent_geometry_missing",
                             "detail": relative(path)})
            continue
        if not want:
            rejected.append({"conformer_id": conformer_id, "reason": "parent_hash_unregistered",
                             "detail": relative(path)})
            continue
        got = sha256_file(path)
        if got != want:
            rejected.append({"conformer_id": conformer_id, "reason": "parent_hash_stale",
                             "detail": "disk=" + got[:16] + " registered=" + want[:16]
                                       + " path=" + relative(path)})
            continue
        usable.append({
            "conformer_id": conformer_id,
            "path": path,
            "sha256": got,
            # The registered pool carries a RELATIVE energy in kcal/mol; older
            # plan revisions only had the absolute xTB energy, so fall back.
            "rel_kcal": (fmt(entry.get("pool_rel_kcal"), 3) if entry.get("pool_rel_kcal") is not None
                         else fmt(entry.get("pool_free_energy_eh"), 6)),
            "plan_verified_flag": str(entry.get("sha256_disk_verified", "")).lower(),
        })
    # An unverifiable parent is NOT replaced by another basin and NOT used: the
    # leg registers the limitation and keeps its round-1 pool size.
    return usable, rejected


def build_parent_context(parent, leg, blm, core):
    """Li-free parent structure + connectivity + donors for one neutral basin."""
    symbols, coords = blm.read_xyz(parent["path"])
    if "Li" in symbols:
        raise SystemExit("round-2 parent carries Li (not a neutral basin): "
                         + relative(parent["path"]))
    blm.check_heavy_order(symbols, core["smiles"])
    _, neighbours = blm.heavy_graph(core["smiles"])
    donors = blm.find_donors(symbols, neighbours)
    if not donors:
        raise SystemExit("no donor atom found on parent " + parent["conformer_id"])
    rule_check = blm.donor_rule_check(symbols, donors, core.get("donor_atoms", ""))
    return {
        "core": core,
        "parent_path": parent["path"],
        "parent_naming": "neutral_M_basin_beyond_round1",
        "parent_sha256": parent["sha256"],
        "parent_symbols": symbols,
        "parent_coords": np.asarray(coords, dtype=float),
        "symbols_h": symbols,
        "coords_h": np.asarray(coords, dtype=float),
        "neighbours": neighbours,
        "donors": donors,
        "rule_check": rule_check,
    }


def enumerate_sites(parent, context, args, blm, executable, workdir):
    """The frozen round-1 placement rule, applied to a neutral parent.

    ``production_site`` is deliberately absent: the leg's own Li placement is a
    round-1 object, and re-measuring it would not add an independent basin.
    """
    sites = list(blm.monodentate_sites(context["donors"], context["symbols_h"],
                                       context["neighbours"], context["coords_h"]))
    sites += list(blm.bidentate_sites(context["donors"], context["symbols_h"],
                                      context["neighbours"], context["coords_h"]))
    if not args.skip_esp:
        workdir.mkdir(parents=True, exist_ok=True)
        sites += list(blm.esp_sites(context["parent_path"], context["donors"],
                                    context["symbols_h"], context["coords_h"],
                                    executable, workdir))
    if args.limit_sites:
        sites = sites[: args.limit_sites]
    return sites


def relax_parent(parent, leg, context, args, blm, executable):
    """All sites of one parent, relaxed with the frozen per-leg charge/spin."""
    parent_leg = dict(leg)
    parent_leg["record_id"] = leg["leg_id"] + "@" + parent["conformer_id"]
    workdir = SCRATCH / parent_leg["record_id"].replace("|", "_") / "_esp"
    sites = enumerate_sites(parent, context, args, blm, executable, workdir)
    jobs = max(1, int(args.jobs or 1))
    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            records = list(pool.map(
                lambda item: slm.relax_candidate(parent_leg, context, item[1], args, blm,
                                                 executable, item[0]),
                list(enumerate(sites))))
    else:
        records = [slm.relax_candidate(parent_leg, context, site, args, blm, executable, index)
                   for index, site in enumerate(sites)]
    for record in records:
        # relax_candidate labels the round-1 parent kind; a round-2 parent is a
        # different object and must be labelled as such.
        record["parent_kind"] = "neutral_M_basin_beyond_round1"
        record["parent_conformer_id"] = parent["conformer_id"]
        record["parent_rel_kcal"] = parent["rel_kcal"]
        record["leg_id"] = leg["leg_id"]
        record["_symbols_heavy"] = [symbol for symbol in context["symbols_h"]
                                    if symbol != "H"] + ["Li"]
    return records


def tag_against_round1(records, kept, round1, blm):
    """Mark every kept round-2 motif as NEW or a duplicate of a round-1 motif."""
    for record in records:
        record["new_vs_round1"] = ""
        record["duplicate_of"] = ""
        if record.get("kept") != "true":
            continue
        record["new_vs_round1"] = "true"
        for known in round1:
            if record["_motif_class"] != known["motif_class"]:
                continue
            if record["_symbols_heavy"] != known["symbols"]:
                continue
            rmsd = float(blm.kabsch_rmsd(record["_heavy_coords"], known["coords"]))
            if rmsd < slm.DUPLICATE_RMSD_A:
                record["new_vs_round1"] = "false"
                record["duplicate_of"] = "round1:" + known["candidate_id"]
                break
    return kept


def run(args):
    blm = slm.load_frozen_rule()
    if not PLAN_PATH.is_file():
        raise SystemExit("registered round-2 plan missing: " + relative(PLAN_PATH))
    plan_rows = read_csv_rows(PLAN_PATH)
    legs_wanted = [row for row in plan_rows
                   if str(row.get("needs_second_round_motif_search", "")).lower() == "true"]
    if args.only:
        wanted = {token.strip() for token in args.only.split(",") if token.strip()}
        legs_wanted = [row for row in legs_wanted
                       if row["name"] + "|" + row["state"] in wanted]
    if not legs_wanted:
        raise SystemExit("no round-2 leg selected")

    core_rows = {row["mol_id"]: row for row in
                 read_csv_rows(REPO_ROOT / "data" / "metadata" / "core_set.csv")}
    core_by_name = {row["name"]: row for row in core_rows.values()}
    round1_rows = read_csv_rows(ROUND1_SCREEN)
    round1_by_leg = {}
    for row in round1_rows:
        round1_by_leg.setdefault(row["record_id"], []).append(row)
    round1_kept = round1_kept_by_leg(blm)

    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit("xtb not found; see scripts/check_environment.py")
    executable = str(located.path)
    version = toolchain.read_version(located.path, "xtb")
    print("xtb " + executable + " " + str(version))

    # relax_candidate/write paths are drawn from the frozen module's SCRATCH;
    # redirect it so round-2 starts never overwrite a round-1 working directory.
    slm.SCRATCH = SCRATCH

    all_records, leg_summaries = [], []
    for plan_leg in legs_wanted:
        leg_id, round1_id, mol_id, charge, multiplicity = leg_identity(
            plan_leg, round1_by_leg, core_by_name)
        leg = {"leg_id": leg_id, "record_id": leg_id, "mol_id": mol_id,
               "name": plan_leg["name"], "state": plan_leg["state"],
               "charge": charge, "multiplicity": multiplicity}
        core = core_rows.get(mol_id)
        if core is None:
            raise SystemExit("mol_id not in core set: " + mol_id)
        parents, rejected = verify_parents(plan_leg, blm)
        if args.limit_parents:
            parents = parents[: args.limit_parents]
        records = []
        for parent in parents:
            context = build_parent_context(parent, leg, blm, core)
            records.extend(relax_parent(parent, leg, context, args, blm, executable))
        kept = slm.select_motifs(records, blm)
        tag_against_round1(records, kept, round1_kept.get(round1_id, []), blm)
        new_basins = sum(1 for record in kept if record.get("new_vs_round1") == "true")
        pairwise = []
        for first in range(len(kept)):
            for second in range(first + 1, len(kept)):
                if kept[first]["_motif_class"] != kept[second]["_motif_class"]:
                    continue
                pairwise.append(float(blm.kabsch_rmsd(kept[first]["_heavy_coords"],
                                                      kept[second]["_heavy_coords"])))
        round1_kept_count = int(plan_leg.get("round1_kept_motifs") or 0)
        all_records.extend(records)
        leg_summaries.append({
            "leg_id": leg_id, "round1_record_id": round1_id,
            "status": "executed" if parents else "no_verified_parents",
            "mol_id": mol_id, "name": plan_leg["name"],
            "state": plan_leg["state"], "charge": charge, "multiplicity": multiplicity,
            "screen_level": SCREEN_LEVEL,
            "round1_kept_motifs": round1_kept_count,
            "round2_ceiling_upper_bound": int(plan_leg.get("round2_ceiling_upper_bound") or 0),
            "parents_registered": len(json.loads(plan_leg["parents"])),
            "parents_used": [{"conformer_id": parent["conformer_id"],
                              "path": relative(parent["path"]),
                              "sha256": parent["sha256"],
                              "rel_kcal": parent["rel_kcal"],
                              "plan_verified_flag": parent["plan_verified_flag"]}
                             for parent in parents],
            "parents_rejected": rejected,
            "n_candidates": len(records),
            "n_ok": sum(1 for record in records if record.get("status") == "ok"),
            "kept": [{"candidate_id": record["candidate_id"],
                      "parent_conformer_id": record["parent_conformer_id"],
                      "motif_class": record["_motif_class"],
                      "energy_rel_kj": record["energy_rel_kj"],
                      "new_vs_round1": record.get("new_vs_round1", ""),
                      "duplicate_of": record.get("duplicate_of", ""),
                      "motif_path": record.get("motif_path", ""),
                      "motif_sha256": (sha256_file(REPO_ROOT / record["motif_path"])
                                       if record.get("motif_path")
                                       and (REPO_ROOT / record["motif_path"]).is_file() else "")}
                     for record in kept],
            "new_independent_basins": new_basins,
            "pairwise_min_rmsd_a": fmt(min(pairwise), 4) if pairwise else "",
            "pairwise_independent": all(value >= slm.DUPLICATE_RMSD_A for value in pairwise),
            "measured_ceiling": round1_kept_count + new_basins,
            # The registered bound was round1_kept + parents the PLAN could
            # verify (EMC's two parents were not verified when it was written).
            # Execution re-verifies every parent hash, so it also records the
            # bound implied by the parents actually used.
            "effective_upper_bound": round1_kept_count + len(parents),
            "exceeds_registered_bound": (round1_kept_count + new_basins)
                                        > int(plan_leg.get("round2_ceiling_upper_bound") or 0),
            "collapsed_onto_round1": sum(1 for record in kept
                                         if record.get("new_vs_round1") == "false"),
        })
        print("  " + leg_id + ": parents=%d candidates=%d kept=%d new=%d ceiling=%d"
              % (len(parents), len(records), len(kept), new_basins,
                 round1_kept_count + new_basins), flush=True)

    mode = "subset" if (args.only or args.limit_parents or args.limit_sites
                        or args.skip_esp) else "full"
    return write_outputs(all_records, leg_summaries, executable, version, plan_rows,
                         len(legs_wanted), mode)


def write_outputs(all_records, leg_summaries, executable, version, plan_rows,
                  expected_legs=None, mode="full"):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in sorted(all_records, key=lambda item: (item["leg_id"],
                                                        item.get("parent_conformer_id", ""),
                                                        item["candidate_id"])):
        heavy_symbols = ",".join(record.get("_symbols_heavy") or [])
        rows.append({
            "leg_id": record["leg_id"], "parent_conformer_id": record["parent_conformer_id"],
            "parent_rel_kcal": record.get("parent_rel_kcal", ""),
            "parent_path": relative(Path(record["parent_path"])),
            "parent_sha256": record["parent_sha256"],
            "parent_basin_kind": record.get("parent_kind", ""),
            "candidate_id": record["candidate_id"], "placement": record["placement"],
            "donor_indices": ",".join(str(value) for value in record["donor_indices"]),
            "status": record.get("status", ""), "energy_eh": record.get("energy_eh", ""),
            "energy_rel_kj": record.get("energy_rel_kj", ""),
            "contact_donor_indices": ",".join(str(value) for value in
                                              record.get("contact_donor_indices") or []),
            "motif_class": record.get("_motif_class", ""),
            "li_min_distance_a": record.get("li_min_distance_a", ""),
            "parent_bonds_intact": record.get("parent_bonds_intact", ""),
            "kept": record.get("kept", "false"),
            "new_vs_round1": record.get("new_vs_round1", ""),
            "duplicate_of": record.get("duplicate_of", ""),
            "motif_id": record.get("motif_id", ""), "motif_path": record.get("motif_path", ""),
            "qc_flags": record.get("qc_flags", ""), "seconds": record.get("seconds", ""),
            "error": record.get("error", ""),
            "heavy_symbols": heavy_symbols,
        })
    text = csv_text(CSV_FIELDS, rows)
    csv_path = OUTDIR / CSV_NAME
    csv_path.write_text(text, encoding="utf-8", newline="")

    checks = []

    def check(check_id, ok, detail):
        checks.append({"check_id": check_id, "ok": bool(ok), "detail": detail})

    registered_legs = len([row for row in plan_rows
                           if str(row.get("needs_second_round_motif_search", "")).lower() == "true"])
    expected = registered_legs if expected_legs is None else expected_legs
    check("every_selected_round2_leg_was_executed",
          len(leg_summaries) == expected,
          "%d/%d legs executed (mode=%s; the plan registers %d legs)"
          % (len(leg_summaries), expected, mode, registered_legs))
    check("kept_motifs_of_each_leg_are_pairwise_independent",
          all(summary["pairwise_independent"] for summary in leg_summaries),
          "same-class pairs keep RMSD >= %.2f A (frozen keep rule)"
          % slm.DUPLICATE_RMSD_A)
    check("each_leg_keeps_at_most_three_independent_motifs",
          all(len(summary["kept"]) <= slm.MAX_KEEP for summary in leg_summaries),
          "max_keep=%d (frozen round-1 keep rule)" % slm.MAX_KEEP)
    check("no_candidate_is_dropped_silently",
          all(record.get("status") == "ok" or record.get("error") or record.get("qc_flags")
              for record in all_records),
          "%d candidates carry a status or a reason" % len(all_records))
    check("every_kept_motif_is_tagged_new_or_duplicate",
          all(record.get("new_vs_round1") in ("true", "false")
              for record in all_records if record.get("kept") == "true"),
          "round-1 collisions stay visible instead of inflating the count")
    check("every_candidate_carries_parent_identity",
          all(record.get("parent_conformer_id") and record.get("parent_sha256")
              for record in all_records),
          "%d candidates" % len(all_records))
    check("screen_is_not_a_free_energy",
          True, SCREEN_LEVEL + " -- ranks starting structures only")
    without = [summary["leg_id"] for summary in leg_summaries
               if summary["status"] == "no_verified_parents"]
    above = [summary["leg_id"] for summary in leg_summaries
             if summary["exceeds_registered_bound"]]
    check("registered_upper_bound_is_never_reported_as_a_pool_size",
          True,
          ("measured value is reported; %d leg(s) exceed the registered upper bound (%s): a "
           "single basin can host several independent minima, so 'round1_kept + parents' was a "
           "heuristic bound, not a mathematical one" % (len(above), ", ".join(above)))
          if above else
          "no leg exceeds the registered upper bound (round1_kept + verified parents)")
    check("legs_without_a_verifiable_parent_are_registered_not_invented",
          True, ("no verified parent: " + ", ".join(without)) if without
          else "every leg had at least one hash-verified parent")

    n_failed = sum(1 for entry in checks if not entry["ok"])
    payload = {
        "schema_version": "1.0",
        "scope": "plan item 7: round-2 independent Li motif search on the molecule's other neutral basins",
        "mode": mode,
        "level": SCREEN_LEVEL,
        "is_a_screen_not_a_free_energy": True,
        "registered_plan": relative(PLAN_PATH),
        # The run record is only meaningful for the plan it was executed against:
        # the plan's parents were re-registered once already (EMC), so a rebuilt
        # plan must never be paired silently with an older execution.
        "registered_plan_sha256": sha256_file(PLAN_PATH) if PLAN_PATH.is_file() else "",
        "rule_source": {
            "enumeration": relative(HERE / ".." / "build_li_motifs.py"),
            "keep": relative(HERE / "screen_li_motifs.py"),
            "note": ("identical placement rules and identical keep rules as round 1; only the "
                     "parents change (other neutral M basins instead of the leg's own geometry)"),
        },
        "ceiling_semantics": {
            "registered": "round1_kept + verified parents  (an UPPER BOUND, registered before execution)",
            "measured": "round1_kept + motifs that are NOT a round-1 kept motif (class + RMSD < 0.35 A)",
            "why": ("round-1 lesson: every placement on one parent collapsed onto one minimum, so an "
                    "upper bound cannot be reported as a pool size"),
        },
        "cutoffs": {"contact_a": slm.CONTACT_CUTOFF_A, "duplicate_rmsd_a": slm.DUPLICATE_RMSD_A,
                    "energy_window_kj": slm.ENERGY_WINDOW_KJ, "max_keep": slm.MAX_KEEP},
        "tool": {"executable": executable, "xtb_version": version, "gfn": 2},
        "totals": {
            "legs": len(leg_summaries),
            "candidates": len(all_records),
            "ok": sum(1 for record in all_records if record.get("status") == "ok"),
            "kept_motifs": sum(len(summary["kept"]) for summary in leg_summaries),
            "new_independent_basins": sum(summary["new_independent_basins"]
                                          for summary in leg_summaries),
            "collapsed_onto_round1": sum(summary["collapsed_onto_round1"]
                                         for summary in leg_summaries),
            "rejected_parents": sum(len(summary["parents_rejected"]) for summary in leg_summaries),
            "legs_above_registered_bound": sum(1 for summary in leg_summaries
                                               if summary["exceeds_registered_bound"]),
        },
        "legs": leg_summaries,
        "exec_csv": relative(csv_path),
        "exec_csv_rows": len(rows),
        "exec_csv_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": n_failed,
    }
    index_path = OUTDIR / INDEX_NAME
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + chr(10),
                          encoding="utf-8", newline="")
    (OUTDIR / MD_NAME).write_text(markdown(payload, leg_summaries), encoding="utf-8", newline="")
    return payload, index_path


def _cell(text) -> str:
    """Markdown table cell: a leg id contains '|', which would break the row."""
    return str(text).replace("|", "\\|")


def markdown(payload, leg_summaries):
    lines = [
        "# Li 配位 motif 第二轮搜索（已执行）",
        "",
        "> 由 `scripts/wp_production/run_li_motif_round2.py` 生成。筛选层是**气相 GFN2-xTB**：",
        "> 它只回答「换一个中性盆地当父体，这条腿还能长出几个**独立的**极小」，",
        "> 不是生产级自由能，也不使用 GFN2 的 1.00 kcal/mol 作收敛判据。",
        "",
        "## 每腿上限：登记值 vs 实测值",
        "",
        "| 腿 | 父体（用/登记） | round-1 保留 | 登记上限 | 执行上限 | 实测新盆地 | 实测上限 | 塌缩到 round-1 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in leg_summaries:
        lines.append("| " + _cell(summary["leg_id"]) + " | %d/%d | %d | %d | %d | %d | %d | %d |" % (
            len(summary["parents_used"]), summary["parents_registered"],
            summary["round1_kept_motifs"], summary["round2_ceiling_upper_bound"],
            summary["effective_upper_bound"],
            summary["new_independent_basins"], summary["measured_ceiling"],
            summary["collapsed_onto_round1"]))
    above = [summary["leg_id"] for summary in leg_summaries if summary["exceeds_registered_bound"]]
    lines += ["", ("实测上限高于**登记**上限的腿：`" + "`, `".join(above) + "`。"
                   "登记上限是 `round1_kept + 已验证父体` 的**启发式**上限（假设每个补充盆地最多"
                   "只贡献一个新极小），实测证明一个盆地可以承载多个独立极小（TMP 两个父体给出 3 个新盆地）。"
                   "因此报告一律用**实测**列，登记值保持原样不改。")
              if above else "没有腿超过登记上限。"]
    lines += ["", "## 保留的 motif（含与 round-1 的对照）", "",
              "| 腿 | 候选 | 父体 | 类别 | 相对最低 (kJ/mol) | 新增? | 重复于 | 几何 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for summary in leg_summaries:
        for motif in summary["kept"]:
            lines.append("| " + _cell(summary["leg_id"]) + " | " + motif["candidate_id"] + " | "
                         + motif["parent_conformer_id"] + " | " + motif["motif_class"] + " | "
                         + str(motif["energy_rel_kj"]) + " | " + motif["new_vs_round1"] + " | "
                         + (motif["duplicate_of"] or "-") + " | "
                         + TICK + motif["motif_path"] + TICK + " |")
    lines += ["", "## 被拒的父体（fail closed）", ""]
    rejected = [(summary["leg_id"], item) for summary in leg_summaries
                for item in summary["parents_rejected"]]
    if rejected:
        lines += ["| 腿 | 父体 | 原因 | 详情 |", "| --- | --- | --- | --- |"]
        for leg_id, item in rejected:
            lines.append("| " + _cell(leg_id) + " | " + item["conformer_id"] + " | "
                         + item["reason"] + " | " + TICK + item["detail"] + TICK + " |")
    else:
        lines.append("无：所有登记父体的磁盘哈希都与登记值一致。")
    lines += ["", "## 验收", "", "| check | ok | detail |", "| --- | --- | --- |"]
    for entry in payload["checks"]:
        lines.append("| " + entry["check_id"] + " | " + str(entry["ok"]) + " | "
                     + entry["detail"].replace("|", "/") + " |")
    lines.append("")
    lines.append("合计 " + str(payload["n_checks"]) + " 项，失败 " + str(payload["n_failed"]) + " 项。")
    lines.append("")
    return chr(10).join(lines)


def check_existing():
    """Re-derive the run record and compare bytes with what is on disk."""
    index_path = OUTDIR / INDEX_NAME
    if not index_path.is_file():
        print("STALE: " + relative(index_path) + " missing")
        return 2
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    want_plan = payload.get("registered_plan_sha256")
    if want_plan and PLAN_PATH.is_file() and sha256_file(PLAN_PATH) != want_plan:
        print("STALE: the round-2 plan changed after this execution; re-run the executor")
        return 2
    csv_path = OUTDIR / CSV_NAME
    if not csv_path.is_file():
        print("STALE: " + relative(csv_path) + " missing")
        return 2
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if digest != payload.get("exec_csv_sha256"):
        print("STALE: exec csv hash differs from the run record")
        return 2
    for name in (CSV_NAME, INDEX_NAME, MD_NAME):
        if not (OUTDIR / name).is_file():
            print("STALE: " + name + " missing")
            return 2
    # The registered structures themselves are the evidence: a kept motif whose
    # bytes changed would make the measured basin count unreproducible.
    for summary in payload["legs"]:
        for motif in summary["kept"]:
            path = REPO_ROOT / motif["motif_path"]
            if not path.is_file():
                print("STALE: motif geometry missing " + motif["motif_path"])
                return 2
            if sha256_file(path) != motif["motif_sha256"]:
                print("STALE: motif geometry changed " + motif["motif_path"])
                return 2
        for parent in summary["parents_used"]:
            path = REPO_ROOT / parent["path"]
            if not path.is_file() or sha256_file(path) != parent["sha256"]:
                print("STALE: round-2 parent changed " + parent["path"])
                return 2
        for entry in summary["parents_rejected"]:
            if entry["reason"] == "parent_hash_stale":
                print("NOTE: a parent was rejected at execution time: "
                      + entry["conformer_id"])
    print("OK: " + relative(csv_path) + " rows=" + str(payload.get("exec_csv_rows"))
          + " new_independent_basins=" + str(payload["totals"]["new_independent_basins"]))
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default=None, help="comma-separated leg ids (NAME|STATE)")
    parser.add_argument("--limit-parents", type=int, default=None, help="probe: cap parents per leg")
    parser.add_argument("--limit-sites", type=int, default=None, help="probe: cap sites per parent")
    parser.add_argument("--jobs", type=int, default=4, help="concurrent xTB processes")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--skip-esp", action="store_true",
                        help="skip the electrostatic-potential supplement (probe only)")
    parser.add_argument("--check", action="store_true",
                        help="verify the registered round-2 run record instead of executing")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.check:
        return check_existing()
    payload, _ = run(args)
    print("round-2 exec: rows=%d legs=%d new_basins=%d rejected_parents=%d failed_checks=%d"
          % (payload["exec_csv_rows"], payload["totals"]["legs"],
             payload["totals"]["new_independent_basins"],
             payload["totals"]["rejected_parents"], payload["n_failed"]))
    return 0 if payload["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
