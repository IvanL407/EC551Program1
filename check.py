"""
check.py - quick self-test for the engine (no Verilog needed).

Run from the project folder:   python3 tests/check.py

Part 1 compares against answers worked out by hand.
Part 2 builds random functions and checks every printed form by feeding it
back through the parser: if the text really means the same function, the
truth table it produces must match the original.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from canonical import on_set, off_set, canonical_sop, canonical_pos
from cover import literal_count
from custom import find_static1_hazards
from inputs import parse_function
from minimize import sop_text, pos_text
from parse import truth_table
from synth import Analysis

failures = 0


def check(label, got, want):
    global failures
    ok = got == want
    failures += not ok
    print(("  ok    " if ok else "  FAIL  ") + label + ("" if ok else f"\n        got  {got!r}\n        want {want!r}"))


def lits(cover):
    return sum(literal_count(c) for c in cover)


print("Part 1: known answers")

a = Analysis(parse_function("F = A'B + AC"))
check("A'B+AC: ON-set", a.on, [2, 3, 5, 7])
check("A'B+AC: OFF-set", a.off, [0, 1, 4, 6])
check("A'B+AC: prime implicants (F)", len(a.primes_f), 3)
check("A'B+AC: essential primes (F)", len(a.ess_f), 2)
check("A'B+AC: minimized SOP", sop_text(a.cover_f, a.f.names), "A'B + AC")
check("A'B+AC: minimized POS", pos_text(a.cover_i, a.f.names), "(A + B)(A' + C)")
check("A'B+AC: SOP literals canonical->min", (3 * len(a.on), lits(a.cover_f)), (12, 4))
check("A'B+AC: one static-1 hazard", len(find_static1_hazards(a.cover_f, a.f.tt, a.f.names)), 1)
check("A'B+AC: canonical SOP", canonical_sop(a.on, a.f.names), "A'BC' + A'BC + AB'C + ABC")
check("A'B+AC: canonical POS", canonical_pos(a.off, a.f.names),
      "(A + B + C)(A + B + C')(A' + B + C)(A' + B' + C)")

a = Analysis(parse_function("F = AB' + A'B"))                    # XOR cannot be simplified
check("XOR: nothing saved", (2 * len(a.on), lits(a.cover_f)), (4, 4))
check("XOR: no hazards", find_static1_hazards(a.cover_f, a.f.tt, a.f.names), [])

a = Analysis(parse_function("F(A,B,C) = m(0,1,2,5,6,7)"))        # cyclic: no essentials
check("cyclic: 6 primes", len(a.primes_f), 6)
check("cyclic: 0 essentials", len(a.ess_f), 0)
check("cyclic: 3 terms, 6 literals", (len(a.cover_f), lits(a.cover_f)), (3, 6))

check("tautology A+A'", parse_function("F = A + A'").tt, [1, 1])
check("contradiction AA'", parse_function("F = AA'").tt, [0, 0])
check("maxterm list == minterm list", parse_function("F(A,B,C) = M(0,1,4,6)").tt,
      parse_function("F(A,B,C) = m(2,3,5,7)").tt)
check("declared order matters", parse_function("F(C,B,A) = A'B + AC").tt != parse_function("F = A'B + AC").tt, True)

print("\nPart 2: 300 random functions, every printed form re-parsed")
random.seed(551)
bad = 0
for _ in range(300):
    n = random.randint(1, 5)
    names = list("ABCDE"[:n])
    tt = [int(random.random() < random.choice([0.2, 0.5, 0.8])) for _ in range(2 ** n)]
    inv = [1 - v for v in tt]
    a = Analysis(parse_function(f"F({','.join(names)}) = m({','.join(str(m) for m in on_set(tt))})"))
    forms = {
        "canonical SOP": (canonical_sop(a.on, names), tt),
        "canonical POS": (canonical_pos(a.off, names), tt),
        "inverse SOP": (canonical_sop(a.off, names), inv),
        "inverse POS": (canonical_pos(a.on, names), inv),
        "minimized SOP": (sop_text(a.cover_f, names), tt),
        "minimized POS": (pos_text(a.cover_i, names), tt),
    }
    for label, (text, want) in forms.items():
        if truth_table(text, declared=names)[1] != want:
            bad += 1
            print(f"  FAIL  {label}: n={n} tt={tt} text={text}")
    if len(a.on) + len(a.off) != 2 ** n:
        bad += 1
failures += bad
print("  ok    all forms match" if bad == 0 else f"  {bad} problem(s)")

print("\n" + ("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED"))
sys.exit(1 if failures else 0)