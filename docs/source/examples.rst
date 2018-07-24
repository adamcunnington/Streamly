========
Examples
========

This page provides some examples to help familiarise the user with the use cases for Streamly.

Basic
-----

Here is the simple, contrived example from the `GitHub README <https://github.com/adamcunnington/Streamly/blob/master/README.rst>`_::

    import requests
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


HTTP Response
-------------

`Please note that this example requires` `requests <http://docs.python-requests.org/en/master/>`_.

As mentioned in :ref:`getting-started`, a common use case where Streamly can help is when dealing with an "unclean" HTTP response, i.e. a report returned by a digital marketing API. We'll use some test data from the `GitHub repository <https://github.com/adamcunnington/Streamly/tree/master/tests/data>`_ to demonstrate the use case here::

    import requests



Merging Files
-------------

Another example would be use Streamly to merge files.