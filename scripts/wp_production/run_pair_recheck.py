"""方案 5.3 / 11 的关键 pair 第二泛函靶向复核 —— 执行器。

只在**已登记的生产 Opt 几何**上做第二泛函单点（S3 = PBE0-D4/def2-TZVP、S4 = PBE0-D4/def2-TZVPD），
不重优化、不算频率、不改任何已有数值、不按结果挑点。

读
--
* outputs/physics_completion/pair_evidence/targeted_recheck/job_plan.csv  预注册计划（ready / blocked）
* outputs/physics_completion/closure/four_molecule_state_closure.csv      每态的 charge / multiplicity
* work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>_opt.xyz                       已登记的生产 Opt 几何

写（全部在仓库外 work/recheck/，不入交付镜像，与既有边界一致）
--
* work/recheck/<record_id>/geom.xyz / .inp / .log   单点作业现场
* work/recheck/<record_id>.json                     结果行（能量 / 几何哈希 / wall / cores / QC）

纪律
----
* 只跑 status=ready 的行；blocked 行不预跑、不替补；
* 串行执行，每作业 2 核（生产队列在跑 2 x 4 核，这里最多再加 2 核，避免打满机器）；
* 已算好的行默认跳过（--force 重跑）。

用法
----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_pair_recheck.py
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_pair_recheck.py --force
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import run_batch as rb  # noqa: E402

ORCA = rb.ORCA
CORES = 2
PLAN = REPO / "outputs" / "physics_completion" / "pair_evidence" / "targeted_recheck" / "job_plan.csv"
CLOSURE = REPO / "outputs" / "physics_completion" / "closure" / "four_molecule_state_closure.csv"
OUT = REPO / "work" / "recheck"
HARTREE_TO_EV = 27.211386245988
SP_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")

#: 登记的泛函标签 -> ORCA 简单输入行里的实际关键字（ORCA 6.1.1 不认 "PBE0-D4" 这种写法；
#: 既有 WP1 审计作业用的就是 "PBE0 D4"，这里沿用同一写法，避免第二泛函口径漂移）。
ORCA_KEYWORD = {"PBE0-D4": "PBE0 D4", "omegaB97X-D4": "wB97X-D4"}


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_charge_multiplicity():
    table = {}
    for row in read_csv(CLOSURE):
        table[(row["mol_id"], row["state"])] = (row["charge"], row["multiplicity"])
    return table


def ready_rows():
    rows = [row for row in read_csv(PLAN) if row["status"] == "ready"]
    rows.sort(key=lambda row: row["record_id"])
    return rows


def run_one(row, charge_mult, force):
    record_id = row["record_id"]
    key = (row["mol_id"], row["state"])
    if key not in charge_mult:
        raise SystemExit("闭环表里没有 %s|%s 的电荷/自旋登记" % key)
    charge, mult = charge_mult[key]
    directory = OUT / record_id.replace("|", "__")
    payload_path = OUT / (record_id.replace("|", "__") + ".json")
    if payload_path.exists() and not force:
        existing = json.loads(payload_path.read_text(encoding="utf-8"))
        if existing.get("status") == "computed":
            print("%-24s exists, skip" % record_id)
            return existing
        print("%-24s 上次未通过 QC (status=%s)，重跑" % (record_id, existing.get("status")))

    source = REPO / row["geometry_source"]
    if not source.is_file():
        raise SystemExit("缺少已登记的生产几何: %s" % source)
    directory.mkdir(parents=True, exist_ok=True)
    geom = directory / "geom.xyz"
    geom.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    keyword = ORCA_KEYWORD.get(row["functional"])
    if keyword is None:
        raise SystemExit("未登记的泛函标签: %s" % row["functional"])
    method = "%s %s" % (keyword, row["basis"])
    inp = directory / ("%s.inp" % record_id.replace("|", "__"))
    inp.write_text("! %s SMD(acetonitrile) SP SlowConv\n"
                   "%%maxcore 2000\n%%pal nprocs %d end\n%%scf MaxIter 300 end\n"
                   "* xyzfile %s %s geom.xyz\n" % (method, CORES, charge, mult),
                   encoding="utf-8")
    _code, text, wall = rb.capture_run([str(ORCA), inp.name], directory,
                                       directory / ("%s.log" % record_id.replace("|", "__")))
    energies = SP_ENERGY.findall(text)
    energy_eh = energies[-1] if energies else ""
    terminated = "ORCA TERMINATED NORMALLY" in text
    scf_converged = bool(re.search(r"SCF CONVERGED AFTER", text))
    payload = {
        "record_id": record_id,
        "mol_id": row["mol_id"], "name": row["name"], "state": row["state"],
        "setting_id": row["setting_id"], "functional": row["functional"], "basis": row["basis"],
        "charge": str(charge), "multiplicity": str(mult),
        "geometry_source": row["geometry_source"],
        "geometry_sha256": sha256_file(geom),
        "orca_keyword": method,
        "energy_eh": energy_eh,
        "energy_ev": ("%.9f" % (float(energy_eh) * HARTREE_TO_EV)) if energy_eh else "",
        "scf_converged": "true" if scf_converged else "false",
        "terminated": "true" if terminated else "false",
        "wall_sec": "%.1f" % wall, "cores": str(CORES),
        "core_hours": "%.6f" % (CORES * wall / 3600.0),
        "job_kind": "second_functional_single_point",
        "notes": ("single point at the frozen registered production Opt geometry; no re-optimisation, "
                  "no frequency; the raw ORCA output stays outside the repository and outside the "
                  "delivery mirror"),
    }
    payload["status"] = "computed" if (terminated and scf_converged and energy_eh) else "failed"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("%-24s %-18s status=%s E=%s Eh  wall=%.0fs"
          % (record_id, method, payload["status"], energy_eh, wall))
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the registered second-functional re-check single points.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", default="", help="只跑某个 record_id（调试用）")
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    charge_mult = state_charge_multiplicity()
    rows = ready_rows()
    if args.only:
        rows = [row for row in rows if row["record_id"] == args.only]
    print("targeted re-check: %d ready single points, %d cores each, serial" % (len(rows), CORES))
    done = 0
    for row in rows:
        payload = run_one(row, charge_mult, args.force)
        done += 1 if payload.get("status") == "computed" else 0
    print("computed %d / %d" % (done, len(rows)))
    return 0 if done == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
