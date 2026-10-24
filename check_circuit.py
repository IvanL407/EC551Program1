"""
check_circuit.py - self-test for circuit (.bench) input.

Run from the project folder:   python3 check_circuit.py

Part 1: the example circuits in tests/ give the truth tables worked out by hand.
Part 2: 300 random circuits. Each one is also written as a Boolean expression
        and run through parse.py. The two truth tables must match, so the
        circuit simulator is checked against a completely separate piece of code.
Part 3: broken circuit files must give a clear error, not a crash.
Part 4: (if iverilog is installed) Verilog generated from the example circuits
        passes its exhaustive testbench.
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from circuit import parse_bench, circuit_to_func, load_circuit
from parse import truth_table

failures = 0


def check(label, got, want):
    global failures
    ok = got == want
    failures += not ok
    print(("  ok    " if ok else "  FAIL  ") + label + ("" if ok else f"\n        got  {got!r}\n        want {want!r}"))


def table(n, rule):
    """Truth table from a Python rule on the input bits (first input = MSB)."""
    return [rule(*[(m >> (n - 1 - i)) & 1 for i in range(n)]) for m in range(2 ** n)]


print("Part 1: example circuits")
t = lambda name: os.path.join(HERE, "tests", name)
f, _ = load_circuit(t("mux.bench"))
check("mux: F = S'A + SB", f.tt, table(3, lambda s, a, b: b if s else a))
f, _ = load_circuit(t("compare.bench"))
check("compare: GT = (A1A0 > B1B0)", f.tt, table(4, lambda a1, a0, b1, b0: int(2 * a1 + a0 > 2 * b1 + b0)))
f, _ = load_circuit(t("adder.bench"), "S")
check("adder: S = A xor B xor Cin", f.tt, table(3, lambda a, b, c: (a + b + c) % 2))
f, _ = load_circuit(t("adder.bench"), "Cout")
check("adder: Cout = majority", f.tt, table(3, lambda a, b, c: int(a + b + c >= 2)))
check("input order = INPUT line order", load_circuit(t("compare.bench"))[0].names, ["A1", "A0", "B1", "B0"])


print("\nPart 2: 300 random circuits vs. the expression parser")


def as_expr(kind, args):
    """The same gate written in the syntax parse.py reads."""
    a = [f"({x})" for x in args]
    if kind == "AND":  return " ".join(a)
    if kind == "OR":   return " + ".join(a)
    if kind == "NAND": return "(" + " ".join(a) + ")'"
    if kind == "NOR":  return "(" + " + ".join(a) + ")'"
    if kind == "NOT":  return a[0] + "'"
    if kind == "BUF":  return a[0]
    # XOR / XNOR of many inputs, built two at a time: x ^ y = x y' + x' y
    acc = a[0]
    for y in a[1:]:
        acc = f"(({acc})({y})' + ({acc})'({y}))"
    return acc if kind == "XOR" else f"({acc})'"


random.seed(551)
bad = 0
for trial in range(300):
    n = random.randint(1, 5)
    ins = list("ABCDE"[:n])
    nets, exprs, lines = list(ins), {x: x for x in ins}, [f"INPUT({x})" for x in ins]
    for g in range(random.randint(1, 8)):
        kind = random.choice(["AND", "OR", "NAND", "NOR", "XOR", "XNOR", "NOT", "BUF"])
        k = 1 if kind in ("NOT", "BUF") else random.randint(2, 3)
        args = [random.choice(nets) for _ in range(k)]
        name = f"n_{g}"
        lines.append(f"{name} = {kind}({', '.join(args)})")
        exprs[name] = as_expr(kind, [exprs[x] for x in args])
        nets.append(name)
    lines.insert(n, "OUTPUT(Y)")
    lines.append(f"Y = BUF({nets[-1]})")
    random.shuffle(lines)                      # file order must not matter
    c = parse_bench("\n".join(lines))
    got = circuit_to_func(c).tt
    want = truth_table(exprs[nets[-1]], declared=c.inputs)[1]   # shuffling also reorders INPUT lines
    if got != want:
        bad += 1
        print("  FAIL ", lines)
failures += bad
print("  ok    all 300 match" if bad == 0 else f"  {bad} mismatch(es)")


print("\nPart 3: broken files give clear errors")
broken = {
    "feedback loop": "INPUT(A)\nOUTPUT(F)\nx = AND(A, F)\nF = OR(x, A)",
    "undefined signal": "INPUT(A)\nOUTPUT(F)\nF = AND(A, B)",
    "unknown gate": "INPUT(A)\nOUTPUT(F)\nF = MUX(A, A)",
    "NOT with 2 inputs": "INPUT(A)\nINPUT(B)\nOUTPUT(F)\nF = NOT(A, B)",
    "no outputs": "INPUT(A)\nx = NOT(A)",
    "output never driven": "INPUT(A)\nOUTPUT(F)\nx = NOT(A)",
    "two gates drive one net": "INPUT(A)\nOUTPUT(F)\nF = NOT(A)\nF = BUF(A)",
    "underscore in input name": "INPUT(a_1)\nOUTPUT(F)\nF = NOT(a_1)",
    "Verilog keyword as input": "INPUT(or)\nOUTPUT(F)\nF = NOT(or)",
    "garbage line": "INPUT(A)\nOUTPUT(F)\nF = NOT(A)\nhello world",
}
for label, text in broken.items():
    try:
        parse_bench(text)
        check(label, "no error", "ValueError")
    except ValueError as e:
        check(f"{label:26} -> {e}", True, True)


print("\nPart 4: Verilog from circuits, simulated with Icarus Verilog")
if not shutil.which("iverilog"):
    print("  skipped (iverilog not installed)")
else:
    from synth import Analysis
    from minimize import sop_text, pos_text
    from verilog import write_all
    for name, output in (("mux.bench", None), ("compare.bench", None), ("adder.bench", "S"), ("adder.bench", "Cout")):
        f, _ = load_circuit(t(name), output)
        a = Analysis(f)
        for form, mode in (("sop", "full"), ("pos", "basic")):
            cover = a.cover_f if form == "sop" else a.cover_i
            text = sop_text(cover, f.names) if form == "sop" else pos_text(cover, f.names)
            with tempfile.TemporaryDirectory() as d:
                write_all(f, cover, form, text, d, mode)
                mod = f"{f.name}_{form}"
                exe = os.path.join(d, "sim")
                subprocess.run(["iverilog", "-o", exe, os.path.join(d, f"{mod}.v"),
                                os.path.join(d, f"tb_{mod}.v")], check=True)
                out = subprocess.run(["vvp", "-n", exe], capture_output=True, text=True).stdout
                check(f"{name} {f.name} [{form}, {mode}]", "PASS" in out, True)

print("\n" + ("ALL CIRCUIT CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED"))
sys.exit(1 if failures else 0)
