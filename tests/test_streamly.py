import io

import pytest

import streamly


@pytest.mark.parametrize("sequence, at_index, expected_part1, expected_part2", (
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], 4, [1, 2, 3, 4], [5, 6, "foo", "bar"]),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], 0, [], [1, 2, 3, 4, 5, 6, "foo", "bar"]),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], -0, [], [1, 2, 3, 4, 5, 6, "foo", "bar"]),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], -1, [1, 2, 3, 4, 5, 6, "foo"], ["bar"]),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], -4, [1, 2, 3, 4], [5, 6, "foo", "bar"]),
    (["bar"], 4, ["bar"], []),
    (["bar"], 0, [], ["bar"]),
    (["bar"], -0, [], ["bar"]),
    (["bar"], -1, [], ["bar"]),
    (["bar"], -4, [], ["bar"]),
))
def test_chop(sequence, at_index, expected_part1, expected_part2):
    # _chop now belongs to stream.Streamly so this needs refactoring!
    part1, part2 = streamly._chop(sequence, at_index)
    assert part1 == expected_part1
    assert part2 == expected_part2


def test_stream():
    string_io = io.StringIO()
    stream = streamly.Stream(string_io, 0)
    assert stream.stream is string_io
    assert stream.length == 0
