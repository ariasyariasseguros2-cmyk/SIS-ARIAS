from flask import request, session
from models.db import get_connection
from datetime import datetime
from utils.rbac import Roles

def get_estado_cuenta_data(filtros_input=None):
    """
    Obtiene los datos para el estado de cuenta de un cliente con filtros aplicados.
    Parámetros:
        filtros_input: dict con filtros (si viene de POST) o None para usar request.args (GET)
    Retorna: dict con 'cliente', 'polizas', 'totales', 'filtros_options'
    """
    try:
        # Obtener parámetros de filtro desde el parámetro o desde request.args
        if filtros_input:
            # Filtros vienen desde POST (pasados como parámetro)
            filters = {
                'cliente_id': filtros_input.get('cliente_id', ''),
                'cliente_search': filtros_input.get('cliente_search', ''),
                'tipo_documento': filtros_input.get('tipo_documento', ''),
                'numero_documento': filtros_input.get('numero_documento', ''),
                'compania': filtros_input.get('compania', ''),
                'moneda': filtros_input.get('moneda', ''),
                'ramo': filtros_input.get('ramo', ''),
                'estado': filtros_input.get('estado', ''),
                'fecha_desde': filtros_input.get('fecha_desde', ''),
                'fecha_hasta': filtros_input.get('fecha_hasta', '')
            }
        else:
            # Filtros vienen desde GET (request.args) - para compatibilidad
            filters = {
                'cliente_id': request.args.get('cliente_id', ''),
                'cliente_search': request.args.get('cliente_search', ''),
                'tipo_documento': request.args.get('tipo_documento', ''),
                'numero_documento': request.args.get('numero_documento', ''),
                'compania': request.args.get('compania', ''),
                'moneda': request.args.get('moneda', ''),
                'ramo': request.args.get('ramo', ''),
                'estado': request.args.get('estado', ''),
                'fecha_desde': request.args.get('fecha_desde', ''),
                'fecha_hasta': request.args.get('fecha_hasta', '')
            }



        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        # Datos del cliente
        cliente = None
        polizas = []
        
        # RBAC: Verificar rol y usuario para filtros
        role_name = session.get('role_name')
        usuario_actual = session.get('user')
        es_subagente = (role_name == Roles.SUB_AGENTE)

        # Buscar cliente
        if filters['cliente_id']:
            query = """
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email, subagente
                FROM clientes 
                WHERE idCliente = %s
            """
            params = [filters['cliente_id']]
            
            if es_subagente:
                query += " AND subagente = %s"
                params.append(usuario_actual)
                
            cur.execute(query, params)
            cliente = cur.fetchone()


        elif filters['tipo_documento'] and filters['numero_documento']:
            # Búsqueda por tipo y número de documento (sin necesidad de cliente_search)
            query = """
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email, subagente
                FROM clientes 
                WHERE tipo_documento = %s 
                  AND numero_documento = %s
            """
            params = [filters['tipo_documento'], filters['numero_documento']]
            
            if es_subagente:
                query += " AND subagente = %s"
                params.append(usuario_actual)
                
            cur.execute(query, params)
            cliente = cur.fetchone()


        elif filters['numero_documento']:
            # Búsqueda solo por número de documento
            query = """
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email
                FROM clientes
                WHERE numero_documento = %s
            """
            params = [filters['numero_documento']]
            
            if es_subagente:
                query += " AND subagente = %s"
                params.append(usuario_actual)
                
            cur.execute(query, params)
            cliente = cur.fetchone()


        elif filters['cliente_search']:
            # Búsqueda por texto en nombre o documento
            search_term = f"%{filters['cliente_search']}%"
            query = """
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email
                FROM clientes 
                WHERE (razon_social LIKE %s OR numero_documento LIKE %s)
            """
            params = [search_term, search_term]
            
            if es_subagente:
                query += " AND subagente = %s"
                params.append(usuario_actual)
                
            query += " LIMIT 1"
            
            cur.execute(query, params)
            cliente = cur.fetchone()



        if cliente and role_name == Roles.SUB_AGENTE:
            if cliente.get('subagente') and cliente.get('subagente') != usuario_actual:
                cliente = None

        if cliente:

            query = """
                SELECT 
                    p.idPoliza,
                    p.cia AS compania,
                    p.ramo,
                    p.ramos_producto AS producto,
                    p.tipo_doc,
                    p.poliza,
                    p.recibo AS proforma,
                    q.cupon AS cupon,
                    q.factura AS factura,
                    DATE_FORMAT(q.fecha_pago, '%d/%m/%Y') AS fecha_pago,
                    DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
                    DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
                    DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
                    DATE_FORMAT(COALESCE(q.fecha_vencimiento, p.fecha_vencimiento), '%d/%m/%Y') AS fecha_venc,
                    COALESCE(q.moneda, p.moneda) AS moneda,
                    CASE WHEN q.idCuota IS NOT NULL THEN q.importe ELSE p.prima_comercial_igv END AS monto_cta_cobrar,
                    CASE 
                        WHEN q.idCuota IS NOT NULL THEN CASE WHEN q.fecha_pago IS NOT NULL THEN 0 ELSE q.importe END
                        ELSE CASE WHEN UPPER(IFNULL(p.estado,'')) = 'CANCELADO' THEN 0 ELSE p.prima_comercial_igv END
                    END AS monto_cta_pagar,
                    CASE 
                        WHEN q.idCuota IS NOT NULL THEN CASE WHEN q.fecha_pago IS NOT NULL THEN 'CANCELADO' ELSE 'PENDIENTE' END
                        ELSE p.estado
                    END AS estado
                FROM polizas p
                LEFT JOIN cuotas q ON q.poliza_id = p.idPoliza
                WHERE p.cliente_id = %s
            """

            params = [cliente['idCliente']]

            # Aplicar filtros adicionales
            if filters['compania']:
                query += " AND p.cia = %s"
                params.append(filters['compania'])

            if filters['moneda']:
                moneda_filtro = filters['moneda'].upper()
                if 'SOLES' in moneda_filtro or 'S/' in moneda_filtro:
                    query += " AND (UPPER(p.moneda) LIKE '%SOLES%' OR UPPER(p.moneda) LIKE '%S/%')"
                elif 'DOLAR' in moneda_filtro or 'US$' in moneda_filtro or 'USD' in moneda_filtro:
                    query += " AND (UPPER(p.moneda) LIKE '%DOLAR%' OR UPPER(p.moneda) LIKE '%US$%' OR UPPER(p.moneda) LIKE '%USD%')"
                else:
                    query += " AND p.moneda = %s"
                    params.append(filters['moneda'])

            if filters['ramo']:
                query += " AND p.ramo = %s"
                params.append(filters['ramo'])

            # estado filtrado luego en Python para considerar cuotas

            if filters['fecha_desde'] and filters['fecha_hasta']:
                # Buscar pólizas donde CUALQUIER fecha esté dentro del rango
                query += """ AND (
                    (p.fecha_emision BETWEEN %s AND %s) OR
                    (p.fecha_vencimiento BETWEEN %s AND %s) OR
                    (p.vig_desde BETWEEN %s AND %s) OR
                    (p.vig_hasta BETWEEN %s AND %s) OR
                    (q.fecha_vencimiento BETWEEN %s AND %s)
                )"""
                params.extend([
                    filters['fecha_desde'], filters['fecha_hasta'],  # fecha_emision
                    filters['fecha_desde'], filters['fecha_hasta'],  # fecha_vencimiento
                    filters['fecha_desde'], filters['fecha_hasta'],  # vig_desde
                    filters['fecha_desde'], filters['fecha_hasta'],  # vig_hasta
                    filters['fecha_desde'], filters['fecha_hasta']   # cuotas.fecha_vencimiento
                ])
            elif filters['fecha_desde']:
                # Solo fecha desde: cualquier fecha >= fecha_desde
                query += """ AND (
                    p.fecha_emision >= %s OR
                    p.fecha_vencimiento >= %s OR
                    p.vig_desde >= %s OR
                    p.vig_hasta >= %s OR
                    q.fecha_vencimiento >= %s
                )"""
                params.extend([
                    filters['fecha_desde'],
                    filters['fecha_desde'],
                    filters['fecha_desde'],
                    filters['fecha_desde'],
                    filters['fecha_desde']
                ])
            elif filters['fecha_hasta']:
                # Solo fecha hasta: cualquier fecha <= fecha_hasta
                query += """ AND (
                    p.fecha_emision <= %s OR
                    p.fecha_vencimiento <= %s OR
                    p.vig_desde <= %s OR
                    p.vig_hasta <= %s OR
                    q.fecha_vencimiento <= %s
                )"""
                params.extend([
                    filters['fecha_hasta'],
                    filters['fecha_hasta'],
                    filters['fecha_hasta'],
                    filters['fecha_hasta'],
                    filters['fecha_hasta']
                ])

            query += " ORDER BY p.fecha_emision DESC, p.vig_desde DESC"

            cur.execute(query, params)
            polizas = cur.fetchall() or []

            if filters['estado']:
                est = filters['estado'].strip().upper()
                polizas = [r for r in polizas if (r.get('estado') or '').upper() == est]


        # Calcular totales por moneda
        totales = {
            'soles_cobrar': 0,
            'soles_pagar': 0,
            'dolares_cobrar': 0,
            'dolares_pagar': 0
        }

        for p in polizas:
            moneda_upper = p['moneda'].upper() if p['moneda'] else ''
            # Reconocer SOLES o S/
            if 'SOLES' in moneda_upper or 'S/' in moneda_upper:
                totales['soles_cobrar'] += float(p['monto_cta_cobrar'] or 0)
                totales['soles_pagar'] += float(p['monto_cta_pagar'] or 0)
            # Reconocer DÓLARES, DOLARES, US$ o USD
            elif 'DOLAR' in moneda_upper or 'US$' in moneda_upper or 'USD' in moneda_upper:
                totales['dolares_cobrar'] += float(p['monto_cta_cobrar'] or 0)
                totales['dolares_pagar'] += float(p['monto_cta_pagar'] or 0)

        # Obtener opciones para los filtros (sin depender del cliente)
        cur.execute("SELECT nombre_corto FROM companias WHERE nombre_corto IS NOT NULL AND nombre_corto != '' ORDER BY nombre_corto")
        companias = [row['nombre_corto'] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT nombre FROM ramos WHERE estado = 'Activo' ORDER BY nombre")
        ramos = [row['nombre'] for row in cur.fetchall()]

        # Obtener los estados reales de la tabla polizas
        cur.execute("SELECT DISTINCT estado FROM polizas WHERE estado IS NOT NULL AND estado != '' ORDER BY estado")
        estados = [row['estado'] for row in cur.fetchall()]

        # Normalizar monedas para el filtro (mostrar opciones simples)
        monedas_normalizadas = ['SOLES', 'DÓLARES']

        filtros_options = {
            'companias': companias,
            'ramos': ramos,
            'estados': estados,
            'monedas': monedas_normalizadas
        }

        cur.close()
        cnx.close()

        return {
            'cliente': cliente,
            'polizas': polizas,
            'totales': totales,
            'filtros_options': filtros_options,
            'filtros_aplicados': filters
        }

    except Exception as e:
        print(f"Error en get_estado_cuenta_data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'cliente': None,
            'polizas': [],
            'totales': {},
            'filtros_options': {'companias': [], 'ramos': [], 'estados': [], 'monedas': []},
            'filtros_aplicados': {}
        }


def buscar_clientes(search_term):
    """
    Busca clientes por nombre, RUC o DNI.
    Retorna lista de clientes encontrados.
    """
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        search = f"%{search_term}%"
        
        # RBAC: Si es SUB AGENTE, filtrar por su usuario
        role_name = session.get('role_name')
        usuario_actual = session.get('user')
        
        if role_name == Roles.SUB_AGENTE:
            cur.execute("""
                SELECT 
                    idCliente,
                    razon_social,
                    tipo_documento,
                    numero_documento,
                    telefono,
                    email
                FROM clientes
                WHERE (razon_social LIKE %s OR numero_documento LIKE %s)
                  AND subagente = %s
                ORDER BY razon_social
                LIMIT 20
            """, (search, search, usuario_actual))
        else:
            cur.execute("""
                SELECT 
                    idCliente,
                    razon_social,
                    tipo_documento,
                    numero_documento,
                    telefono,
                    email
                FROM clientes
                WHERE (razon_social LIKE %s OR numero_documento LIKE %s)
                ORDER BY razon_social
                LIMIT 20
            """, (search, search))

        clientes = cur.fetchall() or []

        cur.close()
        cnx.close()

        return clientes

    except Exception as e:
        print(f"Error en buscar_clientes: {e}")
        return []


def export_estado_cuenta_data(args, fmt='xlsx'):
    """Genera un archivo (xlsx o pdf) con las pólizas filtradas.
    args: request.args-like (mapping)
    fmt: 'xlsx' o 'pdf'
    Retorna: (filepath, filename)
    """
    from models.db import get_connection
    import os
    from datetime import datetime

    # Reconstruir filtros desde args
    filters = {
        'cliente_id': args.get('cliente_id', ''),
        'cliente_search': args.get('cliente_search', ''),
        'tipo_documento': args.get('tipo_documento', ''),
        'numero_documento': args.get('numero_documento', ''),
        'compania': args.get('compania', ''),
        'moneda': args.get('moneda', ''),
        'ramo': args.get('ramo', ''),
        'estado': args.get('estado', ''),
        'fecha_desde': args.get('fecha_desde', ''),
        'fecha_hasta': args.get('fecha_hasta', '')
    }

    # Reusar la lógica de consulta para obtener polizas
    cnx = get_connection()
    cur = cnx.cursor(dictionary=True)

    cliente = None
    polizas = []

    # RBAC: Verificar rol y usuario para filtros
    role_name = session.get('role_name')
    usuario_actual = session.get('user')
    es_subagente = (role_name == Roles.SUB_AGENTE)

    # Buscar cliente (misma lógica que get_estado_cuenta_data)
    if filters['cliente_id']:
        query = """
            SELECT idCliente, razon_social, tipo_documento, numero_documento, subagente
            FROM clientes WHERE idCliente = %s
        """
        params = [filters['cliente_id']]
        
        if es_subagente:
            query += " AND subagente = %s"
            params.append(usuario_actual)
            
        cur.execute(query, params)
        cliente = cur.fetchone()

    elif filters['tipo_documento'] and filters['numero_documento']:
        query = """
            SELECT idCliente, razon_social, tipo_documento, numero_documento, subagente
            FROM clientes WHERE tipo_documento = %s AND numero_documento = %s
        """
        params = [filters['tipo_documento'], filters['numero_documento']]
        
        if es_subagente:
            query += " AND subagente = %s"
            params.append(usuario_actual)
            
        cur.execute(query, params)
        cliente = cur.fetchone()

    elif filters['numero_documento']:
        query = """
            SELECT idCliente, razon_social, tipo_documento, numero_documento, subagente
            FROM clientes WHERE numero_documento = %s
        """
        params = [filters['numero_documento']]
        
        if es_subagente:
            query += " AND subagente = %s"
            params.append(usuario_actual)
            
        cur.execute(query, params)
        cliente = cur.fetchone()

    elif filters['cliente_search']:
        search_term = f"%{filters['cliente_search']}%"
        query = """
            SELECT idCliente, razon_social, tipo_documento, numero_documento, subagente
            FROM clientes WHERE (razon_social LIKE %s OR numero_documento LIKE %s)
        """
        params = [search_term, search_term]
        
        if es_subagente:
            query += " AND subagente = %s"
            params.append(usuario_actual)
            
        query += " LIMIT 1"
        cur.execute(query, params)
        cliente = cur.fetchone()

    if cliente and role_name == Roles.SUB_AGENTE:
        if cliente.get('subagente') and cliente.get('subagente') != usuario_actual:
            cliente = None

    if cliente:
        query = """
            SELECT 
                p.cia AS compania,
                p.ramo,
                p.ramos_producto AS producto,
                p.tipo_doc,
                p.poliza,
                p.recibo AS proforma,
                q.cupon AS cupon,
                q.factura AS factura,
                DATE_FORMAT(q.fecha_pago, '%d/%m/%Y') AS fecha_pago,
                DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
                DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
                DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
                DATE_FORMAT(COALESCE(q.fecha_vencimiento, p.fecha_vencimiento), '%d/%m/%Y') AS fecha_venc,
                COALESCE(q.moneda, p.moneda) AS moneda,
                CASE WHEN q.idCuota IS NOT NULL THEN q.importe ELSE p.prima_comercial_igv END AS monto_cta_cobrar,
                CASE 
                    WHEN q.idCuota IS NOT NULL THEN CASE WHEN q.fecha_pago IS NOT NULL THEN 0 ELSE q.importe END
                    ELSE CASE WHEN UPPER(IFNULL(p.estado,'')) = 'CANCELADO' THEN 0 ELSE p.prima_comercial_igv END
                END AS monto_cta_pagar,
                CASE 
                    WHEN q.idCuota IS NOT NULL THEN CASE WHEN q.fecha_pago IS NOT NULL THEN 'CANCELADO' ELSE 'PENDIENTE' END
                    ELSE p.estado
                END AS estado
            FROM polizas p
            LEFT JOIN cuotas q ON q.poliza_id = p.idPoliza
            WHERE p.cliente_id = %s
        """
        params = [cliente['idCliente']]

        if filters['compania']:
            query += " AND p.cia = %s"
            params.append(filters['compania'])

        if filters['moneda']:
            moneda_filtro = filters['moneda'].upper()
            if 'SOLES' in moneda_filtro or 'S/' in moneda_filtro:
                query += " AND (UPPER(p.moneda) LIKE '%SOLES%' OR UPPER(p.moneda) LIKE '%S/%')"
            elif 'DOLAR' in moneda_filtro or 'US$' in moneda_filtro or 'USD' in moneda_filtro:
                query += " AND (UPPER(p.moneda) LIKE '%DOLAR%' OR UPPER(p.moneda) LIKE '%US$%' OR UPPER(p.moneda) LIKE '%USD%')"
            else:
                query += " AND p.moneda = %s"
                params.append(filters['moneda'])

        if filters['ramo']:
            query += " AND p.ramo = %s"
            params.append(filters['ramo'])

        # estado filtrado luego en Python para considerar cuotas

        if filters['fecha_desde'] and filters['fecha_hasta']:
            query += """ AND ((p.fecha_emision BETWEEN %s AND %s) OR (p.fecha_vencimiento BETWEEN %s AND %s) OR (p.vig_desde BETWEEN %s AND %s) OR (p.vig_hasta BETWEEN %s AND %s) OR (q.fecha_vencimiento BETWEEN %s AND %s))"""
            params.extend([filters['fecha_desde'], filters['fecha_hasta']] * 5)
        elif filters['fecha_desde']:
            query += """ AND (p.fecha_emision >= %s OR p.fecha_vencimiento >= %s OR p.vig_desde >= %s OR p.vig_hasta >= %s OR q.fecha_vencimiento >= %s)"""
            params.extend([filters['fecha_desde']] * 5)
        elif filters['fecha_hasta']:
            query += """ AND (p.fecha_emision <= %s OR p.fecha_vencimiento <= %s OR p.vig_desde <= %s OR p.vig_hasta <= %s OR q.fecha_vencimiento <= %s)"""
            params.extend([filters['fecha_hasta']] * 5)

        query += " ORDER BY p.fecha_emision DESC, p.vig_desde DESC"
        cur.execute(query, params)
        polizas = cur.fetchall() or []

        if filters['estado']:
            est = filters['estado'].strip().upper()
            polizas = [r for r in polizas if (r.get('estado') or '').upper() == est]
    cur.close()
    cnx.close()

    # Preparar datos para exportar
    headers = [
        'Compañía',
        'Ramo',
        'Producto',
        'Tipo Doc',
        'N° de Póliza',
        'Proforma',
        'Cupón',
        'Fecha Emisión',
        'Vigencia (Desde - Hasta)',
        'Factura',
        'Fecha de Pago',
        'Fecha Vencimiento',
        'Moneda',
        'Cta. Cobrar',
        'Cta. Pagar',
        'Estado'
    ]
    rows = []
    for p in polizas:
        vig = f"{p.get('vig_inicio') or '-'} - {p.get('vig_fin') or '-'}"
        moneda = p.get('moneda') or ''
        if moneda:
            mu = moneda.upper()
            if 'SOLES' in mu or 'S/' in mu:
                moneda = 'S/'
            elif 'DOLAR' in mu or 'US$' in mu or 'USD' in mu:
                moneda = 'US$'

        rows.append([
            p.get('compania') or '-',
            p.get('ramo') or '-',
            p.get('producto') or '-',
            p.get('tipo_doc') or '-',
            p.get('poliza') or '-',
            p.get('proforma') or '-',
            p.get('cupon') or '-',
            p.get('fecha_emision') or '-',
            vig,
            p.get('factura') or '-',
            p.get('fecha_pago') or '-',
            p.get('fecha_facturacion') or '-',
            p.get('fecha_emision') or '-',
            p.get('fecha_venc') or '-',
            moneda or '-',
            float(p.get('monto_cta_cobrar') or 0),
            float(p.get('monto_cta_pagar') or 0),
            p.get('estado') or '-'
        ])

    # Crear carpeta de export
    upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'static', 'uploads')
    # Prefer current_app if disponible
    try:
        from flask import current_app
        upload_folder = current_app.config.get('UPLOAD_FOLDER', upload_folder)
    except Exception:
        pass

    exports_dir = os.path.join(upload_folder, 'exports')
    os.makedirs(exports_dir, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = f"estado_cuenta_{cliente['idCliente'] if cliente else 'sincliente'}_{ts}"

    if fmt == 'xlsx':
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = 'Estado de Cuenta'

            # Escribir headers
            for col, h in enumerate(headers, start=1):
                ws.cell(row=1, column=col, value=h)

            # Escribir filas
            for r, row in enumerate(rows, start=2):
                for c, val in enumerate(row, start=1):
                    ws.cell(row=r, column=c, value=val)

            filename = f"{base_name}.xlsx"
            filepath = os.path.join(exports_dir, filename)
            wb.save(filepath)
            return filepath, filename
        except Exception as e:
            raise
    elif fmt == 'pdf':
        # Generar PDF con reportlab - formato optimizado para estado de cuenta
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

            filename = f"{base_name}.pdf"
            filepath = os.path.join(exports_dir, filename)

            # Landscape A4 con márgenes ajustados
            doc = SimpleDocTemplate(
                filepath,
                pagesize=landscape(A4),
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )
            elements = []
            styles = getSampleStyleSheet()

            # Agregar logo de la empresa
            try:
                logo_path = os.path.join(upload_folder, 'logo', 'Logo-banner.png')
                if os.path.exists(logo_path):
                    logo = Image(logo_path)
                    # Ajustar tamaño del logo (ancho máximo 60mm, mantener proporción)
                    logo.drawHeight = 15*mm
                    logo.drawWidth = 60*mm
                    logo.hAlign = 'LEFT'
                    elements.append(logo)
                    elements.append(Spacer(1, 8))
            except Exception as e:
                print(f"[WARN] No se pudo cargar el logo: {e}")

            # Título principal
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1F59A3'),
                spaceAfter=10,
                alignment=TA_CENTER
            )
            title = Paragraph('<b>Estado de Cuenta</b>', title_style)
            elements.append(title)

            # Información del cliente
            if cliente:
                cliente_info_style = ParagraphStyle(
                    'ClienteInfo',
                    parent=styles['Normal'],
                    fontSize=9,
                    spaceAfter=5,
                    alignment=TA_LEFT
                )
                info_text = f"<b>Cliente:</b> {cliente.get('razon_social', 'N/A')} | "
                info_text += f"<b>Documento:</b> {cliente.get('tipo_documento', '')} - {cliente.get('numero_documento', 'N/A')}"

                cliente_para = Paragraph(info_text, cliente_info_style)
                elements.append(cliente_para)

            elements.append(Spacer(1, 10))

            # Preparar datos de la tabla
            table_data = [headers]
            for r in rows:
                # Convertir numéricos a string con 2 decimales
                r2 = [("{:.2f}".format(x) if isinstance(x, float) else x) for x in r]
                table_data.append(r2)

            # Definir anchos de columna específicos (en orden de las columnas)
            # Total disponible en landscape A4 ≈ 267mm - 30mm (márgenes) = 237mm
            col_widths = [
                28*mm,  # Compañía
                20*mm,  # Ramo
                26*mm,  # Producto
                16*mm,  # Tipo Doc
                22*mm,  # N° de Póliza
                22*mm,  # Proforma
                22*mm,  # Cupón
                18*mm,  # Fecha Emisión
                32*mm,  # Vigencia (Desde - Hasta)
                22*mm,  # Factura
                20*mm,  # Fecha de Pago
                18*mm,  # Fecha Vencimiento
                14*mm,  # Moneda
                16*mm,  # Cta. Cobrar
                16*mm,  # Cta. Pagar
                16*mm   # Estado
            ]

            t = Table(table_data, colWidths=col_widths, repeatRows=1)

            # Estilo mejorado de la tabla
            t.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Datos
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (12, -1), 'LEFT'),      # Texto a la izquierda hasta Fecha Vencimiento
                ('ALIGN', (13, 1), (-1, -1), 'RIGHT'),    # Moneda, Cobrar, Pagar, Estado a la derecha
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),

                # Bordes y colores alternados
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),

                # Resaltar columnas numéricas
                ('FONTNAME', (14, 1), (15, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (14, 1), (14, -1), colors.HexColor('#0066CC')),  # Cta. Cobrar en azul
                ('TEXTCOLOR', (15, 1), (15, -1), colors.HexColor('#CC0000')), # Cta. Pagar en rojo
            ]))

            elements.append(t)

            # Agregar fecha de generación al final
            elements.append(Spacer(1, 10))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=7,
                textColor=colors.grey,
                alignment=TA_RIGHT
            )
            fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            footer = Paragraph(f'Generado: {fecha_generacion}', footer_style)
            elements.append(footer)

            doc.build(elements)
            return filepath, filename
        except Exception as e:
            raise
    else:
        raise ValueError('Formato no soportado')
