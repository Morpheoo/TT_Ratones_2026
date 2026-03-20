
import sys
import os
import traceback

# Root path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root)

try:
    print(f"PYTHONPATH: {sys.path[0]}")
    import src.security_logger as sl
    print("Import src.security_logger success")
    print(f"Dir sl: {dir(sl)}")
    
    # Check if we can access the functions
    print(f"log_security_event: {sl.log_security_event}")
    print(f"_log_to_db: {sl._log_to_db}")
    
except Exception:
    traceback.print_exc()
