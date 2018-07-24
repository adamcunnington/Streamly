import io
import logging

import pytest

import streamly


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    def __init__(self, *args, **kwargs):
        self.messages = None
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.upper()].append(record.getMessage())

    def reset(self):
        self.messages = {
            "DEBUG": [],
            "INFO": [],
            "WARNING": [],
            "ERROR": [],
            "CRITICAL": [],
        }


_general_test_data = (
b"""Header
Metadata
Unwanted
=
Garabage

Report Fields:
col1,col2,col3,col4
START,foo,bar,baz
lorem,foo,bar,baz
lorem,foo,bar,baz
lorem,foo,bar,baz
lorem,foo,bar,baz
lorem,foo,bar,baz
lorem,foo,bar,baz
lorem,foo,bar,baz
Grand Total:,0,0,1000,0
More
Footer
Garbage
"""
)


def _general_byte_stream():
    return io.BytesIO(_general_test_data)


def _general_text_stream():
    return io.StringIO(_general_test_data.decode(encoding="utf8"))


def test_stream():
    string_io = io.StringIO()
    stream = streamly.Stream(string_io, 100)
    assert stream.stream is string_io
    assert stream.length == 100


class TestStreamly(object):
    def test_current_stream(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream)
        assert wrapped_stream.current_stream["stream"] is raw_stream
        wrapped_stream.current_stream_index += 1
        with pytest.raises(IndexError):
            _ = wrapped_stream.current_stream

    def test_is_first_stream(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream, raw_stream)
        assert wrapped_stream.is_first_stream
        wrapped_stream.current_stream_index += 1
        assert not wrapped_stream.is_first_stream

    def test_is_last_stream(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream, raw_stream)
        assert not wrapped_stream.is_last_stream
        wrapped_stream.current_stream_index += 1
        assert wrapped_stream.is_last_stream

    def total_length_read(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream, header_row_identifier=None)
        assert wrapped_stream.total_length_read == 0
        _ = wrapped_stream.read(50)
        assert wrapped_stream.total_length_read == 50

    def test__calc_end_of_prev_read(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream)
        data = wrapped_stream.read(50)
        one_long_identifier = b"\n"
        assert wrapped_stream._calc_end_of_prev_read(data, one_long_identifier) == wrapped_stream._empty
        six_long_identifier = b"Header"
        assert wrapped_stream._calc_end_of_prev_read(data, six_long_identifier) == data[-5:]

    def test__calc_total_length(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream)
        assert wrapped_stream._calc_total_length() is None
        stream_with_length = streamly.Stream(raw_stream, 50)
        wrapped_stream = streamly.Streamly(stream_with_length, stream_with_length)
        assert wrapped_stream._calc_total_length() == 100

    @pytest.mark.parametrize("sequence, at_index, expected_part1, expected_part2", (
        ([1, 2, 3, 4, 5, 6, "foo", "bar"], 4, [1, 2, 3, 4], [5, 6, "foo", "bar"]),
        ([1, 2, 3, 4, 5, 6, "foo", "bar"], 0, [], [1, 2, 3, 4, 5, 6, "foo", "bar"]),
        ([1, 2, 3, 4, 5, 6, "foo", "bar"], -0, [], [1, 2, 3, 4, 5, 6, "foo", "bar"]),
        ([1, 2, 3, 4, 5, 6, "foo", "bar"], -1, [1, 2, 3, 4, 5, 6, "foo"], ["bar"]),
        ([1, 2, 3, 4, 5, 6, "foo", "bar"], -4, [1, 2, 3, 4], [5, 6, "foo", "bar"]),
        (["bar"], 4, ["bar"], ""),
        (["bar"], 0, [], ["bar"]),
        (["bar"], -0, [], ["bar"]),
        (["bar"], -1, [], ["bar"]),
        (["bar"], -4, [], ["bar"]),
    ))
    def test__chop(self, sequence, at_index, expected_part1, expected_part2):
        raw_stream = _general_text_stream()
        wrapped_stream = streamly.Streamly(raw_stream, binary=False)
        part1, part2 = wrapped_stream._chop(sequence, at_index)
        assert part1 == expected_part1
        assert part2 == expected_part2

    def test__end_stream(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream)
        wrapped_stream._end_stream()
        with pytest.raises(ValueError):
            _ = wrapped_stream.streams[0]["stream"].read()
        assert wrapped_stream.end_reached

    def test__footer_check_needed(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream)
        assert not wrapped_stream._footer_check_needed()
        wrapped_stream = streamly.Streamly(raw_stream, footer_identifier=b"Grand")
        assert wrapped_stream._footer_check_needed()

    def test__header_check_needed(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream, header_row_identifier=None)
        assert not wrapped_stream._header_check_needed()
        wrapped_stream = streamly.Streamly(raw_stream)
        assert wrapped_stream._header_check_needed()

    def test__log_progress(self):
        raw_stream = _general_byte_stream()
        wrapped_stream = streamly.Streamly(raw_stream)
        logger = logging.getLogger("streamly")
        mock_handler = MockLoggingHandler()
        logger.addHandler(mock_handler)
        logger.setLevel(logging.INFO)
        wrapped_stream._log_progress()
        assert mock_handler.messages["INFO"]