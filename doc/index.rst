+++++++++++
Python perf
+++++++++++

The Python ``perf`` module is a toolkit to write and run benchmarks.

Features:

* Store results as JSON to be able to reload and process results later
* Run benchmarks in multiple processes, compute the average and the standard
  deviation to get reliable and realistic benchmark result

Links:

* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `perf documentation
  <https://perf.readthedocs.io/>`_ (this documentation)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_
* License: MIT

perf supports Python 2.7 and Python 3. Install perf on Python 3::

    python3 -m pip install perf

The ``-m perf hist --scipy`` command requires numpy, scipy and pylab. Command
to install these packages on Fedora::

    sudo dnf install -y python3-{numpy,scipy,matplotlib}

.. toctree::
   :maxdepth: 3

   perf
   cli
   api
   changelog
