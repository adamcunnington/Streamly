.. _installation:

============
Installation
============

If you've done this kind of thing before, suffice to say that Streamly has been published to `PyPI <https://pypi.org/project/streamly>`_ and so it is installable under the name, **streamly**.

Requirements
------------

Streamly requires `Python 3.1 <https://www.python.org/downloads/>`_ or newer, and requires no dependencies.


Installation
------------

It goes without saying that you should not install directly into your system-wide python installation, but instead into a project-specific `virtual environment <https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments>`_.

It is highly recommended that you :ref:`use pipenv <with_pipenv>` as it consolidates the installation of your application's dependencies and virtual environment management into one simple tool.

Otherwise, :ref:`use pip and venv separately <with_pip_and_venv>`.

.. _with_pipenv:

With `pipenv <https://packaging.python.org/tutorials/managing-dependencies/>`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section assumes that pipenv is installed. If not, `install it <https://docs.pipenv.org/install/#installing-pipenv>`_ first.

Create and/or Activate Virtual Environment & Install:

.. code-block:: text

    pipenv install streamly

**OR** Activate Virtual Environment & Update:

.. code-block:: text

    pipenv update streamly

.. _with_pip_and_venv:

With `pip <https://packaging.python.org/guides/installing-using-pip-and-virtualenv/#installing-pip>`_ and `venv <https://docs.python.org/3/library/venv.html>`_ separately
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section assumes that you have created and/or activated your virtual environment manually. If not, `install/create/activate <https://packaging.python.org/guides/installing-using-pip-and-virtualenv/#installing-virtualenv>`_ first.

Install Or Update:

.. code-block:: text

    pip install streamly --upgrade
