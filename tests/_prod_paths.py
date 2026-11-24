"""按文件名解析 `scripts/production/` 下的真实实现。

为什么测试需要这个解析器（2026-11 重组）：

实现按职责搬进 `scripts/production/<category>/`，旧路径 `scripts/wp_production/<name>`
只剩**兼容入口**（在本模块命名空间内 exec 真实源码）。

「导入」类测试走兼容入口仍然正确（`__file__` 指向真实实现），但
**「读源码文本」类测试会读到那 20 行转发文件**——于是 `"token" in src` 这类断言
会静默变成「断言一段转发代码」。所以凡是要 `read_text()` 源码的测试，必须先用
`prod_script()` 解析到真实实现。

判据：`grep -rn "scripts/wp_production" tests/` 在源码读取场景应为 0 命中。
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRODUCTION = REPO / "scripts" / "production"
CATEGORIES = ("jobs", "ingest", "validation", "ensembles", "analysis", "release")
LEGACY = REPO / "scripts" / "wp_production"


def prod_script(name: str) -> Path:
    """返回 `name` 在六分类目录里的真实路径；找不到就抛错（不静默回退）。"""
    filename = os.fspath(name)
    for category in CATEGORIES:
        candidate = PRODUCTION / category / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "生产脚本 %s 未在 %s 的六个分类目录中找到" % (filename, PRODUCTION))


class _ProdDirectory:
    """让旧的 `PROD / "x.py"` 写法继续工作，但解析到真实实现。

    `str(PROD)` 仍是 `scripts/production/`（供 `sys.path.insert` 之类使用）；
    `glob()` / `iterdir()` 会跨六个分类目录遍历（实现已不在同一层）。
    """

    def __truediv__(self, name: str | os.PathLike[str]) -> Path:
        return prod_script(os.fspath(name))

    def joinpath(self, name: str | os.PathLike[str]) -> Path:
        return prod_script(os.fspath(name))

    def __str__(self) -> str:
        return str(PRODUCTION)

    def __fspath__(self) -> str:
        return str(PRODUCTION)

    def exists(self) -> bool:
        return PRODUCTION.is_dir()

    def is_dir(self) -> bool:
        return PRODUCTION.is_dir()

    def glob(self, pattern: str) -> list[Path]:
        return sorted(PRODUCTION.rglob(pattern))

    def rglob(self, pattern: str) -> list[Path]:
        return sorted(PRODUCTION.rglob(pattern))

    def iterdir(self) -> list[Path]:
        out: list[Path] = []
        for category in CATEGORIES:
            out.extend(sorted((PRODUCTION / category).iterdir()))
        return out


PROD_DIR = _ProdDirectory()

__all__ = ["REPO", "PRODUCTION", "CATEGORIES", "LEGACY", "prod_script", "PROD_DIR"]
