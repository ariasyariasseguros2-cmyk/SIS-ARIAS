import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from models.db import get_connection
except ImportError:
    print("Could not import get_connection from models.db")
    exit(1)

def fix_juanito():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        print("Updating juanito to BROKER (id_rol=1)...")
        cur.execute("UPDATE usuarios SET id_rol = 1 WHERE username = 'juanito'")
        conn.commit()
        print(f"Rows affected: {cur.rowcount}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_juanito()
