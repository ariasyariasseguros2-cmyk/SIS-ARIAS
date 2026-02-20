# controllers/ramos.py

from models.db import get_connection

def get_ramos() -> list[str]:
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        try:
            cur.execute("SELECT idRamo, nombre FROM ramos ORDER BY idRamo ASC")
            db_rows = cur.fetchall() or []
        except Exception:
            cur.execute("CALL sp_listar_ramos()")
            db_rows = cur.fetchall() or []
        cur.close()
        cnx.close()
        rows = [r['nombre'] for r in db_rows if r and r.get('nombre')]
    except Exception:
        rows = []
    return rows
