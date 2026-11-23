`timescale 1ns / 1ps
// tap_clocks: the sensor clocks from one MMCME4_ADV (no IP core).
//
//   VCO = 100 MHz x 10 = 1 GHz, so one fine phase step = 1/(56 x 1 GHz) = 17.857 ps,
//   the same step as the Nexys 4 DDR design (Artix-7, clk_wiz_0 x10).
//   clk_sys    0 deg                         launch registers, FF2 of every sensor, checkers
//   clk_phase  PHASE_DEG + fine phase shift  FF1 of every sensor
//   clk_catch  CATCH_DEG                     FF3 of every sensor (alarm latch)
//   clk_board  BUFG of the board oscillator  VIO / debug hub (keeps JTAG alive if the MMCM unlocks)
//
// PHASE_DEG must stay 0: a static phase on an output with fine phase shift is rejected by the DRC
// (AVAL-152). The sensor therefore has no designed guard band: at phase step 0, FF1 and FF2 differ
// only by the implementation (clock skew and routing), which report_taps.tcl quantifies per tap.
// PSCLK is clk_sys. The fine shift is driven by tap_sweep (PSINCDEC = 0 moves clk_phase earlier).
module tap_clocks #(
  parameter real PHASE_DEG = 0.0,
  parameter real CATCH_DEG = 63.0
)(
  input  logic clk_in,      // 100 MHz from the IBUFDS (dedicated route to the MMCM)
  output logic clk_board,
  output logic clk_sys,
  output logic clk_phase,
  output logic clk_catch,
  output logic locked,
  input  logic psen,
  input  logic psincdec,
  output logic psdone
);
  logic fb, c0, c1, c2;

  MMCME4_ADV #(
    .BANDWIDTH("OPTIMIZED"), .COMPENSATION("INTERNAL"), .STARTUP_WAIT("FALSE"),
    .CLKIN1_PERIOD(10.0), .DIVCLK_DIVIDE(1),
    .CLKFBOUT_MULT_F(10.0), .CLKFBOUT_PHASE(0.0),
    .CLKOUT0_DIVIDE_F(10.0), .CLKOUT0_PHASE(CATCH_DEG), .CLKOUT0_DUTY_CYCLE(0.5),
    .CLKOUT1_DIVIDE(10), .CLKOUT1_PHASE(PHASE_DEG), .CLKOUT1_DUTY_CYCLE(0.5),
    .CLKOUT1_USE_FINE_PS("TRUE"),
    .CLKOUT2_DIVIDE(10), .CLKOUT2_PHASE(0.0), .CLKOUT2_DUTY_CYCLE(0.5)
  ) u_mmcm (
    .CLKIN1(clk_in), .CLKIN2(1'b0), .CLKINSEL(1'b1),
    .CLKFBIN(fb), .CLKFBOUT(fb), .CLKFBOUTB(),
    .CLKOUT0(c0), .CLKOUT0B(), .CLKOUT1(c1), .CLKOUT1B(), .CLKOUT2(c2), .CLKOUT2B(),
    .CLKOUT3(), .CLKOUT3B(), .CLKOUT4(), .CLKOUT5(), .CLKOUT6(),
    .LOCKED(locked), .RST(1'b0), .PWRDWN(1'b0),
    .PSCLK(clk_sys), .PSEN(psen), .PSINCDEC(psincdec), .PSDONE(psdone),
    .DADDR(7'd0), .DCLK(1'b0), .DEN(1'b0), .DI(16'd0), .DWE(1'b0), .DO(), .DRDY(),
    .CDDCDONE(), .CDDCREQ(1'b0), .CLKFBSTOPPED(), .CLKINSTOPPED()
  );

  BUFG u_bg_catch (.I(c0), .O(clk_catch));
  BUFG u_bg_phase (.I(c1), .O(clk_phase));
  BUFG u_bg_sys   (.I(c2), .O(clk_sys));
  BUFG u_bg_board (.I(clk_in), .O(clk_board));
endmodule
