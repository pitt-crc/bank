Install and Setup
=================

Prerequisites
-------------

You will need the following utilities installed

- Slurm: 17.11.7 is recommended, but most of the queries should work for
  older, and newer, versions.
- SMTP: A working SMTP server to send emails via `smtplib` in python.

Installing Source Code
----------------------

.. code-block:: bash

   git clone https://github.com/pitt-crc/bank
   pip install -r requirements.txt

Configuring Slurm
-----------------

In your Slurm configuration you will need to configure the following:

.. code-block::

   PriorityDecayHalfLife=0-00:00:00
   PriorityUsageResetPeriod=NONE


Slurm Accounts
^^^^^^^^^^^^^^

By default, when you create an account:

.. code-block:: bash

   sacctmgr add account barrymoo
   sacctmgr list account

      Account                Descr                  Org
   ---------- -------------------- --------------------
     barrymoo             barrymoo             barrymoo

The script pulls the description and turns it into an email address to notify
users. Removing the ``@<email.com>`` can be done but is not necessary. To do
this for existing accounts (if you are unsure):

.. code-block:: bash

   sacctmgr update account where account=barrymoo set description="<email>"

Slurm Associations
^^^^^^^^^^^^^^^^^^

If you have multiple Slurm clusters, this tool was designed to provide a single
bank account for all of them. Obviously, you can modify the script to enforce
them separately or use multiple versions. It is recommended to explicitly define
all available clusters (especially if you have some clusters for which there is
no banking enforcement),

.. code-block:: bash

   sacctmgr add account barrymoo description="<email>" cluster=<cluster/s>
