"""Provide a wrapper for streams (file-like objects) that increases flexibility without costing efficiency.

Include the following functionality during on the fly read operations:
- Adjoining of multiple streams
- Removal of header and footer data, identified by a value (e.g. byte string or string)
- Logging of read progress
- Guaranteed read size (where the data is not yet exhausted)
- Consistent API for streams returning byte strings or strings
"""


import logging


# Singleton sentinel values for parameter defaults. Use class rather than object() so Sphinx documents correctly.
class _Sentinel:
    pass


_EMPTY = _Sentinel()
_LINE_FEED = _Sentinel()


_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class Stream:
    """Provide a simple object to represent a stream resource with a known length for use with :class:`Streamly`.

    If the length is unknown, the user should just pass the raw stream object directly to Streamly.

    :param stream: the file-like object
    :param int length: the length of the stream
    """

    def __init__(self, stream, length):
        """Initialise a stream object with a length."""
        self.stream = stream
        self.length = length


class Streamly:
    """Provide a wrapper for streams (aka file-like objects).

    :param streams: one or more stream objects to be read. Each object can either be a stream object or some sort of
        container object that implements a stream attribute and optionally, a length attribute. i.e.
        :class:`streamly.Stream`.
    :param bool binary: whether or not the underlying streams return bytes when read. If it returns text, set this to
        ``False``. Defaults to ``True``.
    :param header_row_identifier: the value to use to identify where the header row starts. If reading the stream
        returns bytes, this should be a byte string. If there is no header, explicitly pass ``None``. Defaults to an
        empty byte string or empty string depending on the value of binary. I.e. the header row is encountered at the
        very start of the stream.
    :param header_row_end_identifier: the value to use to identify where the header row ends. If reading the stream
        returns bytes, this should be a byte string. Defaults to a line feed byte string or a line feed string character
        depending on the value of binary.
    :param footer_identifier: the value to use to identify where the footer starts. Defaults to ``None``, i.e. no
        footer.
    :param bool retain_first_header_row: whether or not the read method should retain the header row of the first
        stream. Headers are removed from the second stream onwards regardless.
    :raises: ValueError if no streams are passed.

    :ivar bool binary: see Parameters.
    :ivar bool contains_header_row: ``True`` if `header_row_identifier` is not ``None``.
    :ivar bool contains_footer: ``True`` if `footer_identifier` is not ``None``.
    :ivar dict current_stream: The stream details that will be referenced on the next read operation.
    :ivar int current_stream_index: The index of the current stream that will be referenced on the next read operation.
    :ivar bool end_reached: ``True`` if the final underlying stream has been exhausted.
    :ivar footer_identifier: See Parameters.
    :ivar header_row_identifier: See Parameters.
    :ivar header_row_end_identifier: See Parameters.
    :ivar bool is_first_stream: ``True`` if the current stream is the first stream.
    :ivar bool is_last_stream: ``True`` if the current stream is the last stream.
    :ivar bool retain_first_header_row: See Parameters.
    :ivar list streams: the list of streams passed on instantiation but as dicts with items that are used to track
        progress.
    :ivar int total_length: The total length of all the streams. If any stream's length is unknown, this value will be
        ``None``.
    :ivar int total_length_read: The total length read across all the streams.
    :ivar int total_streams: The amount of underlying streams.
    """

    def __init__(self, *streams, binary=True, header_row_identifier=_EMPTY, header_row_end_identifier=_LINE_FEED,
                 footer_identifier=None, retain_first_header_row=True):
        """Initialise a Stream wrapper object with header and footer identifiers referenced in the read process."""
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

    def _chop(self, sequence, at_index):
        # If the sequence is smaller than the index then there is no need to slice the list
        if len(sequence) <= at_index:
            return sequence, self._empty
        return sequence[:at_index], sequence[at_index:]

    def _end_stream(self):
        self.current_stream["stream"].close()
        if self.is_last_stream:
            self.end_reached = True
        else:
            self.current_stream_index += 1
        self._data_backlog = self._data_read_ahead

    def _footer_check_needed(self):
        return self.contains_footer and not self.current_stream["footer_found"]

    def _header_check_needed(self):
        return self.contains_header_row and (not self.current_stream["header_row_found"] or
                                             self._seeking_header_row_end)

    def _log_progress(self):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        _logger.info("Reading Stream %s/%s", self.current_stream_index + 1, self.total_streams)
        length_read = current_stream["length_read"]
        length = current_stream["length"]
        progress = "?" if length is None else "%.2f%%" % ((length_read / length) * 100)
        _logger.info("Stream Progress: %s/%s (%s%%)", length_read, length or "?", progress)
        total_progress = "?" if self.total_length is None else "%.2f%%" % ((self.total_length_read /
                                                                            self.total_length) * 100)
        if self.total_streams > 1:
            _logger.info("Overall Progress: %s/%s (%s%%)", self.total_length_read, self.total_length or "?",
                         total_progress)

    def _read(self, size):
        if size <= 0:
            return self._empty
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        data = current_stream["stream"].read(size)
        current_stream["length_read"] += len(data)
        self._log_progress()
        return data

    def _remove_footer(self, raw_data):
        index = raw_data.find(self.footer_identifier)
        if index == -1:
            footer_identifier_length = len(self.footer_identifier)
            if footer_identifier_length > 1:
                # If the footer's length > 1, it is possible that it starts at the end of current raw_data but ends in
                # the next read. Given that we need to return data up until the footer is encountered, we need to read
                # ahead to check - specifically, we need to read a size of 1 less than the footer identifier length in
                # case it starts in the very last byte (or string character) of this read.
                raw_data += self._read(footer_identifier_length - 1)
                index = raw_data.find(self.footer_identifier)
            if index == -1:
                return raw_data
        self.current_stream["footer_found"] = True
        # On the off chance that the footer starts exactly at the start of raw_data, then we already have all the data
        # we want and so we should return an empty byte string (or empty string).
        return self._empty if index == 0 else raw_data[:index]

    def _remove_header(self, raw_data):
        # Save current_stream so property does not need to be evaluated more than once
        current_stream = self.current_stream
        start = None
        if not current_stream["header_row_found"]:
            index = raw_data.find(self.header_row_identifier)
            if index == -1:
                # If the header's length > 1, it is possible that it starts at the end of current raw_data but ends in
                # the next read. We need to "save" the last x length of raw_data so it can be included in the subsequent
                # read's search for the header.
                return self._calc_end_of_prev_read(raw_data, self.header_row_identifier), self._empty
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
                # Similarly to the previous index == 1 check, we must return the end of raw_data in case the header row
                # does start towards the end of raw_data but overlaps into the next read. Note that
                # _calc_end_of_prev_read will return an empty byte string (or empty string) if the identifier's length
                # was 1 as the overlap scenario is then not possible.
                return self._calc_end_of_prev_read(raw_data, self.header_row_end_identifier), self._empty
            self._seeking_header_row_end = False
            # Like in the case of the header_row_identifier, add the length of the identifier to get the index of where
            # the data actually starts.
            index += len(self.header_row_end_identifier)
        # If the index is 0 (header was found at start of raw_data and no header row end seeking was necessary), slicing
        # the list is an unnecessary expense.
        return self._empty, raw_data if index == 0 else raw_data[index:]

    def read(self, size=8192):
        """Read incrementally from the underlying streams.

        Automatically handle the removal of headers and footers based
        on the instance properties and iterate through the underlying stream objects where there are more than one.
        Always return data of length, size, unless the underlying streams are exhausted. The subsequent read will return
        an empty byte string or empty string depending on self.binary.

        :param int size: the length to return
        :returns: either a byte string or string depending on what the underlying streams return when read
        """
        if self.end_reached and not self._data_backlog:
            _logger.debug("End reached and backlog empty. Returning empty.")
            # The end of the streams may be reached but if there is data in the backlog, there is still work to be
            # done. If not, an empty byte string (or empty string) will signify to the caller that the stream is
            # exhausted.
            return self._empty
        data_to_return = self._empty
        total_size = 0
        while total_size < size:
            size_remaining = size - total_size
            if self._data_backlog:
                _logger.debug("Data found on the backlog.")
                # Data on the backlog must be prioritised. It's possible the stream is exhausted, and thus no more data
                # to be read, but we need to return the backlog first.
                processed_data, self._data_backlog = self._chop(self._data_backlog, size_remaining)
            elif self.end_reached:
                _logger.debug("End of the final stream has been reached. Breaking out of loop.")
                # We now know that the backlog is empty and the end of the streams are reached. Therefore, we can break
                # out of the loop and return to the caller. Their subsequent call will be caught by the top-level if
                # statement.
                break
            elif self.current_stream["footer_found"]:
                _logger.debug("Footer found. Ending current stream.")
                self._end_stream()
                continue
            else:
                _logger.debug("Reading data from the underlying stream...")
                raw_data = self._read(size_remaining - len(self._data_read_ahead))
                if not raw_data and not self._data_read_ahead:
                    _logger.debug("Underlying stream returned no data.")
                    self._end_stream()
                    continue
                else:
                    if self._header_check_needed():
                        _logger.debug("Looking for header...")
                        self._end_of_prev_read, processed_data = self._remove_header(self._end_of_prev_read + raw_data)
                    else:
                        processed_data = raw_data
                    # Don't look for the footer unless the header is found. Can't do an else if as the header may have
                    # only just been found.
                    if not self._header_check_needed() and self._footer_check_needed():
                        _logger.debug("Looking for footer...")
                        processed_data = self._remove_footer(self._data_read_ahead + processed_data)
                    processed_data, self._data_read_ahead = self._chop(processed_data, size_remaining)
            total_size += len(processed_data)
            data_to_return += processed_data
        return data_to_return
