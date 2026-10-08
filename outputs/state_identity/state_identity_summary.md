# C1 还原轴 state-identity 分层（R13）

> 本文件由 `scripts/classify_state_identity.py` 从已冻结的 Week-5 产物现算，不跑任何新 QM 计算。

## 一句话结论

- 全部主 motif 还原态：**n = 10**，C0→C1 Kendall **τ_b = -0.467**，f_robust_inv = 0。
- 只用 `molecule_centered_redox` 的还原态：**n = 1**，排序无定义（成员少于两个，配不成 pair）。
- 冻结标签计数（还原态）：`{"Li_centered_or_mixed_redox": 11, "molecule_centered_redox": 1}`。

## 为什么必须分层

12 个还原态里 11 个外加电子落在 Li 上（`Li_centered_or_mixed_redox`）。电子一旦离开分子，
数值 ranking 的变化就不再是「同一 observable 的排序不稳定」，而是 **observable identity failure**。
因此主还原 ranking 只接受 `molecule_centered_redox`，其余标签一律作为 mechanistic state-identity outcome 单独统计。

## 分层结果

| 轴 | 集合 | n | n_pairs | τ_b | ρ | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| reduction | all states | 10 | 45 | -0.467 | -0.552 | 可排名 |
| reduction | molecule-centered | 1 | 0 | n/a | n/a | **无定义（成员 < 2）** |
| oxidation | all states | 10 | 45 | 0.689 | 0.770 | 可排名 |
| oxidation | molecule-centered | 6 | 15 | 0.733 | 0.829 | 可排名 |

## 冻结还原对的三态重标注

| 状态 | n | 占比 |
| --- | --- | --- |
| STABLE | 4/45 | 0.089 |
| UNRESOLVED | 41/45 | 0.911 |
| ROBUST_INVERSION | 0/45 | 0.000 |

> 还原轴 tau_b = -0.467 的「表面翻转」由 UNRESOLVED 主导（f_unresolved = 0.8），robust inversion = 0；
> 再叠加 state-identity 分层后，只有分子中心还原的态才有资格进入排序，而这类态在本 core set 里只剩 1 个。

## 桶目录

- `outputs/state_identity/li_centered_or_mixed/members.csv` —— Li_centered_or_mixed_redox（11 行）
- `outputs/state_identity/molecule_centered/members.csv` —— molecule_centered_redox（9 行）
- `outputs/state_identity/no_intact_minimum/members.csv` —— no_intact_minimum_found（4 行）

