Database Migrations
===================

Project maintainers may find themselves changing the application's database schema when adding new features / patches.
Migrations to the database schema are managed using the `alembic <https://alembic.sqlalchemy.org/en/latest/>`_ command line tool.
**Reading through the alembic documentation is highly recommended**.
However, a quick reference is provided here for project developers.

Creating a New Migration
------------------------

Start by changing into the migrations directory and generating a new migration.
``alembic`` will automatically generate the “obvious” migrations by comparing
the existing database against the schema used by the banking application.

.. code-block:: bash

   cd migrations
   alembic revision --autogenerate -m "A description of applied changes"

Once the new migration has been created, open the generated file and
make any necessary modifications to the automatically generated code.

.. important:: You should never blindly trust an automatically generated
   database migration. **Always** check the generated python file and verify
   the migration steps.

Once you have created the migration, you can apply it by running

.. code-block:: bash

   alembic upgrade head
