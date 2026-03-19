# controllers/proveedor.compañia.py
from models.db import get_connection

def get_aseguradoras() -> list[dict]:
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        # SP: devuelve al menos nombre_corto
        cur.execute("CALL sp_listar_companias()")
        db_rows = cur.fetchall() or []
        while cur.nextset():
            pass
        cur.close()
        cnx.close()

        has_crecer = False

        for dr in db_rows:
            nombre_corto = (dr.get('nombre_corto') or '').strip()
            nombre_largo = (dr.get('nombre') or '').strip()
            nombre = nombre_corto or nombre_largo
            low_short = nombre_corto.lower()
            low_full = nombre_largo.lower()
            low = (low_short + ' ' + low_full).strip()
            # Mapear al slug que tu parser espera
            if 'mapfre' in low and ('vida' in low and 'ley' in low):
                slug = 'mapfre-vida-ley'
            elif 'mapfre' in low:
                slug = 'mapfre'
            elif 'positiva' in low or 'lpv' in low:
                # Unificar EPS/Salud bajo 'lpv-eps' y Vida bajo 'lpv-vida'/'lpv-vida-ley'
                if 'lpeps' in low or 'eps' in low or 'entidad prestadora' in low or 'salud' in low:
                    slug = 'lpv-eps'
                elif 'vida' in low and 'ley' in low:
                    slug = 'lpv-vida-ley'
                elif 'vida' in low:
                    slug = 'lpv-vida'
                elif 'pension' in low or 'pensión' in low:
                    slug = 'lpv-pension'
                else:
                    slug = 'positiva'
            elif 'sanitas' in low:
                slug = 'sanitas'
            elif 'pacifico' in low or 'pacífico' in low:
                slug = 'pacifico'
            elif 'pacífico' in low or 'pacífico' in low:
                slug = 'pacifico'
            elif 'rimac' in low or 'rímac' in low:
                slug = 'rimac'
            elif 'hdi' in low:
                slug = 'hdi'
            elif 'ohio' in low:
                slug = 'ohio'
            elif 'qualitas' in low or 'quálitas' in low:
                slug = 'qualitas'
            elif 'avla' in low:
                slug = 'avla'
            elif 'grandia' in low and 'eps' in low:
                slug = 'grandia-eps'
            elif 'crecer' in low and ('vida' in low and 'ley' in low):
                slug = 'crecer'
                has_crecer = True
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

        # No inyectar variante “Crecer Vida Ley”; mantener solo “Crecer”
    except Exception:
        rows = []
    return rows
