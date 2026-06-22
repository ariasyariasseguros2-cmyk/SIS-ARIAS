from models.db import get_connection
from utils.financiamiento_grupal_reportes import enrich_rows_with_fg_metadata

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
                p.idPoliza AS idPoliza,
                c.financiamiento_grupal_id,
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
            LEFT JOIN (
                SELECT
                    MAX(idPoliza) AS idPoliza,
                    TRIM(
                        COALESCE(
                            CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4),
                            poliza
                        ) COLLATE utf8mb4_0900_ai_ci
                    ) AS poliza_plain
                FROM polizas
                WHERE activo = 1
                  AND (anulado = 0 OR anulado IS NULL)
                  AND COALESCE(prima_anulada, 0) = 0
                GROUP BY poliza_plain
            ) p_lookup
              ON c.poliza_id IS NULL
             AND TRIM(
                    COALESCE(
                        CONVERT(AES_DECRYPT(FROM_BASE64(c.poliza), @SIS_KEY) USING utf8mb4),
                        c.poliza
                    ) COLLATE utf8mb4_0900_ai_ci
                 ) = p_lookup.poliza_plain
            LEFT JOIN (
                SELECT
                    i.financiamiento_grupal_id,
                    MIN(i.poliza_id) AS poliza_id
                FROM financiamiento_grupal_avisos i
                INNER JOIN polizas p2 ON p2.idPoliza = i.poliza_id
                WHERE i.activo = 1
                  AND p2.activo = 1
                  AND (p2.anulado = 0 OR p2.anulado IS NULL)
                  AND COALESCE(p2.prima_anulada, 0) = 0
                GROUP BY i.financiamiento_grupal_id
            ) fg_lookup
              ON c.poliza_id IS NULL
             AND COALESCE(c.financiamiento_grupal_id, 0) > 0
             AND fg_lookup.financiamiento_grupal_id = c.financiamiento_grupal_id
            INNER JOIN polizas p ON p.idPoliza = COALESCE(c.poliza_id, p_lookup.idPoliza, fg_lookup.poliza_id)
            LEFT JOIN clientes cl ON p.cliente_id = cl.idCliente
            WHERE c.activo = 1
              AND c.fecha_pago IS NULL
              AND p.activo = 1
              AND (p.anulado = 0 OR p.anulado IS NULL)
              AND COALESCE(p.prima_anulada, 0) = 0
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

        # Ordenar
        if orden_fechas and orden_fechas.upper() == 'DESC':
            query += " ORDER BY c.fecha_vencimiento DESC, c.idCuota DESC"
        else:
            # Priorizar fechas no nulas y las más antiguas primero
            # Para fechas iguales, mostrar los registros más recientes primero
            query += " ORDER BY (c.fecha_vencimiento IS NULL), c.fecha_vencimiento ASC, c.idCuota DESC"

        # Paginación
        rows_params = list(params)
        use_python_search = bool(search_str)
        total = 0
        if not use_python_search:
            count_query = f"SELECT COUNT(*) AS total FROM ({query}) AS T"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total'] if cursor.rowcount is not None else 0

        if not use_python_search and isinstance(limit, int) and limit > 0:
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
        enrich_rows_with_fg_metadata(rows, poliza_id_keys=("idPoliza", "poliza_id"))
        
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
            if row.get('es_financiamiento_grupal') and row.get('poliza_fg_numero'):
                row['poliza'] = f"{row.get('poliza_fg_prefijo') or 'FG-'}{row.get('poliza_fg_numero')}"
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

        if use_python_search:
            needle = search_str.lower()
            rows = [
                row for row in rows
                if needle in str(row.get('poliza') or '').lower()
                or needle in str(row.get('cupon') or '').lower()
                or needle in str(row.get('polizas_relacionadas') or '').lower()
            ]
            total = len(rows)
            if isinstance(limit, int) and limit > 0:
                try:
                    page = int(page) if page else 1
                except Exception:
                    page = 1
                page = max(1, page)
                offset = (page - 1) * limit
                rows = rows[offset:offset + limit]

        cursor.close()  
        conn.close()
        
        return {'rows': rows, 'total': total}
    except Exception as e:
        print(f"Error getting gestion rows: {e}")
        return {'rows': [], 'total': 0}
