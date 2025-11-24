# controllers/subagente.py
from models.db import get_connection

def get_subagentes_abreviaciones() -> list[str]:
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("CALL sp_listar_SubAgente_abreviacion()")
        db_rows = cur.fetchall() or []
        while cur.nextset():
            pass
        cur.close()
        cnx.close()
        # Dedup y limpieza
        seen = set()
        for dr in db_rows:
            abbr = (dr.get('abreviacion') or '').strip()
            if abbr and abbr not in seen:
                seen.add(abbr)
                rows.append(abbr)
    except Exception:
        rows = []
    return rows