from models.db import get_connection


def get_productos():
    cnx = get_connection()
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT p.id_producto AS id, p.nombre, p.codigo, p.grupo, p.idRamo AS ramo_id, r.nombre AS ramo_nombre FROM productos p JOIN ramos r ON r.idRamo = p.idRamo ORDER BY p.id_producto ASC")
        return cur.fetchall() or []
    finally:
        cnx.close()


def insert_producto(idRamo, nombre, codigo=None, grupo=None):
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute("CALL sp_insertar_producto(%s, %s, %s, %s, @p_new_id)", (idRamo, nombre or '', codigo or '', grupo or ''))
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


def delete_producto(id_):
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute("CALL sp_eliminar_producto(%s)", (id_,))
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

