from typing import Dict, Any, List, Tuple

from flask import session, current_app

from models.db import get_connection
from utils.financiamiento_grupal_reportes import enrich_rows_with_fg_metadata
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

    sql_filters.append("p.activo = 1")
    sql_filters.append("(p.anulado = 0 OR p.anulado IS NULL)")
    sql_filters.append("COALESCE(p.prima_anulada, 0) = 0")

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

    if filters.get("moneda"):
        mon = (filters.get("moneda") or "").strip().upper()
        if mon in {"S/", "S/.", "SOLES", "PEN"}:
            sql_filters.append(
                "(UPPER(TRIM(p.moneda)) LIKE 'S/%' OR UPPER(TRIM(p.moneda)) IN ('SOLES','PEN'))"
            )
        elif mon in {"US$", "USD", "$", "DOLARES", "DÓLARES", "DOLAR"}:
            sql_filters.append(
                "(UPPER(TRIM(p.moneda)) IN ('US$','USD','$','DOLARES','DÓLARES','DOLAR'))"
            )
        else:
            sql_filters.append("p.moneda = %s")
            params.append(filters["moneda"])

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
                p.idPoliza AS idPoliza,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR), c.numero_documento) AS ruc,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR), c.razon_social) AS contratante,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.direccion), @SIS_KEY) AS CHAR), c.direccion) AS direccion_contratante,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR), p.asegurado) AS asegurado,
                p.cia,
                p.ramo AS ram,
                p.ramos_producto AS prod,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR), p.poliza) AS poliza,
                p.tipo_doc AS td,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), p.recibo) AS aviso_cob,
                '' AS estado_comision,
                p.vig_desde AS ini_vig,
                p.vig_hasta AS fin_vig,
                p.moneda AS mon,
                COALESCE(p.prima_neta, 0) AS prim_neta,
                COALESCE(p.prima_comercial_igv) AS prim_total,
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
                p.asegurada AS breve_descripcion,
                p.usuario_registro AS usuario,
                DATE(p.creado_en) AS f_reg
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
        enrich_rows_with_fg_metadata(rows, poliza_id_keys=("idPoliza", "poliza_id"))
        
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
                r.get("idPoliza"),
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
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Produccion"

    title = "REPORTE DE PRODUCCIÓN"
    vig_desde = filters.get("vig_desde") or ""
    vig_hasta = filters.get("vig_hasta") or ""
    if vig_desde and vig_hasta:
        title = f"{title} — {vig_desde} a {vig_hasta}"

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    title_cell = ws.cell(row=1, column=1, value=title)
    title_cell.font = Font(bold=True, size=13, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1F59A3")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    header_fill = PatternFill("solid", fgColor="399AD6")
    header_font = Font(bold=True, color="FFFFFF", size=9)
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    ws.row_dimensions[2].height = 22

    money_cols = {15, 16, 18, 21}
    percent_cols = {17, 20}

    for row_idx, row in enumerate(table_rows, start=3):
        fill = PatternFill("solid", fgColor="F4F8FF") if row_idx % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        for col_idx, value in enumerate(row, start=1):
            if col_idx == 1:
                continue
            excel_col_idx = col_idx - 1
            cell = ws.cell(row=row_idx, column=excel_col_idx, value=value)
            cell.border = border
            cell.fill = fill
            cell.font = Font(size=9)
            if excel_col_idx in money_cols:
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif excel_col_idx in percent_cols:
                cell.number_format = '0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if excel_col_idx == 8:
                fg_meta = rows[row_idx - 3] if row_idx - 3 < len(rows) else {}
                if fg_meta.get("es_financiamiento_grupal"):
                    cell.font = Font(size=9, bold=True, color="7A3DB8")

    total_row = len(table_rows) + 3
    ws.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True, size=9)
    total_cols = [15, 16, 18, 21]
    for col in total_cols:
        cell = ws.cell(row=total_row, column=col)
        cell.font = Font(bold=True, size=9)
        cell.number_format = '#,##0.00'
        cell.alignment = Alignment(horizontal="right", vertical="center")
        if table_rows:
            col_letter = get_column_letter(col)
            cell.value = f"=SUBTOTAL(109,{col_letter}3:{col_letter}{total_row-1})"
        else:
            cell.value = 0

    for c in [15, 16, 18, 21]:
        ws.cell(row=total_row, column=c).number_format = '#,##0.00'
        ws.cell(row=total_row, column=c).alignment = Alignment(horizontal="right", vertical="center")

    col_widths = [
        12, 28, 28, 28, 16, 18, 18, 16, 6, 16,
        14, 12, 12, 10, 12, 12, 8, 12, 16, 8,
        12, 12, 18, 18, 14, 16, 16, 18, 16, 12
    ]
    for i, w in enumerate(col_widths[:len(headers)], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    wb.save(filepath)

    return filepath, filename
