# report_taps: per-tap static timing of the routed tap_top (both corners).
#
# For every tap j and both sensor flops (FF1 on clk_phase, FF2 on clk_sys) it reports the worst
# setup path from the stimulus registers: data-path delay and slack. The chain paths carry a
# set_max_delay target (tap_impl.tcl), so the slack is converted back to the clock:
#   slack_clk = slack + (relationship - requirement)
# with the relationship taken from the same path's clocks (10 ns to FF2; 10 ns + PHASE to FF1).
# delta = slack_clk(FF2) - slack_clk(FF1) is the predicted warning band (FF1 ahead of FF2).
# pred_steps = slack_clk(FF1) / step is the reading predicted by that corner.
proc tap_path {pin} {
  set srcs [get_cells -hier -filter {NAME =~ u_chain/op_*_reg* && IS_SEQUENTIAL}]
  set p [get_timing_paths -setup -from $srcs -to [get_pins $pin] -max_paths 1 -nworst 1]
  if {[llength $p] == 0} { return [list NA NA NA NA] }
  set req   [get_property REQUIREMENT $p]
  set slack [get_property SLACK $p]
  set dly   [get_property DATAPATH_DELAY $p]
  set ckp   [get_property ENDPOINT_CLOCK $p]
  # setup relationship to this clock at phase 0 of the sweep
  set period 10.0
  set wf [get_property WAVEFORM [get_clocks $ckp]]
  set rise [lindex $wf 0]
  set rel [expr {$rise > 0 ? $rise : $period + $rise}]
  if {$rel <= 0} { set rel [expr {$rel + $period}] }
  set sclk [expr {$slack + ($rel - $req)}]
  return [list $dly $slack $sclk $rel]
}

proc report_taps {csv} {
  set step [expr {1.0 / 56.0}]
  set stages $::tap_stage_list
  set fh [open $csv w]
  puts $fh "tap,stage,corner,ff2_delay_ns,ff1_delay_ns,ff2_slack_clk_ns,ff1_slack_clk_ns,delta_ns,pred_steps,ff1_rel_ns"
  foreach corner {Slow Fast} {
    if {$corner eq "Slow"} {
      config_timing_corners -corner Slow -delay_type min_max
      config_timing_corners -corner Fast -delay_type none
    } else {
      config_timing_corners -corner Slow -delay_type none
      config_timing_corners -corner Fast -delay_type min_max
    }
    for {set j 0} {$j < [llength $stages]} {incr j} {
      lassign [tap_path "g_tap\[$j\].u_sens/FF2/D"] d2 s2 c2 r2
      lassign [tap_path "g_tap\[$j\].u_sens/FF1/D"] d1 s1 c1 r1
      if {$c2 eq "NA" || $c1 eq "NA"} {
        puts $fh "$j,[lindex $stages $j],$corner,NA,NA,NA,NA,NA,NA,NA"
        continue
      }
      set delta [expr {$c2 - $c1}]
      set pred  [expr {$c1 / $step}]
      puts $fh [format "%d,%d,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.1f,%.3f" $j [lindex $stages $j] $corner \
                  $d2 $d1 $c2 $c1 $delta $pred $r1]
    }
  }
  config_timing_corners -corner Slow -delay_type min_max
  config_timing_corners -corner Fast -delay_type min_max
  close $fh
  puts "TAPSTA written $csv"
}
