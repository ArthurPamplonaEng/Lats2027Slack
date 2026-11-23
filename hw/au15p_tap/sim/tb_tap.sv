`timescale 1ns / 1ps
// tb_tap: behavioural test of tap_top with the real MMCME4_ADV model (unisims) and a chain whose
// stages have SIM_STAGE_NS of delay (TAP_SIM). With the default 0.083 ns/stage + 0.1 ns tap LUT:
//   delay(S) = 0.083 S + 0.1 ns; the clock period is 10 ns. The offset between FF1 and FF2 in the
//   clock model (the "guard", measured on tap 1) sets where each reading reaches zero.
//   expected reading = first step s with s * 17.857 ps > 10 - delay(S) - 0.25 ns (0 if negative);
//   taps with delay > 10 ns fail: FF2 wrong every cycle and no alarm before MAX_STEPS.
module tb_tap;
  localparam real STAGE  = 0.083;
  localparam real TAPD   = 0.100;
  localparam real STEPNS = 1.0 / 56.0;     // 17.857 ps
  localparam real GUARD  = 0.250;          // -9 deg of 10 ns
  localparam int  WIN    = 60_000;
  localparam int  NWIN   = 4;
  localparam int  N      = tap_pkg::N_TAPS;

  logic clk_p = 1'b0;
  always #5.0 clk_p = ~clk_p;
  wire clk_n = ~clk_p;
  wire tx, mcu_rx, led;

  tap_top #(.WINDOW_CYCLES(WIN), .MAX_STEPS(440), .SIM_STAGE_NS(STAGE)) dut (
    .sys_clk_p(clk_p), .sys_clk_n(clk_n), .fpga_uart_rx(1'b1), .fpga_uart_tx(tx),
    .mcu_usart1_rx(mcu_rx), .mcu_usart1_tx(1'b1), .fpga_button(1'b0), .status_o(led));

  function automatic int stage_of(int j);
    return int'(tap_pkg::TAP_STAGE[8*j +: 8]);
  endfunction

  function automatic real delay_of(int j);
    return STAGE * stage_of(j) + TAPD;
  endfunction

  // Reading of a tap with sensor slack s (ns) and a guard g (ns): the first step past s - g.
  function automatic int reading_of(real s, real g);
    if (s - g < 0.0) return 0;
    return int'($floor((s - g) / STEPNS)) + 1;
  endfunction

  // Expected reading (guard measured on tap 0, see below): -1 = no alarm before MAX_STEPS.
  // A failing tap (T < delay < 2T) aliases to the slack against 2T, if that falls in the sweep.
  real g_eff = GUARD;
  function automatic int expected(int j);
    real s;
    int  r;
    s = 10.0 - delay_of(j);
    if (s >= 0.0) begin
      r = reading_of(s, g_eff);
      return (r > 440 - 10) ? -1 : r;  // beyond the sweep: no alarm (short control taps)
    end
    r = reading_of(20.0 - delay_of(j), g_eff);
    return (r > 440 - 10) ? -1 : r;    // near or past MAX_STEPS / the catcher window: no alarm
  endfunction
  function automatic bit fails(int j);
    return delay_of(j) > 10.0;
  endfunction

  int nwin = 0;
  int errors = 0;
  initial begin
    $display("TB: stage %0.3f ns, guard %0.3f ns, step %0.4f ns", STAGE, GUARD, STEPNS);
    for (int j = 0; j < N; j++)
      $display("TB tap %2d stage %3d delay %6.3f ns expected %0d", j, stage_of(j), delay_of(j), expected(j));
  end

  // one cycle after each window end, the w_* registers hold the closed window
  logic wend_d = 1'b0;
  always @(posedge dut.clk_sys) wend_d <= dut.u_stats.wend & dut.u_stats.run_rst_n;
  always @(posedge dut.clk_sys) if (wend_d) begin
    nwin++;
    // effective guard of the clock model, from control tap 1 (S48), always inside the sweep
    if (nwin == 2 && dut.w_got[63:32] != 0)
      g_eff = (10.0 - delay_of(1)) - (real'(dut.w_min[31:16]) - 0.5) * STEPNS;
    $display("TB window %0d: id %0d sweeps %0d sat %0d tmo %0d lock %0d flags %b guard %0.3f ns",
             nwin, dut.w_id, dut.w_sweeps, dut.w_sat, dut.w_tmo, dut.w_lock, dut.flags, g_eff);
    for (int j = 0; j < N; j++) begin
      automatic int  g   = dut.w_got[32*j +: 32];
      automatic int  mn  = dut.w_min[16*j +: 16];
      automatic int  mx  = dut.w_max[16*j +: 16];
      automatic int  e   = dut.w_err[32*j +: 32];
      automatic real avg = (g > 0) ? real'(dut.w_sum[32*j +: 32]) / g : -1.0;
      automatic int  ex  = expected(j);
      automatic bit  ok;
      if (nwin == 1) ok = 1'b1;      // first window: lock, count_en and the first sweep
      else if (ex < 0) ok = (g == 0) && (fails(j) ? (e > WIN - 10) : (e == 0));
      else ok = (g == dut.w_sweeps) && (mn >= ex - 1) && (mx <= ex + 1) &&
                (fails(j) ? (e > WIN - 10) : (e == 0));
      if (!ok) errors++;
      $display("TB   tap %2d S%3d got %0d min %0d max %0d mean %7.2f err %0d exp %0d %s",
               j, stage_of(j), g, mn, mx, avg, e, ex, ok ? "ok" : "MISMATCH");
    end
    if (nwin >= NWIN) begin
      if (dut.w_sweeps == 0) errors++;
      $display("TB RESULT: %s (%0d mismatches)", errors == 0 ? "PASS" : "FAIL", errors);
      $finish;
    end
  end

  initial begin
    #20ms;
    $display("TB RESULT: FAIL (timeout)");
    $finish;
  end
endmodule
