# Stage 20 / Part 1 -- 第六级台阶：P2 单点 -> P2 弛豫

本文件由 `scripts/analyze_stage20_relax_rung.py` 生成；**本周没有跑任何新的量化计算**，
只是把 Stage 19（Week 18）已经落盘的 37 格弛豫能量放到 Stage 10 五级台阶的同一把尺子上。

## 1. 台阶的定义

一个几何弛豫只会压低带电态，所以这条台阶按轴分开定义：

```
Delta_ox(name)  = p_ox(弛豫)  - p_ox(单点)  = - drop(cation)
Delta_red(name) = p_red(弛豫) - p_red(单点) = - drop(anion)
```

两个轴都是「越大越稳」，所以 **Delta 为负 = 弛豫把该轴的值推低**。

## 2. 总量

| 切片 | n_cells | 分子数 | shift_mean (eV) | shift_std (eV) | 相对散布 std/|mean| | min (eV) | max (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 全 37 格 | 37 | 7 | -1.372 | 0.714 | 0.52 | -2.440 | -0.191 |
| cation（氧化轴） | 16 | 3 | -0.610 | 0.315 | 0.52 | -0.850 | -0.191 |
| anion（还原轴） | 21 | 4 | -1.953 | 0.160 | 0.08 | -2.440 | -1.757 |

两轴方向一致（都被推低），但**位移的类型完全不同**：还原轴是「平移型」，氧化轴是「散布型」。

## 3. eps 不敏感性：弛豫是一个「态内量」

同一个 (分子, 态) 在它已有的各个介电常数上，Delta 几乎不动：

| 分子 | 态 | n_eps | eps 范围 | Delta 极差 (eV) | Delta 均值 (eV) |
| --- | --- | --- | --- | --- | --- |
| DEC | anion | 3 | 5-200 | 0.215 | -1.842 |
| DMC | cation | 1 | 5-5 | 0.000 | -0.335 |
| EC | cation | 5 | 5-20 | 0.011 | -0.195 |
| EMC | anion | 6 | 5-1000 | 0.026 | -1.944 |
| PC | anion | 10 | 5-1000 | 0.053 | -1.900 |
| TEGDME | anion | 2 | 20-200 | 0.064 | -2.408 |
| TMP | cation | 10 | 5-1000 | 0.007 | -0.845 |

极差中位 **0.0263 eV**、最大 **0.215 eV**（DEC）；作为对照，同一批分子的单点环境位移（P1->P2）是 -2.1 ~ -2.9 eV。
也就是说 **弛豫修正几乎与连续介质的介电常数无关**，是一个态内量；
它与「环境位移随 eps 强烈变化」形成直接对照。

## 4. 放在五级台阶的同一把尺子上

Stage 10 的中心结论是「决定排序是否被改写的是位移的**离散度**，不是位移的大小」。
下表把新台阶与五级台阶在**同一批分子**上并列（因此可比），只列与该台阶同轴的那一半：

### ox_dmc_ec_tmp_eps5（axis = oxidation，DMC;EC;TMP）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
| --- | --- | --- | --- |
| P0_to_P1 | -1.661 | 0.173 | 0.10 |
| P1_to_P2 | -2.346 | 0.398 | 0.17 |
| G1_to_G2 | -0.016 | 0.053 | 3.31 |
| P2sp_to_P2relax | -0.462 | 0.342 | 0.74 |

### ox_carbonates_eps5（axis = oxidation，DMC;EC）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
| --- | --- | --- | --- |
| P0_to_P1 | -1.568 | 0.092 | 0.06 |
| P1_to_P2 | -2.559 | 0.211 | 0.08 |
| G1_to_G2 | +0.014 | 0.003 | 0.24 |
| P2sp_to_P2relax | -0.269 | 0.094 | 0.35 |

### ox_all_eps_mean（axis = oxidation，DMC;EC;TMP）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
| --- | --- | --- | --- |
| P0_to_P1 | -1.661 | 0.173 | 0.10 |
| P1_to_P2 | -2.346 | 0.398 | 0.17 |
| G1_to_G2 | -0.016 | 0.053 | 3.31 |
| P2sp_to_P2relax | -0.459 | 0.342 | 0.75 |

### red_dec_emc_pc_tegdme_eps20（axis = reduction，DEC;EMC;PC;TEGDME）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
| --- | --- | --- | --- |
| P0_to_P1 | +7.494 | 2.960 | 0.39 |
| P1_to_P2 | -2.165 | 0.557 | 0.26 |
| G1_to_G2 | -0.081 | 0.008 | 0.09 |
| P2sp_to_P2relax | -2.010 | 0.254 | 0.13 |

### red_dec_emc_pc_eps5（axis = reduction，DEC;EMC;PC）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
| --- | --- | --- | --- |
| P0_to_P1 | +8.973 | 0.110 | 0.01 |
| P1_to_P2 | -2.428 | 0.224 | 0.09 |
| G1_to_G2 | -0.081 | 0.008 | 0.09 |
| P2sp_to_P2relax | -1.947 | 0.023 | 0.01 |

### red_all_eps_mean（axis = reduction，DEC;EMC;PC;TEGDME）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
| --- | --- | --- | --- |
| P0_to_P1 | +7.494 | 2.960 | 0.39 |
| P1_to_P2 | -2.165 | 0.557 | 0.26 |
| G1_to_G2 | -0.081 | 0.008 | 0.09 |
| P2sp_to_P2relax | -2.024 | 0.260 | 0.13 |

## 5. 结论

1. **弛豫不是「另一个环境」**：它的位移几乎与 eps 无关（极差中位 0.0263 eV），而 P1->P2 的环境位移是 -2.1 ~ -2.9 eV。
2. **它也不是「纯平移」**：还原轴接近刚性平移（相对散布 0.08），氧化轴的相对散布 0.52，是六级台阶里最大的之一。
3. 按 Stage 10 的 H_var 判据（rho(std, tau_b) = -0.851），这条台阶在**还原轴上几乎不可能改写排序**，
   而在**氧化轴上具备改写排序所需的散布**。
4. 因此 Week 18 §10 提的「回填 P2 腿」问题有了定性答案：把弛豫当第六级台阶，它对**还原**排序是安全的，
   对**氧化**排序不是；后者应该在下一次真正改动 P2 腿时被显式检验。

## 6. 读法纪律

- **不报 tau_b / Top-k**：本目录里每个分子只有一种态（DEC/EMC/PC/TEGDME 只有阴离子，DMC/EC/TMP 只有阳离子），
  氧化轴 n = 3、还原轴 n = 4。三个分子的秩相关不是推断，报告它只会诱导误读；
  这不是偷懒，而是延续 Week 11 起的一贯纪律（`rank_metrics` 列逐行写明省略原因）。
- **不可读成「P2 腿错了 1.9 eV」**：本目录的格子是**裸 CPCM、逐格自己的 eps**，
  而五级台阶的 P2 腿是 **SMD(乙腈)**；两者不是同一个环境模型，本节只给「垂直近似」的量级尺度。
- **不可把氧化轴的散布读成「碳酸酯之间的差异」**：氧化轴的 3 个分子跨了 2 个家族（碳酸酯 EC/DMC + 亚磷酸酯 TMP），
  相对散布里含有家族对比；同一家族的碳酸酯子集（DMC/EC）在 §4 里单列。
- **相对散布在 |mean| 接近 0 时会发散**：G1->G2 的氧化位移 |mean| ~ 0.01 eV，它的相对散布没有意义，本表照抄只为并置，不作比较。

## 7. 产物

- `outputs/week19/stage20_relax_rung.json`
- `outputs/week19/stage20_relax_rung_cells.csv`
- `outputs/week19/stage20_relax_rung_epsilon.csv`
- `outputs/week19/stage20_relax_rung_ladder.csv`

输入（SHA256 记录在 JSON 的 `inputs` 段）：

- `outputs/week18/stage19_relax_cells_analysis.csv`  `7e1333d553ebb72f`
- `outputs/week18/stage19_relax_plan.json`  `8729b7758a436235`
- `outputs/week9/stage10_ladder.csv`  `c4cdec417373fcd6`

