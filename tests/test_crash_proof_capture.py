"""驱动落盘纪律：ORCA 的 stdout/stderr 必须**边走边落盘**，不能等进程结束才写。

2026-10-10 的 `GBL|LiM_plus` 被 MPI 失联打断时，`subprocess.run(capture_output=True)`
把四个多小时的计算留在内存里一起丢掉——没有 log、没有现场，只能整条重跑。
这里钉住替代实现 `run_batch.capture_run` 的三条性质：

1. 子进程**还在跑**时，`<log>.stdout.tmp` 里就已经能读到输出；
2. 正常结束时 `<log>` 的文本 == `stdout + "\\n" + stderr`（与既有 10 条腿的字节约定一致，
   provenance 与 `verify_archive.py` 照样能哈希）；
3. 子进程非零退出也照样落盘（不吞现场）。
"""

from __future__ import annotations

import importlib.util
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "run_batch.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_batch_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read(path):
    """log 用默认换行写（Windows 上是 CRLF），比较前先归一化。"""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_log_matches_the_legacy_concatenation(tmp_path):
    module = _load()
    log = tmp_path / "job.log"
    code, text, wall = module.capture_run(
        [sys.executable, "-u", "-c", "import sys; print('OUT'); print('ERR', file=sys.stderr)"],
        tmp_path, log)
    assert code == 0 and wall >= 0
    assert (tmp_path / "job.log.stdout.tmp").read_text(encoding="utf-8") == "OUT\n"
    assert (tmp_path / "job.log.stderr.tmp").read_text(encoding="utf-8") == "ERR\n"
    assert text == "OUT\n\nERR\n"
    assert _read(log) == text


def test_partial_output_is_on_disk_while_the_child_still_runs(tmp_path):
    module = _load()
    log = tmp_path / "slow.log"
    result = {}

    def _run():
        try:
            result["value"] = module.capture_run(
                [sys.executable, "-u", "-c", "import time; print('PARTIAL'); time.sleep(6)"],
                tmp_path, log)
        except Exception as exc:  # pragma: no cover - 只在实现坏掉时走到
            result["error"] = exc

    thread = threading.Thread(target=_run)
    thread.start()
    tmp = tmp_path / "slow.log.stdout.tmp"
    deadline = time.time() + 4
    while time.time() < deadline and not (tmp.is_file() and "PARTIAL" in tmp.read_text(encoding="utf-8")):
        time.sleep(0.1)
    assert tmp.is_file() and "PARTIAL" in tmp.read_text(encoding="utf-8"), \
        "子进程还在跑时就应该能从 .stdout.tmp 读到输出"
    assert not log.is_file(), "进程没结束前不该写最终 log"
    thread.join(timeout=30)
    assert "error" not in result, result.get("error")
    code, text, _wall = result["value"]
    assert code == 0
    assert _read(log).startswith("PARTIAL")


def test_nonzero_exit_still_writes_the_log(tmp_path):
    module = _load()
    log = tmp_path / "fail.log"
    code, text, _wall = module.capture_run(
        [sys.executable, "-u", "-c", "print('ABORTING'); raise SystemExit(9)"], tmp_path, log)
    assert code == 9
    assert "ABORTING" in text
    assert _read(log).strip() == "ABORTING"


def test_drivers_use_capture_run_instead_of_capture_output():
    """不许回退到 `capture_output=True`：那正是丢现场的那一行。"""
    for name in ("run_wp2_production.py", "run_wp2_extra.py"):
        text = (REPO_ROOT / "scripts" / "wp_production" / name).read_text(encoding="utf-8")
        assert "capture_run(" in text, "%s 没有用 capture_run" % name
        assert "capture_output" not in text, "%s 又用回了 capture_output" % name