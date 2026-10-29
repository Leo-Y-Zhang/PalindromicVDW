"""Explicit, one-at-a-time mutants; never edits the working tree's pdw files.

Run before/after adding tests with:
    python tests/mutation_check.py before
    python tests/mutation_check.py after

Each subprocess starts fresh in an isolated copy, without bytecode or plugins.
The baseline is the repository's solver-free CI gate; the after phase runs
pytest as well. Timeouts are reported separately, never counted as kills.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (module, unique original fragment, replacement). IDs are stable list indices.
MUTANTS = [
    ("verify_witness", "return colouring == colouring[::-1]", "return True"),
    ("verify_witness", "if length <= 0:", "if length <= 1:"),
    ("verify_witness", "return len(positions) > 0", "return len(positions) >= 0"),
    ("verify_witness", "return len(positions) >= 2", "return len(positions) > 2"),
    ("verify_witness", "if k == length:", "if k != length:"),
    ("verify_witness", "nxt += d", "nxt += d + 1"),
    ("verify_witness", 'if set(colouring) - {"1", "2"}:', "if False:"),
    ("verify_witness", "if has_progression(part1, 3):", "if False:"),
    ("verify_witness", "if has_progression(part2, n):", "if False:"),
    ("verify_witness", 'if ch == "2"}', 'if ch == "1"}'),
    ("encode", "return min(i, m + 1 - i)", "return min(i, m - i)"),
    ("encode", "if length <= 0:", "if length <= 1:"),
    ("encode", "for a in range(1, m + 1):", "for a in range(1, m):"),
    ("encode", "while a_max(m, length, d) >= 1:", "while a_max(m, length, d) > 1:"),
    ("encode", "nv = (m + 1) // 2", "nv = m // 2"),
    ("encode", "{-var_of(i, m) for i in ap}", "{var_of(i, m) for i in ap}"),
    ("encode", "{var_of(i, m) for i in ap})", "{-var_of(i, m) for i in ap})"),
    ("encode", "return nv, clauses", "return nv, clauses[:-1]"),
    ("encode", 'f"p cnf {nv} {len(clauses)}"', 'f"p cnf {nv} {len(clauses) + 1}"'),
    ("encode", '+ " 0" for c in clauses', '+ "" for c in clauses'),
    ("encode", 'return "\\n".join(out) + "\\n"', 'return "\\n".join(out[:-1]) + "\\n"'),
    ("encode", "if x > 0}", "if x < 0}"),
    ("encode", "for i in range(1, m + 1))", "for i in range(1, m))"),
    ("solve", 'if line.startswith("v "):', 'if not line.startswith("v "):'),
    ("solve", "for x in lits if x != 0", "for x in lits if x == 0"),
    ("solve", "int(t) for t in line[2:].split()", "abs(int(t)) for t in line[2:].split()"),
    ("solve", "if proc.returncode == UNSAT:", "if proc.returncode != SAT:"),
    ("solve", "elif proc.returncode == SAT:", "elif proc.returncode != SAT:"),
    ("solve", "reason = check(colouring, n)", "reason = None"),
    (
        "solve",
        '"SAT_WITNESS_VERIFIED" if reason is None',
        '"SAT_WITNESS_VERIFIED" if reason is not None',
    ),
    (
        "solve",
        'if reason:\n            rec["witness_error"] = reason',
        'if False:\n            rec["witness_error"] = reason',
    ),
    ("solve", 'timed_out=True, verdict="TIMEOUT"', 'timed_out=True, verdict="UNSAT"'),
    ("solve", 'rec["sat"] = False', 'rec["sat"] = True'),
    ("solve", 'rec["sat"] = True', 'rec["sat"] = False'),
    ("brute", "half = (m + 1) // 2", "half = m // 2"),
    ("brute", "left[::-1][m % 2:]", "left[::-1][1 - m % 2:]"),
    ("brute", "if check(colouring, n) is None:", "if check(colouring, n) is not None:"),
    ("brute", "m_cap - last_ok < 2", "m_cap - last_ok < 1"),
    ("brute", "return first_fail - 1, last_ok + 1", "return first_fail, last_ok + 1"),
    ("reach", "reason = check(colouring, n)", "reason = None"),
    ("reach", "if reason is None else", "if reason is not None else"),
    ("verify_all", "while m - (length - 1) * d >= 1:", "while m - (length - 1) * d > 1:"),
    ("verify_all", "type(value) is type(expected) and value == expected", "value == expected"),
    ("verify_all", 'if not same(rec.get("vars"), (m + 1) // 2):', "if False:"),
    ("verify_all", 'if not same(rec.get("clauses"), clauses):', "if False:"),
    (
        "verify_all",
        'not same(code, 10) or rec.get("sat", True) is not True',
        'not same(code, 10) and rec.get("sat", True) is not True',
    ),
    ("verify_all", 'or rec.get("sat", True) is not True', "or False"),
    ("verify_all", 'or not rec.get("colouring")', "or False"),
    (
        "verify_all",
        'not same(code, 20) or rec.get("sat") is not False',
        'not same(code, 20) and rec.get("sat") is not False',
    ),
    ("verify_all", 'or rec.get("sat") is not False', "or False"),
    (
        "verify_all",
        'not same(code, 20) or rec.get("sat") is not False or "colouring" in rec:',
        'not same(code, 20) or rec.get("sat") is not False or False:',
    ),
    (
        "verify_all",
        'if code is not None or rec.get("timed_out", True) is not True',
        'if False or rec.get("timed_out", True) is not True',
    ),
    ("verify_all", 'or rec.get("timed_out", True) is not True', "or False"),
    ("verify_all", 'or "sat" in rec or "colouring" in rec:', 'or False or "colouring" in rec:'),
    ("verify_all", 'or "sat" in rec or "colouring" in rec:', 'or "sat" in rec or False:'),
    ("verify_all", 'problems.append(f"verdict {verdict!r} is not one this gate knows")', "pass"),
    ("verify_all", "return problems", "return []"),
    ("verify_all", 'len(colouring) == rec["m"]', "True"),
    ("verify_all", "tally == CLAIMED_AGREEMENT", "True"),
]


def run(command, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    try:
        result = subprocess.run(
            command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    if result.returncode == 0:
        return "survived"
    if command[2:4] == ["pytest", "-q"] and result.returncode != 1:
        raise RuntimeError(f"pytest infrastructure failure:\n{result.stdout}\n{result.stderr}")
    return "killed"


def measure(work, module, original, replacement, commands):
    source_path = work / "pdw" / f"{module}.py"
    source = source_path.read_bytes()
    text = source.decode().replace("\r\n", "\n")
    if text.count(original) != 1:
        raise ValueError(f"{module}: fragment must occur exactly once")
    mutated = text.replace(original, replacement)
    compile(mutated, str(source_path), "exec")
    try:
        source_path.write_text(mutated)
        statuses = [run(commands[0], work)]
        if len(commands) > 1 and statuses[0] == "survived":
            statuses.append(run(commands[1], work))
        return statuses
    finally:
        source_path.write_bytes(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after"))
    parser.add_argument("--resume", action="store_true", help="Reuse completed after measurements")
    args = parser.parse_args()
    if args.resume and args.phase != "after":
        parser.error("--resume is only supported for after measurements")
    result_path = ROOT / "tests" / "mutation_results.json"
    results = json.loads(result_path.read_text()) if result_path.exists() else []
    if args.phase == "before":
        results = []
    elif len(results) != len(MUTANTS) or any(
        result.get("before") not in ("killed", "survived")
        or (result["module"], result["original"], result["replacement"]) != mutant
        for result, mutant in zip(results, MUTANTS, strict=True)
    ):
        raise RuntimeError("Run a complete before phase with this mutation catalog first")
    commands = [[sys.executable, "pdw/verify_all.py"]]
    if args.phase == "after":
        commands = [[sys.executable, "-m", "pytest", "-q"], *commands]
    for command in commands:
        if run(command, ROOT) != "survived":
            raise RuntimeError(f"Unmutated baseline failed: {command}")
    with tempfile.TemporaryDirectory(prefix=".pdw-mutant-", dir=ROOT) as directory:
        work = Path(directory)
        shutil.copytree(ROOT / "pdw", work / "pdw", ignore=shutil.ignore_patterns("__pycache__"))
        if args.phase == "after":
            shutil.copytree(
                ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__")
            )
        for index, (module, original, replacement) in enumerate(MUTANTS, 1):
            if args.resume and "after" in results[index - 1]:
                continue
            statuses = measure(work, module, original, replacement, commands)
            status = (
                "killed"
                if "killed" in statuses
                else "timeout"
                if "timeout" in statuses
                else "survived"
            )
            if len(results) < index:
                results.append(
                    {
                        "id": f"M{index:02}",
                        "module": module,
                        "original": original,
                        "replacement": replacement,
                    }
                )
            results[index - 1][args.phase] = status
            if args.phase == "after":
                results[index - 1]["pytest"] = statuses[0]
            result_path.write_text(json.dumps(results, indent=2) + "\n")
            print(f"M{index:02} {module}: {args.phase} {status}", flush=True)
    print(
        f"{args.phase}: "
        + ", ".join(
            f"{sum(r[args.phase] == status for r in results)} {status}"
            for status in ("killed", "survived", "timeout")
        )
    )


if __name__ == "__main__":
    main()
