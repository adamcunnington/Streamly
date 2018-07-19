import logging


_MIN_READ_SIZE = 128


logging.getLogger(__name__).addHandler(logging.NullHandler())


class Stream:
    def __init__(self, stream, length):
        self.stream = stream
        self.length = length


class Streamly:
    def __init__(self, *streams, header_row_identifier=b"", new_line_identifier=b"\n", footer_identifier=None,
                 retain_first_header_row=True):
        if not streams:
            raise ValueError("there must be at least one stream")
        self.streams = [{
            "stream": getattr(stream, "stream", stream),
            "header_found": False,
            "header_row_found": False,
            "length": getattr(stream, "length", None),
            "footer_found": False,
            "bytes_read": 0
        } for stream in streams]
        self.header_row_identifier = header_row_identifier
        self.new_line_identifier = new_line_identifier
        self.footer_identifier = footer_identifier
        self.retain_first_header_row = retain_first_header_row
        self.current_stream_index = 0
        self.end_reached = False
        self._end_of_prev_read = b""
        self._bytes_read_ahead = b""
        self._bytes_backlog = b""

    @staticmethod
    def _read(stream, size):
        _bytes = stream["stream"].read(size)
        stream["bytes_read"] += len(_bytes)
        return _bytes

    @property
    def contains_footer(self):
        return self.footer_identifier is not None

    @property
    def contains_header_row(self):
        return self.header_row_identifier is not None

    @property
    def current_stream(self):
        return self.streams[self.current_stream_index]

    @property
    def is_first_stream(self):
        return self.current_stream_index == 0

    @property
    def footer_found(self):
        return self.current_stream["footer_found"]

    @property
    def header_found(self):
        return self.current_stream["header_found"] and self.current_stream["header_row_found"]

    @property
    def is_last_stream(self):
        return self.current_stream_index == len(self.streams) - 1

    def _end_stream(self):
        self.current_stream["stream"].close()
        if self.is_last_stream:
            self.end_reached = True
        else:
            self.current_stream_index += 1

    def _footer_check_needed(self):
        return self.contains_footer and not self.footer_found

    def _header_check_needed(self):
        return self.contains_header_row and not self.header_found

    def _log_progress(self):
        pass

    def _remove_footer(self, _bytes, max_size):  # bytes is a builtin name
        index = _bytes.find(self.footer_identifier)
        if index == -1:
            head = self._read(self.current_stream, len(self.footer_identifier) - 1)
            index = (_bytes + head).index(self.footer_identifier)
            if index == -1:
                if index > max_size:
                    return _bytes[: max_size], _bytes[max_size: ] + head
                return _bytes, head
        self._end_stream()
        return _bytes[: index], b""

    def _remove_header(self, _bytes):  # bytes is a builtin name
        current_stream = self.current_stream
        start = None
        if not current_stream["header_found"]:
            index = _bytes.find(self.header_row_identifier)
            if index == -1:
                return b"", _bytes[-(len(self.header_row_identifier) - 1): ]
            current_stream["header_found"] = True
            start = index
        if not self.is_first_stream or not self.retain_first_header_row:
            index = _bytes.find(self.new_line_identifier, start)
            if index == -1:
                return b"", _bytes[-(len(self.new_line_identifier) - 1): ]
            index += 1
        return (_bytes if index == 0 else _bytes[index: ]), b""

    def read(self, size=8192):
        if self.end_reached and not self._bytes_backlog:
            # Signify to the caller that the stream is exhausted
            return b""
        bytes_to_return = b""
        total_size = 0
        while total_size < size:
            size_remaining = size - total_size
            if self._bytes_backlog:
                processed_bytes = self._bytes_backlog[: size_remaining]
                self._bytes_backlog = self._bytes_backlog[size_remaining: ]
            elif self.end_reached:
                break
            else:
                processed_bytes = b""
                # If there are a small amount of bytes left to read, we could enter in to a situation where there are a
                # large volumes of reads needed, i.e. perhaps we're still trying to identify where the header ends,
                # constantly evaluating just 5 additional bytes at a time. Therefore, read at least the _MIN_READ_SIZE.
                # Any bytes read ahead that won't be returned just now will be saved for a subsequent read.
                raw_bytes = self._read(self.current_stream, max(size_remaining, _MIN_READ_SIZE))
                # There's no point doing checks for the header and footer if there are no bytes left to read as the
                # result will be the same as the last iteration of the loop.
                if raw_bytes:
                    if self._header_check_needed():
                        self._end_of_prev_read, processed_bytes, self._bytes_read_ahead = self._remove_header(
                            self._end_of_prev_read + raw_bytes, size_remaining)
                    # Don't look for the footer unless the header is found. Can't do an else if as it might have only
                    # just been found.
                    if self.header_found and self._footer_check_needed():
                        processed_bytes, self._bytes_read_ahead = self._remove_footer(
                            self._bytes_read_ahead + raw_bytes, size_remaining)
                else:
                    self._end_stream()
                    # We know that the stream we are reading from is exhausted but there could be data that was read
                    # ahead in the previous footer check. We now know that this data can be returned but it could be
                    # larger than the size_remaining and so, save it to a backlog that will be returned in subsequent
                    # calls.
                    self._bytes_backlog = self._bytes_read_ahead
            total_size += len(processed_bytes)
            bytes_to_return += processed_bytes
        return bytes_to_return
