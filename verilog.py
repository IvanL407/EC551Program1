"""
verilog.py - Step 8: write the minimized circuit out as structural Verilog.

Covers output requirement 3 (structural Verilog) and feeds requirement 4 (FPGA).

"Structural" means we only INSTANTIATE primitive gates (not, and, or, buf) and
wire them together. No assign statements, no always blocks, no operators.
The circuit is exactly the minimized expression the engine printed:

  SOP  F = A'B + AC        POS  F = (A + B)(A' + C)

     A --[not]-- A_n           A --[not]-- A_n
     A_n, B --[and]-- p_0      A, B   --[or]--- s_0
     A, C   --[and]-- p_1      A_n, C --[or]--- s_1
     p_0, p_1 --[or]-- F       s_0, s_1 --[and]-- F

Rules that keep the netlist small and legal:
  * one NOT gate per variable that appears complemented (shared by all terms)
  * a term with a single literal needs no gate - its wire is used directly
  * if there is only one term, a buf drives the output (a primitive can't
    have its output tied straight to another wire without an assign)
  * constant functions (F = 0 or F = 1) become  buf (F, 1'b0)  /  buf (F, 1'b1)

Every name we invent contains an underscore (A_n, p_0, s_0, g_and_0).
Variable names are a letter plus digits only, so an invented name can never
collide with a variable.

Files written by write_all():
  <F>_<form>.v       the structural module                  (generated)
  tb_<F>_<form>.v    exhaustive testbench, all 2^n inputs     (generated)
  top.v              Nexys4 DDR wrapper: switches -> module   (generated port map)
  + the board files copied from fpga/ (hand-written / course-provided), see BOARD_FILES

Two board modes, both using the course's Nexys4DDR_Master.xdc port names (swt, led, ...):
  basic  the master XDC exactly as given: only swt[7:0] and led[7:0] are enabled.
         Inputs on the switches, F on led[7]. Up to 8 inputs.
  full   Nexys4DDR_full.xdc = the same file with the clock, swt/led 8..15, RGB LED16
         and the 7-segment pins uncommented. Up to 16 inputs, adds the display.
"""
import os
import shutil

# Board files (XDC, seg7_mux.v, tcl scripts) live in fpga/ if that folder exists,
# otherwise right next to this file (flat repo layout).
_HERE = os.path.dirname(os.path.abspath(__file__))
FPGA_DIR = os.path.join(_HERE, "fpga") if os.path.isdir(os.path.join(_HERE, "fpga")) else _HERE
BOARD_FILES = {
    "basic": ("Nexys4DDR_Master.xdc", "build.tcl", "program.tcl"),
    "full":  ("Nexys4DDR_full.xdc", "seg7_mux.v", "build.tcl", "program.tcl"),
}
SWITCHES = {"basic": 8, "full": 16}    # switches enabled in each constraint file

# A few Verilog keywords a user could plausibly type as a function name.
KEYWORDS = {"and", "or", "not", "nand", "nor", "xor", "xnor", "buf", "wire", "reg",
            "input", "output", "module", "endmodule", "begin", "end", "if", "else",
            "assign", "always", "initial", "case", "for", "integer", "parameter"}


# ---- step 1: cube -> list of literals ------------------------------------------------

def _literals(cube, names, form):
    """Literals of one term as (variable, complemented?) pairs.

    SOP: the cube is a product of F.    '0' -> A',  '1' -> A
    POS: the cube is a product of F'.  DeMorgan flips every literal, so the
         sum term of F has                '1' -> A',  '0' -> A
    """
    flip = "0" if form == "sop" else "1"
    return [(name, c == flip) for c, name in zip(cube, names) if c != "-"]


def _wire(lit):
    name, neg = lit
    return name + "_n" if neg else name


# ---- step 2: build the netlist -------------------------------------------------------

def build_netlist(cover, names, form="sop", out="F"):
    """Return (gate_lines, wire_names, stats) for the minimized cover.

    cover: list of cubes. For form="sop" these are the cubes of F;
           for form="pos" they are the cubes of F' (Analysis.cover_i).
    """
    term_gate, final_gate = ("and", "or") if form == "sop" else ("or", "and")
    tag = "p" if form == "sop" else "s"           # p_k = product term, s_k = sum term
    terms = [_literals(c, names, form) for c in cover]

    lines, wires = [], []
    stats = {"not": 0, "and": 0, "or": 0, "buf": 0, "gate_inputs": 0}

    def gate(kind, inst, output, inputs):
        lines.append(f"    {kind:<4} {inst} ({output}, {', '.join(inputs)});")
        stats[kind] += 1
        if kind != "buf":
            stats["gate_inputs"] += len(inputs)

    # Constant cases.
    #   SOP: no terms -> F = 0;  a term with no literals is the constant 1 -> F = 1
    #   POS: no terms -> F = 1;  a term with no literals is the constant 0 -> F = 0
    empty_value, full_value = ("1'b0", "1'b1") if form == "sop" else ("1'b1", "1'b0")
    if not terms:
        gate("buf", "g_const", out, [empty_value])
        return lines, wires, stats
    if any(len(t) == 0 for t in terms):
        gate("buf", "g_const", out, [full_value])
        return lines, wires, stats

    # Inverters: one per variable that shows up complemented, in variable order.
    need_not = {name for t in terms for name, neg in t if neg}
    for name in names:
        if name in need_not:
            wires.append(name + "_n")
            gate("not", f"g_not_{name}", name + "_n", [name])

    # One gate per term (single-literal terms just reuse the literal's wire).
    term_wires = []
    for k, t in enumerate(terms):
        if len(t) == 1:
            term_wires.append(_wire(t[0]))
        else:
            w = f"{tag}_{k}"
            wires.append(w)
            gate(term_gate, f"g_{term_gate}_{k}", w, [_wire(l) for l in t])
            term_wires.append(w)

    # Final gate combines the terms.
    if len(term_wires) == 1:
        gate("buf", "g_out", out, term_wires)
    else:
        gate(final_gate, f"g_{final_gate}_out", out, term_wires)
    return lines, wires, stats


def gate_summary(stats):
    parts = [f"{stats[k]} {k.upper()}" for k in ("not", "and", "or", "buf") if stats[k]]
    total = sum(stats[k] for k in ("not", "and", "or", "buf"))
    return f"{', '.join(parts)}  ({total} gates, {stats['gate_inputs']} gate inputs)"


# ---- step 3: text of the files ---------------------------------------------------------

def port_name(f):
    """Output port name. Rename if it clashes with an input or a keyword."""
    out = f.name
    if out in f.names or out in KEYWORDS:
        out += "_out"
    return out


def module_name(f, form):
    return f"{f.name}_{form}"


def structural_module(f, cover, form, expr_text):
    """The complete structural Verilog module as a string."""
    out = port_name(f)
    lines, wires, stats = build_netlist(cover, f.names, form, out)
    mod = module_name(f, form)
    header = [
        f"// {mod}.v - generated by the EC551 logic synthesis engine (verilog.py)",
        f"// Function : {f.name}({','.join(f.names)})",
        f"// Minimized {form.upper()}: {f.name} = {expr_text}",
        f"// Gates    : {gate_summary(stats)}",
        "// Structural only: primitive gate instances, no assign/always.",
        "",
        "`timescale 1ns / 1ps",
        "",
        f"module {mod} (",
        f"    input  wire {', '.join(f.names)},",
        f"    output wire {out}",
        ");",
    ]
    body = []
    if wires:
        body.append(f"    wire {', '.join(wires)};")
        body.append("")
    body += lines
    return "\n".join(header + body + ["endmodule", ""]), stats


def testbench(f, form):
    """Exhaustive self-checking testbench: tries every input pattern and compares
    the module's output to the truth table the engine computed from the input."""
    n, mod, out = len(f.names), module_name(f, form), port_name(f)
    # EXPECTED[i] = F at minterm i. Verilog writes the MSB first, so reverse the table.
    bits = "".join(str(v) for v in reversed(f.tt))
    regs = ", ".join(f.names)
    ports = ", ".join(f".{x}({x})" for x in f.names) + f", .{out}({out})"
    return f"""// tb_{mod}.v - generated exhaustive testbench for {mod}
// Applies all {2 ** n} input patterns and checks the output against the truth table.
`timescale 1ns / 1ps

module tb_{mod};
    reg  {regs};
    wire {out};
    localparam [{2 ** n - 1}:0] EXPECTED = {2 ** n}'b{bits};

    {mod} dut ({ports});

    integer i, errors;
    initial begin
        errors = 0;
        for (i = 0; i < {2 ** n}; i = i + 1) begin
            {{{regs}}} = i;          // first variable = MSB, same as the minterm number
            #1;
            if ({out} !== EXPECTED[i]) begin
                errors = errors + 1;
                $display("FAIL  m%0d: {out}=%b, expected %b", i, {out}, EXPECTED[i]);
            end
        end
        if (errors == 0) $display("PASS  {mod}: all {2 ** n} input patterns match");
        else             $display("FAILED  {mod}: %0d of {2 ** n} patterns wrong", errors);
        $finish;
    end
endmodule
"""


def top_wrapper(f, form, mode="full"):
    """Nexys4 DDR top level. Port names match the course's Nexys4DDR_Master.xdc
    (swt, led, CA..CG, AN, DP, LED16_*).

    Switch mapping: the first variable (MSB) goes on the highest switch used and
    the last variable on swt[0], so the switch row reads as the minterm number
    in binary."""
    n, mod, out = len(f.names), module_name(f, form), port_name(f)
    mapping = ", ".join(f".{x}(swt[{n - 1 - k}])" for k, x in enumerate(f.names))
    table = "\n".join(f"//   swt[{n - 1 - k}] -> {x}" for k, x in enumerate(f.names))
    core = f"""    wire f_out;

    // The generated structural circuit. keep_hierarchy stops Vivado from
    // dissolving it into the wrapper, so it stays visible in the schematic.
    (* keep_hierarchy = "yes" *)
    {mod} core ({mapping}, .{out}(f_out));
"""
    if mode == "basic":
        mask = f"8'h{(1 << n) - 1:02X}"
        return f"""// top.v - Nexys4 DDR wrapper for {mod}, BASIC mode (port map generated by verilog.py)
// Uses only the pins enabled in the course's Nexys4DDR_Master.xdc: swt[7:0], led[7:0].
//
// Inputs:
{table}
// Outputs:
//   led[7]       = {f.name}
//   led[6:0]     shows which input switches are on
`timescale 1ns / 1ps

module top (
    input  wire [7:0] swt,
    output wire [7:0] led
);
{core}
    wire [7:0] used = swt & {mask};     // only the switches that are real inputs
    assign led = {{f_out, used[6:0]}};
endmodule
"""

    mask = f"16'h{(1 << n) - 1:04X}"
    digits = (n + 3) // 4                         # hex digits needed for the minterm number
    # Digits that stay lit: AN0 (value), AN1 ("F") and AN4.. for the minterm number.
    lit = {0, 1} | {4 + d for d in range(digits)}
    blank = "8'b" + "".join("0" if j in lit else "1" for j in range(7, -1, -1))
    return f"""// top.v - Nexys4 DDR wrapper for {mod}, FULL mode (port map generated by verilog.py)
// Constraints: Nexys4DDR_full.xdc (course master XDC with the extra pins uncommented).
//
// Inputs:
{table}
// Outputs:
//   led[{n - 1}:0]     shows which input switches are on
//   LED16 (RGB)  green when {f.name} = 1, red when {f.name} = 0
//   7-segment    left digits: minterm number (hex)   right digits: "F" and the value
`timescale 1ns / 1ps

module top (
    input  wire        CLK100MHZ,
    input  wire [15:0] swt,
    output wire [15:0] led,
    output wire        LED16_R, LED16_G, LED16_B,
    output wire        CA, CB, CC, CD, CE, CF, CG,   // segments, active low
    output wire        DP,
    output wire [7:0]  AN                            // digit enables, active low
);
{core}
    wire [15:0] used = swt & {mask};    // only the switches that are real inputs
    assign led = used;

    // RGB LED at 1/16 brightness (full brightness is painful to look at).
    reg [3:0] pwm = 4'd0;
    always @(posedge CLK100MHZ) pwm <= pwm + 4'd1;
    wire dim = (pwm == 4'd0);
    assign LED16_G = dim &  f_out;
    assign LED16_R = dim & ~f_out;
    assign LED16_B = 1'b0;

    // digits[31:28] = leftmost digit (AN7) ... digits[3:0] = rightmost (AN0)
    wire [6:0] seg;                  // {{g,f,e,d,c,b,a}}
    seg7_mux display (
        .clk    (CLK100MHZ),
        .digits ({{used, 8'h00, 4'hF, 3'b000, f_out}}),
        .blank  ({blank}),           // 1 = digit off
        .an     (AN),
        .seg    (seg)
    );
    assign {{CG, CF, CE, CD, CC, CB, CA}} = seg;
    assign DP = 1'b1;                  // decimal points off
endmodule
"""


# ---- step 4: write everything ------------------------------------------------------------

def write_all(f, cover, form, expr_text, outdir, mode="full"):
    """Write the module, testbench, top wrapper and the board files for `mode`.
    Returns (list_of_paths, gate_stats)."""
    if form not in ("sop", "pos"):
        raise ValueError("form must be 'sop' or 'pos'")
    if mode not in BOARD_FILES:
        raise ValueError("board mode must be 'full' or 'basic'")
    if len(f.names) > SWITCHES[mode]:
        raise ValueError(f"{len(f.names)} variables but {mode} mode has {SWITCHES[mode]} switches"
                         + (" (try 'full')" if mode == "basic" else ""))
    os.makedirs(outdir, exist_ok=True)

    # Remove board files left over from the other mode, so Vivado never reads
    # two constraint files.
    other = {x for files in BOARD_FILES.values() for x in files} - set(BOARD_FILES[mode])
    if os.path.abspath(outdir) == os.path.abspath(FPGA_DIR):
        other = set()                  # never delete the repo's own copies of the board files
    for name in other:
        stale = os.path.join(outdir, name)
        if os.path.exists(stale):
            os.remove(stale)

    mod = module_name(f, form)
    text, stats = structural_module(f, cover, form, expr_text)
    files = {
        f"{mod}.v": text,
        f"tb_{mod}.v": testbench(f, form),
        "top.v": top_wrapper(f, form, mode),
    }
    paths = []
    for name, body in files.items():
        p = os.path.join(outdir, name)
        with open(p, "w") as fh:
            fh.write(body)
        paths.append(p)
    for name in BOARD_FILES[mode]:
        dst = os.path.join(outdir, name)
        src = os.path.join(FPGA_DIR, name)
        if os.path.abspath(src) != os.path.abspath(dst):    # --out . in a flat layout
            shutil.copyfile(src, dst)
        paths.append(dst)
    return paths, stats


def main():
    """Command line, so this file works on its own next to the engine:

        python3 verilog.py -e "F = A'B + AC"                       SOP, full mode, out/
        python3 verilog.py -e "F = A'B + AC" --form pos --mode basic
        python3 verilog.py tests/example1.eqn --out build1
    """
    import argparse
    from inputs import parse_function, load_function_file
    from minimize import sop_text, pos_text
    from synth import Analysis

    ap = argparse.ArgumentParser(description="EC551: structural Verilog for the minimized function")
    ap.add_argument("file", nargs="?", help="file containing a function")
    ap.add_argument("-e", "--expr", help="function given directly, e.g. \"F = A'B + AC\"")
    ap.add_argument("--form", choices=("sop", "pos"), default="sop", help="minimized form to build")
    ap.add_argument("--mode", choices=("full", "basic"), default="full",
                    help="basic = course XDC as given (8 switches); full = with 7-seg/RGB/16 switches")
    ap.add_argument("--out", default="out", help="output folder (default out/)")
    args = ap.parse_args()
    if not (args.file or args.expr):
        ap.error("give a file or -e \"<function>\"")

    try:
        f = load_function_file(args.file) if args.file else parse_function(args.expr)
        a = Analysis(f)
        cover = a.cover_f if args.form == "sop" else a.cover_i
        text = sop_text(cover, f.names) if args.form == "sop" else pos_text(cover, f.names)
        paths, stats = write_all(f, cover, args.form, text, args.out, args.mode)
    except ValueError as e:
        raise SystemExit(f"error: {e}")
    print(f"[V] Structural Verilog ({args.form.upper()}, {args.mode} board mode): {f.name} = {text}")
    print(f"    gates: {gate_summary(stats)}")
    for p in paths:
        print(f"    wrote {p}")


if __name__ == "__main__":
    main()
