"""
circuit.py - input type 2: a digital combinational logic CIRCUIT (gates + wires).

The assignment asks for two kinds of input:
  1. a Boolean algebraic function   -> synth.py  (e.g. F = A'B + AC)
  2. a combinational circuit        -> this file (a graph of gates)

Format: ISCAS ".bench", a standard netlist format used for benchmark circuits.
Each line is one node of the graph; a gate's inputs are its edges.

    # 2:1 multiplexer built from NAND gates
    INPUT(S)
    INPUT(A)
    INPUT(B)
    OUTPUT(F)
    Sn = NOT(S)
    n1 = NAND(A, Sn)
    n2 = NAND(B, S)
    F  = NAND(n1, n2)

Gates: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUF (any number of inputs, except
NOT/BUF which take one). Lines can be in any order; '#' starts a comment.

How it works: the circuit is evaluated for every input combination to get a
truth table. From then on it is exactly the same as an algebraic input, so
all 12 synth.py commands (and verilog.py) work on it unchanged.

    python3 circuit.py tests/mux.bench -c all          run commands, then exit
    python3 circuit.py tests/compare.bench              interactive prompt
    python3 circuit.py tests/adder.bench --output S     pick one output if there are several
"""
import re

from inputs import Func, MAX_VARS
from verilog import KEYWORDS

GATES = {"AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR", "BUF", "BUFF"}

# Inputs and outputs become Verilog port names and appear in printed
# expressions, so they must be a letter followed by letters/digits (no '_',
# which verilog.py keeps for the names it invents). Internal nets can be anything.
PORT_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
NET_RE = re.compile(r"[A-Za-z0-9_\[\]\.]+")
IO_RE = re.compile(r"(INPUT|OUTPUT)\s*\(\s*([^)]*?)\s*\)", re.I)
GATE_RE = re.compile(r"([^=\s]+)\s*=\s*([A-Za-z]+)\s*\(\s*(.*?)\s*\)")


class Circuit:
    def __init__(self):
        self.inputs = []          # input names, in file order
        self.outputs = []         # output names, in file order
        self.gates = {}           # net name -> (gate type, [input nets])


def parse_bench(text):
    """Read .bench text into a Circuit and check that it makes sense."""
    c = Circuit()
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        io = IO_RE.fullmatch(line)
        g = GATE_RE.fullmatch(line)
        if io:
            kind, name = io.group(1).upper(), io.group(2)
            if not PORT_RE.fullmatch(name):
                raise ValueError(f"line {lineno}: {kind.lower()} name {name!r} must be a letter "
                                 "followed by letters/digits (no '_')")
            if name in KEYWORDS:
                raise ValueError(f"line {lineno}: {name!r} is a Verilog keyword, pick another name")
            (c.inputs if kind == "INPUT" else c.outputs).append(name)
        elif g:
            out, kind, args = g.group(1), g.group(2).upper(), g.group(3)
            if kind not in GATES:
                raise ValueError(f"line {lineno}: unknown gate {kind!r} "
                                 f"(use {', '.join(sorted(GATES - {'BUFF'}))})")
            ins = [a.strip() for a in args.split(",") if a.strip()]
            for net in [out] + ins:
                if not NET_RE.fullmatch(net):
                    raise ValueError(f"line {lineno}: bad signal name {net!r}")
            if kind in ("NOT", "BUF", "BUFF") and len(ins) != 1:
                raise ValueError(f"line {lineno}: {kind} takes exactly one input")
            if not ins:
                raise ValueError(f"line {lineno}: {kind} gate has no inputs")
            if out in c.gates:
                raise ValueError(f"line {lineno}: {out!r} is driven by two gates")
            c.gates[out] = ("BUF" if kind == "BUFF" else kind, ins)
        else:
            raise ValueError(f"line {lineno}: cannot read {line!r}")

    # --- sanity checks on the whole graph ---
    if not c.inputs:
        raise ValueError("the circuit has no INPUT lines")
    if not c.outputs:
        raise ValueError("the circuit has no OUTPUT lines")
    if len(set(c.inputs)) != len(c.inputs):
        raise ValueError("an input is listed twice")
    for name in c.inputs:
        if name in c.gates:
            raise ValueError(f"{name!r} is an input but is also driven by a gate")
    for out, (_, ins) in c.gates.items():
        for net in ins:
            if net not in c.gates and net not in c.inputs:
                raise ValueError(f"gate {out!r} uses {net!r}, which is never defined")
    for out in c.outputs:
        if out not in c.gates and out not in c.inputs:
            raise ValueError(f"output {out!r} is never driven")
    if len(c.inputs) > MAX_VARS:
        raise ValueError(f"too many inputs ({len(c.inputs)}); the maximum is {MAX_VARS}")
    c.order = _topological_order(c)
    return c


def _topological_order(c):
    """Order the gates so every gate comes after the gates that feed it.
    A loop (a gate that depends on its own output) is not combinational -> error."""
    order, state = [], {}               # state: 1 = visiting, 2 = done

    def visit(net, path):
        if net in c.inputs or state.get(net) == 2:
            return
        if state.get(net) == 1:
            loop = path[path.index(net):] + [net]
            raise ValueError("feedback loop (not combinational): " + " -> ".join(loop))
        state[net] = 1
        for src in c.gates[net][1]:
            visit(src, path + [net])
        state[net] = 2
        order.append(net)

    for net in c.gates:
        visit(net, [])
    return order


def _gate_value(kind, vals):
    if kind == "AND":  return int(all(vals))
    if kind == "OR":   return int(any(vals))
    if kind == "NAND": return 1 - int(all(vals))
    if kind == "NOR":  return 1 - int(any(vals))
    if kind == "XOR":  return sum(vals) % 2
    if kind == "XNOR": return 1 - sum(vals) % 2
    if kind == "NOT":  return 1 - vals[0]
    return vals[0]                       # BUF


def simulate(c, assignment):
    """Value of every net for one input assignment {input name: 0/1}."""
    v = dict(assignment)
    for net in c.order:
        kind, ins = c.gates[net]
        v[net] = _gate_value(kind, [v[x] for x in ins])
    return v


def circuit_to_func(c, output=None):
    """Truth table of one output -> the same Func object inputs.py makes.
    The first INPUT line is the most significant bit, like F(A,B,C) declares order."""
    if output is None:
        output = c.outputs[0]
    if output not in c.outputs:
        raise ValueError(f"{output!r} is not an output (outputs: {', '.join(c.outputs)})")
    n = len(c.inputs)
    tt = []
    for m in range(2 ** n):
        env = {name: (m >> (n - 1 - i)) & 1 for i, name in enumerate(c.inputs)}
        tt.append(simulate(c, env)[output])
    return Func(output, list(c.inputs), tt)


def load_circuit(path, output=None):
    """Read a .bench file and return (Func, Circuit)."""
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError as e:
        raise ValueError(f"cannot read {path!r}: {e.strerror}")
    c = parse_bench(text)
    return circuit_to_func(c, output), c


def describe(c):
    """One-line summary of the circuit: size and depth (levels of gates)."""
    level = {x: 0 for x in c.inputs}
    for net in c.order:
        level[net] = 1 + max(level[x] for x in c.gates[net][1])
    kinds = {}
    for kind, _ in c.gates.values():
        kinds[kind] = kinds.get(kind, 0) + 1
    mix = ", ".join(f"{k} {kinds[k]}" for k in sorted(kinds))
    depth = max((level[o] for o in c.outputs), default=0)
    return (f"circuit: {len(c.inputs)} inputs, {len(c.outputs)} output(s), "
            f"{len(c.gates)} gates ({mix}), depth {depth}")


def main():
    import argparse
    from synth import Engine

    ap = argparse.ArgumentParser(description="EC551 logic synthesis engine - circuit (.bench) input")
    ap.add_argument("file", help=".bench circuit file")
    ap.add_argument("--output", help="which OUTPUT to analyse (default: the first one)")
    ap.add_argument("-c", "--cmd", action="append", default=[],
                    help="command to run (repeatable); omit for interactive mode")
    args = ap.parse_args()

    try:
        f, c = load_circuit(args.file, args.output)
    except ValueError as e:
        raise SystemExit(f"error: {e}")
    print(describe(c))
    if len(c.outputs) > 1:
        print(f"analysing output {f.name} (others: {', '.join(o for o in c.outputs if o != f.name)};"
              " pick with --output)")

    eng = Engine()
    eng.set_function(f)
    if args.cmd:                                 # batch mode
        for cmd in args.cmd:
            eng.execute(cmd)
        return
    print("EC551 Logic Synthesis Engine - type 'help' for commands")
    while True:                                  # interactive mode
        try:
            line = input("synth> ")
        except EOFError:
            break
        if not eng.execute(line):
            break


if __name__ == "__main__":
    main()
