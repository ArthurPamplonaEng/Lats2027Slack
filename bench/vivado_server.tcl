# Vivado hardware-manager procedures for the tap bench, sourced by a persistent
#   vivado -mode tcl -nolog -nojournal -source bench/vivado_server.tcl
# The Python side (bench/tapbench.py) writes one command per line on stdin and waits for a line
# that starts with TAPOK, TAPDATA or TAPERR. Nothing here writes the configuration flash.

proc _reply {tag msg} { puts "$tag $msg"; flush stdout }

proc tap_connect {} {
  if {[catch {
    open_hw_manager
    connect_hw_server -allow_non_jtag
    set tg [get_hw_targets]
    if {[llength $tg] != 1} { error "expected one JTAG target, found [llength $tg]: $tg" }
    open_hw_target [lindex $tg 0]
    set ::dev [lindex [get_hw_devices xcau15p*] 0]
    if {$::dev eq ""} { error "no xcau15p on the JTAG chain" }
    current_hw_device $::dev
    refresh_hw_device -update_hw_probes false $::dev
    set ::sm [lindex [get_hw_sysmons -of_objects $::dev] 0]
  } err]} { _reply TAPERR "connect: $err"; return }
  _reply TAPOK "connected dna=[get_property REGISTER.EFUSE.FUSE_DNA $::dev] usr=[get_property REGISTER.USR_ACCESS $::dev]"
}

proc tap_program {bit ltx} {
  if {[catch {
    set_property PROGRAM.FILE $bit $::dev
    set_property PROBES.FILE $ltx $::dev
    set_property FULL_PROBES.FILE $ltx $::dev
    program_hw_devices $::dev
    refresh_hw_device $::dev
  } err]} { _reply TAPERR "program: $err"; return }
  _reply TAPOK "programmed usr=[get_property REGISTER.USR_ACCESS $::dev] vios=[get_hw_vios -of_objects $::dev]"
}

proc tap_attach {ltx} {
  if {[catch {
    set_property PROBES.FILE $ltx $::dev
    set_property FULL_PROBES.FILE $ltx $::dev
    refresh_hw_device $::dev
  } err]} { _reply TAPERR "attach: $err"; return }
  _reply TAPOK "attached usr=[get_property REGISTER.USR_ACCESS $::dev] vios=[get_hw_vios -of_objects $::dev]"
}

proc tap_info {} {
  set out {}
  if {[catch {
    set vio [lindex [get_hw_vios -of_objects $::dev] 0]
    foreach p [get_hw_probes -of_objects $vio] {
      set props {}
      foreach k [list_property $p] { lappend props "$k=[get_property $k $p]" }
      lappend out "[get_property NAME $p] {[join $props {;}]}"
    }
  } err]} { _reply TAPERR "info: $err"; return }
  _reply TAPOK "probes [join $out { | }]"
}

# One snapshot: every VIO input probe (hex, keyed by its port index) and the SYSMON channels.
proc tap_read {} {
  if {[catch {
    set vio [lindex [get_hw_vios -of_objects $::dev] 0]
    if {![info exists ::radix_done]} {
      foreach p [get_hw_probes -of_objects $vio -filter {TYPE == vio_input}] {
        set_property INPUT_VALUE_RADIX HEX $p
      }
      set ::radix_done 1
    }
    refresh_hw_vio $vio
    set t [clock milliseconds]
    set parts [list "t_ms=$t"]
    foreach p [get_hw_probes -of_objects $vio -filter {TYPE == vio_input}] {
      if {[catch {set port [get_property PROBE_PORT $p]}]} { set port [get_property NAME $p] }
      lappend parts "p$port=[get_property INPUT_VALUE $p]"
    }
    refresh_hw_sysmon $::sm
    foreach k {TEMPERATURE VCCINT VCCAUX VCCBRAM} {
      lappend parts "[string tolower $k]=[get_property $k $::sm]"
    }
    foreach {name reg} {temp_raw 0x00 vccint_raw 0x01 vccaux_raw 0x02 vccbram_raw 0x06} {
      lappend parts "$name=[get_hw_sysmon_reg $::sm $reg]"
    }
  } err]} { _reply TAPERR "read: $err"; return }
  _reply TAPDATA [join $parts " "]
}

# SYSMON only (works with any design in the FPGA)
proc tap_sysmon {} {
  if {[catch {
    refresh_hw_sysmon $::sm
    set parts [list "t_ms=[clock milliseconds]"]
    foreach k {TEMPERATURE VCCINT VCCAUX VCCBRAM} {
      lappend parts "[string tolower $k]=[get_property $k $::sm]"
    }
  } err]} { _reply TAPERR "sysmon: $err"; return }
  _reply TAPDATA [join $parts " "]
}

# VIO outputs: port 0 = mask (hex), port 1 = clear (0/1)
proc tap_set_out {port value} {
  if {[catch {
    set vio [lindex [get_hw_vios -of_objects $::dev] 0]
    set p [get_hw_probes -of_objects $vio -filter "TYPE == vio_output && PROBE_PORT == $port"]
    set_property OUTPUT_VALUE $value $p
    commit_hw_vio $p
  } err]} { _reply TAPERR "set_out: $err"; return }
  _reply TAPOK "out$port=$value"
}

proc tap_close {} {
  catch { close_hw_target }
  catch { disconnect_hw_server }
  catch { close_hw_manager }
  _reply TAPOK "closed"
}

_reply TAPOK "server ready"
