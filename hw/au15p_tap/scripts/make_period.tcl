# Same routed design with a longer clock period: only the MMCM output dividers change. The VCO stays
# at 1 GHz, so the fine phase step stays 1/(56 f_VCO) = 17.857 ps, and placement and routing are those
# of the input checkpoint. FF1 and the system clock stay at 0 deg; the catcher keeps its distance in
# time after the system clock (1.75 ns = 14 settings of 125 ps), since its phase must be a multiple
# of 45 deg / DIVIDE (DRC AVAL-168: 63 deg is valid only at DIVIDE 10).
# With T = DIVIDE ns the failure boundary moves to longer taps, so the taps that already fail at the
# top of the 10 ns shmoo (S94-S150) cross failure inside the voltage range.
#   vivado -mode batch -source make_period.tcl -tclargs <routed.dcp> <out_dir> <divide>
# then the per-tap STA components for the offset model:
#   vivado -mode batch -source report_taps_detail.tcl -tclargs <out_dir>/tap_top_routed.dcp <out_dir>/taps_sta_detail.csv
lassign $argv dcp out div
if {$div eq "" || $div < 10 || $div > 20} { error "divide must be 10..20 (period in ns at f_VCO = 1 GHz)" }
file mkdir $out
open_checkpoint $dcp
set m [get_cells u_clocks/u_mmcm]
if {[get_property CLKOUT1_PHASE $m] != 0 || [get_property CLKOUT2_PHASE $m] != 0} {
  error "use a checkpoint without guard (CLKOUT1/2_PHASE must be 0)"
}
set div0 [get_property CLKOUT0_DIVIDE_F $m]
set catch_ns [expr {[get_property CLKOUT0_PHASE $m] / 360.0 * $div0}]
set grid [expr {45.0 / $div}]
set catch_deg [expr {round($catch_ns * 360.0 / $div / $grid) * $grid}]
set_property CLKOUT0_DIVIDE_F $div $m
set_property CLKOUT0_PHASE    $catch_deg $m
set_property CLKOUT1_DIVIDE   $div $m
set_property CLKOUT2_DIVIDE   $div $m
puts "PERIOD catcher [format %.3f $catch_ns] ns after the system clock: CLKOUT0_PHASE $catch_deg deg"
puts "PERIOD MMCM CLKFBOUT_MULT_F=[get_property CLKFBOUT_MULT_F $m] DIVIDE=$div ->\
 catch [get_property CLKOUT0_DIVIDE_F $m] phase [get_property CLKOUT1_DIVIDE $m] sys [get_property CLKOUT2_DIVIDE $m]"
foreach pin {CLKOUT0 CLKOUT1 CLKOUT2} {
  set c [get_clocks -of_objects [get_pins u_clocks/u_mmcm/$pin]]
  puts "PERIOD $pin $c period [get_property PERIOD $c] waveform [get_property WAVEFORM $c]"
}
report_timing_summary -max_paths 10 -file $out/timing_summary.rpt
report_drc -file $out/drc.rpt
foreach {from to kind} {FF2 FF3 setup FF1 FF3 setup FF1 FF3 hold} {
  set p [get_timing_paths -from [get_cells g_tap[12].u_sens/$from] -to [get_cells g_tap[12].u_sens/$to] -$kind]
  puts "PERIOD $from->$to $kind slack [get_property SLACK $p]"
}
write_checkpoint -force $out/tap_top_routed.dcp
write_bitstream -force $out/tap_top.bit
write_debug_probes -force $out/tap_top.ltx
puts "PERIOD done: $out/tap_top.bit"
