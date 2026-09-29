# P1 core set 独立复核报告（T1 / r2SCAN-3c 气相单点）

- 生成时间（UTC）：2026-09-29T03:04:29Z
- ORCA 产物目录：outputs\week4\orca
- 输出目录：outputs\week4

## 这是什么 / 为什么需要独立复核

本报告由 scripts/audit_p1_core_set.py 生成。该脚本不复用上游 scripts/run_core_set_p1.py 或 src/electrolyte_ranking/orca.py 的任何解析逻辑，而是直接从 ORCA 原始 .out 文本重新提取 FINAL SINGLE POINT ENERGY、SCF 收敛信息、<S**2> 期望值、终止标志与程序版本号，再与 JSON sidecar 逐行交叉核对。T1 记录会驱动后续的决策稳定性分析，上游解析若读错键、取错能量或漏判未收敛/异常终止，错误会被静默放大；独立复核把任何分歧变成显式的 QC flag。

## 汇总

- 记录数：54
- 分子数：18
- 三态齐全的分子数：18
- 无 flag 的记录数：36
- flag 计数：{"abnormal_termination": 0, "energy_mismatch": 0, "missing_output": 0, "scf_failed": 0, "spin_contamination_flag": 0, "unbound_anion": 18}

| 分子 | 三态齐全 | E(neutral)/Eh | E(cation)/Eh | E(anion)/Eh | S²(neutral) | S²(cation) | S²(anion) | flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN | 是 | -132.715575 | -132.269423 | -132.598111 | - | 0.7534 | 0.7519 | unbound_anion |
| DEC | 是 | -422.163434 | -421.796516 | -422.039623 | - | 0.7546 | 0.7546 | unbound_anion |
| DMC | 是 | -343.552370 | -343.163567 | -343.425047 | - | 0.7598 | 0.7555 | unbound_anion |
| DME | 是 | -308.777456 | -308.452003 | -308.640408 | - | 0.7538 | 0.7515 | unbound_anion |
| DMSO | 是 | -553.134579 | -552.810664 | -553.032442 | - | 0.7565 | 0.7552 | unbound_anion |
| DOL | 是 | -268.291327 | -267.949075 | -268.141130 | - | 0.7539 | 0.7512 | unbound_anion |
| EA | 是 | -307.642945 | -307.275347 | -307.542378 | - | 0.7559 | 0.7559 | unbound_anion |
| EC | 是 | -342.352336 | -341.956578 | -342.257146 | - | 0.7549 | 0.7513 | unbound_anion |
| EMC | 是 | -382.857926 | -382.483025 | -382.736030 | - | 0.7555 | 0.7531 | unbound_anion |
| FEC | 是 | -441.605140 | -441.189042 | -441.511196 | - | 0.7574 | 0.7543 | unbound_anion |
| GBL | 是 | -306.437999 | -306.072287 | -306.343214 | - | 0.7565 | 0.7553 | unbound_anion |
| MA | 是 | -268.337776 | -267.962858 | -268.237224 | - | 0.7561 | 0.7559 | unbound_anion |
| PC | 是 | -381.660924 | -381.273629 | -381.554875 | - | 0.7546 | 0.7517 | unbound_anion |
| SL | 是 | -705.751087 | -705.391199 | -705.641659 | - | 0.7554 | 0.7533 | unbound_anion |
| SN | 是 | -264.230490 | -263.804064 | -264.162345 | - | 0.7556 | 0.7526 | unbound_anion |
| TEGDME | 是 | -770.169436 | -769.890313 | -770.064021 | - | 0.7520 | 0.7508 | unbound_anion |
| TMP | 是 | -761.969291 | -761.599710 | -761.862235 | - | 0.7548 | 0.7513 | unbound_anion |
| VC | 是 | -341.129299 | -340.775814 | -341.056195 | - | 0.7587 | 0.7551 | unbound_anion |

## 不一致与异常

- AN_anion（state=anion）：unbound_anion [out=outputs\week4\orca\AN\AN_anion.out]
- DEC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\DEC\DEC_anion.out]
- DMC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\DMC\DMC_anion.out]
- DME_anion（state=anion）：unbound_anion [out=outputs\week4\orca\DME\DME_anion.out]
- DMSO_anion（state=anion）：unbound_anion [out=outputs\week4\orca\DMSO\DMSO_anion.out]
- DOL_anion（state=anion）：unbound_anion [out=outputs\week4\orca\DOL\DOL_anion.out]
- EA_anion（state=anion）：unbound_anion [out=outputs\week4\orca\EA\EA_anion.out]
- EC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\EC\EC_anion.out]
- EMC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\EMC\EMC_anion.out]
- FEC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\FEC\FEC_anion.out]
- GBL_anion（state=anion）：unbound_anion [out=outputs\week4\orca\GBL\GBL_anion.out]
- MA_anion（state=anion）：unbound_anion [out=outputs\week4\orca\MA\MA_anion.out]
- PC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\PC\PC_anion.out]
- SL_anion（state=anion）：unbound_anion [out=outputs\week4\orca\SL\SL_anion.out]
- SN_anion（state=anion）：unbound_anion [out=outputs\week4\orca\SN\SN_anion.out]
- TEGDME_anion（state=anion）：unbound_anion [out=outputs\week4\orca\TEGDME\TEGDME_anion.out]
- TMP_anion（state=anion）：unbound_anion [out=outputs\week4\orca\TMP\TMP_anion.out]
- VC_anion（state=anion）：unbound_anion [out=outputs\week4\orca\VC\VC_anion.out]

## 结论

- 上游 JSON 与原始 .out 能量：54 行全部一致（容差 1e-6 Eh）。
- 阴离子束缚性：发现 18 个阴离子未束缚（E(anion) > E(neutral)）：AN_anion, DEC_anion, DMC_anion, DME_anion, DMSO_anion, DOL_anion, EA_anion, EC_anion, EMC_anion, FEC_anion, GBL_anion, MA_anion, PC_anion, SL_anion, SN_anion, TEGDME_anion, TMP_anion, VC_anion。
- 双重态 <S**2>：36 行落在 0.75 ± 0.05 区间。
