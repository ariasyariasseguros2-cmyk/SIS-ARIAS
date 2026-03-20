from models.db import get_connection


def get_subagentes():
    rows = []
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            # Intentamos con el nombre de tabla en mayúsculas
            cur.execute("""
                SELECT
                    idProductor AS id,
                    nombre,
                    abreviacion
                FROM SubAgente
                ORDER BY nombre ASC
            """)
        except Exception as e_subagente:
            # Fallback si la tabla existe con nombre en minúsculas
            try:
                cur.execute("""
                    SELECT
                        idProductor AS id,
                        nombre,
                        abreviacion
                    FROM subagente
                    ORDER BY nombre ASC
                """)
            except Exception as e_legacy:
                print(f"[maestros.subagentes] SQL error selecting subagentes: {e_subagente} | {e_legacy}")
                return []
        rows = cur.fetchall() or []
    except Exception as e:
        print(f"[maestros.subagentes] error: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows

