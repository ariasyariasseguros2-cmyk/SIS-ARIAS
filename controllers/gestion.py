from models.db import get_connection

def get_gestion_rows(fecha_desde=None, fecha_hasta=None, orden_fechas='ASC', limit=None, page=1, search=None):
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
                CONVERT(
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(c.cupon, @SIS_KEY) AS CHAR),
                        c.cupon
                    ) USING utf8mb4
                ) COLLATE utf8mb4_0900_ai_ci as cupon,
                c.fecha_vencimiento,
                CONVERT(
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(cl.razon_social), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(cl.razon_social, @SIS_KEY) AS CHAR),
                        cl.razon_social,
                        'Sin Contratante'
                    ) USING utf8mb4
                ) COLLATE utf8mb4_0900_ai_ci as contratante,
                TRIM(
                    CONVERT(
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(cl.numero_documento), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(cl.numero_documento, @SIS_KEY) AS CHAR),
                            cl.numero_documento,
                            ''
                        ) USING utf8mb4
                    ) COLLATE utf8mb4_0900_ai_ci
                ) as cliente_numero_documento,
                CONVERT(
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                        p.poliza
                    ) USING utf8mb4
                ) COLLATE utf8mb4_0900_ai_ci as poliza,
                p.cia as compania,
                COALESCE(p.ramos_producto, p.ramo) as producto,
                p.vig_desde,
                p.vig_hasta,
                c.numero_cuota,
                p.moneda,
                c.importe,
                c.fecha_pago,
                c.factura,
                c.observacion
            FROM cuotas c
            INNER JOIN polizas p ON c.poliza_id = p.idPoliza
            LEFT JOIN clientes cl ON p.cliente_id = cl.idCliente
            WHERE c.activo = 1 AND c.fecha_pago IS NULL
        """
        
        fecha_desde_str = str(fecha_desde).strip() if fecha_desde else ''
        fecha_hasta_str = str(fecha_hasta).strip() if fecha_hasta else ''
        search_str = str(search).strip() if search else ''

        if fecha_desde_str and fecha_hasta_str and fecha_desde_str == fecha_hasta_str:
            query += " AND DATE(c.fecha_vencimiento) = %s"
            params.append(fecha_desde_str)
        else:
            if fecha_desde_str:
                query += " AND c.fecha_vencimiento >= %s"
                params.append(fecha_desde_str)
            if fecha_hasta_str:
                query += " AND c.fecha_vencimiento < DATE_ADD(%s, INTERVAL 1 DAY)"
                params.append(fecha_hasta_str)

        if search_str:
            like = f"%{search_str}%"
            query += """
                AND (
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR) LIKE %s
                    OR CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR) LIKE %s
                    OR p.poliza LIKE %s
                    OR CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR) LIKE %s
                    OR CAST(AES_DECRYPT(c.cupon, @SIS_KEY) AS CHAR) LIKE %s
                    OR c.cupon LIKE %s
                    OR CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR) LIKE %s
                    OR CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR) LIKE %s
                    OR p.recibo LIKE %s
                )
            """
            params += [like, like, like, like, like, like, like, like, like]
            
        # Ordenar
        if orden_fechas and orden_fechas.upper() == 'DESC':
            query += " ORDER BY c.fecha_vencimiento DESC, c.idCuota DESC"
        else:
            # Priorizar fechas no nulas y las más antiguas primero
            # Para fechas iguales, mostrar los registros más recientes primero
            query += " ORDER BY (c.fecha_vencimiento IS NULL), c.fecha_vencimiento ASC, c.idCuota DESC"
            
        # Total para paginación
        count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS T"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total'] if cursor.rowcount is not None else 0

        # Paginación
        rows_params = list(params)
        if isinstance(limit, int) and limit > 0:
            try:
                page = int(page) if page else 1
            except Exception:
                page = 1
            page = max(1, page)
            offset = (page - 1) * limit
            query += " LIMIT %s OFFSET %s"
            rows_params += [limit, offset]
        
        cursor.execute(query, rows_params)
        rows = cursor.fetchall()
        
        # Formatear fechas y moneda para la vista
        def _clean_text(value):
            if value is None:
                return value
            if isinstance(value, (bytes, bytearray)):
                try:
                    value = value.decode('utf-8', errors='ignore')
                except Exception:
                    value = value.decode(errors='ignore')
            else:
                value = str(value)
            return value.replace('\x00', '').strip()

        for row in rows:
            row['cupon'] = _clean_text(row.get('cupon'))
            row['poliza'] = _clean_text(row.get('poliza'))
            row['compania'] = _clean_text(row.get('compania'))
            row['contratante'] = _clean_text(row.get('contratante'))

            if row['fecha_vencimiento']:
                row['fecha_vencimiento'] = row['fecha_vencimiento'].strftime('%d-%m-%Y')
            if row['vig_desde']:
                row['vig_desde'] = row['vig_desde'].strftime('%d-%m-%Y')
            if row['vig_hasta']:
                row['vig_hasta'] = row['vig_hasta'].strftime('%d-%m-%Y')
            
            # Asegurar símbolo de moneda
            if row['moneda'] == 'SOLES':
                row['moneda_simbolo'] = 'S/.'
            elif row['moneda'] == 'DOLARES':
                row['moneda_simbolo'] = 'US$'
            else:
                row['moneda_simbolo'] = row['moneda']

        cursor.close()  
        conn.close()
        
        return {'rows': rows, 'total': total}
    except Exception as e:
        print(f"Error getting gestion rows: {e}")
        return {'rows': [], 'total': 0}
