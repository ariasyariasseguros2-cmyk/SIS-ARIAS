
def search_polizas_global(query: str, search_type: str) -> dict:
    rows = []
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        # Base query
        sql = """
            SELECT 
                p.idPoliza,
                c.razon_social AS contratante,
                p.asegurado,
                p.cia,
                p.ramo,
                p.ramos_producto AS producto,
                p.poliza,
                p.nro,
                p.moneda,
                DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
                DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
                DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
                p.sub_agente,
                p.asegurada,
                p.usuario_registro,
                p.usuario_edicion
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
            WHERE 1=1
        """
        params = []
        q = f"%{query}%"
        
        if search_type == 'historica':
            sql += " AND (p.poliza LIKE %s)"
            params.append(q)
        elif search_type == 'aviso':
            sql += " AND (p.nro LIKE %s OR p.contrato_nro LIKE %s)"
            params.extend([q, q])
        elif search_type == 'placa':
            sql += " AND (p.asegurada LIKE %s)"
            params.append(q)
        elif search_type == 'titular':
            sql += " AND (c.razon_social LIKE %s OR p.asegurado LIKE %s)"
            params.extend([q, q])
        else: # General
            sql += """ AND (
                p.poliza LIKE %s OR 
                c.razon_social LIKE %s OR 
                p.asegurado LIKE %s OR 
                p.asegurada LIKE %s OR
                p.nro LIKE %s
            )"""
            params.extend([q, q, q, q, q])
            
        sql += " ORDER BY p.creado_en DESC LIMIT 100"
        
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
        
        # Normalizar 'producto'
        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''
            
        cur.close()
        cnx.close()
    except Exception as e:
        print(f"Error searching polizas: {e}")
        rows = []

    return {
        'rows': rows
    }
