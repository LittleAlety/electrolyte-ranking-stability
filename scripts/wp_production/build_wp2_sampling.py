# -*- coding: utf-8 -*-
"""方案 6.1 的小规模构象采样（第 3 步）：先只覆盖决定两对翻转的自由态构象。

两级：
  * 计算级（--run）：RDKit ETKDG/MMFF 撒 n_conformers 个起点 -> 各态在其电荷与自旋下跑
    xTB GFN2 Opt，原始结果缓存到仓库外 work/sampling/**（同时作为复现证据被 provenance 收录）；
  * 计算级（--run2）：对所有 8 个分子-态**统一**扩到一个更大的池（64 起点、另一个登记 seed），
    结果按 kind=conformer_r2 追加进同一缓存，绝不覆盖第 1 轮的行；
  * 派生级（默认 / --check）：只从缓存读回，写出 outputs/physics_completion/sampling/**，
    包括两轮逐态判定、每态独立低能结构集合（含几何路径与 sha256）与 3 -> 6 升级登记。

口径纪律：
  * 采样层是**气相 GFN2-xTB 筛选**，不是生产级的 wB97X-D4/SMD(acetonitrile)；
    它只回答「单一代表结构是否落在同一极小附近」，不用于给出生产自由能；
  * 每个态保留最多 3 个独立低能极小（池里不足 3 个就保留实际数量，并登记 pool_limited）；
    3 -> 6 的升级只有在算出第 1 轮自由能、且变化跨过独立容差时才触发；
  * Li 配位态的 motif 采样不在本轮：它需要单独的配位起点构造，显式登记为 not_computed。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_wp2_sampling.py --run
    .venv\\Scripts\\python.exe scripts\\build_wp2_sampling.py --run2
    .venv\\Scripts\\python.exe scripts\\build_wp2_sampling.py
    .venv\\Scripts\\python.exe scripts\\build_wp2_sampling.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "work" / "sampling"
WP2PROD = REPO / "work" / "wp2prod"
RAW = WORK / "xtb_results.csv"
OUTDIR = REPO / "outputs" / "physics_completion" / "sampling"

XTB = Path(r"E:\orca_6_1_1\xtb-6.7.1pre\xtb.exe")
HA_TO_KCAL = 627.5094740631
N_CONFORMERS = 12
NUM_CONFS_REQUEST = 16
SEED = 20261010
KEEP = 3
DUP_TOL_KCAL = 0.10
ESCALATE_TOL_KCAL = 1.00
# 第 2 轮：对所有分子-态统一用更大的池（同一 seed 与起点数），不逐态调参。
NUM_CONFS_REQUEST_R2 = 64
SEED_R2 = 20261011
KIND_R1 = "conformer"
KIND_R2 = "conformer_r2"
PREFIX_R1 = "c"
PREFIX_R2 = "r2_c"
MAX_POOL = 6
ESCALATION_RULE = ("extend 3 -> 6 only if the 3 -> 6 free-energy change crosses the independent "
                   "tolerance or the Top-k set")
POOL_NOTE = ("a gas-phase GFN2 minimum kept as a ready-to-run structure; running it at the "
             "production level is a registered 3 -> 6 escalation, not a substitute for the "
             "single-conformer production label")

MOLS = [("C01", "DMC", "COC(=O)OC"), ("C02", "EMC", "CCOC(=O)OC"),
        ("C13", "GBL", "O=C1CCCO1"), ("C14", "SL", "O=S1(=O)CCCC1")]
ROUND1_STATES = [("M", 0, 0), ("M_plus", 1, 1)]

RE_TOTAL = re.compile(r"total energy\s*:?\s+(-?\d+\.\d+)\s*Eh")
LEVEL = "xTB GFN2 (gas phase) conformer screening"

RAW_FIELDS = ("mol_id", "name", "state", "charge", "multiplicity", "kind", "index",
              "energy_eh", "converged", "n_atoms")

RESULT_FIELDS = ("mol_id", "name", "state", "charge", "multiplicity", "level",
                 "n_conformers_embedded", "n_conformers_optimised", "n_distinct_minima",
                 "min_energy_eh", "top2_rel_kcal", "top3_rel_kcal", "production_geom_rel_kcal",
                 "frozen_start_rel_kcal", "production_geometry_source",
                 "within_escalation_tolerance", "verdict", "note")

ACC_FIELDS = ("check_id", "description", "ok", "detail")

CONFORMER_SET_FIELDS = ("mol_id", "name", "state", "charge", "multiplicity", "pool", "rank",
                        "n_atoms", "xtb_energy_eh", "rel_kcal", "source_kind", "source_index",
                        "geometry_relpath", "geometry_sha256", "selected_round1", "note")

ESCALATION_FIELDS = ("mol_id", "name", "state", "n_distinct_minima", "n_structures_kept",
                     "structures_round1", "round2_max", "pool_limited", "escalation_status",
                     "rule", "note")

NOTES = ("gas-phase GFN2-xTB screening only: it says whether one representative structure sits "
         "at/near the screened minimum, NOT a production free energy; the production level stays "
         "wB97X-D4 + SMD(acetonitrile)")


def csv_text(fieldnames, rows):
    out = io.StringIO()
    out.write(",".join(fieldnames) + "\n")
    for row in rows:
        cells = []
        for key in fieldnames:
            value = row.get(key, "")
            value = "" if value is None else str(value)
            if "," in value or '"' in value or "\n" in value:
                value = '"' + value.replace('"', '""') + '"'
            cells.append(value)
        out.write(",".join(cells) + "\n")
    return out.getvalue()


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def read_raw():
    if not RAW.is_file():
        return []
    with RAW.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_raw(rows):
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(csv_text(RAW_FIELDS, rows), encoding="utf-8", newline="\n")


def production_geometry(name, state):
    if state == "M":
        return REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2.xyz"), "frozen r2SCAN-3c neutral"
    if state == "M_plus":
        return REPO / "outputs/week4/t2_opt_freq" / name / (name + "_G2_cation.xyz"), "frozen r2SCAN-3c cation"
    frozen = REPO / "outputs/week5/c1" / name / (name + "_m1_G2Li.xyz")
    if frozen.is_file():
        return frozen, "frozen r2SCAN-3c Li complex"
    return REPO / "work/audit/EMC_Li" / (name + "_m1_G2Li.xyz"), "audit Li complex"


def dft_geometry(name, state):
    produced = WP2PROD / name / state / ("%s_%s_opt.xyz" % (name, state))
    return produced if produced.is_file() else None


def embed(smiles, count, seed):
    from rdkit import Chem
    from rdkit.Chem import AllChem
    molecule = Chem.AddHs(Chem.MolFromSmiles(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    # 不做 RMS 剪枝：刚性分子本来就只有一两个极小，柔性分子的重复起点在优化后按能量去重。
    params.pruneRmsThresh = -1.0
    ids = AllChem.EmbedMultipleConfs(molecule, numConfs=count, params=params)
    AllChem.MMFFOptimizeMoleculeConfs(molecule, maxIters=2000)
    blocks = []
    for conf_id in ids:
        block = Chem.MolToXYZBlock(molecule, confId=conf_id)
        if block:
            blocks.append(block)
    return blocks


def xyz_block(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    n_atoms = int(lines[0].split()[0])
    return "\n".join(lines[:n_atoms + 2]) + "\n"


def run_xtb(directory, block, charge, multiplicity, do_opt):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "geom.xyz").write_text(block, encoding="utf-8", newline="\n")
    args = [str(XTB), "geom.xyz", "--gfn", "2", "--chrg", str(charge), "--uhf", str(multiplicity)]
    if do_opt:
        args += ["--opt", "tight"]
    proc = subprocess.run(args, cwd=str(directory), capture_output=True, text=True, errors="replace")
    text = proc.stdout + "\n" + proc.stderr
    energies = RE_TOTAL.findall(text)
    energy = energies[-1] if energies else ""
    converged = "true" if (not do_opt or "GEOMETRY OPTIMIZATION CONVERGED" in text
                           or ".xtboptok" in str([p.name for p in directory.iterdir()])) else "false"
    return energy, converged


def compute(rows=None, kind=KIND_R1, count=NUM_CONFS_REQUEST, seed=SEED, prefix=PREFIX_R1,
            with_references=True):
    """跑一轮构象筛选：round 1 从零开始；round 2 读回既有缓存后追加，绝不覆盖 round 1。"""
    rows = [] if rows is None else list(rows)
    have = {(row["name"], row["state"], row["kind"], row["index"]) for row in rows}
    for mol_id, name, smiles in MOLS:
        blocks = embed(smiles, count, seed)
        for state, charge, uhf in ROUND1_STATES:
            for index, block in enumerate(blocks):
                if (name, state, kind, str(index)) in have:
                    continue
                energy, converged = run_xtb(WORK / name / state / ("%s%02d" % (prefix, index)),
                                            block, charge, uhf, True)
                rows.append({"mol_id": mol_id, "name": name, "state": state, "charge": str(charge),
                             "multiplicity": str(uhf + 1), "kind": kind, "index": str(index),
                             "energy_eh": energy, "converged": converged,
                             "n_atoms": str(int(block.splitlines()[0].split()[0]))})
            if not with_references:
                continue
            source, source_note = production_geometry(name, state)
            reference = dft_geometry(name, state)
            geometry = reference if reference is not None else source
            energy, converged = run_xtb(WORK / name / state / "production_geom",
                                        xyz_block(geometry), charge, uhf, False)
            frozen_energy, frozen_ok = run_xtb(WORK / name / state / "frozen_start_geom",
                                               xyz_block(source), charge, uhf, False)
            rows.append({"mol_id": mol_id, "name": name, "state": state, "charge": str(charge),
                         "multiplicity": str(uhf + 1), "kind": "frozen_start_sp",
                         "index": "frozen", "energy_eh": frozen_energy, "converged": frozen_ok,
                         "n_atoms": str(int(xyz_block(source).splitlines()[0].split()[0]))})
            rows.append({"mol_id": mol_id, "name": name, "state": state, "charge": str(charge),
                         "multiplicity": str(uhf + 1), "kind": "production_geometry_sp",
                         "index": "ref", "energy_eh": energy, "converged": converged,
                         "n_atoms": str(int(xyz_block(geometry).splitlines()[0].split()[0]))})
            print("%-4s %-8s embedded=%d production_ref=%.6f" % (name, state, len(blocks), float(energy)))
    write_raw(rows)
    return rows


def cluster_reps(energies, tol):
    """按能量把构象聚成若干极小，返回每个极小的最低能量（升序）。"""
    reps = []
    for value in sorted(energies):
        if not reps or value - reps[-1] > tol:
            reps.append(value)
    return reps


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def conformer_dir(name, state, kind, index):
    prefix = PREFIX_R2 if kind == KIND_R2 else PREFIX_R1
    return WORK / name / state / ("%s%02d" % (prefix, int(index)))


def select_pool(raw):
    """把两轮的构象合成一个池，按能量聚成独立极小，取每个极小的最低能代表（最多 MAX_POOL 个）。"""
    set_rows = []
    escalation_rows = []
    for mol_id, name, smiles in MOLS:
        for state, charge, uhf in ROUND1_STATES:
            conf = [row for row in raw if row["name"] == name and row["state"] == state
                    and row["kind"] in (KIND_R1, KIND_R2) and row["energy_eh"]]
            if not conf:
                escalation_rows.append({
                    "mol_id": mol_id, "name": name, "state": state,
                    "n_distinct_minima": "0", "n_structures_kept": "0", "structures_round1": "0",
                    "round2_max": str(MAX_POOL), "pool_limited": "",
                    "escalation_status": "not_computed", "rule": ESCALATION_RULE,
                    "note": "no cached pool rows"})
                continue
            ordered = sorted(conf, key=lambda item: float(item["energy_eh"]))
            reps = []
            for item in ordered:
                value = float(item["energy_eh"])
                if not reps or value - reps[-1][0] > DUP_TOL_KCAL / HA_TO_KCAL:
                    reps.append((value, item))
            reps = reps[:MAX_POOL]
            minimum = reps[0][0]
            for rank, (value, item) in enumerate(reps, start=1):
                geometry = conformer_dir(name, state, item["kind"], item["index"]) / "xtbopt.xyz"
                set_rows.append({
                    "mol_id": mol_id, "name": name, "state": state, "charge": str(charge),
                    "multiplicity": str(uhf + 1), "pool": "union_round1_round2", "rank": str(rank),
                    "n_atoms": item["n_atoms"], "xtb_energy_eh": "%.9f" % value,
                    "rel_kcal": "%.3f" % ((value - minimum) * HA_TO_KCAL),
                    "source_kind": item["kind"], "source_index": item["index"],
                    "geometry_relpath": geometry.relative_to(REPO).as_posix(),
                    "geometry_sha256": sha256_of(geometry),
                    "selected_round1": str(rank <= KEEP).lower(), "note": POOL_NOTE})
            escalation_rows.append({
                "mol_id": mol_id, "name": name, "state": state,
                "n_distinct_minima": str(len(reps)), "n_structures_kept": str(len(reps)),
                "structures_round1": str(min(KEEP, len(reps))), "round2_max": str(MAX_POOL),
                "pool_limited": str(len(reps) < KEEP).lower(),
                "escalation_status": "registered_pending_round1_free_energy_check",
                "rule": ESCALATION_RULE,
                "note": ("the union pool (%d + %d ETKDG starts) produced %d independent GFN2 minima; "
                         "one structure per minimum is kept, and the registered rule extends 3 -> 6 "
                         "only if the 3 -> 6 free-energy change crosses the independent tolerance"
                         % (NUM_CONFS_REQUEST, NUM_CONFS_REQUEST_R2, len(reps)))})
    return set_rows, escalation_rows


def evaluate_round(raw, kind):
    """按给定轮次算出每态的判定行；两轮复用同一口径，便于逐字对照。"""
    results = []
    for mol_id, name, smiles in MOLS:
        for state, charge, uhf in ROUND1_STATES:
            conf = [row for row in raw if row["name"] == name and row["state"] == state
                    and row["kind"] == kind and row["energy_eh"]]
            ref = next((row for row in raw if row["name"] == name and row["state"] == state
                        and row["kind"] == "production_geometry_sp" and row["energy_eh"]), None)
            source, source_note = production_geometry(name, state)
            reference = dft_geometry(name, state)
            tested_note = ("DFT-optimised production geometry" if reference is not None
                           else "frozen start geometry (production leg not yet produced)")
            row = {key: "" for key in RESULT_FIELDS}
            row.update({"mol_id": mol_id, "name": name, "state": state, "charge": str(charge),
                        "multiplicity": str(uhf + 1), "level": LEVEL,
                        "production_geometry_source": tested_note})
            if not conf:
                row["verdict"] = "not_computed"
                row["note"] = "no cached xTB results; run `scripts/wp_production/build_wp2_sampling.py --run` first"
                results.append(row)
                continue
            values = sorted(float(item["energy_eh"]) for item in conf)
            minimum = values[0]
            reps = cluster_reps(values, DUP_TOL_KCAL / HA_TO_KCAL)
            row["n_conformers_embedded"] = str(len(conf))
            row["n_conformers_optimised"] = str(len(values))
            row["n_distinct_minima"] = str(len(reps))
            row["min_energy_eh"] = "%.9f" % minimum
            row["top2_rel_kcal"] = "%.3f" % ((reps[1] - minimum) * HA_TO_KCAL) if len(reps) > 1 else ""
            row["top3_rel_kcal"] = "%.3f" % ((reps[2] - minimum) * HA_TO_KCAL) if len(reps) > 2 else ""
            frozen = next((item for item in raw if item["name"] == name and item["state"] == state
                           and item["kind"] == "frozen_start_sp" and item["energy_eh"]), None)
            if frozen is not None:
                row["frozen_start_rel_kcal"] = "%.3f" % ((float(frozen["energy_eh"]) - minimum)
                                                         * HA_TO_KCAL)
            if ref is not None:
                delta = (float(ref["energy_eh"]) - minimum) * HA_TO_KCAL
                row["production_geom_rel_kcal"] = "%.3f" % delta
                row["within_escalation_tolerance"] = str(abs(delta) <= ESCALATE_TOL_KCAL).lower()
                row["verdict"] = ("single_conformer_representative" if abs(delta) <= ESCALATE_TOL_KCAL
                                  else "sampling_sensitive")
                row["note"] = ("the %s sits %.3f kcal/mol above the best screened GFN2 minimum "
                               "(the frozen r2SCAN-3c start geometry sits %s kcal/mol above it); "
                               "this is a gas-phase semiempirical screen, so a large gap flags the "
                               "state as sampling-sensitive for a production-level 3 -> 6 escalation "
                               "rather than overturning the production label"
                               % (tested_note, delta, row["frozen_start_rel_kcal"] or "n/a"))
            else:
                row["verdict"] = "not_computed"
                row["note"] = "cached conformers exist but the production-geometry reference is missing"
            results.append(row)

    return results


def derive(raw):
    files = {}
    results = evaluate_round(raw, KIND_R1)
    results2 = evaluate_round(raw, KIND_R2)
    pool_rows, escalation_rows = select_pool(raw)

    li_rows = []
    for mol_id, name, smiles in MOLS:
        for state in ("LiM_plus", "LiM_2plus"):
            li_rows.append({
                "mol_id": mol_id, "name": name, "state": state, "level": LEVEL,
                "n_motifs_screened": "0", "status": "not_computed",
                "note": ("Li coordination-motif sampling needs its own complex construction "
                         "(the Li mother state and the oxidised state must each be sampled "
                         "separately) and is not part of round 1"),
            })

    n_done = sum(1 for row in results if row["verdict"] != "not_computed")
    n_ok = sum(1 for row in results if row["verdict"] == "single_conformer_representative")
    n_sensitive = sum(1 for row in results if row["verdict"] == "sampling_sensitive")
    n_done2 = sum(1 for row in results2 if row["verdict"] != "not_computed")
    n_limited = sum(1 for row in escalation_rows if row["pool_limited"] == "true")

    checks = [
        {"check_id": "round1_covers_the_states_that_govern_the_two_flips",
         "description": "第一轮采样覆盖 DMC/EMC/GBL/SL 的自由态与阳离子态（两对翻转的决定性态）",
         "ok": str(len(results) == len(MOLS) * len(ROUND1_STATES)).lower(),
         "detail": "%d molecule-state pairs" % len(results)},
        {"check_id": "sampling_is_labelled_as_a_screen_not_a_production_free_energy",
         "description": "采样层显式标注为气相 GFN2 筛选，不外推到生产级自由能",
         "ok": str(all(row["level"] == LEVEL for row in results)).lower(),
         "detail": LEVEL},
        {"check_id": "undetermined_states_are_registered_not_inferred",
         "description": "未算的分子-态显式标 not_computed，不推断结论",
         "ok": str(all((row["verdict"] != "not_computed") == bool(row["min_energy_eh"])
                       for row in results)).lower(),
         "detail": "%d/%d computed" % (n_done, len(results))},
        {"check_id": "li_motif_sampling_is_registered_separately",
         "description": "Li 配位 motif 采样单列登记（本轮未做），不并进自由态结论",
         "ok": str(all(row["status"] == "not_computed" for row in li_rows)).lower(),
         "detail": "%d Li entries registered" % len(li_rows)},
        {"check_id": "conformer_set_structures_come_from_the_registered_pool",
         "description": "结构集合的每个结构都来自登记的两轮采样池，不引入池外几何",
         "ok": str(all(row["source_kind"] in (KIND_R1, KIND_R2) for row in pool_rows)).lower(),
         "detail": "%d structures kept" % len(pool_rows)},
        {"check_id": "conformer_set_geometries_are_hash_recorded",
         "description": "每个入选结构的几何文件存在且逐条记录 sha256（可原样复核与重跑）",
         "ok": str(all(row["geometry_sha256"] and (REPO / row["geometry_relpath"]).is_file()
                       for row in pool_rows)).lower(),
         "detail": "%d/%d hashed" % (sum(1 for row in pool_rows if row["geometry_sha256"]),
                                     len(pool_rows))},
        {"check_id": "round2_uses_one_uniform_pool_across_states",
         "description": "第 2 轮对所有分子-态用同一 seed 与同一起点数（统一池、不逐态调参）",
         "ok": str(len(results2) > 0
                   and all(row["n_conformers_optimised"] for row in results2)
                   and len({row["n_conformers_optimised"] for row in results2}) == 1).lower(),
         "detail": "round-2 optimised counts: %s" % " ".join(
             sorted({row["n_conformers_optimised"] or "-" for row in results2}))},
        {"check_id": "escalation_is_registered_not_decided_by_outcome",
         "description": "3 -> 6 升级只登记待判（等第 1 轮自由能），不按结果事后决定",
         "ok": str(all(row["escalation_status"] in ("registered_pending_round1_free_energy_check",
                                                    "not_computed")
                       for row in escalation_rows)).lower(),
         "detail": "%d states registered / %d pool-limited" % (len(escalation_rows), n_limited)},
        {"check_id": "designated_sampling_set_deviation_is_registered",
         "description": ("方案 3.3 指定的采样集（EMC/DEC/DME/TMP）与本层实际执行集"
                         "（DMC/EMC/GBL/SL）的偏差显式登记，不宣称完成 3.3"),
         "ok": "true",
         "detail": "registered=EMC/DEC/DME/TMP executed=DMC/EMC/GBL/SL; "
                   "DEC/DME/TMP have no sampling product"},
    ]

    index = {
        "scope": ("plan 6.1 round 1: conformer screening for the free neutral / cation states of "
                  "DMC / EMC / GBL / SL, i.e. the states that decide the EMC-GBL and EMC-SL flips"),
        "level": LEVEL,
        "protocol": {"n_conformers_requested": NUM_CONFS_REQUEST, "keep_lowest": KEEP, "seed": SEED,
                     "duplicate_tolerance_kcal": DUP_TOL_KCAL,
                     "escalate_tolerance_kcal": ESCALATE_TOL_KCAL,
                     "escalation_rule": ("extend 3 -> 6 only if the 3 -> 6 free-energy change crosses "
                                         "the independent tolerance or the Top-k set"),
                     "stop_rule": ("after two rounds without resolution report sampling_limited / "
                                   "unresolved instead of searching for a preferred outcome")},
        "totals": {"states_screened": n_done, "states_total": len(results),
                   "single_conformer_representative": n_ok, "sampling_sensitive": n_sensitive},
        "round2": {
            "level": LEVEL,
            "protocol": {"n_conformers_requested": NUM_CONFS_REQUEST_R2, "seed": SEED_R2,
                         "note": ("one uniform larger pool for all 8 states; the round-1 rows are "
                                  "untouched so the two rounds stay separately auditable")},
            "totals": {"states_screened": n_done2, "states_total": len(results2)},
        },
        "conformer_pool": {
            "pool": ("union of round 1 (%d starts) and round 2 (%d starts)"
                     % (NUM_CONFS_REQUEST, NUM_CONFS_REQUEST_R2)),
            "duplicate_tolerance_kcal": DUP_TOL_KCAL, "keep_round1": KEEP, "max_pool": MAX_POOL,
            "structures_kept": len(pool_rows), "states_registered": len(escalation_rows),
            "pool_limited_states": sorted("%s|%s" % (row["name"], row["state"])
                                          for row in escalation_rows
                                          if row["pool_limited"] == "true"),
        },
        "li_motif_sampling": li_rows,
        "cohort_deviation": {
            "registered_set": {"source": ("implementation plan section 3.3 and "
                                         "docs/physics_completion_protocol.md"),
                               "mol_ids": ["C02", "C03", "C08", "C17"],
                               "names": ["EMC", "DEC", "DME", "TMP"]},
            "executed_set": {"mol_ids": ["C01", "C02", "C13", "C14"],
                             "names": ["DMC", "EMC", "GBL", "SL"],
                             "reason": ("these are the free neutral / cation states that decide "
                                        "the EMC-GBL and EMC-SL flips, which is what this layer "
                                        "is for")},
            "consequence": ("this layer does not claim to have executed section 3.3: DEC / DME / "
                            "TMP have no sampling product, and the registered per-state "
                            "structure budget (3 -> 6) is only reachable where the gas-phase "
                            "screen finds competing minima at all"),
        },
        "raw_cache": ("outside-repo: work/sampling/xtb_results.csv; its sha256 is recorded in "
                      "outputs/physics_completion/provenance/provenance_index.json (raw_cache), "
                      "and every conformer start directory is hashed line by line in "
                      "outputs/physics_completion/provenance/job_archive_manifest.csv"),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }

    md = [
        "# 方案 6.1 第 1 轮构象采样（气相 GFN2 筛选）",
        "",
        "> 由 `scripts/wp_production/build_wp2_sampling.py` 生成。采样层是**气相 GFN2-xTB 筛选**，",
        "> 不是生产级 `wB97X-D4 + SMD(acetonitrile)`；它只回答「单一代表结构是否落在同一极小附近」。",
        ">",
        "> **集合偏差**：方案 3.3 指定的采样集是 EMC/DEC/DME/TMP，本层实际执行的是 DMC/EMC/GBL/SL",
        "> （两对翻转的决定性自由态 / 阳离子态）。偏差登记在 `sampling_index.json` 的",
        "> `cohort_deviation`，**不宣称完成方案 3.3**；DEC / DME / TMP 没有任何采样产物。",
        "",
        "| 分子 | 态 | 撒点数 | 独立极小 | 次低极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in results:
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["state"], row["n_conformers_optimised"] or "-",
            row["n_distinct_minima"] or "-", row["top2_rel_kcal"] or "-",
            row["production_geom_rel_kcal"] or "-", row["frozen_start_rel_kcal"] or "-",
            row["verdict"]))
    md += [
        "",
        "## 升级与停止规则",
        "",
        "* 每态先保留最多 **3** 个独立低能极小；只有 3 -> 6 的变化跨过独立容差或改写 Top-k 才升到 6。",
        "* 两轮后仍无法解析就报告 `sampling_limited` / `unresolved`，不为「得到翻转」调窗口。",
        "* Li 配位 motif 采样单列登记，本轮未做。",
        "",
    ]

    md += [
        "",
        "## 第 2 轮：统一扩大的池",
        "",
        "> 同样是**气相 GFN2 筛选**。第 2 轮对所有 8 个分子-态用同一个更大的池",
        "> （%d 起点、seed %d），不逐态调参，也不覆盖第 1 轮的行，两轮分开审计。"
        % (NUM_CONFS_REQUEST_R2, SEED_R2),
        "",
        "| 分子 | 态 | 撒点数 | 独立极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in results2:
        md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["state"], row["n_conformers_optimised"] or "-",
            row["n_distinct_minima"] or "-", row["production_geom_rel_kcal"] or "-",
            row["frozen_start_rel_kcal"] or "-", row["verdict"]))
    md += [
        "",
        "## 独立低能结构（可执行结构集合）",
        "",
        "| 分子 | 态 | 序 | 相对最低 (kcal/mol) | 来源 | 几何（仓库相对路径） | sha256 前 12 位 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in pool_rows:
        md.append("| %s | %s | %s | %s | %s#%s | `%s` | `%s` |" % (
            row["name"], row["state"], row["rank"], row["rel_kcal"], row["source_kind"],
            row["source_index"], row["geometry_relpath"], row["geometry_sha256"][:12]))
    md += [
        "",
        "| 分子 | 态 | 池内独立极小 | 保留结构 | 第 1 轮用 | 池受限 | 升级状态 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in escalation_rows:
        md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["state"], row["n_distinct_minima"], row["n_structures_kept"],
            row["structures_round1"], row["pool_limited"] or "-", row["escalation_status"]))
    md += [
        "",
        "* 每个独立 GFN2 极小保留一个最低能结构（最多 %d 个）；`池受限 = true` 表示这个池" % MAX_POOL,
        "  在这一水平上只给出少于 3 个独立极小，结构集合无法凑满 3 个——这是登记的事实，不是结论。",
        "  是否把第 3 个结构升到生产级，由登记规则在算出第 1 轮自由能之后决定。",
        "",
    ]

    files["outputs/physics_completion/sampling/sampling_round1.csv"] = csv_text(RESULT_FIELDS, results)
    files["outputs/physics_completion/sampling/sampling_round2.csv"] = csv_text(RESULT_FIELDS, results2)
    files["outputs/physics_completion/sampling/sampling_conformer_set.csv"] = csv_text(
        CONFORMER_SET_FIELDS, pool_rows)
    files["outputs/physics_completion/sampling/sampling_escalation.csv"] = csv_text(
        ESCALATION_FIELDS, escalation_rows)
    files["outputs/physics_completion/sampling/sampling_index.json"] = dump(index)
    files["outputs/physics_completion/sampling/sampling_acceptance.csv"] = csv_text(ACC_FIELDS, checks)
    files["outputs/physics_completion/sampling/sampling_summary.md"] = "\n".join(md)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Round-1 conformer screening (plan 6.1).")
    parser.add_argument("--run", action="store_true", help="run the round-1 xTB screen and cache it")
    parser.add_argument("--run2", action="store_true",
                        help="run the larger uniform round-2 pool and append it to the cache")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.run:
        compute()
        return 0
    if args.run2:
        compute(rows=read_raw(), kind=KIND_R2, count=NUM_CONFS_REQUEST_R2, seed=SEED_R2,
                prefix=PREFIX_R2, with_references=False)
        return 0

    raw = read_raw()
    files = derive(raw)
    if args.check:
        failures = []
        for rel, text in sorted(files.items()):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_text(encoding="utf-8") != text:
                failures.append("differs %s" % rel)
        if OUTDIR.is_dir():
            for path in sorted(OUTDIR.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(REPO).as_posix()
                    if rel not in files:
                        failures.append("stray %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:40]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d sampling files are byte-identical" % len(files))
        return 0

    for rel, text in sorted(files.items()):
        target = REPO / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    n_checks = 0
    n_failed = 0
    for rel, text in sorted(files.items()):
        if rel.endswith("_acceptance.csv"):
            for line in text.splitlines()[1:]:
                n_checks += 1
                if line.split(",")[2] == "false":
                    n_failed += 1
    print("wp2 sampling")
    print("-" * 70)
    print("  files      : %d" % len(files))
    print("  acceptance : %d checks / %d failed" % (n_checks, n_failed))
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())