#!/usr/bin/env python
"""Batch cost settlement from sacct EVIDENCE, not from estimates (2026-10-27 ruling).

The ruling adds to ``collect_sacct`` the two fields that independently compute
core-hours -- ``AllocCPUS`` and ``ElapsedRaw`` -- and pins the accounting rules:

  * match by EXACT raw array-element id (``<array>_<index>``); the parent
    array row and the ``.batch``/``.extern`` children are NOT added (they
    double-bill the same allocation);
  * a MISSING record for an expected element refuses the settlement
    (``MISSING``, reservation kept, never zero-filled);
  * a DUPLICATE record for the same element refuses simple addition and
    demands reconciliation;
  * the result is ALLOCATED core-hours (AllocCPUS x wallclock), not TotalCPU.

2026-10-27 audit fixes (gate-code-auditor REPORT.md, adopted):
  F-6  missing/invalid COLUMNS and malformed values raise the project's own
       ``ValueError`` (``MISSING_COLUMNS``/``非法费用字段``) instead of a bare
       ``KeyError``/native int() crash -- upstream ``except ValueError`` keeps
       working as the docstring promises;
  F-7  ``AllocCPUS=0`` with ``Elapsed=0`` is a LEGAL 0-CH terminal record (the
       project settled 3747724 exactly that way) -- only a negative or
       inconsistent allocation is refused;
  F-8  the billing path reuses ``parse_elapsed_raw`` for pretty ``Elapsed``
       forms when ``ElapsedRaw`` is absent, and rejects negative components.

Read-only: parsing and arithmetic only.
"""

from __future__ import annotations

from decimal import Decimal

_REQUIRED_COLUMNS = ("JobIDRaw", "AllocCPUS")


def parse_sacct_rows(text: str) -> list[dict]:
    """Parse ``sacct -P`` output WITH a header line (field names first).

    The header is REQUIRED (audit F-10): the existing ``-n`` capture format has
    no header, and feeding it here would turn the first data row into field
    names.  Callers must capture with ``-P`` (no ``-n``) or supply a header.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("|")
    rows = []
    for ln in lines[1:]:
        parts = ln.split("|")
        rows.append(dict(zip(header, parts)))
    return rows


def _elapsed_seconds(row: dict, job_id: str) -> int:
    """ElapsedRaw (plain seconds) or the pretty Elapsed form -- never both."""
    raw = str(row.get("ElapsedRaw", "")).strip()
    if raw:
        try:
            return parse_elapsed_raw(raw)
        except ValueError:
            raise ValueError("非法费用字段: %s (ElapsedRaw=%r)" % (job_id, raw))
    pretty = str(row.get("Elapsed", "")).strip()
    if pretty:
        try:
            return parse_elapsed_raw(pretty)
        except ValueError:
            raise ValueError("非法费用字段: %s (Elapsed=%r)" % (job_id, pretty))
    raise ValueError("非法费用字段: %s (无 ElapsedRaw/Elapsed)" % job_id)


def allocated_core_hours(rows, expected_job_ids) -> Decimal:
    """Allocated core-hours for EXACTLY the expected raw array-element ids.

    Raises ValueError on a missing element (settlement refused, never
    zero-filled) or on duplicate records for the same element (reconcile the
    restart/re-submission first).  Parent ``.batch``/``.extern`` rows and any
    id outside ``expected_job_ids`` are ignored -- they would double-bill.

    ``AllocCPUS=0`` with zero elapsed is a legal 0-CH record (a cancelled
    before-start element, settled that way historically); only negative or
    inconsistent allocations are refused.
    """
    expected = set(expected_job_ids)
    selected: dict[str, dict] = {}
    for row in rows:
        missing_cols = [c for c in _REQUIRED_COLUMNS if c not in row]
        if missing_cols:
            raise ValueError("MISSING_COLUMNS: %s (需 %s，实际列 %s)"
                             % (row.get("JobIDRaw", "?"), _REQUIRED_COLUMNS,
                                sorted(row)))
        job_id = str(row["JobIDRaw"])
        if job_id not in expected:
            continue
        if job_id in selected:
            raise ValueError("重复调度记录，需核对重启/重复作业: %s" % job_id)
        selected[job_id] = row
    if set(selected) != expected:
        missing = expected - set(selected)
        raise ValueError("MISSING: 调度费用记录不完整，不得释放全部预留 (缺 %s)"
                         % sorted(missing))
    total = Decimal("0")
    for job_id, row in selected.items():
        cores_s = str(row["AllocCPUS"]).strip()
        try:
            cores = int(Decimal(cores_s))
        except Exception:
            raise ValueError("非法费用字段: %s (AllocCPUS=%r)" % (job_id, cores_s))
        seconds = _elapsed_seconds(row, job_id)
        if cores < 0 or seconds < 0:
            raise ValueError("非法费用字段: %s (cores=%d, seconds=%d)"
                             % (job_id, cores, seconds))
        total += Decimal(cores) * Decimal(seconds) / Decimal(3600)
    return total


def parse_elapsed_raw(value: str) -> int:
    """sacct ElapsedRaw is plain seconds; the pretty form is [[DD-]HH:]MM:SS."""
    value = value.strip()
    if value.startswith("-") or not value:
        raise ValueError("非法 ElapsedRaw: %r" % value)
    if "-" in value:                     # DD-HH:MM:SS form
        days, rest = value.split("-", 1)
        if not days.isdigit() or int(days) < 0:
            raise ValueError("非法 ElapsedRaw: %r" % value)
        h, m, s = rest.split(":")
        if min(int(h), int(m), int(s)) < 0:
            raise ValueError("非法 ElapsedRaw: %r" % value)
        return int(days) * 86400 + int(h) * 3600 + int(m) * 60 + int(s)
    parts = value.split(":")
    if any(int(p) < 0 for p in parts):
        raise ValueError("非法 ElapsedRaw: %r" % value)
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0])