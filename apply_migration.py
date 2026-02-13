import os
import sys

# Add project root to sys.path to import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.db import get_connection

def run_migration(file_path):
    print(f"Reading migration file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple parser for SQL with delimiters
    statements = []
    delimiter = ';'
    current_statement = []
    
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('DELIMITER'):
            delimiter = stripped.split()[1]
            continue
            
        if not stripped or stripped.startswith('--'):
            # Keep comments inside procedures but ignore empty lines or pure comment lines outside if needed
            # For simplicity, we just add line to current statement
            pass
            
        current_statement.append(line)
        
        # Check if line ends with delimiter
        # Note: stripped might be "END$$"
        if stripped.endswith(delimiter):
            # Remove delimiter from the end of the statement string for execution
            stmt_str = '\n'.join(current_statement)
            
            # Find the last occurrence of delimiter and remove it
            # Be careful: delimiter might be "$$" or ";"
            # We need to strip the delimiter from the actual SQL sent to MySQL
            
            # For $$
            if delimiter != ';':
                 if stmt_str.strip().endswith(delimiter):
                     stmt_str = stmt_str.strip()[: -len(delimiter)]
            else:
                 if stmt_str.strip().endswith(delimiter):
                     stmt_str = stmt_str.strip()[: -len(delimiter)]
            
            if stmt_str.strip():
                statements.append(stmt_str)
            current_statement = []

    print(f"Found {len(statements)} statements to execute.")
    
    cnx = get_connection()
    cursor = cnx.cursor()
    
    for i, sql in enumerate(statements):
        try:
            # print(f"Executing statement {i+1}...")
            # print(sql[:50] + "...")
            cursor.execute(sql)
            # Consumir resultados si los hay (para evitar "Unread result found")
            while cursor.nextset():
                pass
        except Exception as e:
            print(f"Error executing statement {i+1}: {e}")
            print(f"Statement: {sql}")
            # Don't break, try next? Or break? 
            # Usually migration should stop.
            # But "DROP PROCEDURE IF EXISTS" might fail if permissions issues etc.
            # Let's continue for now but log error.
    
    cnx.commit()
    cursor.close()
    cnx.close()
    print("Migration finished.")

if __name__ == "__main__":
    migration_file = os.path.join(os.path.dirname(__file__), 'db', 'roles_migration.sql')
    run_migration(migration_file)
