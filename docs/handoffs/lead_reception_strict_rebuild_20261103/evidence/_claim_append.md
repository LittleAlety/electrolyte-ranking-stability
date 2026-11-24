
---

## Claim · lead_reception_strict_rebuild_20261103（只读接收轮，2026-11-03）

**范围**：A 线五态/AN M⁺/AN LiM²⁺/TMP 两态/36 态分组 + B 线数组映射/EC·DMC 哈希/coverage 状态/隔离复跑；全部产出仅在 `docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/`。

**关键发现（供共同修复，本会话不改公共代码）**：
1. `scripts/wp_production/rebuild_strict_isolated.py` 尾部守卫键集不匹配：起始 `input_hashes` 含 corrections jsonl（20 键）而末检只遍历 `INPUTS`（19 键）⇒ corrections 存在时**必误报** "input changed"。已独立证明运行期间 19 输入零漂移；最小修复（两侧键集统一 + 回归测试）**待用户批准**。
2. `build_coverage_reviews.py` 处于未提交三版本态：HEAD `5a73d88f`（v2）→ v7 快照 `1fa95011`（v3）→ 工作树 `ed2b621d`（v3+strict_scope）；`strict_scope=True` 唯一调用方 = `run_eight_terminal_admission.py`，生产主通道走默认 False。
3. 隔离复跑结论：`states.json` 与上游逐字节同（`779dda1c…`）；gap_actions 46/48 同（仅 DMC 两态因元数据更正应用而异）；正式标签/费用等 8 共享面文件起止哈希全等（labels `c21003f5…`、cost `e92fbeeb…`）。
4. A 线判定：五态全部「证据已有但未绑定」（无一态覆盖证据不足）；AN|M⁺ 身份门 HELD（本地限定来源未找到、远端 INACCESSIBLE_NOT_VERIFIED，非身份失败）与单盆地证据分离成立；TMP 两态承重成员 27/c13，缺口为登记起点不合格与去重簇未重建。

**边界**：本会话零新增计算、零作业提交、零共享生产写入、未改阈值/判据/正式标签、未手填 resolved、未迁入未批准跨协议成员；不构成准入结论或用户签认。
**证据**：`docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/`（A1/A2/A3/A4/A5/B2/B3/B4 报告 + b4_* 复跑产物）。
