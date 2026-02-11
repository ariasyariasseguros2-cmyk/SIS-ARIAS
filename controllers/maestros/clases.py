from models.db import get_connection


def get_clases():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, nombre, costo_soat, estado FROM clases ORDER BY nombre ASC")
        rows = cur.fetchall()
        return rows
    finally:
        conn.close()


def insert_clase(nombre, costo_soat=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        if costo_soat is None:
            costo_soat = 0.00
        cur.execute("INSERT INTO clases (nombre, costo_soat) VALUES (%s, %s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)", (nombre.strip(), costo_soat))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_clase(id_):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM clases WHERE id = %s", (id_,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

