"""How far does the satisfiable side reach once the solver is told to expect SAT?

The gate showed the two halves of the question failing at different rates: at
n = 22 a satisfiable instance took 500 s while `kissat --sat` did the same one
in 186 s, and no configuration decided the unsatisfiable side at all. That is
worth measuring properly, because "this is hard" and "this half is hard" are
different findings.

For each n this solves the largest instance known to be satisfiable, m = M2 - 1,
and verifies the witness without a solver.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdw import encode
from pdw.gate import PUB2
from pdw.solve import find_kissat, parse_model
from pdw.verify_witness import check


def classify(colouring, n):
    """The solver-free half of this file's verdict: re-check a claimed
    satisfying colouring and translate the result into the same two labels
    `main()` writes to `pdw/evidence/reach.jsonl`.

    Factored out of `main()`'s loop so it can be exercised without a live
    kissat: `main()` only ever calls this with a colouring `--sat` itself just
    produced, so nothing here previously ran unless this module's own binary
    search reached a fresh instance. See `pdw/verify_all.py`'s "reach.py"
    section, which imports this function directly and feeds it both a stored
    witness and a one-character-flipped copy of it.
    """
    reason = check(colouring, n)
    return ('SAT_WITNESS_VERIFIED' if reason is None else 'SAT_WITNESS_BAD'), reason


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="lo", type=int, default=23)
    ap.add_argument("--to", dest="hi", type=int, default=27)
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--config", default="--sat")
    ap.add_argument("--kissat")
    ap.add_argument("--out", default="pdw/evidence/reach.jsonl")
    args = ap.parse_args()

    kissat = find_kissat(args.kissat)
    if not kissat:
        sys.exit("kissat not found")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    with open(args.out, "a", encoding="utf-8") as log:
        for n in range(args.lo, args.hi + 1):
            m = PUB2[n - 1] - 1          # the largest size known to be satisfiable
            nv, clauses = encode.build(n, m)
            fd, path = tempfile.mkstemp(suffix=".cnf")
            with os.fdopen(fd, "w", encoding="ascii", newline="\n") as fh:
                fh.write(encode.to_dimacs(nv, clauses))
            rec = {"n": n, "m": m, "vars": nv, "clauses": len(clauses),
                   "config": args.config}
            t0 = time.time()
            try:
                p = subprocess.run([kissat, "-q", args.config, path],
                                   capture_output=True, text=True,
                                   timeout=args.timeout)
                rec["solve_s"] = round(time.time() - t0, 1)
                rec["returncode"] = p.returncode
                if p.returncode == 10:
                    colouring = encode.colouring_from_model(parse_model(p.stdout), m)
                    rec["verdict"], reason = classify(colouring, n)
                    rec["colouring"] = colouring
                    if reason:
                        rec["witness_error"] = reason
                else:
                    rec["verdict"] = "UNEXPECTED"
            except subprocess.TimeoutExpired:
                rec.update(solve_s=round(time.time() - t0, 1), returncode=None,
                           verdict="TIMEOUT")
            finally:
                if os.path.exists(path):
                    os.unlink(path)
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(f"n={n} m={m} vars={rec['vars']} clauses={rec['clauses']} "
                  f"{rec['verdict']} in {rec['solve_s']}s", flush=True)
            if rec["verdict"] == "TIMEOUT":
                print("stopping: the satisfiable side has run out too", flush=True)
                break


if __name__ == "__main__":
    main()
