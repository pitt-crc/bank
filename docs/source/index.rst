CRC Bank Utility
================

The `Slurm workload manager <https://slurm.schedmd.com/overview.html>`_
is a useful tool for managing the allocation of computational resources
between users. However, the association based limits used by Slurm may not
provide enough control for certain groups' needs. The **CRC Bank Utility**
is a wrapper around the Slurm command line tool that provides additional
functionality for managing user allocations. THis functionality includes:

 - Streamlined utilities for managing Slurm user accounts across multiple clusters
 - Fine grained control over resource allocations per Slurm account/cluster
 - Automatic and configurable user notifications based on their usage of cluster resources
 - Support for the prioritized allocation of resources to users who have donated hardware (`investments`)

How It Works
------------

Slurm `users` are grouped together into `accounts`. When a user submits
a job through Slurm, the number of cpu-seconds they use is added to the total
number of resources used by their group account. The total number of cpu-seconds
used by an account is referred to as the account's ``RawUsage``. Borrowing from
the official Slum documentation:

.. code-block:: text

   Raw Usage
     The number of cpu-seconds of all the jobs that charged the account by the user.
     This number will decay over time when PriorityDecayHalfLife is defined

The ``crc_bank`` application maintains a database for the number of cpu-seconds
that are allocated to each user. The application monitors the ``RawUsage`` of
each account and automatically notifies/locks user accounts if their total usage
exceeds a given threshold. These notifications are configurable and can be sent
based on:

 1. The percent usage of an account's allocation
 2. The number of days left until an account is scheduled to expire
 3. Whether an account has run out of service units

.. toctree::
   :hidden:

   Overview<self>
   install.rst
   command_line.rst

.. toctree::
   :hidden:
   :caption: Developer Notes

   dev_notes/database_migrations.rst

.. toctree::
   :hidden:
   :caption: API Reference

   api/cli.rst
   api/account_logic.rst
   api/orm.rst
   api/system/system.rst
   api/settings.rst
   api/exceptions.rst