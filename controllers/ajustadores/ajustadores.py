from models.db import get_connection


def get_ajustadores():
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("CALL sp_listar_ajustadores()")
        rows = cur.fetchall() or []
        while cur.nextset():
            pass
        cur.close()
        cnx.close()
        return rows
    except Exception:
        return []


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
