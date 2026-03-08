from models.db import get_connection


def get_produccion_soat(page=1, per_page=20, search='', fecha_desde=None, fecha_hasta=None):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        offset = (page - 1) * per_page

        where_clauses = ["p.ramo LIKE '%SOAT%'", "p.anulado = 0"]
        params = []

        if search:
            where_clauses.append(
                "(p.poliza LIKE %s OR p.recibo LIKE %s OR p.contrato_nro LIKE %s "
                "OR p.codigo_agente LIKE %s OR p.ejecutivo LIKE %s)"
            )
            s = f"%{search}%"
            params += [s, s, s, s, s]

        if fecha_desde:
            where_clauses.append("p.vig_hasta >= %s")
            params.append(fecha_desde)

        if fecha_hasta:
            where_clauses.append("p.vig_hasta <= %s")
            params.append(fecha_hasta)

        where_sql = " AND ".join(where_clauses)

        # Total
        cur.execute(f"SELECT COUNT(*) AS total FROM polizas p WHERE {where_sql}", params)
        total = cur.fetchone()['total']

        # Datos
        query = f"""
            SELECT
                p.idPoliza,
                p.poliza,
                p.recibo,
                p.contrato_nro                          AS planilla,
                p.codigo_agente                         AS codigo,
                p.ejecutivo                             AS vendedor,
                p.prima_neta,
                p.prima_comercial_igv,
                p.porc_compania,
                p.imp_compania,
                p.porc_subagente,
                p.imp_subagente,
                ROUND(COALESCE(p.imp_compania,0) - COALESCE(p.imp_subagente,0), 2) AS produccion_neta,
                p.vig_desde,
                p.vig_hasta,
                p.cia,
                p.asegurado,
                p.estado
            FROM polizas p
            WHERE {where_sql}
            ORDER BY p.creado_en DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [per_page, offset])
        rows = cur.fetchall()

        # Totales generales
        cur.execute(f"""
            SELECT
                ROUND(SUM(COALESCE(prima_neta,0)), 2)          AS total_prima_neta,
                ROUND(SUM(COALESCE(prima_comercial_igv,0)), 2) AS total_prima_igv,
                ROUND(SUM(COALESCE(imp_compania,0)), 2)        AS total_imp_compania,
                ROUND(SUM(COALESCE(imp_subagente,0)), 2)       AS total_imp_subagente,
                ROUND(SUM(COALESCE(imp_compania,0) - COALESCE(imp_subagente,0)), 2) AS total_produccion_neta
            FROM polizas p
            WHERE {where_sql}
        """, params)
        totales = cur.fetchone()

        return {
            'rows': rows,
            'total': total,
            'totales': totales
        }
    except Exception as e:
        print(f"Error en get_produccion_soat: {e}")
        return {'rows': [], 'total': 0, 'totales': {}}
    finally:
        cur.close()
        conn.close()


def export_produccion_soat_excel(search='', fecha_desde=None, fecha_hasta=None):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        where_clauses = ["p.ramo LIKE '%SOAT%'", "p.anulado = 0"]
        params = []

        if search:
            where_clauses.append(
                "(p.poliza LIKE %s OR p.recibo LIKE %s OR p.contrato_nro LIKE %s "
                "OR p.codigo_agente LIKE %s OR p.ejecutivo LIKE %s)"
            )
            s = f"%{search}%"
            params += [s, s, s, s, s]

        if fecha_desde:
            where_clauses.append("p.vig_hasta >= %s")
            params.append(fecha_desde)

        if fecha_hasta:
            where_clauses.append("p.vig_hasta <= %s")
            params.append(fecha_hasta)

        where_sql = " AND ".join(where_clauses)

        query = f"""
            SELECT
                p.poliza,
                p.recibo,
                p.contrato_nro                          AS planilla,
                p.codigo_agente                         AS codigo,
                p.ejecutivo                             AS vendedor,
                p.prima_neta,
                p.prima_comercial_igv,
                p.porc_compania,
                p.imp_compania,
                p.porc_subagente,
                p.imp_subagente,
                ROUND(COALESCE(p.imp_compania,0) - COALESCE(p.imp_subagente,0), 2) AS produccion_neta,
                p.vig_desde,
                p.vig_hasta,
                p.cia,
                p.asegurado,
                p.estado
            FROM polizas p
            WHERE {where_sql}
            ORDER BY p.creado_en DESC
        """
        cur.execute(query, params)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    # Generate Excel
    import os
    from datetime import datetime
    from flask import current_app
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers = [
        "Póliza", "Recibo", "Planilla", "Código", "Vendedor", 
        "Prima Neta", "Prima C. IGV", "% Cía", "Imp. Cía", 
        "% Agente", "Imp. Agente", "Producción Neta",
        "Vigencia Desde", "Vigencia Hasta", "Cía", "Asegurado", "Estado"
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Produccion SOAT"
    bold_font = Font(bold=True)

    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = bold_font

    for r_idx, row in enumerate(rows, start=2):
        ws.cell(row=r_idx, column=1, value=row.get('poliza'))
        ws.cell(row=r_idx, column=2, value=row.get('recibo'))
        ws.cell(row=r_idx, column=3, value=row.get('planilla'))
        ws.cell(row=r_idx, column=4, value=row.get('codigo'))
        ws.cell(row=r_idx, column=5, value=row.get('vendedor'))
        
        c = ws.cell(row=r_idx, column=6, value=float(row.get('prima_neta') or 0))
        c.number_format = '#,##0.00'
        
        c = ws.cell(row=r_idx, column=7, value=float(row.get('prima_comercial_igv') or 0))
        c.number_format = '#,##0.00'
        
        c = ws.cell(row=r_idx, column=8, value=float(row.get('porc_compania') or 0))
        c.number_format = '0.00'
        
        c = ws.cell(row=r_idx, column=9, value=float(row.get('imp_compania') or 0))
        c.number_format = '#,##0.00'
        
        c = ws.cell(row=r_idx, column=10, value=float(row.get('porc_subagente') or 0))
        c.number_format = '0.00'
        
        c = ws.cell(row=r_idx, column=11, value=float(row.get('imp_subagente') or 0))
        c.number_format = '#,##0.00'
        
        c = ws.cell(row=r_idx, column=12, value=float(row.get('produccion_neta') or 0))
        c.number_format = '#,##0.00'
        
        ws.cell(row=r_idx, column=13, value=row.get('vig_desde'))
        ws.cell(row=r_idx, column=14, value=row.get('vig_hasta'))
        ws.cell(row=r_idx, column=15, value=row.get('cia'))
        ws.cell(row=r_idx, column=16, value=row.get('asegurado'))
        ws.cell(row=r_idx, column=17, value=row.get('estado'))

    # Save file
    try:
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
    except Exception:
        upload_folder = None
        
    if not upload_folder:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        upload_folder = os.path.join(base_dir, "static", "uploads")
    
    exports_dir = os.path.join(upload_folder, "exports")
    os.makedirs(exports_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"produccion_soat_{ts}.xlsx"
    filepath = os.path.join(exports_dir, filename)
    
    wb.save(filepath)
    return filepath, filename



