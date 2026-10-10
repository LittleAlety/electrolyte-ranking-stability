"""归档可重新解析性的契约测试：全部用合成日志 + 临时目录，不依赖 work/、不依赖真归档。

钉住的是三条容易悄悄退化的性质：
1. 生产腿的 E_SP 必须取**热化学段的 `Electronic energy`**（不是起始几何的首个 SP），
   取不到才退回最后一个 `FINAL SINGLE POINT ENERGY`；
2. 交付账本（`production_ledger.csv`）的数值列也必须能由归档日志重算出来——
   这是比 manifest 更强的一条主张；
3. 缺文件、sha256 不符、登记值算不出来，三种情况要分别报出来，不能混成「通过」。
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "verify_archive.py"

INP_NAME = "DMC_LiM_plus.inp"
LOG_NAME = "DMC_LiM_plus.log"
JOB_ID = "wp2prod/DMC/LiM_plus"

INP_TEXT = ("! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) TightOpt TightSCF\n"
            "%maxcore 2000\n%pal nprocs 4 end\n* xyzfile 1 1 geom.xyz\n")

LOG_TEXT = """\
Program Version 6.1.1 - RELEASE
Some ORCA banner text
FINAL SINGLE POINT ENERGY      -9.900000000000

-------------
THERMOCHEMISTRY AT 298.15K
-------------
Electronic energy                ...    -10.50000000 Eh
Total Enthalpy                   ...    -10.45000000 Eh
Final Gibbs free energy         ...    -10.40000000 Eh

VIBRATIONAL FREQUENCIES
-------------
   0:       0.00 cm**-1
   6:     -12.34 cm**-1
   7:      55.10 cm**-1
NORMAL MODES
-------------

THE OPTIMIZATION HAS CONVERGED
****ORCA TERMINATED NORMALLY****
"""

XTB_TEXT = """\
    0.0
   energy: -12.3456789 gnorm: 0.0123 xtb: 6.7.1
    1.0
   energy: -12.3400000 gnorm: 0.0004 xtb: 6.7.1
"""


def _load():
    spec = importlib.util.spec_from_file_location("verify_archive_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _write(root, arcname, text):
    path = root / arcname
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def _production_dir(tmp_path, log_text=LOG_TEXT, write_log=True, write_inp=True):
    """造一个「已解压归档目录」，返回 (module, source, 该作业的 manifest 行)。"""
    module = _load()
    root = tmp_path / "archive"
    if write_log:
        _write(root, "%s/%s" % (JOB_ID, LOG_NAME), log_text)
    if write_inp:
        _write(root, "%s/%s" % (JOB_ID, INP_NAME), INP_TEXT)
    row = {
        "job_id": JOB_ID, "cohort": "wp2_production", "mol_id": "C01", "name": "DMC",
        "state": "LiM_plus",
        "input_path": "work/wp2prod/DMC/LiM_plus/%s" % INP_NAME,
        "input_sha256": _sha(INP_TEXT.encode("utf-8")),
        "raw_output_path": "work/wp2prod/DMC/LiM_plus/%s" % LOG_NAME,
        "raw_output_sha256": _sha(log_text.encode("utf-8")),
        "orca_keyword": "! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) TightOpt TightSCF",
        "orca_version": "6.1.1",
        "final_sp_eh": "-10.50000000",
        "g_single_eh": "-10.40000000",
        "n_freq": "3",
        "imaginary_modes": "1",
        "lowest_freq_cm1": "55.10",
        "opt_converged": "true",
        "terminated": "true",
    }
    return module, module.DirSource(root), row


def test_every_registered_field_is_reproduced_from_the_archived_log(tmp_path):
    module, source, row = _production_dir(tmp_path)
    report = module.verify(source, rows=[row])
    assert report["compared"] == 9, report
    assert (report["mismatched"], report["missing"], report["not_reparsable"]) == (0, 0, 0)
    assert module.render(report) == 0


def test_thermochemistry_wins_over_the_first_single_point(tmp_path):
    """首个 SP 是起始几何的垂直能；E_SP 必须取热化学段（这是历史 bug 的现场）。"""
    module, source, row = _production_dir(tmp_path)
    row["final_sp_eh"] = "-9.900000000000"
    report = module.verify(source, rows=[row])
    assert report["mismatched"] == 1
    assert module.render(report) == 1


def test_single_point_fallback_only_applies_without_thermochemistry(tmp_path):
    module = _load()
    log = ("FINAL SINGLE POINT ENERGY      -9.900000000000\n"
           "FINAL SINGLE POINT ENERGY      -9.950000000000\n")
    _, source, row = _production_dir(tmp_path, log_text=log)
    row = {"job_id": JOB_ID, "cohort": "wp2_production", "final_sp_eh": "-9.950000000000",
           "raw_output_path": row["raw_output_path"]}
    report = module.verify(source, rows=[row])
    assert report["compared"] == 1 and report["mismatched"] == 0
    assert module.render(report) == 0


def test_missing_archive_entry_is_a_failure_not_a_pass(tmp_path):
    module, source, row = _production_dir(tmp_path, write_log=False)
    report = module.verify(source, rows=[row])
    assert report["missing"] == 1
    assert module.render(report) == 1


def test_sha256_mismatch_is_a_failure(tmp_path):
    module, source, row = _production_dir(tmp_path)
    row["raw_output_sha256"] = "0" * 64
    report = module.verify(source, rows=[row])
    assert report["sha_mismatched"] == 1
    assert module.render(report) == 1


def test_unparsable_field_only_fails_under_strict(tmp_path):
    module, source, row = _production_dir(tmp_path, log_text="Program Version 6.1.1\n")
    row = {"job_id": JOB_ID, "cohort": "wp2_production", "n_freq": "3",
           "raw_output_path": row["raw_output_path"]}
    report = module.verify(source, rows=[row])
    assert report["compared"] == 0 and report["not_reparsable"] == 1
    assert module.render(report, strict=False) == 0
    assert module.render(report, strict=True) == 1


def test_sampling_cohort_reads_xtb_opt_log(tmp_path):
    module = _load()
    root = tmp_path / "archive"
    _write(root, "wp2sampling/DMC/M_plus/c00/xtbopt.log", XTB_TEXT)
    row = {"job_id": "wp2sampling/DMC/M_plus/c00", "cohort": "wp2_sampling",
           "mol_id": "C01", "name": "DMC", "state": "M_plus",
           "raw_output_path": "work/sampling/DMC/M_plus/c00/xtbopt.log",
           "engine_version": "6.7.1", "final_sp_eh": "-12.3400000",
           "opt_converged": "true"}
    report = module.verify(source=module.DirSource(root), rows=[row])
    assert report["compared"] == 2
    assert report["mismatched"] == 0
    assert report["out_of_scope"] == 1, "opt_converged 是采样 cohort 的常量登记，不该算作复算字段"


def test_ledger_values_are_reproducible_from_the_archive(tmp_path):
    module, source, row = _production_dir(tmp_path)
    ledger = [{"name": "DMC", "state": "LiM_plus", "e_sp_eh": "-10.50000000",
               "g_single_eh": "-10.40000000", "n_freq": "3", "imaginary_modes": "1",
               "lowest_freq_cm1": "55.10"}]
    report = module.verify_ledger(source, jobs=[row], ledger_rows=ledger)
    assert report["compared"] == 5 and report["mismatched"] == 0
    assert module.render(report) == 0
    ledger[0]["e_sp_eh"] = "-9.900000000000"
    bad = module.verify_ledger(source, jobs=[row], ledger_rows=ledger)
    assert bad["mismatched"] == 1
    assert module.render(bad) == 1


def test_ledger_rows_without_a_manifest_job_are_reported(tmp_path):
    module, source, _row = _production_dir(tmp_path)
    report = module.verify_ledger(source, jobs=[], ledger_rows=[{"name": "SL", "state": "LiM_plus"}])
    assert report["not_reparsable"] == 1
    assert module.render(report, strict=True) == 1


def test_zip_source_works_like_a_directory(tmp_path):
    module, source, row = _production_dir(tmp_path)
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for relative in ("%s/%s" % (JOB_ID, LOG_NAME), "%s/%s" % (JOB_ID, INP_NAME)):
            handle.writestr(relative, (tmp_path / "archive" / relative).read_bytes())
    report = module.verify(module.ZipSource(archive), rows=[row])
    assert report["mismatched"] == 0 and report["missing"] == 0
    assert module.render(report) == 0

def test_freshness_is_proven_by_the_embedded_manifest(tmp_path):
    """归档是否「同版」不能靠猜：内嵌登记表必须与仓库当前那份逐字节一致才算新鲜。"""
    module = _load()
    current = tmp_path / "job_archive_manifest.csv"
    current.write_bytes(b"job_id\nwp2prod/DMC/M\n")
    fresh = tmp_path / "fresh.zip"
    with zipfile.ZipFile(fresh, "w") as handle:
        handle.writestr(module.EMBEDDED_MANIFEST, current.read_bytes())
    report = module.check_freshness(module.ZipSource(fresh), manifest_path=current)
    assert report["embedded_present"] and report["verifiable"] and report["fresh"] is True

    stale = tmp_path / "stale.zip"
    with zipfile.ZipFile(stale, "w") as handle:
        handle.writestr(module.EMBEDDED_MANIFEST, b"job_id\nwp2prod/DMC/LiM_plus\n")
    bad = module.check_freshness(module.ZipSource(stale), manifest_path=current)
    assert bad["verifiable"] and bad["fresh"] is False


def test_an_archive_without_the_embedded_manifest_is_not_declared_fresh(tmp_path):
    """旧版归档没有内嵌登记表：必须报「无法判定」，绝不能默认当成新鲜。"""
    module = _load()
    legacy = tmp_path / "legacy.zip"
    with zipfile.ZipFile(legacy, "w") as handle:
        handle.writestr("wp2prod/DMC/M/DMC_M.log", "Program Version 6.1.1\n")
    report = module.check_freshness(module.ZipSource(legacy))
    assert report["embedded_present"] is False
    assert report["verifiable"] is False
    assert report["fresh"] is False


def test_latest_archive_picks_the_newest_zip(tmp_path):
    module = _load()
    import os
    older = tmp_path / "raw_jobs_1_aaaa_20260101.zip"
    newer = tmp_path / "raw_jobs_2_bbbb_20260102.zip"
    for path in (older, newer):
        with zipfile.ZipFile(path, "w") as handle:
            handle.writestr("x", b"1")
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    assert module.latest_archive(tmp_path) == newer
    assert module.latest_archive(tmp_path / "empty") is None


def test_the_gate_is_advisory_until_the_queue_is_complete(capsys):
    """生产在跑期间归档必然落后于 manifest：门禁必须只提示、不算失败，否则收口链会被永远卡住。"""
    module = _load()
    module.queue_is_complete = lambda: (False, 20)
    assert module.main(["--gate-when-complete"]) == 0
    assert "非门禁" in capsys.readouterr().out
