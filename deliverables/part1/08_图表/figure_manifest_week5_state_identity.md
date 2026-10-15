# Figure manifest - Stage 5 / T4 C1 state identity (F13)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F13 | `F13_c1_state_identity.png` | 4cee653dfc195e3909da08b1d3405c7bd429b40cdede29103c21ee80b26787ca | `c1_state_identity.json` b7672afcb48594c3e0950a70091a87ff340dae9e6131759ecfa96eeed96199d0 | `c1_li_coordination.csv` 33e1192b2b12e4dbbe1094618b5edc9a99365b813b676b9d807c5228e884b431 |
| | | | `li_motif_generation.json` 5a87805098a2cf4e884e9a79537e0a2a1ad227ea3ed45207258e92f29ea3de2f |

F13 note: the classification is read off the Mulliken charge/spin block that
every C1 ORCA job already wrote, so the figure costs no new quantum chemistry.
Panel (a) is the Mulliken projection of the singly occupied orbital onto Li,
used as the practical stand-in for the SOMO/LUMO localisation that
config/scientific_definitions.yaml requires; panel (b) is the same evidence
seen as a charge ladder. Both come from the relaxed redox geometry where the
state was re-optimised and from the gas-phase vertical single point otherwise.

- n (molecule, motif, redox state) determinations: 24
- oxidised [Li M]2+: molecule_centered_redox 8; no_intact_minimum_found 4
- reduced [Li M]0: Li_centered_or_mixed_redox 11; molecule_centered_redox 1
- frozen indicator thresholds: spin 0.15 / 0.5, charge 0.25 / 0.5
- lowest |spin on Li| among the 11 Li-centred reductions: 0.899

state_identity_label per (molecule, motif, redox state). Geometry outranks the electrons: a redox state whose optimised geometry lost the Li-M minimum is labelled no_intact_minimum_found, and one whose parent connectivity broke is labelled dissociated_optimized_product. Otherwise the label follows the redox electron: |Mulliken spin on Li| >= 0.5 or |dq(Li)| >= 0.5 eV/e means Li_centered_or_mixed_redox; |spin on Li| <= 0.15 and |dq(Li)| <= 0.25 means molecule_centered_redox; a disagreement between the two indicators (one places the electron on Li while the other places it on the molecule), and any reading that neither indicator resolves, means state_identity_ambiguous. Reference state is [Li M]+ at the same motif.

Labels are English on purpose (no guaranteed CJK font in the workspace).
