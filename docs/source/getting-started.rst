===============
Getting Started
===============

Once :ref:`installed <installation>`, launch your virtual environment's interpreter and check that ``streamly`` can be imported::

    >>> import streamly

If you receive a `ModuleNotFoundError <https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError>`_, either something went wrong during the installation process or you have not launched the correct python interpreter.


Usage
-----

Using Streamly is incredibly simple and generally consists of 2 steps:

    #. Create a :ref:`streamly.Streamly <streamly>` object
    #. Replace occurrences of ``<old-stream>.read`` with ``<streamly-object>.read``

1. Create a Streamly Object
^^^^^^^^^^^^^^^^^^^^^^^^^^^

:ref:`Streamly <streamly>`'s constructor expects one or more stream positional argument followed by optional keyword arguments.

Positional Arguments
""""""""""""""""""""

A stream can be anything with a read method that remembers it's position between reads. Typically, this is an OS-level file or data from a network socket such as a HTTP response but Streamly does not care! The streams can either be all text or all bytes.

In order for Streamly to meaningfully :ref:`log progress <logging>`, it must know the total length of the stream(s). This is not required for streamly to work but if the length is known (i.e. the web response includes a Content-Length header), you can create a :ref:`streamly.Stream <stream>` object, and then pass that as an arg to \*streams. For example, if the underlying stream object is a `requests.Response <http://docs.python-requests.org/en/master/user/quickstart/#response-content>`_ stream::

    >>> my_stream = streamly.Stream(raw_stream.raw,
                                    raw_stream.headers["Content-Type"])
    >>> wrapped_stream = streamly.Streamly(my_stream)

.. _keyword_args:

Keyword Arguments
"""""""""""""""""

The following keyword arguments impact the behaviour of the header and footer identification and whether the header row is retained when .read() is called. They are all optional and have sensible defaults:

    * **binary** - By default, streams are assumed to be byte streams, not text streams. This means that the parameter defaults, as well as values internal to the workings of the ``streamly`` object are bytestrings, not strings. As per the `changes introduced in python 3 <https://docs.python.org/3/whatsnew/3.0.html#text-vs-data-instead-of-unicode-vs-8-bit>`_, you must be explicit about the conversion between text and bytes. Therefore, if your stream returns text when read, you must set ``binary=False``.
    * **header_row_identifier** - If you wish Streamly to locate the header - either for the purpose of excluding junk data before the header row, or excluding the header row entirely (in the first, or subsequent streams) - this value must not be ``None``. By default, it will be an empty byte string (or empty string if ``binary=False``) which tells Streamly that the header row is the first thing encountered in each stream. It will therefore be removed from all subsequent streams. If the header row does not start immediately in the stream, you can pass a value that can be used to identify where the header row starts. For example, if ``header_row_identifier=b"Fields:\n"`` and the stream starts with ``b"foo\nbar\baz\Fields:\ncol1,col2,col3..."``, Streamly will know that the header row starts with ``"col1"``.
    * **header_row_end_identifier** - If ``header_row_identifier=None``, this parameter is ignored. Otherwise, it is used to understand where the header row ends, and therefore, where the data of interest starts.

    .. warning::

        If the ``header_row_end_identifer`` value is not found, .read() will return no data for the stream in question. See the :ref:`note <reading_writing_text>` below for a common pitfall.

    * **footer_identifier** - Similarly to the ``header_row_identifier``, this parameter is used to locate the footer, in order to remove it. It defaults to ``None`` which assumes there is no footer to remove.
    * **retain_first_header_row** - As described in the ``header_row_identifier`` description above, if the header row can be located, it will be excluded from .read() operations on subsequent streams. By default, the header is included when the first stream is read. If it should be excluded, set ``retain_first_header_row=False``.

.. _reading_writing_text:
.. note::

    With regards to reading and writing text using `open() <https://docs.python.org/3/library/functions.html#open>`_ (or similar interfaces), users should be aware of a common pitfall, unrelated to Streamly. Open's ``newline`` keyword argument defaults to None and the associated behaviour is as follows:

        * When reading, `valid EOL characters <https://docs.python.org/3/glossary.html#term-universal-newlines>`_ are translated into \n before they are returned to the caller. `Incidentally, this is the reason why Streamly's default :ref:`header_row_end_identifier <_keyword_args>` is a representation of ``"\n"``.
        * When writing, any ``"\n"`` characters are translated to the system default line separator, `os.linesep <https://docs.python.org/3/library/os.html#os.linesep>`_. `This doesn't affect Streamly but can lead to an unexpected discrepancy in file sizes`.

    If you wish to avoid this translation behaviour, you can pass ``newline=""`` to open().

2. Replace Occurrences of .read()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Very simply, wherever you were calling .read() on the raw stream, substitute the reference to the raw stream for the :ref:`streamly.Streamly <streamly>` object. For example, if you had the following code::

    >>> data = raw_stream.read(8192)
    >>> if data:
    ...     with open("output.csv") as fp:
    ...         while data:
    ...             fp.write(data)
    ...             data = raw_stream.read(8192)

You would replace that with something like the following. Note that the first two lines are additions and the changes are highlighted:

.. code-block:: python
    :emphasize-lines: 4, 9

    >>> import streamly
    >>> wrapped_stream = streamly.Streamly(raw_stream)

    >>> data = wrapped_stream.read(8192)
    >>> if data:
    ...     with open("output.csv") as fp:
    ...         while data:
    ...             fp.write(data)
    ...             data = raw_stream.read(8192)

.. _logging:

Logging
-------

Streamly implements logging via `Python's standard library logging module <https://docs.python.org/3/library/logging.html>`_ and follows `best practice for library logging configuration <https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library>`_. If you wish to access the library's logger, you can do so with::

    >>> import logging
    >>> logger = logging.getLogger("streamly")

In order to access the output messages, you will need to:

    #. Attach a `handler <https://docs.python.org/3/howto/logging.html#handlers>`_
    #. Set the `threshold <https://docs.python.org/3/library/logging.html#levels>`_ in which messages of `level` severity or above are sent on. You have two options here:

        * `Set the level on the handler object <https://docs.python.org/3/library/logging.html#logging.Handler.setLevel>`_
        * `Set the level on the logger object <https://docs.python.org/3/library/logging.html#logging.Logger.setLevel>`_

    >>> import logging
    >>> logger = logging.getLogger("streamly")
    >>> stream_handler = logging.StreamHandler()  # sys.stderr
    >>> logger.addHandler(stream_handler)
    >>> logger.setLevel(logging.INFO)  # logger level threshold

However, more often than not, you can just attach a handler to the root logger object and allow the messages to propogate up through the logger objects. Again, you must set the appropriate threshold for message handling, either on the handler object or the logger object. For example::

    >>> root_logger = logging.getLogger(__name__)
    >>> stream_handler = logging.StreamHandler()
    >>> stream_handler.setLevel(logging.INFO)  # handler level threshold
    >>> root_logger.addHandler(stream_handler)

.. note::

    Streamly uses INFO level messages for recording .read() progress and DEBUG level messages for internals. If you encounter an issue, it will be helpful to provide DEBUG logs.