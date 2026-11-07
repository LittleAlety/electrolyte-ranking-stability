# F58 manifest — R15 模型层独立性 / 信息增益审计

- script：`scripts/audit_layer_independence.py`
- figure：`outputs/figures/F58_layer_independence.png`（1263 × 1285 px @ 200 dpi）
- stats：`outputs/week27/layer_independence.json`、`outputs/week27/layer_independence.md`
- 新电子结构计算：**0**（全部数值为冻结产物读回）

## 图注

(a) 每级位移的 dispersion（氧化/还原），标注该层 ORCA job 数；
(b) 5 个 rung 两两之间位移向量的 max |Pearson|（同分子集上现算）；
(c) 每级的 Kendall tau_b（红虚线 = 0.90 排序门槛）与最大 f_unresolved；
(d) 结论卡片：层不是同一信号的再编码；阶梯是分解；T3 说常数位移免费。

数值：同轴 rung 对 20 对，|Pearson| 中位 0.383、最大 0.791；

## 复现命令

```powershell
.venv\Scripts\python.exe scripts\audit_layer_independence.py --check
.venv\Scripts\python.exe scripts\audit_layer_independence.py
```

## 输入 sha256

| 路径 | sha256 |
| --- | --- |
| `outputs/week4/p1_core_set_derived.csv` | `2987f8771b722d5a07517289a18a486fb2da24ed5775a196ffd7baf2c57517d3` |
| `outputs/week4/p2_environment_effects.csv` | `b74de81a66979f04c96b52c4280842ae8df8c8db2a9c50d6fb96675e0b752363` |
| `outputs/week5/c1_coord_shifts.csv` | `1f9597ba376ffb19610e855e4d83a4e2360a8ac5009209cf764be91008634b5d` |
| `outputs/week8/stage9_shell_shifts.csv` | `ce206cbd8c7ce81031b4f247c0c45d5ab24a0013ef49bfb35fae2da27c24e348` |
| `outputs/week4/t2_opt_freq_summary.json` | `eb383c6c1760cd04ae5d84807de660e518c032d16e65778051df88bca7f23b17` |
| `outputs/week9/stage10_ladder.json` | `3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf` |
| `outputs/week4/p1_core_set_summary.json` | `b941d7fb1124900c5e148c6108478c0f00395e9430ee59da291bca878db42809` |
| `outputs/week4/p2_summary_smd_acetonitrile.json` | `b39720c91180ce116eb3edb13d718f7a31f78ce3ca2a8ac8435db70746688cea` |
| `outputs/week4/t2_opt_freq_summary.json` | `eb383c6c1760cd04ae5d84807de660e518c032d16e65778051df88bca7f23b17` |
| `outputs/week5/c1_li_coordination_summary.json` | `772d35d250312382829a74fc6b07dd8fa980a88eaffb392fe750d5038f1a5022` |
| `outputs/week8/stage9_summary.json` | `fb445a5557de9f43396c4a0a66ecd56e43de76ac0981fe02104039e1e1590329` |

## 输出 sha256

| 路径 | sha256 |
| --- | --- |
| `outputs/week27/layer_independence.json` | `fe2be0e94ee0abf99e0621e21d21e72d7d640bba9ff4d5af54813cddc54e92e5` |
| `outputs/week27/layer_independence.md` | `b365e108e00a2ffc3689bed24519931a5ba9c410d8efdfbdc95906ba36c5b323` |
| `outputs/week27/F58_manifest.md` | `6021f53cbd378f0605a9ceeed035a82c7edfd3b079a243f786d106f2d321d2f1` |
| `outputs/figures/F58_layer_independence.png` | `4c255a190f7135aa3a5fa44ac30db56724a16767597325757b5d3c68441e8fce` |

## 纪律声明

- 本图不跑任何新电子结构；所有数字均为已冻结产物的现算读出。
- 跳板是逐级加 realism 的拆解，不是互相独立的证据；本图把这一点明写出来。
- 本图不改变任何既有判决；不读取仓库外文件。
- 字体：Microsoft YaHei / SimHei，axes.unicode_minus = False。
