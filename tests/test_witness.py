import pytest

from pdw.reach import classify
from pdw.verify_witness import check, has_progression, is_palindrome


@pytest.mark.parametrize(
    ("positions", "length", "expected"),
    [
        (set(), -1, False),
        (set(), 0, False),
        ({1, 2, 3}, 0, False),
        (set(), 1, False),
        ({7}, 1, True),
        ({7}, 2, False),
        ({2, 9}, 2, True),
        ({2, 9}, 3, False),
        ({2, 5, 8}, 3, True),
        ({2, 5, 9}, 3, False),
        ({1, 4, 7, 10}, 4, True),
        ({1, 4, 7, 11}, 4, False),
        ({1, 4, 7, 10, 13}, 4, True),
        ({1, 2, 6, 10}, 3, True),
    ],
)
def test_progression_boundaries(positions, length, expected):
    assert has_progression(positions, length) is expected


@pytest.mark.parametrize(
    ("colouring", "n"), [("", 3), ("11", 1), ("121", 2), ("11211", 3), ("1221", 3)]
)
def test_valid_witness_and_reach_verdict(colouring, n):
    assert is_palindrome(colouring)
    assert check(colouring, n) is None
    assert classify(colouring, n) == ("SAT_WITNESS_VERIFIED", None)


@pytest.mark.parametrize(
    ("colouring", "n", "reason"),
    [
        ("21211", 3, "colouring is not palindromic"),  # one flipped colour in 11211
        ("1121", 3, "colouring is not palindromic"),  # truncated witness
        ("11011", 3, "colouring uses characters other than 1 and 2"),
        ("11111", 3, "part 1 contains a 3-term arithmetic progression"),
        ("22222", 3, "part 2 contains a 3-term arithmetic progression"),
        ("1221", 2, "part 2 contains a 2-term arithmetic progression"),
        ("121", 1, "part 2 contains a 1-term arithmetic progression"),
    ],
)
def test_specific_witness_corruptions(colouring, n, reason):
    assert check(colouring, n) == reason
    assert classify(colouring, n) == ("SAT_WITNESS_BAD", reason)
