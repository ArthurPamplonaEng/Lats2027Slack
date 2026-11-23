# Implementation A' = implementation A with a designed guard band: the system clock (launch
# registers, FF2, checkers) is delayed by SYS_DEG with a static MMCM phase, so FF1 (on the swept
# output, which must stay at 0 deg) samples SYS_DEG earlier at phase step 0. Placement and routing
# are those of A (same routed checkpoint): only the MMCM attributes change. The catcher keeps its
# distance after the system clock.
#   vivado -mode batch -source make_guard.tcl -tclargs <routed.dcp> <out_dir> <sys_deg>
lassign $argv dcp out sys_deg
open_checkpoint $dcp
set m [get_cells u_clocks/u_mmcm]
set catch0 [get_property CLKOUT0_PHASE $m]
set_property CLKOUT2_PHASE $sys_deg $m
set_property CLKOUT0_PHASE [expr {$catch0 + $sys_deg}] $m
puts "GUARD MMCM CLKOUT0_PHASE=[get_property CLKOUT0_PHASE $m] CLKOUT1_PHASE=[get_property CLKOUT1_PHASE $m] CLKOUT2_PHASE=[get_property CLKOUT2_PHASE $m]"
report_timing_summary -max_paths 10 -file $out/timing_summary.rpt
source [file join [file dirname [info script]] report_taps.tcl]
set ::tap_stage_list {24 48 70 74 78 82 86 90 94 98 102 106 110 114 118 122 126 130 134 138 142 146 150}
report_taps $out/taps_sta.csv
set p [get_timing_paths -from [get_cells g_tap[12].u_sens/FF2] -to [get_cells g_tap[12].u_sens/FF3] -setup]
puts "GUARD FF2->FF3 setup slack [get_property SLACK $p]"
set p [get_timing_paths -from [get_cells g_tap[12].u_sens/FF1] -to [get_cells g_tap[12].u_sens/FF3] -setup]
puts "GUARD FF1->FF3 setup slack [get_property SLACK $p]"
set p [get_timing_paths -from [get_cells g_tap[12].u_sens/FF1] -to [get_cells g_tap[12].u_sens/FF3] -hold]
puts "GUARD FF1->FF3 hold slack [get_property SLACK $p]"
write_checkpoint -force $out/tap_top_routed.dcp
write_bitstream -force $out/tap_top.bit
write_debug_probes -force $out/tap_top.ltx
puts "GUARD done"
