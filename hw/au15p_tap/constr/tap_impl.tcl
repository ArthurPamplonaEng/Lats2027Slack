# Implementation constraints of tap_top, applied to the synthesised netlist (sourced by build.tcl
# after synth_design, before opt_design).

# ----------------------------------------------------------------------------- clocks
set c_catch [get_clocks -of_objects [get_pins u_clocks/u_mmcm/CLKOUT0]]
set c_phase [get_clocks -of_objects [get_pins u_clocks/u_mmcm/CLKOUT1]]
set c_sys   [get_clocks -of_objects [get_pins u_clocks/u_mmcm/CLKOUT2]]
puts "TAPIMPL clocks: catch=$c_catch phase=$c_phase sys=$c_sys"

# The VIO and the debug hub run on the board oscillator (sys_clk). The only paths between it and
# the MMCM clocks are the VIO probes: w_* change once per window, mask/clear are synchronised.
set_clock_groups -asynchronous -group [get_clocks sys_clk] -group [list $c_catch $c_phase $c_sys]

# ----------------------------------------------------------------------------- tapped chain
# Every tap's path, from the stimulus registers to FF1 and FF2 of its sensor, gets a reachable
# target of 0.6 + 0.15 ns per stage (slow corner). The long taps exceed the 10 ns period on
# purpose; without a target the router would either chase an impossible requirement or, with a
# loose one, use slow LUT pins (the Nexys 4 lesson: ~45 % slower). Clock skew is kept in the
# analysis (no -datapath_only), so report_taps.tcl can convert the slack back to the clock.
set stages {}
foreach c [lsort -dictionary [get_cells -hier -filter {REF_NAME == LUT3 && NAME =~ u_chain/tp*.sum}]] {
  lappend stages $c
}
set srcs [get_cells -hier -filter {NAME =~ u_chain/op_*_reg* && IS_SEQUENTIAL}]
puts "TAPIMPL stimulus registers: [llength $srcs]"
set ::tap_stage_list {24 48 70 74 78 82 86 90 94 98 102 106 110 114 118 122 126 130 134 138 142 146 150}
for {set j 0} {$j < [llength $::tap_stage_list]} {incr j} {
  set S   [lindex $::tap_stage_list $j]
  set tgt [format %.3f [expr {0.6 + 0.15 * $S}]]
  set eps [get_pins [list "g_tap\[$j\].u_sens/FF1/D" "g_tap\[$j\].u_sens/FF2/D"]]
  if {[llength $eps] != 2} { error "tap $j: sensor D pins not found ($eps)" }
  set_max_delay $tgt -from $srcs -to $eps
}
puts "TAPIMPL max_delay set for [llength $::tap_stage_list] taps"

# ----------------------------------------------------------------------------- sensor catcher
# Vivado models the MMCM output phase as clock latency (all three waveforms are {0 5}), so by
# default it times FF1/FF2 -> XOR -> FF3 against the NEXT catcher edge and treats the intended
# same-cycle capture (catcher at CATCH_DEG after clk_sys) as a hold requirement, which the router
# then "fixes" by padding the XOR route past the catcher edge (5.3 ns on the first build). A setup
# multiplier of 0 restores the intent (setup to the same edge); the default hold edge then moves to
# the previous cycle by itself (adding "-hold -1" would pull it back onto the setup edge).
set ff3  [get_cells -hier -filter {NAME =~ g_tap*.u_sens/FF3}]
set ff12 [get_cells -hier -filter {NAME =~ g_tap*.u_sens/FF1 || NAME =~ g_tap*.u_sens/FF2}]
set_multicycle_path 0  -setup -from $ff12 -to $ff3
puts "TAPIMPL catcher exceptions on [llength $ff3] sensors"

# ----------------------------------------------------------------------------- placement
# Chain, sensors and checkers in one exclusive region inside a single clock region.
# TAP_PBLOCK selects the region (default: implementation A); a second implementation in another
# region gives different FF1/FF2 routing, i.e. an out-of-sample test of the STA offset prediction.
set pb_range [expr {[info exists ::env(TAP_PBLOCK)] ? $::env(TAP_PBLOCK) : "SLICE_X30Y65:SLICE_X45Y114"}]
create_pblock pb_cut
resize_pblock pb_cut -add $pb_range
add_cells_to_pblock pb_cut [get_cells u_chain]
add_cells_to_pblock pb_cut [get_cells -hier -filter {NAME =~ g_tap*.u_sens}]
add_cells_to_pblock pb_cut [get_cells -hier -filter {NAME =~ g_tap*.err_q*}]
set_property EXCLUDE_PLACEMENT 1 [get_pblocks pb_cut]
puts "TAPIMPL pblock $pb_range"
