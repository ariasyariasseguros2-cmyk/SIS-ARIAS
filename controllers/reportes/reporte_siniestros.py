from flask import jsonify, request, session, current_app, send_file
from controllers.siniestros.siniestros_controller import list_siniestros, generar_pdf_siniestro


def get_reporte_siniestros(filters=None):
    try:
        # Implementación directa para evitar dependencias de list_siniestros() que es un controlador
        from models.db import get_connection
        from utils.rbac import Roles

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # RLS Logic (Copiar lógica de siniestros_controller)
        rls_filter = ""
        rls_params = []
        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            # Get user's full name for sub_agente match
            cursor.execute("SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s", (user,))
            u_row = cursor.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else user) or user

            rls_filter = """
                AND (
                    s.usuario_registro = %s
                    OR s.usuario_registro = %s
                    OR EXISTS (
                        SELECT 1 FROM polizas p 
                        WHERE p.poliza = s.poliza 
                        AND (
                            p.sub_agente = %s
                            OR p.sub_agente = %s
                            OR p.usuario_registro = %s
                            OR p.usuario_registro = %s
                        )
                    )
                )
            """
            rls_params = [user, nombre_usuario, user, nombre_usuario, user, nombre_usuario]

        sql = f"""
            SELECT
                s.id, s.grupo_ramo, s.contratante, s.poliza, s.cia, s.ramo, s.fec_stro,
                s.causa, s.siniestro_no, s.monto_siniestro, s.estado, s.ejecutivo_cia, s.placa, s.fecha_registro AS creado_en
            FROM siniestros s
            WHERE s.eliminado = 0 {rls_filter}
        """

        # Filtros
        if not filters:
            filters = {}
            # Intentar sacar de request si filters es None
            if request:
                filters = {
                    'fec_desde': request.args.get('fec_desde'),
                    'fec_hasta': request.args.get('fec_hasta'),
                    'poliza': request.args.get('poliza'),
                    'texto': request.args.get('texto') # No usado en query original pero por si acaso
                }

        fec_desde = filters.get('fec_desde')
        fec_hasta = filters.get('fec_hasta')

        if fec_desde and fec_hasta:
            sql += " AND s.fec_stro BETWEEN %s AND %s"
            rls_params.extend([fec_desde, fec_hasta])
        elif fec_desde:
            sql += " AND s.fec_stro >= %s"
            rls_params.append(fec_desde)
        elif fec_hasta:
            sql += " AND s.fec_stro <= %s"
            rls_params.append(fec_hasta)

        # Filtro poliza opcional (usado en dashboards, etc)
        if filters.get('poliza'):
            sql += " AND s.poliza LIKE %s"
            rls_params.append(f"{filters.get('poliza')}%")

        sql += " ORDER BY s.fec_stro DESC"

        cursor.execute(sql, tuple(rls_params))
        siniestros = cursor.fetchall()

        # Serializar fechas y decimales
        from datetime import date, datetime
        from decimal import Decimal
        for s in siniestros:
            for k, v in s.items():
                if isinstance(v, (date, datetime)):
                    s[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    s[k] = float(v)

        cursor.close()
        connection.close()

        return {'ok': True, 'rows': siniestros}

    except Exception as e:
        current_app.logger.error(f"Error obteniendo reporte siniestros: {e}")
        return {'ok': False, 'error': str(e)}


def export_reporte_siniestros_pdf(siniestro_ids=None, inline=False):

    # Caso 1: si se especifican ids, devolvemos un zip? Para simplicidad: si hay un solo id delegamos a generar_pdf_siniestro
    try:
        if siniestro_ids and isinstance(siniestro_ids, (list, tuple)) and len(siniestro_ids) == 1:
            # Delegar a la función existente para obtener el PDF
            siniestro_id = siniestro_ids[0]
            # generar_pdf_siniestro devuelve un Response (send_file) normalmente; llamar y retornar ese Response
            # Para forzar inline añadimos ?inline=1 si requested
            with current_app.test_request_context(f"/fake?inline={1 if inline else 0}"):
                return generar_pdf_siniestro(siniestro_id)

        # Caso general: crear PDF resumen en memoria con reportlab
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO
        from datetime import datetime

        # Obtener datos
        data_resp = get_reporte_siniestros()
        if not data_resp.get('ok'):
            raise Exception(data_resp.get('error') or 'Error al obtener datos')
        rows = data_resp.get('rows') or []

        # Filtrar por IDs si se especificaron
        if siniestro_ids and isinstance(siniestro_ids, (list, tuple)) and len(siniestro_ids) > 0:
            # Asegurar que los IDs en rows sean del mismo tipo que siniestro_ids (probablemente int)
            try:
                target_ids = set([int(x) for x in siniestro_ids])
                rows = [r for r in rows if r.get('id') in target_ids]
            except ValueError:
                # Si fallan las conversiones, intentar comparación directa
                target_ids = set(siniestro_ids)
                rows = [r for r in rows if r.get('id') in target_ids]

        buffer = BytesIO()
        # Usar landscape para más ancho horizontal y evitar overflow
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1.2*cm, rightMargin=1.2*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('title', parent=styles['Heading1'], alignment=1, fontSize=12)
        header_style = ParagraphStyle('hdr', parent=styles['Normal'], fontSize=8, textColor=colors.white)
        cell_style = ParagraphStyle('cell', parent=styles['Normal'], fontSize=7)

        story = []
        story.append(Paragraph('REPORTE DE SINIESTROS', title_style))
        story.append(Spacer(1, 6))

        # Tabla simple: id, poliza, contratante, cia, ramo, fecha, monto, estado
        table_data = [[ Paragraph('ID', header_style), Paragraph('Póliza', header_style), Paragraph('Contratante', header_style), Paragraph('Cía', header_style), Paragraph('Ramo', header_style), Paragraph('Fecha', header_style), Paragraph('Monto', header_style), Paragraph('Estado', header_style) ]]
        for s in rows:
            # Usar Paragraph para permitir wrapping y alturas variables
            table_data.append([
                Paragraph(str(s.get('id') or ''), cell_style),
                Paragraph(str(s.get('poliza') or ''), cell_style),
                Paragraph(str(s.get('contratante') or s.get('asegurado') or ''), cell_style),
                Paragraph(str(s.get('cia') or ''), cell_style),
                Paragraph(str(s.get('ramo') or ''), cell_style),
                Paragraph(str((s.get('fec_stro') or '')[:10]), cell_style),
                Paragraph(f"{float(s.get('monto_siniestro') or 0):,.2f}", cell_style),
                Paragraph(str(s.get('estado') or ''), cell_style)
            ])

        # Ajustar anchos para que quepan en la página A4 landscape con márgenes 1.2cm
        # Landscape A4 width ~29.7cm; usable = 29.7 - 2*1.2 = 27.3 cm
        col_widths = [1.5*cm, 3.5*cm, 6.0*cm, 3.5*cm, 3.5*cm, 3.0*cm, 2.5*cm, 2.0*cm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F59A3')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (6,1), (6,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))

        story.append(table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))

        doc.build(story)
        buffer.seek(0)

        if inline:
            return send_file(buffer, mimetype='application/pdf', as_attachment=False)

        # Guardar en uploads/exports
        import os
        exports_dir = os.path.join(current_app.root_path, 'uploads', 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        filename = f"Reporte Siniestros {datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(exports_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(buffer.getbuffer())
        return filepath, filename

    except Exception as e:
        current_app.logger.error(f"Error exportando reporte siniestros: {e}")
        raise

