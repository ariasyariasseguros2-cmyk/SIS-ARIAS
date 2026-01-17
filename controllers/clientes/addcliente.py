def validate_cliente_payload(data: dict) -> tuple[bool, list[str]]:
    errors = []
    required = [
        'tipoPersona', 'razonSocial', 'numeroDocumento', 'direccion',
        'distrito', 'departamento', 'provincia', 'telefono1', 'email',
        'subAgente', 'contactoNombre', 'contactoEmail', 'contactoTelefono'
    ]
    for key in required:
        if not str(data.get(key, '')).strip():
            errors.append(f'Falta {key}')
    return (len(errors) == 0, errors)

def save_cliente(data: dict) -> dict:

    ok, errors = validate_cliente_payload(data)
    if not ok:
        return {'ok': False, 'errors': errors}

    def normalize_tipo_doc(td: str) -> str:
        t = (td or '').upper().strip()
        if 'RUC' in t:
            return 'RUC'
        if 'PAS' in t:
            return 'PAS'
        if 'CEX' in t or 'CE' in t:
            return 'CE'
        return 'DNI'

    # tipo de persona 1=NATURAL, 2=JURIDICA
    def normalize_tipo_persona(tp) -> int | None:
        t = str(tp or '').strip().upper()
        if not t:
            return None
        if t.isdigit():
            return int(t)
        if 'NAT' in t:   # NATURAL, P. NATURAL, etc.
            return 1
        if 'JUR' in t:   # JURIDICA, P. JURIDICA, etc.
            return 2
        return None

    tipo_documento = normalize_tipo_doc(data.get('tipoDocumento'))
    razon = (data.get('razonSocial') or '').strip()
    numero = (data.get('numeroDocumento') or '').strip()
    telefono = (data.get('telefono1') or '').strip()
    subag = (data.get('subAgente') or '').strip()
    email = (data.get('email') or '').strip()
    direccion = (data.get('direccion') or '').strip()
    estado = (data.get('estado') or 'Vigente').strip()
    tipo_persona = normalize_tipo_persona(data.get('tipoPersona'))

    # Nuevos campos
    recibir_notificaciones = 1 if data.get('recibirNotificaciones') in (True, 'true', 'True', 1, '1', 'SI', 'si') else 0
    contacto_nombre = (data.get('contactoNombre') or '').strip()
    contacto_email = (data.get('contactoEmail') or '').strip()
    contacto_telefono = (data.get('contactoTelefono') or '').strip()
    profesion = (data.get('profesion') or '').strip()
    referencias_interes = (data.get('referenciasInteres') or '').strip()
    # aceptar las claves posibles: 'masInformacion' o 'notasInteres'
    notas = (data.get('masInformacion') or data.get('notasInteres') or '').strip()

    if tipo_persona is None:
        return {'ok': False, 'errors': ['tipoPersona inválida. Use NATURAL o JURIDICA']}

    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()

        # Verificar existencia por numero_documento
        cur.execute("CALL sp_get_cliente_por_numero(%s)", (numero,))
        row = cur.fetchone()
        while cur.nextset():
            pass
        if row:
            cur.close()
            cnx.close()
            return {'ok': False, 'errors': [f'Cliente ya existe con ese número de documento {numero}']}

        # Insertar si no existe
        cur.execute(
            "CALL sp_insert_cliente(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                razon, tipo_documento, numero, telefono, subag, email, direccion, estado, tipo_persona,
                recibir_notificaciones, contacto_nombre, contacto_email, contacto_telefono,
                profesion, referencias_interes, notas
            )
        )
        cnx.commit()
        while cur.nextset():
            pass
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'errors': [str(e)]}
