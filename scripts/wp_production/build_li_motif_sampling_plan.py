"""HISTORICAL_ENTRY — 兼容入口；实现已迁移到 ``scripts/production/ensembles/build_li_motif_sampling_plan.py``。

本文件由 ``scripts/production/build_script_index.py --emit-shims`` 生成，**请勿手工编辑**。
它存在的唯一理由：历史产物把 ``scripts/wp_production/build_li_motif_sampling_plan.py`` 记为生成者，文档与测试也用它作为定位键；
删掉它会让那些已登记的路径悬空（= 破坏可追溯性）。退休条件见 ``scripts/wp_production/README.md``。

实现方式：在**本模块自己的命名空间里** exec 目标源码（而不是复制符号），这样
``monkeypatch.setattr(<本模块>, ...)`` 对目标函数真正生效——222 个测试依赖这一点。
``__file__`` 指向真实实现，目标文件自己的 ``Path(__file__)`` 定位因此正确。
"""
from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "production" / "ensembles" / "build_li_motif_sampling_plan.py"
if not TARGET.is_file():
    raise SystemExit("HISTORICAL_ENTRY 目标缺失：%s" % TARGET)

__file__ = str(TARGET)
sys.path.insert(0, str(TARGET.parent))
with open(TARGET, encoding="utf-8") as _legacy_fh:
    _legacy_code = compile(_legacy_fh.read(), str(TARGET), "exec")
exec(_legacy_code, globals())
