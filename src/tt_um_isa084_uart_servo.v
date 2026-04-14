`default_nettype none
`timescale 1ns / 1ps

// UART-controlled hobby servo pulse generator.
// ui_in[0] is UART RX. ui_in[3:1] provide direct demo overrides.
module tt_um_isa084_uart_servo #(
    parameter integer CLKS_PER_BIT       = 25,
    parameter integer COUNTER_WIDTH      = 20,
    parameter integer FRAME_CYCLES       = 500000,
    parameter integer MIN_PULSE_CYCLES   = 25000,
    parameter integer CENTER_PULSE_CYCLES = 37500,
    parameter integer MAX_PULSE_CYCLES   = 50000
) (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
  reg [COUNTER_WIDTH-1:0] frame_counter;
  reg [COUNTER_WIDTH-1:0] pulse_cycles;
  reg [3:0] preset_code;
  reg ack_toggle;
  reg command_seen;

  wire [7:0] rx_data;
  wire rx_valid;
  wire rx_busy;

  function [COUNTER_WIDTH-1:0] digit_to_pulse_cycles;
    input [3:0] digit;
    integer pulse_step;
    begin
      pulse_step = (MAX_PULSE_CYCLES - MIN_PULSE_CYCLES) / 9;
      digit_to_pulse_cycles = MIN_PULSE_CYCLES + (digit * pulse_step);
    end
  endfunction

  uart_rx8 #(
      .CLKS_PER_BIT(CLKS_PER_BIT)
  ) uart_rx (
      .clk(clk),
      .rst_n(rst_n),
      .rx_i(ui_in[0]),
      .data_o(rx_data),
      .valid_o(rx_valid),
      .busy_o(rx_busy)
  );

  always @(posedge clk) begin
    if (!rst_n) begin
      frame_counter <= {COUNTER_WIDTH{1'b0}};
      pulse_cycles  <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
      preset_code   <= 4'd5;
      ack_toggle    <= 1'b0;
      command_seen  <= 1'b0;
    end else begin
      if (frame_counter == FRAME_CYCLES - 1) begin
        frame_counter <= {COUNTER_WIDTH{1'b0}};
      end else begin
        frame_counter <= frame_counter + 1'b1;
      end

      if (ui_in[1]) begin
        pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code  <= 4'd5;
      end else if (ui_in[2]) begin
        pulse_cycles <= MIN_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code  <= 4'd0;
      end else if (ui_in[3]) begin
        pulse_cycles <= MAX_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code  <= 4'd9;
      end else if (rx_valid) begin
        if (rx_data >= "0" && rx_data <= "9") begin
          preset_code  <= rx_data[3:0];
          pulse_cycles <= digit_to_pulse_cycles(rx_data[3:0]);
          ack_toggle   <= ~ack_toggle;
          command_seen <= 1'b1;
        end else if (rx_data == "c" || rx_data == "C") begin
          preset_code  <= 4'd5;
          pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
          ack_toggle   <= ~ack_toggle;
          command_seen <= 1'b1;
        end else if (rx_data == "m") begin
          preset_code  <= 4'd0;
          pulse_cycles <= MIN_PULSE_CYCLES[COUNTER_WIDTH-1:0];
          ack_toggle   <= ~ack_toggle;
          command_seen <= 1'b1;
        end else if (rx_data == "M") begin
          preset_code  <= 4'd9;
          pulse_cycles <= MAX_PULSE_CYCLES[COUNTER_WIDTH-1:0];
          ack_toggle   <= ~ack_toggle;
          command_seen <= 1'b1;
        end
      end
    end
  end

  assign uo_out[0] = (frame_counter < pulse_cycles);
  assign uo_out[1] = ack_toggle;
  assign uo_out[5:2] = preset_code;
  assign uo_out[6] = command_seen;
  assign uo_out[7] = rx_busy;
  assign uio_out = 8'b0;
  assign uio_oe = 8'b0;

  wire _unused = &{ena, uio_in, ui_in[7:4]};

endmodule
