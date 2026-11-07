# Stage 24 / R5 -- [Li(EC)n]+ 的 n = 3 符号检验（GFN2-xTB 级）

> 由 `scripts/run_shell3_xtb_sign_test.py` 生成。**层级是 GFN2-xTB，不是 r2SCAN-3c**：
> 本节的数值**不得**与 `docs/18` 的 r2SCAN-3c 阶梯并列，也不进入任何冻结量。
> 它只回答一个问题：第三个配体的增量是否**继续同号、继续变小**。

## 0. 一句话结论

EC 的第三个配体在 xTB 级**继续同号且增量继续变小**，与「次线性、与饱和一致」的形状相容 —— 但这是**两点之外的一个点**，不是饱和的证明。判定：**consistent_with_saturation**。

## 1. 阶梯（同一层级内部可比）

| n | 参考态 | 电荷/多重度 | IP (eV) | EA (eV) | dIP = IP(n) - IP(0) | dEA = EA(n) - EA(0) | 几何来源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | free EC | 0 / 1 | 15.590 | 1.747 | 0.000 | 0.000 | EC fragment of structures/li_motifs/EC_m1.xyz, relaxed free here (GFN2-xTB opt) |
| 1 | [Li(EC)]+ | 1 / 1 | 19.487 | 8.039 | 3.897 | 6.291 | reused unchanged: structures/li_motifs/EC_m1.xyz |
| 2 | [Li(EC)2]+ | 1 / 1 | 17.605 | 7.420 | 2.015 | 5.672 | reused unchanged: structures/microsolvation/EC_m1_shell2.xyz |
| 3 | [Li(EC)3]+ | 1 / 1 | 16.882 | 7.084 | 1.292 | 5.336 | built with Stage 9's placement rule, relaxed here (GFN2-xTB opt): structures/microsolvation/EC_m1_shell3.xyz |

## 2. 增量与判据

| 量 | 氧化轴 | 还原轴 |
| --- | --- | --- |
| dd(1->0) = d(1) - d(0) | 3.897 | 6.291 |
| dd(2->1) = d(2) - d(1) | -1.882 | -0.619 |
| dd(3->2) = d(3) - d(2) | -0.723 | -0.336 |
| sign(dd(3->2)) == sign(dd(2->1)) | True | True |
| abs(dd(3->2)) < abs(dd(2->1)) | True | True |
| 比值 abs(dd(3->2))/abs(dd(2->1)) | 0.384 | 0.543 |

**判定**：`consistent_with_saturation`

- 两个轴的 dd(3->2) 都与 dd(2->1) 同号，且绝对值更小 —— 第三个点与「次线性、与饱和一致」的形状相容。这只支持措辞「与饱和一致」，**不支持**「证明了饱和」：三个点仍然定不出渐近线。

## 3. 与 `docs/18` 的关系（层级纪律）

| 项 | `docs/18`（Stage 9） | 本节（R5 n=3） |
| --- | --- | --- |
| 方法 | ORCA r2SCAN-3c | **GFN2-xTB** |
| 分子 | 12 个 motif（8 个家族） | **1 个**（EC / m1） |
| 壳层 | 1:1、1:2 | 1:1、1:2、**1:3** |
| 用途 | 冻结的台阶结论 | **只做符号/形状示意**，不冻结、不并列 |

### 3.1 跨层级的**无量纲**对照（只比比值，不比数值）

允许跨层级的只有**无量纲的形状比** `dd(2->1)/dd(1->0)`：

| 轴 | r2SCAN-3c（`outputs/week8/stage9_shell_shifts.csv`）| GFN2-xTB（本节）|
| --- | --- | --- |
| 氧化 | -0.4080 | -0.4829 |
| 还原 | -0.2386 | -0.0984 |

读法必须按轴分开：氧化轴的形状比在两层之间**接近**（-0.408 vs -0.483），
还原轴**不接近**（-0.239 vs -0.098）—— 也就是说「第二个配体回收多少」这条形状结论
在氧化侧跨层级可搬运，在还原侧**不能**：还原轴在 Stage 9 就已经被 state-identity 问题标记过（C₁ 还原态在 11/12 个体系里电子落在 Li 上），xTB 与 r2SCAN-3c 对「电子落在哪」的判断不必一致。这一条只能作为**提示**，不是结论。

绝对值的对照在此**一律不做**：GFN2-xTB 的 IP/EA 与 r2SCAN-3c 相差 eV 量级。

两张表**唯一的共同结论**是一条命题：增量同号且绝对值递减。
`docs/18` 用 12 个分子、2 个点得到它；本节用 1 个分子、3 个点复核它。
任何把它们放在同一张数值表里的写法都是错的。

## 4. 限制

1. **层级不同**：GFN2-xTB 的绝对 IP/EA 与 r2SCAN-3c 相差 eV 量级，本节的绝对值没有意义。
2. **分子只有一个**（EC）。第三个点在一元数据上成立，不构成对 12 个 motif 的普查。
3. **几何约定**：n = 1 与 n = 2 复用项目既有的 GFN2-xTB 优化结构（原样不动），
   n = 0（自由 EC）与 n = 3（第三配体）在本脚本内做 GFN2-xTB 优化。四个跂都是 xTB 优化点，
   但不是同一次运行的产物，几何噪声没有被单独分离。
4. **第三配体的放置**沿用 Stage 9 的**同一条确定性规则**（donor x fibonacci 方向 x roll，
   按最近交叉接触打分，最优的 4 个各做一次 GFN2-xTB 单点，胜者预优化）。
   它给出的是该规则下的最低能放置，不是全局最优壳层。
5. 本脚本不写入任何冻结量，不修改 `docs/18` 的任何数字。

## 5. 产物

| 文件 | 说明 |
| --- | --- |
| `structures/microsolvation/EC_m1_shell3.xyz` | 新的 n = 3 壳层结构（可复用） |
| `outputs/week23/shell3_xtb_sign_test.json` | 完整记录（含全部候选放置） |
| `outputs/week23/shell3_xtb_sign_test.csv` | 阶梯表 |
| `outputs/_week23_scratch/shell3/` | 原始 xTB 文本 |

---

生成时间（UTC）：2026-10-02T03:15:54.237643+00:00

xTB 版本：6.7.1pre
