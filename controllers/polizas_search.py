
def search_polizas_global(query: str, search_type: str) -> dict:
    rows = []
    try:
        from models.db import get_connection
        from flask import session
        from utils.rbac import Roles

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        # Determine Role Context
        role_name = session.get('role_name')
        username = session.get('user')
        
        user_filter_sql = ""
        user_filter_params = []

        if role_name == Roles.SUB_AGENTE and username:
            # Get user's full name for sub_agente match
            cur.execute("SELECT nombre FROM usuarios WHERE username = %s", (username,))
            u_row = cur.fetchone()
            nombre_usuario = u_row['nombre'] if u_row else username
            
            # Filter by creator or assigned sub_agente
            user_filter_sql = " AND (p.usuario_registro = %s OR p.sub_agente = %s)"
            user_filter_params = [username, nombre_usuario]

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
            WHERE p.activo = 1 AND p.anulado = 0
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
            
        # Apply User Filter (RLS)
        if user_filter_sql:
            sql += user_filter_sql
            params.extend(user_filter_params)

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
