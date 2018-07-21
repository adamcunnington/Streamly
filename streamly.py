import time
"""Provide a wrapper for streams (aka file-like objects) that increases flexibility without costing efficiency.

Include the following functionality during on-the-fly read operations:
- Adjoining of multiple streams
- Removal of header and footer data, identified by a value (e.g. byte string string or string)
- Logging of read progress (accessible through logging.getLogger("streamly"))
- Guaranteed read size (where the data is not yet exhausted)
- Consistent API for both byte strings and strings

"""


import logging


_EMPTY = object()
_LINE_FEED = object()
_MIN_READ_SIZE = 128


_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


def _chop(sequence, at_index):
    return sequence[:at_index], sequence[at_index:]


class Stream:
    """Provide a simple object (stub!) to represent a stream resource that has a known length for use with Streamly."""

    def __init__(self, stream, length):
        """Initialise a stream object with a length.

        If the length is unknown, just pass the raw stream object directly to Streamly.

        :param stream: file-like object
        :param length: integer length
        """
        self.stream = stream
        self.length = length


class Streamly:
    """Provide a wrapper for streams (aka file-like objects) that increases flexibility without costing efficiency."""

    def __init__(self, *streams, binary=True, header_row_identifier=_EMPTY, header_row_end_identifier=_LINE_FEED,
                 footer_identifier=None, retain_first_header_row=True):
        """Initialise a Stream wrapper object with header and footer identifiers to be utilised during the read process.

        :param streams: one or more stream objects to be read. Each object can either be a stream object or some sort of
        container object that implements a stream attribute and optionally, a length attribute. i.e. streamly.Stream.
        :param binary: whether or not the underlying streams return bytes when read. If it returns text, set this to
        False. Defaults to True.
        :param header_row_identifier: the value to use to identify where the header row starts. If reading the stream
        returns bytes, this should be a byte string. If there is no header, explicitly pass None. Defaults to an empty
        byte string or empty string depending on the value of binary. I.e. the header row is encountered at the very
        start of the stream.
        :param header_row_end_identifier: the value to use to identify where the header row ends. If reading the stream
        returns bytes, this should be a byte string. Defaults to a line feed byte string or a line feed string character
        depending on the value of binary.
        :param footer_identifier: the value to use to identify where the footer starts. Defaults to None, i.e. no
        footer.
        :param retain_first_header_row: whether or not the read method should retain the header row of the first stream.
        Headers are removed from the second stream onwards regardless.
        """
        if not streams:
            raise ValueError("there must be at least one stream")
        self.streams = [{
            "length_read": 0,
            "stream": getattr(stream, "stream", stream),
            "header_row_found": False,
            "footer_found": False,
            "length": getattr(stream, "length", None)
        } for stream in streams]
        self.binary = binary
        self._empty = b"" if self.binary else ""
        self.header_row_identifier = header_row_identifier if header_row_identifier is not _EMPTY else self._empty
        if header_row_end_identifier is _LINE_FEED:
            self.header_row_end_identifier = b"\n" if self.binary else "\n"
        else:
            self.header_row_end_identifier = header_row_end_identifier
        self.footer_identifier = footer_identifier
        self.retain_first_header_row = retain_first_header_row
        self.contains_header_row = self.header_row_identifier is not None
        self.contains_footer = self.footer_identifier is not None
        self.current_stream_index = 0
        self.total_streams = len(self.streams)
        self.total_length = self._calc_total_length()
        self.end_reached = False
        self._seeking_header_row_end = False
        self._end_of_prev_read = self._empty
        self._data_read_ahead = self._empty
        self._data_backlog = self._empty

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
    def total_length_read(self):
        return sum(stream["length_read"] for stream in self.streams)

    def _calc_end_of_prev_read(self, data, identifier):
        identifier_length = len(identifier)
        return data[-(identifier_length - 1):] if identifier_length > 1 else self._empty

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
        length_read = current_stream["length_read"]
        length = current_stream["length"]
        progress = "?" if length is None else "%.2f%%" % ((length_read / length) * 100)
        _logger.info("Stream Progress: %s/%s (%s%%)" %(length_read, length or "?", progress))
        total_progress = "?" if self.total_length is None else "%.2f%%" % ((self.total_length_read /
                                                                            self.total_length) * 100)
        if self.total_streams > 1:
            _logger.info("Overall Progress: %s/%s (%s%%)" %(self.total_length_read, self.total_length or "?",
                                                            total_progress))

    def _read(self, size):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        data = current_stream["stream"].read(size)
        current_stream["length_read"] += len(data)
        self._log_progress()
        return data

    def _remove_footer(self, raw_data, max_size):
        index = raw_data.find(self.footer_identifier)
        if index == -1:
            # The footer was not found but if its length > 1, it's possible that it could be at the end of raw_data but
            # this would not be known to us until subsequent read(s). Unlike in the case of the header removal where we
            # just return an empty byte string (or empty string) if the header has not yet been started, here we are
            # trying to return data up until the footer starts and so we must know when that is! Therefore, read some
            # more data - specifically 1 less than the length of the identifier.
            data_read_ahead = self._read(len(self.footer_identifier) - 1)
            index = (raw_data + data_read_ahead).find(self.footer_identifier)
            if index == -1:
                return raw_data, data_read_ahead
        self.current_stream["footer_found"] = True
        if index == 0:
            # On the off chance that the footer starts exactly at the start of raw_data, then we already have all the
            # data we want and so we should return an empty byte string (or empty string).
            return self._empty, self._empty
        processed_data = raw_data[:index]
        data_read_ahead = self._empty
        if len(processed_data) > max_size:
            # The data to return could be longer than the max size requested because the raw_data passed is very likely
            # to have started with a read ahead from the previous call and the match may have occurred in that prepend.
            processed_data, data_read_ahead = _chop(processed_data, max_size)
        return processed_data, data_read_ahead

    def _remove_header(self, raw_data, max_size):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        start = None
        if not current_stream["header_row_found"]:
            index = raw_data.find(self.header_row_identifier)
            if index == -1:
                # The header row identifier was not found but if its length > 1, it's possible that it could actually
                # be at the end of raw_data but this is not known to us until subsequent read(s) where we have enough
                # data to evaluate. Therefore, return the end of raw_data - specifically 1 less than the length of the
                # identifier.
                return self._calc_end_of_prev_read(raw_data, self.header_row_identifier), self._empty, self._empty
            current_stream["header_row_found"] = True
            # Add the length of the header_row_identifier to get the index where the header row actually starts. This
            # has the nice property of being 0 if the header row identifier was an empty string (i.e. start of stream)
            index += len(self.header_row_identifier)
            start = index
        # The header row has now been found but if this is not the first stream or the user does not want to retain the
        # header row from the first stream, then we need to look for the line end.
        if not self.is_first_stream or not self.retain_first_header_row:
            self._seeking_header_row_end = True
            index = raw_data.find(self.header_row_end_identifier, start)
            if index == -1:
                # Similarly to the previous top-level if block, we must return the end of raw_data in case the
                # identifier does start towards the end of raw_data but overlaps into the next read. Note that
                # _calc_end_of_prev_read will return an empty byte string (or empty string) if the identifier's length
                # was 1 as the overlap scenario is then not possible.
                return self._calc_end_of_prev_read(raw_data, self.header_row_end_identifier), self._empty, self._empty
            self._seeking_header_row_end = False
            # Like in the case of the header_row_identifier, add the length of the identifier to get the index of where
            # the data actually starts.
            index += len(self.header_row_end_identifier)
        # Note that with regards to code paths, technically speaking, this index may be referenced before it is
        # assigned. However, this is not possible based on the logic and if it does happen, it's a bug and we want a
        # NameError.
        processed_data = raw_data if index == 0 else raw_data[index:]
        data_read_ahead = self._empty
        # If the index is 0 (header was found at start of raw_data and no header row end seeking was necessary), don't
        # unnecessarily slice the list.
        if len(processed_data) > max_size:
            # The data to return could be longer than the max size requested because the raw_data passed may have
            # included data from the end of the previous call and the match may have occurred within that prepend.
            processed_data, data_read_ahead = _chop(processed_data, max_size)
        return self._empty, processed_data, data_read_ahead

    def read(self, size=8192):
        """Read from the underlying streams, remembering the position of the previous read as per regular read
        behaviour. Automatically handle the removal of headers and footers based on the instance properties and iterate
        through the underlying stream objects where there are more than one. Always return data of length, size,
        unless the underlying streams are fully read. The subsequent read will return an empty byte string or empty
        string depending on self.binary

        :param size: the length to return
        :return: either a byte string or string depending on what the underlying streams return when read
        """
        if self.end_reached and not self._data_backlog:
            # The end of the streams may be reached but if there is data in the backlog, there is still work to be
            # done. If not, an empty byte string (or empty string) will signify to the caller that the stream is
            # exhausted.
            return self._empty
        data_to_return = self._empty
        total_size = 0
        while total_size < size:
            size_remaining = size - total_size - len(self._data_read_ahead)
            if self._data_backlog:
                _logger.debug("Data found on the backlog")
                # Data on the backlog must be prioritised. It's possible the stream is exhausted, and thus no more data
                # to be read, but we need to return the backlog first.
                processed_data, self._data_backlog = _chop(self._data_backlog, size_remaining)
            elif self.end_reached:
                _logger.debug("The end of the last stream has been reached")
                # We now know that the backlog is empty and the end of the streams are reached. Therefore, we can break
                # out of the loop and return to the caller but the penultimate time. Their subsequent call will be
                # caught by the top-level if statement.
                break
            else:
                processed_data = self._empty
                # If there are a small amount of data left to read, we could enter in to a situation where there are a
                # large volumes of reads needed, i.e. perhaps we're still trying to identify where the header ends,
                # constantly evaluating a small amount of data each time. Therefore, read at least the _MIN_READ_SIZE.
                # Any data read ahead that won't be returned just now will be saved for a subsequent read.
                _logger.debug("Reading raw data")
                raw_data = self._read(max(size_remaining, _MIN_READ_SIZE))
                _logger.debug(len(raw_data))
                # There's no point doing checks for the header and footer if there is no data left to read as the
                # result will be the same as the last iteration of the loop.
                if raw_data:
                    if self._header_check_needed():
                        _logger.debug("Looking for header...")
                        self._end_of_prev_read, processed_data, self._data_read_ahead = self._remove_header(
                            self._end_of_prev_read + raw_data, size_remaining)
                    else:
                        # Given the size of the raw_data read takes into account the length of self._data_read_ahead,
                        # we know that self._data_read_ahead + raw_data won't be too long and so we don't need a call to
                        # _chop
                        processed_data, self._data_read_ahead = _chop(self._data_read_ahead + raw_data, size_remaining)
                    # Don't look for the footer unless the header is found. Can't do an else if as the header may have
                    # only just been found.
                    if not self._header_check_needed() and self._footer_check_needed():
                        _logger.debug("Looking for footer...")
                        processed_data, self._data_read_ahead = self._remove_footer(processed_data, size_remaining)
                else:
                    _logger.debug("Underlying stream returned no data")
                    self._end_stream()
                    # We know that the stream we are reading from is exhausted but there could be data that was read
                    # ahead in the previous footer check. We know that this data is ready to be returned but it could be
                    # larger than the size_remaining and so, save it to a backlog that will be returned in subsequent
                    # calls.
                    self._data_backlog = self._data_read_ahead
                print(repr(self._end_of_prev_read), repr(processed_data), repr(self._data_read_ahead), repr(self._data_backlog))
            time.sleep(2)
            total_size += len(processed_data)
            data_to_return += processed_data
        return data_to_return
