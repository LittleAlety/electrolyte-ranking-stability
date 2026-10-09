# -*- coding: utf-8 -*-
"""方案 6.1 的小规模构象采样（第 3 步）：先只覆盖决定两对翻转的自由态构象。

两级：
  * 计算级（--run）：RDKit ETKDG/MMFF 撒 n_conformers 个起点 -> 各态在其电荷与自旋下跑
    xTB GFN2 Opt，原始结果缓存到仓库外 work/sampling/**（同时作为复现证据被 provenance 收录）；
  * 派生级（默认 / --check）：只从缓存读回，写出 outputs/physics_completion/sampling/**。

口径纪律：
  * 采样层是**气相 GFN2-xTB 筛选**，不是生产级的 wB97X-D4/SMD(acetonitrile)；
    它只回答「单一代表结构是否落在同一极小附近」，不用于给出生产自由能；
  * 每个态保留最多 3 个独立低能极小；只有当 3 个极小之间跨过容差才升级到 6；
  * Li 配位态的 motif 采样不在本轮：它需要单独的配位起点构造，显式登记为 not_computed。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_wp2_sampling.py --run
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

REPO = Path(__file__).resolve().parents[1]
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


def compute():
    rows = []
    for mol_id, name, smiles in MOLS:
        blocks = embed(smiles, NUM_CONFS_REQUEST, SEED)
        for state, charge, uhf in ROUND1_STATES:
            for index, block in enumerate(blocks):
                energy, converged = run_xtb(WORK / name / state / ("c%02d" % index), block,
                                            charge, uhf, True)
                rows.append({"mol_id": mol_id, "name": name, "state": state, "charge": str(charge),
                             "multiplicity": str(uhf + 1), "kind": "conformer", "index": str(index),
                             "energy_eh": energy, "converged": converged,
                             "n_atoms": str(int(block.splitlines()[0].split()[0]))})
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


def derive(raw):
    files = {}
    results = []
    for mol_id, name, smiles in MOLS:
        for state, charge, uhf in ROUND1_STATES:
            conf = [row for row in raw if row["name"] == name and row["state"] == state
                    and row["kind"] == "conformer" and row["energy_eh"]]
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
                row["note"] = "no cached xTB results; run `scripts/build_wp2_sampling.py --run` first"
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
        "li_motif_sampling": li_rows,
        "raw_cache": "outside-repo: work/sampling/xtb_results.csv (hash-recorded by the provenance manifest)",
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }

    md = [
        "# 方案 6.1 第 1 轮构象采样（气相 GFN2 筛选）",
        "",
        "> 由 `scripts/build_wp2_sampling.py` 生成。采样层是**气相 GFN2-xTB 筛选**，",
        "> 不是生产级 `wB97X-D4 + SMD(acetonitrile)`；它只回答「单一代表结构是否落在同一极小附近」。",
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

    files["outputs/physics_completion/sampling/sampling_round1.csv"] = csv_text(RESULT_FIELDS, results)
    files["outputs/physics_completion/sampling/sampling_index.json"] = dump(index)
    files["outputs/physics_completion/sampling/sampling_acceptance.csv"] = csv_text(ACC_FIELDS, checks)
    files["outputs/physics_completion/sampling/sampling_summary.md"] = "\n".join(md)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Round-1 conformer screening (plan 6.1).")
    parser.add_argument("--run", action="store_true", help="run the xTB conformer screen and cache it")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.run:
        compute()
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