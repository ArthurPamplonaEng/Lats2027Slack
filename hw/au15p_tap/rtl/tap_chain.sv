`timescale 1ns / 1ps
// tap_chain: a LUT ripple-carry chain of N_STAGES stages with N_TAPS taps.
//
// Same structure and stimulus as rca_lut_toggle of the 9-chain AU15P design (au15p_multi_B):
// one LUT3 majority (carry) per stage, op_a alternating 0x55..55 / 0x55..56 and op_b = 0xAA..AA.
// Every stage propagates (a_i ^ b_i = 1), the carry is generated or killed at bit 1, and both
// edges ripple through the whole chain, so c[k] (k >= 2) toggles every clk cycle.
//
// Tap j is the sum bit of stage S = TAP_STAGE[j] (s_S = a_S ^ b_S ^ c_S = ~c_S), each through its
// own LUT3, so every tap adds the same load to the chain. A tap that meets timing toggles every
// cycle: after edge n its settled value equals ~toggle(n), so the FF2 of its sensor holds
// toggle(n+1) = t_ref after edge n+1 (t_ref is a replica of toggle, see tap_top's checkers).
//
// Simulation (TAP_SIM): every stage and tap LUT is a behavioural gate with SIM_STAGE_NS /
// SIM_TAP_NS of delay, so the testbench can place taps on both sides of the clock period.
(* DONT_TOUCH = "yes" *)
module tap_chain #(
  parameter int N_STAGES = 128,
  parameter int N_TAPS   = 22,
  parameter logic [N_TAPS*8-1:0] TAP_STAGE = '0,
  parameter real SIM_STAGE_NS = 0.083,
  parameter real SIM_TAP_NS   = 0.100
)(
  input  logic              clk,
  input  logic              rst_n,
  output logic [N_TAPS-1:0] tap_o,
  output logic              t_ref_o
);
  localparam logic [N_STAGES-1:0] A0 = {(N_STAGES/2){2'b01}};
  localparam logic [N_STAGES-1:0] B0 = {(N_STAGES/2){2'b10}};
  localparam logic [N_STAGES-1:0] A1 = A0 + 1'b1;

  (* DONT_TOUCH = "yes" *) logic                toggle;
  (* DONT_TOUCH = "yes" *) logic                t_ref;
  (* DONT_TOUCH = "yes" *) logic [N_STAGES-1:0] op_a;
  (* DONT_TOUCH = "yes" *) logic [N_STAGES-1:0] op_b;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      toggle <= 1'b0;
      t_ref  <= 1'b0;
      op_a   <= A0;
      op_b   <= B0;
    end else begin
      toggle <= ~toggle;
      t_ref  <= ~t_ref;
      op_a   <= toggle ? A0 : A1;
      op_b   <= B0;
    end
  end
  assign t_ref_o = t_ref;

  logic [N_STAGES:0] c;
  assign c[0] = 1'b0;

  for (genvar i = 0; i < N_STAGES; i++) begin : st
`ifdef TAP_SIM
    assign #(SIM_STAGE_NS) c[i+1] = (op_a[i] & op_b[i]) | (op_a[i] & c[i]) | (op_b[i] & c[i]);
`else
    (* DONT_TOUCH = "yes" *)
    LUT3 #(.INIT(8'hE8)) carry (.O(c[i+1]), .I0(op_a[i]), .I1(op_b[i]), .I2(c[i]));
`endif
  end

  for (genvar j = 0; j < N_TAPS; j++) begin : tp
    localparam int S = TAP_STAGE[8*j +: 8];
`ifdef TAP_SIM
    assign #(SIM_TAP_NS) tap_o[j] = op_a[S] ^ op_b[S] ^ c[S];
`else
    (* DONT_TOUCH = "yes" *)
    LUT3 #(.INIT(8'h96)) sum (.O(tap_o[j]), .I0(op_a[S]), .I1(op_b[S]), .I2(c[S]));
`endif
  end
endmodule
