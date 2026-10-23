"""
check_verilog.py - self-test for the structural Verilog generator (verilog.py).

Run from the project folder:   python3 check_verilog.py
Needs Icarus Verilog (iverilog + vvp):   sudo apt install iverilog   /   brew install icarus-verilog

For each function: write the structural module + exhaustive testbench, simulate
it, and expect PASS (output matches the engine's truth table for all 2^n inputs).
The board wrapper top.v is compiled too, in both board modes.
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inputs import parse_function
from minimize import sop_text, pos_text
from synth import Analysis
from verilog import write_all

if not shutil.which("iverilog"):
    raise SystemExit("iverilog not found - install Icarus Verilog first")


def simulate(func_text, form, mode="full"):
    """Return the PASS/FAIL line from the testbench, or the error text."""
    a = Analysis(parse_function(func_text))
    cover = a.cover_f if form == "sop" else a.cover_i
    text = sop_text(cover, a.f.names) if form == "sop" else pos_text(cover, a.f.names)
    with tempfile.TemporaryDirectory() as d:
        write_all(a.f, cover, form, text, d, mode)
        mod = f"{a.f.name}_{form}"
        exe = os.path.join(d, "sim")
        build = subprocess.run(["iverilog", "-g2005", "-o", exe,
                                os.path.join(d, f"{mod}.v"), os.path.join(d, f"tb_{mod}.v")],
                               capture_output=True, text=True)
        if build.returncode:
            return "compile error: " + build.stderr.strip()
        # the wrapper must compile too (synthesis itself happens in Vivado)
        extra = [os.path.join(d, "seg7_mux.v")] if mode == "full" else []
        top = subprocess.run(["iverilog", "-g2005", "-o", exe + "_top",
                              os.path.join(d, f"{mod}.v"), os.path.join(d, "top.v"), *extra],
                             capture_output=True, text=True)
        if top.returncode:
            return "top.v compile error: " + top.stderr.strip()
        run = subprocess.run(["vvp", "-n", exe], capture_output=True, text=True)
        verdict = [l for l in run.stdout.splitlines() if l.startswith(("PASS", "FAIL"))]
        return verdict[-1] if verdict else run.stdout + run.stderr


failures = 0

print("Part 1: hand-picked functions (incl. constants and single literals)")
fixed = ["F = A'B + AC", "F(A,B,C) = m(0,1,2,5,6,7)", "F = AB' + A'B", "F = A",
         "F = A'", "F = A + A'", "F = AA'", "G(x1,x2,x3,x4) = x1*x2 + !x3*(x1 + x4)"]
for t in fixed:
    for form, mode in (("sop", "full"), ("pos", "basic")):
        out = simulate(t, form, mode)
        ok = out.startswith("PASS")
        failures += not ok
        print(("  ok    " if ok else "  FAIL  ") + f"{t}  [{form}, {mode}]" + ("" if ok else f"\n        {out}"))

print("\nPart 2: 40 random functions, SOP and POS")
random.seed(463)
bad = 0
for _ in range(40):
    n = random.randint(1, 6)
    names = list("ABCDEF"[:n])
    ones = [m for m in range(2 ** n) if random.random() < 0.5]
    func = f"F({','.join(names)}) = m({','.join(map(str, ones))})"
    for form in ("sop", "pos"):
        out = simulate(func, form, random.choice(("full", "basic")))
        if not out.startswith("PASS"):
            bad += 1
            print(f"  FAIL  {func} [{form}]: {out}")
failures += bad
print("  ok    all pass in simulation" if bad == 0 else f"  {bad} problem(s)")

print("\n" + ("ALL VERILOG CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED"))
sys.exit(1 if failures else 0)
