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
    parameter integer MAX_PULSE_CYCLES   = 50000,
    parameter integer FAILSAFE_FRAMES    = 32
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
  reg [COUNTER_WIDTH-1:0] target_pulse_cycles;
  reg [3:0] preset_code;
  reg ack_toggle;
  reg failsafe_active;
  reg sweep_active;
  reg sweep_direction;
  reg [7:0] inactivity_frames;

  wire [7:0] rx_data;
  wire rx_valid;
  wire rx_busy;
  wire frame_tick;
  wire override_center;
  wire override_min;
  wire override_max;
  wire cmd_digit;
  wire cmd_center;
  wire cmd_min;
  wire cmd_max;
  wire cmd_sweep;
  wire valid_command;
  wire control_activity;
  wire [3:0] sweep_next_code;
  wire sweep_next_direction;

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

  assign frame_tick = (frame_counter == FRAME_CYCLES - 1);
  assign override_center = ui_in[1];
  assign override_min = ui_in[2];
  assign override_max = ui_in[3];
  assign cmd_digit = rx_valid && (rx_data >= "0") && (rx_data <= "9");
  assign cmd_center = rx_valid && ((rx_data == "c") || (rx_data == "C"));
  assign cmd_min = rx_valid && (rx_data == "m");
  assign cmd_max = rx_valid && (rx_data == "M");
  assign cmd_sweep = rx_valid && ((rx_data == "s") || (rx_data == "S"));
  assign valid_command = cmd_digit || cmd_center || cmd_min || cmd_max || cmd_sweep;
  assign control_activity = override_center || override_min || override_max || valid_command || sweep_active;
  assign sweep_next_code = (preset_code == 4'd9) ? 4'd8 :
                           (preset_code == 4'd0) ? 4'd1 :
                           (sweep_direction ? (preset_code + 4'd1) : (preset_code - 4'd1));
  assign sweep_next_direction = (preset_code == 4'd9) ? 1'b0 :
                                (preset_code == 4'd0) ? 1'b1 :
                                sweep_direction;

  always @(posedge clk) begin
    if (!rst_n) begin
      frame_counter <= {COUNTER_WIDTH{1'b0}};
      pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
      target_pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
      preset_code <= 4'd5;
      ack_toggle <= 1'b0;
      failsafe_active <= 1'b0;
      sweep_active <= 1'b0;
      sweep_direction <= 1'b1;
      inactivity_frames <= 8'd0;
    end else begin
      if (frame_tick) begin
        frame_counter <= {COUNTER_WIDTH{1'b0}};
      end else begin
        frame_counter <= frame_counter + 1'b1;
      end

      if (override_center) begin
        target_pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code <= 4'd5;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (override_min) begin
        target_pulse_cycles <= MIN_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code <= 4'd0;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (override_max) begin
        target_pulse_cycles <= MAX_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code <= 4'd9;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (cmd_digit) begin
        target_pulse_cycles <= digit_to_pulse_cycles(rx_data[3:0]);
        preset_code <= rx_data[3:0];
        ack_toggle <= ~ack_toggle;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (cmd_center) begin
        target_pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code <= 4'd5;
        ack_toggle <= ~ack_toggle;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (cmd_min) begin
        target_pulse_cycles <= MIN_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code <= 4'd0;
        ack_toggle <= ~ack_toggle;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (cmd_max) begin
        target_pulse_cycles <= MAX_PULSE_CYCLES[COUNTER_WIDTH-1:0];
        preset_code <= 4'd9;
        ack_toggle <= ~ack_toggle;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b0;
      end else if (cmd_sweep) begin
        ack_toggle <= ~ack_toggle;
        failsafe_active <= 1'b0;
        sweep_active <= 1'b1;
        if (preset_code == 4'd9) begin
          sweep_direction <= 1'b0;
        end else begin
          sweep_direction <= 1'b1;
        end
      end

      if (frame_tick) begin
        if (control_activity) begin
          inactivity_frames <= 8'd0;
        end else if (inactivity_frames < FAILSAFE_FRAMES) begin
          inactivity_frames <= inactivity_frames + 8'd1;
        end

        if (!control_activity && (inactivity_frames == FAILSAFE_FRAMES - 1)) begin
          target_pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
          pulse_cycles <= CENTER_PULSE_CYCLES[COUNTER_WIDTH-1:0];
          preset_code <= 4'd5;
          failsafe_active <= 1'b1;
          sweep_active <= 1'b0;
        end else if (!override_center && !override_min && !override_max && !cmd_digit && !cmd_center && !cmd_min && !cmd_max && !cmd_sweep && sweep_active) begin
          target_pulse_cycles <= digit_to_pulse_cycles(sweep_next_code);
          pulse_cycles <= digit_to_pulse_cycles(sweep_next_code);
          preset_code <= sweep_next_code;
          sweep_direction <= sweep_next_direction;
        end else begin
          pulse_cycles <= target_pulse_cycles;
        end
      end
    end
  end

  assign uo_out[0] = (frame_counter < pulse_cycles);
  assign uo_out[1] = ack_toggle;
  assign uo_out[5:2] = preset_code;
  assign uo_out[6] = failsafe_active;
  assign uo_out[7] = sweep_active;
  assign uio_out = 8'b0;
  assign uio_oe = 8'b0;

  wire _unused = &{ena, rx_busy, uio_in, ui_in[7:4]};

endmodule
