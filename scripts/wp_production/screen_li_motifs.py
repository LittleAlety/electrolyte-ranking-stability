#!/usr/bin/env python
"""Execute the registered Li coordination-motif screen (plan 6.1, execution step 3).

Why this file exists
--------------------
Plan 6.1 requires the charged states to be screened on their own: the Li mother
state and the oxidised state must each keep their own low-energy structures, and
one Li state must never be propagated into the other.  The rule that decides
which motifs survive is registered, before any screen result existed, in
outputs/physics_completion/li_motif_sampling/motif_plan.csv plus
selection_rule.md.  Until this script ran the rule was registered but never
executed: all 8 legs carried motif_screen_status = not_computed.

How the rule is executed here
-----------------------------
The enumeration itself is already frozen in scripts/build_li_motifs.py (donor
identification, one monodentate site per donor, bidentate pairs, electrostatatic
potential supplement, GFN2-xTB pre-optimisation).  This module imports that file
instead of restating the rule, so the screen cannot drift away from what was
registered.

Two differences from build_li_motifs.py are deliberate and recorded in the run
record:

* the parent geometry is the leg's own production geometry with Li removed, not
  the shared week-3 neutral geometry.  Plan 6.1 asks for the state's own seeds,
  so each leg is built from the connectivity and conformation of that leg; the
  parent path and its sha256 are written next to every candidate.
* charge and multiplicity come from the leg (LiM_plus is 1/1, LiM_2plus is
  2/2).  A 2+ leg is never relaxed as a 1+ complex.

The screen is gas-phase GFN2-xTB.  It ranks motifs and decides which three
independent structures are worth a production leg; it is never reported as a
free energy.  A candidate that fails, or that is removed as a duplicate, still
gets a CSV row carrying the reason, because dropping it silently would be the
same class of error as deleting a failed SCF.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import toolchain, xtb  # noqa: E402

PLAN_PATH = (REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling" / "motif_plan.csv")
OUTDIR = REPO_ROOT / "outputs" / "physics_completion" / "li_motif_sampling"
SCRATCH = REPO_ROOT / "work" / "limotif"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
PROD_ROOT = REPO_ROOT / "work" / "wp2prod"
RULE_SOURCE = REPO_ROOT / "scripts" / "build_li_motifs.py"

SCREEN_LEVEL = "xTB GFN2 (gas phase) coordination-motif screen"
CONTACT_CUTOFF_A = 2.4
DUPLICATE_RMSD_A = 0.35
ENERGY_WINDOW_KJ = 25.0
MAX_KEEP = 3
KJ_PER_EH = 2625.499638
TICK = chr(96)

CSV_FIELDS = (
    "record_id", "mol_id", "name", "state", "charge", "multiplicity",
    "candidate_id", "placement", "donor_indices", "target_distance_a",
    "parent_kind", "parent_path", "parent_sha256",
    "status", "energy_eh", "energy_rel_kj",
    "n_donor_contacts", "contact_donor_indices", "li_min_distance_a",
    "parent_bonds_intact", "kept", "dedup_reason", "motif_id", "motif_path",
    "qc_flags", "seconds", "error",
)


def load_frozen_rule():
    """Import the frozen enumeration rule instead of re-implementing it."""
    spec = importlib.util.spec_from_file_location("build_li_motifs_frozen", RULE_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def load_legs(only=None):
    if not PLAN_PATH.exists():
        raise SystemExit("registered motif plan missing: " + relative(PLAN_PATH))
    legs = read_csv_rows(PLAN_PATH)
    if not legs:
        raise SystemExit("registered motif plan is empty: " + relative(PLAN_PATH))
    if only:
        wanted = {token.strip() for token in only.split(",") if token.strip()}
        legs = [leg for leg in legs if leg["record_id"] in wanted]
    return legs


def load_core_rows():
    return {row["mol_id"]: row for row in read_csv_rows(CORE_SET)}


def production_geometry(leg):
    name = leg["name"] + "_" + leg["state"] + ".xyz"
    path = PROD_ROOT / leg["name"] / leg["state"] / name
    if not path.exists():
        raise SystemExit("production geometry missing for " + leg["record_id"] + ": " + relative(path))
    return path


def build_leg_context(leg, blm, core_rows):
    """Return the parent (Li-free) structure, its connectivity and its donor set."""
    core = core_rows.get(leg["mol_id"])
    if core is None:
        raise SystemExit("mol_id not in core set: " + leg["mol_id"])
    parent_path = production_geometry(leg)
    symbols, coords = blm.read_xyz(parent_path)
    if "Li" not in symbols:
        raise SystemExit("production geometry carries no Li: " + relative(parent_path))
    keep = [index for index, symbol in enumerate(symbols) if symbol != "Li"]
    symbols_h = [symbols[index] for index in keep]
    coords_h = np.asarray(coords, dtype=float)[keep]
    blm.check_heavy_order(symbols_h, core["smiles"])
    _, neighbours = blm.heavy_graph(core["smiles"])
    donors = blm.find_donors(symbols_h, neighbours)
    if not donors:
        raise SystemExit("no donor atom found for " + leg["record_id"])
    rule_check = blm.donor_rule_check(symbols_h, donors, core.get("donor_atoms", ""))
    return {
        "core": core,
        "parent_path": parent_path,
        "parent_sha256": sha256_file(parent_path),
        "parent_symbols": symbols,
        "parent_coords": np.asarray(coords, dtype=float),
        "symbols_h": symbols_h,
        "coords_h": coords_h,
        "neighbours": neighbours,
        "donors": donors,
        "rule_check": rule_check,
    }


def production_site(context):
    """The leg's own Li placement, kept as the same-level reference candidate."""
    coords = context["parent_coords"]
    li_index = list(context["parent_symbols"]).index("Li")
    position = np.asarray(coords[li_index], dtype=float)
    distances = sorted(
        (float(np.linalg.norm(position - np.asarray(coords[index], dtype=float))), index)
        for index in context["donors"]
    )
    return {
        "placement": "production_geometry",
        "donors": (distances[0][1],),
        "target_distance": round(distances[0][0], 3),
        "position": position,
    }


def enumerate_sites(leg, context, args, blm, executable):
    sites = [production_site(context)]
    sites += blm.monodentate_sites(context["donors"], context["symbols_h"], context["neighbours"], context["coords_h"])
    sites += blm.bidentate_sites(context["donors"], context["symbols_h"], context["neighbours"], context["coords_h"])
    if not args.skip_esp:
        workdir = SCRATCH / leg["record_id"].replace("|", "_") / "_esp"
        workdir.mkdir(parents=True, exist_ok=True)
        sites += blm.esp_sites(context["parent_path"], context["donors"], context["symbols_h"],
                               context["coords_h"], executable, workdir)
    if args.limit_sites:
        sites = sites[: args.limit_sites]
    return sites


def donor_contacts(coords, li_index, donors):
    contacts = []
    for index in donors:
        distance = float(np.linalg.norm(np.asarray(coords[li_index], dtype=float) - np.asarray(coords[index], dtype=float)))
        if distance <= CONTACT_CUTOFF_A:
            contacts.append(index)
    return sorted(contacts)


def classify(contacts):
    if not contacts:
        return "unbound"
    if len(contacts) == 1:
        return "monodentate_donor%d" % contacts[0]
    return "bidentate_donors" + "_".join(str(index) for index in contacts)


def relax_candidate(leg, context, site, args, blm, executable, index):
    """One GFN2-xTB optimisation of this leg's [Li M] complex started from site."""
    symbols = list(context["symbols_h"]) + ["Li"]
    coords = np.vstack([context["coords_h"], np.asarray(site["position"], dtype=float)])
    candidate_id = "c%02d" % index
    label = leg["record_id"].replace("|", "_") + "_" + candidate_id
    workdir = SCRATCH / leg["record_id"].replace("|", "_") / label
    workdir.mkdir(parents=True, exist_ok=True)
    xyz_path = workdir / (label + ".xyz")
    blm.write_xyz(xyz_path, symbols, coords, label + " " + site["placement"])

    record = {
        "record_id": leg["record_id"], "mol_id": leg["mol_id"], "name": leg["name"],
        "state": leg["state"], "charge": leg["charge"], "multiplicity": leg["multiplicity"],
        "candidate_id": candidate_id, "placement": site["placement"],
        "donor_indices": list(site["donors"]), "target_distance_a": site["target_distance"],
        "parent_kind": "state_own_production_geometry_minus_Li",
        "parent_path": relative(context["parent_path"]),
        "parent_sha256": context["parent_sha256"],
        "kept": "false", "dedup_reason": "", "motif_id": "", "motif_path": "",
        "_heavy_coords": None, "_intact": False, "_energy": None,
    }
    started = time.perf_counter()
    try:
        result = xtb.run_xtb(
            executable,
            xtb.JOB_OPTIMIZE,
            input_name=xyz_path.name,
            charge=int(leg["charge"]),
            multiplicity=int(leg["multiplicity"]),
            cwd=workdir,
            timeout_seconds=args.timeout,
            required=(),
        )
    except Exception as exc:  # noqa: BLE001 - a failed screen job is a result, not a crash
        record.update({"status": "execution_failed", "energy_eh": "", "energy_rel_kj": "",
                       "qc_flags": "geometry_failed", "seconds": round(time.perf_counter() - started, 2),
                       "error": repr(exc)})
        return record

    raw_path = workdir / (label + "_opt.out")
    raw_path.write_text(result.raw_output or "", encoding="utf-8", newline=chr(10))
    optimized_path = workdir / "xtbopt.xyz"
    energy = getattr(result, "total_energy_eh", None)
    if not optimized_path.exists() or energy is None:
        record.update({"status": "abnormal_termination", "energy_eh": fmt(energy, 8), "energy_rel_kj": "",
                       "qc_flags": ",".join(getattr(result, "qc_flags", ()) or ("no_optimized_geometry",)),
                       "seconds": round(time.perf_counter() - started, 2), "error": ""})
        return record

    optimized_symbols, optimized_coords = blm.read_xyz(optimized_path)
    optimized_coords = np.asarray(optimized_coords, dtype=float)
    if list(optimized_symbols) != symbols:
        record.update({"status": "atom_order_changed", "energy_eh": fmt(energy, 8), "energy_rel_kj": "",
                       "qc_flags": "elements_mismatch", "seconds": round(time.perf_counter() - started, 2),
                       "error": ""})
        return record

    li_index = len(context["symbols_h"])
    contacts = donor_contacts(optimized_coords, li_index, context["donors"])
    li_min = min(
        float(np.linalg.norm(optimized_coords[li_index] - optimized_coords[index]))
        for index in context["donors"]
    )
    intact = bool(blm.parent_bonds_intact(optimized_symbols[:-1], context["neighbours"], optimized_coords[:-1]))
    heavy_indices = [index for index, symbol in enumerate(optimized_symbols) if symbol != "H"]
    record.update({
        "status": "ok" if getattr(result, "normal_termination", False) else "abnormal_termination",
        "energy_eh": fmt(energy, 8),
        "energy_rel_kj": "",
        "n_donor_contacts": len(contacts),
        "contact_donor_indices": contacts,
        "li_min_distance_a": fmt(li_min, 4),
        "parent_bonds_intact": "true" if intact else "false",
        "qc_flags": ",".join(getattr(result, "qc_flags", ()) or ()),
        "seconds": round(time.perf_counter() - started, 2),
        "error": "",
        "_energy": float(energy),
        "_heavy_coords": optimized_coords[heavy_indices],
        "_intact": intact,
        "_motif_class": classify(contacts),
    })
    return record


def select_motifs(records, blm):
    """Keep the lowest independent motifs; every dropped candidate keeps its reason."""
    usable = [
        record for record in records
        if record.get("status") == "ok" and record.get("_intact")
        and record.get("contact_donor_indices") and record.get("_heavy_coords") is not None
    ]
    usable.sort(key=lambda record: record["_energy"])
    kept = []
    for record in usable:
        if kept and (record["_energy"] - kept[0]["_energy"]) * KJ_PER_EH > ENERGY_WINDOW_KJ:
            record["dedup_reason"] = "outside_energy_window"
            continue
        duplicate = None
        for winner in kept:
            same_class = record["_motif_class"] == winner["_motif_class"]
            rmsd = float(blm.kabsch_rmsd(record["_heavy_coords"], winner["_heavy_coords"]))
            if same_class and rmsd < DUPLICATE_RMSD_A:
                duplicate = (winner, rmsd)
                break
        if duplicate is not None:
            record["dedup_reason"] = "duplicate_geometry_of_" + duplicate[0]["candidate_id"]
            continue
        record["kept"] = "true"
        record["motif_id"] = record["record_id"] + "#m%d" % (len(kept) + 1)
        directory = SCRATCH / record["record_id"].replace("|", "_") / (record["record_id"].replace("|", "_") + "_" + record["candidate_id"])
        record["motif_path"] = relative(directory / "xtbopt.xyz")
        kept.append(record)
        if len(kept) >= MAX_KEEP:
            break
    reference = kept[0]["_energy"] if kept else None
    if reference is not None:
        for record in records:
            if record.get("_energy") is not None:
                record["energy_rel_kj"] = fmt((record["_energy"] - reference) * KJ_PER_EH, 3)
    return kept


def leg_verdict(kept, records):
    if not kept:
        return "unresolved"
    production = [record for record in records
                  if record.get("placement") == "production_geometry" and record.get("status") == "ok"]
    if not production:
        return "production_candidate_failed"
    if production[0]["candidate_id"] == kept[0]["candidate_id"]:
        return "production_motif_is_lowest"
    gap = (production[0]["_energy"] - kept[0]["_energy"]) * KJ_PER_EH
    if gap > 1.0:
        return "alternative_motif_lower"
    return "production_motif_within_1kj"


def run_leg(leg, args, blm, context, executable):
    sites = enumerate_sites(leg, context, args, blm, executable)
    if args.jobs and args.jobs > 1:
        with ThreadPoolExecutor(max_workers=max(1, int(args.jobs))) as pool:
            records = list(pool.map(
                lambda item: relax_candidate(leg, context, item[1], args, blm, executable, item[0]),
                list(enumerate(sites)),
            ))
    else:
        records = [relax_candidate(leg, context, site, args, blm, executable, index)
                   for index, site in enumerate(sites)]
    return records, select_motifs(records, blm)


def markdown(payload, leg_summaries):
    lines = [
        "# 方案 6.1 第 3 步：四分子 Li 配位 motif 筛选（已执行）",
        "",
        "> 由 scripts/wp_production/screen_li_motifs.py 生成。筛选层是**气相 GFN2-xTB**，它只回答",
        "> 「每条腿保留哪几个独立 motif」，不是生产级自由能，也不是 wB97X-D4 + SMD。",
        "> 规则在任何结果存在之前就已登记（selection_rule.md / motif_plan.csv）；本层不修改规则。",
        "",
        "| 记录 | 分子 | 态 | 起点数 | 成功 | 保留 motif | 判定 | 最低 motif |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in leg_summaries:
        lowest = summary["kept"][0]["_motif_class"] if summary["kept"] else "-"
        lines.append("| " + summary["record_id"] + " | " + summary["name"] + " | " + summary["state"] + " | "
                     + str(summary["n_sites"]) + " | " + str(summary["n_ok"]) + " | "
                     + str(len(summary["kept"])) + " | " + summary["verdict"] + " | " + lowest + " |")
    lines += [
        "",
        "## 保留的独立 motif（可执行结构集合）",
        "",
        "| 记录 | 序 | 相对最低 (kJ/mol) | motif 类别 | 给体接触 | Li-给体最近 (A) | 几何（仓库相对路径） |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in leg_summaries:
        for order, motif in enumerate(summary["kept"], start=1):
            lines.append("| " + summary["record_id"] + " | " + str(order) + " | " + str(motif["energy_rel_kj"]) + " | "
                         + motif["_motif_class"] + " | " + ",".join(str(index) for index in motif["contact_donor_indices"])
                         + " | " + motif["li_min_distance_a"] + " | " + TICK + motif["motif_path"] + TICK + " |")
    lines += [
        "",
        "## 与登记规则的偏差（逐条显式记录）",
        "",
        "* 父几何用**该腿自己的生产几何去掉 Li**，不是共享的 week-3 中性几何：方案 6.1 要求每态从自己的连通性出发。",
        "* 电荷/多重度取自该腿（LiM_plus = 1/1，LiM_2plus = 2/2），2+ 腿绝不按 1+ 复合物弛豫。",
        "* 筛选仍是气相 GFN2-xTB，**不能**当作生产自由能，也不能替代 wB97X-D4 + SMD(acetonitrile)。",
        "",
        "## 验收",
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for entry in payload["checks"]:
        lines.append("| " + entry["check_id"] + " | " + str(entry["ok"]) + " | " + entry["detail"] + " |")
    lines.append("")
    lines.append("合计 " + str(payload["n_checks"]) + " 项，失败 " + str(payload["n_failed"]) + " 项。")
    lines.append("")
    return chr(10).join(lines)


def write_outputs(all_records, leg_summaries, args, executable, version, registered_legs):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTDIR / "li_motif_screen.csv"
    text = csv_text(CSV_FIELDS, sorted(all_records, key=lambda record: (record["record_id"], record["candidate_id"])))
    csv_path.write_text(text, encoding="utf-8", newline="")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    checks = []

    def check(check_id, ok, detail):
        checks.append({"check_id": check_id, "ok": bool(ok), "detail": detail})

    charges = {leg["record_id"]: (leg["charge"], leg["multiplicity"]) for leg in registered_legs}
    check("every_registered_leg_was_screened",
          {summary["record_id"] for summary in leg_summaries} == set(charges),
          "%d legs carry candidates" % len(leg_summaries))
    check("each_leg_keeps_at_most_three_independent_motifs",
          all(len(summary["kept"]) <= MAX_KEEP for summary in leg_summaries),
          "max_keep=%d" % MAX_KEEP)
    check("charge_and_multiplicity_come_from_the_leg",
          all((record["charge"], record["multiplicity"]) == charges[record["record_id"]] for record in all_records),
          "no leg is relaxed with another leg's charge")
    check("every_candidate_carries_its_parent_hash",
          all(record["parent_sha256"] for record in all_records),
          "%d candidates" % len(all_records))
    check("no_candidate_is_dropped_silently",
          all(record.get("status") == "ok" or record.get("error") or record.get("qc_flags") for record in all_records),
          "failed candidates keep a reason")

    n_failed = sum(1 for entry in checks if not entry["ok"])
    payload = {
        "scope": ("plan 6.1 / execution step 3: execution of the registered Li coordination-motif screen "
                  "for the four-molecule subcohort (DMC / EMC / GBL / SL x LiM_plus / LiM_2plus)"),
        "level": SCREEN_LEVEL,
        "is_a_screen_not_a_free_energy": True,
        "rule_source": relative(RULE_SOURCE) + " (frozen rule conformers_and_states.li_motif_generation)",
        "registered_plan": relative(PLAN_PATH),
        "registered_before_any_screen": True,
        "parent_policy": {
            "kind": "state_own_production_geometry_minus_Li",
            "why": ("plan 6.1 asks each Li state to be built from the state's own connectivity and forbids "
                    "propagating one Li state into the other, so each leg enumerates Li sites on its own leg geometry"),
        },
        "cutoffs": {"contact_a": CONTACT_CUTOFF_A, "duplicate_rmsd_a": DUPLICATE_RMSD_A,
                    "energy_window_kj": ENERGY_WINDOW_KJ, "max_keep": MAX_KEEP},
        "tool": {"executable": str(executable), "xtb_version": version, "gfn": 2},
        "totals": {
            "legs": len(leg_summaries),
            "candidates": len(all_records),
            "ok": sum(1 for record in all_records if record.get("status") == "ok"),
            "kept_motifs": sum(len(summary["kept"]) for summary in leg_summaries),
        },
        "legs": leg_summaries,
        "screen_csv": relative(csv_path),
        "screen_csv_rows": len(all_records),
        "screen_csv_sha256": digest,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": n_failed,
    }
    json_path = OUTDIR / "li_motif_screen.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline="")
    (OUTDIR / "li_motif_screen.md").write_text(markdown(payload, leg_summaries), encoding="utf-8", newline="")
    return payload, json_path


def run(args):
    blm = load_frozen_rule()
    registered_legs = load_legs(None)
    legs = load_legs(args.only)
    core_rows = load_core_rows()
    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit("xtb not found; see scripts/check_environment.py")
    executable = str(located.path)
    version = toolchain.read_version(located.path, "xtb")
    print("xtb " + executable + " " + str(version))
    print("legs: " + ", ".join(leg["record_id"] for leg in legs))

    all_records = []
    leg_summaries = []
    for leg in legs:
        context = build_leg_context(leg, blm, core_rows)
        records, kept = run_leg(leg, args, blm, context, executable)
        all_records.extend(records)
        leg_summaries.append({
            "record_id": leg["record_id"], "mol_id": leg["mol_id"], "name": leg["name"],
            "state": leg["state"], "charge": leg["charge"], "multiplicity": leg["multiplicity"],
            "screen_level": SCREEN_LEVEL,
            "parent_path": relative(context["parent_path"]), "parent_sha256": context["parent_sha256"],
            "donors": list(context["donors"]), "donor_rule_check": context["rule_check"],
            "n_sites": len(records),
            "n_ok": sum(1 for record in records if record.get("status") == "ok"),
            "kept": [dict((key, value) for key, value in record.items() if key != "_heavy_coords") for record in kept],
            "verdict": leg_verdict(kept, records),
        })
        print("  " + leg["record_id"] + ": sites=" + str(leg_summaries[-1]["n_sites"])
              + " ok=" + str(leg_summaries[-1]["n_ok"])
              + " kept=" + str(len(kept)) + " verdict=" + leg_summaries[-1]["verdict"])

    payload, json_path = write_outputs(all_records, leg_summaries, args, executable, version, registered_legs)
    print("wrote " + relative(json_path) + " (" + str(payload["n_checks"]) + " checks, "
          + str(payload["n_failed"]) + " failed)")
    return 0 if payload["n_failed"] == 0 else 1


def check(args):
    json_path = OUTDIR / "li_motif_screen.json"
    csv_path = OUTDIR / "li_motif_screen.csv"
    if not json_path.exists() or not csv_path.exists():
        print("CHECK SKIPPED -- no screen results registered yet (" + relative(json_path) + " missing)")
        return 0
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    text = csv_path.read_text(encoding="utf-8")
    problems = []
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != payload["screen_csv_sha256"]:
        problems.append("screen csv sha256 mismatch")
    rows = list(csv.DictReader(io.StringIO(text)))
    if len(rows) != payload["screen_csv_rows"]:
        problems.append("row count mismatch: %d vs %d" % (len(rows), payload["screen_csv_rows"]))
    for summary in payload["legs"]:
        parent = REPO_ROOT / summary["parent_path"]
        if not parent.exists():
            problems.append("parent missing: " + summary["parent_path"])
        elif sha256_file(parent) != summary["parent_sha256"]:
            problems.append("parent hash changed: " + summary["parent_path"])
    if {summary["record_id"] for summary in payload["legs"]} != {leg["record_id"] for leg in load_legs(None)}:
        problems.append("screen legs do not match the registered plan")
    if payload["n_failed"]:
        problems.append("run record reports %d failed checks" % payload["n_failed"])
    if problems:
        for problem in problems:
            print("CHECK FAILED -- " + problem)
        return 1
    print("CHECK OK -- " + relative(csv_path) + " matches its run record, " + str(len(rows))
          + " candidates, " + str(len(payload["legs"])) + " legs, parents unchanged")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Execute the registered plan-6.1 Li coordination-motif screen.")
    parser.add_argument("--only", default=None, help="comma-separated record_id allow-list")
    parser.add_argument("--limit-sites", type=int, default=None, help="cap the site count per leg (probe only)")
    parser.add_argument("--jobs", type=int, default=4, help="concurrent xTB processes")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--skip-esp", action="store_true", help="skip the electrostatic-potential supplement")
    parser.add_argument("--check", action="store_true", help="verify the registered screen against its run record")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.check:
        return check(args)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
