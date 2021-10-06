CRC Bank Utility
================

A Banking and Proposal System For Slurm

Why?
----

The Slurm association based limits may not provide enough power for certain groups'
needs.  Other banking systems tended to be outdated – their last commits being at least a
year old. This code is written in hopes that it will prove valuable to the community.
However, this model may not work for everyone.

How?
----

Using the existing associations in your Slurm database, the "RawUsage" value
reported from `sshare` is utilized to monitor service units (CPU hours) on the cluster.

From the documentation:

.. code-block:: text

   Raw Usage
   The number of cpu-seconds of all the jobs that charged the account by the user.
   This number will decay over time when PriorityDecayHalfLife is defined

   PriorityDecayHalfLife
   This controls how long prior resource use is considered in determining how
   over- or under-serviced an association is (user, bank account and cluster) in
   determining job priority. The record of usage will be decayed over time, with
   half of the original value cleared at age PriorityDecayHalfLife. If set to 0 no
   decay will be applied. This is helpful if you want to enforce hard time limits
   per association. If set to 0 PriorityUsageResetPeriod must be set to some
   interval.

The ``crc_bank`` application takes care of resetting "RawUsage" for you.
The bank enforces two limits:

1. A service unit limit: How many compute hours is an account allowed to use?
2. A data limit: How long does the proposal last?

Charging
^^^^^^^^

Our group uses a MAX(CPU, Memory, GPU) charging scheme (``PriorityFlags=MAX_TRES``).
For each cluster, ``DefMemPerCPU=<RAM in Mb> / <cores per node>`` (choosing lowest value on each cluster) is defined.

Then:
 - CPU Only Node: ``TresBillingWeights="CPU=1.0,Mem=<value>G"`` where ``<value> = 1 / (DefMemPerCPU / 1024)``
 - GPU Node: ``TresBillingWeights="CPU=0.0,Mem=0.0G,GRES/gpu=1.0"``

Here, ``CPU=1.0`` means 1 service unit per hour to use 1 core and ``GRES/gpu=1.0``
means 1 service unit per hour to use 1 GPU card. ``Mem=<value>G`` is defined such
that for one hour using the default RAM users are charged 1 service unit.

Checking and Notifications
--------------------------

You will probably want to check the limits once a day. The checks which are completed:

1. Have you overdrawn your limit? If yes, email account manager, put hold on
   account

  - Is the account above 25% of their limit? If yes, email account manager
  - Is the account above 50% of their limit? If yes, email account manager
  - Is the account above 75% of their limit? If yes, email account manager
  - Is the account above 90% of their limit? If yes, email account manager

2. Has your proposal ended? If yes, email account manager

  - Is the account 3 months away from reaching this limit? If yes, email account manager


.. toctree::
   :hidden:
   :maxdepth: 0
   :titlesonly:

   Overview<self>
   overview/install.rst
   overview/command_line.rst


.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: API Reference
   :titlesonly:

   api/cli.rst
   api/dao.rst
   api/orm/orm.rst
   api/settings.rst
   api/system.rst
   api/exceptions.rst