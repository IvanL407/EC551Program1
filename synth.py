"""
synth.py - Step 7b: the command interface. Run this file.

    python3 synth.py tests/hazard.eqn -c all          run commands, then exit
    python3 synth.py -e "F = A'B + AC" -c msop -c mpos
    python3 synth.py tests/example1.eqn               interactive prompt

Each command is a thin wrapper that calls the module that does the real work:
    inputs.py    reading the function          canonical.py   items 1-4, 9, 10
    parse.py     expression -> truth table     minimize.py    text for items 5, 6
    qm.py        prime implicants              custom.py      items 11, 12
    cover.py     essentials + minimum cover
"""
import argparse
from functools import cached_property

import cover as cover_mod
from canonical import on_set, off_set, canonical_sop, canonical_pos
from cover import essential_primes, minimum_cover, literal_count
from custom import truth_table_text, export_csv, hazard_report
from inputs import parse_function, load_function_file
from minimize import product_text, sop_text, pos_text
from qm import prime_implicants

MAX_TERMS = 256     # cap on terms printed in one expression
MAX_LIST = 64       # cap on items printed in one list


def _list(numbers):
    """'1,3,5' style list, shortened if it is very long."""
    s = ",".join(str(x) for x in numbers[:MAX_LIST])
    if len(numbers) > MAX_LIST:
        s += f",... ({len(numbers) - MAX_LIST} more)"
    return s


class Analysis:
    """Results for one function. cached_property means each piece is computed
    the first time a command needs it, so cheap commands (csop, minterms) stay
    fast even when minimization would be slow."""

    def __init__(self, f):
        self.f, self.n = f, len(f.names)
        self.on, self.off = on_set(f.tt), off_set(f.tt)

    @cached_property
    def primes_f(self): return prime_implicants(self.on, self.n)        # F  -> SOP side
    @cached_property
    def primes_i(self): return prime_implicants(self.off, self.n)       # F' -> POS side
    @cached_property
    def ess_f(self): return essential_primes(self.primes_f, self.on, self.n)
    @cached_property
    def ess_i(self): return essential_primes(self.primes_i, self.off, self.n)
    @cached_property
    def cover_f(self):
        c = minimum_cover(self.primes_f, self.on, self.n)
        self.exact_f = cover_mod.last_search_exact      # False if the search hit its limit
        return c

    @cached_property
    def cover_i(self):
        c = minimum_cover(self.primes_i, self.off, self.n)
        self.exact_i = cover_mod.last_search_exact
        return c


HELP = """Commands:
  load <file>          load a function from a file
  expr <function>      enter a function, e.g.  expr F(A,B,C) = A'B + AC
  csop | cpos          [1][2] canonical SOP / POS
  icsop | icpos        [3][4] canonical SOP / POS of the inverse F'
  msop | mpos          [5][6] minimized SOP / POS, literals saved
  pi                   [7] prime implicant counts
  epi                  [8] essential prime implicant counts
  minterms | maxterms  [9][10] ON-set / OFF-set counts
  tt [file.csv]        [11] truth table (print, or export to CSV)
  hazard               [12] static-1 hazard detection
  all                  run items 1-12
  help | quit"""


class Engine:
    def __init__(self):
        self.f = None
        self.a = None

    # ---- loading -----------------------------------------------------------
    def set_function(self, f):
        self.f, self.a = f, Analysis(f)
        print(f"Loaded {f.name}({','.join(f.names)}): {self.a.n} variables, "
              f"{len(self.a.on)} ON-set minterms, {len(self.a.off)} OFF-set maxterms")

    # ---- items 1-4: canonical forms -----------------------------------------
    def _canon(self, item, title, label, idx, sop):
        names, n = self.f.names, self.a.n
        text = (canonical_sop if sop else canonical_pos)(idx[:MAX_TERMS], names)
        if len(idx) > MAX_TERMS:
            text += f" ... ({len(idx) - MAX_TERMS} more terms)"
        print(f"[{item}] {title}")
        print(f"    {label} = {'m' if sop else 'M'}({_list(idx)})")
        print(f"    {label} = {text}")
        print(f"    terms: {len(idx)}, literals: {n * len(idx)}")

    def csop(self):  self._canon(1, "Canonical SOP", self.f.name, self.a.on, True)
    def cpos(self):  self._canon(2, "Canonical POS", self.f.name, self.a.off, False)
    def icsop(self): self._canon(3, "Inverse canonical SOP", self.f.name + "'", self.a.off, True)
    def icpos(self): self._canon(4, "Inverse canonical POS", self.f.name + "'", self.a.on, False)

    # ---- items 5-6: minimized forms ------------------------------------------
    def msop(self):
        a, names = self.a, self.f.names
        canon, mini = a.n * len(a.on), sum(literal_count(c) for c in a.cover_f)
        print("[5] Literal-minimized SOP")
        print(f"    {self.f.name} = {sop_text(a.cover_f, names)}")
        print(f"    literals: canonical {canon} -> minimized {mini}  (saved {canon - mini})")
        print(f"    product terms: {len(a.on)} -> {len(a.cover_f)}")
        if not a.exact_f:
            print("    note: search limit reached; valid cover, but not guaranteed minimum")

    def mpos(self):
        a, names = self.a, self.f.names
        canon, mini = a.n * len(a.off), sum(literal_count(c) for c in a.cover_i)
        print("[6] Literal-minimized POS")
        print(f"    {self.f.name} = {pos_text(a.cover_i, names)}")
        print(f"    literals: canonical {canon} -> minimized {mini}  (saved {canon - mini})")
        print(f"    sum terms: {len(a.off)} -> {len(a.cover_i)}")
        if not a.exact_i:
            print("    note: search limit reached; valid cover, but not guaranteed minimum")

    # ---- items 7-8: implicants -------------------------------------------------
    def _implicants(self, item, title, cubes_f, cubes_i):
        names = self.f.names
        print(f"[{item}] {title}")
        print(f"    F  (for SOP): {len(cubes_f)}")
        for c in cubes_f[:MAX_LIST]:
            print(f"      {c}  {product_text(c, names)}")
        if len(cubes_f) > MAX_LIST:
            print("      ...")
        print(f"    F' (for POS): {len(cubes_i)}")

    def pi(self):  self._implicants(7, "Prime implicants", self.a.primes_f, self.a.primes_i)
    def epi(self): self._implicants(8, "Essential prime implicants", self.a.ess_f, self.a.ess_i)

    # ---- items 9-10: set sizes ---------------------------------------------------
    def minterms(self):
        print(f"[9] ON-set minterms\n    count = {len(self.a.on)}   m({_list(self.a.on)})")

    def maxterms(self):
        print(f"[10] OFF-set maxterms\n    count = {len(self.a.off)}   M({_list(self.a.off)})")

    # ---- items 11-12: custom ---------------------------------------------------------
    def tt(self, path=None):
        f = self.f
        if path:
            export_csv(path, f.tt, f.names, f.name)
            print(f"[11] truth table ({len(f.tt)} rows) written to {path}")
            return
        print("[11] Truth table")
        print(truth_table_text(f.tt[:MAX_LIST], f.names, f.name))      # a prefix of the rows
        if len(f.tt) > MAX_LIST:
            print(f"... ({len(f.tt) - MAX_LIST} more rows; use 'tt file.csv' to export all)")

    def hazard(self):
        hazard_report(self.f.tt, self.f.names)

    def all(self):
        for step in (self.csop, self.cpos, self.icsop, self.icpos, self.msop, self.mpos,
                     self.pi, self.epi, self.minterms, self.maxterms, self.tt, self.hazard):
            step()

    # ---- command dispatch ----------------------------------------------------------------
    COMMANDS = {"csop", "cpos", "icsop", "icpos", "msop", "mpos", "pi", "epi",
                "minterms", "maxterms", "tt", "hazard", "all"}

    def execute(self, line):
        """Run one command line. Returns False when the user wants to quit."""
        parts = line.split()
        if not parts:
            return True
        cmd, args = parts[0].lower(), parts[1:]
        try:
            if cmd in ("quit", "exit", "q"):
                return False
            if cmd in ("help", "?"):
                print(HELP)
            elif cmd == "load":
                if not args:
                    raise ValueError("usage: load <file>")
                self.set_function(load_function_file(args[0]))
            elif cmd == "expr":
                text = line.split(None, 1)[1] if len(parts) > 1 else ""
                self.set_function(parse_function(text))
            elif cmd in self.COMMANDS:
                if self.f is None:
                    raise ValueError("no function loaded (use 'load <file>' or 'expr <function>')")
                getattr(self, cmd)(*args[:1]) if cmd == "tt" else getattr(self, cmd)()
            else:
                print(f"unknown command {cmd!r} (type 'help')")
        except Exception as e:                   # show a message instead of a traceback
            print(f"error: {e}")
        return True


def main():
    ap = argparse.ArgumentParser(description="EC551 logic synthesis engine")
    ap.add_argument("file", nargs="?", help="file containing a function")
    ap.add_argument("-e", "--expr", help="function given directly, e.g. \"F = A'B + AC\"")
    ap.add_argument("-c", "--cmd", action="append", default=[],
                    help="command to run (repeatable); omit for interactive mode")
    args = ap.parse_args()

    eng = Engine()
    if args.file:
        eng.execute(f"load {args.file}")
    elif args.expr:
        eng.execute(f"expr {args.expr}")

    if args.cmd:                                  # batch mode
        if eng.f is None:
            raise SystemExit(1)
        for c in args.cmd:
            eng.execute(c)
        return

    print("EC551 Logic Synthesis Engine - type 'help' for commands")
    while True:                                   # interactive mode
        try:
            line = input("synth> ")
        except EOFError:
            break
        if not eng.execute(line):
            break


if __name__ == "__main__":
    main()