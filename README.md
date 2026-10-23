# Structural Verilog + FPGA flow

(Section for the main README.)

## What gets generated

`verilog.py` turns the **minimized** SOP or POS (the same cover `msop` / `mpos` print)
into a structural Verilog module built only from primitive gates (`not`, `and`, `or`, `buf`):

```
python3 verilog.py -e "F = A'B + AC"                              # SOP, full mode, out/
python3 verilog.py -e "F = A'B + AC" --form pos --mode basic --out out
python3 verilog.py myfunction.eqn --out out                       # same input files as synth.py
```

```verilog
module F_sop (
    input  wire A, B, C,
    output wire F
);
    wire A_n, p_0, p_1;

    not  g_not_A (A_n, A);
    and  g_and_0 (p_0, A_n, B);
    and  g_and_1 (p_1, A, C);
    or   g_or_out (F, p_0, p_1);
endmodule
```

How the netlist is built (`verilog.py`):
- one NOT per variable that appears complemented, shared by every term
- SOP: one AND per product term, then one OR; POS: one OR per sum term, then one AND
- POS comes from the cover of F' (DeMorgan), the same one `mpos` prints
- a single-literal term uses the wire directly (no 1-input gate)
- constant functions become `buf (F, 1'b0)` / `buf (F, 1'b1)`
- invented names all contain `_`, so they can't clash with variable names

| File in `out/` | Source | Purpose |
|---|---|---|
| `F_sop.v` / `F_pos.v` | generated | structural circuit |
| `tb_F_sop.v` | generated | exhaustive self-checking testbench (all 2^n inputs vs. the truth table) |
| `top.v` | generated port map | Nexys4 DDR wrapper (port names match the course XDC) |
| `Nexys4DDR_Master.xdc` | course-provided (`fpga/`) | constraints, **basic** mode |
| `Nexys4DDR_full.xdc` | course XDC + extra lines uncommented (`fpga/`) | constraints, **full** mode |
| `seg7_mux.v` | hand-written (`fpga/`) | 8-digit 7-segment driver (full mode) |
| `build.tcl`, `program.tcl` | hand-written (`fpga/`) | Vivado batch build / program |

## Board modes (Nexys4 DDR, part xc7a100tcsg324-1)

Both use the port names from the course's `Nexys4DDR_Master.xdc` (`swt`, `led`, `CA`..`CG`, `AN`, `DP`, `LED16_*`).

**basic**: the master XDC exactly as given (only `swt[7:0]` and `led[7:0]` enabled), up to 8 inputs.

| Board | Meaning |
|---|---|
| `swt[n-1] .. swt[0]` | inputs, first variable on the highest switch, so the switches read as the minterm number in binary |
| `led[7]` | F |
| `led[6:0]` | shows which input switches are on |

**full** (default): `Nexys4DDR_full.xdc` is the same file with the clock, `swt`/`led` 8–15, RGB LED16
and the 7-segment lines uncommented (as the file's header says to do). Up to 16 inputs.

| Board | Meaning |
|---|---|
| `swt[n-1] .. swt[0]` | inputs (same order as above) |
| `led[n-1:0]` | shows which input switches are on |
| RGB `LED16` | green = F is 1, red = F is 0 |
| 7-seg left digits | minterm number in hex |
| 7-seg right digits | `F` and the output value |

## Simulate

```
cd out
iverilog -o sim F_sop.v tb_F_sop.v && vvp sim      # prints PASS / FAIL
```
`python3 check_verilog.py` does this automatically for 48 functions (96 simulations: SOP and POS, both board modes).

## Build and program

```
cd out
vivado -mode batch -source build.tcl     # -> top.bit, utilization.rpt, timing.rpt
vivado -mode batch -source program.tcl   # board plugged in over USB
```
Or in the Vivado GUI: add the `.v` files (not `tb_*`) and the `.xdc` from `out/`,
set `top` as top, part `xc7a100tcsg324-1`, then Generate Bitstream.
*RTL Analysis → Schematic* shows the generated gates inside the `core` instance.
