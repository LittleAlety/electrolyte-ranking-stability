"""生成并校验两处脚本索引与旧路径兼容入口。

这个脚本存在的原因：`scripts/wp_production/` 里的文件现在**不是实现**，而是兼容入口。
手工维护 100 多条转发文件与两份索引必然漂移，所以把三件事收进一个带 `--check` 的生成器：

  * `--emit-shims`：按 `registry.json` 重写每个旧路径的 HISTORICAL_ENTRY 转发文件；
  * 默认：重写 `scripts/production/README.md` 与 `scripts/wp_production/README.md`；
  * `--check`：只读复核（新路径存在 / 旧路径与模板逐字节一致 / 两份索引与磁盘一致 / 无未登记脚本）。

判据口径：`--check` 的退出码就是结论；它不写任何文件。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402

PROD = _paths.PRODUCTION_DIR
LEGACY = _paths.LEGACY_ENTRY_DIR
REGISTRY = PROD / "registry.json"

PY_SHIM = '''"""HISTORICAL_ENTRY — 兼容入口；实现已迁移到 ``{new}``。

本文件由 ``scripts/production/build_script_index.py --emit-shims`` 生成，**请勿手工编辑**。
它存在的唯一理由：历史产物把 ``{old}`` 记为生成者，文档与测试也用它作为定位键；
删掉它会让那些已登记的路径悬空（= 破坏可追溯性）。退休条件见 ``scripts/wp_production/README.md``。

实现方式：在**本模块自己的命名空间里** exec 目标源码（而不是复制符号），这样
``monkeypatch.setattr(<本模块>, ...)`` 对目标函数真正生效——222 个测试依赖这一点。
``__file__`` 指向真实实现，目标文件自己的 ``Path(__file__)`` 定位因此正确。
"""
from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "production" / "{cat}" / "{filename}"
if not TARGET.is_file():
    raise SystemExit("HISTORICAL_ENTRY 目标缺失：%s" % TARGET)

__file__ = str(TARGET)
sys.path.insert(0, str(TARGET.parent))
with open(TARGET, encoding="utf-8") as _legacy_fh:
    _legacy_code = compile(_legacy_fh.read(), str(TARGET), "exec")
exec(_legacy_code, globals())
'''

PS1_SHIM = """# HISTORICAL_ENTRY — 兼容入口；实现已迁移到 scripts\\production\\{cat}\\{filename}
# 由 scripts/production/build_script_index.py --emit-shims 生成，请勿手工编辑。
$target = Join-Path $PSScriptRoot "..\\production\\{cat}\\{filename}"
if (-not (Test-Path -LiteralPath $target)) {{
  Write-Error "HISTORICAL_ENTRY 目标缺失: $target"
  exit 1
}}
& $target @args
exit $LASTEXITCODE
"""

PRODUCTION_HEADER = """# `scripts/production/SCRIPT_INDEX.md` —— 逐脚本索引（生成物）

> 本文件由 `scripts/production/build_script_index.py` 生成，**不要手改**；
> `python scripts/production/build_script_index.py --check` 复核它与磁盘一致。
> 手写说明（导数政策 / 一键收口 / 队列纪律）在 `scripts/production/README.md`；
> 逐脚本的详细职责与输入→输出见 `docs/65_repo_layout.md` §3.1。

六类职责（一个文件只属于一类）：

| 目录 | 职责 |
| --- | --- |
{category_table}

公共入口：

| 入口 | 用途 |
| --- | --- |
| `jobs/run_wp2_queue.py` | 生产队列：查状态、断点续跑、并发上限 |
| `ingest/import_hpc_opt_numfreq.py` | 超算 Opt+NumFreq 结果回收与导入 |
| `validation/strict_readiness_wiring.py` | 逐项严格总闸门的证据推导 |
| `ensembles/build_production_ensemble_aggregator.py` | 生产系综聚合（权重 / 去重 / 三态标签） |
| `analysis/build_plan_compliance.py` | 方案逐条合规台账 |
| `release/finalize_wp2.ps1` | 一键收口链 |

历史路径 `scripts/wp_production/<name>.py` 仍然存在，但只是转发到这里的兼容入口，
见 `scripts/wp_production/README.md`。
"""

LEGACY_HEADER = """# `scripts/wp_production/` —— 历史入口兼容层（HISTORICAL_ENTRY）

> 本文件由 `scripts/production/build_script_index.py` 生成，**不要手改**。

**这里没有实现。** 真实实现已按职责迁到 `scripts/production/<category>/`。
本目录下每个 `*.py` 都是同形状的转发文件：被导入时加载真实模块并把符号转出，
被直接执行时以 `__main__` 运行真实文件。

## 为什么必须保留

删除任一兼容入口 = 让一个**已登记路径**悬空：

1. 22 个生成器把 `scripts/wp_production/<自己>.py` 写进已生成的 `*_index.json` / 记录件；
2. `outputs/week26/provenance_refreeze_record.json` 是**冻结历史**，同样记录旧路径；
3. `screen_li_motifs.py` 的路径写在 32 个**已计算** CSV 正文里（重跑需要 xTB）；
4. 243 个测试文件用旧路径作为定位键。

## 实现里为什么还留着旧路径字符串

真实实现里仍能见到 `"generator": "scripts/wp_production/<x>.py"` 这类字面量与
命令示例——这些**故意不改**：

* `generator` 字段是被写进已生成产物里的**稳定标识**；改它等于改产物字节（并作废已核验哈希）；
* 命令示例指的就是本兼容入口，照抄仍然可执行。

分类与真实实现位置以 `scripts/production/SCRIPT_INDEX.md` 为准。

## 提交纪律

`submit_hpc_batch.py` 是唯一正式提交入口；不得直接调用 `hpc submit`。
每条任务使用不可变 `attempts/<attempt-id>`，并在账户级 `.wp2_submit.lock`
保护下执行“运行中 + 排队中 ≤20”门禁。用 `--collect-sacct` 取得终态证据后，
才能判断是否属于自动技术重试。

## 退休条件（三条全满足才可删）

1. 生成器重建后，产物里的 `generator` 全部指向新路径且各自 `--check` 通过；
2. `tests/` 里不再有**以旧路径为入口**的调用——2026-11-07 实测：仍有 88 个测试文件提到
   `scripts/wp_production`，但**读实现源码的命中为 0**（源码读取一律走 `tests/_prod_paths.py`
   的 `prod_script()`）；剩下的都是子进程调用或 `spec_from_file_location`，**当前是有意保留**，
   用来持续验证本兼容层；
3. 交付镜像重建且 `build_physics_completion_deliverables.py --check` 通过。

满足后：删本目录 `*.py`，把 `registry.json` 里对应 `shim` 置 `no`，再跑
`python scripts/production/build_script_index.py --check`。

## 索引（兼容入口 → 真实实现）

| 兼容入口 | 真实实现 | 分类 |
| --- | --- | --- |
{rows}
"""


def _load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _docstring_line(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'^\s*"""(.*?)("""|\n)', text, re.S)
    if match:
        first = " ".join(match.group(1).split())
        if first:
            return first[:120]
    return "—"


def _render_production(reg: dict) -> str:
    rows = []
    for name, desc in reg["categories"].items():
        rows.append("| `%s/` | %s |" % (name, desc))
    body = [PRODUCTION_HEADER.format(category_table="\n".join(rows))]
    for category in reg["categories"]:
        scripts = [r for r in reg["scripts"] if r["category"] == category]
        body.append("\n## `%s/`（%d 个文件）\n" % (category, len(scripts)))
        body.append("| 文件 | 一句话职责 |")
        body.append("| --- | --- |")
        for row in scripts:
            target = _paths.REPO_ROOT / row["new"]
            summary = _docstring_line(target) if target.is_file() else "（缺失）"
            body.append("| `%s` | %s |" % (row["name"], summary.replace("|", "\\|")))
    return "\n".join(body) + "\n"


def _render_legacy(reg: dict) -> str:
    rows = []
    for row in sorted(reg["scripts"], key=lambda r: r["name"]):
        if row["shim"] != "yes":
            continue
        rows.append("| `%s` | `%s` | %s |" % (row["name"], row["new"], row["category"]))
    return LEGACY_HEADER.format(rows="\n".join(rows))


def _split_registry(reg: dict) -> tuple[dict[str, dict], list[str], list[str]]:
    by_old = {r["old"]: r for r in reg["scripts"]}
    names_new = sorted({r["name"] for r in reg["scripts"]})
    names_old = sorted({Path(r["old"]).name for r in reg["scripts"] if r["shim"] == "yes"})
    return by_old, names_new, names_old


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit-shims", action="store_true")
    args = parser.parse_args()

    reg = _load()
    problems: list[str] = []

    production_readme = PROD / "SCRIPT_INDEX.md"
    legacy_readme = LEGACY / "README.md"
    production_text = _render_production(reg)
    legacy_text = _render_legacy(reg)

    for row in reg["scripts"]:
        target = _paths.REPO_ROOT / row["new"]
        if not target.is_file():
            problems.append("缺失真实实现：%s" % row["new"])

    if not args.check:
        if args.emit_shims:
            for row in reg["scripts"]:
                if row["shim"] != "yes":
                    continue
                old = _paths.REPO_ROOT / row["old"]
                filename = Path(row["name"]).name
                if filename.endswith(".py"):
                    old.write_text(PY_SHIM.format(new=row["new"], old=row["old"],
                                                  cat=row["category"], filename=filename),
                                   encoding="utf-8", newline="\n")
                else:
                    old.write_text(PS1_SHIM.format(cat=row["category"], filename=filename),
                                   encoding="utf-8", newline="\n")
        production_readme.write_text(production_text, encoding="utf-8", newline="\n")
        legacy_readme.write_text(legacy_text, encoding="utf-8", newline="\n")
        print("wrote %s  (%d bytes)" % (production_readme.relative_to(_paths.REPO_ROOT).as_posix(),
                                        len(production_text.encode("utf-8"))))
        print("wrote %s  (%d bytes)" % (legacy_readme.relative_to(_paths.REPO_ROOT).as_posix(),
                                        len(legacy_text.encode("utf-8"))))
        return 0

    by_old, names_new, names_old = _split_registry(reg)
    for row in reg["scripts"]:
        if row["shim"] != "yes":
            continue
        old = _paths.REPO_ROOT / row["old"]
        if not old.is_file():
            problems.append("缺失兼容入口：%s" % row["old"])
            continue
        filename = Path(row["name"]).name
        expected = (PY_SHIM.format(new=row["new"], old=row["old"], cat=row["category"],
                                   filename=filename) if filename.endswith(".py")
                    else PS1_SHIM.format(cat=row["category"], filename=filename))
        if old.read_text(encoding="utf-8") != expected:
            problems.append("兼容入口与模板不一致：%s" % row["old"])

    for path, expected, label in ((production_readme, production_text, "scripts/production/SCRIPT_INDEX.md"),
                                  (legacy_readme, legacy_text, "scripts/wp_production/README.md")):
        if not path.is_file():
            problems.append("缺失索引：%s" % label)
        elif path.read_text(encoding="utf-8") != expected:
            problems.append("索引与磁盘不一致：%s（请重跑生成器）" % label)

    for path in sorted(LEGACY.glob("*.py")):
        if path.name not in names_old:
            problems.append("兼容入口未登记到 registry：%s" % path.name)
    for category in reg["categories"]:
        directory = PROD / category
        if not directory.is_dir():
            problems.append("缺失分类目录：%s" % category)
            continue
        for path in sorted(directory.glob("*.py")):
            if path.name not in names_new:
                problems.append("分类目录里有未登记脚本：%s/%s" % (category, path.name))

    if problems:
        print("CHECK FAILED -- %d problem(s)" % len(problems))
        for item in problems:
            print("  -", item)
        return 1
    print("CHECK OK -- %d scripts across %d categories; %d legacy entries consistent"
          % (len(names_new), len(reg["categories"]), len(names_old)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
