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
    text = text.replace(",", ".")
    try:
        return float(text)
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
    raw = (value or "").strip()
    if not raw:
        return "Activo"
    lower = raw.lower()
    if lower.startswith("act"):
        return "Activo"
    if lower.startswith("ina"):
        return "Inactivo"
    return "Activo"


def _load_dataframe() -> pd.DataFrame:
    path = _get_excel_path()
    df = pd.read_excel(
        path,
        sheet_name=0,
        header=None,
        skiprows=1,
        usecols="A:R",
        names=[
            "ramo_nombre",
            "ramo_abreviacion",
            "ramo_codigo",
            "ramo_grupo",
            "ramo_estado",
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
    if not df.empty:
        first_ramo = df.iloc[0]["ramo_nombre"]
        if isinstance(first_ramo, str) and first_ramo.strip().lower().startswith("nombre"):
            df = df.iloc[1:].reset_index(drop=True)
    return df


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
    cursor = conn.cursor()
    try:
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


def main():
    df = _load_dataframe()
    conn = get_connection()
    try:
        _upsert_ramos_y_productos(conn, df)
        _insert_comisiones_temp(conn, df)
        _refrescar_comisiones(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
    
