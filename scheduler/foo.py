import time
from storage_manager import StorageManager

while True:
    print("running")
    storage_mgr = StorageManager()
    storage_mgr.sync_to_db()
    time.sleep(100)
