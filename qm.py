
"""
qm.py - Step 2: find all prime implicants with the Quine-McCluskey method.
 
A "cube" is a string with one character per variable:
    '0'  the variable appears complemented   (A')
    '1'  the variable appears uncomplemented (A)
    '-'  the variable does not appear (don't care)
So with variables A,B,C the cube "1-1" is the product A*C, and it covers
minterms 101 and 111. A cube with k dashes covers 2**k minterms.
 
Core idea: if two cubes differ in exactly ONE position, they can be merged
into one bigger cube with a dash there:   "010" + "011" -> "01-"
(because A'BC' + A'BC = A'B). Keep merging until nothing merges. Cubes that
never merged into anything bigger are the PRIME IMPLICANTS.
"""

from collections import defaultdict

def minterm_to_cube(m, n):
    """Minterm number -> n-bit string, first variable = most significant bit."""
    return format(m, f"0{n}b")

def combine(a, b):
    """Merge two cubes if they differ in exactly one position, else return None."""
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(diff) != 1:
        return None
    i = diff[0]
    if a[i] == "-" or b[i] == "-":
        return None
    return a[:i] + "-" + a[i + 1:]

def prime_implicants(minterms, n):
    """Return the sorted list of prime-implicant cubes for an ON-set.
 
    minterms: list of minterm numbers where the function is 1
    n:        number of variables
    """
    current = {minterm_to_cube(m, n) for m in minterms}
    primes = set()

    while current:
        # Group cubes by how many '1's they contain. Two cubes that differ in
        # exactly one bit must have counts that differ by exactly one, so we
        # only ever compare neighbouring groups (this is the "table" in the
        # classic QM method and avoids comparing every pair).

        groups = defaultdict(set)
        for cube in current:
            groups[cube.count("1")].add(cube)

        next_level = set()
        was_merged = set()
        for k in groups:
            for a in groups[k]:
                for b in groups.get(k + 1, ()):
                    merged = combine(a, b)
                    if merged:
                        next_level.add(merged)
                        was_merged.add(a)
                        was_merged.add(b)
        primes |= current - was_merged
        current = next_level

    return sorted(primes)

# --- helpers ---

def covers(cube, m, n):
    """True if the cube includes minterm m."""
    bits = format(m, f"0{n}b")
    return all(c == "-" or c == b for c, b in zip(cube, bits))

def cube_to_product(cube, names):
    """'01-' with names [A,B,C] -> "A'B". An all-dash cube is the constant 1."""
    out = [(name + "'" if c == "0" else name)
           for c, name in zip(cube, names) if c != "-"]
    return "".join(out) if out else "1"

if __name__ == "__main__":
    from parse import truth_table
 
    names, tt = truth_table("A'B + AC")
    on = [m for m, v in enumerate(tt) if v]
    primes = prime_implicants(on, len(names))
    print("ON-set:", on)
    for p in primes:
        covered = [m for m in on if covers(p, m, len(names))]
        print(f"  {p}  {cube_to_product(p, names):4}  covers {covered}")





