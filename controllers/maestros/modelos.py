from models.db import get_connection


def get_modelos():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT m.id, m.nombre, m.estado, m.marca_id, ma.nombre AS marca_nombre FROM modelos m JOIN marcas ma ON ma.id = m.marca_id ORDER BY m.id ASC")
        return cur.fetchall()
    finally:
        conn.close()


def insert_modelo(marca_id, nombre):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO modelos (marca_id, nombre) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)", (marca_id, nombre.strip()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_modelo_por_nombres(marca_nombre, modelo_nombre):
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Insert marca if not exists
        cur.execute("INSERT INTO marcas (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)", (marca_nombre.strip(),))
        marca_id = cur.lastrowid
        cur.execute("INSERT INTO modelos (marca_id, nombre) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)", (marca_id, modelo_nombre.strip()))
        conn.commit()
        return marca_id, cur.lastrowid
    finally:
        conn.close()


def delete_modelo(id_):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM modelos WHERE id = %s", (id_,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

