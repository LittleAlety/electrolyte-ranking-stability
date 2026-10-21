"""Parse ORCA 6.1 ``! FMOPop`` output into per-atom frontier populations.

The frontier legs now carry ``FMOPop`` so the electronic-identity numbers are
ORCA's own Mulliken AND Loewdin populations -- both of which account for the
basis-function overlap, which the raw ``|AO coefficient|^2`` shortcut does not.
The Molden route stays as a cross-check, so both calibers coexist in one table.

Format (measured, ORCA 6.1.1, unrestricted calculations print one block per
spin operator)::

    FRONTIER MOLECULAR ORBITAL POPULATION ANALYSIS
    ----------------------------------------------
    OPERATOR OP = 0: HOMO=  11 LUMO=  12
    ------------------------------------------------------------------------
       Atom        Q(Mulliken)     Q(Loewdin)     Q(Mulliken)     Q(Loewdin)
                 <<<<<<<<<<<<HOMO>>>>>>>>>>>>   <<<<<<<<<<<<LUMO>>>>>>>>>>>>
    ------------------------------------------------------------------------
       0-C         0.207071        0.189913       0.075188        0.158750
       ...
       6-Li        0.000175        0.001727       0.024072        0.023715
    ------------------------------------------------------------------------

Everything here is fail-closed: a log whose block is truncated, unparsable or
whose populations do not sum to ~1 per column raises ``ValueError`` rather than
silently producing a partial weight table.
"""
from __future__ import annotations

import re
from pathlib import Path

# unrestricted prints "OPERATOR OP = 0: HOMO= 11 LUMO=  12"; restricted/closed
# shell prints "ANALYZING ORBITALS: HOMO=  11 LUMO=  12" -- both must parse
_RE_OPERATOR = re.compile(r"(?:OPERATOR OP =\s*(\d+)|ANALYZING ORBITALS):\s*"
                         r"HOMO=\s*(\d+)\s+LUMO=\s*(\d+)")
# Mulliken columns can be NEGATIVE (overlap pathology) -- accept the sign
_RE_ATOM = re.compile(r"^\s*(\d+)-([A-Za-z]+)\s+"
                     r"(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s*$")

TOLERANCE = 5e-2          # per-column sum: closed shells sum to 1 per operator


def parse_fmopop(text: str) -> dict[int, dict]:
    """{op: {"homo": int, "lumo": int, "atoms": [(idx, symbol, m_h, l_h, m_l, l_l)]}}."""
    ops: dict[int, dict] = {}
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        m = _RE_OPERATOR.search(lines[i])
        if not m:
            i += 1
            continue
        op = int(m.group(1)) if m.group(1) is not None else 0
        homo, lumo = int(m.group(2)), int(m.group(3))
        atoms: list[tuple] = []
        j = i + 1
        while j < n:
            am = _RE_ATOM.match(lines[j])
            if am:
                atoms.append((int(am.group(1)), am.group(2),
                              float(am.group(3)), float(am.group(4)),
                              float(am.group(5)), float(am.group(6))))
                j += 1
                continue
            if atoms:
                # the block ends at the FIRST non-atom line after data rows:
                # unrestricted blocks close with a "-----" rule, but closed-shell
                # blocks just stop (the next line is blank or the MAYER banner),
                # so requiring a closing rule would reject every closed shell
                break
            if lines[j].strip().startswith("---"):
                j += 1                    # header rules before the first row
                continue
            j += 1
        if not atoms:
            raise ValueError("FMOPop block %d has no atom rows" % op)
        # Only the LÖWDIN columns are validated.  Mulliken populations are
        # famous for going non-physical when the basis overlap is large
        # (measured in this very project: a block whose Mulliken LUMO column
        # holds -1.848 and 1.394 while its Löwdin column is well-behaved).
        # They are reported verbatim but NEVER used for classification.
        for col in (3, 5):
            total = sum(a[col] for a in atoms)
            if not (1.0 - TOLERANCE <= total <= 1.0 + TOLERANCE):
                raise ValueError(
                    "FMOPop block %d Loewdin column %d sums to %.4f (expected ~1)"
                    % (op, col, total))
        ops[op] = {"homo": homo, "lumo": lumo, "atoms": atoms}
        i = j
    if not ops:
        raise ValueError("no FMOPop operator block found")
    return ops


def frontier_populations(text: str, *, op: int = 0) -> dict[str, dict[str, float]]:
    """Li/donor weights per frontier, from the FMOPop block of one operator.

    Returns {"homo": {"li": .., "donor": .., "mulliken_li": .., ...},
             "lumo": {...}} -- both calibers kept, so the table can show them
    side by side.  ``donor`` uses the same DONOR_ELEMENTS set as the Molden
    route so the two calibers classify identically.
    """
    ops = parse_fmopop(text)
    if op not in ops:
        # unrestricted prints OP=0 (alpha) and OP=1 (beta); restricted prints
        # only OP=0.  Missing op means the log is not what the caller thinks.
        raise ValueError("operator %d missing (have %s)" % (op, sorted(ops)))
    atoms = ops[op]["atoms"]

    def _sum(pred, mcol, lcol):
        m = sum(r[mcol] for r in atoms if pred(r[1]))
        l = sum(r[lcol] for r in atoms if pred(r[1]))
        return m, l

    li_m_h, li_l_h = _sum(lambda s: s == "Li", 2, 3)
    li_m_l, li_l_l = _sum(lambda s: s == "Li", 4, 5)
    don_m_h, don_l_h = _sum(_is_donor, 2, 3)
    don_m_l, don_l_l = _sum(_is_donor, 4, 5)

    return {
        "homo": {"mulliken_li": li_m_h, "loewdin_li": li_l_h,
                 "mulliken_donor": don_m_h, "loewdin_donor": don_l_h},
        "lumo": {"mulliken_li": li_m_l, "loewdin_li": li_l_l,
                 "mulliken_donor": don_m_l, "loewdin_donor": don_l_l},
    }


def _is_donor(symbol: str) -> bool:
    # kept in sync with build_frontier_localization.DONOR_ELEMENTS
    return symbol in {"N", "O", "F", "P", "S", "Cl"}
