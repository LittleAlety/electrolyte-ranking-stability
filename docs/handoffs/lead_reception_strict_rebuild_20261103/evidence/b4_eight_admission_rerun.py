#!/usr/bin/env python3
"""b4_eight_admission_rerun.py — 八态准入通道（strict_scope=True）隔离复跑。

公共文件不动：仅把 run_eight_terminal_admission.OUT 重定向到本 evidence 目录后调用 main()。
用法: PYTHONIOENCODING=utf-8 python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/b4_eight_admission_rerun.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # evidence→lead_reception→handoffs→docs→仓库根
sys.path.insert(0, str(ROOT / "scripts/wp_production"))
import run_eight_terminal_admission as eta  # noqa: E402

eta.OUT = ROOT / "docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/b4_eight_admission_rerun"
eta.main()
print("rerun OUT =", eta.OUT)
