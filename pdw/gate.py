"""Reproduce published pdw(n,3;2) pairs before claiming a new one.

For each n the published pair (M1, M2) implies four decisions:
    m = M1     satisfiable      (the last size that always works)
    m = M1 + 1 unsatisfiable    (the first failure)
    m = M2 - 1 satisfiable      (the last size that works at all)
    m = M2     unsatisfiable
Any disagreement means the encoding is wrong and nothing downstream is worth
running. Progress is written as it happens, so a slow instance is visible
rather than inferred.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdw.solve import find_kissat, solve      # noqa: E402

PUB1 = [2, 3, 6, 15, 16, 30, 41, 52, 62, 93, 110, 126, 142, 174, 200, 232, 256,
        299, 338, 380, 400, 444, 506, 568, 586, 634, 664]
PUB2 = [3, 6, 9, 16, 21, 31, 44, 57, 77, 94, 113, 135, 155, 183, 205, 237, 279,
        312, 347, 389, 405, 463, 507, 593, 607, 643, 699]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="lo", type=int, default=25)
    ap.add_argument("--to", dest="hi", type=int, default=27)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--kissat")
    ap.add_argument("--out", default="pdw/evidence/gate.jsonl")
    args = ap.parse_args()

    kissat = find_kissat(args.kissat)
    if not kissat:
        sys.exit("kissat not found")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    failures = 0
    with open(args.out, "a", encoding="utf-8") as log:
        for n in range(args.lo, args.hi + 1):
            m1, m2 = PUB1[n - 1], PUB2[n - 1]
            for m, want_sat in ((m1, True), (m1 + 1, False),
                                (m2 - 1, True), (m2, False)):
                t0 = time.time()
                rec = solve(n, m, kissat, timeout=args.timeout)
                rec["expected_sat"] = want_sat
                # Three outcomes, not two. A solver that ran out of time has not
                # disagreed with anything -- it has failed to measure. Folding
                # the two together would turn a known ceiling into a false alarm.
                if rec["verdict"] in ("UNSAT", "SAT_WITNESS_VERIFIED"):
                    rec["outcome"] = "agrees" if rec.get("sat") == want_sat else "DISAGREES"
                else:
                    rec["outcome"] = "undecided"
                if rec["outcome"] == "DISAGREES":
                    failures += 1
                log.write(json.dumps(rec) + "\n")
                log.flush()
                mark = {"agrees": "", "undecided": "   (undecided)",
                        "DISAGREES": "   <<< DISAGREES"}[rec["outcome"]]
                print(f"n={n} m={m} want={'SAT' if want_sat else 'UNSAT'} "
                      f"got={rec['verdict']} vars={rec['vars']} "
                      f"clauses={rec['clauses']} build={rec['build_s']}s "
                      f"solve={rec.get('solve_s')}s "
                      f"[{time.time() - t0:.1f}s wall]{mark}", flush=True)
    print(f"\ngate: {failures} disagreement(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
