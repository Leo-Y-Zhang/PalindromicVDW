import json

import pytest

from pdw import verify_all as gate

RECORDS = {
    "SAT": {
        "n": 3,
        "m": 5,
        "vars": 3,
        "clauses": 8,
        "returncode": 10,
        "sat": True,
        "colouring": "11211",
        "verdict": "SAT_WITNESS_VERIFIED",
    },
    "UNSAT": {
        "n": 3,
        "m": 7,
        "vars": 4,
        "clauses": 18,
        "returncode": 20,
        "sat": False,
        "verdict": "UNSAT",
    },
    "TIMEOUT": {
        "n": 3,
        "m": 7,
        "vars": 4,
        "clauses": 18,
        "returncode": None,
        "timed_out": True,
        "verdict": "TIMEOUT",
    },
}


@pytest.mark.parametrize("kind", RECORDS)
def test_consistent_record_is_accepted(kind):
    assert gate.record_problems(RECORDS[kind]) == []


@pytest.mark.parametrize(
    ("kind", "key", "value"),
    [
        ("SAT", "vars", 2),
        ("SAT", "vars", 3.0),
        ("SAT", "vars", True),
        ("SAT", "clauses", 7),
        ("SAT", "clauses", 9),
        ("SAT", "clauses", 8.0),
        ("SAT", "returncode", 20),
        ("SAT", "returncode", 10.0),
        ("SAT", "sat", False),
        ("SAT", "sat", 1),
        ("SAT", "colouring", ""),
        ("SAT", "colouring", None),
        ("UNSAT", "returncode", 10),
        ("UNSAT", "returncode", 20.0),
        ("UNSAT", "sat", True),
        ("UNSAT", "sat", 0),
        ("UNSAT", "colouring", "11211"),
        ("UNSAT", "colouring", ""),
        ("TIMEOUT", "returncode", 0),
        ("TIMEOUT", "returncode", 20),
        ("TIMEOUT", "timed_out", False),
        ("TIMEOUT", "timed_out", 1),
        ("TIMEOUT", "sat", False),
        ("TIMEOUT", "colouring", ""),
        ("SAT", "verdict", "SAT_WITNESS_BAD"),
        ("UNSAT", "verdict", "UNKNOWN"),
    ],
)
def test_one_corrupted_record_field_is_rejected(kind, key, value):
    assert gate.record_problems(dict(RECORDS[kind], **{key: value}))


@pytest.mark.parametrize(
    ("kind", "key"),
    [
        ("SAT", "vars"),
        ("SAT", "clauses"),
        ("SAT", "returncode"),
        ("SAT", "colouring"),
        ("UNSAT", "sat"),
        ("UNSAT", "returncode"),
    ],
)
def test_missing_required_record_field_is_rejected(kind, key):
    record = RECORDS[kind].copy()
    del record[key]
    assert gate.record_problems(record)


@pytest.mark.parametrize(
    ("value", "expected", "equal"),
    [
        (1, 1, True),
        (True, True, True),
        (None, None, True),
        (1, True, False),
        (1.0, 1, False),
        (False, 0, False),
        (2, 1, False),
    ],
)
def test_json_equality_checks_type_and_value(value, expected, equal):
    assert gate.same(value, expected) is equal


@pytest.mark.parametrize(
    ("m", "length", "count"), [(0, 1, 0), (4, 1, 4), (3, 3, 1), (5, 3, 4), (7, 3, 9), (2, 3, 0)]
)
def test_closed_form_includes_progression_ending_at_boundary(m, length, count):
    assert gate.ap_count(m, length) == count


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """Tiny real records; replace only the costly exhaustive pair re-derivation."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    runs = []
    for m, clauses, colouring in [
        (6, 12, "112211"),
        (7, 18, None),
        (8, 24, "12122121"),
        (9, 32, None),
    ]:
        record = {
            "n": 3,
            "m": m,
            "vars": (m + 1) // 2,
            "clauses": clauses,
            "returncode": 10 if colouring else 20,
            "sat": bool(colouring),
            "expected_sat": bool(colouring),
            "agrees": True,
            "verdict": "SAT_WITNESS_VERIFIED" if colouring else "UNSAT",
        }
        if colouring:
            record["colouring"] = colouring
        runs.append(record)
    runs.append(
        {
            "n": 3,
            "m": 9,
            "vars": 5,
            "clauses": 32,
            "returncode": None,
            "verdict": "TIMEOUT",
            "expected_sat": False,
            "agrees": False,
        }
    )
    (evidence_dir / "reach.jsonl").write_text(json.dumps(runs[2]) + "\n")
    monkeypatch.setattr(gate, "HERE", str(tmp_path))
    monkeypatch.setattr(gate, "passed", 0)
    monkeypatch.setattr(gate, "failed", 0)
    monkeypatch.setattr(
        gate, "CLAIMED_AGREEMENT", {"instances": 4, "agree": 4, "disagree": 0, "undecided": 0}
    )
    monkeypatch.setattr(gate, "CLAIMED_SAT_RANGE", (3, 3))
    monkeypatch.setattr(gate, "LAST_FULLY_DECIDED", 3)
    monkeypatch.setattr(
        gate,
        "pair",
        lambda n, cap: None if n == 5 and cap in (17, 19) else (gate.PUB1[n - 1], gate.PUB2[n - 1]),
    )
    monkeypatch.setattr(gate, "satisfiable", lambda n, m: (m == gate.PUB1[n - 1], None))
    return evidence_dir / "gate.jsonl", runs


def write_records(path, runs):
    path.write_text("".join(json.dumps(record) + "\n" for record in runs))


def test_evidence_gate_accepts_complete_consistent_files(evidence, capsys):
    path, runs = evidence
    write_records(path, runs)
    assert gate.main() == 0
    assert "0 failed" in capsys.readouterr().out


def test_evidence_gate_rejects_wrong_claimed_instance_count(evidence, monkeypatch, capsys):
    path, runs = evidence
    write_records(path, runs)
    monkeypatch.setattr(
        gate,
        "CLAIMED_AGREEMENT",
        {"instances": 5, "agree": 4, "disagree": 0, "undecided": 0},
    )
    assert gate.main() == 1
    assert "GATE FAILED" in capsys.readouterr().out


@pytest.mark.parametrize(
    "corruption", ["colour", "short-witness", "clause-count", "removed-record"]
)
def test_evidence_gate_rejects_corruptions(evidence, corruption, capsys):
    path, runs = evidence
    if corruption == "colour":
        runs[0]["colouring"] = "212211"
    elif corruption == "short-witness":
        # Still a valid palindromic colouring: only the stored m detects this.
        runs[0]["colouring"] = "1221"
    elif corruption == "clause-count":
        runs[0]["clauses"] -= 1
    else:
        del runs[2]
    write_records(path, runs)
    assert gate.main() == 1
    assert "GATE FAILED" in capsys.readouterr().out


def test_evidence_gate_rejects_truncated_json_file(evidence):
    path, runs = evidence
    write_records(path, runs)
    path.write_text(path.read_text()[:-3])
    with pytest.raises(json.JSONDecodeError):
        gate.main()
