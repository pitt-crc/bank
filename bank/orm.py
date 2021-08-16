import dataset

from settings import app_settings

db = dataset.connect(f'sqlite:///{app_settings.db_test_path if app_settings.is_testing else app_settings.db_path}')
proposal_table = db["proposal"]
investor_table = db["investor"]
investor_archive_table = db["investor_archive"]
proposal_archive_table = db["proposal_archive"]
