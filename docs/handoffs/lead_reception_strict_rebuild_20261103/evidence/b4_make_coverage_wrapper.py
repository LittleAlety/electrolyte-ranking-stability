#!/usr/bin/env python3
"""b4_make_coverage_wrapper.py — 从公共跑器生成私有隔离副本（仅改 OUT 与 import 路径）。

公共文件保持原字节不动；本脚本只写 evidence/ 目录。
用法: python b4_make_coverage_wrapper.py   (cwd = 仓库根)
"""
import hashlib
from pathlib import Path

SRC = Path("scripts/wp_production/run_coverage_generator_strict_sandbox.py")
DST = Path("docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/b4_coverage_rerun.py")

src = SRC.read_text(encoding="utf-8")
orig_out = 'OUT = ROOT / "docs/handoffs/strict_rebuild_20261103/coverage_generator_sandbox_20261103_v7"'
new_out = 'OUT = ROOT / "docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/b4_coverage_rerun"'
assert src.count(orig_out) == 1, "OUT 行定位失败"
src = src.replace(orig_out, new_out)

old_head = 'HERE = Path(__file__).resolve().parent\nROOT = HERE.parents[1]\nsys.path.insert(0, str(HERE))'
new_head = ('HERE = Path(__file__).resolve().parent  # evidence/（私有副本位置）\n'
            'ROOT = HERE.parents[3]  # evidence → lead_reception… → handoffs → docs → 仓库根\n'
            'sys.path.insert(0, str(ROOT / "scripts/wp_production"))')
assert src.count(old_head) == 1, "路径头定位失败"
src = src.replace(old_head, new_head)

fut = "from __future__ import annotations\n"
assert src.count(fut) == 1
src = src.replace(fut, fut + '\n# b4_coverage_rerun.py — 私有隔离副本；源=run_coverage_generator_strict_sandbox.py sha '
                  + hashlib.sha256(SRC.read_bytes()).hexdigest()
                  + "；仅改 OUT→本目录与 import 路径，公共文件未改。\n", 1)

DST.write_text(src, encoding="utf-8")
print("wrote", DST)
print("wrapper sha", hashlib.sha256(DST.read_bytes()).hexdigest())
print("source sha ", hashlib.sha256(SRC.read_bytes()).hexdigest())
