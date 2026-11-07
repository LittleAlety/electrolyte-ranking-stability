"""Read ORCA's per-state energy ledger out of a single-point output file.

Why this module exists
----------------------
Every single point in this project is an ``r2SCAN-3c`` calculation, and ORCA
prints its final number as a *sum of named terms*:

    FINAL SINGLE POINT ENERGY  =  Total Energy  +  Dispersion correction  +  gCP correction

When a continuum solvent is switched on, ``Total Energy`` is itself already
split into an electronic part plus two solvation terms (see ORCA's
``TOTAL SCF ENERGY`` block):

    Total Energy  =  (electronic + nuclear)  +  CPCM Dielectric  +  SMD CDS (Gcds)

* a **gas-phase** run prints neither solvation term;
* a **bare CPCM** run prints only ``CPCM Dielectric`` (the electrostatic part);
* an **SMD** run prints both, and ``SMD CDS (Gcds)`` is the non-electrostatic
  cavity-dispersion-solvent-structure term.

Reading those numbers is therefore enough to say, per state and per
environment, exactly how much of an environment shift is *electrostatic* and
how much is *everything else*. That is Stage 13's whole point, and it is an
identity rather than a difference of two separate calculations -- the split
comes from one self-consistent calculation, not from subtracting two runs that
differ in more than one thing.

This module is a pure parser: it never launches ORCA and never writes files.
"""

from __future__ import annotations

import re

#: CODATA-ish conversion used across the project (matches analyze_cpcm_eps_scan).
HARTREE_TO_EV = 27.211386245988


HARTREE_TO_KCAL = 627.509474

_TOTAL_ENERGY = re.compile(r"^Total Energy\s+:\s+(-?\d+\.\d+)\s+Eh", re.M)
_CPCM_DIELECTRIC = re.compile(r"^CPCM Dielectric\s+:\s+(-?\d+\.\d+)\s+Eh", re.M)
_SMD_CDS_EH = re.compile(r"^SMD CDS \(Gcds\)\s+:\s+(-?\d+\.\d+)\s+Eh", re.M)
_SMD_CDS_KCAL = re.compile(
    r"^SMD CDS free energy correction energy :\s+(-?\d+\.\d+)\s+Kcal/mol", re.M)
_DISPERSION = re.compile(r"^Dispersion correction\s+(-?\d+\.\d+)\s*$", re.M)
_GCP = re.compile(r"^gCP correction\s+(-?\d+\.\d+)\s*$", re.M)
_FINAL = re.compile(r"^FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)\s*$", re.M)
_EPSILON = re.compile(r"^  Epsilon\s+\.\.\.\s+(\d+\.\d+)", re.M)
_REFRAC = re.compile(r"^  Refrac\s+\.\.\.\s+(\d+\.\d+)", re.M)
_SOLVENT = re.compile(r"^Solvent:\s+\.\.\.\s+(\S+)", re.M)

#: The keys every ledger carries, in report order.
LEDGER_KEYS = (
    "final_single_point_eh",
    "total_energy_eh",
    "dispersion_eh",
    "gcp_eh",
    "cpcm_dielectric_eh",
    "smd_cds_eh",
)


def _last(pattern: re.Pattern[str], text: str) -> float | None:
    """The last match of ``pattern``; a single point prints each term once."""

    found = pattern.findall(text)
    if not found:
        return None
    try:
        return float(found[-1])
    except (TypeError, ValueError):
        return None


def parse_ledger(text: str) -> dict:
    """The energy ledger of one ORCA single-point output.

    Absent terms come back as ``None`` rather than 0.0, so that "no solvent"
    and "solvent with a zero contribution" stay distinguishable. ``identity``
    is the residual of ``FINAL = Total + dispersion + gCP``; it is non-zero
    only because ORCA prints each term to a fixed number of decimals.
    """

    final = _last(_FINAL, text)
    total = _last(_TOTAL_ENERGY, text)
    dispersion = _last(_DISPERSION, text)
    gcp = _last(_GCP, text)
    cpcm = _last(_CPCM_DIELECTRIC, text)
    cds = _last(_SMD_CDS_EH, text)
    cds_kcal = _last(_SMD_CDS_KCAL, text)
    epsilon = _last(_EPSILON, text)

    identity = None
    if None not in (final, total, dispersion, gcp):
        identity = final - (total + dispersion + gcp)

    cds_check = None
    if cds is not None and cds_kcal is not None:
        cds_check = cds - cds_kcal / HARTREE_TO_KCAL

    solvent = _SOLVENT.search(text)
    refrac = _last(_REFRAC, text)
    return {
        "final_single_point_eh": final,
        "total_energy_eh": total,
        "dispersion_eh": dispersion,
        "gcp_eh": gcp,
        "cpcm_dielectric_eh": cpcm,
        "smd_cds_eh": cds,
        "smd_cds_kcal": cds_kcal,
        "cpcm_epsilon": epsilon,
        "cpcm_refrac": refrac,
        "cpcm_solvent": solvent.group(1) if solvent else None,
        "identity_residual_eh": identity,
        "cds_kcal_vs_eh_residual_eh": cds_check,
    }


def environment_is_smd(ledger: dict) -> bool:
    """True when ORCA reported an SMD run (both solvation terms present)."""

    return ledger.get("smd_cds_eh") is not None and ledger.get("cpcm_dielectric_eh") is not None


def environment_is_bare_cpcm(ledger: dict) -> bool:
    """True when ORCA reported a bare-CPCM run (dielectric only, no CDS)."""

    return ledger.get("cpcm_dielectric_eh") is not None and ledger.get("smd_cds_eh") is None


def shift_components(ledger: dict, gas: dict) -> dict:
    """Split ``FINAL_SMD - FINAL_gas`` into electrostatic and everything else.

    Returns ``electrostatic_eh`` (the CPCM dielectric term of this run) and
    ``non_electrostatic_eh`` (CDS of this run, plus any solvent-induced change
    in the D4 dispersion and gCP terms -- both of which are computed from the
    solvent-adapted density). Their sum reproduces ``d_final_eh`` exactly.
    """

    d_final = None
    if ledger.get("final_single_point_eh") is not None and gas.get("final_single_point_eh") is not None:
        d_final = ledger["final_single_point_eh"] - gas["final_single_point_eh"]

    electrostatic = ledger.get("cpcm_dielectric_eh") or 0.0
    non_electrostatic = None
    if None not in (d_final,):  # d_final includes both terms by construction
        non_electrostatic = d_final - electrostatic

    return {
        "d_final_eh": d_final,
        "electrostatic_eh": electrostatic if ledger.get("cpcm_dielectric_eh") is not None else None,
        "non_electrostatic_eh": non_electrostatic,
        "smd_cds_eh": ledger.get("smd_cds_eh"),
        "d_dispersion_eh": (
            None if None in (ledger.get("dispersion_eh"), gas.get("dispersion_eh"))
            else ledger["dispersion_eh"] - gas["dispersion_eh"]),
        "d_gcp_eh": (
            None if None in (ledger.get("gcp_eh"), gas.get("gcp_eh"))
            else ledger["gcp_eh"] - gas["gcp_eh"]),
    }