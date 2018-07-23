[1mdiff --git a/README.rst b/README.rst[m
[1mindex 31867e1..d1ddebd 100644[m
[1m--- a/README.rst[m
[1m+++ b/README.rst[m
[36m@@ -1,3 +1,94 @@[m
 ========[m
 Streamly[m
[31m-========[m
\ No newline at end of file[m
[32m+[m[32m========[m
[32m+[m
[32m+[m[32mStreamly is a very simple yet powerful wrapper for streams (file-like objects). It is primarily designed to help with the cleaning up of flat data during on the fly read operations.[m
[32m+[m
[32m+[m[32mA typical use case that is especially prevalent with digital marketing data sources, is wanting to download/upload a web stream to some target location that expects clean, flat delimited data but the stream includes unwanted header and footer data. Developers often deal with this by loading the data as-is into an interim location and then opening the file and culling the unwanted leading and trailing lines. This approach works but limitations include: not easily reproducible; increases the complexity of the solution; assumes a storage component; inefficient with large data sets.[m
[32m+[m
[32m+[m[32mStreamly solves this problem by handling the unwanted headers and footers on the fly in a highly efficient manner.[m
[32m+[m
[32m+[m[32mDocumentation: https://streamly.readthedocs.io[m
[32m+[m
[32m+[m
[32m+[m[32mInstallation[m
[32m+[m[32m------------[m
[32m+[m
[32m+[m[32m**Requires Python 3.1+**[m
[32m+[m
[32m+[m[32mUsing `pipenv <https://packaging.python.org/tutorials/managing-dependencies/#installing-pipenv>`[m
[32m+[m[32m^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[m
[32m+[m
[32m+[m[32mInstall:[m
[32m+[m[32m.. code-block:: text[m
[32m+[m
[32m+[m[32m    pipenv install streamly --upgrade[m
[32m+[m
[32m+[m[32m**Or** Update:[m
[32m+[m
[32m+[m[32m..code-block::text[m
[32m+[m
[32m+[m[32m    pipenv update streamly[m
[32m+[m
[32m+[m[32mUsing `pip <https://pip.pypa.io/en/stable/quickstart/>`[m
[32m+[m[32m^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^[m
[32m+[m
[32m+[m[32mInstall & Update:[m
[32m+[m
[32m+[m[32m..code-block::text[m
[32m+[m
[32m+[m[32m    pip install streamly --upgrade[m
[32m+[m
[32m+[m
[32m+[m[32mExample Usage[m
[32m+[m[32m-----[m
[32m+[m
[32m+[m[32mThe below example writes a byte stream to a file, removing the unwanted header and footer details on the fly.[m
[32m+[m
[32m+[m[32m..code-block:: python[m
[32m+[m
[32m+[m[32m    import io[m
[32m+[m
[32m+[m[32m    import streamly[m
[32m+[m
[32m+[m
[32m+[m[32m    my_stream = io.BytesIO([m
[32m+[m[32m    b"""Header[m
[32m+[m[32m    Metadata[m
[32m+[m[32m    Unwanted[m
[32m+[m[32m    =[m
[32m+[m[32m    Garabage[m
[32m+[m
[32m+[m[32m    Report Fields:[m
[32m+[m[32m    col1,col2,col3,col4,col5[m
[32m+[m[32m    data,that,we,actually,want[m
[32m+[m[32m    and,potentially,loads,of,it,[m
[32m+[m[32m    foo,bar,baz,lorem,ipsum[m
[32m+[m[32m    foo,bar,baz,lorem,ipsum[m
[32m+[m[32m    foo,bar,baz,lorem,ipsum[m
[32m+[m[32m    ...,...,...,...,...[m
[32m+[m[32m    Grand Total:,0,0,1000,0[m
[32m+[m[32m    More[m
[32m+[m[32m    Footer[m
[32m+[m[32m    Garbage[m
[32m+[m[32m    """[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    wrapped_stream = streamly.Streamly(my_stream, header_row_identifier=b"Report Fields:\n", footer_identifier=b"Grand")[m
[32m+[m
[32m+[m[32m    with open("output.csv", "wb") as fp:[m
[32m+[m[32m        data = wrapped_stream.read()[m
[32m+[m[32m        while data:[m
[32m+[m[32m            fp.write(data)[m
[32m+[m[32m            data = wrapped_stream.read()[m
[32m+[m
[32m+[m
[32m+[m[32mFeatures[m
[32m+[m[32m--------[m
[32m+[m
[32m+[m[32mIncludes the following functionality during on the fly read operations:[m
[32m+[m[32m- Adjoining of multiple streams[m
[32m+[m[32m- Removal of header and footer data, identified by a value (e.g. byte string or string)[m
[32m+[m[32m- Logging of read progress[m
[32m+[m[32m- Guaranteed read size (where the data is not yet exhausted)[m
[32m+[m[32m- Consistent API for streams returning byte strings or strings[m
