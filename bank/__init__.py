import constants

if constants.Settings.db_path == constants.Settings.db_test_path:
    raise RuntimeError(
        'Path to testing and production databases are configured to be the same. '
        'Exiting to protect deployment database from accidental overwrite.'
    )
