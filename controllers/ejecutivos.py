# controllers/ejecutivos.py

from models.db import get_connection

def get_ejecutivos():
    rows = []
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        # Intentar con SP
        try:
            cur.callproc('sp_listar_ejecutivos')
            for result in cur.stored_results():
                for r in result.fetchall():
                    rows.append({
                        'id': r.get('idEjecutivo') or r.get('id') or None,
                        'nombre': r.get('nombre') or '',
                        'abreviacion': r.get('abreviacion') or '',
                        'grupo': r.get('grupo') or ''
                    })
        except Exception:
            rows = []
        # Si el SP no trae id, consultar tabla directa
        if not rows or all(r.get('id') is None for r in rows):
            cur.execute("SELECT idEjecutivo AS id, nombre, abreviacion, grupo FROM ejecutivos ORDER BY idEjecutivo ASC")
            rows = cur.fetchall() or []
        try:
            rows = sorted(rows, key=lambda r: r.get('id'))
        except Exception:
            pass
        cur.close()
    except Exception as e:
        print(f'[ejecutivos] error: {e}')
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows
