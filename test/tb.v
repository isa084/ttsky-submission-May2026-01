`default_nettype none
`timescale 1ns / 1ps

/* Cocotb wrapper for the UART-servo project. */
module tb ();

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

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
      .CLKS_PER_BIT(4),
      .COUNTER_WIDTH(8),
      .FRAME_CYCLES(100),
      .MIN_PULSE_CYCLES(10),
      .CENTER_PULSE_CYCLES(15),
      .MAX_PULSE_CYCLES(19)
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
