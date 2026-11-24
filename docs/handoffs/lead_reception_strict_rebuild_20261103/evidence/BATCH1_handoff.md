# 首个执行批次 · 工程交接包（D7/D8 版本核收 → 作业别名对账 → 排除来源守卫 → 五态隔离绑定）

> 会话：公共处理会话（唯一共享生产写入者）｜批次授权：Plan「首个执行批次」原文；**本 plan 本身不授权新增计算、账本迁移或正式晋升**。
> 仓库 HEAD `80933e54f8a605d9dd6d033c0f2861e33b591c13`｜完成时间 2026-11-03。

## 改了什么

| 项 | 对象 | 授权 | 前 → 后 |
|---|---|---|---|
| P1 版本核收 | **无修改**（只读核收） | 首批第 1 项 | receiver 轴 7 版、D7 修复面、D8 缺陷、MANIFEST 时序登记入 `P1_D7D8_version_reconciliation.md` |
| B1 别名对账 | **无修改**（只读对账） | A/B 线交付（已验收） | `B1_scheduling_mapping.csv` `8431547c…` + `.md` `477510e2…` |
| P3 排除来源守卫 | `scripts/wp_production/build_coverage_reviews.py::_rejected_probe_members()` | 首批第 3 项（action item 4 前半） | `ed2b621d…`/27,332B → `a7eee5aa…`/29,558B（原字节副本+BASELINE.json 存 `evidence/p3_exclusion_guard/baseline/`）；新增测试 `tests/test_exclusion_source_completeness.py` `22610644…` |
| P4 五态隔离绑定 | **仅新增** `evidence/p4_five_state_binding/`（绑定器+产物） | 首批第 4 项（隔离演练） | 无前值；产物 `binding_package.json` `4a35436e…`/10,837B |

零共享账本改动、零正式产物改动、零作业、零新增计算、零阈值改动、零 `resolved` 填写。

## 证明了什么

| 项 | 证据（命令 → 实测） |
|---|---|
| P1 | `P1_D7D8_version_reconciliation.md` §6 七条复现（P1-R1..R7 全 exit 0，R5 测试 exit 1 明细=35 passed+5 rdkit 环境败）；D7 修复面绑定 `205f1ba9…`+签章 `e0c47ef9…`；D8 缺陷 `:1821` 与账本三轴偏斜 `c336acb5…` 实测；MANIFEST v2 `9de6c2e0…` missing=[] |
| B1 | 127×19 CSV + 198 行 MD；88 映射/39 歧义/费用仅 0.9 CH；SUMMARY 哈希总表机器补验 `FINAL: OK 10 / NOTFOUND 0 / MISMATCH 0` |
| P3 | `py_compile` exit 0；新旧契约 22/22 exit 0；消费方 `test_strict_coverage_single_cluster` 5/5 exit 0；真实层只读：排除集 3 键、溯源 4/4 sha_ok；负测=损坏/不可读/非对象 manifest 逐律 SystemExit（原静默跳过路径清零） |
| P4 | `--negative-selftest` exit 0（缺 freeze、冻结漂移双拒）；正式跑 exit 0：5 态 × 8 源（4 冻结逐个 SHA 复核）+ 1 显式排除（stale `3f2c692d…`≠`3a795ce8…` 再证）；包内无 `resolved` 键、全 `ISOLATED_CANDIDATE_BINDING`、全 `NOT_TOUCHED` |

## 发布了什么

**无正式发布。** P3 是门控工程修改（预存 M 文件上的授权追加，未提交未推送）；P4 是隔离候选绑定。历史正式状态 **45/2/1 不变**；正式标签、费用账本、coverage 登记、`full_generator_8` 产物均未触碰（P3/P4 后受控面扫描：仅 P3 对象一处写入，其余零）。

## 没有关闭什么

1. **D7 独立复审签章缺口**：`D7_FIX_VERIFICATION.json` 作者独立性未声明 → 交 Lead。
2. **D8**：缺陷仍在当前模块；账本三轴偏斜保持盘态未迁移；切换授权（Open question 1）未裁 → 保持 HOLD。
3. **五态身份与 coverage 裁定**：全 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW` → 交数据分析；生产侧 `registered_starts`/`coverage_review_id` 绑定待批准。
4. **rdkit 环境缺口**：三解释器均无，历史 89/89 环境不可定位 → 未确定，不自行改造环境。
5. Plan action items 5–9（准入门、隔离重建入口、受保护提交、正式发布、归档）与其余 Open questions 不在本批范围。

## 如何恢复

```bash
# P3（唯一被改共享对象）：原字节副本已存，恢复后 sha256 应为 ed2b621d30f8df5c2f3088f56012d7ca66447591918b2f00114ff06af2ad6784
cp docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p3_exclusion_guard/baseline/build_coverage_reviews.py.orig \
   scripts/wp_production/build_coverage_reviews.py
# P3 新测试（如需回退）：rm tests/test_exclusion_source_completeness.py
# P4：整目录删除即回改前状态
rm -r docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/
```
未使用 `git reset`；未覆盖任何并行工作（本批写入面 = evidence/ + 该一个授权共享对象 + 测试新文件）。

## 逐项证据文件

- `P1_D7D8_version_reconciliation.md`（含 §6 复现命令与 exit code、§8 对象哈希总表）
- `SUMMARY.md`（A/B 两线终稿，哈希总表机器补验全绿）
- `P3_exclusion_source_guard.md`（基线/修改/测试/恢复）
- `P4_five_state_binding.md`（绑定配方/输入哈希总表/负测/边界）
