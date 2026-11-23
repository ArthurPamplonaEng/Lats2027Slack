`timescale 1ns / 1ps
// tap_sweep: one fine-phase sweep for all taps, repeated continuously.
//
// From the phase origin the engine moves clk_phase earlier one step at a time (PSINCDEC = 0, the
// direction of the SBCCI controller). After each PSDONE it waits FLUSH cycles (FF1 -> XOR -> FF3
// -> alarm_s) and then watches the alarms for OBS cycles; a tap's reading is the first step at
// which its alarm is seen (the SBCCI criterion). The sweep ends when every tap selected by `mask`
// has alarmed, or after MAX_STEPS steps (`sat_o`; taps without an alarm have got_o = 0). Then the
// phase goes back to the origin step by step and the next sweep starts.
//
// `offset` counts the steps confirmed by the MMCM away from the origin. It is reset only at
// configuration (run_rst_n), so after a lock loss the phase is first brought back to the origin.
module tap_sweep #(
  parameter int N         = 22,
  parameter int MAX_STEPS = 440,
  parameter int FLUSH     = 6,
  parameter int OBS       = 4,
  parameter int STEP_TMO  = 4095
)(
  input  logic            clk,
  input  logic            rst_n,       // low while the MMCM is unlocked
  input  logic            run_rst_n,   // low only before the first lock
  input  logic [N-1:0]    alarm,       // FF3 outputs (clk_catch, related to clk)
  input  logic [N-1:0]    mask,
  output logic            psen,
  output logic            psincdec,
  input  logic            psdone,
  output logic            done_o,      // pulse: a sweep finished, got_o / val_o valid
  output logic            sat_o,
  output logic [N-1:0]    got_o,
  output logic [N*16-1:0] val_o,
  output logic            tmo_o,       // pulse: no PSDONE within STEP_TMO cycles
  output logic [15:0]     offset_o
);
  typedef enum logic [2:0] {S_INIT, S_FLUSH, S_OBS, S_CHECK, S_STEP, S_WAIT, S_RET, S_RWAIT} st_t;
  st_t st;

  (* ASYNC_REG = "FALSE" *) logic [N-1:0] alarm_s;
  logic [15:0] step;
  logic [15:0] offset;
  logic [7:0]  cnt;
  logic [12:0] tmo;
  logic [N-1:0] got;
  logic [N*16-1:0] val;

  assign got_o    = got;
  assign val_o    = val;
  assign offset_o = offset;

  always_ff @(posedge clk) alarm_s <= alarm;

  always_ff @(posedge clk) begin
    psen   <= 1'b0;
    done_o <= 1'b0;
    tmo_o  <= 1'b0;
    if (!run_rst_n) begin
      offset <= 16'd0;
    end
    if (!rst_n || !run_rst_n) begin
      st       <= S_INIT;
      step     <= 16'd0;
      cnt      <= 8'd0;
      tmo      <= 13'd0;
      got      <= '0;
      psincdec <= 1'b0;
      sat_o    <= 1'b0;
    end else begin
      case (st)
        S_INIT: begin
          got  <= '0;
          step <= 16'd0;
          tmo  <= 13'd0;
          if (offset != 16'd0) begin
            st <= S_RET;
          end else begin
            cnt <= FLUSH[7:0];
            st  <= S_FLUSH;
          end
        end
        S_FLUSH: begin
          if (cnt == 8'd0) begin
            cnt <= OBS[7:0];
            st  <= S_OBS;
          end else begin
            cnt <= cnt - 8'd1;
          end
        end
        S_OBS: begin
          for (int j = 0; j < N; j++) begin
            if (alarm_s[j] && !got[j]) begin
              got[j]          <= 1'b1;
              val[16*j +: 16] <= step;
            end
          end
          if (cnt <= 8'd1) st <= S_CHECK;
          else             cnt <= cnt - 8'd1;
        end
        S_CHECK: begin
          if (&(got | ~mask)) begin
            sat_o  <= 1'b0;
            done_o <= 1'b1;
            st     <= S_RET;
          end else if (step >= MAX_STEPS[15:0]) begin
            sat_o  <= 1'b1;
            done_o <= 1'b1;
            st     <= S_RET;
          end else begin
            st <= S_STEP;
          end
        end
        S_STEP: begin
          psen     <= 1'b1;
          psincdec <= 1'b0;           // earlier
          tmo      <= 13'd0;
          st       <= S_WAIT;
        end
        S_WAIT: begin
          if (psdone) begin
            step   <= step + 16'd1;
            offset <= offset + 16'd1;
            cnt    <= FLUSH[7:0];
            st     <= S_FLUSH;
          end else if (tmo == STEP_TMO[12:0]) begin
            tmo_o <= 1'b1;
            st    <= S_RET;
          end else begin
            tmo <= tmo + 13'd1;
          end
        end
        S_RET: begin
          if (offset == 16'd0) begin
            st <= S_INIT;
          end else begin
            psen     <= 1'b1;
            psincdec <= 1'b1;         // back towards the origin
            tmo      <= 13'd0;
            st       <= S_RWAIT;
          end
        end
        S_RWAIT: begin
          if (psdone) begin
            offset <= offset - 16'd1;
            st     <= S_RET;
          end else if (tmo == STEP_TMO[12:0]) begin
            tmo_o <= 1'b1;
            st    <= S_RET;
          end else begin
            tmo <= tmo + 13'd1;
          end
        end
        default: st <= S_INIT;
      endcase
    end
  end
endmodule
