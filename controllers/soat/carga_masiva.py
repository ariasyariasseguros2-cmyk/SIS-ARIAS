"""
Controlador para carga masiva de pólizas SOAT desde Excel
"""
import pandas as pd
from datetime import datetime, timedelta
from models.db import get_connection, get_encrypt_key
import mysql.connector
import unicodedata
from typing import Optional, Tuple


def validate_excel_structure(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Valida que el Excel tenga las columnas requeridas"""
    required_columns = [
        'TIPO_PERSONA', 'NOMBRE_RAZON_SOCIAL', 'NUMERO_DOCUMENTO',
        'DIRECCION', 'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO',

        'POLIZA_CERTF',
        'VIGENCIA_INICIO', 'VIGENCIA_FIN', 'MONEDA_ABREVIACION',
        'PRIMA_NETA', 'PRIMA_TOTAL',

        'PLACA', 'CLASE', 'USO', 'SERIE', 'MARCA', 'MODELO', 'ANIO'
    ]

    errors = []
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        errors.append(f"Faltan las siguientes columnas: {', '.join(missing_columns)}")
        return False, errors

    return True, []

def map_excel_columns(df: pd.DataFrame) -> pd.DataFrame:
    def _strip_accents(s: str) -> str:
        return ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))

    def _normalize_header(h: str) -> str:
        if h is None:
            return ''
        s = str(h).replace('\u00A0', ' ').strip()
        # eliminar sufijo de duplicado tipo '.1', '.2'
        if '.' in s:
            base, last = s.rsplit('.', 1)
            if last.isdigit():
                s = base
        s = ' '.join(s.split())
        s = _strip_accents(s).lower()
        return s

    df2 = df.copy()
    norm_to_indices = {}
    for idx, col in enumerate(list(df2.columns)):
        key = _normalize_header(col)
        norm_to_indices.setdefault(key, []).append(idx)

    synonyms = {
        'poliza': 'POLIZA_CERTF',
        'cia'                   : 'COMPANIA_NOMBRE_CORTO',
        'cia.'                  : 'COMPANIA_NOMBRE_CORTO',
        'compania'              : 'COMPANIA_NOMBRE_CORTO',
        'compañia'              : 'COMPANIA_NOMBRE_CORTO',
        'compania nombre corto' : 'COMPANIA_NOMBRE_CORTO',
        'aseguradora'           : 'COMPANIA_NOMBRE_CORTO',
        'fec emision': 'FECHA_EMISION',
        'fec. emision': 'FECHA_EMISION',
        'fecha emision': 'FECHA_EMISION',
        'ini vigencia': 'VIGENCIA_INICIO',
        'ini.vigencia': 'VIGENCIA_INICIO',
        'fin vigencia': 'VIGENCIA_FIN',
        'fecha vencimiento': 'FECHA_VENCIMIENTO',
        'fec vencimiento': 'FECHA_VENCIMIENTO',
        'fec. vencimiento': 'FECHA_VENCIMIENTO',
        'moneda': 'MONEDA_ABREVIACION',
        'prima': 'PRIMA',
        'cod agenc': 'COD_AGENTE',
        'cod.agenc': 'COD_AGENTE',
        'vendedor': 'VENDEDOR',
        'aplicacion': 'APLICACION',
        'tipo persona': 'TIPO_PERSONA',
        'tipopersona': 'TIPO_PERSONA',
        'nombre': 'NOMBRE_RAZON_SOCIAL',
        'numero documento': 'NUMERO_DOCUMENTO',
        'direccion': 'DIRECCION',
        'departamento': 'DEPARTAMENTO',
        'provincia': 'PROVINCIA',
        'distrito': 'DISTRITO',
        'telefono': 'TELEFONO',
        'celular': 'CELULAR',
        'email': 'EMAIL',
        'prod': 'PRODUCTO_ABREVIACION',
        'producto': 'PRODUCTO_ABREVIACION',
        'tipo placa': 'TIPO_PLACA',
        'tipoplaca': 'TIPO_PLACA',
        'placa': 'PLACA',
        'uso': 'USO',
        'clase': 'CLASE',
        'marca': 'MARCA',
        'desc modelo': 'MODELO',
        'desc.modelo': 'MODELO',
        'serie': 'SERIE',
        'asientos': 'ASIENTOS',
        'anio': 'ANIO',
        'ano': 'ANIO',
        'año': 'ANIO',
        'planilla': 'PLANILLA',
        'recibo': 'RECIBO',
        'cupon': 'CUPON',
        'formulario': 'FORMULARIO',
        'estado': 'ESTADO'
    }

    for norm_key, dst in synonyms.items():
        if dst in df2.columns:
            continue
        if norm_key in norm_to_indices:
            idxs = norm_to_indices[norm_key]
            chosen_idx = idxs[-1]  # tomar la última aparición (contratante suele ir después)
            df2[dst] = df2.iloc[:, chosen_idx]

    if 'PRIMA' in df2.columns:
        if 'PRIMA_MAS_IGV' not in df2.columns:
            df2['PRIMA_MAS_IGV'] = df2['PRIMA']

        if 'PRIMA_NETA' not in df2.columns:
            df2['PRIMA_NETA'] = None
        if 'PRIMA_TOTAL' not in df2.columns:
            df2['PRIMA_TOTAL'] = df2['PRIMA']

    if 'RECIBO' in df2.columns and 'AVISO_COB' not in df2.columns:
        df2['AVISO_COB'] = df2['RECIBO']
    elif 'PLANILLA' in df2.columns and 'AVISO_COB' not in df2.columns:
        df2['AVISO_COB'] = df2['PLANILLA']
    elif 'CUPON' in df2.columns and 'AVISO_COB' not in df2.columns:
        df2['AVISO_COB'] = df2['CUPON']
    if 'VENDEDOR' in df2.columns:
        if 'SUBAGENTE_ABREVIACION' not in df2.columns:
            df2['SUBAGENTE_ABREVIACION'] = df2['VENDEDOR']
        if 'EJECUTIVO_ABREVIACION' not in df2.columns:
            df2['EJECUTIVO_ABREVIACION'] = df2['VENDEDOR']
    if 'VIGENCIA_FIN' in df2.columns and 'FECHA_VENCIMIENTO' not in df2.columns:
        df2['FECHA_VENCIMIENTO'] = df2['VIGENCIA_FIN']
    if 'PRODUCTO_ABREVIACION' not in df2.columns and 'USO' in df2.columns:
        df2['PRODUCTO_ABREVIACION'] = df2['USO']
    return df2


def _normalize_header_token(token: str) -> str:
    token = '' if token is None else str(token)
    token = token.replace('\u00A0', ' ').strip()
    token = ' '.join(token.split())
    token = ''.join(ch for ch in unicodedata.normalize('NFKD', token) if not unicodedata.combining(ch))
    return token.lower()


def _detect_header_row(df_raw: pd.DataFrame) -> Optional[int]:
    candidates = {
        'poliza', 'ini vigencia', 'ini.vigencia', 'fin vigencia', 'fec emision', 'fec. emision',
        'nombre', 'numero documento', 'direccion', 'departamento', 'provincia', 'distrito',
        'moneda', 'prima', 'vendedor', 'cod agenc', 'placa', 'uso', 'clase', 'marca',
        'desc modelo', 'desc.modelo', 'serie', 'ano', 'año', 'anio',
        'cia', 'cia.', 'compania', 'compañia', 'aseguradora',
        'recibo', 'planilla', 'cupon', 'fecha vencimiento', 'telefono', 'celular', 'email', 'prod', 'producto'
    }
    max_score = 0
    best_row = None
    check_rows = min(len(df_raw), 15)
    for i in range(check_rows):
        vals = [_normalize_header_token(x) for x in list(df_raw.iloc[i].values)]
        score = sum(1 for v in vals if v in candidates)
        if score > max_score:
            max_score = score
            best_row = i
    return best_row if (best_row is not None and max_score >= 5) else None


def load_excel_flexible(file_path: str) -> Tuple[pd.DataFrame, list[str]]:
    debug_msgs = []
    try:
        df_std = pd.read_excel(file_path, dtype=str)
        df_std = map_excel_columns(df_std)
        cols_std = [str(c) for c in getattr(df_std, 'columns', [])]
        # Heurística: si hay muchos 'Unnamed' o aparece un título de bloque como 'CERTIFICADO',
        # o si falta un canónico clave tras el mapeo, intentamos detección flexible.
        has_unnamed = sum(1 for c in cols_std if str(c).lower().startswith('unnamed')) >= max(3, len(cols_std)//3 if cols_std else 0)
        has_group_title = any(_normalize_header_token(c) in {'certificado','resp de pago','contratante','vehiculo'} for c in cols_std)
        lacks_key = not any(x in df_std.columns for x in ['POLIZA_CERTF','VIGENCIA_INICIO','NOMBRE_RAZON_SOCIAL','NUMERO_DOCUMENTO'])
        if not (has_unnamed or has_group_title or lacks_key):
            return df_std, debug_msgs
        else:
            debug_msgs.append('Se detectaron encabezados no estándar; intentando detección flexible')
    except Exception as e:
        debug_msgs.append(f'Lectura estándar falló: {e}')
    try:
        df_raw = pd.read_excel(file_path, header=None, dtype=str)
        hdr_row = _detect_header_row(df_raw)
        if hdr_row is not None:
            headers = list(df_raw.iloc[hdr_row].values)
            data = df_raw.iloc[hdr_row + 1:].reset_index(drop=True)
            # aplicar headers sólo hasta el número de columnas de data
            if len(headers) > data.shape[1]:
                headers = headers[:data.shape[1]]
            elif len(headers) < data.shape[1]:
                headers = headers + [f'Unnamed_extra_{i}' for i in range(data.shape[1] - len(headers))]
            data.columns = headers
            df = map_excel_columns(data)
            debug_msgs.append(f'Encabezado detectado en fila {hdr_row+1}')
            return df, debug_msgs
        else:
            debug_msgs.append('No se detectó fila de encabezados compatible')
    except Exception as e:
        debug_msgs.append(f'Lectura flexible falló: {e}')
    # Fallback vacío
    return pd.DataFrame(), debug_msgs

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

        # Eliminar parte de la hora si existe (split por espacio ' ')
        if ' ' in value_str:
            value_str = value_str.split(' ')[0]

        # Formato DD/MM/YYYY (convertir a YYYY-MM-DD)
        if '/' in value_str:
            parts = value_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        # Formato YYYY-MM-DD (ya está correcto)
        if '-' in value_str:
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


def _normalize_estado_token(value) -> str:
    if pd.isna(value) or value is None:
        return ''
    s = str(value).strip().upper()
    s = ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))
    s = ''.join(ch if ch.isalnum() else ' ' for ch in s)
    return ' '.join(s.split())


def _is_recibo_zero(recibo: str) -> bool:
    s = '' if recibo is None else str(recibo).strip()
    if not s:
        return False
    digits = ''.join(ch for ch in s if ch.isdigit())
    if not digits:
        return s == '0'
    try:
        return int(digits) == 0
    except Exception:
        return False


def _recibo_tiene_numero(recibo: str) -> bool:
    s = '' if recibo is None else str(recibo).strip()
    if not s:
        return False
    digits = ''.join(ch for ch in s if ch.isdigit())
    if not digits:
        return False
    try:
        return int(digits) > 0
    except Exception:
        return False


def resolver_estado_y_anulado_soat(recibo: str, estado_excel: str) -> tuple[str, int]:
    """Reglas de negocio para estado/anulado en carga masiva SOAT."""
    estado_norm = _normalize_estado_token(estado_excel)

    # Cuando recibo tiene numero, siempre se considera pagado
    if _recibo_tiene_numero(recibo):
        return 'PAGADO', 0

    # Reglas especiales cuando recibo es cero
    if _is_recibo_zero(recibo):
        if estado_norm == 'ANULADO':
            return 'ANULADO', 0
        if estado_norm == 'CANCELADO PTO VENTA':
            return 'EMISION', 1

    return 'EMISION', 0


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
        cur2 = cnx.cursor(dictionary=True)
        cur2.callproc('sp_insertar_uso', [uso_nombre, 0])
        for _ in cur2.stored_results():
            pass
        cur2.execute("SELECT @_sp_insertar_uso_1 AS uso_id")
        row = cur2.fetchone()
        cur2.close()
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
        cur2 = cnx.cursor(dictionary=True)
        cur2.callproc('sp_insertar_marca', [marca_nombre, 0])
        for _ in cur2.stored_results():
            pass
        cur2.execute("SELECT @_sp_insertar_marca_1 AS marca_id")
        row = cur2.fetchone()
        cur2.close()
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
        cur2 = cnx.cursor(dictionary=True)
        cur2.callproc('sp_insertar_modelo_por_nombres', [marca_nombre, modelo_nombre, 0, 0])
        for _ in cur2.stored_results():
            pass
        cur2.execute("SELECT @_sp_insertar_modelo_por_nombres_2 AS marca_id, @_sp_insertar_modelo_por_nombres_3 AS modelo_id")
        row = cur2.fetchone()
        cur2.close()
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


def get_or_create_clase(cursor, cnx, clase_nombre: str, commit: bool = True) -> int | None:
    """Obtiene el ID de una clase, o la crea si no existe"""
    if not clase_nombre or clase_nombre.strip() == '':
        return None

    clase_nombre = clase_nombre.strip().upper()

    try:
        cur2 = cnx.cursor(dictionary=True)
        cur2.callproc('sp_insertar_clase', [clase_nombre, 0])
        for _ in cur2.stored_results():
            pass
        cur2.execute("SELECT @_sp_insertar_clase_1 AS clase_id")
        row = cur2.fetchone()
        cur2.close()
        if commit:
            cnx.commit()
        return row['clase_id'] if row else None
    except Exception:
        # Si el SP no existe, buscar directamente por nombre
        try:
            cur2 = cnx.cursor(dictionary=True)
            cur2.execute("SELECT id FROM clases WHERE UPPER(nombre) = %s LIMIT 1", (clase_nombre,))
            row = cur2.fetchone()
            cur2.close()
            return row['id'] if row else None
        except Exception as e:
            print(f"Error al obtener clase '{clase_nombre}': {str(e)}")
            return None


def get_or_create_agente(cursor, cnx, codigo_agente: str, nombre_vendedor: str, commit: bool = True) -> int | None:
    """Obtiene el ID de un agente. Si no existe lo crea. Si ya existe, NO sobreescribe porcentajes."""
    if not codigo_agente or codigo_agente.strip() == '':
        return None

    codigo_agente = codigo_agente.strip()
    nombre_vendedor = nombre_vendedor.strip() if nombre_vendedor else codigo_agente

    try:
        cur2 = cnx.cursor(dictionary=True)
        # Primero intentar obtener el agente existente
        cur2.execute(
            "SELECT id FROM agentes WHERE codigo_agente = %s LIMIT 1",
            (codigo_agente,)
        )
        row = cur2.fetchone()
        if row:
            cur2.close()
            return row['id']
        # Si no existe, crear con porcentajes en 0 (serán configurados manualmente)
        cur2.callproc('sp_insertar_agente', [codigo_agente, nombre_vendedor, 0])
        for _ in cur2.stored_results():
            pass
        cur2.execute("SELECT @_sp_insertar_agente_2 AS agente_id")
        row = cur2.fetchone()
        cur2.close()
        if commit:
            cnx.commit()
        return row['agente_id'] if row else None
    except Exception as e:
        if commit:
            cnx.rollback()
        print(f"Error al insertar agente '{codigo_agente}': {str(e)}")
        return None


def get_tipo_soat(cnx, clase_id: int | None, uso_id: int | None) -> tuple[int | None, str | None, float]:
    """
    Consulta configuracion_soat y tipos_soat para obtener el tipo de SOAT
    según la clase y uso del vehículo.
    Retorna (tipo_soat_id, tipo_soat_nombre, tasa_aas)
    """
    if clase_id is None:
        return None, None, 0.0

    try:
        cur2 = cnx.cursor(dictionary=True)

        # Intentar con clase_id + uso_id
        if uso_id is not None:
            cur2.execute("""
                SELECT cs.tipo_soat_id, ts.nombre, ts.tasa_aas
                FROM configuracion_soat cs
                JOIN tipos_soat ts ON ts.id = cs.tipo_soat_id
                WHERE cs.clase_id = %s AND cs.uso_id = %s
                  AND cs.estado = 'Activo' AND ts.estado = 'Activo'
                LIMIT 1
            """, (clase_id, uso_id))
            row = cur2.fetchone()
            if row:
                cur2.close()
                return row['tipo_soat_id'], row['nombre'], float(row['tasa_aas'] or 0)

        # Fallback: solo clase_id
        cur2.execute("""
            SELECT cs.tipo_soat_id, ts.nombre, ts.tasa_aas
            FROM configuracion_soat cs
            JOIN tipos_soat ts ON ts.id = cs.tipo_soat_id
            WHERE cs.clase_id = %s
              AND cs.estado = 'Activo' AND ts.estado = 'Activo'
            LIMIT 1
        """, (clase_id,))
        row = cur2.fetchone()
        cur2.close()
        if row:
            return row['tipo_soat_id'], row['nombre'], float(row['tasa_aas'] or 0)
        return None, None, 0.0
    except Exception as e:
        print(f"Error en get_tipo_soat clase_id={clase_id} uso_id={uso_id}: {e}")
        return None, None, 0.0


def get_porc_subagente(cnx, codigo_agente: str, tipo_soat_nom: str | None) -> float:
    """
    Consulta SELECT * FROM agentes WHERE codigo_agente = %s
    y retorna tipo_menor o tipo_regular según el tipo de SOAT.
    """
    if not codigo_agente or codigo_agente.strip() == '':
        return 0.0

    try:
        cur2 = cnx.cursor(dictionary=True)
        cur2.execute(
            "SELECT tipo_menor, tipo_regular FROM agentes WHERE codigo_agente = %s LIMIT 1",
            (codigo_agente.strip(),)
        )
        row = cur2.fetchone()
        cur2.close()

        if not row:
            print(f"Agente no encontrado: codigo_agente='{codigo_agente}'")
            return 0.0

        if tipo_soat_nom == 'Menor':
            return float(row['tipo_menor'] or 0)
        else:
            return float(row['tipo_regular'] or 0)
    except Exception as e:
        print(f"Error en get_porc_subagente codigo_agente='{codigo_agente}': {e}")
        return 0.0


def _find_poliza_id_por_poliza_recibo(cur, poliza: str, recibo: str) -> int | None:
    poliza = '' if poliza is None else str(poliza).strip()
    recibo = '' if recibo is None else str(recibo).strip()
    if not poliza or not recibo:
        return None

    k = get_encrypt_key()
    cur.execute(
        """
        SELECT idPoliza
        FROM polizas
        WHERE activo = 1
          AND (
            CONVERT(TRIM(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(poliza), %s) AS CHAR),
                CAST(AES_DECRYPT(poliza, %s) AS CHAR),
                poliza
            )) USING utf8mb4) COLLATE utf8mb4_bin
              = CONVERT(TRIM(%s) USING utf8mb4) COLLATE utf8mb4_bin
          )
          AND (
            CONVERT(TRIM(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(recibo), %s) AS CHAR),
                CAST(AES_DECRYPT(recibo, %s) AS CHAR),
                recibo
            )) USING utf8mb4) COLLATE utf8mb4_bin
              = CONVERT(TRIM(%s) USING utf8mb4) COLLATE utf8mb4_bin
          )
        ORDER BY creado_en DESC
        LIMIT 1
        """,
        (k, k, poliza, k, k, recibo),
    )
    row = cur.fetchone()
    return int(row['idPoliza']) if row and row.get('idPoliza') is not None else None


def _poliza_recibo_existe(cur, poliza: str, recibo: str) -> bool:
    return _find_poliza_id_por_poliza_recibo(cur, poliza, recibo) is not None


def _insertar_cuota_soat(cur, row, idx: int, poliza_num: str, cupon_poliza: str, recibo_poliza: str,
                         fecha_emision_poliza: str, moneda: str, prima_mas_igv: float, usuario: str,
                         errors_list: list[str]) -> tuple[bool, bool]:
    poliza_id = _find_poliza_id_por_poliza_recibo(cur, poliza_num, cupon_poliza)
    if poliza_id is None:
        errors_list.append(
            f"Fila {idx + 2}: Advertencia - No existe combinación Póliza/Recibo en polizas (póliza={poliza_num}, recibo={cupon_poliza}). No se insertó cuota."
        )
        return False, False

    factura = (recibo_poliza or cupon_poliza or '').strip()
    if not factura:
        factura = None

    try:
        k = get_encrypt_key()
        if factura:
            cur.execute(
                """
                SELECT 1
                FROM cuotas
                WHERE activo = 1
                  AND CONVERT(TRIM(COALESCE(factura, '')) USING utf8mb4) COLLATE utf8mb4_bin
                      = CONVERT(TRIM(%s) USING utf8mb4) COLLATE utf8mb4_bin
                LIMIT 1
                """,
                (factura,),
            )
            if cur.fetchone() is not None:
                raise mysql.connector.Error(msg=f"El número de factura ya existe: {factura}")

        cur.execute(
            """
            SELECT 1
            FROM cuotas
            WHERE poliza_id = %s
              AND activo = 1
              AND (
                CONVERT(TRIM(COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(cupon), %s) AS CHAR),
                    CAST(AES_DECRYPT(cupon, %s) AS CHAR),
                    cupon
                )) USING utf8mb4) COLLATE utf8mb4_bin
                  = CONVERT(TRIM(%s) USING utf8mb4) COLLATE utf8mb4_bin
              )
            LIMIT 1
            """,
            (poliza_id, k, k, cupon_poliza),
        )
        if cur.fetchone() is not None:
            return False, True

        cur.execute(
            """
            INSERT INTO cuotas (
                poliza_id, poliza, cupon, fecha_vencimiento, moneda,
                importe, fecha_pago, factura, observacion, usuario_registro,
                numero_cuota, activo
            ) VALUES (
                %s,
                TO_BASE64(AES_ENCRYPT(%s, %s)),
                TO_BASE64(AES_ENCRYPT(%s, %s)),
                %s,%s,%s,%s,%s,%s,%s,%s, 1
            )
            """,
            (
                poliza_id,
                poliza_num,
                k,
                cupon_poliza,
                k,
                fecha_emision_poliza,
                moneda,
                prima_mas_igv,
                fecha_emision_poliza,
                factura,
                None,
                usuario,
                1,
            ),
        )

        if fecha_emision_poliza:
            cur.execute("UPDATE polizas SET estado = 'PAGADO' WHERE idPoliza = %s", (poliza_id,))

        return True, False
    except mysql.connector.Error as err_cuota:
        msg = str(err_cuota)
        if 'ya existe' in msg.lower():
            return False, True
        errors_list.append(
            f"Fila {idx + 2}: Advertencia - Error al insertar cuota para póliza {row.get('POLIZA_CERTF')}: {msg}"
        )
        return False, False


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
        df, load_debug = load_excel_flexible(file_path)

        # Validar estructura
        is_valid, errors = validate_excel_structure(df)
        if not is_valid:
            # Añadir pistas de depuración para entender encabezados reales
            head_cols = list(df.columns) if hasattr(df, 'columns') else []
            if head_cols:
                errors.append("Encabezados leídos: " + ", ".join([str(c) for c in head_cols]))
            errors.extend(load_debug)
            return {'ok': False, 'errors': errors}

        fecha_emision_min = None
        fecha_emision_max = None
        for _, r in df.iterrows():
            emision_iso = None
            emision_val = r.get('FECHA_EMISION')
            if pd.notna(emision_val):
                emision_iso = normalize_date(emision_val)
            if not emision_iso:
                vig_val = r.get('VIGENCIA_INICIO')
                if pd.notna(vig_val):
                    emision_iso = normalize_date(vig_val)
            if emision_iso:
                try:
                    d = datetime.strptime(emision_iso, '%Y-%m-%d').date()
                except Exception:
                    d = None
                if d:
                    if fecha_emision_min is None or d < fecha_emision_min:
                        fecha_emision_min = d
                    if fecha_emision_max is None or d > fecha_emision_max:
                        fecha_emision_max = d

        fecha_emision_excel_min = fecha_emision_min.strftime('%d/%m/%Y') if fecha_emision_min else None
        fecha_emision_excel_max = fecha_emision_max.strftime('%d/%m/%Y') if fecha_emision_max else None

        # Contadores
        clientes_nuevos = 0
        clientes_existentes = 0
        polizas_insertadas = 0
        polizas_existentes = 0
        cuotas_insertadas = 0
        cuotas_existentes = 0
        errors_list = []

        # Conectar a BD
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        commit_db = not preview

        if commit_db:
            try:
                # Obtener el siguiente ID basado en el máximo actual
                cur.execute("SELECT COALESCE(MAX(idPoliza),0)+1 AS next_id FROM polizas")
                r1 = cur.fetchone()
                expected_next = int(r1['next_id']) if r1 and r1.get('next_id') is not None else 1
                
                # Forzar el reinicio del AUTO_INCREMENT al valor correcto (rellena huecos al final si se borraron registros)
                # Esto asegura que si la tabla está vacía, empiece en 1.
                cur.execute(f"ALTER TABLE polizas AUTO_INCREMENT = {expected_next}")
                cnx.commit()
            except Exception as e:
                # Si falla (ej. permisos), continuamos sin detener la carga, pero lo logueamos
                print(f"Advertencia: No se pudo resetear AUTO_INCREMENT: {e}")
                pass

        clientes_procesados = set()
        doc_map = {}

        for idx, row in df.iterrows():
            try:
                numero_documento_excel = normalize_numero_documento(row['NUMERO_DOCUMENTO'])
                razon_social = normalize_string(row.get('NOMBRE_RAZON_SOCIAL', ''))

                if not numero_documento_excel:
                    errors_list.append(f"Fila {idx + 2}: Número de documento vacío")
                    continue

                numero_documento = doc_map.get(numero_documento_excel) or numero_documento_excel

                tipo_doc_excel = normalize_string(row.get('TIPO_DOCUMENTO', ''))
                if not tipo_doc_excel:
                    tipo_doc_excel = identificar_tipo_documento(numero_documento_excel)

                # 1. PROCESAR CLIENTE (si no se ha procesado antes)
                if numero_documento_excel not in clientes_procesados:
                    # Verificar si existe (considerando campos cifrados)
                    k = get_encrypt_key()
                    cur.execute(
                        """
                        SELECT
                            idCliente,
                            COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                                CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                                numero_documento
                            ) AS numero_documento_plain
                        FROM clientes
                        WHERE (
                            CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR) = %s
                            OR CAST(AES_DECRYPT(numero_documento, %s) AS CHAR) = %s
                            OR numero_documento = %s
                            OR (
                                TRIM(
                                    COALESCE(
                                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                                        razon_social
                                    )
                                ) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                                AND (%s = '' OR tipo_documento = %s)
                            )
                        )
                        AND activo = 1 
                        LIMIT 1
                        """,
                        (
                            k, k,
                            k, numero_documento, k, numero_documento, numero_documento,
                            k, k, razon_social, tipo_doc_excel, tipo_doc_excel
                        )
                    )
                    cliente_existe = cur.fetchone()

                    if not cliente_existe:
                        # Insertar nuevo cliente
                        tipo_persona = normalize_tipo_persona(row.get('TIPO_PERSONA', 1))
                        telefono = str(row['TELEFONO']) if pd.notna(row.get('TELEFONO')) else (str(row['CELULAR']) if pd.notna(row.get('CELULAR')) else '000000000')
                        celular = str(row['CELULAR']) if pd.notna(row.get('CELULAR')) else telefono
                        email = str(row['EMAIL']) if pd.notna(row.get('EMAIL')) else f'cliente{numero_documento}@temp.com'

                        cliente_args = (
                            normalize_string(row['NOMBRE_RAZON_SOCIAL']),
                            tipo_doc_excel,
                            numero_documento,
                            telefono,
                            celular,
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
                            usuario
                        )

                        try:
                            cur.execute("CALL sp_insert_cliente(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                      cliente_args)
                            try:
                                cur.fetchall()
                            except Exception:
                                pass
                            while cur.nextset():
                                try:
                                    cur.fetchall()
                                except Exception:
                                    pass
                            if commit_db:
                                cnx.commit()
                            clientes_nuevos += 1
                            try:
                                cur.execute(
                                    """
                                    SELECT idCliente
                                    FROM clientes
                                    WHERE (
                                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR) = %s
                                        OR CAST(AES_DECRYPT(numero_documento, %s) AS CHAR) = %s
                                        OR numero_documento = %s
                                    )
                                    AND activo = 1
                                    LIMIT 1
                                    """,
                                    (k, numero_documento, k, numero_documento, numero_documento),
                                )
                                cliente_existe = cur.fetchone()
                            except Exception:
                                cliente_existe = None
                        except mysql.connector.Error as err:
                            errors_list.append(f"Fila {idx + 2}: Error al insertar cliente {numero_documento}: {str(err)}")
                            cnx.rollback()
                            continue
                    else:
                        clientes_existentes += 1

                    numero_doc_cliente = normalize_numero_documento((cliente_existe or {}).get('numero_documento_plain') or numero_documento)
                    if numero_doc_cliente and numero_doc_cliente != numero_documento:
                        errors_list.append(f"Fila {idx + 2}: Advertencia - Cliente ya existe por razón social, se usará N° doc {numero_doc_cliente} en póliza")
                        numero_documento = numero_doc_cliente
                    doc_map[numero_documento_excel] = numero_documento

                    clientes_procesados.add(numero_documento_excel)

                # 2. PROCESAR PÓLIZA
                # Validar e insertar USO si no existe, y obtener su ID
                uso_nombre = normalize_string(row.get('USO', ''))
                uso_id = None
                if uso_nombre:
                    uso_id = get_or_create_uso(cur, cnx, uso_nombre, commit=commit_db)

                # Validar e insertar MARCA y MODELO si no existen
                marca_nombre = normalize_string(row.get('MARCA', ''))
                modelo_nombre = normalize_string(row.get('MODELO', ''))
                if marca_nombre and modelo_nombre:
                    get_or_create_modelo(cur, cnx, marca_nombre, modelo_nombre, commit=commit_db)

                # Resolver clase_id desde nombre de clase (para cálculo de comisiones en SP)
                clase_nombre = normalize_string(row.get('CLASE', ''))
                clase_id = None
                if clase_nombre:
                    clase_id = get_or_create_clase(cur, cnx, clase_nombre, commit=commit_db)

                # Validar e insertar AGENTE si no existe (solo si tiene código)
                raw_cod = row.get('COD_AGENTE', '')
                raw_vend = row.get('VENDEDOR', '')
                print(f"[DEBUG] COD_AGENTE raw='{raw_cod}' | VENDEDOR raw='{raw_vend}' | cols={[c for c in row.index if 'COD' in str(c).upper() or 'AGENC' in str(c).upper() or 'VEND' in str(c).upper()]}")
                codigo_agente = normalize_numero_documento(raw_cod)
                nombre_vendedor = normalize_string(raw_vend)
                print(f"[DEBUG] codigo_agente normalizado='{codigo_agente}'")
                if codigo_agente:
                    get_or_create_agente(cur, cnx, codigo_agente, nombre_vendedor, commit=commit_db)

                # Si no hay código de agente, usar cadena vacía para evitar errores
                if not codigo_agente:
                    codigo_agente = ''

                # ── Normalizar primas (necesario antes del cálculo de comisiones) ──
                prima_mas_igv = normalize_decimal(row.get('PRIMA_MAS_IGV'))
                prima_neta = normalize_decimal(row.get('PRIMA_NETA'))

                if prima_neta is None and prima_mas_igv is not None:
                    prima_neta = round(prima_mas_igv / 1.2154, 2)
                elif prima_neta is None:
                    prima_neta = 0.0

                if prima_mas_igv is None:
                    prima_mas_igv = 0.0

                # ── Calcular comisiones en Python directamente ──────────────
                # 1. Obtener tipo SOAT desde configuracion_soat
                _, tipo_soat_nom, tasa_aas = get_tipo_soat(cnx, clase_id, uso_id)

                # 2. porc_compania e imp_compania
                # Lógica para manejar tasas: si <= 1.0 se asume factor (ej: 0.10 = 10%), si > 1.0 se asume porcentaje (ej: 10 = 10%)
                porc_compania = round(tasa_aas, 2)
                factor_cia = porc_compania if porc_compania <= 1.0 else (porc_compania / 100.0)
                imp_compania  = round(factor_cia * prima_neta, 2)

                # 3. porc_subagente desde tabla agentes directamente
                porc_subagente = get_porc_subagente(cnx, codigo_agente, tipo_soat_nom)
                factor_sub = porc_subagente if porc_subagente <= 1.0 else (porc_subagente / 100.0)
                imp_subagente  = round(factor_sub * imp_compania, 2)

                print(f"[COMISION] cod={codigo_agente} tipo_soat={tipo_soat_nom} "
                      f"porc_cia={porc_compania} imp_cia={imp_compania} "
                      f"porc_sub={porc_subagente} imp_sub={imp_subagente}")

                # Construir JSON con datos del vehículo
                datos_vehiculo = {
                    'inciso': normalize_string(row.get('INCISO', '')),
                    'placa': normalize_string(row.get('PLACA', '')),
                    'clase': clase_nombre,
                    'uso': uso_nombre,
                    'motor': normalize_string(row.get('MOTOR', '')),
                    'serie': normalize_string(row.get('SERIE', '')),
                    'marca': marca_nombre,
                    'modelo': modelo_nombre,
                    'anio': int(row['ANIO']) if pd.notna(row.get('ANIO')) else None,
                    'suma_asegurada': normalize_decimal(row.get('SUMA_ASEGURADA')),
                    'fecha_inclusion': normalize_date(row.get('FECINCLUSION'))
                }

                import json
                datos_vehiculo_json = json.dumps(datos_vehiculo)

                # Normalizar moneda
                moneda_map = {'S/.': 'S/', 'S/': 'S/', 'SOLES': 'S/', 'PEN': 'S/', '$': '$', 'USD': '$', 'DOLARES': '$', 'DÓLARES': '$'}
                moneda_raw = normalize_string(row.get('MONEDA_ABREVIACION', 'S/'))
                moneda = moneda_map.get(moneda_raw, 'S/')

                # Validar que la compañía no venga vacía (advertencia, no bloquea)
                compania_nombre_corto = normalize_string(row.get('COMPANIA_NOMBRE_CORTO', ''))
                if not compania_nombre_corto:
                    errors_list.append(f"Fila {idx + 2}: Advertencia - Compañía no encontrada (columna CIA/COMPAÑIA vacía o no detectada)")

                fecha_emision_poliza = normalize_date(row.get('FECHA_EMISION')) if pd.notna(row.get('FECHA_EMISION')) else normalize_date(row.get('VIGENCIA_INICIO'))
                if not fecha_emision_poliza:
                    fecha_emision_poliza = datetime.today().strftime('%Y-%m-%d')
                fecha_vencimiento_poliza = fecha_emision_poliza

                recibo_poliza = normalize_numero_documento(row.get('AVISO_COB', '')) if pd.notna(row.get('AVISO_COB')) else ''
                cupon_poliza = normalize_numero_documento(row.get('CUPON', '')) if pd.notna(row.get('CUPON')) else ''
                if not cupon_poliza:
                    cupon_poliza = recibo_poliza
                # Para reglas de estado/anulado, priorizamos PLANILLA; si no viene, usamos AVISO_COB.
                referencia_estado_raw = row.get('PLANILLA') if pd.notna(row.get('PLANILLA')) else row.get('AVISO_COB', '')
                referencia_estado = normalize_numero_documento(referencia_estado_raw) if pd.notna(referencia_estado_raw) else ''
                estado_excel = normalize_string(row.get('ESTADO', ''))
                estado_poliza, anulado_poliza = resolver_estado_y_anulado_soat(referencia_estado, estado_excel)
                producto_abreviacion = normalize_string(row.get('PRODUCTO_ABREVIACION', ''))

                poliza_num = normalize_numero_documento(row.get('POLIZA_CERTF', '')) if pd.notna(row.get('POLIZA_CERTF')) else ''
                if poliza_num and cupon_poliza and _poliza_recibo_existe(cur, poliza_num, cupon_poliza):
                    polizas_existentes += 1
                    inserted, existed = _insertar_cuota_soat(
                        cur=cur,
                        row=row,
                        idx=idx,
                        poliza_num=poliza_num,
                        cupon_poliza=cupon_poliza,
                        recibo_poliza=recibo_poliza,
                        fecha_emision_poliza=fecha_emision_poliza,
                        moneda=moneda,
                        prima_mas_igv=prima_mas_igv,
                        usuario=usuario,
                        errors_list=errors_list,
                    )
                    if inserted:
                        cuotas_insertadas += 1
                    elif existed:
                        cuotas_existentes += 1
                        errors_list.append(f"Fila {idx + 2}: Advertencia - Cuota ya existe para póliza {row.get('POLIZA_CERTF')}: {cupon_poliza}")
                    if preview:
                        continue
                    cnx.commit()
                    continue

                poliza_args = (
                    numero_documento,
                    normalize_string(row.get('TIPO_DOC', 'EMISION')),
                    normalize_string(row.get('NOMBRE_RAZON_SOCIAL', '')),  # asegurado
                    compania_nombre_corto,
                    normalize_string(row.get('RAMO_ABREVIACION', 'SOAT')),
                    poliza_num,
                    cupon_poliza,  # recibo
                    poliza_num,  # contrato_nro
                    normalize_numero_documento(row.get('INCISO', '')) if pd.notna(row.get('INCISO')) else '',  # nro
                    moneda,
                    fecha_emision_poliza,
                    normalize_date(row['VIGENCIA_INICIO']),
                    normalize_date(row['VIGENCIA_FIN']),
                    fecha_vencimiento_poliza,  # ultimo_dia_pago
                    fecha_vencimiento_poliza,
                    normalize_string(row.get('TIPO_POLIZA', 'ANUAL')),
                    normalize_string(row.get('ENDOSATARIO', '')),
                    normalize_string(row.get('TIPO_PAGO', 'CONTADO')),
                    normalize_string(row.get('SUBAGENTE_ABREVIACION', '')),
                    normalize_string(row.get('EJECUTIVO_ABREVIACION', '')),
                    '', # asegurada
                    (normalize_string(row.get('APLICACION', '')) or normalize_string(row.get('MOTIVO', ''))),
                    prima_neta,
                    prima_neta,
                    prima_mas_igv,
                    prima_mas_igv,
                    porc_compania,   # calculado en Python
                    imp_compania,    # calculado en Python
                    porc_subagente,  # calculado en Python desde tabla agentes
                    imp_subagente,   # calculado en Python
                    producto_abreviacion,
                    estado_poliza,
                    None,  # pdf_path
                    usuario,
                    datos_vehiculo_json,
                    codigo_agente
                )

                try:
                    cur.execute(
                        "CALL sp_insert_poliza_soat_masivo(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        poliza_args
                    )
                    # Consumir todos los resultsets que devuelve el SP (incluido el SELECT final)
                    poliza_id_insertada = None
                    try:
                        rows = cur.fetchall()
                        if rows and isinstance(rows[0], dict) and 'id' in rows[0]:
                            poliza_id_insertada = rows[0]['id']
                    except Exception:
                        pass
                    while cur.nextset():
                        try:
                            rows = cur.fetchall()
                            if poliza_id_insertada is None and rows and isinstance(rows[0], dict) and 'id' in rows[0]:
                                poliza_id_insertada = rows[0]['id']
                        except Exception:
                            pass

                    if poliza_id_insertada is not None:
                        cur.execute(
                            "UPDATE polizas SET estado = %s, anulado = %s WHERE idPoliza = %s",
                            (estado_poliza, anulado_poliza, poliza_id_insertada)
                        )
                        inserted, existed = _insertar_cuota_soat(
                            cur=cur,
                            row=row,
                            idx=idx,
                            poliza_num=poliza_num,
                            cupon_poliza=cupon_poliza,
                            recibo_poliza=recibo_poliza,
                            fecha_emision_poliza=fecha_emision_poliza,
                            moneda=moneda,
                            prima_mas_igv=prima_mas_igv,
                            usuario=usuario,
                            errors_list=errors_list,
                        )
                        if inserted:
                            cuotas_insertadas += 1
                        elif existed:
                            cuotas_existentes += 1
                            errors_list.append(f"Fila {idx + 2}: Advertencia - Cuota ya existe para póliza {row.get('POLIZA_CERTF')}: {cupon_poliza}")

                    if commit_db:
                        cnx.commit()
                    polizas_insertadas += 1
                except mysql.connector.Error as err:
                    if 'Póliza ya existe' in str(err):
                        polizas_existentes += 1
                        if commit_db:
                            try:
                                cnx.rollback()
                            except Exception:
                                pass
                        inserted, existed = _insertar_cuota_soat(
                            cur=cur,
                            row=row,
                            idx=idx,
                            poliza_num=poliza_num,
                            cupon_poliza=cupon_poliza,
                            recibo_poliza=recibo_poliza,
                            fecha_emision_poliza=fecha_emision_poliza,
                            moneda=moneda,
                            prima_mas_igv=prima_mas_igv,
                            usuario=usuario,
                            errors_list=errors_list,
                        )
                        if inserted:
                            cuotas_insertadas += 1
                            if commit_db:
                                cnx.commit()
                        elif existed:
                            cuotas_existentes += 1
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
            'polizas_existentes': polizas_existentes,
            'cuotas_insertadas': cuotas_insertadas,
            'cuotas_existentes': cuotas_existentes,
            'fecha_emision_excel_min': fecha_emision_excel_min,
            'fecha_emision_excel_max': fecha_emision_excel_max,
            'errors': errors_list
        }

    except Exception as e:
        return {
            'ok': False,
            'errors': [f"Error al procesar archivo: {str(e)}"]
        }


def get_ultima_fecha_emision_soat() -> dict:
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("""
            SELECT MAX(fecha_emision) AS max_fecha
            FROM polizas
            WHERE UPPER(TRIM(ramo)) = 'SOAT'
              AND activo = 1
              AND (anulado = 0 OR anulado IS NULL)
        """)
        row = cur.fetchone()
        cur.close()
        cnx.close()

        max_fecha = row.get('max_fecha') if row else None
        if not max_fecha:
            return {
                'ultima_fecha_emision_bd': None,
                'cargar_desde_sugerido': None
            }

        if isinstance(max_fecha, datetime):
            max_fecha = max_fecha.date()

        return {
            'ultima_fecha_emision_bd': max_fecha.strftime('%d/%m/%Y'),
            'cargar_desde_sugerido': (max_fecha + timedelta(days=1)).strftime('%d/%m/%Y')
        }
    except Exception:
        return {
            'ultima_fecha_emision_bd': None,
            'cargar_desde_sugerido': None
        }
