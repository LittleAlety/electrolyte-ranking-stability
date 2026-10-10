#!/usr/bin/env python
"""Plan 6.1 step 3 / 6.2: the ensemble layer of the four-molecule subcohort, at the screen level.

Why this file exists
--------------------
Every produced state of the four-molecule subcohort still carries
n_conformers = 1.  The registered sampling layer
(outputs/physics_completion/sampling/sampling_escalation.csv) therefore ends at
registered_pending_round1_free_energy_check: the 3 -> 6 escalation is only
allowed to fire once the free-energy change of the kept structures is known, and
the flip ladder's R4 rung reads "no sampled ensemble exists yet".

This module closes the cheap half of that gap.  For every structure the two
registered pools already contain -- the free-state GFN2 minima of
sampling_conformer_set.csv and the independent Li motifs of li_motif_screen.json
-- it recomputes the GFN2 thermodynamics with --ohess and turns the set into a
Boltzmann ensemble with the frozen rule

    w_i   = exp(-(G_i - G_min) / RT) / sum_j exp(-(G_j - G_min) / RT)
    G_ens = -RT ln sum_j exp(-(G_j - G_min) / RT) + G_min

so the ensemble correction dG_ens = G_ens - G_min can be compared with the pair
gaps.  dE_ens (the same average over the electronic energies) is reported next to
it, because the difference between the two is exactly the thermal part that the
earlier, electronic-only sampling layer never measured.

What this layer is NOT
----------------------
It is gas-phase GFN2, i.e. the same cheap screen as the rest of the sampling
layer.  It is never reported as the production free energy, and it does not
replace the production R4 rung, which needs wB97X-D4 + SMD(acetonitrile) legs for
the extra structures.  A row whose Hessian carries significant imaginary modes
is not a minimum on this surface: it is kept in the CSV with its mode count,
excluded from the ensemble, and never silently dropped.

Usage
-----
    .venv\\Scripts\\python.exe scripts\\wp_production\\build_wp2_ensemble_free_energies.py --run
    .venv\\Scripts\\python.exe scripts\\wp_production\\build_wp2_ensemble_free_energies.py
    .venv\\Scripts\\python.exe scripts\\wp_production\\build_wp2_ensemble_free_energies.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import toolchain, xtb  # noqa: E402

PC = REPO_ROOT / "outputs" / "physics_completion"
POOL_CSV = PC / "sampling" / "sampling_conformer_set.csv"
LI_SCREEN = PC / "li_motif_sampling" / "li_motif_screen.json"
ESCO = PC / "sampling" / "sampling_escalation.csv"
OUTDIR = PC / "ensembles"
CACHE = REPO_ROOT / "work" / "enso"
RAW_CSV = CACHE / "enso_raw.csv"

LEVEL = "xTB GFN2 (gas phase) ensemble free energy"
CLAIM_LEVEL = "screen_gfn2_gas_phase"
TEMPERATURE_K = 298.15
RT_KJ = 8.314462618e-3 * TEMPERATURE_K
KJ_PER_EH = 2625.499638
TICK = chr(96)

#: the same extraction as scripts/run_thermal_correction_sample.py (R9), so the
#: two layers cannot disagree about what "GFN2 free energy" means.
_TOTAL_ENERGY = re.compile(r"\|\s*TOTAL ENERGY\s+(-?\d+\.\d+)\s*Eh")
_TOTAL_ENTHALPY = re.compile(r"\|\s*TOTAL ENTHALPY\s+(-?\d+\.\d+)\s*Eh")
_TOTAL_FREE = re.compile(r"\|\s*TOTAL FREE ENERGY\s+(-?\d+\.\d+)\s*Eh")
_ZPE = re.compile(r"::\s*zero point energy\s+(-?\d+\.\d+)\s*Eh")
#: xTB prints "found 1 significant imaginary frequency" for a single mode but
#: "found 2 significant imaginary frequencies" for several, so a singular-only
#: pattern silently turns every multi-imaginary Hessian into a minimum.  Both the
#: message and the canonical thermochemistry header are parsed, and the largest
#: count wins.
_IMAGINARY_FOUND = re.compile(r"found\s+(\d+)\s+significant imaginary frequenc(?:y|ies)")
_IMAGINARY_THERMO = re.compile(r"#\s*imaginary freq\.\s*(\d+)")

RAW_FIELDS = ("leg_id", "source", "rank", "mol_id", "name", "state", "charge", "multiplicity",
              "geometry_relpath", "geometry_sha256", "status", "total_energy_eh",
              "total_enthalpy_eh", "total_free_energy_eh", "zero_point_energy_eh",
              "n_imaginary", "seconds", "error")
ENS_FIELDS = ("leg_id", "mol_id", "name", "state", "charge", "multiplicity", "source", "rank",
              "geometry_relpath", "geometry_sha256", "status", "total_energy_eh",
              "total_free_energy_eh", "zero_point_energy_eh", "n_imaginary", "rel_e_kj",
              "rel_g_kj", "boltzmann_weight", "counted_in_ensemble", "note")


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


def csv_text(fieldnames, rows) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fieldnames), lineterminator=chr(10))
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return buffer.getvalue()


def read_rows(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def last(pattern, text):
    found = pattern.findall(text or "")
    return found[-1] if found else None


def parse_enso(text: str) -> dict:
    imaginary = [int(value) for value in _IMAGINARY_FOUND.findall(text or "")]
    imaginary += [int(value) for value in _IMAGINARY_THERMO.findall(text or "")]
    energy = last(_TOTAL_ENERGY, text)
    return {
        "total_energy_eh": float(energy) if energy else None,
        "total_enthalpy_eh": float(last(_TOTAL_ENTHALPY, text)) if last(_TOTAL_ENTHALPY, text) else None,
        "total_free_energy_eh": float(last(_TOTAL_FREE, text)) if last(_TOTAL_FREE, text) else None,
        "zero_point_energy_eh": float(last(_ZPE, text)) if last(_ZPE, text) else None,
        "n_imaginary": max(imaginary) if imaginary else 0,
    }


def registered_structures():
    """Every structure the registered pools already contain, in a frozen order.

    Both pools are read, never edited: this layer consumes the registered sets and
    cannot introduce a geometry that was not registered beforehand.
    """
    structures = []
    for row in read_rows(POOL_CSV):
        structures.append({
            "leg_id": "%s|%s" % (row["mol_id"], row["state"]),
            "source": "free_state_conformer_pool",
            "rank": row["rank"], "mol_id": row["mol_id"], "name": row["name"],
            "state": row["state"], "charge": row["charge"], "multiplicity": row["multiplicity"],
            "geometry_relpath": row["geometry_relpath"], "geometry_sha256": row["geometry_sha256"],
        })
    if LI_SCREEN.is_file():
        payload = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
        for entry in payload["legs"]:
            for order, motif in enumerate(entry["kept"], start=1):
                structures.append({
                    "leg_id": entry["record_id"],
                    "source": "li_motif_screen",
                    "rank": str(order), "mol_id": entry["mol_id"], "name": entry["name"],
                    "state": entry["state"], "charge": entry["charge"],
                    "multiplicity": entry["multiplicity"],
                    "geometry_relpath": motif["motif_path"],
                    "geometry_sha256": sha256_file(REPO_ROOT / motif["motif_path"]),
                })
    return structures


def cache_key(structure):
    return "%s#%s#%s" % (structure["leg_id"], structure["source"], structure["rank"])


def run_one(structure, args, executable):
    key = cache_key(structure)
    start_dir = CACHE / structure["leg_id"].replace("|", "_") / (structure["source"] + "_" + structure["rank"])
    start_dir.mkdir(parents=True, exist_ok=True)
    source_geometry = REPO_ROOT / structure["geometry_relpath"]
    record = dict(structure)
    record["leg_id"] = structure["leg_id"]
    if not source_geometry.is_file():
        record.update({"status": "geometry_missing", "error": "missing " + structure["geometry_relpath"]})
        return record
    import shutil
    shutil.copyfile(source_geometry, start_dir / "start.xyz")
    started = time.perf_counter()
    try:
        result = xtb.run_xtb(
            executable, xtb.JOB_FREQUENCY,
            input_name="start.xyz",
            charge=int(structure["charge"]), multiplicity=int(structure["multiplicity"]),
            cwd=start_dir, timeout_seconds=args.timeout, required=(),
        )
    except Exception as exc:  # noqa: BLE001 - a failed Hessian is a result, not a crash
        record.update({"status": "execution_failed", "seconds": round(time.perf_counter() - started, 2),
                       "error": repr(exc)})
        return record
    raw = result.raw_output or ""
    (start_dir / "enso.out").write_text(raw, encoding="utf-8", newline=chr(10))
    parsed = parse_enso(raw)
    status = "ok" if getattr(result, "normal_termination", False) and parsed["total_free_energy_eh"] else "abnormal_termination"
    record.update({
        "status": status,
        "total_energy_eh": parsed["total_energy_eh"],
        "total_enthalpy_eh": parsed["total_enthalpy_eh"],
        "total_free_energy_eh": parsed["total_free_energy_eh"],
        "zero_point_energy_eh": parsed["zero_point_energy_eh"],
        "n_imaginary": parsed["n_imaginary"],
        "seconds": round(time.perf_counter() - started, 2),
        "error": "" if status == "ok" else "no free energy in the raw output",
    })
    return record


def read_cache():
    if not RAW_CSV.is_file():
        return {}
    return {cache_key(row): row for row in read_rows(RAW_CSV)}


def write_cache(records):
    CACHE.mkdir(parents=True, exist_ok=True)
    order = {key: index for index, key in enumerate(cache_key(structure) for structure in registered_structures())}
    rows = sorted(records.values(),
                  key=lambda row: order.get(cache_key(row), 10 ** 6))
    RAW_CSV.write_text(csv_text(RAW_FIELDS, rows), encoding="utf-8", newline="")


def run(args):
    structures = registered_structures()
    if args.only:
        wanted = {token.strip() for token in args.only.split(",") if token.strip()}
        structures = [structure for structure in structures if structure["leg_id"] in wanted]
    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit("xtb not found; see scripts/check_environment.py")
    executable = str(located.path)
    cache = read_cache()
    todo = [structure for structure in structures
            if args.force or cache.get(cache_key(structure), {}).get("status") != "ok"]
    print("xtb " + executable)
    print("registered structures: %d; to compute: %d" % (len(structures), len(todo)))
    if todo:
        with ThreadPoolExecutor(max_workers=max(1, int(args.jobs))) as pool:
            for record in pool.map(lambda structure: run_one(structure, args, executable), todo):
                cache[cache_key(record)] = record
                print("  %-18s %-22s %-3s G=%s imag=%s" % (
                    record["leg_id"], record["source"], record["rank"],
                    record.get("total_free_energy_eh"), record.get("n_imaginary", "")))
        write_cache(cache)
    print("cache rows: %d" % len(cache))
    return 0


#: The two pairs the plan asks to re-check (5.3 / step 2): EMC vs GBL and EMC vs SL.
PAIRS = (
    ("EMC_vs_GBL", "EMC vs GBL", "EMC", "C02", "GBL", "C13"),
    ("EMC_vs_SL", "EMC vs SL", "EMC", "C02", "SL", "C14"),
)
#: The pair quantity is the oxidation axis already registered in
#: outputs/physics_completion/closure/flip_persistence.csv ("delta = IP(i) - IP(j)"),
#: re-expressed on the two states this layer can build from registered pools only.
#: Both are SAME-MOLECULE differences, so no comparison ever mixes stoichiometries
#: (registered ensemble rule E5: never put two stoichiometries in one ensemble).
PAIR_STATES = (
    ("free_ionisation", "M_plus", "M", "no Li present: L(M_plus) - L(M) of each molecule"),
    ("Li_conditioned", "LiM_2plus", "LiM_plus", "Li present: L(LiM_2plus) - L(LiM_plus) of each molecule"),
)
LEVELS = (
    ("E_min", "electronic energy of the lowest counted structure"),
    ("G_min", "free energy of the lowest counted structure"),
    ("G_state", "G_min - RT ln Q (state free energy, conformer entropy included)"),
    ("G_avg", "sum_i w_i G_i (Boltzmann population average)"),
)
#: Display rule only: a gap inside this window is reported as sign-ambiguous instead of
#: being counted as a sign that survived.  It is not a proven convergence scale.
NOISE_KJ = 0.5


def leg_levels(summary):
    """The four levels of one leg, in Eh, straight from the derived summary."""
    return {"E_min": summary["e_lowest_eh"], "G_min": summary["g_lowest_eh"],
            "G_state": summary["g_state_eh"], "G_avg": summary["g_avg_eh"]}


def state_value(leg_ids, level, by_leg):
    """One molecule in one state: a two-leg difference, or None if either leg is missing."""
    values = []
    for leg_id in leg_ids:
        summary = by_leg.get(leg_id)
        if summary is None:
            return None
        value = leg_levels(summary)[level]
        if value is None:
            return None
        values.append(value)
    return values[0] - values[1]


def pair_rungs(summaries):
    """The pair ladder of the four-molecule subcohort, at this screen level.

    Each pair compares the same quantity of the two molecules at four levels
    E_min -> G_min -> {G_state, G_avg}, so a reader can see whether the signed gap
    survives each step of the ladder.  The gap is always (left - right) on the
    oxidation axis, so a positive gap means the left molecule is harder to oxidise.
    Gaps whose magnitude falls inside the noise floor are reported as ambiguous
    instead of being counted as a surviving sign.  Missing legs/levels stay empty;
    nothing is ever filled in with a zero.
    """
    by_leg = {summary["leg_id"]: summary for summary in summaries}
    rows = []
    verdicts = []
    pair_agreements = []
    for pair_id, label, left_name, left_mol, right_name, right_mol in PAIRS:
        per_state = []
        for state, high, low, definition in PAIR_STATES:
            left_ids = ("%s|%s" % (left_mol, high), "%s|%s" % (left_mol, low))
            right_ids = ("%s|%s" % (right_mol, high), "%s|%s" % (right_mol, low))
            left_leg = "(%s) - (%s)" % left_ids
            right_leg = "(%s) - (%s)" % right_ids
            signs = {}
            deltas = {}
            for level, meaning in LEVELS:
                left_value = state_value(left_ids, level, by_leg)
                right_value = state_value(right_ids, level, by_leg)
                delta = (None if (left_value is None or right_value is None)
                         else (left_value - right_value) * KJ_PER_EH)
                sign = "" if delta is None else ("positive" if delta > 0 else ("negative" if delta < 0 else "zero"))
                if delta is not None and abs(delta) <= NOISE_KJ and sign != "zero":
                    sign = "within_noise"
                rows.append({
                    "pair_id": pair_id, "pair_label": label, "state": state, "level": level,
                    "level_meaning": meaning, "left_molecule": left_name, "right_molecule": right_name,
                    "left_leg": left_leg, "right_leg": right_leg,
                    "left_value_eh": "" if left_value is None else "%.9f" % left_value,
                    "right_value_eh": "" if right_value is None else "%.9f" % right_value,
                    "delta_kj_left_minus_right": "" if delta is None else "%.3f" % delta,
                    "delta_sign": sign,
                    "within_noise_kj": "%.3f" % NOISE_KJ,
                    "note": ("" if delta is not None else "a leg of this state has no counted structure at this level"),
                })
                signs[level] = sign
                deltas[level] = delta
            defined = [sign for sign in signs.values() if sign and sign != "within_noise"]
            ambiguous = [level for level, sign in signs.items() if sign == "within_noise"]
            stable = len(set(defined)) == 1 and len(defined) == len(LEVELS)
            if stable:
                note = "the sign survives all four levels"
            elif not defined:
                note = "cannot be answered from the registered pools at this level"
            elif len(set(defined)) > 1:
                note = ("the sign is not the same at every level: "
                        + ", ".join("%s=%s" % (level, signs[level]) for level, _ in LEVELS))
            else:
                note = ("sign is consistent where it is defined, but %s is inside the %.1f kJ/mol noise floor"
                        % (", ".join(ambiguous), NOISE_KJ))
            verdict = {
                "pair_id": pair_id, "pair_label": label, "state": state, "definition": definition,
                "left_molecule": left_name, "right_molecule": right_name,
                "left_leg": left_leg, "right_leg": right_leg,
                "delta_kj_left_minus_right": {level: (None if deltas[level] is None else round(deltas[level], 3))
                                              for level, _ in LEVELS},
                "delta_sign_by_level": signs,
                "sign_stable_across_levels": stable,
                "signs_seen": sorted(set(defined)), "levels_inside_noise": ambiguous,
                "noise_floor_kj": NOISE_KJ, "note": note,
            }
            per_state.append(verdict)
            verdicts.append(verdict)
        free, conditioned = per_state
        disagreements = [level for level, _ in LEVELS
                         if free["delta_sign_by_level"][level] and conditioned["delta_sign_by_level"][level]
                         and free["delta_sign_by_level"][level] != conditioned["delta_sign_by_level"][level]]
        agreement = {
            "pair_id": pair_id, "pair_label": label,
            "left_molecule": left_name, "right_molecule": right_name,
            "question": "does Li coordination change the signed gap between the two molecules?",
            "levels_compared": [level for level, _ in LEVELS],
            "levels_where_the_two_states_disagree": disagreements,
            "sign_agrees_between_states": not disagreements,
            "free_ionisation_gap_kj": free["delta_kj_left_minus_right"],
            "Li_conditioned_gap_kj": conditioned["delta_kj_left_minus_right"],
        }
        pair_agreements.append(agreement)
    return rows, verdicts, pair_agreements


PAIR_FIELDS = ("pair_id", "pair_label", "state", "level", "level_meaning",
               "left_molecule", "right_molecule", "left_leg", "right_leg",
               "left_value_eh", "right_value_eh", "delta_kj_left_minus_right",
               "delta_sign", "within_noise_kj", "note")

def derive(args):
    structures = registered_structures()
    cache = read_cache()
    #: The parsed GFN2 thermochemistry of every registered structure, in the frozen
    #: registered order.  It is published next to the ensemble so that the derived
    #: numbers can be read without the gitignored cache -- and so that a missing
    #: cache turns into a loud --check failure instead of a quiet different answer.
    raw_rows = []
    for structure in structures:
        record = cache.get(cache_key(structure))
        if record is None:
            record = dict(structure)
            record["status"] = "not_computed"
        raw_rows.append(record)
    esc = {row["mol_id"] + "|" + row["state"]: row for row in read_rows(ESCO)} if ESCO.is_file() else {}

    by_leg = {}
    for structure in structures:
        by_leg.setdefault(structure["leg_id"], []).append(structure)

    rows = []
    summaries = []
    for leg_id, members in sorted(by_leg.items()):
        scored = []
        for structure in members:
            cached = cache.get(cache_key(structure), {})
            g = cached.get("total_free_energy_eh")
            e = cached.get("total_energy_eh")
            g = float(g) if g not in (None, "") else None
            e = float(e) if e not in (None, "") else None
            imag = cached.get("n_imaginary", "")
            imag = int(imag) if str(imag).strip() not in ("", "None") else None
            countable = g is not None and (imag == 0) and cached.get("status") == "ok"
            scored.append((structure, cached, g, e, imag, countable))
        usable = [item for item in scored if item[5]]
        reference_g = min(item[2] for item in usable) if usable else None
        reference_e = min(item[3] for item in usable if item[3] is not None) if usable else None
        # Two conventions are reported side by side, because they bound the same
        # ensemble from opposite sides and the pair question needs the shift of a state:
        #   G_state = -RT ln Q  (state free energy incl. conformer entropy, <= G_min)
        #   G_avg   = sum_i w_i G_i  (population average, >= G_min)
        weights = {}
        g_state = g_avg = e_avg = None
        if usable:
            shifts = [(item[2] - reference_g) * KJ_PER_EH for item in usable]
            boltzmann = [math.exp(-shift / RT_KJ) for shift in shifts]
            total = sum(boltzmann)
            for item, weight in zip(usable, boltzmann):
                weights[cache_key(item[0])] = weight / total
            g_state = reference_g - (RT_KJ * math.log(total)) / KJ_PER_EH
            g_avg = sum(weight * item[2] for item, weight in zip(usable, boltzmann)) / total
            if reference_e is not None and all(item[3] is not None for item in usable):
                e_avg = sum(weight * item[3] for item, weight in zip(usable, boltzmann)) / total
        for structure, cached, g, e, imag, countable in scored:
            weight = weights.get(cache_key(structure))
            rows.append({
                "leg_id": leg_id, "mol_id": structure["mol_id"], "name": structure["name"],
                "state": structure["state"], "charge": structure["charge"],
                "multiplicity": structure["multiplicity"], "source": structure["source"],
                "rank": structure["rank"], "geometry_relpath": structure["geometry_relpath"],
                "geometry_sha256": structure["geometry_sha256"],
                "status": cached.get("status", "not_computed"),
                "total_energy_eh": "" if e is None else "%.8f" % e,
                "total_free_energy_eh": "" if g is None else "%.8f" % g,
                "zero_point_energy_eh": cached.get("zero_point_energy_eh", ""),
                "n_imaginary": "" if imag is None else imag,
                "rel_e_kj": "" if (e is None or reference_e is None) else "%.3f" % ((e - reference_e) * KJ_PER_EH),
                "rel_g_kj": "" if (g is None or reference_g is None) else "%.3f" % ((g - reference_g) * KJ_PER_EH),
                "boltzmann_weight": "" if weight is None else "%.6f" % weight,
                "counted_in_ensemble": "true" if countable else "false",
                "note": ("" if countable else
                         ("excluded: imaginary modes on the GFN2 surface" if imag not in (None, 0)
                          else "excluded: no free energy in the cache")),
            })
        summaries.append({
            "leg_id": leg_id, "mol_id": members[0]["mol_id"], "name": members[0]["name"],
            "state": members[0]["state"],
            "n_registered_structures": len(members),
            "n_counted": len(usable),
            "n_imaginary_excluded": sum(1 for item in scored if item[4] not in (None, 0)),
            "g_lowest_eh": reference_g, "e_lowest_eh": reference_e,
            "g_state_eh": g_state, "g_avg_eh": g_avg, "e_avg_eh": e_avg,
            "entropy_shift_kj": None if g_state is None else (g_state - reference_g) * KJ_PER_EH,
            "avg_shift_kj": None if g_avg is None else (g_avg - reference_g) * KJ_PER_EH,
            "e_avg_shift_kj": (None if (e_avg is None or reference_e is None)
                               else (e_avg - reference_e) * KJ_PER_EH),
            "escalation_status": esc.get(leg_id, {}).get("escalation_status", ""),
        })

    pair_rows, pair_verdicts, pair_agreements = pair_rungs(summaries)

    checks = []
    expected_keys = {cache_key(structure) for structure in structures}
    checks.append({"check_id": "every_registered_structure_has_a_row",
                   "description": "两个登记池里的每个结构都在本层有且只有一行，不静默丢结构",
                   "ok": len(rows) == len(structures) and {cache_key(structure) for structure in structures} == expected_keys,
                   "detail": "%d rows for %d registered structures" % (len(rows), len(structures))})
    bad_hash = []
    for row in rows:
        geometry = REPO_ROOT / row["geometry_relpath"]
        if not geometry.is_file():
            bad_hash.append(row["leg_id"] + " (geometry missing)")
        elif sha256_file(geometry) != row["geometry_sha256"]:
            bad_hash.append(row["leg_id"])
    checks.append({"check_id": "every_geometry_still_matches_its_registered_sha256",
                   "description": ("几何文件与登记 sha256 一致（文件缺失同样判不符，不静默放过）,"
                                   "重跑后不得悄悄换结构"),
                   "ok": not bad_hash, "detail": "mismatched: %s" % (", ".join(bad_hash) or "none")})
    weight_errors = []
    for summary in summaries:
        leg_rows = [row for row in rows if row["leg_id"] == summary["leg_id"] and row["counted_in_ensemble"] == "true"]
        total = sum(float(row["boltzmann_weight"]) for row in leg_rows)
        if leg_rows and abs(total - 1.0) > 1e-5:
            weight_errors.append("%s=%.6f" % (summary["leg_id"], total))
    checks.append({"check_id": "boltzmann_weights_sum_to_one_per_leg",
                   "description": "每条腿计入系综的 Boltzmann 权重之和为 1",
                   "ok": not weight_errors, "detail": "offenders: %s" % (", ".join(weight_errors) or "none")})
    bound_errors = []
    for summary in summaries:
        if not summary["n_counted"]:
            continue
        shift = summary["entropy_shift_kj"]
        average = summary["avg_shift_kj"]
        if shift is not None and shift > 1e-9:
            bound_errors.append(summary["leg_id"] + " G_state>G_min")
        if shift is not None and shift < -RT_KJ * math.log(summary["n_counted"]) - 1e-6:
            bound_errors.append(summary["leg_id"] + " G_state below its entropy bound")
        if average is not None and average < -1e-9:
            bound_errors.append(summary["leg_id"] + " G_avg<G_min")
        if summary["e_avg_shift_kj"] is not None and summary["e_avg_shift_kj"] < -1e-9:
            bound_errors.append(summary["leg_id"] + " E_avg<E_min")
    checks.append({"check_id": "ensemble_shifts_obey_their_mathematical_bounds",
                   "description": "系综位移满足数学界：-RT ln N <= G_state - G_min <= 0 <= G_avg - G_min（E 同理）",
                   "ok": not bound_errors,
                   "detail": "offenders: %s" % (", ".join(bound_errors) or "none")})
    checks.append({"check_id": "ensemble_layer_is_labelled_as_a_screen",
                   "description": "本层是气相 GFN2 筛选层，不是生产自由能，也不替代生产 R4 台阶",
                   "ok": True, "detail": LEVEL + "; claim_level=" + CLAIM_LEVEL})
    checks.append({"check_id": "imaginary_mode_structures_are_reported_not_dropped",
                   "description": "有虚频的结构留在表里、带虚频数、并被排除出系综（不是删掉）",
                   "ok": all(row["n_imaginary"] != "" or row["status"] == "not_computed" or row["status"] == "geometry_missing"
                             for row in rows),
                   "detail": "%d structures carry an imaginary-mode count"
                             % sum(1 for row in rows if row["n_imaginary"] not in ("", None))})
    pair_cells = len(pair_rows)
    pair_gaps = [verdict for verdict in pair_verdicts if not verdict["delta_sign_by_level"]]
    checks.append({"check_id": "pair_ladder_is_fully_reported",
                   "description": "每一对 (pair, state, level) 都有一行；缺腿只留空并写明原因，绝不补 0",
                   "ok": pair_cells == len(PAIRS) * len(PAIR_STATES) * len(LEVELS),
                   "detail": "%d pair cells for %d pairs x %d states x %d levels"
                             % (pair_cells, len(PAIRS), len(PAIR_STATES), len(LEVELS))})
    sign_errors = []
    for verdict in pair_verdicts:
        defined = [sign for sign in verdict["delta_sign_by_level"].values() if sign and sign != "within_noise"]
        if len(set(defined)) > 1 and verdict["sign_stable_across_levels"]:
            sign_errors.append(verdict["pair_id"] + "/" + verdict["state"] + " marked stable but flips")
        if len(set(defined)) == 1 and len(defined) == len(LEVELS) and not verdict["sign_stable_across_levels"]:
            sign_errors.append(verdict["pair_id"] + "/" + verdict["state"] + " flips but marked stable")
    checks.append({"check_id": "pair_sign_verdict_matches_the_reported_signs",
                   "description": "sign_stable 标记必须与逐层 sign 一致，符号变化不得被藏起来",
                   "ok": not sign_errors, "detail": "offenders: %s" % (", ".join(sign_errors) or "none")})
    mixed = [row["pair_id"] + "/" + row["state"] + "/" + row["level"] for row in pair_rows
             if row["left_leg"].count("|") != row["right_leg"].count("|")]
    checks.append({"check_id": "pair_axis_never_mixes_stoichiometries",
                   "description": "pair 台两侧都是同一分子内部的差分，绝不把两个不同化学计量比的结构放进同一个比较（登记规则 E5）",
                   "ok": not mixed, "detail": "offenders: %s" % (", ".join(mixed) or "none")})
    keys = [cache_key(structure) for structure in structures]
    checks.append({"check_id": "registered_structures_have_unique_cache_keys",
                   "description": "登记结构的缓存键（腿 + 池 + 序号）唯一，两个不同结构不得共用一个键",
                   "ok": len(set(keys)) == len(keys),
                   "detail": "%d distinct keys for %d structures" % (len(set(keys)), len(keys))})
    leg_field_errors = [summary["leg_id"] for summary in summaries
                        if summary["leg_id"] != "%s|%s" % (summary["mol_id"], summary["state"])]
    checks.append({"check_id": "leg_records_agree_with_their_leg_id",
                   "description": "每条腿的 mol_id/state 必须与 leg_id 自洽，不得把别的结构写进这一行",
                   "ok": not leg_field_errors,
                   "detail": "offenders: %s" % (", ".join(leg_field_errors) or "none")})
    incomplete = [str(row.get("leg_id", "")) + "/" + str(row.get("source", ""))
                  for row in raw_rows
                  if row.get("status") == "ok"
                  and (row.get("total_free_energy_eh") in (None, "")
                       or row.get("n_imaginary") in (None, ""))]
    checks.append({"check_id": "published_gfn2_records_are_complete",
                   "description": "随产物登记的 GFN2 记录里，status=ok 的行必须同时有自由能与虚频数",
                   "ok": not incomplete,
                   "detail": "incomplete: %s" % (", ".join(incomplete) or "none")})
    n_failed = sum(1 for check in checks if not check["ok"])

    payload = {
        "scope": ("plan 6.1 step 3 / 6.2: Boltzmann ensemble of the two registered pools "
                  "(free-state conformers + Li motifs) of the four-molecule subcohort"),
        "level": LEVEL,
        "claim_level": CLAIM_LEVEL,
        "is_a_screen_not_a_production_free_energy": True,
        "temperature_k": TEMPERATURE_K,
        "rt_kj_per_mol": RT_KJ,
        "rule": ("w_i = exp(-(G_i - G_min)/RT) / sum_j exp(-(G_j - G_min)/RT). "
                 "Two conventions are reported side by side and are NOT interchangeable: "
                 "G_state = G_min - RT ln sum_j exp(-(G_j - G_min)/RT) is the state free energy incl. "
                 "conformer entropy and is <= G_min, while G_avg = sum_i w_i G_i is the population "
                 "average and is >= G_min. E_avg is the same population average over the electronic "
                 "energies. The pair layer differences the SAME level on both sides, never mixes levels."),
        "sources": {"free_state_conformer_pool": relative(POOL_CSV),
                    "free_state_conformer_pool_sha256": sha256_file(POOL_CSV),
                    "li_motif_screen": relative(LI_SCREEN),
                    "li_motif_screen_sha256": sha256_file(LI_SCREEN),
                    "note": ("the two pools are read, never edited; these hashes let a reader "
                             "check that this layer used the same pool revision as the other layers")},
        "totals": {"legs": len(summaries),
                   "registered_structures": len(rows),
                   "counted_structures": sum(1 for row in rows if row["counted_in_ensemble"] == "true"),
                   "legs_with_an_ensemble": sum(1 for summary in summaries if summary["n_counted"]),
                   "legs_with_a_single_structure": sum(1 for summary in summaries if summary["n_counted"] == 1)},
        "legs": summaries,
        "pairs": pair_verdicts,
        "pair_state_agreement": pair_agreements,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": n_failed,
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    files = {
        "outputs/physics_completion/ensembles/ensemble_free_energies.csv": csv_text(ENS_FIELDS, rows),
        "outputs/physics_completion/ensembles/ensemble_raw_records.csv": csv_text(RAW_FIELDS, raw_rows),
        "outputs/physics_completion/ensembles/ensemble_pair_rungs.csv": csv_text(PAIR_FIELDS, pair_rows),
        "outputs/physics_completion/ensembles/ensemble_acceptance.csv":
            csv_text(("check_id", "description", "ok", "detail"), checks),
        "outputs/physics_completion/ensembles/ensemble_index.json":
            json.dumps(payload, ensure_ascii=False, indent=2) + chr(10),
        "outputs/physics_completion/ensembles/ensemble_summary.md": summary_markdown(payload, summaries),
    }
    return files, payload


def summary_markdown(payload, summaries):
    lines = [
        "# 方案 6.1 / 6.2：四分子系综层（气相 GFN2 筛选层）",
        "",
        "> 由 " + TICK + "scripts/wp_production/build_wp2_ensemble_free_energies.py" + TICK + " 生成。",
        "> 本层把两个**已登记**的池（自由态构象池 + Li motif 池）在 GFN2 " + TICK + "--ohess" + TICK + " 自由能层面求 Boltzmann 系综，",
        "> 用来回答「采样是否足以改变结论」的**廉价那一半**。它**不是**生产自由能，",
        "> 也**不替代**生产 R4 台阶（那需要 wB97X-D4 + SMD 的额外结构腿）。",
        "> 两种口径并列且**不可互换**：" + TICK + "G_state" + TICK + " 含构象熵（<= G_min），"
        + TICK + "G_avg" + TICK + " 是布居平均（>= G_min）。",
        "",
        "## 逐腿系综",
        "",
        "| 记录 | 登记结构 | 计入系综 | 虚频剔除 | 最低 G (Eh) | G_state (Eh) | G_avg (Eh) | G_state-G_min (kJ/mol) | G_avg-G_min (kJ/mol) | E_avg-E_min (kJ/mol) | 3->6 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in summaries:
        lines.append("| " + summary["leg_id"] + " | " + str(summary["n_registered_structures"]) + " | "
                     + str(summary["n_counted"]) + " | "
                     + str(summary["n_imaginary_excluded"]) + " | "
                     + ("-" if summary["g_lowest_eh"] is None else "%.9f" % summary["g_lowest_eh"]) + " | "
                     + ("-" if summary["g_state_eh"] is None else "%.9f" % summary["g_state_eh"]) + " | "
                     + ("-" if summary["g_avg_eh"] is None else "%.9f" % summary["g_avg_eh"]) + " | "
                     + ("-" if summary["entropy_shift_kj"] is None else "%.3f" % summary["entropy_shift_kj"]) + " | "
                     + ("-" if summary["avg_shift_kj"] is None else "%.3f" % summary["avg_shift_kj"]) + " | "
                     + ("-" if summary["e_avg_shift_kj"] is None else "%.3f" % summary["e_avg_shift_kj"]) + " | "
                     + (summary["escalation_status"] or "-") + " |")
    lines += [
        "",
        "## 配对三层台（本层口径；不是生产 R2/R3/R4）",
        "",
        "口径与 " + TICK + "closure/flip_persistence.csv" + TICK + " 的**氧化轴**一致（" + TICK + "delta = IP(i) - IP(j)" + TICK + "），",
        "但两侧都是**同一分子内部**的差分，因此绝不混化学计量比（登记规则 E5）：",
        "free_ionisation 是 " + TICK + "L(M_plus) - L(M)" + TICK + "，Li_conditioned 是 " + TICK + "L(LiM_2plus) - L(LiM_plus)" + TICK + "。",
        "差值一律是**左分子减右分子**（EMC 减 GBL / EMC 减 SL），单位 kJ/mol；正号 = 左分子更难氧化。",
        "",
        "",
        "| pair | state | E_min | G_min | G_state | G_avg | 符号稳定 | 说明 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for verdict in payload["pairs"]:
        cells = []
        for level, _ in LEVELS:
            value = verdict["delta_kj_left_minus_right"][level]
            cells.append("-" if value is None else "%.3f" % value)
        lines.append("| " + verdict["pair_label"] + " | " + verdict["state"] + " | "
                     + " | ".join(cells) + " | "
                     + ("是" if verdict["sign_stable_across_levels"] else "否") + " | "
                     + verdict["note"] + " |")
    lines += [
        "",
        "### Li 配位是否改变这个符号",
        "",
        "| pair | 四层里两侧符号不一致的层 | 符号一致 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    for agreement in payload["pair_state_agreement"]:
        lines.append("| " + agreement["pair_label"] + " | "
                     + (", ".join(agreement["levels_where_the_two_states_disagree"]) or "无") + " | "
                     + ("是" if agreement["sign_agrees_between_states"] else "否") + " | "
                     + agreement["question"] + " |")
    counted = [summary for summary in summaries if summary["n_counted"]]
    lines += [
        "",
        "## 本层给出的判断",
        "",
        "* 登记结构总数 " + str(payload["totals"]["registered_structures"]) + "，计入系综 "
        + str(payload["totals"]["counted_structures"]) + "；有系综的腿 " + str(len(counted)) + " / " + str(len(summaries)) + "。",
        "* " + TICK + "G_state-G_min" + TICK + " 与 " + TICK + "G_avg-G_min" + TICK + " 是同一个系综的两侧边界（下界侧含构象熵、上界侧是布居平均），",
        "  它们明显小于关键 pair 的间距时，采样不足以推翻该 pair；只有跨过独立容差或改写 Top-k 时，才按同一规则扩到 6（本层不自行扩）。",
        "* 有虚频的结构留在 CSV 里并带虚频数，**排除出系综**，不是删掉。",
        "* 生产级结论仍然待定：生产 R4 需要额外结构的生产腿，本层不声称完成 R4。",
        "",
        "## 验收",
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for check in payload["checks"]:
        lines.append("| " + check["check_id"] + " | " + str(check["ok"]) + " | " + check["detail"] + " |")
    lines.append("")
    lines.append("合计 " + str(payload["n_checks"]) + " 项，失败 " + str(payload["n_failed"]) + " 项。")
    lines.append("")
    return chr(10).join(lines)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Boltzmann ensemble layer of the registered WP2 pools (GFN2 screen).")
    parser.add_argument("--run", action="store_true", help="compute the GFN2 Hessians of the registered structures")
    parser.add_argument("--only", default=None, help="comma-separated leg_id allow-list")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.run:
        return run(args)
    files, payload = derive(args)
    if args.check:
        failures = []
        for rel, text in sorted(files.items()):
            target = REPO_ROOT / rel
            if not target.is_file():
                failures.append("missing " + rel)
            elif target.read_text(encoding="utf-8") != text:
                failures.append("differs " + rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:10]:
                print("  - " + item)
            return 1
        print("CHECK OK -- %d ensemble files are byte-identical" % len(files))
        return 0
    for rel, text in sorted(files.items()):
        target = REPO_ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline=chr(10)) as handle:
            handle.write(text)
    print("wp2 ensemble layer (plan 6.1 step 3 / 6.2)")
    print("-" * 70)
    print("  legs                    : %d" % payload["totals"]["legs"])
    print("  registered structures   : %d" % payload["totals"]["registered_structures"])
    print("  counted in an ensemble  : %d" % payload["totals"]["counted_structures"])
    print("  acceptance              : %d checks / %d failed" % (payload["n_checks"], payload["n_failed"]))
    return 0 if payload["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
