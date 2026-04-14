`default_nettype none
`timescale 1ns / 1ps

/* Cocotb wrapper for the UART-servo project. */
module tb ();

`ifdef GL_TEST
  localparam integer TEST_CLKS_PER_BIT = 25;
  localparam integer TEST_COUNTER_WIDTH = 20;
  localparam integer TEST_FRAME_CYCLES = 500000;
  localparam integer TEST_MIN_PULSE_CYCLES = 25000;
  localparam integer TEST_CENTER_PULSE_CYCLES = 37500;
  localparam integer TEST_MAX_PULSE_CYCLES = 50000;
`else
  localparam integer TEST_CLKS_PER_BIT = 4;
  localparam integer TEST_COUNTER_WIDTH = 8;
  localparam integer TEST_FRAME_CYCLES = 100;
  localparam integer TEST_MIN_PULSE_CYCLES = 10;
  localparam integer TEST_CENTER_PULSE_CYCLES = 15;
  localparam integer TEST_MAX_PULSE_CYCLES = 19;
`endif

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;
  wire [31:0] cfg_clks_per_bit;
  wire [31:0] cfg_min_pulse_cycles;
  wire [31:0] cfg_center_pulse_cycles;
  wire [31:0] cfg_max_pulse_cycles;
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  assign cfg_clks_per_bit = TEST_CLKS_PER_BIT;
  assign cfg_min_pulse_cycles = TEST_MIN_PULSE_CYCLES;
  assign cfg_center_pulse_cycles = TEST_CENTER_PULSE_CYCLES;
  assign cfg_max_pulse_cycles = TEST_MAX_PULSE_CYCLES;

  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    clk = 1'b0;
    rst_n = 1'b0;
    ena = 1'b0;
    ui_in = 8'd0;
    uio_in = 8'd0;
    #1;
  end

`ifdef GL_TEST
  tt_um_isa084_uart_servo user_project (
      .VPWR(VPWR),
      .VGND(VGND),
      .ui_in(ui_in),
      .uo_out(uo_out),
      .uio_in(uio_in),
      .uio_out(uio_out),
      .uio_oe(uio_oe),
      .ena(ena),
      .clk(clk),
      .rst_n(rst_n)
  );
`else
  tt_um_isa084_uart_servo #(
      .CLKS_PER_BIT(TEST_CLKS_PER_BIT),
      .COUNTER_WIDTH(TEST_COUNTER_WIDTH),
      .FRAME_CYCLES(TEST_FRAME_CYCLES),
      .MIN_PULSE_CYCLES(TEST_MIN_PULSE_CYCLES),
      .CENTER_PULSE_CYCLES(TEST_CENTER_PULSE_CYCLES),
      .MAX_PULSE_CYCLES(TEST_MAX_PULSE_CYCLES)
  ) user_project (
      .ui_in(ui_in),
      .uo_out(uo_out),
      .uio_in(uio_in),
      .uio_out(uio_out),
      .uio_oe(uio_oe),
      .ena(ena),
      .clk(clk),
      .rst_n(rst_n)
  );
`endif
endmodule
