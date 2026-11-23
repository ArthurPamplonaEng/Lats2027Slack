# Non-project build of tap_top for the RV02A board (xcau15p-ffvb676-1-i).
#   vivado -mode batch -source scripts/build.tcl -tclargs <out_dir> [jobs]
# Writes tap_top.bit / .ltx / _routed.dcp, timing and utilisation reports, and taps_sta.csv
# (per-tap STA, report_taps.tcl).
set ROOT [file normalize [file join [file dirname [info script]] ..]]
set OUT  [file normalize [expr {[llength $argv] > 0 ? [lindex $argv 0] : "$ROOT/build/impl"}]]
set JOBS [expr {[llength $argv] > 1 ? [lindex $argv 1] : 8}]
set PART xcau15p-ffvb676-1-i
file mkdir $OUT
set_param general.maxThreads $JOBS

create_project -in_memory -part $PART
set_property target_language Verilog [current_project]

# ---------------------------------------------------------------- VIO (23 x 128-bit in, 2 out)
set NIN 24
file mkdir $OUT/ip
create_ip -name vio -vendor xilinx.com -library ip -version 3.0 -module_name vio_tap -dir $OUT/ip
set props [list CONFIG.C_NUM_PROBE_IN $NIN CONFIG.C_NUM_PROBE_OUT 2 CONFIG.C_EN_PROBE_IN_ACTIVITY 0]
for {set i 0} {$i < $NIN} {incr i} { lappend props CONFIG.C_PROBE_IN${i}_WIDTH 128 }
lappend props CONFIG.C_PROBE_OUT0_WIDTH 23 CONFIG.C_PROBE_OUT0_INIT_VAL 0x7FFFFF
lappend props CONFIG.C_PROBE_OUT1_WIDTH 1  CONFIG.C_PROBE_OUT1_INIT_VAL 0x0
set_property -dict $props [get_ips vio_tap]
generate_target all [get_ips vio_tap]
synth_ip [get_ips vio_tap]

# ---------------------------------------------------------------- sources
read_verilog -sv [list \
  $ROOT/rtl/tap_pkg.sv $ROOT/rtl/tap_clocks.sv $ROOT/rtl/tap_chain.sv $ROOT/rtl/tap_sensor.sv \
  $ROOT/rtl/tap_sweep.sv $ROOT/rtl/tap_stats.sv $ROOT/rtl/tap_top.sv]
read_xdc $ROOT/constr/tap_pins.xdc

synth_design -top tap_top -part $PART -flatten_hierarchy rebuilt
write_checkpoint -force $OUT/tap_top_synth.dcp
report_utilization -file $OUT/utilization_synth.rpt

source $ROOT/constr/tap_impl.tcl

opt_design
place_design
route_design
write_checkpoint -force $OUT/tap_top_routed.dcp
report_timing_summary -max_paths 20 -report_unconstrained -file $OUT/timing_summary.rpt
report_utilization -file $OUT/utilization.rpt
report_clock_utilization -file $OUT/clock_utilization.rpt
report_drc -file $OUT/drc.rpt
report_methodology -file $OUT/methodology.rpt

source $ROOT/scripts/report_taps.tcl
report_taps $OUT/taps_sta.csv

write_bitstream -force $OUT/tap_top.bit
write_debug_probes -force $OUT/tap_top.ltx
puts "TAPBUILD done: $OUT/tap_top.bit"
