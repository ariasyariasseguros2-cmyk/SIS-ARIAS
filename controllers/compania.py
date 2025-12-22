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

        # Flags para inyectar opción “Crecer Vida Ley” si falta
        has_crecer = False
        has_crecer_vidaley = False

        for dr in db_rows:
            nombre = (dr.get('nombre_corto') or dr.get('nombre') or '').strip()
            low = nombre.lower()
            # Mapear al slug que tu parser espera
            if 'mapfre' in low and ('vida' in low and 'ley' in low):
                slug = 'mapfre-vida-ley'
            elif 'mapfre' in low:
                slug = 'mapfre'
            elif 'positiva' in low or 'lpv' in low:
                # Slug genérico de La Positiva cuando no se distingue en UI
                slug = 'positiva'
            elif 'sanitas' in low:
                slug = 'sanitas'
            elif 'pacifico' in low or 'pacífico' in low:
                slug = 'pacifico'
            elif 'pacífico' in low or 'pacífico' in low:
                slug = 'pacifico'
            elif 'crecer' in low and ('vida' in low and 'ley' in low):
                slug = 'vida-ley-crecer'
                has_crecer_vidaley = True
            elif 'crecer' in low:
                slug = 'crecer'
                has_crecer = True
            elif 'protecta' in low or 'proctecta' in low:
                # Mantener compatibilidad con el JS que usa 'proctecta'
                slug = 'proctecta'
            else:
                # Desconocidos: usar auto-detección (cadena vacía)
                slug = ''
            rows.append({'nombre_corto': nombre, 'slug': slug})

        # Inyectar opción “Crecer Vida Ley” si solo existe “Crecer”
        if has_crecer and not has_crecer_vidaley:
            rows.append({'nombre_corto': 'Crecer Vida Ley', 'slug': 'vida-ley-crecer'})
    except Exception:
        rows = []
    return rows