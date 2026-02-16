"""
Controlador para carga masiva de pólizas SOAT desde Excel
"""
import pandas as pd
from datetime import datetime
from models.db import get_connection
import mysql.connector


def validate_excel_structure(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Valida que el Excel tenga las columnas requeridas"""
    required_columns = [
        # Datos del cliente
        'TIPO_PERSONA', 'NOMBRE_RAZON_SOCIAL', 'NUMERO_DOCUMENTO',
        'DIRECCION', 'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO',

        # Datos de la póliza
        'SUBAGENTE_ABREVIACION', 'POLIZA_CERTF', 'COMPANIA_NOMBRE_CORTO',
        'RAMO_ABREVIACION', 'PRODUCTO_ABREVIACION',
        'TIPO_POLIZA', 'VIGENCIA_INICIO', 'VIGENCIA_FIN', 'MONEDA_ABREVIACION',
        'EJECUTIVO_ABREVIACION', 'AVISO_COB', 'TIPO_DOC', 'TIPO_PAGO',
        'PRIMA_NETA', 'PRIMA_TOTAL', 'FECHA_VENCIMIENTO',

        # Datos del vehículo
        'INCISO', 'SUMA_ASEGURADA', 'FECINCLUSION', 'PLACA',
        'CLASE', 'USO', 'SERIE', 'MARCA', 'MODELO', 'ANIO'

        # Nota: TIPO_DOCUMENTO, COD_AGENTE y VENDEDOR son opcionales
        # Si TIPO_DOCUMENTO está vacío, se detecta automáticamente según el número
    ]

    errors = []
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        errors.append(f"Faltan las siguientes columnas: {', '.join(missing_columns)}")
        return False, errors

    return True, []


def normalize_string(value) -> str:
    """Normaliza valores a string limpio y en mayúsculas"""
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip().upper()


def normalize_date(value) -> str | None:
    """Convierte fechas a formato YYYY-MM-DD. Maneja DD/MM/YYYY y YYYY-MM-DD"""
    if pd.isna(value) or value is None or value == '':
        return None

    try:
        # Si ya es datetime
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')

        # Intentar parsear string
        value_str = str(value).strip()

        if not value_str:
            return None

        # Formato DD/MM/YYYY (convertir a YYYY-MM-DD)
        if '/' in value_str:
            parts = value_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        # Formato YYYY-MM-DD (ya está correcto)
        if '-' in value_str and len(value_str) >= 10:
            parts = value_str.split('-')
            if len(parts) == 3:
                year, month, day = parts
                # Validar que year está primero (formato correcto)
                if len(year) == 4:
                    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        return None
    except Exception:
        return None


def normalize_decimal(value) -> float | None:
    """Convierte valores a decimal"""
    if pd.isna(value) or value is None or value == '':
        return None

    try:
        # Limpiar y convertir
        value_str = str(value).replace(',', '.').replace(' ', '')
        return float(value_str)
    except Exception:
        return None


def normalize_numero_documento(value) -> str:
    """
    Normaliza el número de documento preservando ceros a la izquierda cuando el valor es texto.
    - Si el valor viene como string y contiene ceros a la izquierda, los conserva.
    - Si viene como float (p.ej. 102836.0) elimina la parte ".0" y devuelve el entero como string.
    - Maneja notación científica y espacios/guiones.
    """
    if pd.isna(value) or value is None:
        return ''

    s = str(value).strip()
    if not s:
        return ''

    # Quitar espacios y guiones
    s = s.replace(' ', '').replace('-', '')

    # Si es algo como '102836.0' -> quitar '.0'
    if s.endswith('.0'):
        s = s[:-2]

    # Si tiene punto decimal y ambas partes son dígitos, quedarnos con la parte entera
    if '.' in s and all(part.isdigit() for part in s.split('.')):
        s = s.split('.')[0]

    # Manejar notación científica (ej: '1.0202836E+05')
    try:
        if 'E' in s.upper():
            from decimal import Decimal
            d = Decimal(s)
            if d == d.to_integral():
                s = str(d.to_integral())
            else:
                # Normalizar a forma sin exponencial y quitar punto si existe
                s = format(d.normalize(), 'f').replace('.', '')
    except Exception:
        pass

    # Si después de limpiar es sólo dígitos, retornarlo tal cual (preserva ceros a la izquierda si existían)
    # Si no son sólo dígitos (p.ej. pasaporte con letras), devolver la cadena limpia
    return s


def normalize_tipo_persona(value) -> int:
    """
    Normaliza el tipo de persona para aceptar texto o número.

    Valores aceptados:
    - 1, '1', 'Natural', 'NATURAL', 'Persona Natural' → 1
    - 2, '2', 'Juridica', 'JURIDICA', 'Persona Juridica' → 2

    Args:
        value: Valor del tipo de persona (puede ser int, str, etc.)

    Returns:
        1 para Persona Natural, 2 para Persona Jurídica
    """
    if pd.isna(value) or value is None or value == '':
        return 1  # Default: Persona Natural

    # Si ya es un número, validar que sea 1 o 2
    if isinstance(value, (int, float)):
        return 2 if int(value) == 2 else 1

    # Si es string, normalizar y comparar
    value_str = str(value).strip().upper()

    # Mapeo de valores de texto a números
    juridica_values = ['2', 'JURIDICA', 'JURÍDICA', 'PERSONA JURIDICA', 'PERSONA JURÍDICA', 'PJ']
    natural_values = ['1', 'NATURAL', 'PERSONA NATURAL', 'PN']

    if value_str in juridica_values:
        return 2
    elif value_str in natural_values:
        return 1

    # Si contiene la palabra JURIDICA o NATURAL
    if 'JURIDICA' in value_str or 'JURÍDICA' in value_str:
        return 2
    elif 'NATURAL' in value_str:
        return 1

    # Por defecto, Persona Natural
    return 1


def identificar_tipo_documento(numero_documento: str) -> str:
    """
    Identifica el tipo de documento basándose en la estructura del número.

    IMPORTANTE: Devuelve solo valores válidos del ENUM de la BD:
    'DNI', 'RUC', 'CE', 'PAS', 'CEX', 'DNI/CEDULA'

    Reglas:
    - DNI: 8 dígitos
    - RUC: 11 dígitos (empieza con 10, 15, 17, 20)
    - CE: 9 dígitos (Carnet de Extranjería)
    - CEX: 7 dígitos o menos (Carnet de Extranjería antiguo)
    - PAS: 12 dígitos o alfanumérico (Pasaporte)

    Args:
        numero_documento: Número de documento como string

    Returns:
        'DNI', 'RUC', 'CE', 'PAS', o 'CEX'
    """
    if not numero_documento:
        return 'DNI'  # Default

    # Limpiar el número (remover espacios, guiones, etc.)
    numero_limpio = str(numero_documento).strip().replace('-', '').replace(' ', '')

    if not numero_limpio:
        return 'DNI'

    # Verificar que solo contenga dígitos
    if not numero_limpio.isdigit():
        # Si tiene letras, probablemente es pasaporte
        return 'PAS'

    longitud = len(numero_limpio)

    # DNI: 8 dígitos
    if longitud == 8:
        return 'DNI'

    # RUC: 11 dígitos
    if longitud == 11:
        if numero_limpio.startswith(('10', '15', '17', '20')):
            return 'RUC'
        else:
            return 'RUC'  # Otros RUC válidos

    # Carnet de Extranjería: 9 dígitos
    if longitud == 9:
        return 'CE'

    # Carnet de Extranjería antiguo: 7 dígitos o menos
    if longitud <= 7:
        return 'CEX'

    # Pasaporte: 12 dígitos o más
    if longitud >= 12:
        return 'PAS'

    # Por defecto: DNI
    return 'DNI'


def get_or_create_uso(cursor, cnx, uso_nombre: str, commit: bool = True) -> int | None:
    """Obtiene el ID de un uso, o lo crea si no existe"""
    if not uso_nombre or uso_nombre.strip() == '':
        return None

    uso_nombre = uso_nombre.strip().upper()

    try:
        # Intentar insertar (ON DUPLICATE KEY lo maneja)
        cursor.callproc('sp_insertar_uso', [uso_nombre, 0])

        # Obtener el resultado (OUT parameter)
        for result in cursor.stored_results():
            pass

        # Recuperar el ID
        cursor.execute("SELECT @_sp_insertar_uso_1 AS uso_id")
        row = cursor.fetchone()
        if commit:
            cnx.commit()

        return row['uso_id'] if row else None
    except Exception as e:
        if commit:
            cnx.rollback()
        print(f"Error al insertar uso '{uso_nombre}': {str(e)}")
        return None


def get_or_create_marca(cursor, cnx, marca_nombre: str, commit: bool = True) -> int | None:
    """Obtiene el ID de una marca, o la crea si no existe"""
    if not marca_nombre or marca_nombre.strip() == '':
        return None

    marca_nombre = marca_nombre.strip().upper()

    try:
        # Intentar insertar (ON DUPLICATE KEY lo maneja)
        cursor.callproc('sp_insertar_marca', [marca_nombre, 0])

        # Obtener el resultado
        for result in cursor.stored_results():
            pass

        # Recuperar el ID
        cursor.execute("SELECT @_sp_insertar_marca_1 AS marca_id")
        row = cursor.fetchone()
        if commit:
            cnx.commit()

        return row['marca_id'] if row else None
    except Exception as e:
        if commit:
            cnx.rollback()
        print(f"Error al insertar marca '{marca_nombre}': {str(e)}")
        return None


def get_or_create_modelo(cursor, cnx, marca_nombre: str, modelo_nombre: str, commit: bool = True) -> tuple[int | None, int | None]:
    """Obtiene los IDs de marca y modelo, o los crea si no existen"""
    if not marca_nombre or not modelo_nombre:
        return None, None

    marca_nombre = marca_nombre.strip().upper()
    modelo_nombre = modelo_nombre.strip().upper()

    try:
        # Usar el SP que maneja marca y modelo juntos
        cursor.callproc('sp_insertar_modelo_por_nombres', [marca_nombre, modelo_nombre, 0, 0])

        # Obtener los resultados
        for result in cursor.stored_results():
            pass

        # Recuperar los IDs
        cursor.execute("SELECT @_sp_insertar_modelo_por_nombres_2 AS marca_id, @_sp_insertar_modelo_por_nombres_3 AS modelo_id")
        row = cursor.fetchone()
        if commit:
            cnx.commit()

        if row:
            return row['marca_id'], row['modelo_id']
        return None, None
    except Exception as e:
        if commit:
            cnx.rollback()
        print(f"Error al insertar marca/modelo '{marca_nombre}/{modelo_nombre}': {str(e)}")
        return None, None


def get_or_create_agente(cursor, cnx, codigo_agente: str, nombre_vendedor: str, commit: bool = True) -> int | None:
    """Obtiene el ID de un agente, o lo crea si no existe"""
    if not codigo_agente or codigo_agente.strip() == '':
        return None

    codigo_agente = codigo_agente.strip()
    nombre_vendedor = nombre_vendedor.strip() if nombre_vendedor else ''

    try:
        # Intentar insertar (ON DUPLICATE KEY lo maneja)
        cursor.callproc('sp_insertar_agente', [codigo_agente, nombre_vendedor, 0])

        # Obtener el resultado
        for result in cursor.stored_results():
            pass

        # Recuperar el ID
        cursor.execute("SELECT @_sp_insertar_agente_2 AS agente_id")
        row = cursor.fetchone()
        if commit:
            cnx.commit()

        return row['agente_id'] if row else None
    except Exception as e:
        if commit:
            cnx.rollback()
        print(f"Error al insertar agente '{codigo_agente}': {str(e)}")
        return None


def process_soat_excel(file_path: str, usuario: str, preview: bool = False) -> dict:
    """
    Procesa un archivo Excel con datos de SOAT y los carga en la BD

    Args:
        file_path: Ruta al archivo Excel
        usuario: Usuario que realiza la carga
        preview: Si es True, no guarda cambios en BD (modo simulación)

    Returns:
        dict con estructura: {
            'ok': bool,
            'clientes_nuevos': int,
            'clientes_existentes': int,
            'polizas_insertadas': int,
            'errors': list[str]
        }
    """
    try:
        # Leer Excel: forzar lectura como string para preservar ceros a la izquierda
        df = pd.read_excel(file_path, dtype=str)

        # Validar estructura
        is_valid, errors = validate_excel_structure(df)
        if not is_valid:
            return {'ok': False, 'errors': errors}

        # Contadores
        clientes_nuevos = 0
        clientes_existentes = 0
        polizas_insertadas = 0
        errors_list = []

        # Conectar a BD
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        commit_db = not preview

        # Agrupar por cliente (NUMERO_DOCUMENTO)
        clientes_procesados = set()

        for idx, row in df.iterrows():
            try:
                numero_documento = normalize_numero_documento(row['NUMERO_DOCUMENTO'])

                if not numero_documento:
                    errors_list.append(f"Fila {idx + 2}: Número de documento vacío")
                    continue

                # 1. PROCESAR CLIENTE (si no se ha procesado antes)
                if numero_documento not in clientes_procesados:
                    # Verificar si existe
                    cur.execute(
                        "SELECT idCliente FROM clientes WHERE numero_documento = %s LIMIT 1",
                        (numero_documento,)
                    )
                    cliente_existe = cur.fetchone()

                    if not cliente_existe:
                        # Insertar nuevo cliente
                        tipo_persona = normalize_tipo_persona(row.get('TIPO_PERSONA', 1))
                        telefono = str(row['TELEFONO']) if pd.notna(row['TELEFONO']) else '000000000'
                        email = str(row['EMAIL']) if pd.notna(row['EMAIL']) else f'cliente{numero_documento}@temp.com'

                        # Detectar tipo de documento si no está presente o está vacío
                        tipo_doc_excel = normalize_string(row.get('TIPO_DOCUMENTO', ''))
                        if not tipo_doc_excel:
                            tipo_doc_excel = identificar_tipo_documento(numero_documento)

                        cliente_args = (
                            normalize_string(row['NOMBRE_RAZON_SOCIAL']),
                            tipo_doc_excel,
                            numero_documento,
                            telefono,
                            telefono,  # celular
                            '',  # telefono_sec
                            normalize_string(row.get('SUBAGENTE_ABREVIACION', '')),
                            None,  # idProductor
                            email,
                            normalize_string(row['DIRECCION']),
                            normalize_string(row['DEPARTAMENTO']),
                            normalize_string(row['PROVINCIA']),
                            normalize_string(row['DISTRITO']),
                            'ACTIVO',
                            tipo_persona,
                            '',  # profesion
                            None,  # fecha_ingreso
                            None,  # fecha_nacimiento
                            None,  # licencia_num
                            None,  # licencia_venc
                            None,  # grupo_economico
                            None,  # giro_negocio
                            None,  # referencia
                            None,  # recomendado_por
                            1,     # recibir_notificaciones
                            None,  # contacto_nombre
                            None,  # contacto_email
                            None,  # contacto_telefono
                            usuario,
                            None   # pdf_path
                        )

                        try:
                            cur.execute("CALL sp_insert_cliente(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                      cliente_args)
                            while cur.nextset():
                                pass
                            if commit_db:
                                cnx.commit()
                            clientes_nuevos += 1
                        except mysql.connector.Error as err:
                            errors_list.append(f"Fila {idx + 2}: Error al insertar cliente {numero_documento}: {str(err)}")
                            cnx.rollback()
                            continue
                    else:
                        clientes_existentes += 1

                    clientes_procesados.add(numero_documento)

                # 2. PROCESAR PÓLIZA
                # Validar e insertar USO si no existe
                uso_nombre = normalize_string(row.get('USO', ''))
                if uso_nombre:
                    get_or_create_uso(cur, cnx, uso_nombre, commit=commit_db)

                # Validar e insertar MARCA y MODELO si no existen
                marca_nombre = normalize_string(row.get('MARCA', ''))
                modelo_nombre = normalize_string(row.get('MODELO', ''))
                if marca_nombre and modelo_nombre:
                    get_or_create_modelo(cur, cnx, marca_nombre, modelo_nombre, commit=commit_db)

                # Validar e insertar AGENTE si no existe (solo si ambos tienen valor)
                codigo_agente = normalize_string(row.get('COD_AGENTE', ''))
                nombre_vendedor = normalize_string(row.get('VENDEDOR', ''))
                if codigo_agente and nombre_vendedor:
                    get_or_create_agente(cur, cnx, codigo_agente, nombre_vendedor, commit=commit_db)

                # Si no hay código de agente, usar cadena vacía para evitar errores
                if not codigo_agente:
                    codigo_agente = ''

                # Construir JSON con datos del vehículo
                datos_vehiculo = {
                    'inciso': normalize_string(row.get('INCISO', '')),
                    'placa': normalize_string(row['PLACA']),
                    'clase': normalize_string(row['CLASE']),
                    'uso': uso_nombre,
                    'motor': normalize_string(row.get('MOTOR', '')),
                    'serie': normalize_string(row['SERIE']),
                    'marca': marca_nombre,
                    'modelo': modelo_nombre,
                    'anio': int(row['ANIO']) if pd.notna(row['ANIO']) else None,
                    'suma_asegurada': normalize_decimal(row['SUMA_ASEGURADA']),
                    'fecha_inclusion': normalize_date(row.get('FECINCLUSION'))
                }

                import json
                datos_vehiculo_json = json.dumps(datos_vehiculo)

                # Normalizar moneda
                moneda_map = {'S/.': 'PEN', 'S/': 'PEN', 'SOLES': 'PEN', '$': 'USD', 'DOLARES': 'USD'}
                moneda_raw = normalize_string(row.get('MONEDA_ABREVIACION', 'PEN'))
                moneda = moneda_map.get(moneda_raw, moneda_raw) if moneda_raw else 'PEN'

                poliza_args = (
                    numero_documento,
                    normalize_string(row.get('TIPO_DOC', 'EMISION')),
                    normalize_string(row.get('NOMBRE_RAZON_SOCIAL', '')),  # asegurado
                    normalize_string(row['COMPANIA_NOMBRE_CORTO']),
                    normalize_string(row['RAMO_ABREVIACION']),
                    normalize_numero_documento(row.get('POLIZA_CERTF', '')) if pd.notna(row.get('POLIZA_CERTF')) else '',
                    normalize_numero_documento(row.get('AVISO_COB', '')) if pd.notna(row.get('AVISO_COB')) else '',  # recibo
                    normalize_numero_documento(row.get('POLIZA_CERTF', '')) if pd.notna(row.get('POLIZA_CERTF')) else '',  # contrato_nro
                    normalize_numero_documento(row.get('INCISO', '')) if pd.notna(row.get('INCISO')) else '',  # nro
                    moneda,
                    normalize_date(row.get('VIGENCIA_INICIO')),  # fecha_emision = inicio_vig
                    normalize_date(row['VIGENCIA_INICIO']),
                    normalize_date(row['VIGENCIA_FIN']),
                    normalize_date(row.get('FECHA_VENCIMIENTO')),  # ultimo_dia_pago
                    normalize_date(row.get('FECHA_VENCIMIENTO')),
                    normalize_string(row.get('TIPO_POLIZA', 'ANUAL')),
                    normalize_string(row.get('ENDOSATARIO', '')),
                    normalize_string(row.get('TIPO_PAGO', 'CONTADO')),
                    normalize_string(row.get('SUBAGENTE_ABREVIACION', '')),
                    normalize_string(row.get('EJECUTIVO_ABREVIACION', '')),
                    normalize_string(row.get('AVISO_COB', '')),  # asegurada
                    normalize_string(row.get('MOTIVO', 'CARGA MASIVA SOAT')),
                    None,  # prima_comercial
                    normalize_decimal(row['PRIMA_NETA']),
                    None,  # prima_comercial_igv
                    normalize_decimal(row['PRIMA_TOTAL']),
                    normalize_decimal(row.get('PORCENTAJE_COMISION_COMPANIA')),
                    None,  # imp_compania
                    normalize_decimal(row.get('PORCENTAJE_COMISION_SUBAGENTE')),
                    None,  # imp_subagente
                    normalize_string(row.get('PRODUCTO_ABREVIACION', 'SOAT')),
                    'CANCELADO',
                    None,  # pdf_path
                    usuario,
                    datos_vehiculo_json,
                    codigo_agente  # Código de agente
                )

                try:
                    cur.execute(
                        "CALL sp_insert_poliza_soat_masivo(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        poliza_args
                    )
                    while cur.nextset():
                        pass
                    if commit_db:
                        cnx.commit()
                    polizas_insertadas += 1
                except mysql.connector.Error as err:
                    if 'Póliza ya existe' in str(err):
                        errors_list.append(f"Fila {idx + 2}: Póliza {row['POLIZA_CERTF']} ya existe para cliente {numero_documento}")
                    else:
                        errors_list.append(f"Fila {idx + 2}: Error al insertar póliza: {str(err)}")
                    # Solo hacemos rollback si estábamos intentando commitear
                    # Si estamos en preview, no commiteamos nada de todas formas
                    if commit_db:
                        cnx.rollback()
                    continue

            except Exception as e:
                errors_list.append(f"Fila {idx + 2}: Error inesperado: {str(e)}")
                continue

        # Si estamos en modo preview, hacemos rollback de todo por si acaso
        if preview:
            cnx.rollback()

        cur.close()
        cnx.close()

        return {
            'ok': True,
            'clientes_nuevos': clientes_nuevos,
            'clientes_existentes': clientes_existentes,
            'polizas_insertadas': polizas_insertadas,
            'errors': errors_list
        }

    except Exception as e:
        return {
            'ok': False,
            'errors': [f"Error al procesar archivo: {str(e)}"]
        }
