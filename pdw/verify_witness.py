"""Solver-free check of a claimed palindromic partition.

This reads the definition and nothing else. It shares no code with encode.py --
no variable map, no progression generator -- so a bug in the encoding cannot
hide inside the check that is supposed to catch it. Progressions are found here
by walking forward from each pair, not by the closed form the encoder uses.
"""


def is_palindrome(colouring):
    return colouring == colouring[::-1]


def has_progression(positions, length):
    """True if `positions` (a set of ints) contains an arithmetic progression
    of exactly the given length. Walks each (first, second) pair forward."""
    if length <= 0:
        return False
    if length == 1:
        return len(positions) > 0
    if length == 2:
        return len(positions) >= 2
    pos = sorted(positions)
    have = set(pos)
    for ai, a in enumerate(pos):
        for b in pos[ai + 1:]:
            d = b - a
            k = 2
            nxt = b + d
            while nxt in have:
                k += 1
                if k == length:
                    return True
                nxt += d
            # a progression longer than `length` also contains one of `length`
    return False


def check(colouring, n):
    """Return None if the colouring is a valid witness, else a reason string.

    `colouring` is a string over {'1','2'}: part 1 must avoid 3-term
    progressions, part 2 must avoid n-term ones.
    """
    if set(colouring) - {"1", "2"}:
        return "colouring uses characters other than 1 and 2"
    if not is_palindrome(colouring):
        return "colouring is not palindromic"
    part1 = {i + 1 for i, ch in enumerate(colouring) if ch == "1"}
    part2 = {i + 1 for i, ch in enumerate(colouring) if ch == "2"}
    if has_progression(part1, 3):
        return "part 1 contains a 3-term arithmetic progression"
    if has_progression(part2, n):
        return f"part 2 contains a {n}-term arithmetic progression"
    return None
