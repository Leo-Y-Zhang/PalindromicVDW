# PalindromicVDW

Palindromic mixed van der Waerden numbers as SAT, and a measured account of how
far that gets on one desktop machine.

A palindromic 2-partition of `{1,...,m}` is a colouring `c` with
`c(i) = c(m+1-i)`. For pdw(n,3;2), one part must contain no 3-term arithmetic
progression and the other no n-term one. Because existence is irregular in `m`,
the answer is a pair rather than a single number:

    M1 = the largest M such that a partition exists for EVERY m <= M
    M2 = the smallest M such that none exists for ANY m >= M

These are OEIS [A198684](https://oeis.org/A198684) and
[A198685](https://oeis.org/A198685), entered by Oliver Kullmann in 2011 and
holding 27 terms each.

## What is established here

**Nothing new.** Every value this repository mentions is published, and is
recorded as published rather than claimed. What it contains is a correct
encoding, an independent checker, and a measurement.

The palindrome lives in the variable map rather than in added clauses, so an
instance on `{1,...,m}` carries `ceil(m/2)` variables. That halving is the
reason these numbers are known to n = 27 while the unrestricted numbers
w(2;3,t) stop at t = 9.

Published pairs are re-derived two independent ways. Exhaustion over all
palindromic colourings reproduces n = 1 through 7 exactly. The SAT route
reproduces every decision implied by the published pairs through n = 23:

    34 distinct instances, 33 agreements, 0 disagreements, 1 undecided.

Every satisfying assignment is re-checked by `verify_witness.py`, which reads
the definition and finds progressions by its own walk, sharing no code with the
encoder — so a bug in the encoding cannot hide inside the check meant to catch
it.

**The last fully decided value is n = 22.** At n = 23 the refutation gets no
verdict in 600 s while the witness still lands in 163 s; at n = 24 neither half
lands, even told to expect satisfiability and given 900 s. Solve time grows
about 2.9x per step in n, which puts the next unpublished term, n = 28, at
roughly three days per instance. `PREFLIGHT.md` has the full table, the
configuration comparison, and what would have to exist before this were worth
restarting.

The clause count was never the constraint. The search is.

## Layout

- `pdw/encode.py` — the CNF, which is the definition and the palindrome and
  nothing else.
- `pdw/verify_witness.py` — solver-free check of a claimed partition, by an
  algorithm sharing nothing with the encoder.
- `pdw/brute.py` — exhaustive ground truth for small n, a second opinion on the
  encoding that involves no solver at all.
- `pdw/solve.py` — build, solve, verify any witness, record the evidence
  including the solver's return code.
- `pdw/gate.py` — reproduce published pairs before trusting anything past them.
- `pdw/verify_all.py` — the solver-free gate, and what CI runs on every push.
- `pdw/calibrate.py` — whether `kissat --sat` / `--unsat` pay for themselves.
- `pdw/reach.py` — how far the satisfiable side alone gets.
- `pdw/evidence/` — one JSON record per decision, including the timeouts.

## Verifying

Clone, then run the gate from the repository root. It is the one command that
checks everything checkable without a solver, and it is what CI runs:

```
python pdw/verify_all.py
```

It re-derives the small pairs by exhaustion, re-verifies every stored witness,
and breaks each one on purpose to confirm the check can still fail. Expect
`EVERY CLAIM IN THIS REPOSITORY IS SUPPORTED BY EVIDENCE ON DISK.` and exit 0,
in well under a minute.

Python 3.13, which is what CI runs and what `ruff.toml` targets. Nothing is
installed and there are no third-party packages — `kissat` is the only external
dependency, and only the solver-backed commands need it:

```
python pdw/gate.py --from 15 --to 22          # needs kissat
python -c "from pdw.brute import pair; print(pair(6, 40))"    # needs nothing
```

`kissat` is [Armin Biere's solver](https://github.com/arminbiere/kissat); the
timings in `PREFLIGHT.md` are 4.0.1. It is located through `--kissat`, the
`KISSAT` environment variable, or `PATH`.

## Honest limits

- No value here is a new result. The reproductions match published values; the
  next term was not reached.
- A timeout is recorded as undecided, never as a disagreement. A solver that
  ran out of time has not contradicted anything.
- The measurement is of one encoding on one machine with one solver. It says a
  single symmetry-naive SAT call does not reach n = 28, not that n = 28 is
  unreachable.
