from models.db import get_connection


def get_ramos():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        # Incluir idRamo como id para consistencia con otras entidades
        cur.execute("SELECT idRamo AS id, nombre, abreviacion, codigo, grupo, estado FROM ramos ORDER BY nombre ASC")
        rows = cur.fetchall() or []
        return rows
    finally:
        conn.close()


def insert_ramo(nombre, abreviacion=None, codigo=None, grupo=None):
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        # Llamar al stored procedure que inserta y deja el id en variable @p_new_id
        cur.execute("CALL sp_insertar_ramo(%s, %s, %s, %s, @p_new_id)", (nombre or '', abreviacion or '', codigo or '', grupo or ''))
        # Recuperar variable OUT
        cur.execute("SELECT @p_new_id")
        res = cur.fetchone()
        new_id = None
        if res:
            try:
                new_id = int(res[0])
            except Exception:
                new_id = None

        cnx.commit()
        return new_id
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


def delete_ramo(id_):
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        # Usar SP para eliminar
        cur.execute("CALL sp_eliminar_ramo(%s)", (id_,))
        # Obtener filas afectadas
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
