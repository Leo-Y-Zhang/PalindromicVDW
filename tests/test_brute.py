import pytest

from pdw.brute import pair, satisfiable


@pytest.mark.parametrize(
    ("n", "m", "expected"),
    [
        (1, 0, (True, "")),
        (1, 2, (True, "11")),
        (1, 3, (False, None)),
        (2, 3, (True, "121")),
        (3, 5, (True, "11211")),
        (3, 6, (True, "112211")),
        (3, 7, (False, None)),
    ],
)
def test_small_exhaustive_decisions_and_exact_witnesses(n, m, expected):
    assert satisfiable(n, m) == expected


@pytest.mark.parametrize(
    ("n", "cap", "expected"),
    [
        (1, 0, None),
        (1, 2, None),
        (1, 3, None),
        (1, 4, (2, 3)),
        (2, 4, None),
        (2, 5, None),
        (2, 6, None),
        (2, 7, (3, 6)),
        (3, 10, (6, 9)),
        (5, 17, None),
        (5, 19, None),
        (5, 22, (16, 21)),
    ],
)
def test_pair_requires_failures_of_both_parities(n, cap, expected):
    assert pair(n, cap) == expected
