# Pre-flight for pdw(28,3;2) — and why it stopped here

This repository was started to compute the next term of OEIS
[A198684](https://oeis.org/A198684) and [A198685](https://oeis.org/A198685),
the palindromic mixed van der Waerden numbers pdw(n,3;2). Both were entered by
Oliver Kullmann in October 2011 and both hold 27 terms. Neither carries an
extensions line, and the nineteen revisions since are editorial, so no term has
been added by anyone in fourteen years.

The measurement below is the reason not to carry on. It is recorded because a
measurement that stops a project is worth as much as one that starts it.

## The question

A palindromic 2-partition of `{1,...,m}` is a colouring `c` with
`c(i) = c(m+1-i)`. One part must contain no 3-term arithmetic progression, the
other no n-term one. Such partitions do not simply stop existing at some size —
existence is irregular — so the answer is a pair:

    M1 = the largest M such that one exists for EVERY m <= M      (A198684)
    M2 = the smallest M such that none exists for ANY m >= M      (A198685)

At n = 27 those are 664 and 699. The target was n = 28.

The palindrome is not a constraint added to the formula; it is built into the
variable map, so an instance on `{1,...,m}` has `ceil(m/2)` variables rather
than `m`. That halving is why these are known to n = 27 while the unrestricted
numbers w(2;3,t) stop at t = 9.

## 1. The encoding is right, and that is established before anything else

Two independent routes, neither trusting the other:

**Exhaustion** over all `2^ceil(m/2)` palindromic colourings, checked against
the definition by `verify_witness.py`, reproduces the published pairs exactly:

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| pdw | (2,3) | (3,6) | (6,9) | (15,16) | (16,21) | (30,31) | (41,44) |

n = 7 took nine minutes; that is where exhaustion ends.

**SAT** decides the same instances through n = 23. Each published pair implies
four decisions — `m = M1` satisfiable, `m = M1+1` not, `m = M2-1` satisfiable,
`m = M2` not — and every satisfying assignment is re-checked by the same
solver-free checker, which shares no code with the encoder.

    34 distinct instances, 33 agreements, 0 disagreements, 1 undecided.

The single undecided instance is the one that ends the project.

## 2. The unsatisfiable side runs out at n = 23

Times are kissat 4.0.1 on one desktop core, default configuration.

| n | vars | clauses | satisfiable (s) | unsatisfiable (s) |
|---:|---:|---:|---:|---:|
| 15 | 103 | 11,804 | 0.2, 0.3 | 0.3, 0.3 |
| 17 | 140 | 21,616 | 1.4, 1.7 | 1.3, 1.5 |
| 18 | 156 | 26,889 | 4.0, 1.2 | 9.3, 9.5 |
| 19 | 174 | 33,102 | 1.5, 26.6 | 9.6, 10.7 |
| 20 | 195 | 41,426 | 70.2, 61.5 | 34.6, 35.5 |
| 21 | 203 | 44,704 | 16.9, 202.9 | 83.5, 82.5 |
| 22 | 232 | 58,234 | 28.1, 560.3 | 506.1, 495.5 |
| **23** | **254** | **69,598** | **163.4** | **no verdict in 600 s** |

Sustained growth is about **2.9x per step in n**, over seven steps. Extrapolated
from n = 22:

| n | 24 | 25 | 27 | **28** |
|---|---|---|---|---|
| per instance | ~70 min | ~3.4 h | ~28 h | **~3 days** |

The target needs several instances, not one. It is out of reach by roughly three
orders of magnitude.

## 3. Telling the solver what to expect helps one half only

Each instance written once, handed to three configurations:

| instance | expected | `--default` | `--sat` | `--unsat` |
|---|---|---|---|---|
| n=21, m=404 | SAT | 225.8 s | **112.6 s** | 225.9 s |
| n=21, m=405 | UNSAT | 91.3 s | 97.2 s | 97.9 s |
| n=22, m=462 | SAT | no verdict in 400 s | **185.8 s** | no verdict in 400 s |
| n=22, m=463 | UNSAT | no verdict in 400 s | no verdict in 400 s | no verdict in 400 s |

`--sat` is worth roughly a factor of two on satisfiable instances, and at
n = 22 it is the difference between an answer and none. It is not reliable,
though: re-run at n = 23, m = 506 it took 165.2 s against the default's
163.4 s, no gain at all. **And nothing helps the unsatisfiable side.** That is
the binding constraint, and an unreliable factor of two against a factor of a
thousand is not a strategy.

## Verdict: NO-GO, and what would change it

Not "this is hard". Specifically: **the unsatisfiable half of pdw(n,3;2) is not
reachable by a single kissat call past n = 23 on one desktop machine.** In rough
order of what would have to exist first:

1. **Cube-and-conquer** over the palindromic half-interval, splitting the search
   and running the parts across all cores. This is the technique that settled
   the headline refutation in my mixed van der Waerden work, and it is the only
   thing here with a plausible order of magnitude in it. It is a different
   program, not a flag.
2. Failing that, an encoding that does not hand the solver `~70,000` clauses of
   3-term progressions — a cardinality or interval formulation that captures
   "no 3-term progression in this part" more compactly.
3. Only then is n = 28 worth attempting, and it would still be one term.

Until (1) exists, this is a no-go. The repository is kept because the encoding,
the checker and the agreement above are correct and reusable, and because the
measurement is the evidence for the decision.

## What is here

Nothing in this repository is a new mathematical claim. Every pdw value it
mentions is published and is recorded as published; the only things computed
here are reproductions of those values and the timings above.
