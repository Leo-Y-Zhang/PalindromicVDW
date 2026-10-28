import subprocess
from pathlib import Path

import pytest

from pdw import solve


def test_parse_multiline_signed_model_ignores_comments_status_and_zeros():
    stdout = "c 99 is a comment\ns SATISFIABLE\nv 1 -2 0\nv   3\nv -4 0\n"
    assert solve.parse_model(stdout) == [1, -2, 3, -4]
    assert solve.parse_model("c no model\ns UNSATISFIABLE\n") == []


@pytest.mark.parametrize("stdout", ["v 1 -", "v 1 nope 0"])
def test_truncated_or_malformed_model_literal_is_rejected(stdout):
    with pytest.raises(ValueError):
        solve.parse_model(stdout)


@pytest.fixture
def solver_result(monkeypatch):
    def run_case(code=10, stdout="v 1 -2 3 0\n", timeout=False):
        paths = []

        def fake_run(command, **kwargs):
            assert command[:2] == ["unused-kissat", "-q"]
            path = Path(command[2])
            paths.append(path)
            assert path.read_text() == (
                "p cnf 3 8\n-1 -2 -3 0\n-2 -3 0\n-1 -2 -3 0\n-1 -3 0\n"
                "1 2 3 0\n2 3 0\n1 2 3 0\n1 3 0\n"
            )
            assert kwargs == {"capture_output": True, "text": True, "timeout": 0.1}
            if timeout:
                raise subprocess.TimeoutExpired(command, 0.1)
            return subprocess.CompletedProcess(command, code, stdout, "failure detail")

        monkeypatch.setattr(solve.subprocess, "run", fake_run)
        result = solve.solve(3, 5, "unused-kissat", timeout=0.1)
        assert len(paths) == 1 and not paths[0].exists()
        assert (result["n"], result["m"], result["vars"], result["clauses"]) == (3, 5, 3, 8)
        return result

    return run_case


def test_sat_model_is_independently_verified(solver_result):
    # 11211: part 1 has no 3-AP, part 2 has only the centre.
    result = solver_result(stdout="v 1 2 -3 0\n")
    assert result["verdict"] == "SAT_WITNESS_VERIFIED"
    assert result["sat"] is True
    assert result["colouring"] == "11211"
    assert result["returncode"] == 10
    assert result["timed_out"] is False
    assert "witness_error" not in result


@pytest.mark.parametrize("stdout", ["v 1 2 3 0\n", "v -1 -2 -3 0\n", "v 1\n", ""])
def test_sat_corrupt_or_truncated_models_are_bad_witnesses(solver_result, stdout):
    result = solver_result(stdout=stdout)
    assert result["sat"] is True
    assert result["verdict"] == "SAT_WITNESS_BAD"
    assert "arithmetic progression" in result["witness_error"]


def test_unsat_uses_return_code_even_with_misleading_output(solver_result):
    result = solver_result(code=20, stdout="s SATISFIABLE\nv 1 2 -3 0\n")
    assert result["sat"] is False
    assert result["verdict"] == "UNSAT"
    assert result["returncode"] == 20
    assert "colouring" not in result


@pytest.mark.parametrize("code", [0, 1, -9])
def test_solver_failure_is_not_unsat(solver_result, code):
    result = solver_result(code=code, stdout="s UNSATISFIABLE\n")
    assert result["verdict"] == "SOLVER_ERROR"
    assert result["returncode"] == code
    assert result["stderr"] == "failure detail"
    assert "sat" not in result and "colouring" not in result


def test_timeout_is_undecided_and_cleans_up(solver_result):
    result = solver_result(timeout=True)
    assert result["verdict"] == "TIMEOUT"
    assert result["returncode"] is None
    assert result["timed_out"] is True
    assert "sat" not in result and "colouring" not in result
