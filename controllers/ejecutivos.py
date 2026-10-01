# controllers/ejecutivos.py

from models.db import get_connection


def get_ejecutivos():
    rows = []
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # =========================================================
        # Intentar obtener ejecutivos mediante Stored Procedure
        # =========================================================
        try:
            cur.callproc('sp_listar_ejecutivos')

            for result in cur.stored_results():
                for r in result.fetchall():

                    # Si el SP trae activo, validar que sea 1
                    activo = r.get('activo', 1)

                    if activo != 1:
                        continue

                    rows.append({
                        'id': r.get('idEjecutivo') or r.get('id') or None,
                        'nombre': r.get('nombre') or '',
                        'abreviacion': r.get('abreviacion') or '',
                        'grupo': r.get('grupo') or '',
                        'activo': 1
                    })

        except Exception:
            rows = []

        # =========================================================
        # Si el SP no funciona o no devuelve datos,
        # consultar directamente la tabla
        # =========================================================
        if not rows or all(r.get('id') is None for r in rows):

            cur.execute("""
                SELECT
                    idEjecutivo AS id,
                    nombre,
                    abreviacion,
                    grupo,
                    activo
                FROM ejecutivos
                WHERE activo = 1
                ORDER BY idEjecutivo ASC
            """)

            rows = cur.fetchall() or []

        # =========================================================
        # Ordenar por ID
        # =========================================================
        try:
            rows = sorted(
                rows,
                key=lambda r: r.get('id') or 0
            )
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