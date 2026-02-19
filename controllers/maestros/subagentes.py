from models.db import get_connection

def get_subagentes():
    rows = []
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT 
                    idProductor AS id,
                    nombre,
                    abreviacion,
                    email,
                    telefono,
                    celular
                FROM SubAgente
                ORDER BY nombre ASC
            """)
        except Exception:
            return []
        rows = cur.fetchall() or []
        cur.close()
    except Exception as e:
        print(f"[maestros.subagentes] error: {e}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows

