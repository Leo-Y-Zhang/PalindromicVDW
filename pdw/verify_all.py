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

from pdw import encode, reach
from pdw.brute import pair, satisfiable
from pdw.gate import PUB1, PUB2
from pdw.verify_witness import check, has_progression

HERE = os.path.dirname(os.path.abspath(__file__))
passed = failed = 0

# What README.md and PREFLIGHT.md say the SAT route found in gate.jsonl, and
# where they say it stopped. Recomputed below from the records, never trusted:
# a record deleted, re-labelled or moved to a different m would otherwise
# leave these sentences standing with nothing under them.
CLAIMED_AGREEMENT = {"instances": 34, "agree": 33, "disagree": 0, "undecided": 1}
CLAIMED_SAT_RANGE = (15, 23)
LAST_FULLY_DECIDED = 22


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


def implied(n):
    """The four decisions a published pair implies, as {m: satisfiable}."""
    m1, m2 = PUB1[n - 1], PUB2[n - 1]
    return {m1: True, m1 + 1: False, m2 - 1: True, m2: False}


def same(value, expected):
    """Equal and of the same JSON type: 1.0 == 1 and True == 1 in Python."""
    return type(value) is type(expected) and value == expected


def record_problems(rec):
    """Everything inconsistent inside one solver record, as reasons.

    The size is recomputed in closed form (one clause per progression, before
    any deduplication, which build() does not do) and the verdict has to agree
    with the solver's return code, since that is what it was read from.
    """
    problems = []
    n, m = rec["n"], rec["m"]
    if not same(rec.get("vars"), (m + 1) // 2):
        problems.append(f"{rec.get('vars')} variables, not ceil(m/2) = {(m + 1) // 2}")
    clauses = ap_count(m, 3) + ap_count(m, n)
    if not same(rec.get("clauses"), clauses):
        problems.append(f"{rec.get('clauses')} clauses, not {clauses}")
    verdict, code = rec.get("verdict"), rec.get("returncode")
    if verdict == "SAT_WITNESS_VERIFIED":
        if not same(code, 10) or rec.get("sat", True) is not True or not rec.get("colouring"):
            problems.append("a verified witness needs returncode 10, sat true and "
                            "a colouring")
    elif verdict == "UNSAT":
        if not same(code, 20) or rec.get("sat") is not False or "colouring" in rec:
            problems.append("an UNSAT needs returncode 20, sat false and no colouring")
    elif verdict == "TIMEOUT":
        if code is not None or rec.get("timed_out", True) is not True \
                or "sat" in rec or "colouring" in rec:
            problems.append("a timeout needs returncode null and records no answer")
    else:
        problems.append(f"verdict {verdict!r} is not one this gate knows")
    return problems


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

    section("the agreement README.md quotes, recomputed from gate.jsonl")
    with open(os.path.join(HERE, "evidence", "gate.jsonl"), encoding="utf-8") as fh:
        runs = [json.loads(line) for line in fh]
    outcomes = {}
    for rec in runs:
        n, m = rec["n"], rec["m"]
        name = f"gate.jsonl n={n} m={m}"
        want = implied(n).get(m) if 1 <= n <= len(PUB1) else None
        problems = record_problems(rec)
        if want is None:
            problems.append("not one of the four instances the published pair implies")
        elif rec.get("expected_sat") is not want:
            problems.append(f"expected_sat should be {want}")
        if rec.get("verdict") == "TIMEOUT":
            outcome = "undecided"
        else:
            outcome = "agree" if (rec.get("verdict") != "UNSAT") is want else "disagree"
        if rec.get("agrees") is not (outcome == "agree"):
            problems.append(f"stored 'agrees' contradicts the recomputed {outcome}")
        check_that(f"{name}: {outcome}, and the record is consistent"
                   + (f" ({'; '.join(problems)})" if problems else ""), not problems)
        # Re-running an instance can decide it, but must never contradict.
        seen = outcomes.setdefault((n, m), set())
        seen.add(outcome)
    # One outcome per instance: any contradiction outweighs everything, and a
    # re-run that decided an instance outweighs the runs that timed out on it.
    final = {key: "disagree" if "disagree" in seen else
             "agree" if "agree" in seen else "undecided"
             for key, seen in outcomes.items()}
    tally = {"instances": len(final), "agree": 0, "disagree": 0, "undecided": 0}
    for outcome in final.values():
        tally[outcome] += 1
    check_that(f"{tally['instances']} distinct instances, {tally['agree']} agreements, "
               f"{tally['disagree']} disagreements, {tally['undecided']} undecided, "
               f"as claimed", tally == CLAIMED_AGREEMENT)
    ns = sorted({n for n, _ in outcomes})
    check_that(f"the SAT route covers n = {ns[0]}..{ns[-1]} "
               f"(claimed {CLAIMED_SAT_RANGE[0]}..{CLAIMED_SAT_RANGE[1]})",
               ns == list(range(CLAIMED_SAT_RANGE[0], CLAIMED_SAT_RANGE[1] + 1)))
    decided = [n for n in ns
               if all(final.get((n, m)) == "agree" for m in implied(n))]
    check_that(f"every n up to {LAST_FULLY_DECIDED} is fully decided and none past it",
               decided == list(range(CLAIMED_SAT_RANGE[0], LAST_FULLY_DECIDED + 1)))

    section("reach.jsonl records what reach.py measures")
    with open(os.path.join(HERE, "evidence", "reach.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            n, m = rec["n"], rec["m"]
            name = f"reach.jsonl n={n} m={m}"
            check_that(f"{name}: m is the largest size known satisfiable, M2 - 1",
                       1 <= n <= len(PUB2) and m == PUB2[n - 1] - 1)
            problems = record_problems(rec)
            check_that(f"{name}: size and verdict agree with each other"
                       + (f" ({'; '.join(problems)})" if problems else ""),
                       not problems)

    section("the record check can fail")
    # Each of these edits to a real record must be reported, or the checks
    # above are not constraining anything.
    sat_rec, unsat_rec, timeout_rec = (
        next((r for r in runs if r.get("verdict") == v), None)
        for v in ("SAT_WITNESS_VERIFIED", "UNSAT", "TIMEOUT"))
    check_that("gate.jsonl holds a SAT, an UNSAT and a TIMEOUT record to edit",
               None not in (sat_rec, unsat_rec, timeout_rec))
    for label, rec, key, value in [] if None in (sat_rec, unsat_rec, timeout_rec) else [
        ("SAT", sat_rec, "clauses", sat_rec["clauses"] + 1),
        ("SAT", sat_rec, "vars", sat_rec["vars"] + 1),
        ("SAT", sat_rec, "returncode", 20),
        ("SAT", sat_rec, "vars", float(sat_rec["vars"])),
        ("UNSAT", unsat_rec, "returncode", 20.0),
        ("UNSAT", unsat_rec, "verdict", "SAT_WITNESS_VERIFIED"),
        ("UNSAT", unsat_rec, "m", unsat_rec["m"] + 1),
        ("TIMEOUT", timeout_rec, "verdict", "UNSAT"),
    ]:
        check_that(f"a {label} record with {key}={value!r} is reported",
                   bool(record_problems(dict(rec, **{key: value}))))

    section("reach.py's own verdict classification, then broken on purpose")
    # The section above re-verifies every stored *colouring* with the
    # solver-free checker, including the one reach.py found -- but reach.py
    # also computes its own SAT_WITNESS_VERIFIED / SAT_WITNESS_BAD verdict from
    # that colouring, and nothing here ever called the function that does it.
    # Forcing it to always report SAT_WITNESS_VERIFIED survived unnoticed (see
    # audit/mutants/SAT_checkers.md, PalindromicVDW M7): reach.py is a
    # standalone offline explorer, imported by nothing in this gate. This
    # imports it directly and calls its real `classify()` on a committed
    # witness and on the same witness with one colour flipped.
    reach_path = os.path.join(HERE, "evidence", "reach.jsonl")
    reach_checked = 0
    with open(reach_path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            colouring = rec.get("colouring")
            if not colouring:
                continue
            reach_checked += 1
            name = f"reach.jsonl n={rec['n']} m={rec['m']}"
            verdict, _ = reach.classify(colouring, rec["n"])
            check_that(f"{name}: reach.classify ACCEPTS the stored witness",
                       verdict == "SAT_WITNESS_VERIFIED")
            flipped = ("2" if colouring[0] == "1" else "1") + colouring[1:]
            verdict, _ = reach.classify(flipped, rec["n"])
            check_that(f"{name}: reach.classify REJECTS a single flipped colour",
                       verdict == "SAT_WITNESS_BAD")
    check_that(f"at least one reach.py witness was checked ({reach_checked} found)",
               reach_checked > 0)

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
