import re
from controllers.clientes.addcliente import parse_date

TIPO_OPERACION_OPTIONS = ['COTIZACION', 'EMISION', 'ENDOSO', 'RENOVACION', 'ANULACION', 'DUPLICADO', 'OTRO']
UBICACION_OPTIONS = ['CLIENTE', 'COMPANIA', 'SUBAGENTE']
PRIORIDAD_OPTIONS = ['NORMAL', 'ALTA', 'URGENTE']
MEDIO_OPTIONS = ['CORREO', 'TELEFONO', 'WHATSAPP', 'PRESENCIAL']

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Decrypt helper reutilizado en todas las columnas cifradas de esta tabla.
_DECRYPT_SQL = """CONVERT(
    COALESCE(
        CAST(AES_DECRYPT(FROM_BASE64({col}), @SIS_KEY) AS CHAR),
        CAST(AES_DECRYPT({col}, @SIS_KEY) AS CHAR),
        {col}
    ) USING utf8mb4
) COLLATE utf8mb4_0900_ai_ci"""


def _parse_emails(raw: str) -> list[str]:
    return [e.strip() for e in (raw or '').split(';') if e.strip()]


def validate_solicitud_payload(data: dict) -> tuple[bool, list[str]]:
    errors = []

    tipo_operacion = (data.get('tipo_operacion') or '').strip().upper()
    if not tipo_operacion:
        errors.append('El campo Tipo Operación es obligatorio')
    elif tipo_operacion not in TIPO_OPERACION_OPTIONS:
        errors.append('Tipo Operación no es válido')

    if not (data.get('fecha_solicitud') or '').strip():
        errors.append('El campo Fecha Solicitud es obligatorio')

    ubicacion = (data.get('ubicacion') or '').strip().upper()
    if not ubicacion:
        errors.append('El campo Ubicación es obligatorio')
    elif ubicacion not in UBICACION_OPTIONS:
        errors.append('Ubicación no es válida')

    prioridad = (data.get('prioridad') or 'NORMAL').strip().upper()
    if prioridad not in PRIORIDAD_OPTIONS:
        errors.append('Prioridad no es válida')

    if not (data.get('gestor') or '').strip():
        errors.append('El campo Gestor es obligatorio')

    for label, key in (('Para', 'para'), ('Cc', 'cc')):
        for email in _parse_emails(data.get(key)):
            if not _EMAIL_RE.match(email):
                errors.append(f'El correo "{email}" en {label} no es válido')

    return (len(errors) == 0, errors)


def save_solicitud(data: dict, usuario_actual: str) -> dict:
    ok, errors = validate_solicitud_payload(data)
    if not ok:
        return {'ok': False, 'errors': errors}

    from models.db import get_connection
    from datetime import date

    medio = (data.get('medio') or 'CORREO').strip().upper()
    if medio not in MEDIO_OPTIONS:
        medio = 'CORREO'

    hoy = date.today().isoformat()

    values = {
        'tipo_operacion': (data.get('tipo_operacion') or '').strip().upper(),
        'fecha_solicitud': parse_date(data.get('fecha_solicitud')) or hoy,
        'ubicacion': (data.get('ubicacion') or '').strip().upper(),
        'prioridad': (data.get('prioridad') or 'NORMAL').strip().upper(),
        'medio': medio,
        'gestor': (data.get('gestor') or '').strip(),
        'fecha_asignacion_gestor': hoy,
        'fecha_asignacion_estado': hoy,
        'fecha_proxima_gestion': parse_date(data.get('fecha_proxima_gestion')),
        'cliente': (data.get('cliente') or '').strip() or None,
        'compania': (data.get('compania') or '').strip() or None,
        'ramo': (data.get('ramo') or '').strip() or None,
        'numero_tramite_cia': (data.get('numero_tramite_cia') or '').strip() or None,
        'poliza': (data.get('poliza') or '').strip() or None,
        'subagente': (data.get('subagente') or '').strip() or None,
        'ejecutivo': (data.get('ejecutivo') or '').strip() or None,
        'para': (data.get('para') or '').strip() or None,
        'cc': (data.get('cc') or '').strip() or None,
        'motivo': (data.get('motivo') or '').strip() or None,
        'contenido': (data.get('contenido') or '').strip() or None,
        'registrado_por': usuario_actual,
    }

    cnx = get_connection()
    try:
        cur = cnx.cursor()
        cur.execute(
            """
            INSERT INTO solicitudes (
                tipo_operacion, fecha_solicitud, ubicacion, prioridad, medio, estado,
                gestor, fecha_asignacion_gestor, fecha_asignacion_estado, fecha_proxima_gestion,
                cliente, compania, ramo, numero_tramite_cia, poliza, subagente, ejecutivo,
                para, cc, asunto, motivo, contenido,
                registrado_por
            ) VALUES (
                %(tipo_operacion)s, %(fecha_solicitud)s, %(ubicacion)s, %(prioridad)s, %(medio)s, 'PENDIENTE',
                %(gestor)s, %(fecha_asignacion_gestor)s, %(fecha_asignacion_estado)s, %(fecha_proxima_gestion)s,
                TO_BASE64(AES_ENCRYPT(%(cliente)s, @SIS_KEY)),
                %(compania)s, %(ramo)s, %(numero_tramite_cia)s,
                TO_BASE64(AES_ENCRYPT(%(poliza)s, @SIS_KEY)),
                %(subagente)s, %(ejecutivo)s,
                TO_BASE64(AES_ENCRYPT(%(para)s, @SIS_KEY)),
                TO_BASE64(AES_ENCRYPT(%(cc)s, @SIS_KEY)),
                %(asunto)s, %(motivo)s, %(contenido)s,
                %(registrado_por)s
            )
            """,
            {**values, 'asunto': None}
        )
        new_id = cur.lastrowid

        numero_ti = f"{new_id:010d}"
        asunto = f"TI-{numero_ti}"
        cur.execute("UPDATE solicitudes SET asunto = %s WHERE idSolicitud = %s", (asunto, new_id))

        cnx.commit()
        cur.close()
        return {
            'ok': True,
            'id': new_id,
            'numero_ti': numero_ti,
            'asunto': asunto,
            'para': _parse_emails(values['para']),
            'cc': _parse_emails(values['cc']),
        }
    except Exception as e:
        cnx.rollback()
        return {'ok': False, 'errors': [str(e)]}
    finally:
        cnx.close()


def add_archivo(solicitud_id: int, ruta_archivo: str, nombre_original: str, usuario: str):
    from models.db import get_connection
    cnx = get_connection()
    try:
        cur = cnx.cursor()
        cur.execute(
            """INSERT INTO solicitud_archivos (solicitud_id, ruta_archivo, nombre_original, usuario)
               VALUES (%s, %s, %s, %s)""",
            (solicitud_id, ruta_archivo, nombre_original, usuario)
        )
        cnx.commit()
        cur.close()
    finally:
        cnx.close()


def get_solicitudes_rows(search: str | None = None, limit: int | None = 20, page: int = 1) -> dict:
    from models.db import get_connection

    decrypt_cliente = _DECRYPT_SQL.format(col='s.cliente')
    decrypt_poliza = _DECRYPT_SQL.format(col='s.poliza')

    query = f"""
        SELECT
            s.idSolicitud, s.tipo_operacion, s.fecha_solicitud, s.ubicacion,
            s.prioridad, s.medio, s.estado, s.gestor, s.fecha_proxima_gestion,
            {decrypt_cliente} AS cliente,
            s.compania, s.ramo, s.numero_tramite_cia,
            {decrypt_poliza} AS poliza,
            s.subagente, s.ejecutivo, s.asunto, s.motivo,
            s.registrado_por, s.fecha_registro
        FROM solicitudes s
        WHERE s.activo = 1
    """
    params = []
    search_str = (search or '').strip()
    if search_str:
        query += f""" AND (
            {decrypt_cliente} LIKE %s
            OR s.compania LIKE %s
            OR s.motivo LIKE %s
            OR s.asunto LIKE %s
            OR s.gestor LIKE %s
        )"""
        needle = f"%{search_str}%"
        params += [needle, needle, needle, needle, needle]

    count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS T"
    query += " ORDER BY s.idSolicitud DESC"

    cnx = get_connection()
    try:
        cur = cnx.cursor(dictionary=True)
        cur.execute(count_query, params)
        total = cur.fetchone()['total']

        rows_params = list(params)
        if isinstance(limit, int) and limit > 0:
            page = max(1, page or 1)
            offset = (page - 1) * limit
            query += " LIMIT %s OFFSET %s"
            rows_params += [limit, offset]

        cur.execute(query, rows_params)
        rows = cur.fetchall()
        cur.close()

        for row in rows:
            row['numero_ti'] = f"{row['idSolicitud']:010d}"
            if row.get('fecha_solicitud'):
                row['fecha_solicitud'] = row['fecha_solicitud'].strftime('%d-%m-%Y')
            if row.get('fecha_proxima_gestion'):
                row['fecha_proxima_gestion'] = row['fecha_proxima_gestion'].strftime('%d-%m-%Y')
            if row.get('fecha_registro'):
                row['fecha_registro'] = row['fecha_registro'].strftime('%d-%m-%Y %H:%M')

        return {'rows': rows, 'total': total}
    finally:
        cnx.close()


def anular_solicitud(idSolicitud: int) -> dict:
    from models.db import get_connection
    cnx = get_connection()
    try:
        cur = cnx.cursor()
        cur.execute("UPDATE solicitudes SET activo = 0 WHERE idSolicitud = %s", (idSolicitud,))
        cnx.commit()
        cur.close()
        return {'ok': True}
    except Exception as e:
        cnx.rollback()
        return {'ok': False, 'errors': [str(e)]}
    finally:
        cnx.close()
