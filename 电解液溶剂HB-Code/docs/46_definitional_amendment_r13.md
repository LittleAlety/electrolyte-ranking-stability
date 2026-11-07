# R13 —— 定义修订（external review 响应）

- 日期：2026-10-08
- 类型：定义修正（append-only amendment，登记于 `config/prereg.yaml` 的 `amendment_log`）
- 冻结件：`config/scientific_definitions.yaml`（schema 1.0 → 2.0）、`config/prereg.yaml`
- Gate 0：修订登记并**重冻结**后仍 **CLOSED**（`scripts/freeze_gates.py` `evaluate_stage0`：所有 amendment `refrozen: true` 即闭合）

本文件回答一个具体问题：**按外部评审的意见，这个仓库到底该改哪些东西、按什么优先级改、哪些不改。**
评审的核心判断是：仓库已经是「相当完整的 decision-stability prototype」，下一阶段不该继续堆 Week 26/27/28，
而应补齐几个**物理定义缺口**、收缩叙事、提高可发表性。

---

## 0. 结论：优先级与落地状态

| 优先级 | 项目 | 评审判断 | R13 落地 | 位置 |
| --- | --- | --- | --- | --- |
| 🔴 P0 | P1 vertical vs adiabatic | 名称一致、物理量不一致 | 拆成 **P1v** + **P1a**，并实跑 12 分子绝热阶梯 | `scientific_definitions.yaml`、`outputs/phase2_p1a/`、`docs/p1v_vs_p1a.md` |
| 🔴 P0 | C1 reduction state identity | 11/12 电子落在 Li 上 | 还原轴分层：仅 `molecule_centered_redox` 进主 ranking | `outputs/state_identity/`、`docs/state_identity_protocol.md` |
| 🔴 P0 | Gate 1 / validated target | 未闭合却被称为 validated | 更名 **designated computational target/reference** | `target_naming`、`docs/gate1_negative_result.md` |
| 🟠 P1 | `f_robust_inv = 0` 的叙事 | 会被读成「稳定」 | 三元化 **STABLE / UNRESOLVED / ROBUST_INVERSION** | `decision_state`、`outputs/decision_state/` |
| 🟠 P1 | C2 命名 | 易被读成 second shell | 更名 **first-shell microsolvation (CN=2)** | `axis_B_environment_states.C2` |
| 🟠 P1 | P2 的 SMD vs dielectric | 两种物理实验要分开 | 拆成 **P2a**（SMD 乙腈）与 **P2eps**（bare CPCM ε） | `axis_A_proxy_hierarchy` |
| 🟠 P1 | GFN2 → r2SCAN-3c 角色 | 不要暗示 truth | `cheap → intermediate → external reference` | README / `framing` |
| 🟠 P1 | z = 1.0 单一判据 | 应给 resolution curve | 报 **f_unresolved(z)**：1.0 / 1.645 / 1.96 / 2.576 | `decision_state.resolution_curve` |
| 🟡 P2 | core 18 / broad 40 | 不用急扩 | 保持，限定泛化声明 | 不变 |
| 🟡 P2 | ML / AL | 不扩张 | 保持当 decision-budget demonstration | 不变 |
| 🟢 | provenance / reproducibility | 不要大改 | 未动 | 不变 |
| 🟢 | σ / displacement 理论 | 不要削弱，应升为主线 | 未削弱；作为核心叙事 | 不变 |

---

## 1. 🔴 P1v 与 P1a：把 vertical 与 adiabatic 正式拆开

### 问题

仓库早期把 Week-4 的「r2SCAN-3c 三态垂直 IP/EA」标为 `P1 = gas-phase molecular redox thermodynamics`。
但 v2 的 P1 定义为 **adiabatic** 自由能差

```
ΔG_ox^gas = G(M+) - G(M)      # 每个电荷态在各自弛豫几何上
```

而仓库实际做的是**同一几何（G1）上的三态单点**：

```
P1^repo = E(M+; G1) - E(M; G1)   →  vertical
```

两者不是同一个物理量（`P1^repo ≠ P1^v2`）。

### 修正

- 现有层正式更名为 **P1v**（gas-phase vertical redox-energy proxy），公式 `IP_v = E(M+; G1) - E(M; G1)`。
- 新增 **P1a**（gas-phase adiabatic redox thermodynamics），公式 `IP_a = E(M+; relaxed) - E(M; relaxed)`，
  每个电荷态各自 r2SCAN-3c Opt 到自身极小。
- 失败规则沿用 v2：气相阴离子不束缚时标 `unbound_anion`，**不**给伪精确的绝热电子亲和能。

### 实现

- runner：`scripts/run_p1a_adiabatic.py`（12 分子 T2 子集；中性弛豫几何直接复用 Week-4 的 G2）。
- 产物：`outputs/phase2_p1a/p1a_adiabatic.csv` / `.json`、`outputs/phase2_p1a/geometry_relaxation/`。
- 对照：`scripts/compare_vertical_adiabatic.py` → `outputs/phase2_p1a/p1v_vs_p1a.json`、`docs/p1v_vs_p1a.md`。
- 关键物理结论（见 `docs/p1v_vs_p1a.md`）：**氧化轴可比较；还原轴因气相阴离子不束缚而按规则排除**——
  这本身就是「为什么需要 P1a 这一层」的直接证据，而不是 runner 的缺陷。

---

## 2. 🔴 C1 还原态的 state-identity 分层

### 问题

Week-5 报出 C0 → C1 还原轴 `τ_b = -0.467`、`f_robust_inv = 0`，容易被读成
「Li⁺ 配位让还原排序翻转」。但同一周的 state-identity QC 显示：**12 个还原态里 11 个外加电子落在 Li 上**
（`Li_centered_or_mixed_redox`）。当电子离开分子时，数值排序的变化**不是**同一 observable 的排序不稳定，
而是 **observable identity failure**。

### 修正

主还原 ranking **只接受 `molecule_centered_redox`**；其余标签作为 mechanistic outcome 单独统计。

### 结果（`outputs/state_identity/state_identity_summary.md`）

- 全部主 motif 还原态：n = 10，τ_b = **-0.467**，f_robust_inv = 0。
- 只用分子中心还原态：n = **1**（仅 SN）→ **排序无定义**（配不成 pair）。
- 冻结还原对的三态重标注：STABLE 4/45、**UNRESOLVED 41/45**、ROBUST_INVERSION 0/45。

>> 结论：还原轴那个「表面翻转」由 UNRESOLVED 主导，且叠加身份分层后几乎没有可排序的 pair。
>> Li⁺ 配位除了改变数值，还会改变**被还原对象的电子身份**。

---

## 3. 🔴 Gate 1 双轨定位：不修数据，改叙事

Gate 1 的排序一致性层（`scripts/check_series_rel_ordering.py`）**未通过**：Kendall τ_b = 0.4286 < 0.90、
n_pairs = 21、判 `ordering_disagrees`；绝对标定层按 limitation 处理。solution anchors 本身也只是 `est`
（transcription-only）。**这个结果不要想办法救。**

R13 把项目拆成两层：

- **Track A —— decision-stability study**：P0 → P1v → P1a → P2a/P2eps → C1 → C2，问「哪些缺失物理会改变 ranking」。
  这一层**独立成立**。
- **Track B —— experimental validity**：把计算排序对到外部溶液排序。当前 **Gate 1 = 未闭合**，记为 negative result。

因此 R13 起：**Gate 1 闭合前，一律不称 P1v/P1a/P2a/P2eps 为 validated target**，改称
**designated computational target / reference**（见 `target_naming`）。详见 `docs/gate1_negative_result.md`。

---

## 4. 🟠 f_robust_inv = 0 不等于稳定：三态判据

单个 `f_robust_inv = 0` 是一个**危险的数字**：它把「没有稳健翻转」和「根本解析不了」压成一个值。
R13 增加 pairwise 三态判据（`decision_state`）：

```
STABLE           两个模型都 resolve 且方向一致
UNRESOLVED       至少一个模型没 resolve
ROBUST_INVERSION 两个模型都 resolve 且方向相反
```

并在 `outputs/decision_state/decision_state_summary.md` 报出每个台阶的三态计数 + 分辨率曲线
`f_unresolved(z)`（z = 1.0 / 1.645 / 1.96 / 2.576）。这样「1σ 还是 2σ」不再需要争，读者直接看到
「在不同证据门槛下，多少 pair 能被真正解析」。

---

## 5. 🟠 C2 命名 与 P2 分层

- **C2**：`[Li(M)2]+` 是 Li⁺ 周围两个配体的**第一配位壳**（coordination number 2），**不是** second solvation
  shell。字段 `axis_B_environment_states.C2.label` 已改为 `first-shell microsolvation (coordination number 2)`。
- **P2**：固定溶剂层（SMD 乙腈）= **P2a**；纯介电扫描（bare CPCM ε）= **P2eps**。两者是两种不同的物理实验：
  `P2a = electrostatic + cavity + dispersion + solvent-specific terms`，`P2eps` 只含 electrostatic screening。
  报告不得把二者混成同一条溶剂阶梯（`continuum_sensitivity.separation_rule` 早已冻结这条）。

---

## 6. 不改的东西（刻意保留）

- **provenance / reproducibility**：冻结 config、prereg、SHA256 清单、确定性重建、raw outputs、QC、tests —— 这是仓库最强的一部分。
- **σ / displacement 理论**：`P_B(i) = P_A(i) + δ_i`，排序改变由**candidate-specific differential displacement**
  而非 common-mode shift 控制（`ρ(std, τ_b) ≈ -0.851`）。这不是辅助分析，而是论文主线。
- **core 18 / broad 40**：作为 mechanistic proof-of-concept 合理；**泛化声明必须降级**，不要用 18 个分子证明
  「方法可泛化到电解液化学空间」，也不要用 40 池证明「active learning 普适只需 8–9 个昂贵标签」。
  扩展顺序（若要做）应是 `18 → 30–40 → 60–100`，而不是 `18 → 300`。
- **ML / AL**：不继续堆模型；`decision-learning behavior` 比 `R²` 更值得报告。

---

## 7. 触发本次修订的证据链（全部可追溯）

| 事实 | 来源 |
| --- | --- |
| P1 实为垂直量 | `outputs/week4/p1_core_set.csv`（三态单点，共用 G1） |
| 气相阴离子全部不束缚 | `outputs/week4/p1_core_set_audit.json`（`unbound_anion = 18`） |
| 11/12 还原态电子落在 Li 上 | `outputs/week5/c1_state_identity.json` |
| 还原轴 f_robust_inv = 0 但 f_unresolved 高 | `outputs/week5/c1_decision_stability.json` |
| Gate 1 ordering_disagrees | `outputs/week25/series_rel_ordering_check.json` |
| σ–τ_b 相关 | `outputs/week22_hardening/stats_b1_b2.json` |

本文件与上述全部产物一致；`scripts/freeze_gates.py --stage 0` 在修订后重新 CLOSED。
