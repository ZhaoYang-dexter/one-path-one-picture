"""Rebuild the timing inputs for the routed Nangate45 gcd from OpenROAD test data.

  python3 designs/gcd_nangate45/build.py /path/to/OpenROAD
Writes gcd_from_def.v (netlist from DEF connectivity) and wire_load.tcl (per-net wire cap from the
routed length on each layer times OpenROAD's Nangate45 layer capacitance).
"""
import pathlib, sys, re
here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[1]))
from stapath.defparse import read_def, read_lef_sizes, read_layer_rc, wire_length_by_layer, to_verilog, safe_net_name

orroot = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
lef = (orroot / "test/Nangate45/Nangate45.lef").read_text() if orroot else ""
d = read_def((here / "gcd_nangate45_route.def").read_text(), read_lef_sizes(lef) if lef else None)
(here / "gcd_from_def.v").write_text(to_verilog(d))
rc = read_layer_rc((here / "Nangate45.rc").read_text())
port_nets = {p.net for p in d.pins.values()}
out = ["# wire cap per net (fF) = routed length per layer x Nangate45 layer capacitance from Nangate45.rc"]
for n in d.nets.values():
    c = sum(l * rc[k][1] for k, l in wire_length_by_layer(n).items() if k in rc)
    if c > 0:
        name = n.name if n.name in port_nets else safe_net_name(n.name)
        out.append(f"set_load {c:.4f} [get_nets {{{name}}}]")
(here / "wire_load.tcl").write_text("\n".join(out) + "\n")
print("nets with wire load:", len(out) - 1)
