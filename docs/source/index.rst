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

Using the existing associations in your Slurm database, "RawUsage"
from `sshare` is utilized to monitor service units (CPU hours) on the cluster. From the documentation:

``` text
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
```

Therefore, in your Slurm configuration you will need:

``` text
PriorityDecayHalfLife=0-00:00:00
PriorityUsageResetPeriod=NONE
```

The `crc-bank.py` takes care of resetting "RawUsage" for you. The bank enforces
two limits:

1. A service unit limit: How many compute hours is an account allowed
   to use?
2. A data limit: How long does the proposal last?

Our department allows for single year proposals and a default of 10,000
service units.

Prerequisites
-------------

- Python 3, specific packages:
    - [dataset](https://dataset.readthedocs.io/en/latest/): "databases for lazy
      people"
    - [docopt](http://docopt.org): "command line arguments parser, that will
      make you smile"
- Slurm: 17.11.7 is recommended, but most of the queries should work for
  older, and newer, versions.
- SMTP: A working SMTP server to send emails via `smtplib` in python.

Slurm Setup
-----------

Accounts
^^^^^^^^

By default, when you create an account:

``` bash
sacctmgr add account barrymoo
sacctmgr list account
   Account                Descr                  Org
---------- -------------------- --------------------
  barrymoo             barrymoo             barrymoo
```

The script pulls the description and turns it into an email address to notify
users. Removing the `@<email.com>` can be done but is not necessary. To do
this for existing accounts (if you are unsure):

``` bash
sacctmgr update account where account=barrymoo set description="<email>"
```

Associations
^^^^^^^^^^^^

If you have multiple Slurm clusters, this tool was designed to provide a single
bank account for all of them. Obviously, you can modify the script to enforce
them separately or use multiple versions. It is recommended to explicitly define
all available clusters (especially if you have some clusters for which there is
no banking enforcement),


``` bash
sacctmgr add account barrymoo description="<email>" cluster=<cluster/s>
```

Charging
^^^^^^^^

Our group uses a MAX(CPU, Memory, GPU) charging scheme (`PriorityFlags=MAX_TRES`). For each
cluster, `DefMemPerCPU=<RAM in Mb> / <cores per node>` (choosing lowest
value on each cluster) is defined. Then:
- CPU Only Node: `TresBillingWeights="CPU=1.0,Mem=<value>G"` where `<value> = 1
  / (DefMemPerCPU / 1024)`
- GPU Node: `TresBillingWeights="CPU=0.0,Mem=0.0G,GRES/gpu=1.0"`
Here, `CPU=1.0` means 1 service unit per hour to use 1 core and `GRES/gpu=1.0`
means 1 service unit per hour to use 1 GPU card. `Mem=<value>G` is defined such
that for one hour using the default RAM users are charged 1 service unit.

Necessary Modifications
-----------------------

Review the `constants.py` and make the appropriate changes

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
    - Is the account 3 months away from reaching this limit? If yes, email
      account manager


.. toctree::
   :hidden:
   :maxdepth: 0
   :titlesonly:

   Overview<self>
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
   api/exceptions.rst