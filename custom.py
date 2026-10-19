"""
custom.py - Step 6: the two custom commands.

  Custom #1 (item 11): truth table exporter - print a table or write a CSV.
  Custom #2 (item 12): static-1 hazard detection for the minimized SOP,
                       plus a hazard-free version of the cover.

What is a static-1 hazard?
  Picture the SOP as AND gates feeding one OR gate. Suppose the output should
  stay at 1 while a single input flips. If the flip turns one AND gate OFF a
  little before another AND gate turns ON, the OR gate briefly sees all zeros
  and the output glitches 1 -> 0 -> 1. This happens exactly when the two input
  patterns (the one before the flip and the one after) are BOTH in the ON-set
  but NO SINGLE product term covers both of them.
  The fix is to add a product term that covers the pair (the "consensus" term).
"""
import csv

from qm import covers
from cover import literal_count


# ---- Custom #1: truth table --------------------------------------------------

def truth_table_text(tt, names, label="F"):
    """A printable table, one row per minterm."""
    n = len(names)
    width = max(len(x) for x in names)
    rows = ["idx  " + " ".join(x.rjust(width) for x in names) + " | " + label]
    for m, v in enumerate(tt):
        bits = format(m, f"0{n}b")
        rows.append(f"{m:3}  " + " ".join(b.rjust(width) for b in bits) + f" | {v}")
    return "\n".join(rows)


def export_csv(path, tt, names, label="F"):
    """Write the full truth table to a CSV file (opens in Excel / Sheets)."""
    n = len(names)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["minterm", *names, label])
        for m, v in enumerate(tt):
            w.writerow([m, *format(m, f"0{n}b"), v])


# ---- Custom #2: static-1 hazards ----------------------------------------------

def find_static1_hazards(cover, tt, names):
    """Return a list of (minterm_before, minterm_after, toggling_variable).

    Look at every pair of ON-set patterns that differ in exactly one input.
    If no single cube of the cover contains both, that transition can glitch.
    """
    n = len(names)
    hazards = []
    for m in range(len(tt)):
        if not tt[m]:
            continue
        for i in range(n):
            bit = 1 << i
            if m & bit:
                continue                      # visit each pair once: m has 0 in this bit
            m2 = m | bit                      # the neighbour with that input flipped to 1
            if tt[m2] and not any(covers(c, m, n) and covers(c, m2, n) for c in cover):
                hazards.append((m, m2, names[n - 1 - i]))   # bit i belongs to names[n-1-i]
    return hazards


def hazard_free_cover(cover, primes, tt, names):
    """Add one prime implicant for each hazard so every adjacent pair is covered."""
    n = len(names)
    result = list(cover)
    for m, m2, _ in find_static1_hazards(cover, tt, names):
        for p in primes:
            if covers(p, m, n) and covers(p, m2, n):    # this prime bridges the gap
                if p not in result:
                    result.append(p)
                break
    return sorted(result)


def hazard_report(tt, names):
    """Run the full hazard analysis and print it."""
    from qm import prime_implicants
    from cover import minimum_cover
    from minimize import sop_text
    from canonical import on_set

    n, on = len(names), on_set(tt)
    primes = prime_implicants(on, n)
    cover = minimum_cover(primes, on, n)
    hazards = find_static1_hazards(cover, tt, names)

    print("[12] static-1 hazard analysis of the minimized SOP")
    print("     cover:", sop_text(cover, names))
    if not hazards:
        print("     no hazards: every adjacent ON-set pair sits inside one product term")
        return
    print(f"     {len(hazards)} hazard(s):")
    for m, m2, var in hazards:
        print(f"       {var} flips: {format(m, f'0{n}b')} <-> {format(m2, f'0{n}b')}"
              "  (no single term covers both)")
    safe = hazard_free_cover(cover, primes, tt, names)
    lits = lambda c: sum(literal_count(x) for x in c)
    print("     hazard-free:", sop_text(safe, names))
    print(f"     cost: {lits(cover)} -> {lits(safe)} literals, {len(cover)} -> {len(safe)} terms")


if __name__ == "__main__":
    from parse import truth_table

    names, tt = truth_table("A'B + AC")
    print("[11] truth table of F = A'B + AC")
    print(truth_table_text(tt, names))
    export_csv("truth_table.csv", tt, names)
    print("     (full table also written to truth_table.csv)\n")
    hazard_report(tt, names)