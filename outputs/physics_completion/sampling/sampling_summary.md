# 方案 6.1 第 1 轮构象采样（气相 GFN2 筛选）

> 由 `scripts/build_wp2_sampling.py` 生成。采样层是**气相 GFN2-xTB 筛选**，
> 不是生产级 `wB97X-D4 + SMD(acetonitrile)`；它只回答「单一代表结构是否落在同一极小附近」。

| 分子 | 态 | 撒点数 | 独立极小 | 次低极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 16 | 1 | - | 0.330 | 0.615 | single_conformer_representative |
| DMC | M_plus | 16 | 1 | - | 4.098 | 4.098 | sampling_sensitive |
| EMC | M | 16 | 2 | 0.675 | 0.453 | 0.729 | single_conformer_representative |
| EMC | M_plus | 16 | 2 | 3.418 | 16.938 | 9.568 | sampling_sensitive |
| GBL | M | 16 | 1 | - | 0.562 | 0.697 | single_conformer_representative |
| GBL | M_plus | 16 | 1 | - | 6.881 | 4.743 | sampling_sensitive |
| SL | M | 16 | 1 | - | 1.261 | 2.957 | sampling_sensitive |
| SL | M_plus | 16 | 1 | - | 3.487 | 5.496 | sampling_sensitive |

## 升级与停止规则

* 每态先保留最多 **3** 个独立低能极小；只有 3 -> 6 的变化跨过独立容差或改写 Top-k 才升到 6。
* 两轮后仍无法解析就报告 `sampling_limited` / `unresolved`，不为「得到翻转」调窗口。
* Li 配位 motif 采样单列登记，本轮未做。
