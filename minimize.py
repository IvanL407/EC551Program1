"""
minimize.py - Step 5: minimized SOP and POS, literals saved, and implicant counts.

Covers assignment items 5 and 6 (and the F' side of items 7 and 8).

Minimized SOP:  run Quine-McCluskey + cover on the ON-set of F.

Minimized POS:  there is no separate "POS algorithm". Instead:
    1. Minimize F' as an SOP (run the same code on F's OFF-set).
    2. Complement the answer with DeMorgan's law.
  If F' = P1 + P2 + ...  then  F = (P1 + P2 + ...)' = P1' * P2' * ...
  and the complement of a product is a sum of complemented literals:
      (A B' C)' = A' + B + C'
  so every cube of F' turns into one sum term of F, with each literal flipped.
  Complementing never changes how many literals there are, so the cheapest
  SOP for F' is exactly the cheapest POS for F.
"""
from qm import prime_implicants
from cover import essential_primes, minimum_cover, literal_count
from canonical import on_set, off_set


# ---- turning cubes into text ------------------------------------------------

def _sep(names):
    # Single-letter names can be written side by side (AB); longer ones need '*'.
    return "" if all(len(x) == 1 for x in names) else "*"


def product_text(cube, names):
    """Cube -> product term. '01-' -> A'B. All dashes -> 1."""
    lits = [name + "'" if c == "0" else name
            for c, name in zip(cube, names) if c != "-"]
    return _sep(names).join(lits) if lits else "1"


def sum_text(cube, names):
    """Cube of F' -> sum term of F (DeMorgan): 1 -> complemented, 0 -> plain.
    '01-' -> (A + B').  All dashes -> 0 (an empty OR is the constant 0)."""
    lits = [name + "'" if c == "1" else name
            for c, name in zip(cube, names) if c != "-"]
    return "(" + " + ".join(lits) + ")" if lits else "0"


def sop_text(cover, names):
    """Whole SOP. No cubes -> the constant 0."""
    if not cover:
        return "0"
    return " + ".join(product_text(c, names) for c in cover)


def pos_text(cover_of_inverse, names):
    """Whole POS built from the cover of F'. No cubes in F' -> F is the constant 1."""
    if not cover_of_inverse:
        return "1"
    terms = [sum_text(c, names) for c in cover_of_inverse]
    return "0" if "0" in terms else "".join(terms)


# ---- the full analysis ------------------------------------------------------

def analyze(tt, names):
    """Run everything for one function and return the results in a dict."""
    n = len(names)
    on, off = on_set(tt), off_set(tt)

    primes_f = prime_implicants(on, n)       # for the SOP side
    primes_i = prime_implicants(off, n)      # primes of F', for the POS side
    cover_f = minimum_cover(primes_f, on, n)
    cover_i = minimum_cover(primes_i, off, n)

    # Every canonical term has all n literals, so literal count = n * (number of terms).
    canon_sop_lits = n * len(on)
    canon_pos_lits = n * len(off)
    min_sop_lits = sum(literal_count(c) for c in cover_f)
    min_pos_lits = sum(literal_count(c) for c in cover_i)

    return {
        "sop": sop_text(cover_f, names),
        "pos": pos_text(cover_i, names),
        "sop_literals": (canon_sop_lits, min_sop_lits, canon_sop_lits - min_sop_lits),
        "pos_literals": (canon_pos_lits, min_pos_lits, canon_pos_lits - min_pos_lits),
        "sop_terms": (len(on), len(cover_f)),
        "pos_terms": (len(off), len(cover_i)),
        "primes": (len(primes_f), len(primes_i)),                       # (F, F')
        "essentials": (len(essential_primes(primes_f, on, n)),
                       len(essential_primes(primes_i, off, n))),
    }


def report(tt, names, label="F"):
    r = analyze(tt, names)
    c, m, s = r["sop_literals"]
    print(f"[5] minimized SOP   {label} = {r['sop']}")
    print(f"      literals: canonical {c} -> minimized {m}  (saved {s});"
          f" terms {r['sop_terms'][0]} -> {r['sop_terms'][1]}")
    c, m, s = r["pos_literals"]
    print(f"[6] minimized POS   {label} = {r['pos']}")
    print(f"      literals: canonical {c} -> minimized {m}  (saved {s});"
          f" terms {r['pos_terms'][0]} -> {r['pos_terms'][1]}")
    print(f"[7] prime implicants:     F (SOP) = {r['primes'][0]},  F' (POS) = {r['primes'][1]}")
    print(f"[8] essential primes:     F (SOP) = {r['essentials'][0]},  F' (POS) = {r['essentials'][1]}")


if __name__ == "__main__":
    from parse import truth_table

    names, tt = truth_table("A'B + AC")
    print("F = A'B + AC")
    report(tt, names)

    print("\nF = XOR(A,B)")
    names, tt = truth_table("AB' + A'B")
    report(tt, names)