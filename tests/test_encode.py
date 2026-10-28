from itertools import combinations, pairwise, product

import pytest

from pdw.encode import aps, build, colouring_from_model, to_dimacs, var_of


def progressions(m, length):
    """Small independent oracle: select subsets and compare adjacent gaps."""
    if length <= 0:
        return []
    return [
        points
        for points in combinations(range(1, m + 1), length)
        if len({b - a for a, b in pairwise(points)}) <= 1
    ]


@pytest.mark.parametrize("m", range(9))
@pytest.mark.parametrize("length", [-1, 0, 1, 2, 3, 4, 9])
def test_progressions_match_subsets(m, length):
    actual = list(aps(m, length))
    assert len(actual) == len(set(actual))
    assert set(actual) == set(progressions(m, length))


@pytest.mark.parametrize(("m", "mapping"), [(1, [1]), (4, [1, 2, 2, 1]), (5, [1, 2, 3, 2, 1])])
def test_palindrome_variable_map(m, mapping):
    assert [var_of(i, m) for i in range(1, m + 1)] == mapping


def test_clause_polarity_deduplication_and_multiplicity():
    assert build(3, 3) == (2, [[-1, -2], [1, 2]])
    assert build(2, 3) == (2, [[-1, -2], [1, 2], [1, 2], [1]])
    assert build(1, 2) == (1, [[1], [1]])


@pytest.mark.parametrize("m", range(9))
@pytest.mark.parametrize("n", range(1, 6))
def test_cnf_truth_table_matches_definition(n, m):
    nv, clauses = build(n, m)
    assert nv == (m + 1) // 2
    assert all(1 <= abs(lit) <= nv for clause in clauses for lit in clause)
    for bits in product((False, True), repeat=nv):
        left = bits
        full = left + left[::-1][m % 2 :]
        expected = not any(all(full[i - 1] for i in ap) for ap in progressions(m, 3))
        expected &= not any(all(not full[i - 1] for i in ap) for ap in progressions(m, n))
        accepted = all(any(bits[abs(lit) - 1] == (lit > 0) for lit in clause) for clause in clauses)
        assert accepted == expected, (n, m, bits)


def test_dimacs_preserves_header_empty_clause_and_last_clause():
    assert to_dimacs(2, [[1, -2], [], [2]]) == "p cnf 2 3\n1 -2 0\n 0\n2 0\n"
    assert to_dimacs(0, []) == "p cnf 0 0\n"


@pytest.mark.parametrize(
    ("model", "m", "expected"),
    [
        ([1, -2], 3, "121"),
        ([-1, 2], 4, "2112"),
        ([-2, 3, 1], 5, "12121"),
        ([], 4, "2222"),
        ([1], 0, ""),
    ],
)
def test_model_signs_and_mirroring(model, m, expected):
    assert colouring_from_model(model, m) == expected
