`timescale 1ns / 1ps
// tap_sensor: the slack sensor of [SBCCI 2025] (modern_sensible / chain_sensor of the AU15P
// designs): FF1 on the phase-swept clock, FF2 on the system clock, their XOR latched by FF3 on
// the catcher clock. FF2 is also the functional capture flop of the tap: tap_top compares it with
// the expected value every cycle (the error checker), so "sensor alarm" (FF1 != FF2) and
// "functional error" (FF2 != expected) are observed on the same flop.
module tap_sensor (
  input  logic sclk,     // clk_sys   -> FF2
  input  logic psclk,    // clk_phase -> FF1
  input  logic cclk,     // clk_catch -> FF3
  input  logic d,        // tap output
  output logic alarm,    // FF3 (clk_catch domain)
  output logic ff2_q     // FF2 (clk_sys domain)
);
  logic ff1, ff2, x;

  (* DONT_TOUCH = "true" *)
  FDCE #(.INIT(1'b0)) FF1 (.Q(ff1), .C(psclk), .CE(1'b1), .CLR(1'b0), .D(d));
  (* DONT_TOUCH = "true" *)
  FDCE #(.INIT(1'b0)) FF2 (.Q(ff2), .C(sclk), .CE(1'b1), .CLR(1'b0), .D(d));
  (* DONT_TOUCH = "true" *)
  LUT2 #(.INIT(4'h6)) XOR1 (.O(x), .I0(ff1), .I1(ff2));
  (* DONT_TOUCH = "true" *)
  FDCE #(.INIT(1'b0)) FF3 (.Q(alarm), .C(cclk), .CE(1'b1), .CLR(1'b0), .D(x));

  assign ff2_q = ff2;
endmodule
