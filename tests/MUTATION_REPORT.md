# Mutation-guided tests

Production Python files are unchanged. The only CI change installs
`pytest==8.4.2` and adds `pytest -q` to the existing solver-free gate job.
There are no new runtime dependencies or importability seams.

## Method

`mutation_check.py` contains 59 explicit, single-site mutations covering the
witness checker, progression enumeration, CNF encoding/serialization, model
parsing, solver verdicts, exhaustive search, reach classification, and evidence
validation. Each mutation is compiled and run in an isolated temporary project
copy under the workspace, restoring the source before applying the next mutation;
the original `pdw/` files are never edited. Each subprocess starts
fresh, disables bytecode and third-party pytest plugins, and has a 60-second
timeout. Timeouts are reported separately from kills. The unmutated gate (and,
in the after phase, pytest) must pass before measuring mutants.

The **before** measurement runs the original CI correctness command,
`python pdw/verify_all.py`; there were no existing pytest tests. The **after**
measurement runs the new pytest suite first, then the gate if pytest lets a
mutant survive. This is a targeted mutation sample, not an exhaustive mutation
score for every line or the solver-backed command-line explorers.

Reproduce with Python and pytest 8.4.2 installed:

```sh
python tests/mutation_check.py before
python tests/mutation_check.py after
```

Exact mutation fragments and per-mutant results are in `mutation_results.json`.

## Results

| Module | Mutants tried | Killed before | Killed after |
| --- | ---: | ---: | ---: |
| `pdw/verify_witness.py` | 10 | 9 | 10 |
| `pdw/encode.py` | 13 | 1 | 13 |
| `pdw/solve.py` | 11 | 0 | 11 |
| `pdw/brute.py` | 5 | 5 | 5 |
| `pdw/reach.py` | 2 | 2 | 2 |
| `pdw/verify_all.py` | 18 | 7 | 18 |
| **Total** | **59** | **24** | **59** |

All 35 baseline survivors are killed. Every mutant is killed directly by pytest;
the after measurement has no survivors or timeouts.

## Tests and representative mutants

| New test file | A mutant it kills (original production location) |
| --- | --- |
| `test_witness.py` | **M07**, `verify_witness.check`, line 45: replace the invalid-character condition with `False`. `11011` stays palindromic and has no forbidden progression in either recognized colour, so only character validation rejects it. Also kills **M40**, `reach.classify`, line 40: replace the checker result with `None`. |
| `test_encode.py` | **M19**, `encode.to_dimacs`, line 65: increase the header's clause count by one. Also kills **M18**, `encode.build`, line 61: drop the last clause. Small truth tables compare CNF decisions with an independent combinations-based definition, without SAT solving. |
| `test_solve.py` | **M29**, `solve.solve`, line 72: replace independent witness verification with `reason = None`. Palindromic but invalid solver models must produce `SAT_WITNESS_BAD`. All subprocess results are mocked, including errors and timeouts. |
| `test_brute.py` | **M38**, `brute.pair`, line 46: change the required gap after the last success from `< 2` to `< 1`, incorrectly certifying an isolated failure. Checks exact small witnesses, both size parities, and insufficient search caps. |
| `test_records.py` | **M47**, `verify_all.record_problems`, line 89: remove the SAT truth-value requirement. Valid records with just `sat=False` must fail. Also kills **M58**, `verify_all.main`, line 161: bypass the witness-length check, and **M59**, line 204: bypass the claimed agreement tally. |

`conftest.py` supplies the checkout import path. `mutation_check.py` is a manual
measurement tool; it is deliberately not collected as a unit test or run by CI.
The unit tests cover valid witnesses/records and isolated corruptions: a changed
colour or character, removed clause/count, missing fields, wrong JSON types,
short valid colourings paired with a larger recorded size, truncated JSON, and
malformed/truncated solver output. The model parser has no expected size
argument; complete literal tokens in a short model are checked at the witness
verification layer rather than asserted to be parser errors.

## Validation

Commands run in the local environment:

- `python tests/mutation_check.py before`: 24 killed, 35 survived, 0 timeouts.
- `.test-env/bin/python tests/mutation_check.py after --resume`: `59 killed, 0 survived, 0 timeout` (exit 0).
  The completed measurements from the initial `after` run were retained; resuming
  runs the unmutated checks again before measuring the remaining mutations.
- `.test-env/bin/pytest -q --durations=5`: 231 passed; slowest test call 0.02 s.
- `.test-env/bin/pytest -q`: exit 0, full output:

```text
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
...............                                                          [100%]
231 passed in 1.14s
```

- `python pdw/verify_all.py`: exit 0, final output:

```text
141 passed / 0 failed
EVERY CLAIM IN THIS REPOSITORY IS SUPPORTED BY EVIDENCE ON DISK.
```

- `.test-env/bin/ruff check .github pdw tests`: `All checks passed!`
- `.test-env/bin/ruff format --check tests`: passed.
- `./.ruff-check check .`: `All checks passed!` (the same Ruff 0.16.1 binary,
  retained temporarily to lint the entire checkout after removing the environment).

Local validation uses Python 3.11.2; the existing CI job continues to use Python
3.13. No SAT solver or network is used by the tests or mutation measurements.
Network access was used only to install the pytest and CI Ruff packages into a
temporary local environment.

The Gitleaks CI job was not run locally because its binary is unavailable.
An interrupted measurement initially left a temporary copy that caused pytest
collection errors on resume; these were treated as infrastructure failures,
contributed no kills, and were cleaned before the successful rerun.
