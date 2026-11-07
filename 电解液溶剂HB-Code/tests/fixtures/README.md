# Fixtures

A real engine output, kept verbatim so the parsers are calibrated against the
software that will actually run, not only against hand-written samples.

## xtb_6.7.1_ec_opt.out

- engine: xtb 6.7.1pre (5071a88), Windows x86_64 build
- command: `xtb EC.xyz --opt --gfn 2 --chrg 0 --uhf 0`
- system: ethylene carbonate (EC), geometry from RDKit ETKDG + MMFF
- produced by: `scripts/run_xtb_job.py --name EC --smiles "C1COC(=O)O1"`
- why it is here: the first hand-written sample assumed a `(HOMO) = <Eh> <eV>`
  layout, while 6.7.1 marks the eV column of the orbital table instead; that
  mismatch left `homo_ev` at `None` until this file was checked in.
