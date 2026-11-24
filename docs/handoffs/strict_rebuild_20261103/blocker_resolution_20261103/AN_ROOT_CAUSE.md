# AN 单簇误判与八态隔离重跑

## 根因与冻结证据

触发输入保留于 `../coverage_generator_sandbox_20261103_v4/input_sandbox/`，实际输出为该目录的 `full_generator_8.json`。`freeze.json` 固定原代码及输入哈希；本目录 `coverage_generator_before.py.snapshot` 与其中原代码 SHA256 完全相同。修复代码另存 `coverage_generator_after.py.snapshot`，版本与哈希见 `code_snapshots.json`。

历史 AN 去重中 primary 是代表，tors_3_0_1_2 是其追随者。严格资格过滤剔除 primary 后，隔离池只含合格的 tors_3_0_1_2，真实去重和权重均只有一个代表。生成器因没有旧成员再指向该代表，将它标为 `new`；随后 `coverage_route` 的第二个 `new` 分支未检查第二个合格独立簇，输出了 `multi_basin_coverage / resolved`。这是生成器缺陷，由正确的严格输入触发；旧 claim 不能作为合格第二簇沿用。

旧决策脚本曾带入历史 duplicate_of 关系，得到 `known` 并走单盆地路线；完整入口使用严格池的去重关系，得到 `new`。两条诊断路径输入语义不同，不能拿旧直接函数试跑替代完整入口。

## 修复与验证

单簇且 novelty 为 new 时，生成器现在输出 `single_basin_scope_review / unresolved`，停点是单盆地搜索范围与生产证据需要单独审查。该处理不将单代表一概判为 coverage 不足；已有 `known`、生产证据与已登记搜索范围齐全的单盆地路线继续保留。

新路由已纳入准入词汇；review version 升为 `coverage_review_v3_strict_basin_guard_20261103`，避免未来入口复用旧语义 verdict。本轮仅运行隔离入口，未生成正式 review。

`tests/test_strict_coverage_single_cluster.py` 与 `tests/test_resolved_route_evidence.py` 最终共 **8 passed**；其中前七项由写入者和独立复审者分别复跑，最后补充的已知单簇正测确认已登记搜索范围齐全时仍可走 `single_basin_verified`。负测运行实际八态隔离入口；双簇正测让真实去重器处理两套不同四碳几何，得到两个独立簇，再运行完整 coverage 入口得到多盆地结果。正测成员资格由合成夹具给定，因此证明范围是去重与路由，并非生产成员资格判定。

## 八态实际路由

完整输出与全部输入 SHA256：`../coverage_generator_sandbox_20261103_v7/full_generator_8.json`、`freeze.json`。冻结新增了 current-attempt 来源索引、探针拒绝 manifest 和所有隔离 CSV，并直接保存拒绝成员集合与生成器源码快照。

| 态 | 实际路由 / verdict | 具体停点 |
|---|---|---|
| AN M⁺ | single_basin_scope_review / unresolved | 合格池仅一簇；64 构象 GFN2 搜索与 methyl-rotor 起点能否支撑目标协议搜索范围仍需审查；前沿身份来源另见候选核实结果 |
| DEC LiM²⁺ | pending / pending | 当前合格成员未形成已登记 recovery start 的覆盖链 |
| DEC M⁺ | pending / pending | 当前合格成员未形成已登记 recovery start 的覆盖链 |
| GBL LiM⁺ | pending / pending | 当前合格成员未形成已登记 recovery start 的覆盖链 |
| PC M⁺ | pending / pending | 当前合格成员未形成已登记 recovery start 的覆盖链 |
| TMP LiM²⁺ | pending / pending | 已登记 r3m_c00 未在当前合格池形成 computed recovery 承重证据 |
| TMP M | pending / pending | 当前合格成员未形成已登记 recovery start 的覆盖链 |
| TMP M⁺ | pending / pending | 已登记 c10、r3_c42 未在当前合格池形成 computed recovery 承重证据 |

这些是生成器实际路由，并非八态科学失败。七个 pending 需要补登记与现有搜索证据绑定；不能自动解释为必须新增计算。
