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

    wrapped_stream = streamly.Streamly(my_stream,
        header_row_identifier=b"Report Fields:\n",
        footer_identifier=b"Grand")

    data = wrapped_stream.read(50)
    while data:
        print(data)
        data = wrapped_stream.read(50)


HTTP Response
-------------

`Please note that this example requires` `requests <http://docs.python-requests.org/en/master/>`_.

As mentioned in :ref:`getting_started`, a common use case where Streamly can help is when dealing with an "unclean" HTTP response, i.e. a report returned by a digital marketing API. We'll use some test data from the `GitHub repository <https://github.com/adamcunnington/Streamly/tree/master/tests/data>`_ to demonstrate the use case here. Ensure you configure the ``output_file_path`` variable below::

    import gzip

    import requests
    import streamly


    # change this to the location you want to write to
    output_file_path = "output.txt"

    url = ("https://raw.githubusercontent.com/adamcunnington/"
           "Streamly/master/tests/data/test_data_1.txt")
    raw_stream = requests.get(url, stream=True).raw
    # raw.githubusercontent.com returns gzip encoded content
    decompressor = gzip.GzipFile(fileobj=raw_stream)
    wrapped_stream = streamly.Streamly(decompressor,
        header_row_identifier=b"Fields:\n", footer_identifier=b"Grand")

    data = wrapped_stream.read()
    if data:
        with open(output_file_path) as fp:
            while data:
                fp.write(data)
                data = wrapped_stream.read()

Navigate to ``output_file_path`` to see the output data.


Merging Files
-------------

Another example would be use Streamly to merge files. For the purposes of demonstration, start by manually downloading the following files to the same directory of your choice:

    * `test_data_1 <https://github.com/adamcunnington/Streamly/blob/master/tests/data/test_data_1.txt>`_
    * `test_data_1 - page 2 <https://github.com/adamcunnington/Streamly/blob/master/tests/data/test_data_1%20-%20page%202.txt>`_

Then configure the ``files_dir_path`` variable below::

    import os

    import streamly


    files_dir_path = "/home/<username>/Downloads/"

    part_1 = os.path.join(files_dir_path, "test_data_1.txt")
    part_2 = os.path.join(files_dir_path, "test_data_1 - page 2.txt")

    kwargs = {"encoding": "utf8", "newline": ""}

    with open(part_1, **kwargs) as fp1:
        with open(part_2, **kwargs) as fp2:
            wrapped_streams = streamly.Streamly(fp1, fp2, binary=False,
                header_row_identifier="Fields:\n", footer_identifier="Grand")
            # Large read size as we're just reading from disk
            data = wrapped_streams.read(100000)
            if data:
                with open(os.path.join(files_dir_path, "output.txt"),
                          "f", **kwargs) as fp_out:
                    while data:
                        fp_out.write(data)
                        data = wrapped_streams.read(100000)

Navigate to the output.txt file @ ``files_dir_path`` to see the output data.