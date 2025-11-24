# controllers/ejecutivos.py

from models.db import get_connection

def get_ejecutivos():
    # Retorna listado de ejecutivos (nombre, abreviacion, grupo) desde el SP
    rows = []
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.callproc('sp_listar_ejecutivos')
        for result in cur.stored_results():
            for r in result.fetchall():
                rows.append({
                    'nombre': r.get('nombre') or '',
                    'abreviacion': r.get('abreviacion') or '',
                    'grupo': r.get('grupo') or ''
                })
        cur.close()
    except Exception as e:
        # En entorno actual, devolver lista vacía si falla
        print(f'[ejecutivos] error: {e}')
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows