# figure_manifest_week16_stage17

| figure | sha256 | size |
| --- | --- | --- |
| `F32_stage17_contamination.png` | `3ed91df76ccdb562637605bb19d4a23369b216d2b3736d7d5150b9979ea15da8` | 258938 B |
| `F33_stage17_solution_identity.png` | `700b1bf53a2bf607fcf3fd27461b67c2b978b08f4282ef440deb696adc97f2c0` | 342191 B |

| input | sha256 |
| --- | --- |
| `outputs/week16/stage17_contamination.json` | `8797127552338efbb73e74b385a51930dec5fa41531f796b2f1cc9b77f170ebe` |
| `outputs/week16/stage17_contamination_cells.csv` | `9ee054fe7cc8ab10fa1299e266802104aaf6db1a6aa87b1c3578ffbfd479eb87` |
| `outputs/week16/stage17_contamination_ladder.csv` | `ff87ab5fc2717b5bf845111a8acdd39ff71b8d435b1ac53af1724d875b2d3cde` |
| `outputs/week16/stage17_solution_identity.json` | `22366dddfaf53c7330339bb0d75496e8c706f9f72d7b35fb3b04771a8bb6b8fd` |
| `outputs/week16/stage17_solution_identity.csv` | `2998f710f09e5a3322ab11032f8f665dfb79799f798151c7e4cc7243b85ad32e` |
| `outputs/week4/orca_cpcm_10/PC/PC_anion_cpcm_10.out` | `836587e9717003a28ff0d61ffa5190d110b9e1168c4db9e8de8dc7235f7161c3` |
| `outputs/week15/orca_moread_cpcm_10/PC/PC_anion_moread_cpcm_10.out` | `c967b330a235f149aad912c0fb4206034ac1168b28e9a71cb85ad722c08b66ef` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage17_figure.py
& $py scripts\make_stage17_figure.py --check
```

## F32 -- `F32_stage17_contamination.png`

### (a) contamination bound, per molecule and axis

`delta = p2_moread - p2_default` over 18 molecules x 2 axes. The reference band is the material threshold 1e-03 eV. Worst |delta| = 0.1562 eV (TEGDME/anion), the largest departure in the 'worse-with-the-restart' sense. The only large positive departure (restart higher than the default) is EC/anion at +0.0923 eV.

### (b) ranking-stability control

- oxidation / default: tau_b = 0.8954, 95% CI [0.7143, 1.0000]
- oxidation / moread: tau_b = 0.9216, 95% CI [0.7738, 1.0000]
- reduction / default: tau_b = 0.6732, 95% CI [0.4035, 0.8733]
- reduction / moread: tau_b = 0.6732, 95% CI [0.4126, 0.8710]
- CI overlap: oxidation = True, reduction = True

### (c) decision quantities, default vs moread

- oxidation: O_20% 0.7500 -> 0.7500, f_unresolved(after) 0.1111 -> 0.1111, f_robust_inv 0.0000 -> 0.0000, sigma median 0.1984 -> 0.1885 eV
- reduction: O_20% 0.5000 -> 0.5000, f_unresolved(after) 0.2222 -> 0.2549, f_robust_inv 0.0000 -> 0.0000, sigma median 0.2168 -> 0.2261 eV
- verdict from the analysis: any published conclusion rewritten = False
- cells with a paired shift above the threshold: 6 (TEGDME/anion -0.1562, TMP/cation -0.1340, PC/anion -0.1183, EC/anion +0.0923, DEC/anion -0.0752, DEC/cation +0.0014)

## F33 -- `F33_stage17_solution_identity.png`

### (d) representative per-atom spin profile (PC / anion / cpcm_10)

Both arms peak on the same atom C4: default 1.4798, moread 1.4672 Mulliken spin. Delta<S**2> = -0.000240, geometry identical = True, spin centre identical = True.

### (e) localisation shift across all 32 cells

- cyclic_carbonate (n = 15): mean loss_in_pr = -0.5025 (PR_moread - PR_default)
- linear_carbonate (n = 7): mean loss_in_pr = +0.4034 (PR_moread - PR_default)
- phosphate (n = 10): mean loss_in_pr = -0.2215 (PR_moread - PR_default)

### (f) spin purity

- Delta<S**2> over the 32 cells spans [-0.004534, +0.001457]; the reference is the pure doublet 0.75.

### (g) charge vs spin reorganisation

- cyclic_carbonate: charge_l1 mean 0.67, spin_l1 mean 0.66
- linear_carbonate: charge_l1 mean 2.59, spin_l1 mean 2.00
- phosphate: charge_l1 mean 0.33, spin_l1 mean 0.67

Palette and dpi follow the other week figures (dpi = 170, bbox_inches = tight). All labels are ASCII because the workspace has no guaranteed CJK font.
