# Per-tap STA components of a routed tap_top checkpoint (both corners), for the offset model:
#   vivado -mode batch -source report_taps_detail.tcl -tclargs <routed.dcp> <out.csv>
# For each tap, sensor flop (FF1/FF2) and corner: slack, requirement, clock uncertainty, clock
# pessimism removal (CPR), skew, data-path delay and clock delays of the worst setup path from the
# stimulus registers. The offset that silicon should show is
#   Delta_si = (s2 + U2 - CPR2) - (s1 + U1 - CPR1)
# i.e. the STA slack difference without the analysis-only uncertainty and pessimism terms.
lassign $argv dcp out
open_checkpoint $dcp
set fh [open $out w]
puts $fh "tap,corner,ff,slack,requirement,uncertainty,pessimism,skew,datapath,start_clk,end_clk"
set srcs [get_cells -hier -filter {NAME =~ u_chain/op_*_reg* && IS_SEQUENTIAL}]
foreach corner {Slow Fast} {
  if {$corner eq "Slow"} {
    config_timing_corners -corner Slow -delay_type min_max; config_timing_corners -corner Fast -delay_type none
  } else {
    config_timing_corners -corner Slow -delay_type none; config_timing_corners -corner Fast -delay_type min_max
  }
  for {set j 0} {$j < 23} {incr j} {
    foreach ff {FF1 FF2} {
      set p [get_timing_paths -setup -from $srcs -to [get_pins "g_tap\[$j\].u_sens/$ff/D"] -max_paths 1]
      puts $fh [join [list $j $corner $ff [get_property SLACK $p] [get_property REQUIREMENT $p] \
        [get_property UNCERTAINTY $p] [get_property CLOCK_PESSIMISM $p] [get_property SKEW $p] \
        [get_property DATAPATH_DELAY $p] [get_property STARTPOINT_CLOCK_DELAY $p] \
        [get_property ENDPOINT_CLOCK_DELAY $p]] ,]
    }
  }
}
close $fh
puts "DETAIL written $out"
