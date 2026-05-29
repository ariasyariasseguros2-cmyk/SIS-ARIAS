# controllers/ramos.py

from models.db import get_connection

def get_ramos() -> list[str]:
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        try:
            cur.execute("SELECT idRamo, nombre FROM ramos ORDER BY nombre ASC")
            db_rows = cur.fetchall() or []
        except Exception:
            cur.execute("CALL sp_listar_ramos()")
            db_rows = cur.fetchall() or []
            # Si el SP no ordena, ordenamos aquí
            db_rows.sort(key=lambda x: (x.get('nombre') or '').lower())
        cur.close()
        cnx.close()
        rows = [r['nombre'] for r in db_rows if r and r.get('nombre')]
    except Exception:
        rows = []
    return rows
