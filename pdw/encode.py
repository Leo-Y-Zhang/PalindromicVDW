"""CNF for the palindromic mixed van der Waerden question pdw(n,3;2).

A palindromic 2-partition of {1,...,m} is a colouring c with c(i) = c(m+1-i).
One part must contain no 3-term arithmetic progression, the other no n-term
one. The pair pdw(n,3;2) records where such partitions stop existing:

    M1 = the largest M such that one exists for EVERY m <= M,
    M2 = the smallest M such that none exists for ANY m >= M.

Between M1 and M2 existence is irregular, which is why the answer is a pair
rather than a single number. A198684 holds M1, A198685 holds M2.

The palindrome is not a constraint added to the formula; it is built into the
variable map, so the search space is 2^ceil(m/2) rather than 2^m. That is the
whole reason these reach n = 27 while the unrestricted numbers stop near t = 9.
"""


def var_of(i, m):
    """Variable index (1-based) for position i under the palindrome i <-> m+1-i."""
    return min(i, m + 1 - i)


def aps(m, length):
    """Every arithmetic progression of the given length inside {1,...,m}."""
    if length <= 0:
        return
    if length == 1:
        for a in range(1, m + 1):
            yield (a,)
        return
    d = 1
    while a_max(m, length, d) >= 1:
        for a in range(1, a_max(m, length, d) + 1):
            yield tuple(a + j * d for j in range(length))
        d += 1


def a_max(m, length, d):
    """Largest start a with a + (length-1)*d <= m."""
    return m - (length - 1) * d


def build(n, m):
    """Return (num_vars, clauses) for pdw(n,3;2) at size m.

    p_v true means the positions mapping to v lie in the part that must avoid
    3-term progressions; false means the part that must avoid n-term ones.
    """
    nv = (m + 1) // 2
    clauses = []

    for ap in aps(m, 3):
        lits = sorted({-var_of(i, m) for i in ap}, key=abs)
        clauses.append(lits)

    for ap in aps(m, n):
        lits = sorted({var_of(i, m) for i in ap})
        clauses.append(lits)

    return nv, clauses


def to_dimacs(nv, clauses):
    out = [f"p cnf {nv} {len(clauses)}"]
    out.extend(" ".join(str(x) for x in c) + " 0" for c in clauses)
    return "\n".join(out) + "\n"


def colouring_from_model(model, m):
    """Model (list of signed ints) -> string over {1,2}, one character per position.

    Character '1' is the part avoiding 3-term progressions.
    """
    true_vars = {abs(x) for x in model if x > 0}
    return "".join("1" if var_of(i, m) in true_vars else "2" for i in range(1, m + 1))
