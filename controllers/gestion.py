from models.db import get_connection

def get_gestion_rows(fecha_desde=None, fecha_hasta=None, orden_fechas='ASC'):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Parámetros para la consulta
        params = []
        
        # Consulta base
        # Se asegura que fecha_pago sea NULL (no pagado)
        query = """
            SELECT 
                c.idCuota,
                c.cupon,
                c.fecha_vencimiento,
                COALESCE(cl.razon_social, 'Sin Contratante') as contratante,
                p.poliza,
                p.cia as compania,
                COALESCE(p.ramos_producto, p.ramo) as producto,
                p.forma_pago,
                c.numero_cuota,
                c.moneda,
                c.importe
            FROM cuotas c
            INNER JOIN polizas p ON c.poliza_id = p.idPoliza
            LEFT JOIN clientes cl ON p.cliente_id = cl.idCliente
            WHERE c.activo = 1 AND c.fecha_pago IS NULL
        """
        
        # Agregar filtros de fecha si existen
        # Aseguramos que los parámetros sean cadenas limpias y no vacías
        if fecha_desde:
            fecha_desde_str = str(fecha_desde).strip()
            if fecha_desde_str:
                query += " AND c.fecha_vencimiento >= %s"
                params.append(fecha_desde_str)
            
        if fecha_hasta:
            fecha_hasta_str = str(fecha_hasta).strip()
            if fecha_hasta_str:
                query += " AND c.fecha_vencimiento <= %s"
                params.append(fecha_hasta_str)
            
        # Ordenar
        if orden_fechas and orden_fechas.upper() == 'DESC':
            query += " ORDER BY c.fecha_vencimiento DESC, c.idCuota DESC"
        else:
            query += " ORDER BY c.fecha_vencimiento ASC, c.idCuota ASC"
            
        # Límite
        query += " LIMIT 500"
        
        # Debug logging
        # print(f"DEBUG QUERY: {query}")
        # print(f"DEBUG PARAMS: {params}")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Formatear fechas y moneda para la vista
        for row in rows:
            if row['fecha_vencimiento']:
                row['fecha_vencimiento'] = row['fecha_vencimiento'].strftime('%d-%m-%Y')
            
            # Asegurar símbolo de moneda
            if row['moneda'] == 'SOLES':
                row['moneda_simbolo'] = 'S/.'
            elif row['moneda'] == 'DOLARES':
                row['moneda_simbolo'] = 'US$'
            else:
                row['moneda_simbolo'] = row['moneda']

        cursor.close()
        conn.close()
        
        return rows
    except Exception as e:
        print(f"Error getting gestion rows: {e}")
        return []
