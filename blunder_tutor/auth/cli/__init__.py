"""Library admin surface — async functions for the operator workflows
that ship with the auth library (list users, reset password, revoke
sessions, delete user, regenerate first-user invite).

Consumers reach this module through the top-level package:

.. code-block:: python

    from blunder_tutor.auth import admin
    await admin.list_users(service)
    await admin.reset_password(service, username, "new-password")

The ``admin`` submodule is bound on the top-level package object via
``blunder_tutor.auth.__init__``, so deep imports
(``from blunder_tutor.auth.cli import admin``) are not required and
not part of the public contract.
"""

