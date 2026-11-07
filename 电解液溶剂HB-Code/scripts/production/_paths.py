"""`scripts/production/` 的布局契约：仓库根 + 六个分类目录 + 跨分类脚本解析。

为什么需要这个文件（而不是每个脚本各写 `parents[N]`）：

1. **仓库根**。迁移前生产脚本都在 `scripts/wp_production/`，用
   `HERE.parents[1]` / `Path(__file__).resolve().parents[2]` 定位仓库根。搬进
   `scripts/production/<category>/` 之后深度变了，散落的数字会在下一次调整时再错一次。
   这里按「`pyproject.toml` + `src/electrolyte_ranking/` 同时存在」定位，与目录深度解耦。

2. **跨分类导入**。六个分类目录互为可导入模块（例如
   `ingest/import_hpc_opt_numfreq.py` 要 `import orca_derivative_policy`，后者在
   `validation/`）。这里把 `scripts/production` 与全部分类目录一次性放进 `sys.path`。

3. **跨分类脚本调用**。若干个脚本用 `HERE / "peer.py"` 起子进程；搬家后 peer 不再同目录。
   `script_path()` 按文件名在分类目录里解析真实路径（找不到时退回 `scripts/wp_production/`
   的兼容入口，便于历史调用继续工作）。

约定：`scripts/production` 顶层只放**基础设施**（本文件、`build_script_index.py`、
`registry.json`、`README.md`），生产脚本一律落在六个分类目录里。
"""
from __future__ import annotations

import sys
from pathlib import Path

PRODUCTION_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PRODUCTION_DIR.parent

CATEGORY_NAMES = ("jobs", "ingest", "validation", "ensembles", "analysis", "release")


def _locate_repo_root(start: Path) -> Path:
    """向上找到同时含 `pyproject.toml` 与 `src/electrolyte_ranking/` 的目录。"""
    for cand in (start, *start.parents):
        if (cand / "pyproject.toml").is_file() and (cand / "src" / "electrolyte_ranking").is_dir():
            return cand
    raise RuntimeError(
        "无法从 %s 定位仓库根：需要同时存在 pyproject.toml 与 src/electrolyte_ranking/" % start)


REPO_ROOT = _locate_repo_root(PRODUCTION_DIR)

CATEGORY_DIRS = tuple(PRODUCTION_DIR / name for name in CATEGORY_NAMES
                      if (PRODUCTION_DIR / name).is_dir())

# 兼容入口目录：历史产物 / 文档 / 测试以这里的路径作为稳定脚本标识。
LEGACY_ENTRY_DIR = SCRIPTS_DIR / "wp_production"

for _dir in (PRODUCTION_DIR, *CATEGORY_DIRS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))


def script_path(name: str) -> Path:
    """按文件名解析生产脚本的真实路径；退回兼容入口时仍然可用。"""
    for directory in (PRODUCTION_DIR, *CATEGORY_DIRS):
        candidate = directory / name
        if candidate.is_file():
            return candidate
    legacy = LEGACY_ENTRY_DIR / name
    if legacy.is_file():
        return legacy
    raise FileNotFoundError("生产脚本未找到：%s（查找 %s 与 %s）"
                            % (name, PRODUCTION_DIR, LEGACY_ENTRY_DIR))


__all__ = ["REPO_ROOT", "SCRIPTS_DIR", "PRODUCTION_DIR", "CATEGORY_DIRS", "CATEGORY_NAMES",
           "LEGACY_ENTRY_DIR", "script_path"]
