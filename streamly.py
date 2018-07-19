import logging


_MIN_READ_SIZE = 128


_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


def _calc_end_of_prev_read(_bytes, identifier):  # bytes is a builtin name
    identifier_length = len(identifier)
    return _bytes[-(identifier_length - 1):] if identifier_length > 1 else b""


def _chop(iterable, at_index):
    return iterable[:at_index], iterable[at_index:]


class Stream:
    def __init__(self, stream, length):
        self.stream = stream
        self.length = length


class Streamly:
    def __init__(self, *streams, header_row_identifier=b"", header_row_end_identifier=b"\n", footer_identifier=None,
                 retain_first_header_row=True):
        if not streams:
            raise ValueError("there must be at least one stream")
        self.streams = [{
            "bytes_read": 0,
            "stream": getattr(stream, "stream", stream),
            "header_row_found": False,
            "footer_found": False,
            "length": getattr(stream, "length", None)
        } for stream in streams]
        self.header_row_identifier = header_row_identifier
        self.header_row_end_identifier = header_row_end_identifier
        self.contains_header_row = self.header_row_identifier is not None
        self.footer_identifier = footer_identifier
        self.contains_footer = self.footer_identifier is not None
        self.retain_first_header_row = retain_first_header_row
        self.current_stream_index = 0
        self.total_streams = len(self.streams)
        self.total_length = self._calc_total_length()
        self.end_reached = False
        self._seeking_header_row_end = False
        self._end_of_prev_read = b""
        self._bytes_read_ahead = b""
        self._bytes_backlog = b""

    @property
    def current_stream(self):
        return self.streams[self.current_stream_index]

    @property
    def is_first_stream(self):
        return self.current_stream_index == 0

    @property
    def is_last_stream(self):
        return self.current_stream_index == self.total_streams - 1

    @property
    def total_bytes_read(self):
        return sum(stream["bytes_read"] for stream in self.streams)

    def _calc_total_length(self):
        accumulative_length = 0
        for stream in self.streams:
            length = stream["length"]
            if length is None:
                return None
            accumulative_length += length
        return accumulative_length

    def _end_stream(self):
        self.current_stream["stream"].close()
        if self.is_last_stream:
            self.end_reached = True
        else:
            self.current_stream_index += 1

    def _footer_check_needed(self):
        return self.contains_footer and not self.current_stream["footer_found"]

    def _header_check_needed(self):
        return self.contains_header_row and (not self.current_stream["header_row_found"] or
                                             self._seeking_header_row_end)
    def _log_progress(self):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        _logger.info("Reading Stream %s/%s" % (self.current_stream_index + 1, self.total_streams))
        bytes_read = current_stream["bytes_read"]
        length = current_stream["length"]
        progress = "?" if length is None else "%.2f%%" % ((bytes_read / length) * 100)
        _logger.info("Stream Progress: %s/%s bytes (%s%%)" %(bytes_read, length or "?", progress))
        total_progress = "?" if self.total_length is None else "%.2f%%" % ((self.total_bytes_read /
                                                                            self.total_length) * 100)
        _logger.info("Overall Progress: %s/%s bytes (%s%%)" %(self.total_bytes_read, self.total_length or "?",
                                                              total_progress))

    def _read(self, size):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        _bytes = current_stream["stream"].read(size)  # bytes is a builtin name
        current_stream["bytes_read"] += len(_bytes)
        return _bytes

    def _remove_footer(self, raw_bytes, max_size):
        index = raw_bytes.find(self.footer_identifier)
        if index == -1:
            # The footer was not found but if it's multiple bytes long, it's possible that it could be at the end of
            # raw_bytes but this would not be known to us until subsequent read(s). Unlike in the case of the header
            # removal here we just return an empty string if the header has not yet been started, we are trying to
            # return data up until the footer starts and so we must know when that is! Therefore, read some more data -
            # specifically 1 less than the length of the identifier.
            bytes_read_ahead = self._read(len(self.footer_identifier) - 1)
            index = (raw_bytes + bytes_read_ahead).find(self.footer_identifier)
            if index == -1:
                return raw_bytes, bytes_read_ahead
        self.current_stream["footer_found"] = True
        if index == 0:
            # On the off chance that the footer starts exactly at the start of raw_bytes, then we already have all the
            # data we want and so we should return an empty string.
            return b"", b""
        processed_bytes = raw_bytes[:index]
        bytes_read_ahead = b""
        if len(processed_bytes) > max_size:
            # The bytes to return could be longer than the max size requested because the raw_bytes passed is very
            # likely to have started with a read ahead from the previous call and the match may have occurred in that
            # prepend.
            processed_bytes, bytes_read_ahead = _chop(processed_bytes, max_size)
        return processed_bytes, bytes_read_ahead

    def _remove_header(self, raw_bytes, max_size):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        start = None
        if not current_stream["header_row_found"]:
            index = raw_bytes.find(self.header_row_identifier)
            if index == -1:
                # The header row identifier was not found but if it's multiple bytes long, it's possible that it could
                # actually be at the end of raw_bytes but this is not known to us until subsequent read(s) where we
                # have enough bytes to evaluate. Therefore, return the end of raw_bytes - specifically 1 less than the
                # length of the identifier.
                return _calc_end_of_prev_read(raw_bytes, self.header_row_identifier), b"", b""
            current_stream["header_row_found"] = True
            start = index
        # The header row has now been found but if this is not the first stream or the user does not want to retain the
        # header row from the first stream, then we need to look for the line end.
        if not self.is_first_stream or not self.retain_first_header_row:
            self._seeking_header_row_end = True
            index = raw_bytes.find(self.header_row_end_identifier, start)
            if index == -1:
                # Similarly to the previous top-level if block, we must return the end of raw_bytes in case the
                # identifier does start towards the end of raw_bytes but overlaps into the next read. Note that
                # _calc_end_of_prev_read will return an empty string if the identifier was only 1 byte long as the
                # overlap scenario is then not possible.
                return _calc_end_of_prev_read(raw_bytes, self.header_row_identifier), b"", b""
            self._seeking_header_row_end = False
            # Unlike in the case of the header row identifier, we don't want to start returning from the found byte
            # but from 1 byte after.
            index += -1
        # Note that with regards to code paths, technically speaking, this index may be referenced before it is
        # assigned. However, this is not possible based on the logic and if it does happen, it's a bug and we want a
        # NameError.
        processed_bytes = raw_bytes if index == 0 else raw_bytes[index:]
        bytes_read_ahead = b""
        # If the index is 0 (header was found at start of raw_bytes and no header row end seeking was necessary), don't
        # unnecessarily slice the list.
        if len(processed_bytes) > max_size:
            # The bytes to return could be longer than the max size requested because the raw_bytes passed may have
            # included bytes from the end of the previous call and the match may have occurred within that prepend.
            processed_bytes, bytes_read_ahead = _chop(processed_bytes, max_size)
        return b"", processed_bytes, bytes_read_ahead

    def read(self, size=8192):
        if self.end_reached and not self._bytes_backlog:
            # The end of the streams may be reached but if there is bytes in the backlog, there is still work to be
            # done. If not, an empty string will signify to the caller that the stream is exhausted
            return b""
        bytes_to_return = b""
        total_size = 0
        while total_size < size:
            size_remaining = size - total_size
            if self._bytes_backlog:
                # Bytes on the backlog must be prioritised. It's possible the stream is exhausted, and thus no more
                # bytes to be read, but we need to return the backlog first.
                processed_bytes, self._bytes_backlog = _chop(self._bytes_backlog, size_remaining)
            elif self.end_reached:
                # We now know that the backlog is empty and the end of the streams are reached. Therefore, we can break
                # out of the loop and return to the caller but the penultimate time. Their subsequent call will be
                # caught by the top-level if statement.
                break
            else:
                processed_bytes = b""
                # If there are a small amount of bytes left to read, we could enter in to a situation where there are a
                # large volumes of reads needed, i.e. perhaps we're still trying to identify where the header ends,
                # constantly evaluating just 5 additional bytes at a time. Therefore, read at least the _MIN_READ_SIZE.
                # Any bytes read ahead that won't be returned just now will be saved for a subsequent read.
                raw_bytes = self._read(max(size_remaining, _MIN_READ_SIZE))
                # There's no point doing checks for the header and footer if there are no bytes left to read as the
                # result will be the same as the last iteration of the loop.
                if raw_bytes:
                    if self._header_check_needed():
                        self._end_of_prev_read, processed_bytes, self._bytes_read_ahead = self._remove_header(
                            self._end_of_prev_read + raw_bytes, size_remaining)
                    # Don't look for the footer unless the header is found. Can't do an else if as it might have only
                    # just been found.
                    if not self._header_check_needed() and self._footer_check_needed():
                        processed_bytes, self._bytes_read_ahead = self._remove_footer(
                            self._bytes_read_ahead + raw_bytes, size_remaining)
                else:
                    self._end_stream()
                    # We know that the stream we are reading from is exhausted but there could be data that was read
                    # ahead in the previous footer check. We know that this data is ready to be returned but it could be
                    # larger than the size_remaining and so, save it to a backlog that will be returned in subsequent
                    # calls.
                    self._bytes_backlog = self._bytes_read_ahead
            total_size += len(processed_bytes)
            bytes_to_return += processed_bytes
        return bytes_to_return
