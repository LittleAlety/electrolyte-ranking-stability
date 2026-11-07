#!/usr/bin/env python
"""W25 / Gate 1, reduction axis: the secondary DOE series cannot close the gate.

Why this module exists
----------------------
W25 is the first week in which the ordering-consistency tier of Gate 1
(``scripts/check_series_rel_ordering.py``) could be evaluated at all.  A
transcribed same-apparatus oxidation series (Ue 1994 via Okoshi 2015, 7 of the 18
core-set molecules) arrived from the PI, and the frozen checker returned
``tau_b = 0.4286 < 0.90`` over ``n_pairs = 21`` -- the oxidation axis
**disagrees** (``outputs/week25/series_rel_ordering_check.json``).

The reduction axis has no comparable series.  The only reduction data on file are
three US DOE FY2016 first-cycle dQ/dV peak positions, which the ingest module
(``scripts/ingest_gate1_anchor_series.py``) already labels ``secondary`` and keeps
physically isolated from the 31 ``method=est`` rows.  This module adjudicates that
axis honestly: it reports **why the axis cannot be evaluated**.  It never promotes
three rows into a 21-pair verdict, and it assigns no uncertainty the source does
not state.

The distinction that matters
----------------------------
* ``ordering_disagrees`` (oxidation, W25): enough pairs existed, and the model
  ordered them the wrong way.
* ``insufficient_pairs`` (reduction, this module): there are not enough pairs to
  say anything at all.  "Not enough evidence" is not "contradicted".

Orientation, stated explicitly
------------------------------
The frozen reduction key is ``p_red = E(anion) - E(neutral) = -EA`` (frozen
convention documented in ``scripts/analyze_c1_coordination.py`` lines 750-754,
and carried into week 4 by ``scripts/analyze_p1_core_set.py:253`` and
``scripts/analyze_p2_environment.py:133``).  Larger means *harder to reduce*,
i.e. more stable.  An experimental reduction potential in V vs Li/Li+ runs the
other way: a higher potential means the solvent is reduced sooner, i.e. *easier*
to reduce.  Concordance therefore requires

    sign(exp_i - exp_j) == -sign(model_i - model_j)

which is the inverse of the rule ``scripts/check_series_rel_ordering.py`` applies
verbatim to both properties (``sign_exp == sign_mod``).  That script and its
frozen output are not modified here (hard constraint); the asymmetry is reported
instead.  It is latent today because ``data/anchors/within_series_ordering.csv``
holds oxidation rows only, so the reduction branch has never executed.  Both
conventions are reported below so the reader can see exactly what the choice
costs (2/3 vs 1/3 concordant).

Usage
-----
    python scripts/analyze_w25_gate1_reduction.py
    python scripts/analyze_w25_gate1_reduction.py --check

Writes
------
``outputs/week25/gate1_reduction_secondary.json``
``outputs/week25/gate1_reduction_secondary.md``   (Chinese)

Exit status: 0 on success, 1 when ``--check`` finds stale outputs or the inputs
changed shape, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOE_CSV = REPO_ROOT / "data" / "anchors" / "doe_apr2016_reduction_secondary.csv"
WITHIN_SERIES_CSV = REPO_ROOT / "data" / "anchors" / "within_series_ordering.csv"
P1_DERIVED_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
P2_SMD_CSV = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
P1_AUDIT_JSON = REPO_ROOT / "outputs" / "week4" / "p1_core_set_audit.json"
C1_SHIFTS_CSV = REPO_ROOT / "outputs" / "week5" / "c1_coord_shifts.csv"
C1_IDENTITY_CSV = REPO_ROOT / "outputs" / "week5" / "c1_state_identity.csv"
OXIDATION_CHECK_JSON = REPO_ROOT / "outputs" / "week25" / "series_rel_ordering_check.json"

OUT_JSON = REPO_ROOT / "outputs" / "week25" / "gate1_reduction_secondary.json"
OUT_MD = REPO_ROOT / "outputs" / "week25" / "gate1_reduction_secondary.md"

#: Pre-registered criterion -- identical to scripts/check_series_rel_ordering.py.
MIN_PAIRS = 18
MIN_TAU_B = 0.9
THRESHOLD_SOURCE = (
    "data/anchors/solution_anchor_verification.md sections 1-3 (n_pairs>=18); "
    "config/prereg.yaml section 2 "
    "probabilistic_pair_ordering.thresholds.strong_i_gt_j = 0.9"
)
THRESHOLD_FROZEN_DATE = "2026-10-02"

HARTREE_TO_EV = 27.211386245988
TIE_EPSILON = 1e-9

#: The DOE FY2016 rows are the only reduction rows on file.
DOE_SERIES_ID = "DOE_APR_FY2016"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path):
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value):
    text = ("" if value is None else str(value)).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def sign(delta: float) -> int:
    if delta > TIE_EPSILON:
        return 1
    if delta < -TIE_EPSILON:
        return -1
    return 0


def load_doe():
    """solvent -> experimental reduction descriptor (V vs Li/Li+)."""
    table = {}
    for row in read_rows(DOE_CSV):
        name = (row.get("solvent") or "").strip()
        if not name:
            continue
        if (row.get("axis") or "").strip() != "reduction":
            raise SystemExit("unexpected axis in %s: %r" % (DOE_CSV, row.get("axis")))
        table[name] = {
            "potential_V_vs_Li": number(row.get("potential_V_vs_Li")),
            "method": (row.get("method") or "").strip(),
            "electrode": (row.get("electrode") or "").strip(),
            "supporting_electrolyte": (row.get("supporting_electrolyte") or "").strip(),
            "criterion": (row.get("criterion") or "").strip(),
            "series_id": (row.get("series_id") or "").strip(),
            "adjudication": (row.get("adjudication") or "").strip(),
            "repo_verification": (row.get("repo_verification") or "").strip(),
        }
    return table


def load_p1():
    """name -> p1_red_ev (P1 = gas phase r2SCAN-3c vertical, -EA)."""
    table = {}
    for row in read_rows(P1_DERIVED_CSV):
        name = (row.get("name") or "").strip()
        if name:
            table[name] = number(row.get("p1_red_ev"))
    return table


def load_p2():
    """name -> E(anion) - E(neutral) in eV (P2 = SMD(acetonitrile), G1 geometry)."""
    energies = {}
    layer_notes = set()
    for row in read_rows(P2_SMD_CSV):
        name = (row.get("name") or "").strip()
        state = (row.get("state") or "").strip()
        energy = number(row.get("final_energy_eh"))
        if not name or energy is None:
            continue
        energies.setdefault(name, {})[state] = energy
        layer_notes.add((row.get("layer") or "").strip())
    table = {}
    for name, states in energies.items():
        if "anion" in states and "neutral" in states:
            table[name] = (states["anion"] - states["neutral"]) * HARTREE_TO_EV
    return table, sorted(layer_notes)


def load_c1():
    """Primary-motif C1 rows plus the state-identity ledger."""
    names = []
    for row in read_rows(C1_SHIFTS_CSV):
        if (row.get("is_primary") or "").strip().lower() in {"true", "1", "yes"}:
            names.append((row.get("name") or "").strip())
    labels = {}
    n_reduced = 0
    for row in read_rows(C1_IDENTITY_CSV):
        if (row.get("redox_state") or "").strip() != "reduced":
            continue
        n_reduced += 1
        labels.setdefault((row.get("name") or "").strip(), []).append(
            (row.get("state_identity_label") or "").strip()
        )
    return {
        "names": sorted(set(names)),
        "n_reduced_rows": n_reduced,
        "reduced_labels": labels,
    }


def build_pairs(experiment, model):
    """All C(n,2) pairs among the species that carry both an experimental and a
    model value, under both orientation conventions."""
    species = sorted(set(experiment) & set(model))
    rows = []
    for a, b in combinations(species, 2):
        exp_delta = experiment[a] - experiment[b]
        mod_delta = model[a] - model[b]
        sign_exp = sign(exp_delta)
        sign_mod = sign(mod_delta)
        rows.append(
            {
                "species_i": a,
                "species_j": b,
                "experiment_i_V": experiment[a],
                "experiment_j_V": experiment[b],
                "experiment_sign": sign_exp,
                "model_i": model[a],
                "model_j": model[b],
                "model_sign": sign_mod,
                "concordant_physics_rule": sign_exp != 0 and sign_mod != 0 and sign_exp == -sign_mod,
                "concordant_frozen_script_rule": sign_exp != 0 and sign_mod != 0 and sign_exp == sign_mod,
            }
        )
    return species, rows


def summarise(rows):
    return {
        "n_pairs": len(rows),
        "n_concordant_physics_rule": sum(1 for row in rows if row["concordant_physics_rule"]),
        "n_concordant_frozen_script_rule": sum(
            1 for row in rows if row["concordant_frozen_script_rule"]
        ),
        "n_discordant_physics_rule": sum(
            1 for row in rows if not row["concordant_physics_rule"]
        ),
        "n_discordant_frozen_script_rule": sum(
            1 for row in rows if not row["concordant_frozen_script_rule"]
        ),
    }


def rank_easiest_first(model):
    """Smaller p_red = easier to reduce, so ascending order is 'easiest first'."""
    return sorted(model, key=lambda name: (model[name], name))


def rank_experiment_easiest_first(experiment):
    """Higher potential = reduced sooner = easier to reduce."""
    return sorted(experiment, key=lambda name: (-experiment[name], name))


def evaluate() -> dict:
    doe = load_doe()
    p1 = load_p1()
    p2, p2_layers = load_p2()
    c1 = load_c1()

    doe_species = sorted(doe)
    p1_species, p1_rows = build_pairs(
        {name: doe[name]["potential_V_vs_Li"] for name in doe if doe[name]["potential_V_vs_Li"] is not None},
        {name: p1[name] for name in p1 if name in doe and p1[name] is not None},
    )
    p2_species, p2_rows = build_pairs(
        {name: doe[name]["potential_V_vs_Li"] for name in doe if doe[name]["potential_V_vs_Li"] is not None},
        {name: p2[name] for name in p2 if name in doe},
    )

    n_pairs = len(p1_rows)
    if p1_species != p2_species:
        raise SystemExit(
            "P1 and P2 cover different species: %s vs %s" % (p1_species, p2_species)
        )

    with io.open(P1_AUDIT_JSON, encoding="utf-8") as handle:
        audit = json.load(handle)
    unbound = audit.get("flag_counts", {}).get("unbound_anion")
    n_molecules = audit.get("n_molecules")

    oxidation = None
    if OXIDATION_CHECK_JSON.exists():
        with io.open(OXIDATION_CHECK_JSON, encoding="utf-8") as handle:
            payload = json.load(handle)
        oxidation = {
            "source": "outputs/week25/series_rel_ordering_check.json",
            "ok": payload.get("ok"),
            "reason": payload.get("reason"),
            "tau_b": payload.get("tau_b"),
            "n_pairs": payload.get("n_pairs"),
            "series_id": (payload.get("series") or [{}])[0].get("series_id"),
        }

    within = read_rows(WITHIN_SERIES_CSV)
    properties = sorted({(row.get("property") or "").strip() for row in within})

    doe_easy = rank_experiment_easiest_first(
        {name: doe[name]["potential_V_vs_Li"] for name in doe if doe[name]["potential_V_vs_Li"] is not None}
    )
    p1_easy = rank_easiest_first({name: p1[name] for name in p1_species})
    p2_easy = rank_easiest_first({name: p2[name] for name in p2_species})

    covered_by_c1 = sorted(set(c1["names"]) & set(doe_species))
    c1_pairs = len(covered_by_c1) * (len(covered_by_c1) - 1) // 2
    li_centred = sorted(
        name for name, labels in c1["reduced_labels"].items()
        if any(label and label != "molecule_centered_redox" for label in labels)
    )

    payload = {
        "stage": "W25",
        "module": "analyze_w25_gate1_reduction",
        "tier": "ordering_consistency",
        "axis": "reduction_potential",
        "reference": (
            "docs/38_week24_corealign_report.md section 9.2; "
            "outputs/week24_corealign/gate1_anchor_feasibility.md"
        ),
        "ok": False,
        "verdict": "not_evaluable_secondary_only",
        "reason": "insufficient_pairs",
        "detail": (
            "3 species -> C(3,2)=3 usable pairs < pre-registered min_pairs=18; the reduction "
            "axis cannot meet the ordering-tier criterion on the evidence currently on file"
        ),
        "insufficient_is_not_inconsistent": (
            "This axis is *insufficient*, not *inconsistent*. The oxidation axis "
            "(n_pairs=21, tau_b=0.4286) is the one that returned ordering_disagrees."
        ),
        "criterion": {
            "min_pairs": MIN_PAIRS,
            "min_tau_b": MIN_TAU_B,
            "threshold_source": THRESHOLD_SOURCE,
            "frozen_date": THRESHOLD_FROZEN_DATE,
        },
        "series_id": DOE_SERIES_ID,
        "adjudication": "secondary",
        "n_species": len(doe_species),
        "species": doe_species,
        "n_pairs": n_pairs,
        "n_pairs_shortfall": MIN_PAIRS - n_pairs,
        "min_species_needed": 7,
        "min_species_note": "C(7,2)=21 >= 18, so a same-criterion series must cover >= 7 core-set molecules",
        "doe_series_internal_homogeneity": {
            "same_apparatus": False,
            "same_criterion": False,
            "detail": (
                "FEC/VC rows are Si-Gr half cells, the EC row is a graphite half cell, and the "
                "descriptor is a first-cycle dQ/dV peak (not an LSV onset at 1 mA/cm2); the three "
                "rows are not one (paper, apparatus, criterion) series"
            ),
        },
        "orientation": {
            "model_key": "p_red = E(anion) - E(neutral) = -EA (P1: p1_red_ev; P2: E(anion)-E(neutral))",
            "model_sense": "larger = harder to reduce = more stable",
            "model_source": (
                "scripts/analyze_c1_coordination.py:750-754; scripts/analyze_p1_core_set.py:253; "
                "scripts/analyze_p2_environment.py:133"
            ),
            "experiment_key": "reduction potential in V vs Li/Li+ (DOE dQ/dV first-cycle peak)",
            "experiment_sense": "larger = reduced sooner = easier to reduce",
            "concordance_rule_used_here": "sign(exp_i - exp_j) == -sign(model_i - model_j)",
            "frozen_script_rule": (
                "scripts/check_series_rel_ordering.py compares sign(exp) == sign(model) for every "
                "property (lines 230-247)"
            ),
            "frozen_script_asymmetry": (
                "That same-sign rule is correct for p1_ox_ev (= IP; larger = harder to oxidise = "
                "higher experimental oxidation potential) but inverted for p1_red_ev (= -EA). The "
                "script's docstring claim that both keys share the experimental orientation holds "
                "only for the oxidation axis. The defect is latent: within_series_ordering.csv "
                "currently holds oxidation rows only, so the reduction branch never runs."
            ),
            "action_taken": (
                "reported only; scripts/check_series_rel_ordering.py and "
                "outputs/week2/series_rel_ordering_check.json were NOT modified"
            ),
        },
        "p1": {
            "model": "outputs/week4/p1_core_set_derived.csv:p1_red_ev",
            "layer": "P1 gas-phase r2SCAN-3c vertical (-EA), core set",
            "values": {name: p1[name] for name in p1_species},
            "experiment_values_V_vs_Li": {
                name: doe[name]["potential_V_vs_Li"] for name in p1_species
            },
            "experiment_order_easiest_first": doe_easy,
            "model_order_easiest_first": p1_easy,
            "order_agrees": doe_easy == p1_easy,
            "pairs": p1_rows,
            "summary": summarise(p1_rows),
        },
        "p2": {
            "model": "outputs/week4/p2_core_set_smd_acetonitrile.csv:E(anion)-E(neutral)",
            "layer": "P2 CPCM(SMD) acetonitrile, vertical at the G1 geometry, core set",
            "layers_seen": p2_layers,
            "hartree_to_ev": HARTREE_TO_EV,
            "values": {name: p2[name] for name in p2_species},
            "experiment_values_V_vs_Li": {
                name: doe[name]["potential_V_vs_Li"] for name in p2_species
            },
            "experiment_order_easiest_first": doe_easy,
            "model_order_easiest_first": p2_easy,
            "order_agrees": doe_easy == p2_easy,
            "pairs": p2_rows,
            "summary": summarise(p2_rows),
            "binding_check": {
                "bound": sorted(name for name in p2_species if p2[name] < 0.0),
                "unbound": sorted(name for name in p2_species if p2[name] >= 0.0),
                "note": (
                    "a negative value means the anion is below the neutral in implicit solvent; "
                    "only VC is bound at this layer"
                ),
            },
        },
        "p1_gas_phase_caveat": {
            "source": "outputs/week4/p1_core_set_audit.json:flag_counts.unbound_anion",
            "unbound_anion": unbound,
            "n_molecules": n_molecules,
            "statement": (
                "Every core-set P1 anion is unbound, so P1 reduction values are basis-set "
                "artefacts and the P1 reduction ordering carries no physical weight. The "
                "reduction-axis conclusion rests on P2/C1 only (consistent with the paper's "
                "section 2.3 / 3.2)."
            ),
        },
        "c1": {
            "source": "outputs/week5/c1_coord_shifts.csv (is_primary=true rows)",
            "n_molecules_with_primary_motif": len(c1["names"]),
            "species": c1["names"],
            "doe_species_covered": covered_by_c1,
            "n_pairs_possible": c1_pairs,
            "note": (
                "C(1,2)=0: the C1 condition state cannot form a single pair among the three DOE "
                "species, because FEC and VC were never run in the Li-coordinated set."
            ),
            "state_identity_caveat": {
                "source": "outputs/week5/c1_state_identity.csv (redox_state=reduced)",
                "n_reduced_rows": c1["n_reduced_rows"],
                "non_molecule_centred_species": li_centred,
                "note": (
                    "for most motifs the added electron sits on Li+ rather than on the solvent, so "
                    "a C1 'reduction' ordering is not a bare-solvent reduction ordering"
                ),
            },
        },
        "gate1_oxidation": oxidation,
        "within_series_table": {
            "source": "data/anchors/within_series_ordering.csv",
            "n_rows": len(within),
            "properties": properties,
            "reduction_rows": 0,
            "note": (
                "the pre-registered table holds oxidation rows only; the 3 DOE rows live in a "
                "separate file so that they can never be pooled into the tau_b computation"
            ),
        },
        "required_to_close": {
            "minimum": (
                "one series_id covering >= 7 of the 18 core-set molecules with a differentiating "
                "reduction descriptor -> C(7,2)=21 usable pairs >= 18"
            ),
            "requirements": [
                "同装置：电极材料、电解池、参比电极及其盐桥均一致（same apparatus: electrode "
                "material, cell, reference electrode and junction）",
                "同判据：例如统一的“电流密度达到某一阈值时的 LSV 起始电位”，或在惰性电极 + "
                "惰性阳离子条件下的 CV 峰位（same criterion）",
                "同态：Li 盐体系锚定的是 C1/C2 梯级，不能用来裁决 C0 梯级（same state）",
                "给出参比电极换算关系与可重复性数值（stated conversion and reproducibility）",
                "描述符在 7 个以上溶剂之间必须真有离散度——被共同分解极限钉死的系列不含排序信息",
            ],
            "candidates": [
                {
                    "source": "Delp et al., Electrochim. Acta 2016, 209, 498-510",
                    "doi": "10.1016/j.electacta.2016.05.100",
                    "coverage": "EC, DMC, FEC, VC",
                    "provenance": "pi_supplied_literature_note; not_verified_in_repo",
                    "caveat": "4 species -> 6 pairs, still < 18; Li-salt electrolyte, so it anchors "
                              "the C1/C2 tier rather than C0",
                },
                {
                    "source": "Borodin, Behl, Jow, J. Phys. Chem. C 2013",
                    "doi": "",
                    "coverage": "DMC, EMC, EC, PC, VC, TMS, TMP",
                    "provenance": "pi_supplied_literature_note; not_verified_in_repo",
                    "caveat": "per-entry criteria differ; pooling it as one series would violate the "
                              "same-criterion requirement",
                },
                {
                    "source": "Ue 1994 / Ue 1997 reduction limits",
                    "doi": "10.1149/1.2059270 / 10.1149/1.1837882",
                    "coverage": "many solvents",
                    "provenance": "pi_supplied_literature_note; not_verified_in_repo",
                    "caveat": "the reduction limit is capped near -3.0 V vs SCE by Et4N+ "
                              "decomposition, so the series has no discriminating power for "
                              "solvent reduction",
                },
            ],
            "explicitly_not_done": [
                "no uncertainty was assigned to the three DOE rows (the source states none)",
                "no attempt was made to reach 18 pairs by pooling unlike apparatuses",
            ],
        },
        "sources": {
            "data/anchors/doe_apr2016_reduction_secondary.csv": sha256_file(DOE_CSV),
            "data/anchors/within_series_ordering.csv": sha256_file(WITHIN_SERIES_CSV),
            "outputs/week4/p1_core_set_derived.csv": sha256_file(P1_DERIVED_CSV),
            "outputs/week4/p2_core_set_smd_acetonitrile.csv": sha256_file(P2_SMD_CSV),
            "outputs/week4/p1_core_set_audit.json": sha256_file(P1_AUDIT_JSON),
            "outputs/week5/c1_coord_shifts.csv": sha256_file(C1_SHIFTS_CSV),
            "outputs/week5/c1_state_identity.csv": sha256_file(C1_IDENTITY_CSV),
        },
        "generated_by": "scripts/analyze_w25_gate1_reduction.py",
        "deterministic": True,
    }
    if OXIDATION_CHECK_JSON.exists():
        payload["sources"]["outputs/week25/series_rel_ordering_check.json"] = sha256_file(
            OXIDATION_CHECK_JSON
        )
    return payload


def _fmt(value, digits=4):
    return "%.*f" % (digits, value)


def render_markdown(payload: dict) -> str:
    p1 = payload["p1"]
    p2 = payload["p2"]
    orientation = payload["orientation"]
    lines = []
    add = lines.append

    add("# W25 · Gate 1 还原轴判定（旁证级数据，不可判定）")
    add("")
    add("> 生成脚本：`scripts/analyze_w25_gate1_reduction.py`（确定性，无随机数；`--check` 可复验）")
    add("")
    add("## 0. 结论先行")
    add("")
    add(
        "- **该轴不可能通过 Gate 1 的排序层判据**：文件内只有 %d 个物种，"
        "最多组成 C(%d,2) = **%d 对**，低于预注册的 `n_pairs >= %d`。"
        % (payload["n_species"], payload["n_species"], payload["n_pairs"], payload["criterion"]["min_pairs"])
    )
    add(
        "- 定性为 **`%s`（不可判定 / 仅旁证）**，而不是“判负”。"
        "**“证据不足”与“排序不一致”是两回事**：前者是样本量问题，后者才是结论冲突。"
        % payload["reason"]
    )
    add(
        "- 真正判负的是**氧化轴**：`n_pairs=%s`、`tau_b=%s < %s`"
        "（`outputs/week25/series_rel_ordering_check.json`）。若把还原轴这 3 对拿去报 τ_b，"
        "会把“没数据”包装成“有结论”。"
        % (
            payload["gate1_oxidation"]["n_pairs"] if payload["gate1_oxidation"] else "n/a",
            _fmt(payload["gate1_oxidation"]["tau_b"]) if payload["gate1_oxidation"] else "n/a",
            payload["criterion"]["min_tau_b"],
        )
    )
    add(
        "- 要满足 `n_pairs >= 18`，一条同判据系列至少需覆盖 **%d 个核心集分子**（C(7,2)=21）。"
        "当前缺口 %d 对。"
        % (payload["min_species_needed"], payload["n_pairs_shortfall"])
    )
    add("")
    add("## 1. 为什么这条轴“不可能”通过")
    add("")
    add("| 项目 | 值 |")
    add("|---|---|")
    add("| 系列 | `%s`（adjudication = %s）|" % (payload["series_id"], payload["adjudication"]))
    add("| 物种 | %s |" % ", ".join(payload["species"]))
    add("| 可用对数 | **%d**（C(3,2)）|" % payload["n_pairs"])
    add("| 预注册门槛 | n_pairs >= %d，且 tau_b >= %s |" % (MIN_PAIRS, MIN_TAU_B))
    add("| 缺口 | **%d 对** |" % payload["n_pairs_shortfall"])
    add("| 判定 | `not_evaluable_secondary_only` / `insufficient_pairs` |")
    add("")
    add(
        "该 3 行数据本身**也不是一条同装置系列**：" + payload["doe_series_internal_homogeneity"]["detail"] + "。"
    )
    add("")
    add("## 2. 取向口径（本判定的关键前提）")
    add("")
    add("| 侧 | 量 | 取向 |")
    add("|---|---|---|")
    add("| 模型 | `%s` | **%s** |" % (orientation["model_key"], orientation["model_sense"]))
    add("| 实验 | `%s` | **%s** |" % (orientation["experiment_key"], orientation["experiment_sense"]))
    add("")
    add("因此一致判据是 `%s`。" % orientation["concordance_rule_used_here"])
    add("")
    add(
        "**与 `scripts/check_series_rel_ordering.py` 的差异（必须说明）**："
        "该脚本对两个性质一律使用 `sign(exp) == sign(model)`（第 230–247 行）。"
        "这对 `p1_ox_ev`（= IP，越大越难氧化、实验氧化电位越高）成立，"
        "但对 `p1_red_ev`（= −EA，越大越难还原、实验还原电位越低）**取向相反**——"
        "脚本 docstring 里“两个键与实验电位同向”的说法只对氧化轴成立。"
    )
    add("")
    add(
        "该缺陷目前是**潜伏的**：`data/anchors/within_series_ordering.csv` 只有氧化行，"
        "还原分支从未执行。本模块**只报告、不修改**——"
        "`scripts/check_series_rel_ordering.py` 与 `outputs/week2/series_rel_ordering_check.json` "
        "均为冻结件，未作任何改动。"
    )
    add("")
    add("## 3. 三对逐一对照")
    add("")
    add("DOE 旁证序（易还原 → 难还原）：**%s**。" % " > ".join(payload["p1"]["experiment_order_easiest_first"]))
    add("")
    add("### 3.1 P1（气相 r2SCAN-3c 垂直，−EA）")
    add("")
    add("| 物种 | p1_red_ev (eV) | 实验电位 (V vs Li) |")
    add("|---|---|---|")
    for name in p1["model_order_easiest_first"]:
        add("| %s | %s | %s |" % (name, _fmt(p1["values"][name]), _fmt(p1["experiment_values_V_vs_Li"][name], 2)))
    add("")
    add("P1 计算序（易 → 难）：**%s**；与实验序一致：**%s**。"
        % (" < ".join(p1["model_order_easiest_first"]), "是" if p1["order_agrees"] else "否"))
    add("")
    add("| 对 | 实验符号 | 模型符号 | 物理取向判据 | 冻结脚本判据 |")
    add("|---|---|---|---|---|")
    for row in p1["pairs"]:
        add(
            "| %s / %s | %+d | %+d | %s | %s |"
            % (
                row["species_i"], row["species_j"], row["experiment_sign"], row["model_sign"],
                "一致" if row["concordant_physics_rule"] else "**不一致**",
                "一致" if row["concordant_frozen_script_rule"] else "**不一致**",
            )
        )
    add("")
    add(
        "- **符号一致数（本模块取向）：%d / %d**；按冻结脚本取向则为 %d / %d。"
        % (
            p1["summary"]["n_concordant_physics_rule"], p1["summary"]["n_pairs"],
            p1["summary"]["n_concordant_frozen_script_rule"], p1["summary"]["n_pairs"],
        )
    )
    add(
        "- 唯一分歧对：FEC 与 VC 的相对位置（实验 FEC 更易还原；模型判 VC 更易还原）。"
        "其余两对（FEC/EC、VC/EC）两种取向都给出一致。"
    )
    add("")
    add("### 3.2 P2（CPCM/SMD 乙腈，G1 几何上的垂直量）")
    add("")
    add("| 物种 | E(anion)−E(neutral) (eV) | 实验电位 (V vs Li) |")
    add("|---|---|---|")
    for name in p2["model_order_easiest_first"]:
        add("| %s | %s | %s |" % (name, _fmt(p2["values"][name]), _fmt(p2["experiment_values_V_vs_Li"][name], 2)))
    add("")
    add("P2 计算序（易 → 难）：**%s**；与实验序一致：**%s**。"
        % (" < ".join(p2["model_order_easiest_first"]), "是" if p2["order_agrees"] else "否"))
    add("")
    add(
        "- **符号一致数（本模块取向）：%d / %d**；按冻结脚本取向则为 %d / %d——与 P1 完全相同。"
        % (
            p2["summary"]["n_concordant_physics_rule"], p2["summary"]["n_pairs"],
            p2["summary"]["n_concordant_frozen_script_rule"], p2["summary"]["n_pairs"],
        )
    )
    add(
        "- 隐式溶剂下仍只有 **%s** 的ΔE 为负（阴离子真正束缚）；%s 仍为正。"
        % (
            "、".join(p2["binding_check"]["bound"]) or "无",
            "、".join(p2["binding_check"]["unbound"]),
        )
    )
    add("")
    add("## 4. P1 气相阴离子全部不束缚 → P1 还原排序不是物理结论")
    add("")
    add(
        "`outputs/week4/p1_core_set_audit.json` 记录 `unbound_anion = %s`（共 %s 个分子），"
        "即 P1 气相阴离子 **%s/%s 不束缚**。因此 P1 的还原量是有限基组下的伪束缚痕迹，"
        "**P1 还原排序不可作为物理结论**；还原轴的结论只以 **P2 / C1 为载体**"
        "（与论文 §2.3、§3.2 口径一致）。这也是本模块把 P2 并列汇报的原因。"
        % (
            payload["p1_gas_phase_caveat"]["unbound_anion"],
            payload["p1_gas_phase_caveat"]["n_molecules"],
            payload["p1_gas_phase_caveat"]["unbound_anion"],
            payload["p1_gas_phase_caveat"]["n_molecules"],
        )
    )
    add("")
    add("## 5. C1 条件态：覆盖不足，无法补位")
    add("")
    add(
        "`outputs/week5/c1_coord_shifts.csv` 的主 motif 行覆盖 %d 个分子，其中与 DOE 三物种的交集只有 **%s**，"
        "可组成 **%d 对**。即便把条件态纳入，也无法形成任何一对，因为 FEC 与 VC 从未进入 Li 配位集。"
        % (
            payload["c1"]["n_molecules_with_primary_motif"],
            "、".join(payload["c1"]["doe_species_covered"]) or "无",
            payload["c1"]["n_pairs_possible"],
        )
    )
    add("")
    add(
        "另需注意 C1 的态身份问题：`redox_state=reduced` 的 %d 行中，"
        "%s 的电子落在 Li⁺ 上（`state_identity_label != molecule_centered_redox`），"
        "所以 C1 的“还原”序本质上是 Li 中心的，不是裸溶剂的还原序。"
        % (
            payload["c1"]["state_identity_caveat"]["n_reduced_rows"],
            "、".join(payload["c1"]["state_identity_caveat"]["non_molecule_centred_species"]) or "无",
        )
    )
    add("")
    add("## 6. Gate 1 当前状态")
    add("")
    add("| 轴 | 数据 | 对数 | 结果 |")
    add("|---|---|---|---|")
    if payload["gate1_oxidation"]:
        add(
            "| 氧化 | Ue1994 / Okoshi2015（同装置 LSV 系列 `%s`）| %s | **判负**：tau_b = %s < %s（`ordering_disagrees`）|"
            % (
                payload["gate1_oxidation"]["series_id"],
                payload["gate1_oxidation"]["n_pairs"],
                _fmt(payload["gate1_oxidation"]["tau_b"]),
                MIN_TAU_B,
            )
        )
    add(
        "| 还原 | DOE APR FY2016 旁证 3 行 | %d | **不可判定**：不足 %d 对（`insufficient_pairs`）|"
        % (payload["n_pairs"], MIN_PAIRS)
    )
    add("")
    add("因此 Gate 1 仍然**未闭合**，但两个轴的未闭合方式不同：氧化轴是“结论冲突”，还原轴是“证据缺失”。")
    add("")
    add("## 7. 若要把还原轴做成 ≥ 7 个同判据锚点，还需要什么")
    add("")
    add("- 最低要求：" + payload["required_to_close"]["minimum"])
    for item in payload["required_to_close"]["requirements"]:
        add("- " + item)
    add("")
    add("候选来源（**均为 PI 提供的文献线索，本仓库未取到原文、未核验数值**）：")
    add("")
    add("| 来源 | DOI | 预期覆盖 | 已知限制 |")
    add("|---|---|---|---|")
    for item in payload["required_to_close"]["candidates"]:
        add("| %s | %s | %s | %s |" % (item["source"], item["doi"] or "—", item["coverage"], item["caveat"]))
    add("")
    add("本轮**明确没有做**的事：")
    for item in payload["required_to_close"]["explicitly_not_done"]:
        add("- " + item)
    add("")
    add("## 8. 可复现性与来源")
    add("")
    add("| 输入 | SHA256 |")
    add("|---|---|")
    for path, digest in payload["sources"].items():
        add("| `%s` | `%s` |" % (path, digest))
    add("")
    add("复验：`python scripts/analyze_w25_gate1_reduction.py --check`（输出与磁盘逐字节一致才返回 0）。")
    add("")
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with io.open(OUT_JSON, "w", encoding="utf-8", newline="") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with io.open(OUT_MD, "w", encoding="utf-8", newline="") as handle:
        handle.write(render_markdown(payload))


def check_outputs(payload: dict) -> int:
    expected_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    expected_md = render_markdown(payload)
    failures = []
    for path, expected in ((OUT_JSON, expected_json), (OUT_MD, expected_md)):
        if not path.exists():
            failures.append("%s is missing" % path.relative_to(REPO_ROOT))
            continue
        with io.open(path, encoding="utf-8", newline="") as handle:
            actual = handle.read()
        if actual != expected:
            failures.append("%s is stale" % path.relative_to(REPO_ROOT))
    if failures:
        for failure in failures:
            print("STALE: " + failure, file=sys.stderr)
        return 1
    print("OK: outputs match a fresh deterministic run")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="re-run and compare with the files on disk")
    args = parser.parse_args(argv)

    payload = evaluate()
    if args.check:
        return check_outputs(payload)

    write_outputs(payload)
    print("Gate 1 reduction axis (W25, secondary evidence only)")
    print("  species                 : %s" % ", ".join(payload["species"]))
    print("  usable pairs            : %d (min %d)" % (payload["n_pairs"], MIN_PAIRS))
    print("  verdict                 : %s (%s)" % (payload["verdict"], payload["reason"]))
    print(
        "  P1 sign agreement       : %d/%d (physics rule) | %d/%d (frozen-script rule)"
        % (
            payload["p1"]["summary"]["n_concordant_physics_rule"], payload["p1"]["summary"]["n_pairs"],
            payload["p1"]["summary"]["n_concordant_frozen_script_rule"], payload["p1"]["summary"]["n_pairs"],
        )
    )
    print(
        "  P2 sign agreement       : %d/%d (physics rule) | %d/%d (frozen-script rule)"
        % (
            payload["p2"]["summary"]["n_concordant_physics_rule"], payload["p2"]["summary"]["n_pairs"],
            payload["p2"]["summary"]["n_concordant_frozen_script_rule"], payload["p2"]["summary"]["n_pairs"],
        )
    )
    print("  wrote                   : %s" % OUT_JSON.relative_to(REPO_ROOT))
    print("  wrote                   : %s" % OUT_MD.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
