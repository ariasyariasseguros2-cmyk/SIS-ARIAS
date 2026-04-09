from models.db import get_connection

def get_soat_conf():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                cs.id,
                t.id as tipo_soat_id,
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

def update_soat_conf(row_id, tipo_soat_id, tasa_aas, tasa_vendedor, tasa_final_override):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Actualizar tasas generales del tipo (afecta a todos los que compartan el tipo)
        if tipo_soat_id:
            query_tipo = "UPDATE tipos_soat SET tasa_aas = %s, tasa_vendedor = %s WHERE id = %s"
            cursor.execute(query_tipo, (tasa_aas, tasa_vendedor, tipo_soat_id))
        
        # 2. Actualizar el override específico de la fila
        query_cs = "UPDATE configuracion_soat SET tasa_final_override = %s WHERE id = %s"
        cursor.execute(query_cs, (tasa_final_override, row_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating soat conf: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
