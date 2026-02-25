from models.db import get_connection

def get_soat_conf():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                cs.id,
                t.nombre as tipo_soat,
                u.nombre as uso,
                c.nombre as clase,
                t.tasa_aas,
                t.tasa_vendedor,
                cs.tasa_final_override
            FROM configuracion_soat cs
            JOIN tipos_soat t ON cs.tipo_soat_id = t.id
            JOIN usos u ON cs.uso_id = u.id
            JOIN clases c ON cs.clase_id = c.id
            ORDER BY t.nombre, c.nombre, u.nombre
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting soat conf: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
