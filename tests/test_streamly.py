import io

import streamly


def test_stream():
    string_io = io.StringIO()
    stream = streamly.Stream(string_io, 0)
    assert stream.stream is string_io and stream.length == 0
