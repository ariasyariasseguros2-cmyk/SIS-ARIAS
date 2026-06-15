def _date_to_sortable_int(value) -> int:
    if not value:
        return 0
    if hasattr(value, 'year'):
        return value.year * 10000 + value.month * 100 + value.day

    raw = str(value).strip()
    if '/' in raw:
        parts = raw.split('/')
        if len(parts) == 3:
            try:
                return int(parts[2]) * 10000 + int(parts[1]) * 100 + int(parts[0])
            except Exception:
                return 0
    if '-' in raw:
        parts = raw.split('-')
        if len(parts) == 3:
            try:
                return int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
            except Exception:
                return 0
    return 0


def _dedupe_poliza_rows(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    best_rows: dict[str, dict] = {}
    for row in rows:
        poliza = str(row.get('poliza') or '').strip()
        if not poliza:
            continue

        current = best_rows.get(poliza)
        if current is None:
            best_rows[poliza] = row
            continue

        candidate_key = (
            _date_to_sortable_int(row.get('vig_hasta')),
            _date_to_sortable_int(row.get('vig_desde')),
            _date_to_sortable_int(row.get('fecha_emision')),
            int(row.get('idPoliza') or 0),
        )
        current_key = (
            _date_to_sortable_int(current.get('vig_hasta')),
            _date_to_sortable_int(current.get('vig_desde')),
            _date_to_sortable_int(current.get('fecha_emision')),
            int(current.get('idPoliza') or 0),
        )
        if candidate_key > current_key:
            best_rows[poliza] = row

    deduped_rows = []
    seen = set()
    for row in rows:
        poliza = str(row.get('poliza') or '').strip()
        if not poliza:
            deduped_rows.append(row)
            continue
        if poliza in seen:
            continue
        seen.add(poliza)
        deduped_rows.append(best_rows[poliza])

    return deduped_rows


def filter_polizas_rapido(filter_type: str) -> dict:
    """Filtros rápidos del listado:
    - 'vigentes': vig_desde <= HOY <= vig_hasta
    - 'vencen-mes': fecha_vencimiento dentro del mes actual
    """
    rows = []
    try:
        from models.db import get_connection
        from flask import session
        from utils.rbac import Roles
        from datetime import date, timedelta
        import calendar

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        role_name = session.get('role_name')
        username = session.get('user')

        user_filter_sql = ""
        user_filter_params = []

        if role_name == Roles.SUB_AGENTE and username:
            cur.execute(
                "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s",
                (username,)
            )
            u_row = cur.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else username) or username
            user_filter_sql = " AND (p.usuario_registro = %s OR p.usuario_registro = %s OR p.sub_agente = %s OR p.sub_agente = %s)"
            user_filter_params = [username, nombre_usuario, username, nombre_usuario]

        base_select = """
            SELECT 
                p.idPoliza,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS contratante,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.asegurado, @SIS_KEY) AS CHAR),
                    p.asegurado
                ) AS asegurado,
                p.cia,
                p.ramo,
                p.ramos_producto AS producto,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                    p.poliza
                ) AS poliza,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
                    p.nro
                ) AS nro,
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
            WHERE p.activo = 1 AND p.anulado = 0 AND COALESCE(p.prima_anulada, 0) = 0
        """

        today = date.today()
        params = []

        if filter_type == 'vigentes':
            # Vigentes: vig_desde <= hoy <= vig_hasta
            sql = base_select + " AND p.vig_desde <= %s AND p.vig_hasta >= %s"
            params = [today, today]

        elif filter_type == 'vencen-mes':
            # Vencen este mes: fecha_vencimiento dentro del mes actual
            first_day = today.replace(day=1)
            last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            sql = base_select + " AND p.fecha_vencimiento BETWEEN %s AND %s"
            params = [first_day, last_day]

        else:
            return {'rows': []}

        if user_filter_sql:
            sql += user_filter_sql
            params.extend(user_filter_params)

        sql += " ORDER BY p.vig_hasta ASC LIMIT 500"

        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []

        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''

        rows = _dedupe_poliza_rows(rows)

        cur.close()
        cnx.close()
    except Exception as e:
        print(f"Error filter_polizas_rapido: {e}")
        rows = []

    return {'rows': rows}


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
            cur.execute("SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s", (username,))
            u_row = cur.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else username) or username
            
            # Filter by creator or assigned sub_agente
            user_filter_sql = " AND (p.usuario_registro = %s OR p.usuario_registro = %s OR p.sub_agente = %s OR p.sub_agente = %s)"
            user_filter_params = [username, nombre_usuario, username, nombre_usuario]

        # Base query (con campos desencriptados para visualización y búsqueda)
        sql = """
            SELECT 
                p.idPoliza,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS contratante,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.asegurado, @SIS_KEY) AS CHAR),
                    p.asegurado
                ) AS asegurado,
                p.cia,
                p.ramo,
                p.ramos_producto AS producto,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                    p.poliza
                ) AS poliza,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
                    p.nro
                ) AS nro,
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
            WHERE p.activo = 1 AND p.anulado = 0 AND COALESCE(p.prima_anulada, 0) = 0
        """
        params = []
        query = (query or '').strip()
        q = f"%{query}%"
        query_no_space = query.replace(' ', '')
        q_no_space = f"%{query_no_space}%"
        
        # Expresiones desencriptadas para filtros textuales
        poliza_expr = """CONVERT(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                CAST(p.poliza AS CHAR)
            ) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci"""
        asegurado_expr = """CONVERT(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(p.asegurado, @SIS_KEY) AS CHAR),
                CAST(p.asegurado AS CHAR)
            ) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci"""
        razon_expr = """CONVERT(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                CAST(c.razon_social AS CHAR)
            ) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci"""
        nro_expr = """CONVERT(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
                CAST(p.nro AS CHAR)
            ) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci"""
        contrato_expr = """CONVERT(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(p.contrato_nro), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(p.contrato_nro, @SIS_KEY) AS CHAR),
                CAST(p.contrato_nro AS CHAR)
            ) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci"""
        asegurada_expr = "CONVERT(CAST(p.asegurada AS CHAR) USING utf8mb4) COLLATE utf8mb4_0900_ai_ci"

        if search_type == 'historica':
            sql += f""" AND (
                {poliza_expr} LIKE %s
                OR REPLACE({poliza_expr}, ' ', '') LIKE %s
                OR CAST(p.poliza AS CHAR) LIKE %s
                OR REPLACE(CAST(p.poliza AS CHAR), ' ', '') LIKE %s
            )"""
            params.extend([q, q_no_space, q, q_no_space])
        elif search_type == 'aviso':
            sql += f" AND ({nro_expr} LIKE %s OR {contrato_expr} LIKE %s)"
            params.extend([q, q])
        elif search_type == 'placa':
            sql += f" AND ({asegurada_expr} LIKE %s)"
            params.append(q)
        elif search_type == 'titular':
            sql += f" AND ({razon_expr} LIKE %s OR {asegurado_expr} LIKE %s)"
            params.extend([q, q])
        else:  # General
            sql += f""" AND (
                {poliza_expr} LIKE %s OR 
                REPLACE({poliza_expr}, ' ', '') LIKE %s OR
                {razon_expr} LIKE %s OR 
                {asegurado_expr} LIKE %s OR 
                {asegurada_expr} LIKE %s OR
                {nro_expr} LIKE %s
            )"""
            params.extend([q, q_no_space, q, q, q, q])
            
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

        rows = _dedupe_poliza_rows(rows)
            
        cur.close()
        cnx.close()
    except Exception as e:
        print(f"Error searching polizas: {e}")
        rows = []

    return {
        'rows': rows
    }
