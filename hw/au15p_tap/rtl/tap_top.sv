`timescale 1ns / 1ps
// tap_top: functional-failure validation of the phase-swept slack sensor on the AU15P (RV02A).
//
// One LUT ripple chain (tap_chain) with N_TAPS taps; each tap has its own sensor (tap_sensor) and
// a functional checker: err_q = FF2 ^ t_ref, i.e. the tap's capture flop holds the wrong value.
// One continuous phase sweep (tap_sweep) reads every tap; tap_stats keeps 1 s window statistics,
// read through the JTAG by a VIO (clocked by the board oscillator, so the debug link survives an
// MMCM lock loss at low VCCINT). Core voltage is set from the PC through the STM32/PMIC; the
// FPGA only measures.
//
// VIO probes (all 128 bits):
//   probe_in0          {w_id, w_sweeps, w_sat, w_tmo[15:0], w_lock[7:0], flags[7:0]}
//   probe_in(1+j)      tap j: {w_err, w_max[15:0], w_min[15:0], w_sum, w_got}
//   probe_out0 [N-1:0] mask: taps that must alarm before a sweep ends (default all)
//   probe_out1         clear: restarts the window statistics (pulse from the host)
// flags = {offset!=0, sat_seen, tmo_seen, count_en, locked_s, run_rst_n, 2'b01}
module tap_top
  import tap_pkg::*;
#(
  parameter int  WINDOW_CYCLES = 100_000_000,
  parameter int  MAX_STEPS     = 440,
  parameter real PHASE_DEG     = 0.0,    // must be 0 with fine PS (DRC AVAL-152)
  parameter real CATCH_DEG     = 63.0,
  parameter real SIM_STAGE_NS  = 0.083
)(
  input  wire sys_clk_p,
  input  wire sys_clk_n,
  input  wire fpga_uart_rx,
  output wire fpga_uart_tx,
  output wire mcu_usart1_rx,   // to the STM32: held idle
  input  wire mcu_usart1_tx,
  input  wire fpga_button,
  output wire status_o
);
  localparam int N = N_TAPS;

  // ------------------------------------------------------------------ clocks
  wire clk_in;
  IBUFDS #(.DIFF_TERM("FALSE"), .IBUF_LOW_PWR("FALSE")) u_ibuf (
    .I(sys_clk_p), .IB(sys_clk_n), .O(clk_in));

  wire clk_board, clk_sys, clk_phase, clk_catch, locked;
  wire psen, psincdec, psdone;
  tap_clocks #(.PHASE_DEG(PHASE_DEG), .CATCH_DEG(CATCH_DEG)) u_clocks (
    .clk_in(clk_in), .clk_board(clk_board), .clk_sys(clk_sys), .clk_phase(clk_phase),
    .clk_catch(clk_catch), .locked(locked), .psen(psen), .psincdec(psincdec), .psdone(psdone));

  // ------------------------------------------------------------------ resets
  logic [3:0] lock_sync = 4'b0000;
  always_ff @(posedge clk_sys or negedge locked)
    if (!locked) lock_sync <= 4'b0000;
    else         lock_sync <= {lock_sync[2:0], 1'b1};
  wire rst_n = lock_sync[3];

  logic run_rst_n = 1'b0;          // rises at the first lock, never falls
  always_ff @(posedge clk_sys) if (rst_n) run_rst_n <= 1'b1;

  logic [10:0] en_cnt = 11'd0;     // errors are counted 1024 cycles after each (re)lock
  always_ff @(posedge clk_sys)
    if (!rst_n)              en_cnt <= 11'd0;
    else if (!en_cnt[10])    en_cnt <= en_cnt + 11'd1;
  wire count_en = en_cnt[10];

  // ------------------------------------------------------------------ host controls (VIO)
  wire [N-1:0] mask_b;
  wire         clear_b;
  (* ASYNC_REG = "TRUE" *) logic [N-1:0] mask_m, mask_s;
  (* ASYNC_REG = "TRUE" *) logic [2:0]   clr_m;
  always_ff @(posedge clk_sys) begin
    mask_m <= mask_b;
    mask_s <= mask_m;
    clr_m  <= {clr_m[1:0], clear_b};
  end
  wire stats_rst_n = run_rst_n & ~clr_m[2];

  // ------------------------------------------------------------------ chain, sensors, checkers
  wire [N-1:0] tap, alarm, ff2;
  wire         t_ref;

  (* KEEP_HIERARCHY = "yes" *)
  tap_chain #(.N_STAGES(N_STAGES), .N_TAPS(N), .TAP_STAGE(TAP_STAGE),
              .SIM_STAGE_NS(SIM_STAGE_NS)) u_chain (
    .clk(clk_sys), .rst_n(rst_n), .tap_o(tap), .t_ref_o(t_ref));

  logic [N-1:0] err_q;
  for (genvar j = 0; j < N; j++) begin : g_tap
    (* KEEP_HIERARCHY = "yes" *)
    tap_sensor u_sens (.sclk(clk_sys), .psclk(clk_phase), .cclk(clk_catch), .d(tap[j]),
                       .alarm(alarm[j]), .ff2_q(ff2[j]));
    always_ff @(posedge clk_sys) err_q[j] <= ff2[j] ^ t_ref;
  end

  // ------------------------------------------------------------------ sweep and statistics
  wire            done, sat, tmo;
  wire [N-1:0]    got;
  wire [N*16-1:0] val;
  wire [15:0]     offset;

  (* KEEP_HIERARCHY = "yes" *)
  tap_sweep #(.N(N), .MAX_STEPS(MAX_STEPS)) u_sweep (
    .clk(clk_sys), .rst_n(rst_n), .run_rst_n(run_rst_n), .alarm(alarm), .mask(mask_s),
    .psen(psen), .psincdec(psincdec), .psdone(psdone),
    .done_o(done), .sat_o(sat), .got_o(got), .val_o(val), .tmo_o(tmo), .offset_o(offset));

  logic locked_s1, locked_s;
  always_ff @(posedge clk_sys) begin
    locked_s1 <= locked;
    locked_s  <= locked_s1;
  end

  wire [31:0]     w_id, w_sweeps, w_sat;
  wire [15:0]     w_tmo;
  wire [7:0]      w_lock;
  wire [N*32-1:0] w_got, w_sum, w_err;
  wire [N*16-1:0] w_min, w_max;

  (* KEEP_HIERARCHY = "yes" *)
  tap_stats #(.N(N), .WINDOW_CYCLES(WINDOW_CYCLES)) u_stats (
    .clk(clk_sys), .run_rst_n(stats_rst_n), .count_en(count_en), .locked_s(locked_s),
    .done_i(done), .sat_i(sat), .got_i(got), .val_i(val), .tmo_i(tmo), .err_i(err_q),
    .w_id(w_id), .w_sweeps(w_sweeps), .w_sat(w_sat), .w_tmo(w_tmo), .w_lock(w_lock),
    .w_got(w_got), .w_sum(w_sum), .w_min(w_min), .w_max(w_max), .w_err(w_err));

  logic sat_seen, tmo_seen;
  always_ff @(posedge clk_sys) begin
    if (!stats_rst_n) begin
      sat_seen <= 1'b0;
      tmo_seen <= 1'b0;
    end else begin
      if (done && sat) sat_seen <= 1'b1;
      if (tmo)         tmo_seen <= 1'b1;
    end
  end
  wire [7:0] flags = {offset != 16'd0, sat_seen, tmo_seen, count_en, locked_s, run_rst_n, 2'b01};

  // ------------------------------------------------------------------ VIO
  logic [127:0] pin [0:N];
  always_comb begin
    pin[0] = {w_id, w_sweeps, w_sat, w_tmo, w_lock, flags};
    for (int j = 0; j < N; j++)
      pin[1+j] = {w_err[32*j +: 32], w_max[16*j +: 16], w_min[16*j +: 16],
                  w_sum[32*j +: 32], w_got[32*j +: 32]};
  end

`ifdef TAP_SIM
  assign mask_b  = {N{1'b1}};
  assign clear_b = 1'b0;
`else
  vio_tap u_vio (
    .clk(clk_board),
    .probe_in0(pin[0]),   .probe_in1(pin[1]),   .probe_in2(pin[2]),   .probe_in3(pin[3]),
    .probe_in4(pin[4]),   .probe_in5(pin[5]),   .probe_in6(pin[6]),   .probe_in7(pin[7]),
    .probe_in8(pin[8]),   .probe_in9(pin[9]),   .probe_in10(pin[10]), .probe_in11(pin[11]),
    .probe_in12(pin[12]), .probe_in13(pin[13]), .probe_in14(pin[14]), .probe_in15(pin[15]),
    .probe_in16(pin[16]), .probe_in17(pin[17]), .probe_in18(pin[18]), .probe_in19(pin[19]),
    .probe_in20(pin[20]), .probe_in21(pin[21]), .probe_in22(pin[22]), .probe_in23(pin[23]),
    .probe_out0(mask_b),
    .probe_out1(clear_b)
  );
`endif

  // ------------------------------------------------------------------ pins
  assign mcu_usart1_rx = 1'b1;
  assign fpga_uart_tx  = 1'b1;

  logic [25:0] heartbeat = 26'd0;
  always_ff @(posedge clk_sys) heartbeat <= heartbeat + 26'd1;
  assign status_o = locked & heartbeat[25];
endmodule
