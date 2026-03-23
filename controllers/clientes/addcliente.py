def validate_cliente_payload(data: dict) -> tuple[bool, list[str]]:
    import re
    errors = []

    # Campos requeridos
    required = [
        'tipoPersona', 'razonSocial', 'numeroDocumento', 'direccion',
        'distrito', 'departamento', 'provincia', 'telefono1', 'email',
        'subAgente'
    ]

    for key in required:
        if not str(data.get(key, '')).strip():
            errors.append(f'El campo {key} es obligatorio')

    # Si hay campos faltantes, retornar inmediatamente
    if errors:
        return (False, errors)

    # Validaciones específicas
    razon_social = str(data.get('razonSocial', '')).strip()
    if len(razon_social) < 3 or len(razon_social) > 200:
        errors.append('La Razón Social debe tener entre 3 y 200 caracteres')

    numero_doc = str(data.get('numeroDocumento', '')).strip()
    if not re.match(r'^[0-9]{8,11}$', numero_doc):
        errors.append('El Número de Documento debe contener entre 8 y 11 dígitos numéricos')

    email = str(data.get('email', '')).strip()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors.append('El Email no tiene un formato válido')

    telefono1 = str(data.get('telefono1', '')).strip()
    if not re.match(r'^[0-9]{9}$', telefono1):
        errors.append('El Celular Principal debe tener exactamente 9 dígitos')

    telefono2 = str(data.get('telefono2', '')).strip()
    if telefono2 and not re.match(r'^[0-9]{7,9}$', telefono2):
        errors.append('El Teléfono Secundario debe tener entre 7 y 9 dígitos')

    direccion = str(data.get('direccion', '')).strip()
    if len(direccion) < 5 or len(direccion) > 200:
        errors.append('La Dirección debe tener entre 5 y 200 caracteres')

    distrito = str(data.get('distrito', '')).strip()
    if len(distrito) < 2 or len(distrito) > 50:
        errors.append('El Distrito debe tener entre 2 y 50 caracteres')

    departamento = str(data.get('departamento', '')).strip()
    if len(departamento) < 2 or len(departamento) > 50:
        errors.append('El Departamento debe tener entre 2 y 50 caracteres')

    provincia = str(data.get('provincia', '')).strip()
    if len(provincia) < 2 or len(provincia) > 50:
        errors.append('La Provincia debe tener entre 2 y 50 caracteres')

    contacto_nombre = str(data.get('contactoNombre', '')).strip()
    if contacto_nombre:
        if len(contacto_nombre) < 3 or len(contacto_nombre) > 100:
            errors.append('El Nombre de Contacto debe tener entre 3 y 100 caracteres')

    contacto_email = str(data.get('contactoEmail', '')).strip()
    if contacto_email:
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', contacto_email):
            errors.append('El Email de Contacto no tiene un formato válido')

    contacto_telefono = str(data.get('contactoTelefono', '')).strip()
    if contacto_telefono:
        if not re.match(r'^[0-9]{7,9}$', contacto_telefono):
            errors.append('El Teléfono de Contacto debe tener entre 7 y 9 dígitos')

    # Validar tipo de persona
    tipo_persona = str(data.get('tipoPersona', '')).strip().upper()
    if tipo_persona not in ['NATURAL', 'JURIDICA', '1', '2']:
        errors.append('El Tipo de Persona debe ser NATURAL o JURIDICA')

    # Validar tipo de documento
    tipo_doc = str(data.get('tipoDocumento', '')).strip().upper()
    valid_doc_types = ['DNI', 'DNI/CE', 'RUC', 'CEX', 'CE', 'PAS', 'PASAPORTE']
    if tipo_doc and tipo_doc not in valid_doc_types:
        errors.append('El Tipo de Documento no es válido')

    # Validar licencia de conducir si se proporciona (permitir formato combinado 'CATEGORIA | NUM')
    licencia_raw = str(data.get('licenciaConducir', '')).strip()
    if licencia_raw:
        # Aceptar letras, números, espacios, guiones y el separador '|' entre 3 y 60 caracteres
        if not re.match(r'^[A-Za-z0-9 \|\-]{3,60}$', licencia_raw):
            errors.append('El campo Licencia de Conducir tiene un formato inválido')

    # Validar vencimiento de licencia (no puede ser menor a la fecha actual)
    vencimiento_licencia = data.get('vencimientoLicencia')
    if vencimiento_licencia:
        try:
            from datetime import datetime
            if isinstance(vencimiento_licencia, str):
                # Intentar parsear la fecha
                if '/' in vencimiento_licencia:
                    fecha_venc = datetime.strptime(vencimiento_licencia, '%d/%m/%Y')
                else:
                    fecha_venc = datetime.strptime(vencimiento_licencia, '%Y-%m-%d')

                # Comparar con fecha actual
                fecha_actual = datetime.now()
                if fecha_venc.date() < fecha_actual.date():
                    errors.append('La fecha de vencimiento de la licencia no puede ser anterior a la fecha actual')
        except (ValueError, TypeError):
            errors.append('La fecha de vencimiento de la licencia no tiene un formato válido')

    return (len(errors) == 0, errors)

def parse_date(date_str: str | None) -> str | None:
    """Convierte fecha en formato dd/mm/yyyy o yyyy-mm-dd a formato MySQL yyyy-mm-dd"""
    if not date_str or not str(date_str).strip():
        return None
    try:
        date_str = str(date_str).strip()
        # Intentar formato dd/mm/yyyy
        from datetime import datetime
        if '/' in date_str:
            dt = datetime.strptime(date_str, '%d/%m/%Y')
        else:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return None

def save_cliente(data: dict) -> dict:
    from flask import current_app, session
    current_app.logger.info(f"[addcliente] Payload recibido: {data}")

    # Obtener usuario de la sesión
    usuario_actual = session.get('user', 'SISTEMA')
    role_name = session.get('role_name')

    # RBAC: Si es SUB AGENTE, forzar que el subagente sea él mismo
    from utils.rbac import Roles
    if role_name == Roles.SUB_AGENTE:
        # Sobreescribir el subagente con el usuario actual
        data['subAgente'] = usuario_actual

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
            return 'CEX'
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

    # Datos básicos
    tipo_documento = normalize_tipo_doc(data.get('tipoDocumento'))
    razon = (data.get('razonSocial') or '').strip()
    numero = (data.get('numeroDocumento') or '').strip()
    telefono = (data.get('telefono1') or '').strip()
    celular = (data.get('telefono1') or '').strip()
    telefono_sec = (data.get('telefono2') or '').strip()
    email = (data.get('email') or '').strip()
    direccion = (data.get('direccion') or '').strip()
    departamento = (data.get('departamento') or '').strip()
    provincia = (data.get('provincia') or '').strip()
    distrito = (data.get('distrito') or '').strip()
    estado = (data.get('estado') or 'Vigente').strip()
    tipo_persona = normalize_tipo_persona(data.get('tipoPersona'))

    # Subagente: obtener idProductor y nombre
    subagente_input = (data.get('subAgente') or '').strip()
    idProductor = None
    subagente_nombre = subagente_input

    # Si subAgente viene como número, es el idProductor
    if subagente_input.isdigit():
        idProductor = int(subagente_input)
    else:
        # Buscar por nombre (fallback)
        subagente_nombre = subagente_input

    # Perfil y clasificación
    profesion = (data.get('profesion') or '').strip()
    fecha_ingreso = parse_date(data.get('fechaIngreso'))
    fecha_nacimiento = parse_date(data.get('cumpleanios'))
    licencia_num = (data.get('licenciaConducir') or '').strip()
    licencia_venc = parse_date(data.get('vencimientoLicencia'))
    grupo_economico = (data.get('grupoEconomico') or '').strip()
    giro_negocio = (data.get('giroNegocio') or '').strip()
    referencia = (data.get('referencia') or '').strip()
    recomendado_por = (data.get('recomendadoPor') or '').strip()

    # Contacto y notificaciones
    recibir_notificaciones = 1 if data.get('recibirNotificaciones') in (True, 'true', 'True', 1, '1', 'SI', 'si') else 0
    contacto_nombre = (data.get('contactoNombre') or '').strip()
    contacto_email = (data.get('contactoEmail') or '').strip()
    contacto_telefono = (data.get('contactoTelefono') or '').strip()

    # Notas y campos eliminados: siniestralidad, referencias_interes, preferencias, notasInteres, masInformacion

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
            return {'ok': False, 'errors': [f'Ya existe un cliente con el número de documento {numero}']}

        # Si idProductor no se obtuvo, buscar por abreviacion
        if not idProductor and subagente_nombre:
            cur.execute("SELECT idProductor, abreviacion FROM subagente WHERE abreviacion = %s LIMIT 1", (subagente_nombre,))
            subagente_row = cur.fetchone()
            if subagente_row:
                idProductor = subagente_row[0]
                subagente_nombre = subagente_row[1]
            else:
                # Fallback: buscar por nombre si no se encuentra por abreviacion
                cur.execute("SELECT idProductor, abreviacion FROM subagente WHERE nombre = %s LIMIT 1", (subagente_nombre,))
                subagente_row = cur.fetchone()
                if subagente_row:
                    idProductor = subagente_row[0]
                    subagente_nombre = subagente_row[1]

        current_app.logger.info(f"[addcliente] Insertando: {razon}, {numero}, subagente={subagente_nombre}, idProductor={idProductor}")

        # Insertar con campos actualizados (sin los eliminados)
        args = (
            razon, tipo_documento, numero,
            telefono, celular, telefono_sec,
            subagente_nombre, idProductor,
            email, direccion, departamento, provincia, distrito,
            estado, tipo_persona,
            profesion, fecha_ingreso, fecha_nacimiento,
            licencia_num, licencia_venc,
            grupo_economico, giro_negocio, referencia, recomendado_por,
            recibir_notificaciones, contacto_nombre, contacto_email, contacto_telefono,
            usuario_actual
        )

        try:
            cur.callproc('sp_insert_cliente', args)
        except Exception as e:
            current_app.logger.error(f"[addcliente] Error al llamar sp_insert_cliente: {e}")
            raise
        cnx.commit()
        while cur.nextset():
            pass
        cur.close()
        cnx.close()
        current_app.logger.info(f"[addcliente] Cliente insertado correctamente: {numero}")
        return {'ok': True}
    except Exception as e:
        current_app.logger.error(f"[addcliente] Error: {e}")
        return {'ok': False, 'errors': [str(e)]}
