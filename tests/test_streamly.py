import io

import pytest

import streamly


@pytest.mark.parametrize("sequence, at_index", (
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], 4),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], 0),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], -0),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], -1),
    ([1, 2, 3, 4, 5, 6, "foo", "bar"], -4),
    (["bar"], 4),
    (["bar"], 0),
    (["bar"], -0),
    (["bar"], -1),
    (["bar"], -4),
))
def test_chop(sequence, at_index):
    sequence = [1, 2, 3, 4, 5, 6, "foo", "bar"]
    part1, part2 = streamly._chop(sequence, 4)
    assert part1 + part2 == sequence


def test_stream():
    string_io = io.StringIO()
    stream = streamly.Stream(string_io, 0)
    assert stream.stream is string_io
    assert stream.length == 0
