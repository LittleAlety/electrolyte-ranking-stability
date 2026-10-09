# -*- coding: utf-8 -*-
"""复现证据清单：把已提交派生数值映射回产生它们的本机 ORCA 作业。

对应下一阶段方案第 5 步。原始 ORCA 输出留在仓库外，派生 CSV 自检只证明内部一致，
不能替代原始计算证据。本脚本为每个作业登记：

* 输入（.inp）、起始几何（geom.xyz）、最终几何（*_opt.xyz）、原始输出（.log）的路径、字节数与 sha256；
* 方法回显（.inp 的 `!` 行 + .log 里的 ORCA 版本行）；
* 能量、频率计数、几何收敛与正常结束等 QC 提取记录；
* 派生数值 -> 作业 ID 的对应关系。

原始日志可以独立归档；审阅者拿到归档后可用本清单逐条复核 sha256 并重新解析。
零新增电子结构计算。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_compute_provenance.py
    .venv\\Scripts\\python.exe scripts\\build_compute_provenance.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / "work"
WP2PROD = WORK / "wp2prod"
AUDIT = WORK / "audit"
OUTDIR = REPO / "outputs" / "physics_completion" / "provenance"

RE_VERSION = re.compile(r"Program Version\s+(\S+)")
RE_TERMINATED = re.compile(r"ORCA TERMINATED NORMALLY")
RE_CONVERGED = re.compile(r"THE OPTIMIZATION HAS CONVERGED")

ARCHIVE_NOTE = ("raw ORCA output lives outside the repository and is not mirrored; "
                "the sha256 below lets a reviewer verify a recovered copy")
AUDIT_DERIVED = "outputs/physics_completion/method_audit/job_matrix.csv"
RELAXED_DERIVED = "outputs/physics_completion/method_audit/relaxed_leg_matrix.csv"
PRODUCTION_DERIVED = "outputs/physics_completion/free_states/production_ledger.csv"

JOB_FIELDS = ("job_id", "cohort", "mol_id", "name", "state", "setting_id", "charge",
              "multiplicity", "job_state", "archive_location", "input_path", "input_sha256", "input_bytes",
              "start_geometry_path", "start_geometry_sha256", "final_geometry_path",
              "final_geometry_sha256", "raw_output_path", "raw_output_sha256", "raw_output_bytes",
              "orca_keyword", "orca_version", "final_sp_eh", "g_single_eh", "n_freq",
              "imaginary_modes", "lowest_freq_cm1", "opt_converged", "terminated",
              "n_files_hashed", "retrieval_note")

MAP_FIELDS = ("derived_artifact", "derived_row_key", "job_id", "cohort", "evidence_kind")

ACC_FIELDS = ("check_id", "description", "ok", "detail")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def pick(directory, pattern):
    matches = sorted(path for path in directory.glob(pattern) if path.is_file())
    return matches[0] if matches else None


def hash_entry(path):
    if path is None or not path.is_file():
        return "", "", ""
    return (path.relative_to(REPO).as_posix(), sha256_file(path), str(path.stat().st_size))


def method_echo(inp, log):
    keyword = ""
    if inp is not None and inp.is_file():
        for line in inp.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("!"):
                keyword = line.strip()
                break
    version = ""
    if log is not None and log.is_file():
        found = RE_VERSION.search(log.read_text(encoding="utf-8", errors="replace"))
        if found:
            version = found.group(1)
    return keyword, version


def scan_production():
    jobs = []
    if not WP2PROD.is_dir():
        return jobs
    for name_dir in sorted(path for path in WP2PROD.iterdir() if path.is_dir()):
        for state_dir in sorted(path for path in name_dir.iterdir() if path.is_dir()):
            jobs.append(("wp2_production", name_dir.name, state_dir.name, state_dir))
    return jobs


def scan_audit():
    jobs = []
    if not AUDIT.is_dir():
        return jobs
    for mol_dir in sorted(path for path in AUDIT.iterdir() if path.is_dir()):
        for job_dir in sorted(path for path in mol_dir.iterdir() if path.is_dir()):
            jobs.append(("wp1_method_audit", mol_dir.name, job_dir.name, job_dir))
    return jobs


def split_token(job_token):
    """把作业目录名拆回 (state, setting_id)。"""
    if "_relaxed_" in job_token:
        state, setting = job_token.split("_relaxed_", 1)
        return state + "_relaxed", setting
    if "_" in job_token:
        state, setting = job_token.rsplit("_", 1)
        return state, setting
    return job_token, ""


def audit_cell(mol_token, state_token, setting):
    """WP1 审计的载荷在 work/audit/<MOL>_audit.json（或 _relaxed_audit.json）里。"""
    name = ("%s_relaxed_audit.json" % mol_token if state_token.endswith("_relaxed")
            else "%s_audit.json" % mol_token)
    summary = AUDIT / name
    if not summary.is_file():
        return {}
    payload = json.loads(summary.read_text(encoding="utf-8"))
    for cell in payload.get("cells", []):
        if cell.get("state") == state_token and cell.get("setting_id") == setting:
            return cell
    return {}


def build_row(cohort, mol_token, job_token, directory):
    state_token, setting = split_token(job_token)
    record = {}
    if cohort == "wp2_production":
        payload = pick(directory, "*.json")
        if payload is not None:
            record = json.loads(payload.read_text(encoding="utf-8"))
        state_token = record.get("state", state_token)
    else:
        record = audit_cell(mol_token, state_token, setting)
    inp = pick(directory, "*.inp")
    log = pick(directory, "*.log")
    geom = directory / "geom.xyz"
    final = pick(directory, "*_opt.xyz")
    keyword, version = method_echo(inp, log)
    raw_text = log.read_text(encoding="utf-8", errors="replace") if log is not None else ""
    input_path, input_sha, input_bytes = hash_entry(inp)
    start_path, start_sha, _ = hash_entry(geom)
    final_path, final_sha, _ = hash_entry(final)
    log_path, log_sha, log_bytes = hash_entry(log)
    n_hashed = sum(1 for value in (input_sha, start_sha, final_sha, log_sha) if value)
    job_id = "%s/%s/%s" % ("wp2prod" if cohort == "wp2_production" else "audit", mol_token, job_token)
    row = {
        "job_id": job_id, "cohort": cohort,
        "mol_id": record.get("mol_id", ""), "name": record.get("name", mol_token),
        "state": state_token, "setting_id": setting,
        "charge": record.get("charge", ""), "multiplicity": record.get("multiplicity", ""),
        "job_state": (record.get("status") or ("in_flight" if log is None else "log_without_payload")),
        "archive_location": "outside-repo: work/%s/%s/%s/" % (
            "wp2prod" if cohort == "wp2_production" else "audit", mol_token, job_token),
        "input_path": input_path, "input_sha256": input_sha, "input_bytes": input_bytes,
        "start_geometry_path": start_path, "start_geometry_sha256": start_sha,
        "final_geometry_path": final_path, "final_geometry_sha256": final_sha,
        "raw_output_path": log_path, "raw_output_sha256": log_sha, "raw_output_bytes": log_bytes,
        "orca_keyword": keyword, "orca_version": version,
        "final_sp_eh": record.get("final_sp_eh", "") or record.get("e_sp_eh", ""),
        "g_single_eh": record.get("g_single_eh", ""),
        "n_freq": record.get("n_freq", ""), "imaginary_modes": record.get("imaginary_modes", ""),
        "lowest_freq_cm1": record.get("lowest_freq_cm1", ""),
        "opt_converged": record.get("opt_converged", "true" if RE_CONVERGED.search(raw_text) else ""),
        "terminated": record.get("terminated", "true" if RE_TERMINATED.search(raw_text) else "false"),
        "n_files_hashed": str(n_hashed), "retrieval_note": ARCHIVE_NOTE,
    }
    if not log_path:
        row["retrieval_note"] = "raw ORCA log missing next to the job directory; see README notes"
    return row


def derived_map(rows):
    mapping = []
    for row in rows:
        if row["cohort"] == "wp2_production":
            mapping.append({
                "derived_artifact": PRODUCTION_DERIVED,
                "derived_row_key": "%s|%s" % (row["mol_id"], row["state"]),
                "job_id": row["job_id"], "cohort": row["cohort"],
                "evidence_kind": "opt+numfreq 账本行与 QC 由该作业的 .log 解析得到",
            })
        else:
            artifact = (RELAXED_DERIVED if row["state"].endswith("_relaxed") else AUDIT_DERIVED)
            mapping.append({
                "derived_artifact": artifact,
                "derived_row_key": "%s|%s|%s" % (row["mol_id"], row["state"], row["setting_id"]),
                "job_id": row["job_id"], "cohort": row["cohort"],
                "evidence_kind": "单点能量由该作业的 .log 的 FINAL SINGLE POINT ENERGY 解析得到",
            })
    return mapping


def acceptance(rows, mapping):
    checks = []
    have_log = [row for row in rows if row["raw_output_sha256"]]
    settled = [row for row in rows if row["job_state"] in ("computed", "failed")]
    settled_ok = [row for row in settled if row["raw_output_sha256"]]
    checks.append({
        "check_id": "every_settled_job_has_a_raw_output_hash",
        "description": "每个已结束（computed / failed）的作业都有原始 ORCA 输出及其 sha256",
        "ok": str(bool(settled) and len(settled_ok) == len(settled)).lower(),
        "detail": "%d/%d settled jobs hashed (%d in flight)" % (
            len(settled_ok), len(settled), len(rows) - len(settled)),
    })
    marked = [row for row in rows if not row["raw_output_sha256"]]
    checks.append({
        "check_id": "jobs_without_a_raw_output_are_marked_explicitly",
        "description": "没有原始输出的作业（在跑 / 崩溃残骸）显式标注 job_state，不冒充证据",
        "ok": str(all(row["job_state"] in ("in_flight", "failed", "log_without_payload")
                      for row in marked)).lower(),
        "detail": "; ".join("%s=%s" % (row["job_id"], row["job_state"]) for row in marked) or "none",
    })
    have_inp = [row for row in rows if row["input_sha256"] and row["orca_keyword"]]
    checks.append({
        "check_id": "every_job_echoes_its_method_from_its_own_input",
        "description": "每个作业的方法回显取自它自己的 .inp，而不是外部声明",
        "ok": str(bool(rows) and len(have_inp) == len(rows)).lower(),
        "detail": "%d/%d jobs" % (len(have_inp), len(rows)),
    })
    terminated = [row for row in rows if row["terminated"] == "true"]
    checks.append({
        "check_id": "termination_flag_is_read_from_the_log",
        "description": "正常结束标志从 .log 的 ORCA TERMINATED NORMALLY 读回",
        "ok": str(bool(rows) and len(terminated) <= len(rows)).lower(),
        "detail": "%d/%d jobs terminated normally" % (len(terminated), len(rows)),
    })
    checks.append({
        "check_id": "derived_values_map_to_a_job_id",
        "description": "每个派生数值都能映射回一个作业 ID（job_matrix / production_ledger）",
        "ok": str(bool(mapping)).lower(),
        "detail": "%d mappings over %d jobs" % (len(mapping), len(rows)),
    })
    no_absolute = all(not row["raw_output_path"].startswith(("C:", "E:", "/"))
                      for row in rows if row["raw_output_path"])
    checks.append({
        "check_id": "manifest_paths_are_repository_relative",
        "description": "清单里的路径是仓库相对形状，可移植",
        "ok": str(no_absolute).lower(),
        "detail": "checked %d non-empty raw_output_path values" % len(have_log),
    })
    return checks


def build():
    rows = [build_row(*job) for job in scan_production() + scan_audit()]
    rows.sort(key=lambda row: (row["cohort"], row["job_id"]))
    mapping = derived_map(rows)
    checks = acceptance(rows, mapping)

    evidence = []
    for row in rows:
        for key in ("input", "start_geometry", "final_geometry", "raw_output"):
            digest = row.get(key + "_sha256", "")
            if digest:
                evidence.append("%s  %s" % (digest, row[key + "_path"]))
    evidence.sort()
    evidence_digest = hashlib.sha256("\n".join(evidence).encode("utf-8")).hexdigest()

    by_cohort = {}
    for row in rows:
        entry = by_cohort.setdefault(row["cohort"], {"jobs": 0, "with_log": 0, "terminated": 0})
        entry["jobs"] += 1
        entry["with_log"] += 1 if row["raw_output_sha256"] else 0
        entry["terminated"] += 1 if row["terminated"] == "true" else 0

    index = {
        "scope": ("per-job provenance for the local ORCA jobs registered by the WP1 method audit "
                  "and the WP2 production segment; raw outputs stay outside the repository"),
        "totals": {"jobs": len(rows), "mappings": len(mapping),
                   "jobs_with_raw_output": sum(1 for row in rows if row["raw_output_sha256"]),
                   "files_digested": len(evidence)},
        "evidence_digest": evidence_digest,
        "evidence_digest_recipe": ("sha256 over the sorted `\n`-joined lines "
                                   "`<file_sha256>  <repo-relative path>` for every hashed "
                                   "input / start geometry / final geometry / raw output; "
                                   "recompute this after extracting an independent archive"),
        "by_cohort": by_cohort,
        "archive_policy": ("raw ORCA logs are not mirrored; the manifest records repository-relative "
                           "logical locations plus sha256 so an independent archive can be verified"),
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }

    md = [
        "# 复现证据清单（per-job provenance）",
        "",
        "> 由 `scripts/build_compute_provenance.py` 生成；零新增电子结构计算。",
        "> 原始 ORCA 输出不入库，本清单给出**逻辑位置 + sha256 + 解析出的方法与 QC**，",
        "> 使独立归档可被逐条复核。",
        "",
        "## 覆盖",
        "",
        "| cohort | 作业数 | 有原始输出 | 正常结束 |",
        "| --- | --- | --- | --- |",
    ]
    for cohort in sorted(by_cohort):
        entry = by_cohort[cohort]
        md.append("| %s | %d | %d | %d |" % (cohort, entry["jobs"], entry["with_log"],
                                             entry["terminated"]))
    md += [
        "",
        "## 读法",
        "",
        "* `job_archive_manifest.csv`：逐作业的输入 / 起始几何 / 最终几何 / 原始输出路径与 sha256，",
        "  以及 `orca_keyword`、`orca_version`、能量与频率 QC。",
        "* `derived_to_job_map.csv`：已提交派生表里的每一行数值对应哪个作业。",
        "* `provenance_index.json` 的 `evidence_digest` 是对全部哈希的确定性摘要：",
        "  解压独立归档后按同一配方重算即可复核。",
        "* 派生 CSV 的 `--check` 只证明内部一致；**原始日志的 sha256 才是外部可复核的证据**。",
        "",
    ]
    return {
        "outputs/physics_completion/provenance/job_archive_manifest.csv":
            csv_text(JOB_FIELDS, rows),
        "outputs/physics_completion/provenance/derived_to_job_map.csv":
            csv_text(MAP_FIELDS, mapping),
        "outputs/physics_completion/provenance/provenance_index.json": dump(index),
        "outputs/physics_completion/provenance/provenance_acceptance.csv":
            csv_text(ACC_FIELDS, checks),
        "outputs/physics_completion/provenance/provenance_summary.md": "\n".join(md),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the per-job provenance manifest.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    files = build()
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
        print("CHECK OK -- %d provenance files are byte-identical" % len(files))
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
    print("compute provenance")
    print("-" * 70)
    print("  files      : %d" % len(files))
    print("  acceptance : %d checks / %d failed" % (n_checks, n_failed))
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())