`default_nettype none
`timescale 1ns / 1ps

module uart_rx8 #(
    parameter integer CLKS_PER_BIT = 25
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx_i,
    output reg  [7:0] data_o,
    output reg        valid_o,
    output wire       busy_o
);
  localparam [1:0] ST_IDLE  = 2'd0;
  localparam [1:0] ST_START = 2'd1;
  localparam [1:0] ST_DATA  = 2'd2;
  localparam [1:0] ST_STOP  = 2'd3;

  reg [1:0] state;
  reg [15:0] clk_count;
  reg [2:0] bit_index;
  reg [7:0] shift_reg;
  reg rx_meta;
  reg rx_sync;

  always @(posedge clk) begin
    if (!rst_n) begin
      state     <= ST_IDLE;
      clk_count <= 16'd0;
      bit_index <= 3'd0;
      shift_reg <= 8'd0;
      data_o    <= 8'd0;
      valid_o   <= 1'b0;
      rx_meta   <= 1'b1;
      rx_sync   <= 1'b1;
    end else begin
      rx_meta <= rx_i;
      rx_sync <= rx_meta;
      valid_o <= 1'b0;

      case (state)
        ST_IDLE: begin
          if (!rx_sync) begin
            state     <= ST_START;
            clk_count <= CLKS_PER_BIT[15:0] >> 1;
          end
        end

        ST_START: begin
          if (clk_count == 16'd0) begin
            if (!rx_sync) begin
              state     <= ST_DATA;
              clk_count <= CLKS_PER_BIT - 1;
              bit_index <= 3'd0;
            end else begin
              state <= ST_IDLE;
            end
          end else begin
            clk_count <= clk_count - 16'd1;
          end
        end

        ST_DATA: begin
          if (clk_count == 16'd0) begin
            shift_reg[bit_index] <= rx_sync;
            clk_count <= CLKS_PER_BIT - 1;
            if (bit_index == 3'd7) begin
              state <= ST_STOP;
            end else begin
              bit_index <= bit_index + 3'd1;
            end
          end else begin
            clk_count <= clk_count - 16'd1;
          end
        end

        default: begin
          if (clk_count == 16'd0) begin
            state <= ST_IDLE;
            if (rx_sync) begin
              data_o  <= shift_reg;
              valid_o <= 1'b1;
            end
          end else begin
            clk_count <= clk_count - 16'd1;
          end
        end
      endcase
    end
  end

  assign busy_o = (state != ST_IDLE);

endmodule
