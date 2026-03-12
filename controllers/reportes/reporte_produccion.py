from typing import Dict, Any, List, Tuple

from flask import session, current_app

from models.db import get_connection
from utils.rbac import Roles


def get_reporte_produccion_filters() -> Dict[str, Any]:
    from controllers.compania import get_aseguradoras
    from controllers.ramos import get_ramos
    from controllers.subagente import get_subagentes_abreviaciones
    from controllers.ejecutivos import get_ejecutivos
    from controllers.maestros.usuarios import get_usuarios

    return {
        "companias": get_aseguradoras() or [],
        "ramos": get_ramos() or [],
        "subagentes": get_subagentes_abreviaciones() or [],
        "ejecutivos": get_ejecutivos() or [],
        "usuarios": get_usuarios() or [],
    }


def _build_filters(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    sql_filters = []
    params: List[Any] = []

    vig_desde = filters.get("vig_desde")
    vig_hasta = filters.get("vig_hasta")

    if vig_desde:
        sql_filters.append("p.vig_desde >= %s")
        params.append(vig_desde)

    if vig_hasta:
        sql_filters.append("p.vig_desde <= %s")
        params.append(vig_hasta)

    if filters.get("cia"):
        sql_filters.append("p.cia = %s")
        params.append(filters["cia"])

    if filters.get("ramo"):
        sql_filters.append("p.ramo = %s")
        params.append(filters["ramo"])

    if filters.get("sub_agente"):
        sql_filters.append("p.sub_agente = %s")
        params.append(filters["sub_agente"])

    if filters.get("ejecutivo"):
        sql_filters.append("p.ejecutivo = %s")
        params.append(filters["ejecutivo"])

    if filters.get("usuario"):
        sql_filters.append(
            "(p.usuario_registro = %s OR p.usuario_registro = (SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1))"
        )
        params.extend([filters["usuario"], filters["usuario"]])

    f_reg_desde = filters.get("f_reg_desde")
    f_reg_hasta = filters.get("f_reg_hasta")

    if f_reg_desde:
        sql_filters.append("DATE(p.creado_en) >= %s")
        params.append(f_reg_desde)
    
    if f_reg_hasta:
        sql_filters.append("DATE(p.creado_en) <= %s")
        params.append(f_reg_hasta)

    # Filtro por rol: sub agente solo ve sus pólizas
    role = session.get("role_name")
    user = session.get("user")

    if role == Roles.SUB_AGENTE and user:
        sql_filters.append(
            "("
            "p.sub_agente = %s "
            "OR p.sub_agente = (SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1) "
            "OR p.usuario_registro = %s "
            "OR p.usuario_registro = (SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1)"
            ")"
        )
        params.extend([user, user, user, user])

    where_clause = ""
    if sql_filters:
        where_clause = " WHERE " + " AND ".join(sql_filters)

    return where_clause, params


def get_reporte_produccion_rows(filters: Dict[str, Any], limit: int = 1000) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        base_sql = """
            SELECT
                c.numero_documento AS ruc,
                c.razon_social AS contratante,
                c.direccion AS direccion_contratante,
                p.asegurado,
                p.cia,
                p.ramo AS ram,
                p.ramos_producto AS prod,
                p.poliza,
                p.tipo_doc AS td,
                p.recibo AS aviso_cob,
                '' AS estado_comision,
                p.vig_desde AS ini_vig,
                p.vig_hasta AS fin_vig,
                p.moneda AS mon,
                p.prima_neta AS prim_neta,
                p.prima_comercial_igv AS prim_total,
                p.porc_compania AS porc_cia,
                p.imp_compania AS comision_cia,
                p.sub_agente AS sagt,
                p.porc_subagente AS porc_sagt,
                p.imp_subagente AS comision_sagt,
                NULL AS fpago_sagt,
                NULL AS comprobante_sagt,
                p.motivo,
                c.departamento AS ciudad,
                NULL AS factura_comision,
                p.ejecutivo,
                NULL AS breve_descripcion,
                p.usuario_registro AS usuario,
                p.creado_en AS f_reg
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
        """

        where_clause, params = _build_filters(filters)
        
        order_clause = " ORDER BY p.fecha_emision DESC, p.creado_en DESC"
        if limit:
            order_clause += f" LIMIT {limit}"

        sql = base_sql + where_clause + order_clause

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall() or []
        
        # Post-process to format dates as strings
        for row in rows:
            if row.get('ini_vig'):
                row['ini_vig'] = str(row['ini_vig'])
            if row.get('fin_vig'):
                row['fin_vig'] = str(row['fin_vig'])
            if row.get('f_reg'):
                row['f_reg'] = str(row['f_reg'])

        return rows
    finally:
        conn.close()


def export_reporte_produccion(filters: Dict[str, Any]) -> Tuple[str, str]:
    # Para exportación, traemos todo (o un límite alto)
    rows = get_reporte_produccion_rows(filters, limit=None)

    headers = [
        "RUC",
        "CONTRATANTE",
        "DIRECCION DEL CONTRATANTE",
        "ASEGURADO",
        "CIA",
        "RAM",
        "PROD",
        "POLIZA",
        "TD",
        "AVISO COB",
        "ESTADO COMISION",
        "INI.VIG",
        "FIN.VIG",
        "MON",
        "PRIM.NETA",
        "PRIM.TOTAL",
        "% CIA",
        "COMISION CIA",
        "SAGT",
        "% SAGT",
        "COMISION SAGT",
        "F.PAGO SAGT",
        "COMPROBANTE SAGT",
        "MOTIVO",
        "CIUDAD",
        "FACTURA COMISION",
        "EJECUTIVO",
        "BREVE DESCRIPCION",
        "Usuario",
        "F.REG",
    ]

    table_rows = []
    for r in rows:
        table_rows.append(
            [
                r.get("ruc") or "",
                r.get("contratante") or "",
                r.get("direccion_contratante") or "",
                r.get("asegurado") or "",
                r.get("cia") or "",
                r.get("ram") or "",
                r.get("prod") or "",
                r.get("poliza") or "",
                r.get("td") or "",
                r.get("aviso_cob") or "",
                r.get("estado_comision") or "",
                r.get("ini_vig"),
                r.get("fin_vig"),
                r.get("mon") or "",
                float(r.get("prim_neta") or 0),
                float(r.get("prim_total") or 0),
                float(r.get("porc_cia") or 0),
                float(r.get("comision_cia") or 0),
                r.get("sagt") or "",
                float(r.get("porc_sagt") or 0),
                float(r.get("comision_sagt") or 0),
                r.get("fpago_sagt"),
                r.get("comprobante_sagt") or "",
                r.get("motivo") or "",
                r.get("ciudad") or "",
                r.get("factura_comision") or "",
                r.get("ejecutivo") or "",
                r.get("breve_descripcion") or "",
                r.get("usuario") or "",
                r.get("f_reg"),
            ]
        )

    import os
    from datetime import datetime

    try:
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
    except Exception:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        upload_folder = os.path.join(base_dir, "..", "uploads")

    if not upload_folder:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        upload_folder = os.path.join(base_dir, "..", "uploads")

    exports_dir = os.path.join(upload_folder, "exports")
    os.makedirs(exports_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reporte_produccion_{ts}.xlsx"
    filepath = os.path.join(exports_dir, filename)

    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Produccion"

    bold_font = Font(bold=True)

    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = bold_font

    for row_idx, row in enumerate(table_rows, start=2):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    wb.save(filepath)

    return filepath, filename
