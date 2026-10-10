"""把靶向复核的**原始单点结果**折成可提交的登记表（手工折步，仓库外 work/ -> 交付层）。

与 archive_raw_outputs.py 同性质：这一步不是收口链的一环，因为它的输入
（work/recheck/ 下的原始 ORCA 现场）按既有边界留在仓库外、不入交付镜像。

写
--
* outputs/physics_completion/pair_evidence/targeted_recheck/recheck_results.csv
      逐单点登记：设定 / 几何哈希 / 能量 / QC / wall / cores / core-hours（原始层，别再推导）

纪律
----
* 只登记 status=computed 且几何哈希与当前生产 Opt 几何一致的作业；其余显式记 failed 并不冒充数值；
* blocked_on_production_leg 的行**没有**结果，不得补数；
* 不复算、不覆盖任何已有产物（方案 13）。

用法
----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\emit_pair_recheck.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PC = REPO / "outputs" / "physics_completion"
RECHECK = PC / "pair_evidence" / "targeted_recheck"
PLAN = RECHECK / "job_plan.csv"
RAW = REPO / "work" / "recheck"
HARTREE_TO_EV = 27.211386245988

RESULT_FIELDS = ("record_id", "mol_id", "name", "state", "setting_id", "functional", "basis",
                 "orca_keyword", "charge", "multiplicity", "geometry_source", "geometry_sha256",
                 "energy_eh", "energy_ev", "wall_sec", "cores", "core_hours", "scf_converged",
                 "terminated", "status", "note")
def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(fields, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows():
    plan = read_csv(PLAN)
    ready = {row["record_id"] for row in plan if row["status"] == "ready"}
    blocked = {row["record_id"] for row in plan if row["status"] != "ready"}
    out = []
    for record_id in sorted(ready):
        payload_path = RAW / (record_id.replace("|", "__") + ".json")
        if not payload_path.is_file():
            raise SystemExit("缺少结果 %s（先跑 run_pair_recheck.py）" % payload_path)
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        if payload["record_id"] != record_id:
            raise SystemExit("record_id 不一致: %s" % payload_path)
        source = REPO / payload["geometry_source"]
        geom_ok = source.is_file() and sha256_file(source) == payload["geometry_sha256"]
        status = payload["status"]
        if status == "computed" and not geom_ok:
            status = "geometry_changed_since_run"
        out.append({
            "record_id": record_id, "mol_id": payload["mol_id"], "name": payload["name"],
            "state": payload["state"], "setting_id": payload["setting_id"],
            "functional": payload["functional"], "basis": payload["basis"],
            "orca_keyword": payload["orca_keyword"], "charge": payload["charge"],
            "multiplicity": payload["multiplicity"],
            "geometry_source": payload["geometry_source"],
            "geometry_sha256": payload["geometry_sha256"],
            "energy_eh": payload["energy_eh"], "energy_ev": payload["energy_ev"],
            "wall_sec": payload["wall_sec"], "cores": payload["cores"],
            "core_hours": payload["core_hours"],
            "scf_converged": payload["scf_converged"], "terminated": payload["terminated"],
            "status": status,
            "note": ("geometry hash matches the registered production Opt geometry"
                     if geom_ok else "geometry file changed after the single point ran"),
        })
    leaked = blocked & {row["record_id"] for row in out}
    if leaked:
        raise SystemExit("blocked 行不应有结果: %s" % sorted(leaked))
    return out, ready, blocked


def main():
    results, ready, blocked = rows()
    RECHECK.mkdir(parents=True, exist_ok=True)
    (RECHECK / "recheck_results.csv").write_text(csv_text(RESULT_FIELDS, results),
                                                 encoding="utf-8", newline="")
    computed = [row for row in results if row["status"] == "computed"]
    core_hours = sum(float(row["core_hours"]) for row in computed)
    by_setting = {}
    for row in computed:
        by_setting.setdefault(row["setting_id"], []).append(row)
    print("targeted re-check fold-in (raw registered single points)")
    print("-" * 70)
    print("  ready rows     : %d (blocked %d)" % (len(ready), len(blocked)))
    print("  registered     : %d computed / %d total" % (len(computed), len(results)))
    print("  core-hours     : %.6f (2 cores each, serial)" % core_hours)
    for setting in sorted(by_setting):
        rows_here = by_setting[setting]
        print("  %-4s %d computed; wall total %.0fs"
              % (setting, len(rows_here), sum(float(r["wall_sec"]) for r in rows_here)))
    print("  派生 (delta / 符号) 由 build_pair_recheck_plan.py 从本表重算，不在这里再推导")
    return 0 if len(computed) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
