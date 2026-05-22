# controllers/proveedor.compañia.py
import re
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

        has_lpv_any = False
        has_lpv_pension = False
        has_lpv_eps = False

        for dr in db_rows:
            nombre_corto = (dr.get('nombre_corto') or '').strip()
            nombre_largo = (dr.get('nombre') or '').strip()
            nombre = nombre_corto or nombre_largo
            low_short = nombre_corto.lower()
            low_full = nombre_largo.lower()
            low = (low_short + ' ' + low_full).strip()
            low_compact = re.sub(r'[^a-z0-9]+', '', low)

            if 'mapfre' in low and ('vida' in low and 'ley' in low):
                slug = 'mapfre-vida-ley'
            elif 'mapfre' in low:
                slug = 'mapfre'
            elif (
                ('positiva' in low)
                or ('lpv' in low)
                or ('lpeps' in low)
                or ('lpv' in low)
                or ('lpv' in low_compact)
                or ('lpeps' in low_compact)
                or ('lpv' in low_compact)
            ):
                has_lpv_any = True
                if ('lpeps' in low) or ('lpeps' in low_compact) or ('eps' in low) or ('entidad prestadora' in low) or ('salud' in low):
                    slug = 'lpv-eps'
                    has_lpv_eps = True
                elif ('vida' in low) and ('ley' in low):
                    slug = 'lpv-vida-ley'
                elif 'vida' in low:
                    slug = 'lpv-vida'
                elif ('pension' in low) or ('pensión' in low) or ('lvp' in low) or ('lvp' in low_compact) or (low_compact == 'lpv') or (low_short.strip() == 'lpv'):
                    slug = 'lpv-pension'
                    has_lpv_pension = True
                else:
                    slug = 'positiva'
            elif 'sanitas' in low:
                slug = 'sanitas'
            elif 'pacifico' in low or 'pacífico' in low:
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
            elif 'crecer' in low:
                slug = 'crecer'
            elif 'protecta' in low or 'proctecta' in low:
                slug = 'proctecta'
            else:
                slug = ''

            rows.append({'nombre_corto': nombre, 'slug': slug})

        if has_lpv_any:
            if not has_lpv_eps:
                rows.append({'nombre_corto': 'LPEPS', 'slug': 'lpv-eps'})
            if not has_lpv_pension:
                rows.append({'nombre_corto': 'LPV', 'slug': 'lpv-pension'})
    except Exception:
        rows = []
    return rows
