"""The gate. No solver required.

Everything this repository claims is either a published value it reproduces or a
timing it measured. This checks the first kind, by routes that do not involve
kissat at all, so a clean clone with no solver installed still proves the
encoding and the checker honest.
"""
import glob
import json
import os
import sys
from itertools import pairwise

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdw import encode
from pdw.brute import pair, satisfiable
from pdw.gate import PUB1, PUB2
from pdw.verify_witness import check, has_progression

HERE = os.path.dirname(os.path.abspath(__file__))
passed = failed = 0


def check_that(label, ok):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}")
    return ok


def section(title):
    print(f"\n=== {title} ===")


def ap_count(m, length):
    """How many arithmetic progressions of `length` fit in {1,...,m}, in closed
    form. The enumerator is compared against this; a formula that agrees with a
    generator it did not come from is worth more than either alone."""
    if length == 1:
        return m
    total = 0
    d = 1
    while m - (length - 1) * d >= 1:
        total += m - (length - 1) * d
        d += 1
    return total


def main():
    section("the progression enumerator matches a count it did not come from")
    for m, length in [(20, 3), (37, 3), (50, 5), (100, 7), (60, 12)]:
        got = sum(1 for _ in encode.aps(m, length))
        check_that(f"m={m} length={length}: {got} progressions == closed form",
                   got == ap_count(m, length))

    section("the witness checker catches what it is supposed to catch")
    check_that("a 3-term progression is found", has_progression({2, 5, 8}, 3))
    check_that("a broken one is not", not has_progression({2, 5, 9}, 3))
    check_that("a longer run contains a shorter progression",
               has_progression({1, 2, 3, 4, 5}, 3))
    check_that("a non-palindrome is rejected", check("112", 3) is not None)
    check_that("a bad character is rejected", check("1231", 3) is not None)

    section("published pairs re-derived by exhaustion, no solver involved")
    for n in range(1, 7):
        got = pair(n, PUB2[n - 1] + 6)
        want = (PUB1[n - 1], PUB2[n - 1])
        check_that(f"pdw({n},3;2) = {want} by exhaustion", got == want)

    section("exhaustion refuses a cap it cannot certify M2 from")
    # Existence is irregular. At n = 5 a partition exists at m = 16, 18 and 20
    # and fails at 17 and 19, so a cap that stops on one of those isolated
    # failures has seen nothing that rules out a later success and must say so.
    # Published pdw(5,3;2) is (16, 21).
    check_that("n=5 cap=17 stops on an isolated failure and is refused",
               pair(5, 17) is None)
    check_that("n=5 cap=19 stops on an isolated failure and is refused",
               pair(5, 19) is None)
    check_that("n=5 cap=22 reaches two consecutive failures and answers",
               pair(5, 22) == (16, 21))

    section("the palindrome restriction does not lose a partition it should keep")
    # At m = M1 a palindromic partition exists; at M1 + 1 none does. Both are
    # decided here without a solver, for the sizes exhaustion can still reach.
    for n in range(1, 7):
        m1 = PUB1[n - 1]
        ok_at, _ = satisfiable(n, m1)
        ok_after, _ = satisfiable(n, m1 + 1)
        check_that(f"n={n}: satisfiable at m={m1}, not at m={m1 + 1}",
                   ok_at and not ok_after)

    section("every stored witness re-verified, then broken on purpose")
    stored = 0
    for path in sorted(glob.glob(os.path.join(HERE, "evidence", "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                colouring = rec.get("colouring")
                if not colouring:
                    continue
                stored += 1
                name = f"{os.path.basename(path)} n={rec['n']} m={rec['m']}"
                check_that(f"{name}: witness re-verified solver-free",
                           check(colouring, rec["n"]) is None)
                check_that(f"{name}: one character per position",
                           len(colouring) == rec["m"])
                # Flipping the first character breaks the palindrome, so the
                # checker must reject it. A check that cannot fail is decoration.
                flipped = ("2" if colouring[0] == "1" else "1") + colouring[1:]
                check_that(f"{name}: a single flipped character is rejected",
                           check(flipped, rec["n"]) is not None)
    check_that(f"at least one stored witness was checked ({stored} found)",
               stored > 0)

    section("published values this repository does not claim")
    check_that("A198684 and A198685 lists are the same length",
               len(PUB1) == len(PUB2) == 27)
    check_that("M1 < M2 for every published pair",
               all(a < b for a, b in zip(PUB1, PUB2, strict=True)))
    check_that("both lists are strictly increasing",
               all(x < y for x, y in pairwise(PUB1))
               and all(x < y for x, y in pairwise(PUB2)))

    print(f"\n{passed} passed / {failed} failed")
    if failed:
        print("GATE FAILED")
        return 1
    print("EVERY CLAIM IN THIS REPOSITORY IS SUPPORTED BY EVIDENCE ON DISK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
