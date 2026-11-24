"""Bind existing submission bytes to candidate result attestations, read-only."""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import hashlib
import json
import tarfile
from pathlib import Path

ROOT = _paths.REPO_ROOT
OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/candidate_sources.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_record(path):
    return {"path": path, "sha256": sha((ROOT / path).read_bytes())}


def bind(tar_path, prefix, result_path, local_result_inputs=False):
    result = json.loads((ROOT / result_path).read_text(encoding="utf-8"))
    stages = {}
    with tarfile.open(ROOT / tar_path) as archive:
        names = set(archive.getnames())
        for stage in ("opt", "freq"):
            member = prefix + f"job_{stage}.inp"
            if member not in names:
                member = next(n for n in names if n.endswith("/" + member))
            raw = archive.extractfile(member).read()
            digest = sha(raw)
            expected = result["stages"][stage]["input_sha256"]
            assert digest == expected, (tar_path, stage)
            log = Path(result_path).parent / stage / f"job_{stage}.log"
            log_raw = (ROOT / log).read_bytes()
            log_digest = sha(log_raw)
            assert log_digest == result["stages"][stage]["log_sha256"]
            first = raw.decode().splitlines()[0]
            log_text = log_raw.decode("utf-8", errors="replace")
            assert first in log_text, (log, first)
            record = {"archive_member": member, "archive_input_sha256": digest,
                      "workflow_input_sha256": expected, "matches": True,
                      "input_first_line": first, "log": log.as_posix(),
                      "log_sha256": log_digest, "input_first_line_echo_matches": True}
            if local_result_inputs:
                local = Path(result_path).parent / stage / f"job_{stage}.inp"
                record["returned_input"] = file_record(local.as_posix())
                assert record["returned_input"]["sha256"] == digest
            stages[stage] = record
        inputs_manifests = [n for n in names if n.startswith(prefix) and n.endswith("inputs.sha256")]
        manifests = [{"archive_member": n, "sha256": sha(archive.extractfile(n).read()),
                      "content": archive.extractfile(n).read().decode()} for n in inputs_manifests]
    return {"result": file_record(result_path), "stages": stages, "input_hash_manifests": manifests}


def main():
    if OUT.exists():
        raise SystemExit("refusing to overwrite source verification")
    an_log = "work/hpc_torsion_probe_v2_realfragment/tasks/AN/M_plus__tors_3_0_1_2/snapshots/3749450_0/job.log"
    task_dir = ROOT / "work/hpc_frontier_localization_v1/tasks"
    an = {"member": "AN|M_plus|tors_3_0_1_2", "existing_opt_freq_log": file_record(an_log),
          "frontier_task_expected": "work/hpc_frontier_localization_v1/tasks/AN__M_plus__tors_3_0_1_2",
          "frontier_task_exists": (task_dir / "AN__M_plus__tors_3_0_1_2").exists(),
          "an_frontier_task_dirs_present": sorted(p.name for p in task_dir.glob("AN__M_plus*")),
          "conclusion": "本地独立前沿身份链缺失；已有优化/频率日志不能替代该来源；远端未核"}
    assert not an["frontier_task_exists"]
    ec_tar = "work/ec_coord_safe_20261102/hpc_ec_safe_coord_20261102.tar.gz"
    ec_submission = "work/hpc_ec_safe_coord_20261102/submission_journal.json"
    journal = json.loads((ROOT / ec_submission).read_text(encoding="utf-8"))
    submission = next(s for s in journal["submissions"] if s["job_id"] == "3953361")
    ec = {"job_id": "3953361", "remote_workdir": submission["remote_workdir"],
          "tar": file_record(ec_tar), "submission": file_record(ec_submission),
          "upload_check": file_record("work/ec_coord_safe_20261102/UPLOAD_CHECK.txt"),
          "candidates": []}
    upload = (ROOT / ec["upload_check"]["path"]).read_text()
    for candidate in ("ring_o2_monodentate", "ring_o2_o5_bidentate"):
        prefix = f"hpc_ec_safe_coord_20261102/tasks/{candidate}/"
        for stage in ("opt", "freq"):
            assert f"tasks/{candidate}/job_{stage}.inp: OK" in upload
        ec["candidates"].append({"candidate": candidate, **bind(ec_tar, prefix,
            f"work/ec_followup_20261103/results/{candidate}/workflow_result.json")})
    ec["conclusion"] = "本地原提交包、上传校验、作业记录与实际结果输入哈希吻合；先前指向endpoint_pair包错误；远端阶段文件独立复核未完成"
    dmc_tar = "work/ec_dmc_campaign_20261031/hpc_ec_dmc_dmc_li_strict_20261031.tar.gz"
    dmc_sub = "work/ec_dmc_campaign_20261031/SUBMISSIONS.json"
    submission = next(s for s in json.loads((ROOT / dmc_sub).read_text()) if s["job_id"] == "3928500")
    dmc = {"candidate": "3928500_0", "job_id": "3928500", "remote_workdir": submission["remote_workdir"],
           "tar": file_record(dmc_tar), "submission": file_record(dmc_sub),
           "upload": file_record("work/ec_dmc_campaign_20261031/hpc_ec_dmc_dmc_li_strict_20261031_upload.txt"),
           **bind(dmc_tar, "hpc_ec_dmc_dmc_li_strict_20261031/tasks/DMC/LiM_2plus__dmc_li_strict/",
                  "work/ec_dmc_campaign_20261031/results/3928500_0/workflow_result.json", True),
           "actual_protocol": "VeryTightSCF SlowConv",
           "conclusion": "提交字节、返还输入、结果输入hash及日志回显一致；旧TightSCF账本标签应作为待更正元数据；C3(i)几何/频率等效规则仍未批准"}
    for stage in dmc["stages"].values():
        assert "VeryTightSCF SlowConv" in stage["input_first_line"]
    remote = {"status": "INACCESSIBLE_NOT_VERIFIED", "cause": "受控桥doctor因专用密钥沙箱读取权限未通过；提权等待审批后中断",
              "no_remote_file_read": True, "no_new_computation": True}
    OUT.write_text(json.dumps({"an_frontier": an, "ec": ec, "dmc": dmc, "remote": remote},
                              ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("3 source issues verified locally; remote independently unverified")


if __name__ == "__main__":
    main()
