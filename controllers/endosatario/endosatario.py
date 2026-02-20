from models.db import get_connection

def get_endosatarios() -> list[dict]:
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        try:
            cur.execute("SELECT idEndosatario AS id, nombre FROM endosatarios ORDER BY idEndosatario ASC")
            db_rows = cur.fetchall() or []
        except Exception:
            cur.execute("CALL sp_listar_endosatarios()")
            db_rows = cur.fetchall() or []
        cur.close()
        cnx.close()
        rows = db_rows
    except Exception as e:
        print(f"Error obteniendo endosatarios: {e}")
        rows = []
    return rows
