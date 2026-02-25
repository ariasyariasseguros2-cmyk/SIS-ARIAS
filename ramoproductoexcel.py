import os
import math
import pandas as pd
from models.db import get_connection


EXCEL_FILENAME = "RamoProducto.xlsx"


def _get_excel_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, EXCEL_FILENAME)


def _normalize_number(value):
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    is_percentage = "%" in text
    text = text.replace(",", ".").replace("%", "")
    try:
        val = float(text)
        return val / 100.0 if is_percentage else val
    except Exception:
        return None


def _normalize_text(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _normalize_estado(value):
    raw = _normalize_text(value)
    if not raw:
        return "Activo"
    lower = raw.lower()
    if lower.startswith("act"):
        return "Activo"
    if lower.startswith("ina"):
        return "Inactivo"
    return "Activo"

def _normalize_estado_activado(value):
    raw = _normalize_text(value)
    if not raw:
        return "Activado"
    lower = raw.lower()
    if lower.startswith("act"):
        return "Activado"
    if lower.startswith("ina"):
        return "Inactivo"
    return "Activado"


def _load_df_with_names(xls: pd.ExcelFile, sheet: str, usecols: str, names: list[str], skiprows: int = 1) -> pd.DataFrame:
    try:
        df = pd.read_excel(
            xls,
            sheet_name=sheet,
            header=None,
            skiprows=skiprows,
            usecols=usecols,
            names=names,
        )
    except ValueError:
        # Hoja no existe
        return pd.DataFrame(columns=names)
    if not df.empty:
        first_col_name = names[0]
        first_val = df.iloc[0].get(first_col_name)
        if isinstance(first_val, str) and first_val.strip().lower().startswith("nombre"):
            df = df.iloc[1:].reset_index(drop=True)
    return df


def _load_dataframe() -> pd.DataFrame:
    path = _get_excel_path()
    xls = pd.ExcelFile(path)
    return _load_df_with_names(
        xls,
        sheet="RamoProducto",
        usecols="A:S",
        names=[
            "ramo_nombre",
            "ramo_abreviacion",
            "ramo_codigo",
            "ramo_grupo",
            "ramo_estado",
            "blank1",
            "producto",
            "producto_abrev",
            "producto_codigo",
            "pos_eps",
            "pos_vsr",
            "pos_sr",
            "pacifico",
            "sanitas",
            "protecta",
            "mapfre",
            "crecer",
            "ohio_natural",
            "factor",
        ],
    )


def _upsert_ramos_y_productos(conn, df: pd.DataFrame) -> None:
    cursor = conn.cursor()
    try:
        ramo_ids = {}
        for _, row in df.iterrows():
            ramo_nombre = (row.get("ramo_nombre") or "").strip()
            if not ramo_nombre:
                continue
            if ramo_nombre not in ramo_ids:
                ramo_abreviacion = _normalize_text(row.get("ramo_abreviacion"))
                ramo_codigo = _normalize_text(row.get("ramo_codigo"))
                ramo_grupo = _normalize_text(row.get("ramo_grupo"))
                ramo_estado = _normalize_estado(row.get("ramo_estado"))
                sql_ramo = """
                    INSERT INTO ramos (nombre, abreviacion, codigo, grupo, estado)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE idRamo = LAST_INSERT_ID(idRamo)
                """
                cursor.execute(
                    sql_ramo,
                    (
                        ramo_nombre.strip(),
                        ramo_abreviacion,
                        ramo_codigo,
                        ramo_grupo,
                        ramo_estado,
                    ),
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                ramo_id = cursor.fetchone()[0]
                ramo_ids[ramo_nombre] = ramo_id
        conn.commit()
        cursor.close()
        cursor = conn.cursor()
        for _, row in df.iterrows():
            ramo_nombre = _normalize_text(row.get("ramo_nombre")) or ""
            producto_nombre = _normalize_text(row.get("producto")) or _normalize_text(row.get("producto_abrev")) or ""
            if not ramo_nombre or not producto_nombre:
                continue
            ramo_id = ramo_ids.get(ramo_nombre)
            if not ramo_id:
                continue
            sql_producto = """
                INSERT INTO productos (idRamo, nombre)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE id_producto = LAST_INSERT_ID(id_producto)
            """
            cursor.execute(sql_producto, (ramo_id, producto_nombre))
        conn.commit()
    finally:
        cursor.close()


def _insert_comisiones_temp(conn, df: pd.DataFrame) -> None:
    # Verificar que exista la tabla comisiones_temp
    cursor = conn.cursor()
    try:
        try:
            cursor.execute("SHOW TABLES LIKE 'comisiones_temp'")
            exists = cursor.fetchone()
            if not exists:
                return
        except Exception:
            return
        cursor.execute("TRUNCATE TABLE comisiones_temp")
        rows = []
        for _, row in df.iterrows():
            producto_nombre = _normalize_text(row.get("producto")) or _normalize_text(row.get("producto_abrev"))
            rows.append(
                [
                    _normalize_text(row.get("ramo_nombre")),
                    _normalize_text(row.get("ramo_abreviacion")),
                    _normalize_text(row.get("ramo_codigo")),
                    _normalize_text(row.get("ramo_grupo")),
                    _normalize_text(row.get("ramo_estado")),
                    producto_nombre,
                    _normalize_text(row.get("producto_abrev")),
                    _normalize_text(row.get("producto_codigo")),
                    _normalize_number(row.get("pos_eps")),
                    _normalize_number(row.get("pos_vsr")),
                    _normalize_number(row.get("pos_sr")),
                    _normalize_number(row.get("pacifico")),
                    _normalize_number(row.get("sanitas")),
                    _normalize_number(row.get("protecta")),
                    _normalize_number(row.get("mapfre")),
                    _normalize_number(row.get("crecer")),
                    _normalize_number(row.get("ohio_natural")),
                    _normalize_number(row.get("factor")),
                ]
            )
        insert_sql = """
            INSERT INTO comisiones_temp (
                ramo_nombre,
                ramo_abreviacion,
                ramo_codigo,
                ramo_grupo,
                ramo_estado,
                producto,
                producto_abrev,
                producto_codigo,
                pos_eps,
                pos_vsr,
                pos_sr,
                pacifico,
                sanitas,
                protecta,
                mapfre,
                crecer,
                ohio_natural,
                factor
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """
        cursor.executemany(insert_sql, rows)
        conn.commit()
    finally:
        cursor.close()


def _refrescar_comisiones(conn) -> None:
    cursor = conn.cursor()
    try:
        # Verificar existencia de tablas
        try:
            cursor.execute("SHOW TABLES LIKE 'comisiones'")
            com_exists = cursor.fetchone()
            cursor.execute("SHOW TABLES LIKE 'comisiones_temp'")
            temp_exists = cursor.fetchone()
            if not com_exists or not temp_exists:
                return
        except Exception:
            return
        cursor.execute("TRUNCATE TABLE comisiones")
        sql_insert = """
            INSERT INTO comisiones (id_producto, id_compania, comision, factor)
            SELECT p.id_producto, c.id_compania, t.pos_eps, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'POS EPS'
            WHERE t.pos_eps IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.pos_vsr, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'POS VSR'
            WHERE t.pos_vsr IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.pos_sr, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'POS SR'
            WHERE t.pos_sr IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.pacifico, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'PACIFICO'
            WHERE t.pacifico IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.sanitas, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'SANITAS'
            WHERE t.sanitas IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.protecta, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'PROTECTA'
            WHERE t.protecta IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.mapfre, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'MAPFRE'
            WHERE t.mapfre IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.crecer, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'CRECER'
            WHERE t.crecer IS NOT NULL
            UNION ALL
            SELECT p.id_producto, c.id_compania, t.ohio_natural, t.factor
            FROM comisiones_temp t
            JOIN productos p ON p.nombre = t.producto
            JOIN companias c ON c.nombre = 'OHIO NATURAL'
            WHERE t.ohio_natural IS NOT NULL
        """
        cursor.execute(sql_insert)
        conn.commit()
    finally:
        cursor.close()


def _upsert_companias(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="compania",
        usecols="A:E",
        names=["nombre", "nombre_corto", "ruc", "tel1", "central_emergencia"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            nombre_corto = _normalize_text(row.get("nombre_corto"))
            ruc = _normalize_text(row.get("ruc"))
            tel1 = _normalize_text(row.get("tel1"))
            central = _normalize_text(row.get("central_emergencia"))
            # Evitar duplicados por nombre/nombre_corto
            cursor.execute(
                "SELECT id_compania FROM companias WHERE nombre = %s OR nombre_corto = %s",
                (nombre, nombre_corto),
            )
            rowid = cursor.fetchone()
            if rowid:
                # Opcional: actualizar datos cambiantes
                cursor.execute(
                    "UPDATE companias SET nombre=%s, nombre_corto=%s, ruc=%s, tel1=%s, central_emergencia=%s WHERE id_compania=%s",
                    (nombre, nombre_corto, ruc, tel1, central, rowid[0]),
                )
            else:
                cursor.execute(
                    "INSERT INTO companias (nombre, nombre_corto, ruc, tel1, central_emergencia) VALUES (%s, %s, %s, %s, %s)",
                    (nombre, nombre_corto, ruc, tel1, central),
                )
        conn.commit()
    finally:
        cursor.close()


def _upsert_ejecutivos(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="ejecutivo",
        usecols="A:C",
        names=["nombre", "abreviacion", "grupo"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            abreviacion = _normalize_text(row.get("abreviacion"))
            grupo = _normalize_text(row.get("grupo"))
            cursor.execute("SELECT idEjecutivo FROM ejecutivos WHERE nombre = %s", (nombre,))
            rowid = cursor.fetchone()
            if rowid:
                cursor.execute(
                    "UPDATE ejecutivos SET abreviacion=%s, grupo=%s WHERE idEjecutivo=%s",
                    (abreviacion, grupo, rowid[0]),
                )
            else:
                cursor.execute(
                    "INSERT INTO ejecutivos (nombre, abreviacion, grupo) VALUES (%s, %s, %s)",
                    (nombre, abreviacion, grupo),
                )
        conn.commit()
    finally:
        cursor.close()


def _upsert_endosatarios(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Endosatarios",
        usecols="A:B",
        names=["nombre", "accion_o_estado"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            # No todos los archivos tienen estado; default 'Activo'
            estado = _normalize_estado(row.get("accion_o_estado")) if _normalize_text(row.get("accion_o_estado")) else "Activo"
            cursor.execute("SELECT idEndosatario FROM endosatarios WHERE nombre = %s", (nombre,))
            rowid = cursor.fetchone()
            if rowid:
                cursor.execute(
                    "UPDATE endosatarios SET estado=%s WHERE idEndosatario=%s",
                    (estado, rowid[0]),
                )
            else:
                cursor.execute(
                    "INSERT INTO endosatarios (nombre, estado) VALUES (%s, %s)",
                    (nombre, estado),
                )
        conn.commit()
    finally:
        cursor.close()


def _upsert_clases(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Clases Veh",
        usecols="A:C",
        names=["nombre", "costo_soat", "estado"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            costo = _normalize_number(row.get("costo_soat")) or 0
            estado = _normalize_estado_activado(row.get("estado"))
            cursor.execute(
                """
                INSERT INTO clases (nombre, costo_soat, estado)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE costo_soat=VALUES(costo_soat), estado=VALUES(estado)
                """,
                (nombre, costo, estado),
            )
        conn.commit()
    finally:
        cursor.close()


def _upsert_marcas(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Marca",
        usecols="A:C",
        names=["nombre", "blank1", "estado"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            estado = _normalize_estado_activado(row.get("estado"))
            cursor.execute(
                """
                INSERT INTO marcas (nombre, estado)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE estado=VALUES(estado)
                """,
                (nombre, estado),
            )
        conn.commit()
    finally:
        cursor.close()


def _upsert_subagentes(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="SubAgent",
        usecols="A:B",
        names=["nombre", "abreviacion"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            abreviacion = _normalize_text(row.get("abreviacion"))
            cursor.execute("SELECT idProductor FROM SubAgente WHERE nombre = %s", (nombre,))
            rowid = cursor.fetchone()
            if rowid:
                cursor.execute(
                    "UPDATE SubAgente SET abreviacion=%s WHERE idProductor=%s",
                    (abreviacion, rowid[0]),
                )
            else:
                cursor.execute(
                    "INSERT INTO SubAgente (nombre, abreviacion) VALUES (%s, %s)",
                    (nombre, abreviacion),
                )
        conn.commit()
    finally:
        cursor.close()


def _upsert_usos(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Uso",
        usecols="A:C",
        names=["nombre", "estado", "accion"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            if not nombre:
                continue
            estado = _normalize_estado_activado(row.get("estado"))
            cursor.execute(
                """
                INSERT INTO usos (nombre, estado)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE estado=VALUES(estado)
                """,
                (nombre, estado),
            )
        conn.commit()
    finally:
        cursor.close()


def _upsert_ajustadores(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Ajustadores",
        usecols="A:C",
        names=["nombre", "abreviacion", "codigo"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            codigo = _normalize_text(row.get("codigo"))
            if not nombre or not codigo:
                continue
            abreviacion = _normalize_text(row.get("abreviacion"))
            cursor.execute(
                """
                INSERT INTO ajustadores (nombre, abreviacion, codigo)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), abreviacion=VALUES(abreviacion)
                """,
                (nombre, abreviacion, codigo),
            )
        conn.commit()
    finally:
        cursor.close()


def _upsert_modelos(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Modelo",
        usecols="A:C",
        names=["marca_nombre", "nombre", "accion"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            marca_nombre = _normalize_text(row.get("marca_nombre"))
            nombre_modelo = _normalize_text(row.get("nombre"))
            if not marca_nombre or not nombre_modelo:
                continue
            estado = _normalize_estado_activado(row.get("accion"))
            cursor.execute("SELECT id FROM marcas WHERE nombre = %s", (marca_nombre,))
            res = cursor.fetchone()
            if res:
                marca_id = res[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO marcas (nombre, estado)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE estado=VALUES(estado)
                    """,
                    (marca_nombre, estado),
                )
                cursor.execute("SELECT id FROM marcas WHERE nombre = %s", (marca_nombre,))
                marca_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO modelos (marca_id, nombre, estado)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE estado=VALUES(estado)
                """,
                (marca_id, nombre_modelo, estado),
            )
        conn.commit()
    finally:
        cursor.close()


def _upsert_usuarios(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Usuario",
        usecols="A:C",
        names=["nombre", "email", "privilegio"],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            nombre = _normalize_text(row.get("nombre"))
            email = _normalize_text(row.get("email"))
            if not email:
                continue
            username = email.lower()
            password = ""
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            res = cursor.fetchone()
            if res:
                cursor.execute(
                    "UPDATE usuarios SET nombre=%s WHERE id=%s",
                    (nombre or username, res[0]),
                )
            else:
                cursor.execute(
                    "INSERT INTO usuarios (username, password, nombre, estado) VALUES (%s, %s, %s, 1)",
                    (username, password, nombre or username),
                )
        conn.commit()
    finally:
        cursor.close()


def _parse_cliente_tipo_doc(value: str) -> str:
    v = (_normalize_text(value) or "").upper()
    if "RUC" in v:
        return "RUC"
    if "DNI" in v and "CED" in v:
        return "DNI/CEDULA"
    if "DNI" in v:
        return "DNI"
    if "CE" in v:
        return "CE"
    if "PAS" in v:
        return "PAS"
    if "CEX" in v:
        return "CEX"
    return "DNI"


def _parse_cliente_tipo_persona(value: str) -> int:
    v = (_normalize_text(value) or "").upper()
    if "JURID" in v:
        return 2
    if "NAT" in v:
        return 1
    try:
        return int(v)
    except Exception:
        return 1


def _normalize_bool_from_number(value):
    n = _normalize_number(value)
    if n is None:
        return 0
    return 1 if n >= 1 else 0


def _parse_cliente_fecha(value):
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.to_pydatetime()
    text = _normalize_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _upsert_clientes(conn, xls: pd.ExcelFile) -> None:
    df = _load_df_with_names(
        xls,
        sheet="Clientes",
        usecols="A:U",
        names=[
            "id_cliente_excel",
            "fec_reg",
            "razon_social",
            "tipo_doc",
            "num_doc",
            "tel1",
            "tel2",
            "subagente",
            "email",
            "direccion",
            "estado",
            "notifica",
            "cumple_aniv",
            "tipo_persona_txt",
            "persona",
            "departamento",
            "provincia",
            "distrito",
            "contacto_nombre",
            "contacto_email",
            "contacto_tel",
        ],
    )
    if df.empty:
        return
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            id_excel_val = _normalize_number(row.get("id_cliente_excel"))
            try:
                id_excel_int = int(id_excel_val) if id_excel_val is not None else None
            except Exception:
                id_excel_int = None
            razon_social = _normalize_text(row.get("razon_social"))
            num_doc = _normalize_text(row.get("num_doc"))
            if not razon_social:
                continue
            tipo_doc = _parse_cliente_tipo_doc(row.get("tipo_doc"))
            # Si no hay documento, generar uno placeholder estable basado en idCliente de Excel
            if not num_doc:
                tipo_persona_guess = _parse_cliente_tipo_persona(row.get("tipo_persona_txt") or row.get("persona"))
                if tipo_persona_guess == 2:
                    tipo_doc = "RUC"
                    prefix = "R"
                else:
                    tipo_doc = "DNI"
                    prefix = "D"
                if id_excel_int is None:
                    num_doc = f"{prefix}X{abs(hash(razon_social))%10_000_000:07d}"
                else:
                    num_doc = f"{prefix}{id_excel_int:09d}" if prefix == "R" else f"{prefix}{id_excel_int:08d}"
                num_doc = num_doc[:20]
            telefono = (_normalize_text(row.get("tel1")) or "")[:20] or None
            celular = (_normalize_text(row.get("tel2")) or "")[:20] or None
            telefono_sec = None
            subagente = _normalize_text(row.get("subagente"))
            email = _normalize_text(row.get("email"))
            direccion = _normalize_text(row.get("direccion"))
            departamento = _normalize_text(row.get("departamento"))
            provincia = _normalize_text(row.get("provincia"))
            distrito = _normalize_text(row.get("distrito"))
            estado = _normalize_text(row.get("estado")) or "Vigente"
            tipo_persona = _parse_cliente_tipo_persona(row.get("tipo_persona_txt") or row.get("persona"))
            recibir_notif = _normalize_bool_from_number(row.get("notifica"))
            contacto_nombre = _normalize_text(row.get("contacto_nombre"))
            contacto_email = _normalize_text(row.get("contacto_email"))
            contacto_tel = (_normalize_text(row.get("contacto_tel")) or "")[:20] or None
            cursor.execute(
                """
                INSERT INTO clientes (
                    razon_social, tipo_documento, numero_documento,
                    telefono, celular, telefono_sec,
                    subagente, idProductor,
                    email, direccion, departamento, provincia, distrito,
                    estado, tipo_persona,
                    profesion, fecha_ingreso, fecha_nacimiento,
                    licencia_num, licencia_venc,
                    grupo_economico, giro_negocio, referencia, recomendado_por,
                    recibir_notificaciones, contacto_nombre, contacto_email, contacto_telefono,
                    usuario_creacion
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, NULL,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    NULL, NULL, NULL,
                    NULL, NULL,
                    NULL, NULL, NULL, NULL,
                    %s, %s, %s, %s,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    razon_social=VALUES(razon_social),
                    telefono=VALUES(telefono),
                    celular=VALUES(celular),
                    telefono_sec=VALUES(telefono_sec),
                    subagente=VALUES(subagente),
                    email=VALUES(email),
                    direccion=VALUES(direccion),
                    departamento=VALUES(departamento),
                    provincia=VALUES(provincia),
                    distrito=VALUES(distrito),
                    estado=VALUES(estado),
                    tipo_persona=VALUES(tipo_persona),
                    recibir_notificaciones=VALUES(recibir_notificaciones),
                    contacto_nombre=VALUES(contacto_nombre),
                    contacto_email=VALUES(contacto_email),
                    contacto_telefono=VALUES(contacto_telefono)
                """,
                (
                    razon_social,
                    tipo_doc,
                    num_doc,
                    telefono,
                    celular,
                    telefono_sec,
                    subagente,
                    email,
                    direccion,
                    departamento,
                    provincia,
                    distrito,
                    estado,
                    tipo_persona,
                    recibir_notif,
                    contacto_nombre,
                    contacto_email,
                    contacto_tel,
                    "excel-import",
                ),
            )
        conn.commit()
    finally:
        cursor.close()


def _upsert_tasa_soat(conn, xls: pd.ExcelFile) -> None:
    """
    Lee la hoja 'TasaSoat' y configura:
    1. Tipos de SOAT y sus tasas (Menor/Regular)
    2. Comisiones extra
    3. Mapeo de (Tipo, Uso, Clase) -> configuracion_soat
    """
    try:
        df = pd.read_excel(xls, sheet_name="TasaSoat", header=None)
    except ValueError:
        return

    cursor = conn.cursor()
    try:
        # -------------------------------------------------------
        # 1. Parse Rates (Buscar encabezado "Tipo" y "Prod. AAS")
        # -------------------------------------------------------
        rate_start_row = -1
        for idx, row in df.iterrows():
            r0 = str(row[0]).strip().lower()
            r1 = str(row[1]).strip().lower() if len(row) > 1 else ""
            if "tipo" in r0 and "aas" in r1:
                rate_start_row = idx
                break
        
        if rate_start_row != -1:
            for idx in range(rate_start_row + 1, len(df)):
                row = df.iloc[idx]
                nombre = _normalize_text(row[0])
                if not nombre:
                    # Si encontramos vacío, chequeamos si es el inicio de la siguiente tabla
                    # O simplemente terminamos si hay muchos vacíos
                    if idx > rate_start_row + 20: 
                         break
                    # Check if this row is actually the header for the next table
                    if len(row) > 2 and str(row[0]).strip().lower() == "tipo" and "clase" in str(row[2]).strip().lower():
                        break
                    continue
                
                # Check for next table header in current row
                if len(row) > 2 and str(row[0]).strip().lower() == "tipo" and "clase" in str(row[2]).strip().lower():
                    break

                val_aas = _normalize_number(row[1]) if len(row) > 1 else None
                val_vend = _normalize_number(row[2]) if len(row) > 2 else None

                if val_vend is not None:
                    # Es un Tipo de SOAT (tiene tasa vendedor)
                    cursor.execute("""
                        INSERT INTO tipos_soat (nombre, tasa_aas, tasa_vendedor)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE tasa_aas=VALUES(tasa_aas), tasa_vendedor=VALUES(tasa_vendedor)
                    """, (nombre, val_aas, val_vend))
                else:
                    # Es un Extra (solo tiene porcentaje en columna AAS o similar)
                    if val_aas is not None:
                         cursor.execute("""
                            INSERT INTO configuracion_comision_extra (descripcion, porcentaje)
                            VALUES (%s, %s)
                            ON DUPLICATE KEY UPDATE porcentaje=VALUES(porcentaje)
                        """, (nombre, val_aas))
        
        conn.commit()

        # -------------------------------------------------------
        # 2. Parse Mappings (Buscar "Tipo", "Uso", "Clase")
        # -------------------------------------------------------
        map_start_row = -1
        col_indices = {}
        
        # Escanear filas buscando los encabezados
        for idx, row in df.iterrows():
            row_str = [str(x).strip().lower() for x in row.values]
            if "tipo" in row_str and "clase" in row_str:
                map_start_row = idx
                col_indices['tipo'] = row_str.index("tipo")
                col_indices['clase'] = row_str.index("clase")
                if "uso" in row_str:
                    col_indices['uso'] = row_str.index("uso")
                break
        
        if map_start_row != -1:
            # Cargar todos los usos para cuando el Excel tenga Uso vacío (aplica a todos)
            cursor.execute("SELECT id, nombre FROM usos")
            all_usos = cursor.fetchall() # list of (id, nombre)
            
            for idx in range(map_start_row + 1, len(df)):
                row = df.iloc[idx]
                
                # Extraer valores usando indices dinámicos
                tipo_name = _normalize_text(row[col_indices['tipo']])
                clase_name = _normalize_text(row[col_indices['clase']])
                
                if not tipo_name or not clase_name:
                    continue
                
                uso_name = None
                if 'uso' in col_indices:
                    uso_name = _normalize_text(row[col_indices['uso']])
                
                # Obtener Tipo ID
                cursor.execute("SELECT id FROM tipos_soat WHERE nombre = %s", (tipo_name,))
                res_tipo = cursor.fetchone()
                if not res_tipo:
                    continue
                tipo_id = res_tipo[0]
                
                # Obtener Clase ID
                cursor.execute("SELECT id FROM clases WHERE nombre = %s", (clase_name,))
                res_clase = cursor.fetchone()
                if not res_clase:
                    continue
                clase_id = res_clase[0]
                
                if uso_name:
                    # Caso 1: Uso especifico
                    cursor.execute("SELECT id FROM usos WHERE nombre = %s", (uso_name,))
                    res_uso = cursor.fetchone()
                    if res_uso:
                        uso_id = res_uso[0]
                        cursor.execute("""
                            INSERT INTO configuracion_soat (tipo_soat_id, uso_id, clase_id)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE tipo_soat_id=VALUES(tipo_soat_id)
                        """, (tipo_id, uso_id, clase_id))
                else:
                    # Caso 2: Uso vacio -> Aplicar a TODOS los usos
                    for (uid, uname) in all_usos:
                        cursor.execute("""
                            INSERT INTO configuracion_soat (tipo_soat_id, uso_id, clase_id)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE tipo_soat_id=VALUES(tipo_soat_id)
                        """, (tipo_id, uid, clase_id))
                        
        conn.commit()

    finally:
        cursor.close()


def main():
    # RamoProducto + comisiones
    df_ramo = _load_dataframe()
    conn = get_connection()
    try:
        def _table_exists(name: str) -> bool:
            c = conn.cursor()
            try:
                c.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s",
                    (name,),
                )
                return c.fetchone() is not None
            finally:
                c.close()
        if not df_ramo.empty and _table_exists("ramos") and _table_exists("productos"):
            _upsert_ramos_y_productos(conn, df_ramo)
            _insert_comisiones_temp(conn, df_ramo)
            _refrescar_comisiones(conn)

        # Abrir Excel una vez para otras hojas
        xls = pd.ExcelFile(_get_excel_path())
        _upsert_companias(conn, xls)
        _upsert_ejecutivos(conn, xls)
        _upsert_endosatarios(conn, xls)
        _upsert_clases(conn, xls)
        _upsert_marcas(conn, xls)
        _upsert_subagentes(conn, xls)
        _upsert_usos(conn, xls)
        _upsert_tasa_soat(conn, xls)
        _upsert_ajustadores(conn, xls)
        _upsert_modelos(conn, xls)
        _upsert_usuarios(conn, xls)
        _upsert_clientes(conn, xls)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
    
