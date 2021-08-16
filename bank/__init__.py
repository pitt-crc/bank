from . import settings

if settings.app_settings.db_path == settings.app_settings.db_test_path:
    raise RuntimeError(
        'Path to testing and production databases are configured to be the same. '
        'Exiting to protect deployment database from accidental overwrite.'
    )
