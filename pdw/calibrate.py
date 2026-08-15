"""Does telling kissat what kind of answer to expect pay for itself?

The gate's growth curve decides whether n = 28 is reachable at all, so it is
worth knowing whether the default configuration is the one to extrapolate from.
Each instance is written once and handed to every configuration, so the only
thing varying is the solver's own heuristics.
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdw import encode                    # noqa: E402
from pdw.solve import find_kissat         # noqa: E402

CONFIGS = ["--default", "--sat", "--unsat"]


def run(kissat, cnf, config, timeout):
    t0 = time.time()
    try:
        p = subprocess.run([kissat, "-q", config, cnf], capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, round(time.time() - t0, 1)
    except subprocess.TimeoutExpired:
        return None, round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=400)
    ap.add_argument("--kissat")
    args = ap.parse_args()
    kissat = find_kissat(args.kissat)

    # A spread of known-answer instances, satisfiable and not.
    cases = [(21, 404, "SAT"), (21, 405, "UNSAT"),
             (22, 462, "SAT"), (22, 463, "UNSAT")]

    print(f"{'instance':>14}  {'expect':>6} " +
          "".join(f"{c:>12}" for c in CONFIGS), flush=True)
    for n, m, expect in cases:
        nv, clauses = encode.build(n, m)
        fd, path = tempfile.mkstemp(suffix=".cnf")
        with os.fdopen(fd, "w", encoding="ascii", newline="\n") as fh:
            fh.write(encode.to_dimacs(nv, clauses))
        row = []
        for cfg in CONFIGS:
            rc, secs = run(kissat, path, cfg, args.timeout)
            verdict = {10: "SAT", 20: "UNSAT"}.get(rc, "timeout")
            row.append(f"{verdict}/{secs}s")
        os.unlink(path)
        print(f"n={n} m={m:>4}  {expect:>6} " +
              "".join(f"{c:>12}" for c in row), flush=True)


if __name__ == "__main__":
    main()
