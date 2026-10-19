"""
inputs.py - Step 7a: read a Boolean function from a line of text or from a file.

parse.py only understands a bare expression ("A'B + AC"). This file wraps it
so the engine accepts the full set of input forms:

    A'B + AC                      bare expression (variables sorted)
    F = A'B + AC                  named
    F(A,B,C) = A'B + AC           names the variables AND fixes their order
    F(A,B,C) = m(2,3,5,7)         list of minterms (rows where F is 1)
    F(A,B,C) = M(0,1,4,6)         list of maxterms (rows where F is 0)

Comments start with '#' or '//'. A trailing ';' is ignored.
"""
import re
from dataclasses import dataclass

from parse import Parser, truth_table

MAX_VARS = 16          # the Nexys A7 has 16 slide switches

VAR_RE = re.compile(r"[A-Za-z]\d*")                  # same rule as the tokenizer
LHS_RE = re.compile(r"([A-Za-z_]\w*)\s*(?:\((.*)\))?")
LIST_RE = re.compile(r"([mM])\s*\(\s*([\d,\s]*)\)")


@dataclass
class Func:
    name: str          # output name, e.g. "F"
    names: list        # variable names; names[0] is the most significant bit
    tt: list           # truth table: tt[m] is 0 or 1


def _natural(var):
    """Sort key so x2 comes before x10 (plain sorting would put x10 first)."""
    return (var[0], int(var[1:]) if len(var) > 1 else -1)


def _strip_comment(line):
    for marker in ("#", "//"):
        line = line.split(marker, 1)[0]
    return line.strip()


def _check_count(n):
    if n < 1:
        raise ValueError("the function must contain at least one variable")
    if n > MAX_VARS:
        raise ValueError(f"too many variables ({n}); the maximum is {MAX_VARS}")


def parse_function(text):
    """Parse one line into a Func. Raises ValueError with a readable message."""
    text = _strip_comment(text).rstrip(";").strip()
    if not text:
        raise ValueError("empty input")

    name, declared = "F", None
    if "=" in text:
        lhs, rhs = (part.strip() for part in text.split("=", 1))
        m = LHS_RE.fullmatch(lhs)
        if not m:
            raise ValueError(f"invalid left-hand side {lhs!r}")
        name = m.group(1)
        if m.group(2) is not None:                       # F(A,B,C) form
            declared = [v.strip() for v in m.group(2).split(",")]
            for v in declared:
                if not VAR_RE.fullmatch(v):
                    raise ValueError(f"invalid variable name {v!r} (use a letter plus digits)")
            if len(set(declared)) != len(declared):
                raise ValueError("duplicate variable in the declared list")
    else:
        rhs = text

    # --- minterm / maxterm list (needs the declared variable list) ---
    lm = LIST_RE.fullmatch(rhs)
    if lm and declared:
        n = len(declared)
        _check_count(n)
        nums = [int(x) for x in re.split(r"[,\s]+", lm.group(2).strip()) if x]
        for x in nums:
            if x >= 2 ** n:
                raise ValueError(f"term {x} is out of range for {n} variables (0..{2 ** n - 1})")
        is_max = lm.group(1) == "M"
        tt = [1 if is_max else 0] * (2 ** n)        # m(...): start all 0, set listed rows to 1
        for x in nums:                               # M(...): start all 1, set listed rows to 0
            tt[x] = 0 if is_max else 1
        return Func(name, declared, tt)

    # --- general expression ---
    parser = Parser(rhs)
    parser.parse()                                   # syntax check + collects variable names
    used = parser.vars
    if declared is not None:
        extra = sorted(used - set(declared))
        if extra:
            raise ValueError(f"variable {extra[0]!r} is used but not in the declared list")
        names = declared
    else:
        names = sorted(used, key=_natural)
    _check_count(len(names))                         # check BEFORE building a 2**n table
    return Func(name, names, truth_table(rhs, declared=names)[1])


def load_function_file(path):
    """Read the first non-empty, non-comment line of a file."""
    try:
        with open(path) as f:
            for line in f:
                if _strip_comment(line):
                    return parse_function(line)
    except OSError as e:
        raise ValueError(f"cannot read {path!r}: {e.strerror}")
    raise ValueError(f"no function found in {path!r}")