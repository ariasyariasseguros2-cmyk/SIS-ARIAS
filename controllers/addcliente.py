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
    # Persistir ...
    return {'ok': True, 'id': 1}