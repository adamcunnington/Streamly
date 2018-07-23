Welcome to Streamly
===================

Streamly is a very simple yet powerful wrapper for streams (file-like objects). It is primarily designed to help with the cleaning up of flat data during on the fly read operations.


Features
--------
Includes the following functionality during on the fly read operations:

* Adjoining of multiple streams
* Removal of header and footer data, identified by a value (e.g. byte string or string)
* Logging of read progress
* Guaranteed read size (where the data is not yet exhausted)
* Consistent API for streams returning byte strings or strings


Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   installation
   getting-started
   read-logic

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api