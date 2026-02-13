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
        'TIPO_PERSONA', 'NOMBRE_RAZON_SOCIAL', 'TIPO_DOCUMENTO', 'NUMERO_DOCUMENTO',
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

        # Nota: COD_AGENTE y VENDEDOR son opcionales
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


def get_or_create_uso(cursor, cnx, uso_nombre: str) -> int | None:
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
        cnx.commit()

        return row['uso_id'] if row else None
    except Exception as e:
        cnx.rollback()
        print(f"Error al insertar uso '{uso_nombre}': {str(e)}")
        return None


def get_or_create_marca(cursor, cnx, marca_nombre: str) -> int | None:
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
        cnx.commit()

        return row['marca_id'] if row else None
    except Exception as e:
        cnx.rollback()
        print(f"Error al insertar marca '{marca_nombre}': {str(e)}")
        return None


def get_or_create_modelo(cursor, cnx, marca_nombre: str, modelo_nombre: str) -> tuple[int | None, int | None]:
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
        cnx.commit()

        if row:
            return row['marca_id'], row['modelo_id']
        return None, None
    except Exception as e:
        cnx.rollback()
        print(f"Error al insertar marca/modelo '{marca_nombre}/{modelo_nombre}': {str(e)}")
        return None, None


def get_or_create_agente(cursor, cnx, codigo_agente: str, nombre_vendedor: str) -> int | None:
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
        cnx.commit()

        return row['agente_id'] if row else None
    except Exception as e:
        cnx.rollback()
        print(f"Error al insertar agente '{codigo_agente}': {str(e)}")
        return None


def process_soat_excel(file_path: str, usuario: str) -> dict:
    """
    Procesa un archivo Excel con datos de SOAT y los carga en la BD

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
        # Leer Excel
        df = pd.read_excel(file_path)

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

        # Agrupar por cliente (NUMERO_DOCUMENTO)
        clientes_procesados = set()

        for idx, row in df.iterrows():
            try:
                numero_documento = str(int(row['NUMERO_DOCUMENTO'])) if pd.notna(row['NUMERO_DOCUMENTO']) else ''

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
                        tipo_persona = int(row['TIPO_PERSONA']) if pd.notna(row['TIPO_PERSONA']) else 1
                        telefono = str(row['TELEFONO']) if pd.notna(row['TELEFONO']) else '000000000'
                        email = str(row['EMAIL']) if pd.notna(row['EMAIL']) else f'cliente{numero_documento}@temp.com'

                        cliente_args = (
                            normalize_string(row['NOMBRE_RAZON_SOCIAL']),
                            normalize_string(row['TIPO_DOCUMENTO']),
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
                    get_or_create_uso(cur, cnx, uso_nombre)

                # Validar e insertar MARCA y MODELO si no existen
                marca_nombre = normalize_string(row.get('MARCA', ''))
                modelo_nombre = normalize_string(row.get('MODELO', ''))
                if marca_nombre and modelo_nombre:
                    get_or_create_modelo(cur, cnx, marca_nombre, modelo_nombre)

                # Validar e insertar AGENTE si no existe (solo si ambos tienen valor)
                codigo_agente = normalize_string(row.get('COD_AGENTE', ''))
                nombre_vendedor = normalize_string(row.get('VENDEDOR', ''))
                if codigo_agente and nombre_vendedor:
                    get_or_create_agente(cur, cnx, codigo_agente, nombre_vendedor)

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
                    str(int(row['POLIZA_CERTF'])) if pd.notna(row['POLIZA_CERTF']) else '',
                    str(int(row.get('AVISO_COB', ''))) if pd.notna(row.get('AVISO_COB')) else '',  # recibo
                    str(int(row['POLIZA_CERTF'])) if pd.notna(row['POLIZA_CERTF']) else '',  # contrato_nro
                    str(int(row.get('INCISO', ''))) if pd.notna(row.get('INCISO')) else '',  # nro
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
                    'VIGENTE',
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
                    cnx.commit()
                    polizas_insertadas += 1
                except mysql.connector.Error as err:
                    if 'Póliza ya existe' in str(err):
                        errors_list.append(f"Fila {idx + 2}: Póliza {row['POLIZA_CERTF']} ya existe para cliente {numero_documento}")
                    else:
                        errors_list.append(f"Fila {idx + 2}: Error al insertar póliza: {str(err)}")
                    cnx.rollback()
                    continue

            except Exception as e:
                errors_list.append(f"Fila {idx + 2}: Error inesperado: {str(e)}")
                continue

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




