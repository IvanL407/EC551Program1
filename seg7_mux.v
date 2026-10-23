// seg7_mux.v - hand-written 8-digit 7-segment driver for the Nexys4 DDR.
//
// The board has 8 digits but only one set of segment pins (CA..CG), so we
// light ONE digit at a time and cycle through all 8 fast enough that the eye
// sees them all on at once ("multiplexing").
//
//   counter bits [19:17] pick the digit: 100 MHz / 2^20 = ~95 full sweeps per second
//   anodes AN and segments are ACTIVE LOW on this board (0 = on)
`timescale 1ns / 1ps

module seg7_mux (
    input  wire        clk,       // 100 MHz
    input  wire [31:0] digits,    // 8 hex digits, [31:28] = leftmost (AN7)
    input  wire [7:0]  blank,     // 1 = keep this digit dark
    output reg  [7:0]  an,        // digit enables, active low
    output reg  [6:0]  seg        // {g,f,e,d,c,b,a}, active low
);
    reg [19:0] count = 20'd0;
    always @(posedge clk) count <= count + 20'd1;

    wire [2:0] sel = count[19:17];
    wire [3:0] nib = digits[sel*4 +: 4];

    always @(*) begin
        an = 8'hFF;
        if (!blank[sel]) an[sel] = 1'b0;
        case (nib)                     //   gfedcba
            4'h0: seg = 7'b1000000;
            4'h1: seg = 7'b1111001;
            4'h2: seg = 7'b0100100;
            4'h3: seg = 7'b0110000;
            4'h4: seg = 7'b0011001;
            4'h5: seg = 7'b0010010;
            4'h6: seg = 7'b0000010;
            4'h7: seg = 7'b1111000;
            4'h8: seg = 7'b0000000;
            4'h9: seg = 7'b0010000;
            4'hA: seg = 7'b0001000;
            4'hB: seg = 7'b0000011;
            4'hC: seg = 7'b1000110;
            4'hD: seg = 7'b0100001;
            4'hE: seg = 7'b0000110;
            default: seg = 7'b0001110; // F
        endcase
    end
endmodule
