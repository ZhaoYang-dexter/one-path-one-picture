# Sources

| File | From | License |
|---|---|---|
| `gcd_nangate45_route.def` | OpenROAD, `src/odb/test/data/gcd/gcd_nangate45_route.def` | BSD-3-Clause (OpenROAD) |
| `Nangate45.lef`, `Nangate45.rc` | OpenROAD, `test/Nangate45/` | Nangate Open Cell Library terms, as shipped with OpenROAD |
| `nangate45_typ.lib.gz` (not copied) | OpenSTA, `examples/` | as shipped with OpenSTA |

Generated here:

- `gcd_from_def.v`: structural netlist rebuilt from the DEF's connectivity (`build.py`).
- `wire_load.tcl`: per-net wire capacitance = routed length on each metal layer × the layer
  capacitance in `Nangate45.rc`. No extracted parasitics exist for this design, so this is an estimate.
- `gcd.sdc`: 0.40 ns clock (tightened so the critical paths fail), propagated clock through the real clock tree.
