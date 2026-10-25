# Time the routed Nangate45 gcd from OpenROAD's test data.
# Usage: OPENSTA=/path/to/OpenSTA sta -no_init -exit designs/gcd_nangate45/run_sta.tcl
set here [file dirname [info script]]
read_liberty $::env(OPENSTA)/examples/nangate45_typ.lib.gz
read_verilog $here/gcd_from_def.v
link_design gcd
read_sdc     $here/gcd.sdc
source       $here/wire_load.tcl
report_wns
report_tns
report_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3 > reports/gcd_nangate45_worst.rpt
report_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3 \
    -group_path_count 20 -endpoint_path_count 1 > reports/gcd_nangate45_top20.rpt
