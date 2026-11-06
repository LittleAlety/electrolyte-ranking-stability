# 有界收尾报告（五项修正；未发布）

**对象**：coverage v4 `7e8584e8…`；**未改候选/科学规则/正式文件**。

## 1. 已修五项

1. **结果哈希对账（更正）**：`d483f76a…` 的**引用载体已找到**——`work/lead2_ledger_v4_20261104/round23_an_closure_20261106/RELEASE_APPLICATION_FINAL.md` 第 38 行。对应结果字节是否留存、该哈希如何生成 **UNVERIFIED**（现 `rebuild_run/REPLAY_RESULT.json` 为 `213b7a1b…`，d483 旧字节未保留）；`coverage_review_20261106/RELEASE_APPLICATION.md`（`7b5e2cf6…`）不含 d483。不能写“旧申请/旧结果保留 d483”。本轮 v2 结果 `19f02168a0d9cf30b602e9fc663530bb73cff3e6c0097c5259cdd2c90609f49f`（76,990 B），由申请文本与外部 `.sha256` 记录绑定；**`REPLAY_RESULT.json` 不内嵌自身哈希**（自哈希不可能）。
2. **真实写入集**：`production_ensemble_dedup_pairs.csv` 已列入发布集/备份；内容四版均 `4d294544…`，但标“会重写、预期字节不变”。
3. **真实读取依赖**：`dependencies_before/after` 登记 **145** 件（三表+labels/weights/dedup/dedup_pairs/manifest+search索引+两份config+动态 probe manifests+聚合器实际几何+冻结 evidence）；前后一致，`formal_unchanged=true`。
4. **fail-closed 入口**：脚本 `47f8e3036abd938c1e9206f9e29265b83982dcbb809cd7effcf9aa03547cebf4`；退出码 2=输入漂移、3=子步骤失败、4=预期不符、5=缺必需输入。负测（独立副本）实际：输入漂移 **2**、子步骤失败 **3**（真实 old 候选 SyntaxError，不是模拟退出码）、预期不符 **4**、缺输入 **5**，均生成 `FAILURE.json`。
5. **证据索引同名覆盖**：`evidence` 键改为相对证据根路径，14 件全部保留；B/C 6 个同名文件由 `B_C_FIXTURES_INDEX.json` 覆盖 6/6。

## 2. 四版结果

| 版本 | counts | labels | weights | dedup_pairs |
|---|---|---|---|---|
| disk | 45/2/1 | `c21003f5…` | `201e1954…` | `4d294544…` |
| shared | 44/3/1 | `280d78ca…` | `201e1954…` | `4d294544…` |
| old | 43/4/1 | `2458f0af…` | `201e1954…` | `4d294544…` |
| v4 | 43/4/1 | `2458f0af…` | `201e1954…` | `4d294544…` |

## 3. 剩余限制

- **B/C 条件回归 OPEN**：仅索引 6/6，未重跑。
- 发布未授权；未改正式表、未登记成员、未入账、未提交作业/git。
- 三态 L2b、可比性、EC 10°、`coord_1` 与新增成员准入均单列，不因本次重放关闭。

## 4. 负测记录

{
  "expected_mismatch": {
    "expected_exit": 4,
    "actual_exit": 4,
    "failure_file": true
  },
  "input_drift": {
    "expected_exit": 2,
    "actual_exit": 2,
    "failure_file": true
  },
  "substep_failure": {
    "expected_exit": 3,
    "actual_exit": 3,
    "failure_file": true
  },
  "missing_input": {
    "expected_exit": 5,
    "actual_exit": 5,
    "failure_file": true
  }
}
