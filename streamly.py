import logging


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
        self._tail = b""
        self._head = b""

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
        return self.current_stream["header_found"]

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

    def _remove_footer(self, _bytes, max_size):
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

    def _remove_header(self, _bytes):
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
        if self.end_reached:
            return b""
        bytes_to_return = b""
        total_size = 0
        while (total_size < size) and not self.end_reached:
            _bytes = b""
            current_stream = self.current_stream
            size_remaining = size - total_size
            size_to_read = max(size_remaining - len(self._head), 0)
            if size_to_read:
                _bytes = self._read(current_stream, size_to_read)
            if not _bytes and not self._head:
                self._end_stream()
                continue
            if self._header_check_needed() or self._tail:
                _bytes, self._tail = self._remove_header(self._tail + _bytes, size_remaining)
            if self._footer_check_needed():
                _bytes = self._remove_footer(self._head + _bytes, size_remaining)
            total_size += len(_bytes)
            bytes_to_return += _bytes
        return bytes_to_return
