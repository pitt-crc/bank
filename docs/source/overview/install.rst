Install and Setup
=================

System Prerequisites
--------------------

You will need the following utilities installed before using the application.
Links to further documentation are provided if you don't already have a
prerequisite application installed.

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Requirements
     - Further Reading
     - Description
   * - **Python**
     - `docs.conda.io <https://docs.conda.io/en/latest/miniconda.html>`_
     - Any version from 3.5 onward should work. Older versions of Python
       (e.g., 2.7) are explicitly not supported. We recommend miniconda.
   * - **Slurm**
     - `slurm.schedmd.com <https://slurm.schedmd.com/overview.html>`_
     - Version 17.11.7 is recommended, but most of the queries should work for
       older, and newer, versions.
   * - **SMTP**
     -
     - A working SMTP server to send emails via ``smtplib`` in python.

The ``git`` and ``pip`` command line utilities are not technically required, but
make life easier when installing the application source code / dependencies.

Installing The Application
--------------------------

Application source code is available on
`GitHub.com <https://github.com/pitt-crc/bank>`_
and can be downloaded using ``git``:

.. code-block:: bash

   git clone https://github.com/pitt-crc/bank bank_source

Once you have the source code downloaded, install the necessary python
requirements:

.. code-block:: bash

   pip install -r bank_source/requirements.txt

Configuring Slurm
-----------------

In your Slurm configuration, you will need to configure the following values:

.. code-block::

   PriorityDecayHalfLife=0-00:00:00
   PriorityUsageResetPeriod=NONE

If your curious what this does, here is a snippet from the Slurm documentation:

.. code-block:: text

   PriorityDecayHalfLife
       This controls how long prior resource use is considered in determining how
       over- or under-serviced an association is (user, bank account and cluster) in
       determining job priority. The record of usage will be decayed over time, with
       half of the original value cleared at age PriorityDecayHalfLife. If set to 0 no
       decay will be applied. This is helpful if you want to enforce hard time limits
       per association. If set to 0 PriorityUsageResetPeriod must be set to some
       interval.

.. important::
   If you don't properly configure the above values, ``slurm`` will compete
   with the ``crc_bank`` utility for control over the ``RawUsage`` value of each
   account. This can lead to unpredictable behavior by both tools.

Configuring The Application
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``crc_bank`` application was built at the University of Pittsburgh and
comes configured out of the box to run on Pitt servers. You will need to
configure the application settings to work on your system.

Application settings can be modified by setting variables in the working
environment. For a full list of application settings, see the table of
available settings in the :ref:`API documentation <settings>`.

Testing Your Installation
^^^^^^^^^^^^^^^^^^^^^^^^^

You may wish to run the application test suite to make sure everything is
working properly.

.. code-block:: bash

   cd bank_source
   python -m unittest discover tests
