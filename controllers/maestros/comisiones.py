from models.db import get_connection

def get_comisiones():
    rows = []
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT 
                  id,
                  ramo_nombre,
                  ramo_abreviacion,
                  producto,
                  producto_abrev,
                  pos_eps,
                  pos_vsr,
                  pos_sr,
                  pacifico,
                  sanitas,
                  protecta,
                  mapfre,
                  crecer,
                  ohio_natural,
                  factor
                FROM comisiones_temp
                ORDER BY id ASC
            """)
        except Exception:
            # Si no existe la tabla, devolver vacío
            return []
        rows = cur.fetchall() or []
        cur.close()
    except Exception as e:
        print(f"[comisiones] error: {e}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows

