# P6 · 可重复完整隔离重建入口（Plan action item 6 · 交付）

> 会话：公共处理会话（唯一共享生产写入者）｜2026-11-03。Plan 本身不授权新增计算/账本迁移/正式晋升——本批全部零计算。
> 受控写入面：`scripts/wp_production/rebuild_strict_isolated.py`（**按 action item 1 先存基线**）+ 本目录 evidence。

## 1. 改了什么（写入授权 = Plan item 6「提供可重复的完整隔离重建入口」+ 基线纪律）

**发现的真实缺陷**：入口 `rebuild_strict_isolated.py` 自带跑后冻结复核，但 `:199` 把 `candidate_source_metadata_corrections.jsonl` 加进 `input_hashes`，`:342` 重算时只遍历 `INPUTS` 漏掉该键 → 键集恒不等 → **每次运行都以 `RuntimeError: An input changed…` 收场，入口不可用**（fail-closed 大声拒、非静默；该 corrections 文件建于 12:31，晚于 B4 跑次，故 B4 未触发）。

| 项 | 前 | 后 |
|---|---|---|
| SHA256 | `468dc00ee21a50f5e8cc605c5e855ec67b4a78823352ce09a6f0cc42a78c0bcd` | `83581f169d26a8d3df1f7a7438a5b06d296ff812fff9458b2a6f20052570fc22` |
| 字节数 | 22,313 | 22,475 |
| 修改 | — | `:342` 复核改为与 `:197-199` 同源收集 corrections 路径后再比对（漏收即拒逻辑不变） |
| git | `??`（未跟踪文件，非并行 61 M 集） | `??` 不变 |
| 基线 | `evidence/p6_isolated_entry/baseline/rebuild_strict_isolated.py.orig` + `BASELINE.json` | 保留 |

## 2. 入口（可重复）

```bash
python scripts/wp_production/rebuild_strict_isolated.py --base <独占目录>
# → <base>/run_<sha256(input_hashes)[:16]>/
```
- **内容寻址 run_id**：相同输入 → 同 id（A/B/C 均 `run_e194e35c5585a7dd`）；
- `out.exists()` → `Refusing to overwrite frozen isolated run`（独占，`:202-203`）；
- 跑后全量 INPUTS+corrections 复核，漂移即 RuntimeError 丢弃本次（`:342-347`，本批修复后正确工作）；
- 输出：`states.json`（48 态停点/代表/历史标签）、`gap_actions.json`（逐态阻断原因与下一动作）、`source_index.json`（全量输入+逐成员原始证据哈希）、`README.md`。

验证器：`p6_entry.py`（`c78de6cd…`）三跑编排 + 双向冻结；`shuffle_child.py`（`0195ef1b…`）顺序打乱镜像（仅 mirror 副本行序，真账本只读）。

## 3. 证明了什么（`p6_verification.json` = `ea4dfbb2…`，exit 0 = PASS）

| 验证项（Plan item 6 验证清单） | 实测 |
|---|---|
| 相同输入重复运行科学内容一致 | **A vs B 逐文件字节一致**（`byte_identical=true`，`diff=[]`，含 README/source_index/states/gap_actions 全部） |
| 顺序变化不导致不同判定 | C（STRUCTURES 行序随机置换，seed 20261103）与 A 规范化深比较：`states.json`/`gap_actions.json`/`source_index.json` **三者全等**（`scientific_content_equal` 全 true） |
| 旧簇头失格后合格追随者可恢复 | 恰 1 态命中：`AN|M_plus`（当前 5 成员/1 合格）→ 旧非簇头追随者 `AN|M_plus|tors_3_0_1_2` 恢复为 `strict_kept` 代表（`new_representatives_from_old_nonkept` 非空态=1） |
| 不得写回正式路径 | `outputs/` 全树 **15,118 个文件前后 SHA 全等**；`git status --porcelain`（除本 evidence 目录）前后全等；INPUTS 全量前后 SHA 全等 |
| 冻结全量输入 | 跑前/跑后 `input_hashes` 全等（脚本内嵌复核 + 验证器独立复核双层） |
| 逐态停点/代表变化/标签差异 | `states.json`/`gap_actions.json`：48 态、132 当前成员、分类 `NO_QUALIFIED_MEMBER=40 / COVERAGE_CLAIM_REVIEW_REQUIRED=3 / CONDITIONAL_EVIDENCE_SUFFICIENT=5`——与 B4 隔离跑（`ab72884b97f0104c`）**跨批一致** |
| 费用不变 | COST/COST_INDEX 属 INPUTS 前后 SHA 全等 + outputs 全树零变化（无任何正式费用写入） |

三跑均 exit 0；命令：
```bash
python evidence/p6_isolated_entry/p6_entry.py     # 编排 A/B/C + 双向冻结 + 出 p6_verification.json
```

## 4. 发布了什么

- **正式发布 = 零**：45/2/1 不变、正式表/账本/费用零写入（上表实测）、未提交作业、未新增计算。
- 受控变更仅 `rebuild_strict_isolated.py` 一处（基线在案）+ 本 evidence 目录。

## 5. 没关闭什么

1. **权重/自由能聚合不在本入口输出**：`states.json`/`gap_actions.json` 中自由能字段 0 命中、无数值权重列——本入口止于「资格→去重→coverage→分类」；如需隔离重建产出权重/自由能，须扩聚合步（需另行授权，本批不越权）。
2. `CONDITIONAL_EVIDENCE_SUFFICIENT=5` 仅隔离检查无阻断，**非正式 accepted**；身份/coverage 裁定仍交数据分析。
3. C3(i) 等效规则关闭；DMC 五 staged 腿单列；EC 新候选未入结构账本（`EC|LiM_2plus` 停点照旧）。
4. rdkit 环境缺口（P5 批 5 例）与 D7/D8 切换授权 HOLD 未变。

## 6. 如何恢复

```bash
# 恢复被改脚本（保留并行工作，不用 git reset）：
cp evidence/p6_isolated_entry/baseline/rebuild_strict_isolated.py.orig scripts/wp_production/rebuild_strict_isolated.py
# 删除本批隔离产物：
rm -rf evidence/p6_isolated_entry/runs evidence/p6_isolated_entry/mirror evidence/p6_isolated_entry/p6_verification.json
```

## 7. 复现命令（cwd=仓库根）

```bash
python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p6_isolated_entry/p6_entry.py
# 期望：三跑 exit 0，RESULT: PASS，p6_verification.json 中 same_input_rerun.byte_identical=true、
#       order_variation.scientific_content_equal 全 true、freeze 三项全 true
```
