# controllers/proveedor.compañia.py
from models.db import get_connection

def get_aseguradoras() -> list[dict]:
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        # SP: devuelve al menos nombre_corto
        cur.execute("CALL sp_listar_aseguradoras()")
        db_rows = cur.fetchall() or []
        while cur.nextset():
            pass
        cur.close()
        cnx.close()

        for dr in db_rows:
            nombre = (dr.get('nombre_corto') or dr.get('nombre') or '').strip()
            low = nombre.lower()
            # Mapear al slug que tu parser espera
            if 'mapfre' in low:
                slug = 'mapfre'
            elif 'positiva' in low:
                slug = 'positiva'
            else:
                # Desconocidos: usar auto-detección (cadena vacía)
                slug = ''
            rows.append({'nombre_corto': nombre, 'slug': slug})
    except Exception:
        rows = []
    return rows
