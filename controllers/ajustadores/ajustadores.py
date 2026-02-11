from models.db import get_connection


def get_ajustadores():
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        # Usamos SELECT directo para asegurarnos de devolver el ID (el SP original no lo incluye)
        cur.execute("SELECT id, nombre, abreviacion, codigo FROM ajustadores ORDER BY nombre ASC")
        rows = cur.fetchall() or []
        return rows
    except Exception:
        return []
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if cnx:
                cnx.close()
        except Exception:
            pass


def insert_ajustador(data: dict) -> dict:
    try:
        nombre = (data.get('nombre') or '').strip()
        abreviacion = (data.get('abreviacion') or '').strip()
        codigo = (data.get('codigo') or '').strip()

        errors = []
        if not nombre:
            errors.append('El nombre es obligatorio')
        if not codigo:
            errors.append('El código es obligatorio')
        if errors:
            return {'ok': False, 'errors': errors}

        cnx = get_connection()
        cur = cnx.cursor()

        # Llamamos al SP con variable de salida @p_new_id y luego la consultamos
        cur.execute("CALL sp_insertar_ajustador(%s, %s, %s, @p_new_id)", (nombre, abreviacion, codigo))
        cur.execute("SELECT @p_new_id")
        res = cur.fetchone()
        new_id = None
        if res:
            try:
                new_id = int(res[0])
            except Exception:
                new_id = None

        cnx.commit()
        cur.close()
        cnx.close()
        return {'ok': True, 'id': new_id}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def delete_ajustador(id_):
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        # Ejecutar el SP que hace DELETE
        cur.execute("CALL sp_eliminar_ajustador(%s)", (id_,))
        # Obtener filas afectadas usando ROW_COUNT()
        cur.execute("SELECT ROW_COUNT()")
        res = cur.fetchone()
        affected = 0
        if res:
            try:
                affected = int(res[0])
            except Exception:
                affected = 0
        cnx.commit()
        return affected
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if cnx:
                cnx.close()
        except Exception:
            pass
