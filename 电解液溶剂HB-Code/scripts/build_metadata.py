#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 0 metadata builder for the "ranking-electrolyte-materials-v2" project.

Deterministically rebuilds the two Stage 0 metadata tables

    data/metadata/core_set.csv     18 rows  (core paired benchmark set)
    data/metadata/broad_pool.csv   40 rows  (broad cheap pool, xTB layer only)

from the authored structure tables below.  The CSV files are *products*: do not
hand-edit them, re-run this script instead.

Design rules
------------
1. The authored SMILES strings in CORE_SET / BROAD_POOL are written to the CSV
   verbatim, so the output is byte-identical whether or not RDKit is installed.
2. RDKit (when importable) is used to
     - validate that every authored SMILES parses,
     - compute heteroatom_count / n_heavy / mw / rotatable_bonds / tpsa,
     - derive the donor-atom labels from the molecular graph.
3. If RDKit is unavailable, the pre-computed FALLBACK_DESCRIPTORS table is used.
   The results must be identical, which --check and --no-rdkit verify.
4. --check never writes anything: it rebuilds the tables in memory and compares
   them with the files on disk, exiting non-zero when they differ.
   The script is idempotent.

Descriptor conventions (frozen in config/scientific_definitions.yaml)
---------------------------------------------------------------------
* donor_atoms  : semicolon-separated label list, ordered "O=" (carbonyl /
  phosphoryl / sulfonyl / sulfoxide oxygen) then "O-" (ether / ester oxygen)
  then "N".
* donor_count  : total number of potential Li+ donor atoms, i.e. every O and
  every N in the molecule (S and P are treated as acceptor centres, not donors).
* heteroatom_count : heavy atoms that are not carbon (O, N, S, P, F, Si, Cl).
* n_heavy      : number of non-hydrogen atoms.
* mw           : average molecular weight [g/mol], 2 decimals (RDKit MolWt).
* tpsa         : topological polar surface area [A^2], 2 decimals (Ertl).
* rotatable_bonds : RDKit *strict* rotatable-bond count (flexibility proxy;
  bonds to terminal atoms, ring bonds and amide C-N bonds are excluded).
"""


from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_CSV = REPO_ROOT / "data" / "metadata" / "core_set.csv"
BROAD_CSV = REPO_ROOT / "data" / "metadata" / "broad_pool.csv"

CORE_COLUMNS = [
    "mol_id",
    "name",
    "smiles",
    "family",
    "role",
    "donor_atoms",
    "donor_count",
    "heteroatom_count",
    "n_heavy",
    "mw",
    "rotatable_bonds",
    "tpsa",
    "functionalization_tags",
    "reason_included",
]

BROAD_COLUMNS = [
    "mol_id",
    "name",
    "smiles",
    "family",
    "role",
    "donor_atoms",
    "donor_count",
    "heteroatom_count",
    "n_heavy",
    "mw",
    "rotatable_bonds",
    "tpsa",
    "functionalization_tags",
    "pool_reason",
]

# ---------------------------------------------------------------------------
# Authored structure tables (the single source of truth)
# ---------------------------------------------------------------------------
# family       : mutually exclusive skeleton family (v2 doc section 5.2).
#                Fluorination is a cross-family functionalization, never a
#                family of its own -> see chemical_space_metadata.md.
# role         : solvent | co-solvent | additive  (v2 doc section 5.2)
# tags         : "|"-separated functionalization tags
# reason/pool  : one-line Chinese justification (carried into the CSV)

CORE_SET = [
    dict(mol_id="C01", name="DMC", smiles="COC(=O)OC",
         full_name="dimethyl carbonate", family="linear_carbonate", role="solvent",
         tags="linear",
         reason_included="低粘度线性碳酸酯，作为最简羰基给体与低粘度共溶剂的基线分子。"),
    dict(mol_id="C02", name="EMC", smiles="CCOC(=O)OC",
         full_name="ethyl methyl carbonate", family="linear_carbonate", role="solvent",
         tags="linear",
         reason_included="不对称线性碳酸酯，连接 DMC 与 DEC 的烷基取代序列并检验链长效应。"),
    dict(mol_id="C03", name="DEC", smiles="CCOC(=O)OCC",
         full_name="diethyl carbonate", family="linear_carbonate", role="co-solvent",
         tags="linear",
         reason_included="长烷基线性碳酸酯，构成同族系统取代序列的末端并降低介电常数。"),
    dict(mol_id="C04", name="EC", smiles="C1COC(=O)O1",
         full_name="ethylene carbonate", family="cyclic_carbonate", role="solvent",
         tags="cyclic",
         reason_included="高介电常数环状碳酸酯主溶剂，是环张力改变还原与开环机理的锚点分子。"),
    dict(mol_id="C05", name="PC", smiles="CC1COC(=O)O1",
         full_name="propylene carbonate", family="cyclic_carbonate", role="co-solvent",
         tags="cyclic",
         reason_included="甲基取代环状碳酸酯，与 EC 对照环上取代对配位与还原稳定性的影响。"),
    dict(mol_id="C06", name="FEC", smiles="O=C1OCC(F)O1",
         full_name="fluoroethylene carbonate", family="cyclic_carbonate", role="additive",
         tags="cyclic|fluorinated",
         reason_included="氟化环状碳酸酯成膜添加剂，提供氟取代对照并关联 LiF 生成机理。"),
    dict(mol_id="C07", name="VC", smiles="O=C1OC=CO1",
         full_name="vinylene carbonate", family="cyclic_carbonate", role="additive",
         tags="cyclic|unsaturated",
         reason_included="不饱和环状碳酸酯成膜添加剂，是还原开环与聚合机理的对照分子。"),
    dict(mol_id="C08", name="DME", smiles="COCCOC",
         full_name="1,2-dimethoxyethane", family="ether", role="solvent",
         tags="linear|chelating",
         reason_included="最简双齿醚，作为 Li+ 螯合配位与醚类还原稳定性的基线分子。"),
    dict(mol_id="C09", name="DOL", smiles="C1COCO1",
         full_name="1,3-dioxolane", family="ether", role="co-solvent",
         tags="cyclic",
         reason_included="五元环醚，与线性醚对照并兼顾开环聚合倾向带来的机理差异。"),
    dict(mol_id="C10", name="TEGDME", smiles="COCCOCCOCCOCCOC",
         full_name="tetraethylene glycol dimethyl ether", family="ether", role="co-solvent",
         tags="linear|chelating|flexible",
         reason_included="长链柔性多齿醚，检验构象柔性与配位数对条件态 redox 的影响。"),
    dict(mol_id="C11", name="EA", smiles="CCOC(C)=O",
         full_name="ethyl acetate", family="ester", role="solvent",
         tags="linear",
         reason_included="乙酸酯类溶剂，以单羰基加单醚氧给体对照碳酸酯的羰基环境差异。"),
    dict(mol_id="C12", name="MA", smiles="COC(C)=O",
         full_name="methyl acetate", family="ester", role="solvent",
         tags="linear",
         reason_included="最简乙酸酯，作为酯类最低分子量给体并与 EA 构成同族取代序列。"),
    dict(mol_id="C13", name="GBL", smiles="O=C1CCCO1",
         full_name="gamma-butyrolactone", family="ester", role="co-solvent",
         tags="cyclic",
         reason_included="环状内酯，以高介电常数与环约束对照线性酯的构象自由度。"),
    dict(mol_id="C14", name="SL", smiles="O=S1(=O)CCCC1",
         full_name="sulfolane", family="sulfone", role="co-solvent",
         tags="cyclic|sulfur_containing",
         reason_included="环状砜，代表 S=O 给体与高氧化稳定性，用于检验硫中心给体化学。"),
    dict(mol_id="C15", name="DMSO", smiles="CS(C)=O",
         full_name="dimethyl sulfoxide", family="sulfoxide", role="co-solvent",
         tags="linear|sulfur_containing",
         reason_included="亚砜类 S=O 给体，作为易氧化方向与氧硫中心电子结构差异的对照。"),
    dict(mol_id="C16", name="AN", smiles="CC#N",
         full_name="acetonitrile", family="nitrile", role="co-solvent",
         tags="linear",
         reason_included="单齿腈，代表 N 给体与高氧化稳定性并与含氧给体形成类型对照。"),
    dict(mol_id="C17", name="TMP", smiles="COP(=O)(OC)OC",
         full_name="trimethyl phosphate", family="phosphate", role="additive",
         tags="linear|phosphorus_containing",
         reason_included="磷酸酯阻燃添加剂，代表 P=O 给体与优先还原成膜的机理路径。"),
    dict(mol_id="C18", name="SN", smiles="N#CCCC#N",
         full_name="succinonitrile", family="nitrile", role="additive",
         tags="linear|chelating",
         reason_included="双齿腈，与单齿 AN 对照以检验螯合与配位数诱导的机理差异。"),
]

BROAD_POOL = [
    dict(mol_id="B01", name="MPC", smiles="CCCOC(=O)OC",
         full_name="methyl propyl carbonate", family="linear_carbonate", role="co-solvent",
         tags="linear", pool_reason="延长烷基链扩展线性碳酸酯取代序列并降低介电常数。"),
    dict(mol_id="B02", name="DPC", smiles="O=C(Oc1ccccc1)Oc1ccccc1",
         full_name="diphenyl carbonate", family="linear_carbonate", role="additive",
         tags="linear|aromatic", pool_reason="芳香取代极端点，测试极性极化率与给体强度的边界。"),
    dict(mol_id="B03", name="FEMC", smiles="FC(F)(F)COC(=O)OC",
         full_name="2,2,2-trifluoroethyl methyl carbonate", family="linear_carbonate", role="co-solvent",
         tags="linear|fluorinated", pool_reason="氟化线性碳酸酯，检验氟取代对还原与配位的同时影响。"),
    dict(mol_id="B04", name="VEC", smiles="C=CC1COC(=O)O1",
         full_name="4-vinyl-1,3-dioxolan-2-one", family="cyclic_carbonate", role="additive",
         tags="cyclic|unsaturated", pool_reason="不饱和环状碳酸酯添加剂，扩展还原聚合类成膜分子。"),
    dict(mol_id="B05", name="TFMEC", smiles="FC(F)(F)C1COC(=O)O1",
         full_name="4-(trifluoromethyl)-1,3-dioxolan-2-one", family="cyclic_carbonate", role="additive",
         tags="cyclic|fluorinated", pool_reason="三氟甲基环状碳酸酯，增强氟化机理对照的取代程度。"),
    dict(mol_id="B06", name="TMC", smiles="O=C1OCCCO1",
         full_name="1,3-dioxan-2-one", family="cyclic_carbonate", role="co-solvent",
         tags="cyclic", pool_reason="六元环碳酸酯，检验环大小对开环还原与配位几何的影响。"),
    dict(mol_id="B07", name="DMEC", smiles="CC1OC(=O)OC1C",
         full_name="4,5-dimethyl-1,3-dioxolan-2-one", family="cyclic_carbonate", role="co-solvent",
         tags="cyclic", pool_reason="双甲基取代环状碳酸酯，扩展位阻与介电常数的变化范围。"),
    dict(mol_id="B08", name="ClEC", smiles="O=C1OCC(Cl)O1",
         full_name="4-chloro-1,3-dioxolan-2-one", family="cyclic_carbonate", role="additive",
         tags="cyclic|halogenated", pool_reason="氯代环状碳酸酯，作为非氟卤素取代的机理对照。"),
    dict(mol_id="B09", name="DEE", smiles="CCOCC",
         full_name="diethyl ether", family="ether", role="co-solvent",
         tags="linear", pool_reason="最简非螯合线性醚，作为醚类单齿给体基线。"),
    dict(mol_id="B10", name="G2", smiles="COCCOCCOC",
         full_name="diethylene glycol dimethyl ether (diglyme)", family="ether", role="co-solvent",
         tags="linear|chelating|flexible", pool_reason="三齿甘醇醚，补全 DME 到 TEGDME 的配位数序列。"),
    dict(mol_id="B11", name="G3", smiles="COCCOCCOCCOC",
         full_name="triethylene glycol dimethyl ether (triglyme)", family="ether", role="co-solvent",
         tags="linear|chelating|flexible", pool_reason="四齿甘醇醚，扩展配位数与构象复杂度的上限。"),
    dict(mol_id="B12", name="THF", smiles="C1CCOC1",
         full_name="tetrahydrofuran", family="ether", role="co-solvent",
         tags="cyclic", pool_reason="单氧五元环醚，与 DOL 对照环上氧原子数目的差异。"),
    dict(mol_id="B13", name="2MeTHF", smiles="CC1CCCO1",
         full_name="2-methyltetrahydrofuran", family="ether", role="co-solvent",
         tags="cyclic", pool_reason="甲基取代环醚，检验环上取代对配位强度与还原的影响。"),
    dict(mol_id="B14", name="DIOX", smiles="C1COCCO1",
         full_name="1,4-dioxane", family="ether", role="co-solvent",
         tags="cyclic|chelating", pool_reason="双齿环醚，检验环约束下双齿螯合的可行性。"),
    dict(mol_id="B15", name="DMM", smiles="COCOC",
         full_name="dimethoxymethane", family="ether", role="co-solvent",
         tags="linear|chelating|acetal", pool_reason="缩醛型醚，氧间距与柔性与 DME 不同，扩展给体几何。"),
    dict(mol_id="B16", name="DEE2", smiles="CCOCCOCC",
         full_name="1,2-diethoxyethane", family="ether", role="co-solvent",
         tags="linear|chelating", pool_reason="乙基封端双齿醚，检验末端取代对螯合构象的微扰。"),
    dict(mol_id="B17", name="HFE347", smiles="FC(F)C(F)(F)OCC(F)(F)F",
         full_name="1,1,2,2-tetrafluoroethyl 2,2,2-trifluoroethyl ether", family="ether", role="co-solvent",
         tags="linear|fluorinated", pool_reason="氟代醚弱溶剂，检验弱给体与极低配位能力的化学空间。"),
    dict(mol_id="B18", name="HFE7100", smiles="COC(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
         full_name="methyl nonafluorobutyl ether", family="ether", role="co-solvent",
         tags="linear|fluorinated", pool_reason="高度氟化醚，作为给体强度接近下限的极端点。"),
    dict(mol_id="B19", name="BTFE", smiles="FC(F)(F)COCC(F)(F)F",
         full_name="bis(2,2,2-trifluoroethyl) ether", family="ether", role="co-solvent",
         tags="linear|fluorinated", pool_reason="对称氟代醚，用于分离分子量效应与氟化效应。"),
    dict(mol_id="B20", name="DMS", smiles="CS(C)(=O)=O",
         full_name="dimethyl sulfone", family="sulfone", role="co-solvent",
         tags="linear|sulfur_containing", pool_reason="最简砜，与亚砜 DMSO 对照硫的氧化态差异。"),
    dict(mol_id="B21", name="EMS", smiles="CCS(C)(=O)=O",
         full_name="ethyl methyl sulfone", family="sulfone", role="co-solvent",
         tags="linear|sulfur_containing", pool_reason="不对称砜，补全砜类烷基取代序列与偶极变化。"),
    dict(mol_id="B22", name="SULFOLENE", smiles="O=S1(=O)CC=CC1",
         full_name="2,5-dihydrothiophene 1,1-dioxide", family="sulfone", role="additive",
         tags="cyclic|unsaturated|sulfur_containing", pool_reason="不饱和环砜，检验不饱和键对还原方向的贡献。"),
    dict(mol_id="B23", name="DESO", smiles="CCS(=O)CC",
         full_name="diethyl sulfoxide", family="sulfoxide", role="co-solvent",
         tags="linear|sulfur_containing", pool_reason="二乙基亚砜，扩展亚砜类给体强度与空间位阻范围。"),
    dict(mol_id="B24", name="THTO", smiles="O=S1CCCC1",
         full_name="tetrahydrothiophene 1-oxide", family="sulfoxide", role="co-solvent",
         tags="cyclic|sulfur_containing", pool_reason="环状亚砜，与环状砜 SL 对照同一环骨架的氧化态效应。"),
    dict(mol_id="B25", name="PN", smiles="CCC#N",
         full_name="propionitrile", family="nitrile", role="co-solvent",
         tags="linear", pool_reason="腈类烷基取代序列扩展点，检验链长对 N 给体强度的影响。"),
    dict(mol_id="B26", name="BN", smiles="CCCC#N",
         full_name="butyronitrile", family="nitrile", role="co-solvent",
         tags="linear", pool_reason="更长的线性腈，扩大粘度与介电常数的覆盖范围。"),
    dict(mol_id="B27", name="ADN", smiles="N#CCCCCC#N",
         full_name="adiponitrile", family="nitrile", role="additive",
         tags="linear|chelating", pool_reason="柔性双齿腈，检验长链螯合配位对条件态 redox 的影响。"),
    dict(mol_id="B28", name="MPN", smiles="COCCC#N",
         full_name="3-methoxypropionitrile", family="nitrile", role="additive",
         tags="linear|mixed_donor", pool_reason="混合 O/N 给体，检验不同给体原子组合的配位选择性。"),
    dict(mol_id="B29", name="MN", smiles="N#CCC#N",
         full_name="malononitrile", family="nitrile", role="additive",
         tags="linear|chelating", pool_reason="刚性双齿腈，与柔性双齿腈对照螯合环大小效应。"),
    dict(mol_id="B30", name="TEP", smiles="CCOP(=O)(OCC)OCC",
         full_name="triethyl phosphate", family="phosphate", role="additive",
         tags="linear|phosphorus_containing", pool_reason="磷酸三乙酯，补全磷酸酯烷基链长与阻燃添加剂系列。"),
    dict(mol_id="B31", name="TBP", smiles="CCCCOP(=O)(OCCCC)OCCCC",
         full_name="tributyl phosphate", family="phosphate", role="additive",
         tags="linear|phosphorus_containing|flexible", pool_reason="长链磷酸酯，作为高柔性与高粘度的磷酸酯端点。"),
    dict(mol_id="B32", name="TFP", smiles="FC(F)(F)COP(=O)(OCC(F)(F)F)OCC(F)(F)F",
         full_name="tris(2,2,2-trifluoroethyl) phosphate", family="phosphate", role="additive",
         tags="linear|fluorinated|phosphorus_containing", pool_reason="氟化磷酸酯，组合氟化与磷氧给体两种机理标签。"),
    dict(mol_id="B33", name="MP", smiles="CCC(=O)OC",
         full_name="methyl propionate", family="ester", role="co-solvent",
         tags="linear", pool_reason="丙酸酯，扩展线性酯的羰基环境与链长序列。"),
    dict(mol_id="B34", name="EF", smiles="CCOC=O",
         full_name="ethyl formate", family="ester", role="co-solvent",
         tags="linear", pool_reason="甲酸酯，最小且位阻最低的酯类给体极端点。"),
    dict(mol_id="B35", name="GVL", smiles="CC1CCC(=O)O1",
         full_name="gamma-valerolactone", family="ester", role="co-solvent",
         tags="cyclic", pool_reason="甲基取代内酯，检验环上取代对内酯还原与配位的影响。"),
    dict(mol_id="B36", name="DVL", smiles="O=C1CCCCO1",
         full_name="delta-valerolactone", family="ester", role="co-solvent",
         tags="cyclic", pool_reason="六元内酯，与五元内酯 GBL 对照环大小效应。"),
    dict(mol_id="B37", name="ES", smiles="O=S1OCCO1",
         full_name="ethylene sulfite", family="sulfite", role="additive",
         tags="cyclic|sulfur_containing", pool_reason="环状亚硫酸酯成膜添加剂，新增含硫成膜机理家族。"),
    dict(mol_id="B38", name="PS", smiles="O=S1(=O)CCCO1",
         full_name="1,3-propane sultone", family="sultone", role="additive",
         tags="cyclic|sulfur_containing", pool_reason="环状磺酸内酯添加剂，新增磺酸酯家族覆盖开环成膜机理。"),
    dict(mol_id="B39", name="HMDSO", smiles="C[Si](C)(C)O[Si](C)(C)C",
         full_name="hexamethyldisiloxane", family="siloxane", role="co-solvent",
         tags="linear|silicon_containing", pool_reason="硅氧烷弱极性溶剂，新增硅氧烷家族检验极低介电常数区域。"),
    dict(mol_id="B40", name="OMTS", smiles="C[Si](C)(C)O[Si](C)(C)O[Si](C)(C)C",
         full_name="octamethyltrisiloxane", family="siloxane", role="co-solvent",
         tags="linear|silicon_containing|flexible", pool_reason="三硅氧烷，扩展硅氧烷链长与柔性覆盖。"),
]

# --- BEGIN GENERATED FALLBACK DESCRIPTORS ---
FALLBACK_DESCRIPTORS: dict = {
    'C1CCOC1': dict(
        heteroatom_count=1,
        n_heavy=5,
        mw=72.11,
        rotatable_bonds=0,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'C1COC(=O)O1': dict(
        heteroatom_count=3,
        n_heavy=6,
        mw=88.06,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'C1COCCO1': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=88.11,
        rotatable_bonds=0,
        tpsa=18.46,
        n_double_o=0,
        n_single_o=2,
        n_n=0,
        donor_atoms='O-',
        donor_count=2,
    ),
    'C1COCO1': dict(
        heteroatom_count=2,
        n_heavy=5,
        mw=74.08,
        rotatable_bonds=0,
        tpsa=18.46,
        n_double_o=0,
        n_single_o=2,
        n_n=0,
        donor_atoms='O-',
        donor_count=2,
    ),
    'C=CC1COC(=O)O1': dict(
        heteroatom_count=3,
        n_heavy=8,
        mw=114.1,
        rotatable_bonds=1,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'CC#N': dict(
        heteroatom_count=1,
        n_heavy=3,
        mw=41.05,
        rotatable_bonds=0,
        tpsa=23.79,
        n_double_o=0,
        n_single_o=0,
        n_n=1,
        donor_atoms='N',
        donor_count=1,
    ),
    'CC1CCC(=O)O1': dict(
        heteroatom_count=2,
        n_heavy=7,
        mw=100.12,
        rotatable_bonds=0,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'CC1CCCO1': dict(
        heteroatom_count=1,
        n_heavy=6,
        mw=86.13,
        rotatable_bonds=0,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'CC1COC(=O)O1': dict(
        heteroatom_count=3,
        n_heavy=7,
        mw=102.09,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'CC1OC(=O)OC1C': dict(
        heteroatom_count=3,
        n_heavy=8,
        mw=116.12,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'CCC#N': dict(
        heteroatom_count=1,
        n_heavy=4,
        mw=55.08,
        rotatable_bonds=0,
        tpsa=23.79,
        n_double_o=0,
        n_single_o=0,
        n_n=1,
        donor_atoms='N',
        donor_count=1,
    ),
    'CCC(=O)OC': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=88.11,
        rotatable_bonds=1,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'CCCC#N': dict(
        heteroatom_count=1,
        n_heavy=5,
        mw=69.11,
        rotatable_bonds=1,
        tpsa=23.79,
        n_double_o=0,
        n_single_o=0,
        n_n=1,
        donor_atoms='N',
        donor_count=1,
    ),
    'CCCCOP(=O)(OCCCC)OCCCC': dict(
        heteroatom_count=5,
        n_heavy=17,
        mw=266.32,
        rotatable_bonds=12,
        tpsa=44.76,
        n_double_o=1,
        n_single_o=3,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=4,
    ),
    'CCCOC(=O)OC': dict(
        heteroatom_count=3,
        n_heavy=8,
        mw=118.13,
        rotatable_bonds=2,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'CCOC(=O)OC': dict(
        heteroatom_count=3,
        n_heavy=7,
        mw=104.1,
        rotatable_bonds=1,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'CCOC(=O)OCC': dict(
        heteroatom_count=3,
        n_heavy=8,
        mw=118.13,
        rotatable_bonds=2,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'CCOC(C)=O': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=88.11,
        rotatable_bonds=1,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'CCOC=O': dict(
        heteroatom_count=2,
        n_heavy=5,
        mw=74.08,
        rotatable_bonds=2,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'CCOCC': dict(
        heteroatom_count=1,
        n_heavy=5,
        mw=74.12,
        rotatable_bonds=2,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'CCOCCOCC': dict(
        heteroatom_count=2,
        n_heavy=8,
        mw=118.18,
        rotatable_bonds=5,
        tpsa=18.46,
        n_double_o=0,
        n_single_o=2,
        n_n=0,
        donor_atoms='O-',
        donor_count=2,
    ),
    'CCOP(=O)(OCC)OCC': dict(
        heteroatom_count=5,
        n_heavy=11,
        mw=182.16,
        rotatable_bonds=6,
        tpsa=44.76,
        n_double_o=1,
        n_single_o=3,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=4,
    ),
    'CCS(=O)CC': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=106.19,
        rotatable_bonds=2,
        tpsa=17.07,
        n_double_o=1,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=1,
    ),
    'CCS(C)(=O)=O': dict(
        heteroatom_count=3,
        n_heavy=6,
        mw=108.16,
        rotatable_bonds=1,
        tpsa=34.14,
        n_double_o=2,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=2,
    ),
    'COC(=O)OC': dict(
        heteroatom_count=3,
        n_heavy=6,
        mw=90.08,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'COC(C)=O': dict(
        heteroatom_count=2,
        n_heavy=5,
        mw=74.08,
        rotatable_bonds=0,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'COC(F)(F)C(F)(F)C(F)(F)C(F)(F)F': dict(
        heteroatom_count=10,
        n_heavy=15,
        mw=250.06,
        rotatable_bonds=3,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'COCCC#N': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=85.11,
        rotatable_bonds=2,
        tpsa=33.02,
        n_double_o=0,
        n_single_o=1,
        n_n=1,
        donor_atoms='O-;N',
        donor_count=2,
    ),
    'COCCOC': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=90.12,
        rotatable_bonds=3,
        tpsa=18.46,
        n_double_o=0,
        n_single_o=2,
        n_n=0,
        donor_atoms='O-',
        donor_count=2,
    ),
    'COCCOCCOC': dict(
        heteroatom_count=3,
        n_heavy=9,
        mw=134.18,
        rotatable_bonds=6,
        tpsa=27.69,
        n_double_o=0,
        n_single_o=3,
        n_n=0,
        donor_atoms='O-',
        donor_count=3,
    ),
    'COCCOCCOCCOC': dict(
        heteroatom_count=4,
        n_heavy=12,
        mw=178.23,
        rotatable_bonds=9,
        tpsa=36.92,
        n_double_o=0,
        n_single_o=4,
        n_n=0,
        donor_atoms='O-',
        donor_count=4,
    ),
    'COCCOCCOCCOCCOC': dict(
        heteroatom_count=5,
        n_heavy=15,
        mw=222.28,
        rotatable_bonds=12,
        tpsa=46.15,
        n_double_o=0,
        n_single_o=5,
        n_n=0,
        donor_atoms='O-',
        donor_count=5,
    ),
    'COCOC': dict(
        heteroatom_count=2,
        n_heavy=5,
        mw=76.09,
        rotatable_bonds=2,
        tpsa=18.46,
        n_double_o=0,
        n_single_o=2,
        n_n=0,
        donor_atoms='O-',
        donor_count=2,
    ),
    'COP(=O)(OC)OC': dict(
        heteroatom_count=5,
        n_heavy=8,
        mw=140.07,
        rotatable_bonds=3,
        tpsa=44.76,
        n_double_o=1,
        n_single_o=3,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=4,
    ),
    'CS(C)(=O)=O': dict(
        heteroatom_count=3,
        n_heavy=5,
        mw=94.13,
        rotatable_bonds=0,
        tpsa=34.14,
        n_double_o=2,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=2,
    ),
    'CS(C)=O': dict(
        heteroatom_count=2,
        n_heavy=4,
        mw=78.14,
        rotatable_bonds=0,
        tpsa=17.07,
        n_double_o=1,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=1,
    ),
    'C[Si](C)(C)O[Si](C)(C)C': dict(
        heteroatom_count=3,
        n_heavy=9,
        mw=162.38,
        rotatable_bonds=2,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'C[Si](C)(C)O[Si](C)(C)O[Si](C)(C)C': dict(
        heteroatom_count=5,
        n_heavy=13,
        mw=236.54,
        rotatable_bonds=4,
        tpsa=18.46,
        n_double_o=0,
        n_single_o=2,
        n_n=0,
        donor_atoms='O-',
        donor_count=2,
    ),
    'FC(F)(F)C1COC(=O)O1': dict(
        heteroatom_count=6,
        n_heavy=10,
        mw=156.06,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'FC(F)(F)COC(=O)OC': dict(
        heteroatom_count=6,
        n_heavy=10,
        mw=158.07,
        rotatable_bonds=1,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'FC(F)(F)COCC(F)(F)F': dict(
        heteroatom_count=7,
        n_heavy=11,
        mw=182.06,
        rotatable_bonds=2,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'FC(F)(F)COP(=O)(OCC(F)(F)F)OCC(F)(F)F': dict(
        heteroatom_count=14,
        n_heavy=20,
        mw=344.07,
        rotatable_bonds=6,
        tpsa=44.76,
        n_double_o=1,
        n_single_o=3,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=4,
    ),
    'FC(F)C(F)(F)OCC(F)(F)F': dict(
        heteroatom_count=8,
        n_heavy=12,
        mw=200.05,
        rotatable_bonds=3,
        tpsa=9.23,
        n_double_o=0,
        n_single_o=1,
        n_n=0,
        donor_atoms='O-',
        donor_count=1,
    ),
    'N#CCC#N': dict(
        heteroatom_count=2,
        n_heavy=5,
        mw=66.06,
        rotatable_bonds=0,
        tpsa=47.58,
        n_double_o=0,
        n_single_o=0,
        n_n=2,
        donor_atoms='N',
        donor_count=2,
    ),
    'N#CCCC#N': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=80.09,
        rotatable_bonds=1,
        tpsa=47.58,
        n_double_o=0,
        n_single_o=0,
        n_n=2,
        donor_atoms='N',
        donor_count=2,
    ),
    'N#CCCCCC#N': dict(
        heteroatom_count=2,
        n_heavy=8,
        mw=108.14,
        rotatable_bonds=3,
        tpsa=47.58,
        n_double_o=0,
        n_single_o=0,
        n_n=2,
        donor_atoms='N',
        donor_count=2,
    ),
    'O=C(Oc1ccccc1)Oc1ccccc1': dict(
        heteroatom_count=3,
        n_heavy=16,
        mw=214.22,
        rotatable_bonds=2,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'O=C1CCCCO1': dict(
        heteroatom_count=2,
        n_heavy=7,
        mw=100.12,
        rotatable_bonds=0,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'O=C1CCCO1': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=86.09,
        rotatable_bonds=0,
        tpsa=26.3,
        n_double_o=1,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=2,
    ),
    'O=C1OC=CO1': dict(
        heteroatom_count=3,
        n_heavy=6,
        mw=86.05,
        rotatable_bonds=0,
        tpsa=43.35,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'O=C1OCC(Cl)O1': dict(
        heteroatom_count=4,
        n_heavy=7,
        mw=122.51,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'O=C1OCC(F)O1': dict(
        heteroatom_count=4,
        n_heavy=7,
        mw=106.05,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'O=C1OCCCO1': dict(
        heteroatom_count=3,
        n_heavy=7,
        mw=102.09,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'O=S1(=O)CC=CC1': dict(
        heteroatom_count=3,
        n_heavy=7,
        mw=118.16,
        rotatable_bonds=0,
        tpsa=34.14,
        n_double_o=2,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=2,
    ),
    'O=S1(=O)CCCC1': dict(
        heteroatom_count=3,
        n_heavy=7,
        mw=120.17,
        rotatable_bonds=0,
        tpsa=34.14,
        n_double_o=2,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=2,
    ),
    'O=S1(=O)CCCO1': dict(
        heteroatom_count=4,
        n_heavy=7,
        mw=122.14,
        rotatable_bonds=0,
        tpsa=43.37,
        n_double_o=2,
        n_single_o=1,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
    'O=S1CCCC1': dict(
        heteroatom_count=2,
        n_heavy=6,
        mw=104.17,
        rotatable_bonds=0,
        tpsa=17.07,
        n_double_o=1,
        n_single_o=0,
        n_n=0,
        donor_atoms='O=',
        donor_count=1,
    ),
    'O=S1OCCO1': dict(
        heteroatom_count=4,
        n_heavy=6,
        mw=108.12,
        rotatable_bonds=0,
        tpsa=35.53,
        n_double_o=1,
        n_single_o=2,
        n_n=0,
        donor_atoms='O=;O-',
        donor_count=3,
    ),
}
# --- END GENERATED FALLBACK DESCRIPTORS ---


# ---------------------------------------------------------------------------
# descriptor computation
# ---------------------------------------------------------------------------
def _import_rdkit():
    """Return a small dict of rdkit handles, or None when rdkit is missing."""
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import Descriptors

        RDLogger.DisableLog("rdApp.*")
        return {"Chem": Chem, "Descriptors": Descriptors}
    except Exception:  # pragma: no cover - exercised only without rdkit
        return None


def _donor_labels_from_counts(n_double_o, n_single_o, n_n):
    labels = []
    if n_double_o:
        labels.append("O=")
    if n_single_o:
        labels.append("O-")
    if n_n:
        labels.append("N")
    return ";".join(labels), n_double_o + n_single_o + n_n


def descriptors_from_rdkit(rd, smiles):
    """Compute the descriptor block for one SMILES; raises on unparseable input."""
    Chem = rd["Chem"]
    Descriptors = rd["Descriptors"]
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("SMILES does not parse: %r" % smiles)
    if "." in Chem.MolToSmiles(mol):
        raise ValueError("unexpected multi-fragment SMILES: %r" % smiles)

    n_double_o = n_single_o = n_n = 0
    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        if symbol == "N":
            n_n += 1
        elif symbol == "O":
            if any(b.GetBondType() == Chem.BondType.DOUBLE for b in atom.GetBonds()):
                n_double_o += 1
            else:
                n_single_o += 1

    donor_atoms, donor_count = _donor_labels_from_counts(n_double_o, n_single_o, n_n)
    return {
        "heteroatom_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() != "C"),
        "n_heavy": mol.GetNumHeavyAtoms(),
        "mw": round(float(Descriptors.MolWt(mol)), 2),
        "rotatable_bonds": int(Descriptors.NumRotatableBonds(mol)),
        "tpsa": round(float(Descriptors.TPSA(mol)), 2),
        "n_double_o": n_double_o,
        "n_single_o": n_single_o,
        "n_n": n_n,
        "donor_atoms": donor_atoms,
        "donor_count": donor_count,
    }


def descriptors_from_fallback(smiles):
    """Static descriptor block, used when rdkit is unavailable."""
    try:
        entry = FALLBACK_DESCRIPTORS[smiles]
    except KeyError:
        raise KeyError(
            "no static descriptors for %r; the fallback table must cover every "
            "authored SMILES (regenerate with --dump-fallback)" % smiles
        )
    out = dict(entry)
    donor_atoms, donor_count = _donor_labels_from_counts(
        out.pop("n_double_o"), out.pop("n_single_o"), out.pop("n_n")
    )
    out["donor_atoms"] = donor_atoms
    out["donor_count"] = donor_count
    return out


def build_rows(definitions, rd, descriptor_key):
    """Build the ordered list of CSV rows for one structure table."""
    rows = []
    seen = set()
    for definition in definitions:
        mol_id = definition["mol_id"]
        if mol_id in seen:
            raise ValueError("duplicate mol_id: %s" % mol_id)
        seen.add(mol_id)
        smiles = definition["smiles"]
        if rd is not None:
            desc = descriptors_from_rdkit(rd, smiles)
        else:
            desc = descriptors_from_fallback(smiles)
        rows.append({
            "mol_id": mol_id,
            "name": definition["name"],
            "smiles": smiles,
            "family": definition["family"],
            "role": definition["role"],
            "donor_atoms": desc["donor_atoms"],
            "donor_count": str(desc["donor_count"]),
            "heteroatom_count": str(desc["heteroatom_count"]),
            "n_heavy": str(desc["n_heavy"]),
            "mw": "%.2f" % desc["mw"],
            "rotatable_bonds": str(desc["rotatable_bonds"]),
            "tpsa": "%.2f" % desc["tpsa"],
            "functionalization_tags": definition["tags"],
            descriptor_key: definition[descriptor_key],
        })
    return rows


def render_csv(columns, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def build_all(rd):
    return {
        CORE_CSV: render_csv(CORE_COLUMNS, build_rows(CORE_SET, rd, "reason_included")),
        BROAD_CSV: render_csv(BROAD_COLUMNS, build_rows(BROAD_POOL, rd, "pool_reason")),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _report_diff(label, path, expected, actual):
    print("[FAIL] %s (%s) differs from the rebuilt table" % (label, path))
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    shown = 0
    for index in range(max(len(expected_lines), len(actual_lines))):
        want = expected_lines[index] if index < len(expected_lines) else "<missing>"
        got = actual_lines[index] if index < len(actual_lines) else "<missing>"
        if want != got and shown < 10:
            print("  line %d" % (index + 1))
            print("    expected: %s" % want)
            print("    found   : %s" % got)
            shown += 1


def cmd_check(rd):
    ok = True
    for path, rendered in build_all(rd).items():
        if not path.exists():
            print("[FAIL] %s is missing (%s)" % (path.name, path))
            ok = False
            continue
        on_disk = path.read_bytes().decode("utf-8")
        if on_disk == rendered:
            print("[ OK ] %s matches the rebuilt table" % path.name)
        else:
            _report_diff(path.name, path, rendered, on_disk)
            ok = False
    return 0 if ok else 1


def cmd_write(rd):
    for path, rendered in build_all(rd).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(rendered.encode("utf-8"))
        print("wrote %s (%d data rows)" % (path, len(rendered.splitlines()) - 1))
    return 0


def cmd_summary(rd):
    for path, rendered in build_all(rd).items():
        rows = list(csv.DictReader(io.StringIO(rendered)))
        families = {}
        for row in rows:
            families[row["family"]] = families.get(row["family"], 0) + 1
        print("%s: %d rows" % (path.name, len(rows)))
        for family in sorted(families):
            print("  %-18s %d" % (family, families[family]))
    return 0


def cmd_dump_fallback(rd):
    if rd is None:
        print("ERROR: --dump-fallback requires rdkit", file=sys.stderr)
        return 2
    entries = {}
    for definition in CORE_SET + BROAD_POOL:
        entries[definition["smiles"]] = descriptors_from_rdkit(rd, definition["smiles"])
    print("FALLBACK_DESCRIPTORS: dict = {")
    for smiles in sorted(entries):
        desc = entries[smiles]
        print("    %r: dict(" % smiles)
        for key in ("heteroatom_count", "n_heavy", "mw", "rotatable_bonds", "tpsa",
                    "n_double_o", "n_single_o", "n_n", "donor_atoms", "donor_count"):
            print("        %s=%r," % (key, desc[key]))
        print("    ),")
    print("}")
    return 0


def _configure_stdio():
    """Make stdout/stderr UTF-8 so Chinese diff output never crashes on a GBK console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass

def main(argv=None):
    _configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="do not write; compare existing CSVs with the rebuilt tables")
    parser.add_argument("--no-rdkit", action="store_true",
                        help="force the static fallback descriptor path (CI without rdkit)")
    parser.add_argument("--summary", action="store_true",
                        help="also print row counts per chemical family")
    parser.add_argument("--dump-fallback", action="store_true",
                        help="print the generated FALLBACK_DESCRIPTORS literal and exit")
    args = parser.parse_args(argv)

    rd = None if args.no_rdkit else _import_rdkit()
    if args.no_rdkit:
        print("[INFO] --no-rdkit: using static fallback descriptors", file=sys.stderr)
    elif rd is None:
        print("[WARN] rdkit not importable - using static fallback descriptors", file=sys.stderr)

    if args.dump_fallback:
        return cmd_dump_fallback(rd)
    if args.check:
        return cmd_check(rd)
    if args.summary:
        cmd_write(rd)
        return cmd_summary(rd)
    return cmd_write(rd)


if __name__ == "__main__":
    raise SystemExit(main())
