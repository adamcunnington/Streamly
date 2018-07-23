========
Streamly
========

Streamly is a very simple yet powerful wrapper for streams (file-like objects). It is primarily designed to help with the cleaning up of flat data during on the fly read operations.

A typical use case that is especially prevalent within digital marketing, is wanting to download/upload a web stream to some target location that expects clean, flat delimited data but the stream includes unwanted header and footer data. Developers often deal with this by loading the data as-is into an interim location and then opening the file and culling the unwanted leading and trailing lines. This approach works but limitations include: not easily reproducible; increases the complexity of the solution; assumes a storage component; inefficient with large data sets.

Streamly solves this problem by handling the unwanted headers and footers on the fly in a highly efficient manner.

Documentation: https://streamly.readthedocs.io


Installation
------------

**Requires** `Python 3.1+ <https://www.python.org/downloads/>`_

Using `pipenv <https://packaging.python.org/tutorials/managing-dependencies/#installing-pipenv>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install:

.. code-block:: text

    pipenv install streamly --upgrade

**OR** Update:

.. code-block:: text

    pipenv update streamly

Using `pip <https://pip.pypa.io/en/stable/quickstart/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install & Update:

.. code-block:: text

    pip install streamly --upgrade


Example Usage
-----

The below example writes a byte stream to a file, removing the unwanted header and footer details on the fly.

.. code-block:: python

    import io

    import streamly


    my_stream = io.BytesIO(
    b"""Header
    Metadata
    Unwanted
    =
    Garabage

    Report Fields:
    col1,col2,col3,col4,col5
    data,that,we,actually,want
    and,potentially,loads,of,it,
    foo,bar,baz,lorem,ipsum
    foo,bar,baz,lorem,ipsum
    foo,bar,baz,lorem,ipsum
    ...,...,...,...,...
    Grand Total:,0,0,1000,0
    More
    Footer
    Garbage
    """
    )

    wrapped_stream = streamly.Streamly(my_stream, header_row_identifier=b"Report Fields:\n",
                                       footer_identifier=b"Grand")

    with open("output.csv", "wb") as fp:
        data = wrapped_stream.read()
        while data:
            fp.write(data)
            data = wrapped_stream.read()


Features
--------

Includes the following functionality during on the fly read operations:

* Adjoining of multiple streams
* Removal of header and footer data, identified by a value (e.g. byte string or string)
* Logging of read progress
* Guaranteed read size (where the data is not yet exhausted)
* Consistent API for streams returning byte strings or strings
