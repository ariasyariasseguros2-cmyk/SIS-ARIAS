from flask import request
from models.db import get_connection
from datetime import datetime

def get_estado_cuenta_data():
    """
    Obtiene los datos para el estado de cuenta de un cliente con filtros aplicados.
    Retorna: dict con 'cliente', 'polizas', 'totales', 'filtros_options'
    """
    try:
        # Obtener parámetros de filtro
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

        print(f"[DEBUG] Filtros recibidos: {filters}")

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        # Datos del cliente
        cliente = None
        polizas = []

        # Buscar cliente
        if filters['cliente_id']:
            print(f"[DEBUG] Buscando por cliente_id: {filters['cliente_id']}")
            cur.execute("""
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email
                FROM clientes 
                WHERE idCliente = %s
            """, (filters['cliente_id'],))
            cliente = cur.fetchone()
            print(f"[DEBUG] Cliente encontrado por ID: {cliente}")

        elif filters['tipo_documento'] and filters['numero_documento']:
            # Búsqueda por tipo y número de documento (sin necesidad de cliente_search)
            print(f"[DEBUG] Buscando por tipo_doc y numero_doc: {filters['tipo_documento']} - {filters['numero_documento']}")
            cur.execute("""
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email
                FROM clientes 
                WHERE tipo_documento = %s 
                  AND numero_documento = %s
            """, (filters['tipo_documento'], filters['numero_documento']))
            cliente = cur.fetchone()
            print(f"[DEBUG] Cliente encontrado por doc: {cliente}")

        elif filters['numero_documento']:
            # Búsqueda solo por número de documento
            print(f"[DEBUG] Buscando solo por numero_doc: {filters['numero_documento']}")
            cur.execute("""
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email
                FROM clientes 
                WHERE numero_documento = %s
            """, (filters['numero_documento'],))
            cliente = cur.fetchone()
            print(f"[DEBUG] Cliente encontrado por numero_doc: {cliente}")

        elif filters['cliente_search']:
            # Búsqueda por texto en nombre o documento
            print(f"[DEBUG] Buscando por texto: {filters['cliente_search']}")
            search_term = f"%{filters['cliente_search']}%"
            cur.execute("""
                SELECT idCliente, razon_social, tipo_documento, numero_documento,
                       direccion, telefono, email
                FROM clientes 
                WHERE (razon_social LIKE %s OR numero_documento LIKE %s)
                LIMIT 1
            """, (search_term, search_term))
            cliente = cur.fetchone()
            print(f"[DEBUG] Cliente encontrado por búsqueda: {cliente}")

        # Si se encontró el cliente, obtener sus pólizas con filtros
        if cliente:
            print(f"[DEBUG] Cliente encontrado: {cliente['razon_social']} (ID: {cliente['idCliente']})")
            print(f"[DEBUG] Buscando pólizas con filtros adicionales...")
            query = """
                SELECT 
                    p.idPoliza,
                    p.cia AS compania,
                    p.ramo,
                    p.ramos_producto AS producto,
                    p.tipo_doc,
                    p.poliza,
                    DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
                    DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
                    DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
                    DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_facturacion,
                    DATE_FORMAT(p.fecha_vencimiento, '%d/%m/%Y') AS fecha_venc,
                    p.moneda,
                    p.prima_comercial AS monto_cta_cobrar,
                    p.prima_neta AS monto_cta_pagar,
                    p.estado
                FROM polizas p
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

            if filters['estado']:
                query += " AND p.estado = %s"
                params.append(filters['estado'])

            if filters['fecha_desde'] and filters['fecha_hasta']:
                # Buscar pólizas donde CUALQUIER fecha esté dentro del rango
                query += """ AND (
                    (p.fecha_emision BETWEEN %s AND %s) OR
                    (p.fecha_vencimiento BETWEEN %s AND %s) OR
                    (p.vig_desde BETWEEN %s AND %s) OR
                    (p.vig_hasta BETWEEN %s AND %s)
                )"""
                params.extend([
                    filters['fecha_desde'], filters['fecha_hasta'],  # fecha_emision
                    filters['fecha_desde'], filters['fecha_hasta'],  # fecha_vencimiento
                    filters['fecha_desde'], filters['fecha_hasta'],  # vig_desde
                    filters['fecha_desde'], filters['fecha_hasta']   # vig_hasta
                ])
            elif filters['fecha_desde']:
                # Solo fecha desde: cualquier fecha >= fecha_desde
                query += """ AND (
                    p.fecha_emision >= %s OR
                    p.fecha_vencimiento >= %s OR
                    p.vig_desde >= %s OR
                    p.vig_hasta >= %s
                )"""
                params.extend([
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
                    p.vig_hasta <= %s
                )"""
                params.extend([
                    filters['fecha_hasta'],
                    filters['fecha_hasta'],
                    filters['fecha_hasta'],
                    filters['fecha_hasta']
                ])

            query += " ORDER BY p.fecha_emision DESC, p.vig_desde DESC"

            cur.execute(query, params)
            polizas = cur.fetchall() or []
            print(f"[DEBUG] Pólizas encontradas: {len(polizas)}")
        else:
            print(f"[DEBUG] No se encontró el cliente con los filtros proporcionados")

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
        cur.execute("SELECT nombre_corto FROM aseguradoras WHERE nombre_corto IS NOT NULL AND nombre_corto != '' ORDER BY nombre_corto")
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
