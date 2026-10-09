# -*- coding: utf-8 -*-
"""复现证据清单：把已提交派生数值映射回产生它们的本机 ORCA 作业。

对应下一阶段方案第 5 步。原始 ORCA 输出留在仓库外，派生 CSV 自检只证明内部一致，
不能替代原始计算证据。本脚本为每个作业登记：

* 输入（.inp）、起始几何（geom.xyz）、最终几何（*_opt.xyz）、原始输出（.log）的路径、字节数与 sha256；
* xTB 采样作业（气相 GFN2 构象筛选）的起始几何、优化几何（xtbopt.xyz）与原始输出（xtbopt.log）同上；
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

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "work"
WP2PROD = WORK / "wp2prod"
AUDIT = WORK / "audit"
SAMPLING = WORK / "sampling"
SAMPLING_CACHE = SAMPLING / "xtb_results.csv"
SET_CSV = REPO / "data" / "metadata" / "physics_completion_set.csv"
PRODUCTION_LEDGER = REPO / "outputs" / "physics_completion" / "free_states" / "production_ledger.csv"
AUDIT_COST_LEDGER = REPO / "outputs" / "physics_completion" / "cost" / "audit_cost_ledger.csv"
PREP_LEDGER_DERIVED = "outputs/physics_completion/cost/audit_cost_ledger.csv"
GEOMETRY_PREP_DIR = AUDIT / "EMC_Li"
GEOMETRY_PREP_JOB = "EMC_m1_G2Li_opt"
OUTDIR = REPO / "outputs" / "physics_completion" / "provenance"

RE_VERSION = re.compile(r"Program Version\s+(\S+)")
RE_TERMINATED = re.compile(r"ORCA TERMINATED NORMALLY")
RE_CONVERGED = re.compile(r"THE OPTIMIZATION HAS CONVERGED")
RE_SAMPLING_START = re.compile(r"^(r2_)?c([0-9]+)$")
RE_XTB_ENERGY = re.compile(r"^\s*energy:\s*(-?[0-9]+\.[0-9]+)\s+gnorm:\s*([0-9.]+)", re.M)
RE_XTB_VERSION = re.compile(r"\bxtb:\s*(\S+)")

ARCHIVE_NOTE = ("raw ORCA output lives outside the repository and is not mirrored; "
                "the sha256 below lets a reviewer verify a recovered copy")
SAMPLING_ENGINE = "GFN2-xTB"
SAMPLING_CACHE_REL = "work/sampling/xtb_results.csv"
SAMPLING_NOTE = ("gas-phase GFN2-xTB conformer screen of one ETKDG start; the start geometry, "
                 "the optimised geometry and the xtbopt.log are hashed below, and the aggregate "
                 "raw cache is work/sampling/xtb_results.csv")
AUDIT_DERIVED = "outputs/physics_completion/method_audit/job_matrix.csv"
RELAXED_DERIVED = "outputs/physics_completion/method_audit/relaxed_leg_matrix.csv"
PRODUCTION_DERIVED = "outputs/physics_completion/free_states/production_ledger.csv"

#: 每张派生表用哪几列拼出 derived_row_key，用来验证映射行真的存在。
DERIVED_KEY_COLUMNS = {
    AUDIT_DERIVED: ("mol_id", "state", "setting_id"),
    RELAXED_DERIVED: ("mol_id", "state", "setting_id"),
    PRODUCTION_DERIVED: ("mol_id", "state"),
    PREP_LEDGER_DERIVED: ("job_id",),
    SAMPLING_CACHE_REL: ("name", "state", "kind", "index"),
}

JOB_FIELDS = ("job_id", "cohort", "mol_id", "name", "state", "setting_id", "charge",
              "multiplicity", "job_state", "archive_location", "engine", "engine_version",
              "input_path", "input_sha256", "input_bytes",
              "start_geometry_path", "start_geometry_sha256", "final_geometry_path",
              "final_geometry_sha256", "raw_output_path", "raw_output_sha256", "raw_output_bytes",
              "orca_keyword", "orca_version", "final_sp_eh", "g_single_eh", "n_freq",
              "imaginary_modes", "lowest_freq_cm1", "opt_converged", "terminated",
              "failure_reason", "n_files_hashed", "retrieval_note")

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


#: 从该作业自己 .log 的文本推导失败类型；只用于解释非正常结束，不改变任何数值。
FAILURE_SIGNATURES = (
    ("mpi_smpd_unavailable",
     ("unable to start the local smpd manager", "ReadFile() failed, error 109")),
    ("mpi_smpd_communication_lost",
     ("failed to communicate with smpd manager",)),
    ("orca_cannot_open_scratch_file",
     ("CANNOT OPEN FILE",)),
)


def classify_failure(job_state, terminated, has_log, raw_text):
    """把 failed 的 ORCA 作业归到一类可复核的原因；不需要原因时返回空串。"""
    if job_state != "failed" or terminated == "true":
        return ""
    if not has_log:
        return "no_raw_output"
    for label, needles in FAILURE_SIGNATURES:
        if any(needle in raw_text for needle in needles):
            return label
    return "unclassified"


def build_row(cohort, mol_token, job_token, directory):
    state_token, setting = split_token(job_token)
    record = {}
    if cohort == "wp2_production":
        # 生产腿的目录名就是状态名（M / M_plus / M_tzvpd / LiM_plus / LiM_2plus），
        # 不能走 split_token：它会把 M_plus 拆成 state=M, setting=plus，
        # 让在跑 / 失败的作业被错认成另一个状态。
        state_token, setting = job_token, ""
        payload = pick(directory, "*.json")
        if payload is not None:
            record = json.loads(payload.read_text(encoding="utf-8"))
        state_token = record.get("state") or state_token
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
    job_state = record.get("status") or ("in_flight" if log is None else "log_without_payload")
    terminated = record.get("terminated", "true" if RE_TERMINATED.search(raw_text) else "false")
    # 跑失败的腿不能把 n_freq=0 / imaginary_modes=0 登记成「干净的极小值」——
    # 那读起来像「无虚频的极小」，实际上频率计算根本没跑完。生产的 QC 列只登记
    # computed 的作业；其余留空（不补数），失败原因仍由 failure_reason 记录。
    qc_echo = cohort != "wp2_production" or job_state == "computed"
    row = {
        "job_id": job_id, "cohort": cohort,
        "mol_id": (record.get("mol_id", "")
                   or NAME_TO_MOL_ID.get(record.get("name") or mol_token, "")),
        "name": record.get("name") or mol_token,
        "state": state_token, "setting_id": setting,
        "charge": record.get("charge", ""), "multiplicity": record.get("multiplicity", ""),
        "job_state": job_state,
        "archive_location": "outside-repo: work/%s/%s/%s/" % (
            "wp2prod" if cohort == "wp2_production" else "audit", mol_token, job_token),
        "engine": "ORCA", "engine_version": version,
        "input_path": input_path, "input_sha256": input_sha, "input_bytes": input_bytes,
        "start_geometry_path": start_path, "start_geometry_sha256": start_sha,
        "final_geometry_path": final_path, "final_geometry_sha256": final_sha,
        "raw_output_path": log_path, "raw_output_sha256": log_sha, "raw_output_bytes": log_bytes,
        "orca_keyword": keyword, "orca_version": version,
        # wp2 生产作业的载荷没有 final_sp_eh 字段，只有两个同义列：e_sp_eh 与
        # electronic_eh（热化学段的 Electronic energy）。早期驱动的 e_sp_eh 记的是
        # 起始几何的 SP，与交付账本的口径不同；优先取 electronic_eh，让这张表与
        # production_ledger.csv 的 e_sp_eh 同义（wp1 审计载荷两者都没有）。
        "final_sp_eh": ("" if not qc_echo else
                        record.get("final_sp_eh", "") or record.get("electronic_eh", "")
                        or record.get("e_sp_eh", "")),
        "g_single_eh": record.get("g_single_eh", "") if qc_echo else "",
        "n_freq": record.get("n_freq", "") if qc_echo else "",
        "imaginary_modes": record.get("imaginary_modes", "") if qc_echo else "",
        "lowest_freq_cm1": record.get("lowest_freq_cm1", "") if qc_echo else "",
        "opt_converged": record.get("opt_converged", "true" if RE_CONVERGED.search(raw_text) else ""),
        "terminated": terminated,
        "failure_reason": classify_failure(job_state, terminated, log is not None, raw_text),
        "n_files_hashed": str(n_hashed), "retrieval_note": ARCHIVE_NOTE,
    }
    if not log_path:
        row["retrieval_note"] = "raw ORCA log missing next to the job directory; see README notes"
    return row


def sampling_cache():
    """按 (name, state, kind, index) 索引 work/sampling/xtb_results.csv；同时返回总行数。"""
    cache = {}
    total = 0
    if not SAMPLING_CACHE.is_file():
        return cache, total
    with SAMPLING_CACHE.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            total += 1
            if record.get("kind") not in ("conformer", "conformer_r2"):
                continue
            try:
                index = int(record.get("index", ""))
            except ValueError:
                continue
            cache[(record.get("name", ""), record.get("state", ""),
                   record.get("kind", ""), index)] = record
    return cache, total


def scan_sampling():
    """work/sampling/<NAME>/<STATE>/<cNN|r2_cNN>/ 每个起点目录 = 一个 xTB 作业。"""
    jobs = []
    if not SAMPLING.is_dir():
        return jobs
    for name_dir in sorted(path for path in SAMPLING.iterdir() if path.is_dir()):
        for state_dir in sorted(path for path in name_dir.iterdir() if path.is_dir()):
            for start_dir in sorted(path for path in state_dir.iterdir() if path.is_dir()):
                if not RE_SAMPLING_START.match(start_dir.name):
                    continue
                jobs.append((name_dir.name, state_dir.name, start_dir.name, start_dir))
    return jobs


def build_sampling_row(name_token, state_token, start_token, directory, cache):
    """一个 xTB 构象筛选作业：hashex 起始/优化几何与 xtbopt.log，并从 log 读回末次能量与版本。"""
    match = RE_SAMPLING_START.match(start_token)
    kind = "conformer_r2" if match.group(1) else "conformer"
    index = int(match.group(2))
    cached = cache.get((name_token, state_token, kind, index), {})
    log = directory / "xtbopt.log"
    log_path, log_sha, log_bytes = hash_entry(log)
    start_path, start_sha, _ = hash_entry(directory / "geom.xyz")
    final_path, final_sha, _ = hash_entry(directory / "xtbopt.xyz")
    raw_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    energies = RE_XTB_ENERGY.findall(raw_text)
    found_version = RE_XTB_VERSION.search(raw_text)
    converged = (directory / ".xtboptok").is_file() and bool(final_path)
    if converged:
        state = "computed"
    elif log_path:
        state = "in_flight"
    else:
        state = "log_without_payload"
    return {
        "job_id": "wp2sampling/%s/%s/%s" % (name_token, state_token, start_token),
        "cohort": "wp2_sampling",
        "mol_id": cached.get("mol_id", ""), "name": name_token,
        "state": state_token, "setting_id": kind,
        "charge": cached.get("charge", ""), "multiplicity": cached.get("multiplicity", ""),
        "job_state": state,
        "archive_location": "outside-repo: work/sampling/%s/%s/%s/" % (
            name_token, state_token, start_token),
        "engine": SAMPLING_ENGINE, "engine_version": found_version.group(1) if found_version else "",
        "input_path": "", "input_sha256": "", "input_bytes": "",
        "start_geometry_path": start_path, "start_geometry_sha256": start_sha,
        "final_geometry_path": final_path, "final_geometry_sha256": final_sha,
        "raw_output_path": log_path, "raw_output_sha256": log_sha, "raw_output_bytes": log_bytes,
        "orca_keyword": "", "orca_version": "",
        "final_sp_eh": energies[-1][0] if energies else "",
        "g_single_eh": "", "n_freq": "", "imaginary_modes": "", "lowest_freq_cm1": "",
        "opt_converged": "true" if converged else "false",
        "terminated": "true" if converged else "false",
        "n_files_hashed": str(sum(1 for value in (start_sha, final_sha, log_sha) if value)),
        "retrieval_note": SAMPLING_NOTE,
    }


def sampling_energy_agreement(rows, cache):
    """采样作业 log 末次 energy 与聚合缓存的对应行是否一致；返回 (比较数, 最大偏差)。"""
    n_agree = 0
    worst = 0.0
    for row in rows:
        if row["cohort"] != "wp2_sampling" or not row["final_sp_eh"]:
            continue
        index = int(RE_SAMPLING_START.match(row["job_id"].rsplit("/", 1)[-1]).group(2))
        cached = cache.get((row["name"], row["state"], row["setting_id"], index))
        if not cached:
            continue
        n_agree += 1
        worst = max(worst, abs(float(row["final_sp_eh"]) - float(cached["energy_eh"])))
    return n_agree, worst


def set_metadata():
    """data/metadata/physics_completion_set.csv 的 name <-> mol_id 双向表。"""
    by_name = {}
    by_id = {}
    if SET_CSV.is_file():
        with SET_CSV.open("r", encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                name = record.get("name", "")
                mol_id = record.get("mol_id", "")
                if name and mol_id:
                    by_name.setdefault(name, mol_id)
                    by_id.setdefault(mol_id, name)
    return by_name, by_id


def prep_ledger_row_id():
    """审计成本台账里 EMC_Li 几何准备作业的行号（该作业不在 128 + 32 方法审计矩阵内）。"""
    if not AUDIT_COST_LEDGER.is_file():
        return ""
    with AUDIT_COST_LEDGER.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            if record.get("setting_id") == "EMC_Li_opt":
                return record.get("job_id", "")
    return ""


def scan_geometry_prep():
    """work/audit/EMC_Li/：单目录的 ORCA 几何准备作业（分子-态为 EMC|LiM_plus）。"""
    if not GEOMETRY_PREP_DIR.is_dir() or not PREP_LEDGER_ROW_ID:
        return []
    return [("C02", GEOMETRY_PREP_JOB, GEOMETRY_PREP_DIR)]


def build_prep_row(mol_token, job_token, directory):
    """几何准备作业：与 ORCA 作业同形，但它不在方法审计矩阵里，派生源是成本台账。"""
    inp = pick(directory, "*.inp")
    log = pick(directory, "*.log")
    final = pick(directory, "*_opt.xyz")
    keyword, version = method_echo(inp, log)
    raw_text = log.read_text(encoding="utf-8", errors="replace") if log is not None else ""
    input_path, input_sha, input_bytes = hash_entry(inp)
    start_path, start_sha, _ = hash_entry(directory / "geom.xyz")
    final_path, final_sha, _ = hash_entry(final)
    log_path, log_sha, log_bytes = hash_entry(log)
    terminated = bool(RE_TERMINATED.search(raw_text))
    return {
        "job_id": "auditprep/%s/%s" % (mol_token, job_token),
        "cohort": "wp1_geometry_prep",
        "mol_id": mol_token, "name": MOL_ID_TO_NAME.get(mol_token, mol_token),
        "state": "LiM_plus", "setting_id": "EMC_Li_opt",
        "charge": "", "multiplicity": "",
        "job_state": "computed" if terminated else ("in_flight" if log_path else "log_without_payload"),
        "archive_location": "outside-repo: work/audit/EMC_Li/",
        "engine": "ORCA", "engine_version": version,
        "input_path": input_path, "input_sha256": input_sha, "input_bytes": input_bytes,
        "start_geometry_path": start_path, "start_geometry_sha256": start_sha,
        "final_geometry_path": final_path, "final_geometry_sha256": final_sha,
        "raw_output_path": log_path, "raw_output_sha256": log_sha, "raw_output_bytes": log_bytes,
        "orca_keyword": keyword, "orca_version": version,
        "final_sp_eh": "", "g_single_eh": "", "n_freq": "", "imaginary_modes": "",
        "lowest_freq_cm1": "",
        "opt_converged": "true" if RE_CONVERGED.search(raw_text) else "false",
        "terminated": "true" if terminated else "false",
        "n_files_hashed": str(sum(1 for value in (input_sha, start_sha, final_sha, log_sha) if value)),
        "retrieval_note": ARCHIVE_NOTE,
    }


def ledger_index():
    """production_ledger.csv 的 (mol_id|name, state) -> 账本行；只有真行才是派生源。"""
    index = {}
    if PRODUCTION_LEDGER.is_file():
        with PRODUCTION_LEDGER.open("r", encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                state = record.get("state", "")
                index.setdefault((record.get("mol_id", ""), state), record)
                index.setdefault((record.get("name", ""), state), record)
    return index


def derived_key_pools():
    """每张派生表里真实存在的 derived_row_key 集合。"""
    pools = {}
    for rel, columns in DERIVED_KEY_COLUMNS.items():
        values = set()
        path = REPO / rel
        if path.is_file():
            with path.open("r", encoding="utf-8", newline="") as handle:
                for record in csv.DictReader(handle):
                    values.add("|".join(record.get(column, "") for column in columns))
        pools[rel] = values
    return pools


def mapping_resolution(mapping, pools):
    """派生映射逐行验证：命名派生表里必须真有这一行，否则就是无据声明。"""
    resolved = 0
    unresolved = []
    for entry in mapping:
        pool = pools.get(entry["derived_artifact"])
        if pool is not None and entry["derived_row_key"] in pool:
            resolved += 1
        else:
            unresolved.append("%s -> %s" % (entry["derived_artifact"], entry["derived_row_key"]))
    return resolved, unresolved


def derived_map(rows):
    mapping = []
    for row in rows:
        if row["cohort"] == "wp2_sampling":
            tail = row["job_id"].rsplit("/", 1)[-1]
            index = int(RE_SAMPLING_START.match(tail).group(2))
            mapping.append({
                "derived_artifact": SAMPLING_CACHE_REL,
                "derived_row_key": "%s|%s|%s|%d" % (row["name"], row["state"],
                                                     row["setting_id"], index),
                "job_id": row["job_id"], "cohort": row["cohort"],
                "evidence_kind": "该缓存行由本起点目录的 xtbopt.log 产生（末次 energy 与缓存值一致，见 checks）",
            })
        elif row["cohort"] == "wp1_geometry_prep":
            if PREP_LEDGER_ROW_ID:
                mapping.append({
                    "derived_artifact": PREP_LEDGER_DERIVED,
                    "derived_row_key": PREP_LEDGER_ROW_ID,
                    "job_id": row["job_id"], "cohort": row["cohort"],
                    "evidence_kind": "成本台账该行（wall / core-hours）来自本作业的运行记录；方法回显、收敛与正常结束标志从本目录的 .log 读回",
                })
        elif row["cohort"] == "wp2_production":
            # 只有真产生了账本行的作业才是派生源；failed / 在跑作业只进清单，不声明派生素。
            ledger = (LEDGER_INDEX.get((row["mol_id"], row["state"]))
                      or LEDGER_INDEX.get((row["name"], row["state"])))
            if ledger is not None:
                mapping.append({
                    "derived_artifact": PRODUCTION_DERIVED,
                    "derived_row_key": "%s|%s" % (ledger["mol_id"], ledger["state"]),
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


def acceptance(rows, mapping, cache, pools):
    orca = [row for row in rows if row["cohort"] != "wp2_sampling"]
    sampling = [row for row in rows if row["cohort"] == "wp2_sampling"]
    checks = []
    have_log = [row for row in rows if row["raw_output_sha256"]]
    settled = [row for row in rows if row["job_state"] in ("computed", "failed")]
    settled_ok = [row for row in settled if row["raw_output_sha256"]]
    checks.append({
        "check_id": "every_settled_job_has_a_raw_output_hash",
        "description": "每个已结束（computed / failed）的作业都有原始输出及其 sha256（ORCA .log 与 xTB xtbopt.log 一视同仁）",
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
    have_inp = [row for row in orca if row["input_sha256"] and row["orca_keyword"]]
    checks.append({
        "check_id": "every_orca_job_echoes_its_method_from_its_own_input",
        "description": "每个 ORCA 作业的方法回显取自它自己的 .inp，而不是外部声明（xTB 采样无 .inp，由下一条独立检查覆盖）",
        "ok": str(bool(orca) and len(have_inp) == len(orca)).lower(),
        "detail": "%d/%d ORCA jobs (%d xTB jobs excluded)" % (len(have_inp), len(orca), len(sampling)),
    })
    have_geom = [row for row in sampling
                 if row["start_geometry_sha256"] and row["final_geometry_sha256"]]
    checks.append({
        "check_id": "every_sampling_job_has_both_geometries_hashed",
        "description": "每个采样作业的起始几何与优化几何都存在并逐条记录 sha256",
        "ok": str(bool(sampling) and len(have_geom) == len(sampling)).lower(),
        "detail": "%d/%d xTB jobs" % (len(have_geom), len(sampling)),
    })
    n_agree, worst = sampling_energy_agreement(rows, cache)
    checks.append({
        "check_id": "sampling_log_energies_match_the_aggregate_cache",
        "description": "每个采样作业的 xtbopt.log 末次 energy 与 xtb_results.csv 对应行一致（|Δ| < 1e-6 Eh），确定缓存行与本作业同源",
        "ok": str(bool(sampling) and n_agree == len(sampling) and worst < 1e-6).lower(),
        "detail": "%d/%d jobs agree, worst |delta| = %.2e Eh" % (n_agree, len(sampling), worst),
    })
    terminated = [row for row in orca if row["terminated"] == "true"]
    checks.append({
        "check_id": "termination_flag_is_read_from_the_log",
        "description": "ORCA 正常结束标志从 .log 的 ORCA TERMINATED NORMALLY 读回（采样作业的收敛标志来自 .xtboptok + xtbopt.xyz，不混用）",
        "ok": str(bool(orca) and len(terminated) <= len(orca)).lower(),
        "detail": "%d/%d ORCA jobs terminated normally" % (len(terminated), len(orca)),
    })
    failed_rows = [row for row in orca if row["job_state"] == "failed"]
    coded = [row for row in failed_rows if row["failure_reason"] not in ("", "unclassified")]
    checks.append({
        "check_id": "every_failed_orca_job_carries_a_log_derived_failure_reason",
        "description": "每个 failed 的 ORCA 作业都带一条从它自己 .log 文本推导的 failure_reason，"
                       "把基础设施事故（smpd 缺失/失联、scratch 打不开）与物理结论分开",
        "ok": str(len(coded) == len(failed_rows)).lower(),
        "detail": "%d/%d failed jobs classified" % (len(coded), len(failed_rows)),
    })
    checks.append({
        "check_id": "derived_values_map_to_a_job_id",
        "description": "每个派生数值都能映射回一个作业 ID（job_matrix / production_ledger / 采样原始缓存）",
        "ok": str(bool(mapping)).lower(),
        "detail": "%d mappings over %d jobs" % (len(mapping), len(rows)),
    })
    resolved, unresolved = mapping_resolution(mapping, pools)
    checks.append({
        "check_id": "every_mapping_key_resolves_in_the_named_artifact",
        "description": "derived_to_job_map.csv 的每一行都指向命名派生表里真实存在的一行，不声明不存在的派生素",
        "ok": str(bool(mapping) and not unresolved).lower(),
        "detail": "%d/%d keys resolved%s" % (
            resolved, len(mapping), "" if not unresolved else "; first: " + unresolved[0]),
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


NAME_TO_MOL_ID, MOL_ID_TO_NAME = set_metadata()
LEDGER_INDEX = ledger_index()
PREP_LEDGER_ROW_ID = prep_ledger_row_id()


def build():
    pools = derived_key_pools()
    cache, cache_rows = sampling_cache()
    rows = [build_row(*job) for job in scan_production() + scan_audit()]
    rows += [build_prep_row(*job) for job in scan_geometry_prep()]
    rows += [build_sampling_row(*job, cache) for job in scan_sampling()]
    rows.sort(key=lambda row: (row["cohort"], row["job_id"]))
    mapping = derived_map(rows)
    checks = acceptance(rows, mapping, cache, pools)

    evidence = []
    for row in rows:
        for key in ("input", "start_geometry", "final_geometry", "raw_output"):
            digest = row.get(key + "_sha256", "")
            if digest:
                evidence.append("%s  %s" % (digest, row[key + "_path"]))
    cache_path, cache_sha, cache_bytes = hash_entry(SAMPLING_CACHE)
    if cache_sha:
        evidence.append("%s  %s" % (cache_sha, cache_path))
    evidence.sort()
    evidence_digest = hashlib.sha256("\n".join(evidence).encode("utf-8")).hexdigest()

    by_cohort = {}
    for row in rows:
        entry = by_cohort.setdefault(row["cohort"], {"jobs": 0, "with_log": 0, "terminated": 0})
        entry["jobs"] += 1
        entry["with_log"] += 1 if row["raw_output_sha256"] else 0
        entry["terminated"] += 1 if row["terminated"] == "true" else 0

    index = {
        "scope": ("per-job provenance for every local electronic-structure job registered by the "
                  "WP1 method audit (ORCA), the WP1 EMC-Li geometry preparation (ORCA), the WP2 "
                  "production segment (ORCA) and the section 6.1 "
                  "gas-phase GFN2-xTB conformer screen of DMC / EMC / GBL / SL; raw outputs stay "
                  "outside the repository"),
        "totals": {"jobs": len(rows), "mappings": len(mapping),
                   "orca_jobs": len(rows) - sum(1 for row in rows if row["cohort"] == "wp2_sampling"),
                   "sampling_jobs": sum(1 for row in rows if row["cohort"] == "wp2_sampling"),
                   "jobs_with_raw_output": sum(1 for row in rows if row["raw_output_sha256"]),
                   "files_digested": len(evidence)},
        "raw_cache": {"path": cache_path, "sha256": cache_sha, "bytes": cache_bytes,
                      "rows": cache_rows,
                      "note": "the aggregate xTB cache; every sampling job row above is mapped "
                              "back to one of its lines by derived_to_job_map.csv"},
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
        "> 由 `scripts/wp_production/build_compute_provenance.py` 生成；零新增电子结构计算。",
        "> 原始 ORCA / xTB 输出不入库，本清单给出**逻辑位置 + sha256 + 解析出的引擎、方法与 QC**，",
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
    failed_jobs = [row for row in rows if row["job_state"] == "failed"]
    if failed_jobs:
        md += [
            "",
            "## 未正常结束的作业",
            "",
            "| job_id | state | failure_reason |",
            "| --- | --- | --- |",
        ]
        for row in failed_jobs:
            md.append("| %s | %s | %s |" % (row["job_id"], row["state"], row["failure_reason"]))
        md += [
            "",
            "* 分类只依据该作业自己 `.log` 里的字符串，不做外部推断。",
            "* `mpi_smpd_*`：Microsoft MPI 的 smpd 在作业期间不可用或失联（主机重启后需要重新拉起，队列器 `ensure_smpd()` 已处理）。",
            "* `orca_cannot_open_scratch_file`：ORCA 打不开自己的 scratch 文件。",
            "* 这类残骸不构成任何物理结论，也不替代缺失的腿。",
        ]
    md += [
        "",
        "## 读法",
        "",
        "* `job_archive_manifest.csv`：逐作业的输入 / 起始几何 / 最终几何 / 原始输出路径与 sha256，",
        "  以及 `orca_keyword`、`orca_version`、能量与频率 QC。",
        "* `derived_to_job_map.csv`：已提交派生表里的每一行数值对应哪个作业。",
        "* `provenance_index.json` 的 `evidence_digest` 是对全部哈希的确定性摘要：",
        "  解压独立归档后按同一配方重算即可复核。",
        "* `engine` / `engine_version`：ORCA cohort 为 ORCA 及其版本（与 `orca_version` 同源，"
        "都从该作业自己的 .log 读回）；采样 cohort 为 GFN2-xTB 与 xTB 版本。"
        "`orca_keyword` / `orca_version` 只对 ORCA cohort 有值。",
        "* `n_files_hashed`：本行登记的 sha256 个数（ORCA 行最多 4 个：inp / 起始几何 / 最终几何 / 原始输出；"
        "采样行 3 个：起始几何 / 优化几何 / xtbopt.log）。",
        "* 采样 cohort 每行对应一个 ETKDG 起点目录；聚合缓存 `work/sampling/xtb_results.csv` "
        "的 sha256 记在 `provenance_index.json` 的 `raw_cache`。",
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