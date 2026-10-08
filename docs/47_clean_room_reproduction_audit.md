# 47 · Clean-room 复现审计（R14）

- 日期：2026-10-08
- 触发：第二轮外部评审第 6 项 —— 「做一次真正的 clean-room reproduction test；
  README 里 `..\成果输出\`、`..\核心文件\`、`..\论文\` 是最明显的 reproducibility boundary」
- 生成器：`scripts/audit_clean_room.py`（离线、只读、不跑新电子结构）
- 生成物：`outputs/week26/clean_room_audit.json`、`outputs/week26/clean_room_audit.md`

## 0. 一句话结论

**仓库内的可复现面与仓库外的交付层已经被显式切开。** 一个全新 clone 在**没有本机
ORCA / xTB、没有 `..\成果输出\` / `..\核心文件\` / `..\论文\`** 的情况下，可以完成
全部 `--check`、全部 manifest 复算与全部测试；只有「新增电子结构计算」才需要那两样
本机资源。

## 1. 复现边界

| 层 | 位置 | 是否随 GitHub 分发 | 作用 |
| --- | --- | --- | --- |
| **代码 / 数据 / 产物层** | 仓库内 `config/ data/ docs/ outputs/ scripts/ src/ structures/ tests/`、`README.md`、`FINAL_CONCLUSIONS.md` | 是 | 一切数字、图、检查与测试的唯一来源 |
| **交付层** | 仓库外 `..\成果输出\`、`..\核心文件\`、`..\论文\` | **否** | 下游派生的汇总件与论文稿；引用它只是交付说明 |
| **本机算力层** | `E:\ORCA软件\ORCA\orca_6_1_1`、`.toolchain\xtb\...` | **否** | **只**用于新增电子结构计算 |

> 结论：任何 `--check` / manifest 复算 / `pytest` 都**不**依赖后两层。

## 2. Clean-room 流程（在全新 clone 中依次执行）

```powershell
.venv\Scripts\python.exe scripts\build_metadata.py --check
.venv\Scripts\python.exe scripts\build_github_readme.py --check
.venv\Scripts\python.exe scripts\build_final_conclusions.py --check
.venv\Scripts\python.exe scripts\analyze_r13_summary_figure.py --check
.venv\Scripts\python.exe scripts\audit_clean_room.py
.venv\Scripts\python.exe scripts\build_terminal_site.py --check
.venv\Scripts\python.exe scripts\freeze_gates.py --stage 2
.venv\Scripts\python.exe -m pytest
```

`freeze_gates.py --stage 2` 是**重写** Stage-2 产物摘要（`outputs/week3/SHA256SUMS`），
因此它是「重冻结」而不是「校验」；校验由 `audit_clean_room.py` 的 C6 完成。

## 3. 审计项与当前结果

| 检查 | 内容 | 结果 |
| --- | --- | --- |
| C1 | 仓库内可复现面是否齐全（12 项顶层条目） | PASS |
| C2 | README 点名的验证入口是否都存在（7 项） | PASS |
| C3 | 哪些脚本会走到仓库外（交付层 / 历史 W24 审计） | INFO（0 个是验证入口） |
| C4 | 测试是否引用仓库外路径 | PASS（0 处） |
| C5 | 本机 ORCA / xTB 是否必需 | INFO（只对新增计算必需） |
| C6 | `outputs/week1|2|3/SHA256SUMS` 逐行复算 | PASS（7458 行全匹配） |
| C7 | README Scope / NOT CLOSABLE 与 `FINAL_CONCLUSIONS.md` 10 问 | PASS |

实时数值以 `outputs/week26/clean_room_audit.md` 为准（本表是它的摘要）。

## 4. 已知的仓库外依赖（非验证路径）

| 脚本 | 读/写对象 |
| --- | --- |
| `scripts/analyze_w24_alignment.py` | `..\核心文件`、`..\论文` |
| `scripts/analyze_w24_audit.py` | `..\核心文件`、`..\论文`、`..\成果输出` |
| `scripts/analyze_w24_decision.py` | `..\核心文件\ranking-electrolyte-materials-v2.md` |
| `scripts/build_compute_budget_ledger.py` | 同上（只用于抄录 §21 条款原文） |
| `scripts/build_week25_deliverables.py` | 写 `..\成果输出\week25_gate1` |
| `scripts/scan_stage15_anchor_literature.py` | `..\核心文件\文献` 本地 PDF |

这些脚本是**历史审计与交付打包**，不是 README 列出的验证入口；在 clean-room 里
不运行它们不影响任何结论。

## 5. 明确**不**在 clean-room 覆盖范围内的事

- **新增电子结构计算**（ORCA / xTB 作业）：需要一个装好 ORCA 与 xTB 的机器；
  这是算力前提，不是复现缺陷。
- **交付层重建**（`build_deliverables.py` 等）：需要 `..\核心文件` 与 `..\成果输出`。
- **提交 hash 与工作树字节的一致性**：本审计复算的是各 `SHA256SUMS` 声明的字节，
  不校验 git 对象；跨平台行尾由 `.gitattributes` 的 `* text=auto eol=lf` 统一。

## 6. 残余风险

- C3 是**源码级启发式**（「向上走 `.parent` 且命名了交付层目录」），不是形式化证明；
  绑定证据是 C2（入口齐全）、C4（测试零外部引用）、C6（7458 行摘要全匹配）。
- C5 只记录「不需要」，不记录本机是否装了 ORCA / xTB（保持报告与机器无关）。
- 若未来新增脚本引用交付层，`audit_clean_room.py` 会把它列进 C3；若新增**验证入口**
  引用交付层，C3 会直接判 FAIL。
