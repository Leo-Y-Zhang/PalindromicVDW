"""Exhaustive ground truth for small m, by enumerating palindromic colourings.

There are 2^ceil(m/2) of them, so this is only usable for the first few n --
which is exactly what it is for: it decides the same instances the SAT encoding
decides, by a completely different route, so the two can be made to disagree.
"""
from itertools import product

from pdw.verify_witness import check


def satisfiable(n, m):
    """(bool, witness or None) by exhaustion over palindromic colourings."""
    half = (m + 1) // 2
    for bits in product("12", repeat=half):
        left = "".join(bits)
        # mirror; for odd m the middle character is shared
        colouring = left + left[::-1][m % 2:]
        if check(colouring, n) is None:
            return True, colouring
    return False, None


def pair(n, m_cap):
    """Return (M1, M2) for pdw(n,3;2) by exhaustion, or None if m_cap is too low.

    M1 = last m before the first failure; M2 = one past the last success.
    """
    first_fail = None
    last_ok = None
    for m in range(1, m_cap + 1):
        ok, _ = satisfiable(n, m)
        if ok:
            last_ok = m
        elif first_fail is None:
            first_fail = m
    if first_fail is None or last_ok is None or last_ok >= m_cap:
        return None
    return first_fail - 1, last_ok + 1
