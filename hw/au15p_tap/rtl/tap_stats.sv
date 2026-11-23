`timescale 1ns / 1ps
// tap_stats: per-window statistics of every tap (window = WINDOW_CYCLES of clk).
//
// Sensor (one entry per finished sweep): n_got (sweeps in which the tap alarmed), sum, min and
// max of its readings. Functional checker: err = clk cycles in which the tap's FF2 differed from
// the expected value (counted only while count_en, i.e. not in the first cycles after a lock).
// Global: window id, sweeps, saturated sweeps, PSDONE timeouts, lock losses (sticky count).
// At the end of a window everything is copied to the w_* registers in one clock cycle, so a
// snapshot of w_* (VIO) is always self-consistent; an event in that same cycle is dropped (one
// cycle in WINDOW_CYCLES, one sweep in about five thousand).
module tap_stats #(
  parameter int N             = 22,
  parameter int WINDOW_CYCLES = 100_000_000
)(
  input  logic            clk,
  input  logic            run_rst_n,
  input  logic            count_en,
  input  logic            locked_s,     // MMCM lock, synchronised to clk (for the lock-loss count)
  input  logic            done_i,
  input  logic            sat_i,
  input  logic [N-1:0]    got_i,
  input  logic [N*16-1:0] val_i,
  input  logic            tmo_i,
  input  logic [N-1:0]    err_i,
  output logic [31:0]     w_id,
  output logic [31:0]     w_sweeps,
  output logic [31:0]     w_sat,
  output logic [15:0]     w_tmo,
  output logic [7:0]      w_lock,
  output logic [N*32-1:0] w_got,
  output logic [N*32-1:0] w_sum,
  output logic [N*16-1:0] w_min,
  output logic [N*16-1:0] w_max,
  output logic [N*32-1:0] w_err
);
  logic [31:0] wcnt;
  wire         wend = (wcnt == WINDOW_CYCLES - 1);

  logic [31:0]     a_sweeps, a_sat;
  logic [15:0]     a_tmo;
  logic [N*32-1:0] a_got, a_sum, a_err;
  logic [N*16-1:0] a_min, a_max;
  logic            lock_prev;

  always_ff @(posedge clk) begin
    if (!run_rst_n) begin
      wcnt      <= 32'd0;
      w_id      <= 32'd0;
      w_sweeps  <= 32'd0;
      w_sat     <= 32'd0;
      w_tmo     <= 16'd0;
      w_lock    <= 8'd0;
      w_got     <= '0;
      w_sum     <= '0;
      w_min     <= '0;
      w_max     <= '0;
      w_err     <= '0;
      a_sweeps  <= 32'd0;
      a_sat     <= 32'd0;
      a_tmo     <= 16'd0;
      a_got     <= '0;
      a_sum     <= '0;
      a_err     <= '0;
      a_min     <= {N{16'hFFFF}};
      a_max     <= '0;
      lock_prev <= 1'b0;
    end else begin
      wcnt      <= wend ? 32'd0 : wcnt + 32'd1;
      lock_prev <= locked_s;
      if (lock_prev && !locked_s && w_lock != 8'hFF) w_lock <= w_lock + 8'd1;

      if (wend) begin
        w_id     <= w_id + 32'd1;
        w_sweeps <= a_sweeps;
        w_sat    <= a_sat;
        w_tmo    <= a_tmo;
        w_got    <= a_got;
        w_sum    <= a_sum;
        w_err    <= a_err;
        w_max    <= a_max;
        for (int j = 0; j < N; j++)
          w_min[16*j +: 16] <= (a_got[32*j +: 32] != 32'd0) ? a_min[16*j +: 16] : 16'hFFFF;
        a_sweeps <= 32'd0;
        a_sat    <= 32'd0;
        a_tmo    <= 16'd0;
        a_got    <= '0;
        a_sum    <= '0;
        a_err    <= '0;
        a_min    <= {N{16'hFFFF}};
        a_max    <= '0;
      end else begin
        if (tmo_i && a_tmo != 16'hFFFF) a_tmo <= a_tmo + 16'd1;
        if (done_i) begin
          a_sweeps <= a_sweeps + 32'd1;
          if (sat_i) a_sat <= a_sat + 32'd1;
          for (int j = 0; j < N; j++) begin
            if (got_i[j]) begin
              a_got[32*j +: 32] <= a_got[32*j +: 32] + 32'd1;
              a_sum[32*j +: 32] <= a_sum[32*j +: 32] + {16'd0, val_i[16*j +: 16]};
              if (val_i[16*j +: 16] < a_min[16*j +: 16]) a_min[16*j +: 16] <= val_i[16*j +: 16];
              if (val_i[16*j +: 16] > a_max[16*j +: 16]) a_max[16*j +: 16] <= val_i[16*j +: 16];
            end
          end
        end
        if (count_en) begin
          for (int j = 0; j < N; j++)
            if (err_i[j] && a_err[32*j +: 32] != 32'hFFFF_FFFF)
              a_err[32*j +: 32] <= a_err[32*j +: 32] + 32'd1;
        end
      end
    end
  end
endmodule
