from datetime import date

from models.db import get_connection


def listar_cumpleanos_colaboradores():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, nombre, area, fecha_nacimiento
            FROM cumpleanos_colaboradores
            ORDER BY MONTH(fecha_nacimiento), DAYOFMONTH(fecha_nacimiento), nombre
        """)
        return cur.fetchall() or []
    finally:
        conn.close()


def obtener_cumpleanos_de_hoy():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT nombre
            FROM cumpleanos_colaboradores
            WHERE MONTH(fecha_nacimiento) = MONTH(CURDATE())
              AND DAYOFMONTH(fecha_nacimiento) = DAYOFMONTH(CURDATE())
            ORDER BY nombre
        """)
        return [row['nombre'] for row in cur.fetchall() or []]
    finally:
        conn.close()


def crear_cumpleanos_colaborador(nombre, area, fecha_nacimiento):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cumpleanos_colaboradores
                (nombre, area, fecha_nacimiento)
            VALUES (%s, %s, %s)
        """, (nombre, area or None, fecha_nacimiento))
        colaborador_id = cur.lastrowid
        conn.commit()
        return {
            'id': colaborador_id,
            'nombre': nombre,
            'area': area or '',
            'fecha_nacimiento': fecha_nacimiento,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def validar_datos_cumpleanos(nombre, area, fecha_nacimiento):
    nombre = (nombre or '').strip()
    area = (area or '').strip()
    if not nombre or len(nombre) > 150:
        raise ValueError('Ingresa un nombre de hasta 150 caracteres.')
    if len(area) > 100:
        raise ValueError('El área o cargo no puede superar los 100 caracteres.')
    try:
        cumpleanos = date.fromisoformat(fecha_nacimiento)
    except (TypeError, ValueError):
        raise ValueError('Ingresa una fecha de nacimiento válida.')
    if cumpleanos > date.today():
        raise ValueError('La fecha de nacimiento no puede ser futura.')
    return nombre, area, cumpleanos
