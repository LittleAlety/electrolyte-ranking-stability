# F57 manifest — R15 指标稳健性与排序可识别性

- script：`scripts/audit_metric_robustness.py`
- figure：`outputs/figures/F57_metric_robustness.png`（1260 × 1400 px @ 200 dpi）
- stats：`outputs/week27/metric_robustness.json`、`outputs/week27/metric_robustness.md`
- 新电子结构计算：**0**（全部数值为冻结产物读回）

## 图注

(a) 每个 block 的排序一致性政策带（pessimistic → optimistic），蓝点为 tie 政策；
(b) f_tie = 证据无法解析的 pair 占比（= 政策带宽度的一半）；
(c) 可分层层数：cheap 自排序 / target 自排序 / 双方认证，竖线为分子数 n；
(d) 近临界 pair 数（比值 ∈ [1, 1.25)），认证了但极易翻转。

## 复现命令

```powershell
.venv\Scripts\python.exe scripts\audit_metric_robustness.py --check
.venv\Scripts\python.exe scripts\audit_metric_robustness.py
```

## 输入 sha256

| 路径 | sha256 |
| --- | --- |
| `outputs/week4/p1_decision_stability.json` | `9fa78cd9f5d81485235981ec750ade9c25cb7eec305f154df43294f73d08b085` |
| `outputs/week4/p2_decision_stability.json` | `38eb6af12228a52016a6e20af6768336d1fa6693cff9422a56cebe83f9df2108` |
| `outputs/week5/c1_decision_stability.json` | `da9df806884640d4ac23a9b074b858d306bfeee216ff516c0d526571b56993cb` |

## 输出 sha256

| 路径 | sha256 |
| --- | --- |
| `outputs/week27/metric_robustness.json` | `488848aedce875398d315198fb1a350408c2cf77d191e190e051b2ae9ec83f81` |
| `outputs/week27/metric_robustness.md` | `35ad11f4552ae2e4258bd7d7557f47499e600e2b2d6e8eff20571dfbd5acbc72` |
| `outputs/week27/F57_manifest.md` | `08eb98883ee386e43b72d2267b7f86d89bb898f9d8c4dc7e1c7fcc654de125fb` |
| `outputs/figures/F57_metric_robustness.png` | `d2dcc79f9813eca908fcd73f9d0c9aa849e75bde7c41e8a0c541bcdde1efa7ed` |

## 纪律声明

- 本图不跑任何新电子结构；所有数字均为已冻结产物的现算读出。
- `tau_b` 是全排序点统计量；「排序不稳」的判据是政策带，不是单个数字。
- 本图不改变任何既有判决；不读取仓库外文件。
- 字体：Microsoft YaHei / SimHei，axes.unicode_minus = False。
