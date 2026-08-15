"""Decide one instance with kissat, and check any witness without it.

Every run records the solver's return code. A solver that dies with empty
output must not be mistaken for a refusal, so the three outcomes are kept
apart: 10 SAT, 20 UNSAT, anything else is a missing measurement rather than an
answer.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdw import encode
from pdw.verify_witness import check

SAT, UNSAT = 10, 20


def find_kissat(explicit=None):
    path = explicit or os.environ.get("KISSAT") or shutil.which("kissat")
    if path and os.path.exists(path):
        return path
    return shutil.which(path) if path else None


def parse_model(stdout):
    lits = []
    for line in stdout.splitlines():
        if line.startswith("v "):
            lits.extend(int(t) for t in line[2:].split())
    return [x for x in lits if x != 0]


def solve(n, m, kissat, timeout=None):
    started = time.time()
    nv, clauses = encode.build(n, m)
    build_s = time.time() - started

    fd, path = tempfile.mkstemp(suffix=".cnf")
    with os.fdopen(fd, "w", encoding="ascii", newline="\n") as fh:
        fh.write(encode.to_dimacs(nv, clauses))

    rec = {"n": n, "m": m, "vars": nv, "clauses": len(clauses),
           "build_s": round(build_s, 2)}
    t0 = time.time()
    try:
        proc = subprocess.run([kissat, "-q", path], capture_output=True,
                              text=True, timeout=timeout)
        rec["solve_s"] = round(time.time() - t0, 2)
        rec["returncode"] = proc.returncode
        rec["timed_out"] = False
    except subprocess.TimeoutExpired:
        rec.update(solve_s=round(time.time() - t0, 2), returncode=None,
                   timed_out=True, verdict="TIMEOUT")
        os.unlink(path)
        return rec
    finally:
        if os.path.exists(path):
            os.unlink(path)

    if proc.returncode == UNSAT:
        rec["sat"] = False
        rec["verdict"] = "UNSAT"
    elif proc.returncode == SAT:
        colouring = encode.colouring_from_model(parse_model(proc.stdout), m)
        reason = check(colouring, n)
        rec["sat"] = True
        rec["colouring"] = colouring
        rec["verdict"] = "SAT_WITNESS_VERIFIED" if reason is None else "SAT_WITNESS_BAD"
        if reason:
            rec["witness_error"] = reason
    else:
        rec["verdict"] = "SOLVER_ERROR"
        rec["stderr"] = proc.stderr[:300]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("m", type=int)
    ap.add_argument("--kissat")
    ap.add_argument("--timeout", type=float)
    args = ap.parse_args()

    kissat = find_kissat(args.kissat)
    if not kissat:
        sys.exit("kissat not found: pass --kissat or set KISSAT")
    print(json.dumps(solve(args.n, args.m, kissat, args.timeout), indent=1))


if __name__ == "__main__":
    main()
