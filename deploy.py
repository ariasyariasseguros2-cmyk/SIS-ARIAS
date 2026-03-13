import zipfile
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def zip_files(zip_name, items_to_zip):
    # Remove existing zip if it exists
    if os.path.exists(zip_name):
        try:
            os.remove(zip_name)
            print(f"Removed existing {zip_name}")
        except OSError as e:
            print(f"Error removing {zip_name}: {e}")
            return

    print(f"Compressing files to {zip_name}...")
    
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            added_dirs = set()

            def add_dir(arc_dir):
                arc_dir = arc_dir.replace(os.path.sep, '/').strip('/').rstrip('/') + '/'
                if arc_dir in added_dirs:
                    return
                zi = zipfile.ZipInfo(arc_dir)
                zi.external_attr = 0o40775 << 16
                zipf.writestr(zi, '')
                added_dirs.add(arc_dir)

            for item in items_to_zip:
                item_path = os.path.join(BASE_DIR, item)
                if not os.path.exists(item_path):
                    print(f"Warning: Item not found: {item}")
                    continue

                if os.path.isfile(item_path):
                    print(f"  Adding file: {item}")
                    # Ensure arcname uses forward slashes
                    rel_path = os.path.relpath(item_path, BASE_DIR)
                    arcname = rel_path.replace(os.path.sep, '/')
                    zipf.write(item_path, arcname=arcname)
                elif os.path.isdir(item_path):
                    print(f"  Adding folder: {item}")
                    for root, dirs, files in os.walk(item_path):
                        # Exclude __pycache__ directories
                        if '__pycache__' in dirs:
                            dirs.remove('__pycache__')

                        rel_root = os.path.relpath(root, BASE_DIR)
                        add_dir(rel_root)
                        for d in dirs:
                            rel_dir = os.path.relpath(os.path.join(root, d), BASE_DIR)
                            add_dir(rel_dir)
                        
                        for file in files:
                            # Exclude .pyc files and .DS_Store
                            if file.endswith('.pyc') or file == '.DS_Store':
                                continue
                            
                            file_path = os.path.join(root, file)
                            # Create archive name relative to current directory
                            rel_path = os.path.relpath(file_path, BASE_DIR)
                            # Force forward slashes for cross-platform compatibility
                            arcname = rel_path.replace(os.path.sep, '/')
                            zipf.write(file_path, arcname=arcname)
        
        print(f"Done! File created: {zip_name}")
        if os.path.exists(zip_name):
            print(f"File size: {os.path.getsize(zip_name)} bytes")
        else:
            print("Error: File was not created!")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    zip_file = "deploy.zip"
    items_to_zip = [
        "app.py",
        "passenger_wsgi.py",
        "requirements.txt",
        "appsettings.json",
        "controllers",
        "db",
        "models",
        "routes",
        "static",
        "templates",
        "uploads",
        "utils",
        ".htaccess"
    ]
    
    zip_files(zip_file, items_to_zip)
