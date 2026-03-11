import sys
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Set the environment variable for Flask to run in production
os.environ['FLASK_ENV'] = 'production'

try:
    from app import app as application
except Exception as e:
    # Log the full traceback to a file we can read
    import traceback
    with open(os.path.join(base_dir, 'error_log_startup.txt'), 'w', encoding='utf-8') as f:
        f.write("Failed to import application:\n")
        f.write(traceback.format_exc())
    
    # Still raise it so Passenger knows it failed
    raise e
