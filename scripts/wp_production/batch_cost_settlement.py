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

Read-only: parsing and arithmetic only.
"""

from __future__ import annotations

from decimal import Decimal


def parse_sacct_rows(text: str) -> list[dict]:
    """Parse ``sacct -P -n`` output with a header line (field names first)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("|")
    rows = []
    for ln in lines[1:]:
        parts = ln.split("|")
        rows.append(dict(zip(header, parts)))
    return rows


def allocated_core_hours(rows, expected_job_ids) -> Decimal:
    """Allocated core-hours for EXACTLY the expected raw array-element ids.

    Raises ValueError on a missing element (settlement refused, never
    zero-filled) or on duplicate records for the same element (reconcile the
    restart/re-submission first).  Parent ``.batch``/``.extern`` rows and any
    id outside ``expected_job_ids`` are ignored -- they would double-bill.
    """
    expected = set(expected_job_ids)
    selected: dict[str, dict] = {}
    for row in rows:
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
        cores = int(row["AllocCPUS"])
        seconds = int(row["ElapsedRaw"])
        if cores <= 0 or seconds < 0:
            raise ValueError("非法费用字段: %s" % job_id)
        total += Decimal(cores) * Decimal(seconds) / Decimal(3600)
    return total


def parse_elapsed_raw(value: str) -> int:
    """sacct ElapsedRaw is plain seconds; the pretty form is [[DD-]HH:]MM:SS."""
    value = value.strip()
    if value.startswith("-") or not value:
        raise ValueError("非法 ElapsedRaw: %r" % value)
    if "-" in value:                     # DD-HH:MM:SS form
        days, rest = value.split("-", 1)
        h, m, s = rest.split(":")
        return int(days) * 86400 + int(h) * 3600 + int(m) * 60 + int(s)
    parts = value.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0])