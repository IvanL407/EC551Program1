
"""
parse.py - Step 1: turn a Boolean expression string into a truth table.
 
Pipeline:   text  --tokenize-->  tokens  --Parser-->  tree  --evaluate-->  truth table
 
Example:    "A'B + AC"
  tokens:   A ' B + A C
  tree:     ("or", ("and", ("not", A), B), ("and", A, C))
  table:    one 0/1 entry per minterm (every combination of the inputs)
  
Accepted syntax:
    +  or  |          OR
    *  &  .  or none  AND   ("AB" means A AND B; "x1*x2" for longer names)
    '  (after)        NOT   (A')
    !  ~  (before)    NOT   (!A)
    ( )               grouping
    0  1              constants
Variable names are one letter followed by optional digits: A, x3, B12.
"""

import re # used for pattern matching, searching, text manipulation with strings
 
# ---------------------------------------------------------------------------
# 1. TOKENIZER: split the string into meaningful pieces
# ---------------------------------------------------------------------------

TOKEN = re.compile(r"\s*(?:([A-Za-z]\d*)|([01])|([+|*&.!~()']))")

def tokenize(text):
    """Return a list of (kind, value) pairs, e.g. [("var","A"), ("'","'"), ...].
 
    The last token is always ("end", ...), so the parser can look one token
    ahead without ever running off the end of the list.
    """

    text = text.rstrip() # removes trailing whitespace
    pos = 0
    tokens = []
    while pos < len(text): # iterate through string
        m = TOKEN.match(text, pos) # re.match(): if match is found, return Match object, else returns None
        if not m: # nothing matched
            raise ValueError(f"illegal character {text[pos:].strip()[0]!r}")
        
        pos = m.end() # move past the token we matched
        var, const, op = m.groups() # returns tuple of all captured groups, exactly one of these three is not None

        if var:
            tokens.append(("var", var))
        elif const:
            tokens.append(("const", int(const)))
        else:
            tokens.append((op, op))
    tokens.append(("end", "end of input"))
    return tokens

# ---------------------------------------------------------------------------
# 2. PARSER: build a tree that respects operator precedence
# ---------------------------------------------------------------------------

class Parser:
    """Recursive-descent parser. There is one method per precedence level, and
    each level calls the next-tighter one, so tighter operators end up deeper
    in the tree and are evaluated first.
 
        or_    ->  handles +          (lowest precedence, binds loosest)
        and_   ->  handles * and AB   (binds tighter than +)
        unary  ->  handles ' and !    (binds tightest)
        atom   ->  a variable, a constant, or a ( parenthesized expr )
 
    So  A'B + AC  parses as  ((A')B) + (AC), which is the usual convention.
 
    The tree is made of plain tuples:
        ("var", "A")   ("const", 1)   ("not", x)   ("and", x, y)   ("or", x, y)
    """
    def __init__(self, text):
        self.toks = tokenize(text)
        self.i = 0 # index of the token we are looking at
        self.vars = set() # every variable name seen (collected in atom())
    
    # --- helpers ---
    def peek(self):
        return self.toks[self.i][0]
    
    def next(self):
        tok = self.toks[self.i]
        self.i += 1
        return tok
    
    def parse(self):
        tree= self.or_()
        if self.peek() != "end":
            raise ValueError(f"unexpected {self.toks[self.i][1]!r}")
        return tree
    
    def or_(self):
        tree = self.and_()
        while self.peek() in ("+", "|"):
            self.next()
            tree = ("or", tree, self.and_())
        return tree
    
    def and_(self):
        tree = self.unary()
        while True:
            kind = self.peek()
            if kind in ("*", "&", "."):
                self.next()
                tree = ("and", tree, self.unary())
            elif kind in ("var", "const", "(", "!", "~"):
                tree = ("and", tree, self.unary())
            else:
                return tree
            
    def unary(self):
        if self.peek() in ("!", "~"):
            self.next()
            return ("not", self.unary())
        tree = self.atom()
        while self.peek() == "'":
            self.next()
            tree = ("not", tree)
        return tree
    
    def atom(self):
        kind, value = self.next()
        if kind == "var":
            self.vars.add(value)
            return ("var", value)
        if kind == "const":
            return ("const", value)
        if kind == "(":
            tree = self.or_()
            if self.next()[0] != ")":
                raise ValueError("missing ')'")
            return tree
        raise ValueError(f"expected a variable, constant or '(' but found {value!r}")
    
# ---------------------------------------------------------------------------
# 3. EVALUATOR + TRUTH TABLE
# ---------------------------------------------------------------------------

def evaluate(node, env):
    """Compute the 0/1 value of a tree.
 
    env maps each variable name to its current 0/1 value, e.g. {"A": 1, "B": 0}.
    """
    kind = node[0]
    if kind == "var":
        return env[node[1]] # look the variable up
    if kind == "const":
        return node[1]
    if kind == "not":
        return 1 - evaluate(node[1], env) # flip 0 <-> 1
    left = evaluate(node[1], env)
    right = evaluate(node[2], env)
    return (left & right) if kind == "and" else (left | right)

def truth_table(text, declared=None):
    """Return (variable_names, table).
 
    table[m] is the function's value for minterm m. The FIRST variable is the
    most significant bit of m, so for names ["A","B","C"], minterm 5 = 101
    means A=1, B=0, C=1.
 
    declared: optional list fixing the variable order, e.g. ["C","B","A"].
    If omitted, variables are sorted alphabetically.
    """
    parser = Parser(text)
    tree = parser.parse()
    names = declared or sorted(parser.vars)
    n = len(names)

    table = []
    for m in range(2 ** n):
        env = {name: (m >> (n - 1 - i)) & 1 for i, name in enumerate(names)}
        table.append(evaluate(tree, env))
    return names, table
    
# ---------------------------------------------------------------------------
# Quick demo:  python3 parse.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    names, tt = truth_table("A'B + AC")
    print(names, tt, "minterms:", [m for m, v in enumerate(tt) if v])
 
    # Same function, different variable order -> the table changes, because
    # the bit positions (and therefore the minterm numbers) change.
    print(truth_table("A'B + AC", declared=["C", "B", "A"]))
 
    print(truth_table("x1*x2' + !x3 (x1 + x2)")[0])
 
    for bad in ["A + + B", "(A + B", "A $ B"]:
        try:
            truth_table(bad)
        except ValueError as e:
            print("error:", e)

