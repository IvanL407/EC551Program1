"""
cover.py - Step 3: essential prime implicants and the minimum cover.

Step 2 gave us ALL prime implicants. A minimized SOP only needs enough of
them to cover every ON-set minterm. Two questions:

  1. Which primes are ESSENTIAL?  A prime is essential if some minterm is
     covered by that prime and by no other prime. We have no choice: it must
     be in the answer.
  2. For the minterms the essentials do not cover, which primes do we add?
     We search for the cheapest choice. "Cheapest" = fewest literals first,
     then fewest product terms (the assignment asks for literal minimization).

The exact search can take exponentially long on big functions, so it starts
from a quick greedy answer and stops after NODE_LIMIT steps. If the limit is
hit the answer is still a valid cover, just not guaranteed to be the minimum;
`last_search_exact` tells the caller which happened.
"""
from qm import prime_implicants, covers, cube_to_product

NODE_LIMIT = 100_000          # search steps allowed before settling for the best found
last_search_exact = True      # set by every call to minimum_cover


def literal_count(cube):
    """Number of literals in the product a cube represents (dashes are free)."""
    return sum(c != "-" for c in cube)


def essential_primes(primes, minterms, n):
    """Primes that are the only cover of at least one minterm."""
    essential = set()
    for m in minterms:
        covering = [p for p in primes if covers(p, m, n)]
        if len(covering) == 1:              # only one prime can cover m -> forced
            essential.add(covering[0])
    return sorted(essential)


def minimum_cover(primes, minterms, n):
    """Return a cheap list of primes covering every minterm (the cheapest, unless
    the search limit is hit - see last_search_exact)."""
    global last_search_exact
    last_search_exact = True

    essential = essential_primes(primes, minterms, n)

    # Minterms still uncovered after taking all essentials.
    uncovered = frozenset(
        m for m in minterms if not any(covers(e, m, n) for e in essential)
    )
    if not uncovered:
        return sorted(essential)
    candidates = [p for p in primes if p not in essential]

    # Work out once which uncovered minterms each candidate covers, and which
    # candidates could cover each minterm. Everything below uses these sets, so
    # the search never calls covers() again.
    cov = {p: frozenset(m for m in uncovered if covers(p, m, n)) for p in candidates}
    choices = {m: [p for p in candidates if m in cov[p]] for m in uncovered}

    def cost(chosen):
        # Tuples compare left to right: total literals first, then number of terms.
        return (sum(literal_count(c) for c in chosen), len(chosen))

    # Greedy answer first: repeatedly take the prime that covers the most
    # still-uncovered minterms per unit cost. Fast, valid, maybe not optimal.
    # It also gives the search a bound to beat, which prunes most branches.
    greedy, left = [], set(uncovered)
    while left:
        p = max(candidates, key=lambda c: len(cov[c] & left) / (literal_count(c) * 1024 + 1))
        greedy.append(p)
        left -= cov[p]
    best = {"choice": greedy, "cost": cost(greedy), "nodes": 0}

    def search(left, chosen):
        best["nodes"] += 1
        if best["nodes"] > NODE_LIMIT:
            return
        c = cost(chosen)
        if c >= best["cost"]:
            return                          # no better than the best found: prune
        if not left:
            best["choice"], best["cost"] = list(chosen), c
            return
        # Branch on the minterm with the FEWEST covering primes (smallest tree).
        m = min(left, key=lambda x: len(choices[x]))
        for p in choices[m]:
            search(left - cov[p], chosen + [p])

    search(uncovered, [])
    last_search_exact = best["nodes"] <= NODE_LIMIT
    return sorted(essential + best["choice"])


def sop_string(cover, names):
    """Join the products of a cover into a readable SOP. Empty cover = 0."""
    if not cover:
        return "0"
    return " + ".join(cube_to_product(c, names) for c in cover)


if __name__ == "__main__":
    # 1) Essentials decide everything.
    on, n, names = [2, 3, 5, 7], 3, ["A", "B", "C"]
    primes = prime_implicants(on, n)
    ess = essential_primes(primes, on, n)
    cover = minimum_cover(primes, on, n)
    print("F = A'B + AC")
    print("  primes   :", primes)
    print("  essential:", ess)
    print("  cover    :", sop_string(cover, names))

    # 2) No essentials at all: a "cyclic" function, so the search must choose.
    on = [0, 1, 2, 5, 6, 7]
    primes = prime_implicants(on, n)
    ess = essential_primes(primes, on, n)
    cover = minimum_cover(primes, on, n)
    print("\nF = m(0,1,2,5,6,7)")
    print("  primes   :", primes)
    print("  essential:", ess)
    print("  cover    :", sop_string(cover, names))