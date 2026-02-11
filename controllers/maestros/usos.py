from models.db import get_connection


def get_usos():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, nombre, estado FROM usos ORDER BY nombre ASC")
        return cur.fetchall()
    finally:
        conn.close()


def insert_uso(nombre):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO usos (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)", (nombre.strip(),))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_uso(id_):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM usos WHERE id = %s", (id_,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

