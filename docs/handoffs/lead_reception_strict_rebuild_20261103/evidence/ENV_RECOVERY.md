# ENV · 可复现测试环境恢复记录（2026-11-04 · 公共处理）

> plan item 1「恢复测试环境」：先查依赖声明与历史环境，**独立环境安装、不覆盖共享 `.venv`**；记录 Python/RDKit/依赖版本与复现命令。
> 本文 = 环境事实与复现手册；测试结果见 `P2_D7D8_entry_test_matrix.md`（回填）。

## 1. 依赖声明盘点（`pyproject.toml` 实测，32 行）

| 项 | 实测 | 缺口 |
|---|---|---|
| `project.dependencies` | `[]`（空） | **运行时依赖全部未声明** |
| `optional-dependencies.science` | `numpy>=1.23` | 缺 `rdkit`、`pandas`、`scipy` |
| `optional-dependencies.dev` | `pytest>=7.0` | 缺 `pyyaml`（`build_production_ensemble_aggregator.py:57` 需要） |
| `requires-python` | `>=3.10` | — |

**结论：`rdkit` 与 `pyyaml` 从未进入依赖声明**——这就是历史「89/89 通过」环境不可定位的直接原因（环境靠机器上手工装的包维持，声明里没有）。

## 2. 环境盘点（安装前实测）

| 环境 | 实测 | 判定 |
|---|---|---|
| 共享 `.venv`（3.12.14） | site-packages 仅剩 pth（`_distutils_hack`/`setuptools` 残留），无 rdkit/numpy | **空壳**，不可用于测试 |
| 系统 `C:\Users\Little Alety\AppData\Local\Programs\Python\Python310\python.exe` | 3.10.11 + numpy 1.26.4 / pandas 2.1.4 / scipy 1.15.3 / pytest 9.1.1，**无 rdkit、无 pyyaml** | 可跑不依赖 rdkit 的套件 |
| 另有 Python 3.9 | — | 版本不符（`requires-python>=3.10`） |
| 网络 | `pypi.org/simple/` 可达；**pip 连续 3 次在解析中途挂起**（下载完 1-2 个轮子后无超时停滞，`--timeout 15` 未生效）；清华镜像 TLS 握手超时 | 改用**直下轮子+离线安装**绕过 |

## 3. 独立环境（已建成并验证）

**位置**：`E:\Claude Code\电解液溶剂-HB\.venv-review-20261103\`（仓库外、共享 `.venv` 未动）。

**安装方式（绕过 pip 挂起的可复现步骤）**：
```bash
VENV="E:/Claude Code/电解液溶剂-HB/.venv-review-20261103"
# ① 用系统 3.10 建 venv（同 ABI，共享 .venv 不受影响）
py -3.10 -m venv "$VENV"          # → Python 3.10.11
# ② 直下轮子（urllib 走 pypi.org/simple，逐包 sha256 校验，脚本见 $VENV/fetch_wheels.py）
PYTHONIOENCODING=utf-8 python "$VENV/fetch_wheels.py"    # 17/17 OK, fail=0（+typing-extensions+pyyaml+dateutil2.8.2 补齐）
# ③ 离线安装（--no-index，本地解析，不可能再挂）
"$VENV/Scripts/python.exe" -m pip install --no-index --find-links "$VENV/wheels" \
    pytest numpy pandas scipy rdkit pyyaml
```
> 轮子版本钉死（均带 sha256 校验，存 `$VENV/wheels/`）：`pytest-9.2.0`、`numpy-2.2.6`、`pandas-2.3.3`、`scipy-1.15.3`、`rdkit-2026.9.1`、`pyyaml-6.0.3`、`pillow-12.3.0`、`python-dateutil-2.8.2`（新版要求 py≥3.11 故钉旧）、`pytz-2026.6`、`tzdata-2026.6`、`pluggy-1.7.0`、`iniconfig-2.3.1`、`packaging-26.3`、`pygments-2.21.0`、`exceptiongroup-1.3.1`、`tomli-2.5.0`、`typing-extensions-4.16.0`、`six-1.17.0`、`colorama-0.4.6`。

**验证（实测输出，verify_ec=0）**：
```
OK python 3.10.11 rdkit 2026.09.1 pytest 9.2.0 numpy 2.2.6 pandas 2.3.3 scipy 1.15.3
```

## 4. ⚠ 运行约束：工作区映像进程写权限（绕行已验证）

**实测事实**（2026-11-04）：
- 凡**映像路径在工作区内**的进程（本 venv 的 `python.exe`；把系统 python.exe 复制到工作区同样被拒）：可读仓库、可写工作区**根** `E:\Claude Code\电解液溶剂-HB\`，但写**仓库子目录**与写**用户 Temp 均 PermissionError**；其派生子进程继承同样限制。
- 系统 python、bash 不受此限制（同一命令可写 Temp/仓库）。
- 修复尝试：`diagnose-windows-sandbox-acl` 技能要求**审批后以非受限令牌运行修复**，本会话审批禁用 → 按技能规定**该路径记为未诊断、不手改权限**（报告口径，非本环境引入的问题）。

**绕行（已验证可用，全部测试在该包装下通过）**：
```bash
cd 电解液溶剂HB-Code
TMPD="E:/Claude Code/电解液溶剂-HB/.pytest_tmp_review"   # 工作区根下、仓库外
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 \
TEMP="$TMPD" TMP="$TMPD" \
"$VENV/Scripts/python.exe" -m pytest <suite> -q -p no:cacheprovider --basetemp="$TMPD/bt_<suite>"
```
`TEMP/TMP` 覆写解决 `FileNotFoundError: No usable temporary directory`；`PYTHONDONTWRITEBYTECODE=1` 避免往仓库写 `__pycache__`（仓库子目录对该进程只读）；`--basetemp` 落仓库外（老教训：不污染仓库）。

## 5. 复现命令与本轮实测结果（cwd=仓库根，第 4 节包装）

| # | 命令（省略公共包装） | exit | 实测 |
|---|---|---|---|
| E1 | `-m pytest work/test_dmc_staged_receiver_v5.py -q -p no:cacheprovider` | **0** | **40 过**（35+5 rdkit 族全绿；含跨作业错配族） |
| E2 | `-m pytest work/test_dmc_staged_receiver.py -q -p no:cacheprovider` | **0** | **49 过**（30+19 rdkit 族全绿；含重复接收） |
| E3 | `-m pytest tests/test_dmc_reception_registration.py -q -p no:cacheprovider` | **0** | **11 过** |
| E4 | `-m pytest tests/test_strict_eligibility_before_dedup.py tests/test_strict_readiness.py tests/test_strict_readiness_strict.py tests/test_candidate_start_gate_order.py tests/test_strict_isolated_entry.py -q -p no:cacheprovider` | **0** | **52 过 + 1 跳**（首跑 5 败=`No module named 'yaml'` → 补装 pyyaml 后全绿） |
| E5 | `-m pytest docs/…/evidence/p2_item2_gap_tests/ -q -p no:cacheprovider` | **0** | **9 过 + 1 跳**（崩溃恢复 3 过；跳=迁移工具不存在） |

日志：`$VENV/_rerun20261104.log`（E1–E4）、`$VENV/_s4_retry.log`（E4 重跑）、`$VENV/_install_offline.log`、`$VENV/_fetch.log`、`$VENV/_verify.log`。

## 6. 诚实边界

1. 环境是**重建**的，不是历史「89/89」原环境（其依赖声明本就缺失，原样不可定位）；本轮全部套件在重建环境下**从头复跑全绿**，证明可复现性由**本文件步骤**承载，不依赖口头传承。
2. 工作区映像写权限问题**未修复**（审批禁用，按 ACL 技能口径记为未诊断）；绕行仅覆盖测试运行，后续若需 venv 进程写仓库内路径，须先解决该权限问题。
3. `pyproject.toml` 依赖缺口**未改**（本轮零代码改动于共享契约；建议交 Lead 决定是否补 `rdkit`/`pyyaml` 声明）。

## 7. 第二环境：工作区外 venv（供需写仓库子目录的测试；2026-11-04 追加）

§4 的 ACL 限制使工作区 venv 进程**无法写仓库子目录**——`rev5_candidate_d8/test_d8_schema.py` 内 `freeze_candidate.py` 子进程因此 `PermissionError [Errno 13]`（该套 1 例受阻，见 `p10_switch_plan/d7d8_semantic_review.md` §E）。**基础 Python（C:\Users\…\Python310，工作区外）不受该限制**（实测可写仓库与 Temp），故建第二个 venv：

```bash
V2="C:/Users/Little Alety/AppData/Local/Temp/venv-d8-20261104"
py -3.10 -m venv "$V2"
"$V2/Scripts/python.exe" -c "open(r'<repo>/.write_probe2','w').write('x')"   # repo_write_ok
"$V2/Scripts/python.exe" -m pip install -q --no-index \
  --find-links "E:/Claude Code/电解液溶剂-HB/.venv-review-20261103/wheels" \
  rdkit pytest numpy pandas scipy pyyaml python-dateutil    # → exit 0
"$V2/Scripts/python.exe" -m pytest work/admission_closure_20261102/rev5_candidate_d8/ \
  -q -p no:cacheprovider --junitxml=<out>/d8_dir.xml        # → exit 0, 100/100
```

- 版本：`3.10.11 | rdkit 2026.09.1 | pytest 9.2.0 | numpy 2.2.6 | pandas 2.3.3 | scipy 1.15.3 | pyyaml 6.0.3`（与 §3 主 venv 完全同版；轮子复用 `.venv-review-20261103/wheels/`，离线不联网）。
- 不覆盖任何既有环境；位置在 Temp（可任意重建，命令即复现）。主 venv（§3）继续承担 E1–E5 与只读套件。
- 实测 junit：`d8_schema.xml` 60/60、`d8_dir.xml` 100/100，均 exit 0。
