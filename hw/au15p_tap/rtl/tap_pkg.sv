`timescale 1ns / 1ps
// tap_pkg: tap positions of the tapped chain.
//   tap 0, 1   stages 24 and 48: controls, far from failure in the whole voltage range
//   tap 2..22  stages 70, 74, ..., 150: 4 stages apart (~0.3-0.4 ns at 0.85 V). With 0.07-0.10 ns
//              per stage in silicon, the 10 ns period is crossed somewhere in stages ~95-135, and
//              the core-voltage range of the bench (about +-10 % delay) moves it by ~15 stages.
package tap_pkg;
  localparam int N_STAGES = 160;
  localparam int N_TAPS   = 23;

  function automatic logic [N_TAPS*8-1:0] default_stages();
    logic [N_TAPS*8-1:0] r;
    r = '0;
    r[7:0]  = 8'd24;
    r[15:8] = 8'd48;
    for (int j = 2; j < N_TAPS; j++) r[8*j +: 8] = 8'(70 + 4 * (j - 2));
    return r;
  endfunction

  localparam logic [N_TAPS*8-1:0] TAP_STAGE = default_stages();
endpackage
