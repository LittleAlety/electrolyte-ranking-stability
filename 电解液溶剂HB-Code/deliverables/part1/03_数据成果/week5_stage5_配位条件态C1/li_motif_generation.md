# Stage 5 / T4 step 1 -- Li+ motif generation (frozen rule replay)

Rule source: config/scientific_definitions.yaml conformers_and_states.li_motif_generation (frozen: true, do not edit).

| mol | family | donors | candidates | kept | motifs (donor atoms, rel kJ/mol) | rule check |
| --- | --- | --- | --- | --- | --- | --- |
| C04 EC | cyclic_carbonate | 3 | 6 | 1 | m1: 4 (0.00) | elements_match |
| C01 DMC | linear_carbonate | 3 | 6 | 2 | m2: 1;4 (24.62); m1: 3 (0.00) | elements_match |
| C08 DME | ether | 2 | 5 | 1 | m1: 1;4 (0.00) | elements_match |
| C09 DOL | ether | 2 | 3 | 1 | m1: 2;4 (0.00) | elements_match |
| C13 GBL | ester | 2 | 4 | 1 | m1: 0 (0.00) | elements_match |
| C14 SL | sulfone | 2 | 5 | 1 | m1: 0;2 (0.00) | elements_match |
| C15 DMSO | sulfoxide | 1 | 3 | 1 | m1: 3 (0.00) | elements_match |
| C16 AN | nitrile | 1 | 1 | 1 | m1: 2 (0.00) | elements_match |
| C18 SN | nitrile | 2 | 3 | 1 | m1: 0;5 (0.00) | elements_match |
| C17 TMP | phosphate | 4 | 10 | 2 | m2: 1;4;6 (14.74); m1: 3 (0.00) | elements_match |

Every candidate above is a row of outputs/week5/li_motif_generation.csv, including the ones that were dropped: dedup_reason records why.
