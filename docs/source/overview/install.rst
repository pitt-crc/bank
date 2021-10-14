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


Applications Settings
^^^^^^^^^^^^^^^^^^^^^

Application settings can be modified by setting variables in the working environment.
The table below lists the available settings and their default value.
Default file paths are typically relative to the installation directory of the application (``[INSTALLDIR]``).

.. list-table::
   :header-rows: 1

   * - Environmental Variable
     - Default Value
     - Description

   * - BANK_DATE_FORMAT
     - ``%m/%d/%y``
     - Format used by the commandline parser when specifying dates as strings.

   * - BANK_LOG_PATH
     - ``[INSTALLDIR]/crc_bank.log``
     - The location of the application log file.

   * - BANK_LOG_FORMAT
     - ``[%(levelname)s] %(asctime)s - %(name)s - %(message)s``
     - The format for content written to the log file.

   * - BANK_LOG_LEVEL
     - ``INFO``
     - The minimum severity level required for an entry to be written to the log.

   * - BANK_DB_PATH
     - ``sqlite:///[INSTALLDIR]/crc_bank.db``
     - Path to the backend application database.

   * - BANK_CLUSTERS
     - ``smp,mpi,gpu,htc``
     - A list of slurm clusters being administrated by the application.

   * - BANK_EMAIL_SUFFIX
     - ``@pitt.edu``
     - The email suffix to use when sending alerts to user accounts.


   * - BANK_NOTIFY_LEVELS
     - ``25,50,75,90``
     - Notify account holders via email when their proposal reaches any of the listed thresholds.


   * - BANK_NOTIFY_SUS_LIMIT_EMAIL_TEXT
     -
     - Email message used to notify account holders about service unit usage and limits.

   * - BANK_THREE_MONTH_PROPOSAL_EXPIRY_NOTIFICATION_EMAIL
     -
     - Email message to send when an account is 90 days from the end of its proposal.


   * - BANK_PROPOSAL_EXPIRES_NOTIFICATION_EMAIL
     -
     - An email to send when an account's proposal has expired.

