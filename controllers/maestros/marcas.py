from models.db import get_connection


def get_marcas():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, nombre, estado FROM marcas ORDER BY nombre ASC")
        return cur.fetchall()
    finally:
        conn.close()


def insert_marca(nombre):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO marcas (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)", (nombre.strip(),))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_marca(id_):
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Will raise error if modelos exist due to FK; we just propagate
        cur.execute("DELETE FROM marcas WHERE id = %s", (id_,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

