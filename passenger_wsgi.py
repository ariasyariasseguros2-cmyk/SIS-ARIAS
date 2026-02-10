import sys
import os

# Ensure the current directory is in sys.path so we can import app.py
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

# Set the environment variable for Flask to run in production
os.environ['FLASK_ENV'] = 'production'

try:
    from app import app as application
except Exception as e:
    # Log the full traceback to a file we can read
    import traceback
    with open('error_log_startup.txt', 'w') as f:
        f.write("Failed to import application:\n")
        f.write(traceback.format_exc())
    
    # Still raise it so Passenger knows it failed
    raise e
