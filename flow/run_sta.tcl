# Generate the reports used in this repo from OpenSTA's public gcd example (sky130hd, routed, with SPEF).
# Usage:  OPENSTA=/path/to/OpenSTA  sta -no_init -exit flow/run_sta.tcl
set ex $::env(OPENSTA)/examples
read_liberty $ex/sky130hd_tt.lib.gz
read_verilog $ex/gcd_sky130hd.v
link_design gcd
read_sdc     [file dirname [info script]]/gcd_4ns.sdc   ;# original example SDC with the clock tightened 5.0 -> 4.0 ns
read_spef    $ex/gcd_sky130hd.spef

report_wns
report_tns
# top 40 endpoints
report_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3 \
    -group_path_count 40 -endpoint_path_count 1 > reports/gcd_4ns_top40.rpt
# worst path from every startpoint (register clock pins and input ports)
set f [open reports/gcd_4ns_per_startpoint.rpt w]; close $f
foreach pin [all_registers -clock_pins] {
  report_checks -from $pin -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3 >> reports/gcd_4ns_per_startpoint.rpt
}
foreach port [all_inputs] {
  if {[get_full_name $port] == "clk"} continue
  report_checks -from $port -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3 >> reports/gcd_4ns_per_startpoint.rpt
}
