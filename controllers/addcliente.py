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
    # Aquí conectar con DB o capa de servicio
    # Retorna un objeto de resultado simplificado
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

    tipo_documento = normalize_tipo_doc(data.get('tipoDocumento'))
    razon = (data.get('razonSocial') or '').strip()
    numero = (data.get('numeroDocumento') or '').strip()
    telefono = (data.get('telefono1') or '').strip()
    subag = (data.get('subAgente') or '').strip()
    email = (data.get('email') or '').strip()
    direccion = (data.get('direccion') or '').strip()

    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute(
            "CALL sp_insert_cliente(%s,%s,%s,%s,%s,%s,%s)",
            (razon, tipo_documento, numero, telefono, subag, email, direccion)
        )
        cnx.commit()
        while cur.nextset():
            pass
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'errors': [str(e)]}
    return {'ok': True, 'id': 1}