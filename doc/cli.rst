perf commands
=============

General note: if a filename is ``-``, read the JSON content from stdin.

show
----

Show a benchmark result::

    python3 -m perf show
        [-v/--verbose] [-m/--metadata]
        |--hist] [--stats]
        filename.json

Example with metadata::

    $ python3 -m perf show --metadata run.json
    Metadata:
    - duration: 59.1 sec
    - loops: 10^7
    - timeit_setup: 'pass'
    - timeit_stmt: 'len("abc")'

    Average: 56.3 ns +- 2.5 ns

Example in verbose mode::

    $ python3 -m perf show -v run.json
    Average: 56.3 ns +- 2.5 ns (25 runs x 3 samples; 1 warmup)

Example in very verbose mode::

    $ python3 -m perf show -vv run.json
    Run 1/25: warmup (1): 555 ms; raw samples (3): 546 ms, 630 ms, 553 ms
    Run 2/25: warmup (1): 572 ms; raw samples (3): 546 ms, 546 ms, 547 ms
    (...)
    Run 25/25: warmup (1): 602 ms; raw samples (3): 649 ms, 642 ms, 607 ms

    Standard deviation: 4%
    Shortest raw sample: 545 ms

    Average: 56.3 ns +- 2.5 ns (min: 54.5 ns, max: 64.9 ns) (25 runs x 3 samples; 1 warmup)


compare and compare_to
----------------------

Compare benchmark results::

    python3 -m perf
        [-v/--verbose] [-m/--metadata]
        compare reference.json filename.json filename2.json [filename3.json ...]

Compare benchmark results to a reference::

    python3 -m perf
        [-v/--verbose] [-m/--metadata]
        compare_to reference.json changed.json [changed2.json ...]

Example::

    $ python3 -m perf compare py2.json py3.json
    Reference (best): py2

    Average: [py2] 46.3 ns +- 2.2 ns -> [py3] 56.3 ns +- 2.5 ns: 1.2x slower
    Significant (t=-25.90)


stats
-----

Compute statistics on a benchmark result::

    python3 -m perf stats filename.json

Example::

    $ python3 -m perf stats telco.json
    Number of samples: 250

    Minimum: 26.4 ms (-1.8%)
    Median +- std dev: 26.9 ms +- 0.2 ms (26.7 ms .. 27.0 ms)
    Maximum: 27.3 ms (+1.7%)

Values:

* `Median <https://en.wikipedia.org/wiki/Median>`_
* "std dev": `Standard deviation (standard error)
  <https://en.wikipedia.org/wiki/Standard_error>`_


.. _hist_cmd:

hist
----

Render an histogram in text mode::

    python3 -m perf hist
        [-n BINS/--bins=BINS] [--extend]
        filename.json [filename2.json ...]

* ``--bins`` is the number of histogram bars. By default, it renders up to 25
  bars, or less depending on the terminal size.
* ``--extend``: don't limit to 80 colums x 25 lines but fill the whole
  terminal if it is wider.

If multiple files are used, the histogram is normalized on the minimum and
maximum of all files to be able to easily compare them.

Example::

    $ python3 -m perf hist telco.json
    26.4 ms:  1 ##
    26.4 ms:  1 ##
    26.4 ms:  2 #####
    26.5 ms:  1 ##
    26.5 ms:  1 ##
    26.5 ms:  4 #########
    26.6 ms:  8 ###################
    26.6 ms:  6 ##############
    26.7 ms: 11 ##########################
    26.7 ms: 13 ##############################
    26.7 ms: 18 ##########################################
    26.8 ms: 21 #################################################
    26.8 ms: 34 ###############################################################################
    26.8 ms: 26 ############################################################
    26.9 ms: 11 ##########################
    26.9 ms: 14 #################################
    27.0 ms: 17 ########################################
    27.0 ms: 14 #################################
    27.0 ms: 10 #######################
    27.1 ms: 10 #######################
    27.1 ms:  7 ################
    27.1 ms: 12 ############################
    27.2 ms:  5 ############
    27.2 ms:  2 #####
    27.3 ms:  0 |
    27.3 ms:  1 ##

See `Gaussian function <https://en.wikipedia.org/wiki/Gaussian_function>`_ and
`Probability density function (PDF)
<https://en.wikipedia.org/wiki/Probability_density_function>`_.


.. _hist_scipy_cmd:

hist_scipy
----------

Render an histogram in graphical mode using the ``scipy`` module::

    python3 -m perf hist_scipy [-n BINS/--bins=BINS] filename.json

* ``--bins`` is the number of histogram bars (default: 25)

This command requires the ``scipy`` dependency: see :ref:`Install perf
<install>`.

Example::

    $ python3 -m perf hist_scipy telco.json

Output:

.. image:: hist_scipy_telco.png


metadata
--------

Collect metadata::

    python3 -m perf metadata

Example::

    $ python3 -m perf metadata
    Metadata:
    - aslr: enabled
    - cpu_count: 4
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - date: 2016-06-15T22:08:21
    - hostname: selma
    - perf_version: 0.4
    - platform: Linux-4.4.8-300.fc23.x86_64-x86_64-with-fedora-23-Twenty_Three
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.4.3
