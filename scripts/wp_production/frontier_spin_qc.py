"""Per-spin frontier populations + the three QC statuses (plan v3.1 items 1-2).

Four defects the plan names, all measured live:

1. **Cross-spin mixing**: unrestricted runs print TWO FMO blocks (OP=0 alpha,
   OP=1 beta).  ``frontier_populations`` read only OP=0, so 42 non-singlet
   members' energies could come from one spin channel while the populations
   came from another -- the plan: "能量与分类可能不是同一轨道".
2. **computed despite no FMO**: the molden parse sets status=computed and the
   FMO failure is swallowed (``except: pass``), so a member with NO formal
   population still reads "computed" -- "解析完成冒充正式身份证据完整".
3. **Mixed calibers in one table**: the report showed the AO weights but the
   FMO classes, "同一表内混用两种量".
4. **Over-claim**: the report said the LUMO composition proves the reduction
   channel -- the plan: "静态 LUMO 组成不能直接证明实际还原通道".

New API (per plan draft A): ``formal_frontiers`` returns ONE record per spin
channel with operator/spin/orbital_index and the Li/donor weights, plus the
atom-composition cross-check against the member's own geometry and the
non-physical-population rejection.  ``frontier_populations`` stays for
back-compat but now demands ALL channels of the declared wavefunction.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from frontier_fmopop import parse_fmopop, _RE_OPERATOR, _RE_ATOM

#: donor set shared with the localization module -- single source
DONOR_ELEMENTS = {"N", "O", "F", "P", "S", "Cl"}

#: printed populations carry six decimals; the tolerance matches that format
#: (the plan: "仅适用已确认的六位小数格式；须登记解析契约")
PRINT_TOL = 0.5e-6


def _classify(li_w: float, donor_w: float) -> str:
    if li_w >= 0.25:
        return "li_localized"
    if donor_w >= 0.50:
        return "donor_localized"
    if li_w + donor_w < 0.50:
        return "ligand_localized"
    return "delocalized"


def formal_frontiers(log_text: str, symbols: list[str], *, wavefunction: str) -> list[dict]:
    """Per-spin-channel frontier records; raises on any integrity violation.

    ``wavefunction`` must come from the run's own input/log ("R" or "U"), never
    guessed from the multiplicity alone.  RO/unknown needs its own contract and
    is refused here rather than silently mislabelled.
    """
    required = {"R": {0}, "U": {0, 1}}.get(wavefunction)
    if required is None:
        raise ValueError("RO/未知波函数需要独立解析契约")

    if "ORCA TERMINATED NORMALLY" not in log_text:
        raise ValueError("日志尚未正常结束")

    ops = parse_fmopop(log_text)
    if set(ops) != required:
        raise ValueError("缺失或多余自旋通道: have %s, require %s"
                         % (sorted(ops), sorted(required)))
    if len(_RE_OPERATOR.findall(log_text)) != len(ops):
        raise ValueError("重复FMO块：需先界定同一最终运行")

    result = []
    for op, block in sorted(ops.items()):
        atoms = block["atoms"]

        if [a[0] for a in atoms] != list(range(len(symbols))):
            raise ValueError("原子编号缺失或重复")
        if [a[1] for a in atoms] != list(symbols):
            raise ValueError("原子组成/顺序与成员几何不一致")
        if not all(math.isfinite(v) for a in atoms for v in a[2:]):
            raise ValueError("非有限布居")

        # Löwdin columns must be physical per-atom (the plan: 禁止截断掩盖)
        if any(not -PRINT_TOL <= a[c] <= 1 + PRINT_TOL
               for a in atoms for c in (3, 5)):
            raise ValueError("非物理Löwdin权重；禁止截断掩盖")

        for frontier, column in (("homo", 3), ("lumo", 5)):
            li = sum(a[column] for a in atoms if a[1] == "Li")
            donor = sum(a[column] for a in atoms
                        if a[1] in DONOR_ELEMENTS)

            eps = len(atoms) * PRINT_TOL
            if not (-eps <= li <= 1 + eps
                    and -eps <= donor <= 1 + eps
                    and li + donor <= 1 + eps):
                raise ValueError("非物理分区权重 (li=%.6f donor=%.6f)" % (li, donor))

            result.append({
                "operator": op,
                "spin": ("restricted" if wavefunction == "R"
                         else ("alpha" if op == 0 else "beta")),
                "orbital_index": block[frontier],
                "frontier": frontier,
                "population_scheme": "ORCA_FMOPop_Loewdin",
                "li_weight": li,
                "donor_weight": donor,
                "frontier_class": _classify(li, donor),
                "fmopop_status": "parsed",
                "identity_qc_status": "pending",
            })
    return result
