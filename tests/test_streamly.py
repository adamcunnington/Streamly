import io

import streamly


def test_chop():
    sequence = [1, 2, 3, 4, 5, 6, "foo", "bar"]
    part1, part2 = streamly._chop(sequence, 4)
    assert part1 == [1, 2, 3, 4] and part2 == [5, 6, "foo", "bar"]


def test_stream():
    string_io = io.StringIO()
    stream = streamly.Stream(string_io, 0)
    assert stream.stream is string_io and stream.length == 0
