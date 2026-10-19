"""
canonical.py - Step 4: canonical SOP / POS, their inverses, and ON/OFF-set counts.
 
Covers assignment items 1, 2, 3, 4, 9 and 10.
 
Vocabulary (for n variables, minterm number m = n-bit pattern):
  minterm m  = the AND of ALL n variables that is 1 only at input pattern m.
               bit 1 -> variable as is, bit 0 -> complemented.   m5=101 -> AB'C
  maxterm M  = the OR of ALL n variables that is 0 only at input pattern M.
               bit 0 -> variable as is, bit 1 -> complemented.   M5=101 -> (A' + B + C')
               (a maxterm is the opposite of a minterm: bits are flipped)
 
  canonical SOP of F = OR of the minterms where F = 1   (the ON-set)
  canonical POS of F = AND of the maxterms where F = 0  (the OFF-set)
 
The inverse function F' is 1 exactly where F is 0, and 0 exactly where F is 1,
so the same two formulas work with the two sets swapped:
  canonical SOP of F' = OR of minterms at F's OFF-set
  canonical POS of F' = AND of maxterms at F's ON-set
"""

def on_set(tt):
    """Minterm numbers where the function is 1."""
    return [m for m, v in enumerate(tt) if v]

def off_set(tt):
    """Minterm numbers where the function is not 1."""
    return [m for m, v in enumerate(tt) if not v]

def _literals(m, names, one_means_plain):
    """List the n literals for pattern m.
 
    one_means_plain=True  -> minterm style:  1 -> A,  0 -> A'
    one_means_plain=False -> maxterm style:  0 -> A,  1 -> A'
    """
    n = len(names)
    bits = format(m, f"0{n}b")
    return [name if (b == "1") == one_means_plain else name + "'" for b, name in zip(bits, names)]

def product_term(m, names):
    """Full minterm as a product string, e.g. 5 -> "AB'C"."""
    # Names longer than one character would run together ("x1x2"), so use '*'.
    sep = "" if all(len(x) == 1 for x in names) else "*"
    return sep.join(_literals(m, names, True))

def sum_term(m, names):
    """Full maxterm as a parenthesized sum, e.g. 5 -> "(A' + B + C')"."""
    return "(" + " + ".join(_literals(m, names, False)) + ")"

def canonical_sop(ones, names):
    """OR of the minterms listed in `ones`. No minterms -> the constant 0."""
    if not ones:
        return "0"
    return " + ".join(product_term(m, names) for m in ones)

def canonical_pos(zeros, names):
    """AND of the maxterms listed in `zeros`. No maxterms -> the constant 1."""
    if not zeros:
        return "1"
    return "".join(sum_term(m, names) for m in zeros)

if __name__ == "__main__":
    from parse import truth_table
 
    names, tt = truth_table("A'B + AC")
    on, off = on_set(tt), off_set(tt)
 
    print("F = A'B + AC     variables:", names)
    print("[1] canonical SOP     F  =", canonical_sop(on, names))
    print("[2] canonical POS     F  =", canonical_pos(off, names))
    print("[3] inverse SOP       F' =", canonical_sop(off, names))
    print("[4] inverse POS       F' =", canonical_pos(on, names))
    print("[9]  ON-set minterms :", len(on), " m", tuple(on))
    print("[10] OFF-set maxterms:", len(off), " M", tuple(off))
