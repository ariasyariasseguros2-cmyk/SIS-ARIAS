def _enriquecer_con_ultima_renovacion(rows, cur):
    """Agrega campos ren_vig_desde y ren_vig_hasta con la última renovación (tipo_doc RENOVACION) por número de póliza."""
    if not rows:
        return rows

    try:
        polizas_numeros = []
        for r in rows:
            p = str(r.get('poliza') or '').strip()
            if p and p not in polizas_numeros:
                polizas_numeros.append(p)

        if not polizas_numeros:
            for r in rows:
                r['ren_vig_desde'] = ''
                r['ren_vig_hasta'] = ''
            return rows

        ren_map = {}
        batch_size = 200
        for i in range(0, len(polizas_numeros), batch_size):
            batch = polizas_numeros[i:i + batch_size]
            ph = ",".join(["%s"] * len(batch))
            params_like = []
            for pz in batch:
                params_like.extend([pz, pz, pz])
            sql = f"""
                SELECT
                    TRIM(COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                        p.poliza
                    )) AS poliza,
                    DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS ren_vig_desde,
                    DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS ren_vig_hasta,
                    p.vig_hasta AS _raw_vig_hasta,
                    p.vig_desde AS _raw_vig_desde
                FROM polizas p
                WHERE (
                    TRIM(COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                        p.poliza
                    )) COLLATE utf8mb4_0900_ai_ci IN ({ph})
                )
                AND (p.activo = 1 OR p.activo IS NULL) AND (p.anulado = 0 OR p.anulado IS NULL)
                AND UPPER(TRIM(COALESCE(p.tipo_doc, ''))) = 'RENOVACION'
            """
            try:
                cur.execute(sql, tuple(batch))
            except Exception:
                sql_fallback = f"""
                    SELECT
                        TRIM(COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                            p.poliza
                        )) AS poliza,
                        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS ren_vig_desde,
                        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS ren_vig_hasta,
                        p.vig_hasta AS _raw_vig_hasta,
                        p.vig_desde AS _raw_vig_desde
                    FROM polizas p
                    WHERE (
                        CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                        OR CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                        OR p.poliza COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                    )
                    AND (p.activo = 1 OR p.activo IS NULL) AND (p.anulado = 0 OR p.anulado IS NULL)
                    AND UPPER(TRIM(COALESCE(p.tipo_doc, ''))) = 'RENOVACION'
                """
                ren_rows_all = []
                for pz in batch:
                    try:
                        cur.execute(sql_fallback, (pz, pz, pz))
                        ren_rows_all.extend(cur.fetchall() or [])
                        while cur.nextset():
                            pass
                    except Exception:
                        pass
                ren_rows = ren_rows_all
            else:
                ren_rows = cur.fetchall() or []
                try:
                    while cur.nextset():
                        pass
                except Exception:
                    pass

            for rr in ren_rows:
                p_key = str(rr.get('poliza') or '').strip()
                if not p_key:
                    continue
                raw_vh = rr.get('_raw_vig_hasta')
                raw_vd = rr.get('_raw_vig_desde')
                def _cmp_val(d):
                    if not d:
                        return 0
                    if hasattr(d, 'year'):
                        return d.year * 10000 + d.month * 100 + d.day
                    s = str(d).strip()
                    if '/' in s:
                        parts = s.split('/')
                        if len(parts) == 3:
                            try:
                                return int(parts[2]) * 10000 + int(parts[1]) * 100 + int(parts[0])
                            except Exception:
                                pass
                    if '-' in s:
                        parts = s.split('-')
                        if len(parts) == 3:
                            try:
                                return int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
                            except Exception:
                                pass
                    return 0
                curr_vh = _cmp_val(raw_vh)
                curr_vd = _cmp_val(raw_vd)
                if p_key not in ren_map:
                    ren_map[p_key] = {
                        'ren_vig_desde': rr.get('ren_vig_desde') or '',
                        'ren_vig_hasta': rr.get('ren_vig_hasta') or '',
                        '_vh': curr_vh,
                        '_vd': curr_vd,
                    }
                else:
                    existing = ren_map[p_key]
                    if curr_vh > existing['_vh'] or (curr_vh == existing['_vh'] and curr_vd > existing['_vd']):
                        ren_map[p_key] = {
                            'ren_vig_desde': rr.get('ren_vig_desde') or '',
                            'ren_vig_hasta': rr.get('ren_vig_hasta') or '',
                            '_vh': curr_vh,
                            '_vd': curr_vd,
                        }

        for r in rows:
            p_key = str(r.get('poliza') or '').strip()
            ren = ren_map.get(p_key)
            if ren:
                r['ren_vig_desde'] = ren['ren_vig_desde']
                r['ren_vig_hasta'] = ren['ren_vig_hasta']
            else:
                r['ren_vig_desde'] = ''
                r['ren_vig_hasta'] = ''

    except Exception:
        for r in rows:
            r['ren_vig_desde'] = r.get('ren_vig_desde') or ''
            r['ren_vig_hasta'] = r.get('ren_vig_hasta') or ''

    return rows


def get_polizas_data(selected: dict | None = None) -> dict:
    rows = []
    details = {}
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        cliente_id = (selected or {}).get('idCliente')
        numero = (selected or {}).get('n_doc') or (selected or {}).get('numero_documento')

        if cliente_id:
            # Preferir listado por ID
            cur.execute("CALL sp_list_polizas_por_cliente_id(%s)", (cliente_id,))
            rows = cur.fetchall() or []
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass

            # Datos del cliente por ID (si existe el SP)
            try:
                cur.execute("CALL sp_get_cliente_por_id(%s)", (cliente_id,))
                cli = cur.fetchone() or {}
                while cur.nextset():
                    pass
            except Exception:
                cli = {}

            details = {
                'nombre_completo': (cli.get('razon_social') or selected.get('razon_social') or selected.get('nombre') or ''),
                'tipo_documento': (cli.get('tipo_documento') or selected.get('doc') or selected.get('tipo_doc') or selected.get('tipo_documento') or ''),
                'numero_documento': (cli.get('numero_documento') or numero or ''),
                'telefono': (cli.get('telefono') or selected.get('tel') or selected.get('telefono') or ''),
            }
        elif numero:
            cur.execute("CALL sp_list_polizas_por_numero(%s)", (numero,))
            rows = cur.fetchall() or []
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass

            cur.execute("CALL sp_get_cliente_por_numero(%s)", (numero,))
            cli = cur.fetchone() or {}
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass

            details = {
                'nombre_completo': (cli.get('razon_social') or selected.get('razon_social') or selected.get('nombre') or ''),
                'tipo_documento': (cli.get('tipo_documento') or selected.get('doc') or selected.get('tipo_doc') or selected.get('tipo_documento') or ''),
                'numero_documento': numero,
                'telefono': (cli.get('telefono') or selected.get('tel') or selected.get('telefono') or ''),
            }
        else:
            # fallback si no hay cliente seleccionado: devuelve vacío
            rows = []
            details = {'nombre_completo': '', 'tipo_documento': '', 'numero_documento': '', 'telefono': ''}

        # Normalizar clave 'producto' desde 'ramos_producto' si aplica
        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''

        # --- DEDUPLICACIÓN DE PÓLIZAS (Visualización) ---
        # Agrupar por 'poliza' y mostrar solo la de vigencia más reciente
        if rows:
            def _to_int(d):
                if not d: return 0
                if hasattr(d, 'year'): 
                    return d.year * 10000 + d.month * 100 + d.day
                s = str(d).strip()
                if '/' in s: # dd/mm/yyyy
                    parts = s.split('/')
                    if len(parts) == 3: 
                        try: return int(parts[2])*10000 + int(parts[1])*100 + int(parts[0])
                        except: pass
                if '-' in s: # yyyy-mm-dd
                    parts = s.split('-')
                    if len(parts) == 3: 
                        try: return int(parts[0])*10000 + int(parts[1])*100 + int(parts[2])
                        except: pass
                return 0

            best_rows = {}
            for r in rows:
                p = str(r.get('poliza') or '')
                if not p: continue
                
                if p not in best_rows:
                    best_rows[p] = r
                else:
                    curr = best_rows[p]
                    # Comparar vig_hasta (mayor es más reciente)
                    if _to_int(r.get('vig_hasta')) > _to_int(curr.get('vig_hasta')):
                        best_rows[p] = r
                    elif _to_int(r.get('vig_hasta')) == _to_int(curr.get('vig_hasta')):
                        # Desempate con vig_desde
                        if _to_int(r.get('vig_desde')) > _to_int(curr.get('vig_desde')):
                            best_rows[p] = r

            # Reconstruir lista manteniendo orden de aparición
            new_rows = []
            seen = set()
            for r in rows:
                p = str(r.get('poliza') or '')
                if not p:
                    new_rows.append(r)
                    continue
                if p not in seen:
                    seen.add(p)
                    new_rows.append(best_rows[p])
            rows = new_rows

        rows = _enriquecer_con_ultima_renovacion(rows, cur)

        cur.close()
        cnx.close()
    except Exception:
        rows = []
        details = {'nombre_completo': '', 'tipo_documento': '', 'numero_documento': '', 'telefono': ''}
        for r in rows:
            r['ren_vig_desde'] = r.get('ren_vig_desde') or ''
            r['ren_vig_hasta'] = r.get('ren_vig_hasta') or ''

    return {
        'title': 'Pólizas',
        'rows': rows,
        'details': details,
    }


def get_poliza_owner_by_id(idPoliza):
    """Devuelve el owner (usuario_registro o sub_agente) de la póliza indicada."""
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT usuario_registro, sub_agente FROM polizas WHERE idPoliza=%s LIMIT 1", (idPoliza,))
        row = cur.fetchone() or {}
        try:
            while cur.nextset():
                pass
        except Exception:
            pass
        cur.close()
        cnx.close()
        owner = row.get('usuario_registro') or row.get('sub_agente')
        return owner
    except Exception:
        return None

# NUEVO: listar TODAS las pólizas (ignora cliente seleccionado)
def get_polizas_all() -> dict:
    rows = []
    try:
        from models.db import get_connection
        from flask import session
        from utils.rbac import Roles

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        # RLS Filter Logic
        rls_filter = ""
        rls_params = []
        
        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            # Get user's full name for sub_agente match if needed, or use username
            # Assuming sub_agente column might store username or name. 
            # Consistent with polizas_search.py logic:
            cur.execute("SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s", (user,))
            u_row = cur.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else user) or user
            
            rls_filter = " AND (p.usuario_registro = %s OR p.usuario_registro = %s OR p.sub_agente = %s OR p.sub_agente = %s) "
            rls_params = [user, nombre_usuario, user, nombre_usuario]

        # Primero intentamos con el SP, si existe
        # Nota: SP sp_list_polizas_all generalmente no acepta params de filtro RLS dinámico.
        # Si es Sub Agente, forzamos el uso de SQL directo para aplicar RLS.
        use_sp = (rls_filter == "")
        
        if use_sp:
            try:
                cur.execute("CALL sp_list_polizas_all()")
                rows = cur.fetchall() or []
                try:
                    while cur.nextset(): pass
                except: pass
            except Exception:
                use_sp = False # Fallback to SQL

        if not use_sp:
            # Fallback directo o RLS aplicado
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
                    p.asegurada
                FROM polizas p
                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                WHERE (p.activo = 1 OR p.activo IS NULL) AND (p.anulado = 0 OR p.anulado IS NULL)
            """ + rls_filter + """
                ORDER BY p.creado_en DESC
            """
            cur.execute(sql, tuple(rls_params))
            rows = cur.fetchall() or []

        # Normalizar 'producto' si hiciera falta
        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''

        # --- DEDUPLICACIÓN DE PÓLIZAS (Visualización) ---
        # Agrupar por 'poliza' y mostrar solo la de vigencia más reciente
        if rows:
            def _to_int(d):
                if not d: return 0
                if hasattr(d, 'year'): 
                    return d.year * 10000 + d.month * 100 + d.day
                s = str(d).strip()
                if '/' in s: # dd/mm/yyyy
                    parts = s.split('/')
                    if len(parts) == 3: 
                        try: return int(parts[2])*10000 + int(parts[1])*100 + int(parts[0])
                        except: pass
                if '-' in s: # yyyy-mm-dd
                    parts = s.split('-')
                    if len(parts) == 3: 
                        try: return int(parts[0])*10000 + int(parts[1])*100 + int(parts[2])
                        except: pass
                return 0

            best_rows = {}
            for r in rows:
                p = str(r.get('poliza') or '')
                if not p: continue
                
                if p not in best_rows:
                    best_rows[p] = r
                else:
                    curr = best_rows[p]
                    # Comparar vig_hasta (mayor es más reciente)
                    if _to_int(r.get('vig_hasta')) > _to_int(curr.get('vig_hasta')):
                        best_rows[p] = r
                    elif _to_int(r.get('vig_hasta')) == _to_int(curr.get('vig_hasta')):
                        # Desempate con vig_desde
                        if _to_int(r.get('vig_desde')) > _to_int(curr.get('vig_desde')):
                            best_rows[p] = r

            # Reconstruir lista manteniendo orden de aparición
            new_rows = []
            seen = set()
            for r in rows:
                p = str(r.get('poliza') or '')
                if not p:
                    new_rows.append(r)
                    continue
                if p not in seen:
                    seen.add(p)
                    new_rows.append(best_rows[p])
            rows = new_rows

        rows = _enriquecer_con_ultima_renovacion(rows, cur)

        cur.close()
        cnx.close()
    except Exception:
        rows = []
        for r in rows:
            r['ren_vig_desde'] = r.get('ren_vig_desde') or ''
            r['ren_vig_hasta'] = r.get('ren_vig_hasta') or ''

    return {
        'title': 'Pólizas',
        'rows': rows,
        'details': {},  # listado global no necesita cabecera de cliente
    }

def get_polizas_all_paginated(page: int | None = 1, per_page: int | None = 10) -> dict:
    rows = []
    total = 0
    page_num = 1
    per_page_num = 10
    pages = 1
    try:
        from models.db import get_connection
        from flask import session
        from utils.rbac import Roles

        try:
            page_num = int(page or 1)
        except Exception:
            page_num = 1
        try:
            per_page_num = int(per_page or 10)
        except Exception:
            per_page_num = 10
        if page_num < 1:
            page_num = 1
        if per_page_num < 1:
            per_page_num = 10
        if per_page_num > 200:
            per_page_num = 200

        offset = (page_num - 1) * per_page_num

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        rls_filter = ""
        rls_params = []
        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            cur.execute("SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s", (user,))
            u_row = cur.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else user) or user
            rls_filter = " AND (p.usuario_registro = %s OR p.usuario_registro = %s OR p.sub_agente = %s OR p.sub_agente = %s) "
            rls_params = [user, nombre_usuario, user, nombre_usuario]

        base_where = " WHERE (p.activo = 1 OR p.activo IS NULL) AND (p.anulado = 0 OR p.anulado IS NULL) "

        count_sql = "SELECT COUNT(*) AS total FROM polizas p INNER JOIN clientes c ON c.idCliente = p.cliente_id " + base_where + rls_filter
        cur.execute(count_sql, tuple(rls_params))
        total_row = cur.fetchone() or {}
        try:
            total = int(total_row.get('total', 0) or 0)
        except Exception:
            total = 0
        pages = max(1, (total + per_page_num - 1) // per_page_num) if per_page_num > 0 else 1
        if page_num > pages:
            page_num = pages
            offset = (page_num - 1) * per_page_num

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
                p.asegurada
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
        """ + base_where + rls_filter + """
            ORDER BY p.creado_en DESC
            LIMIT %s OFFSET %s
        """
        page_params = list(rls_params)
        page_params.extend([per_page_num, offset])
        cur.execute(sql, tuple(page_params))
        rows = cur.fetchall() or []

        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''

        if rows:
            def _to_int(d):
                if not d: return 0
                if hasattr(d, 'year'):
                    return d.year * 10000 + d.month * 100 + d.day
                s = str(d).strip()
                if '/' in s:
                    parts = s.split('/')
                    if len(parts) == 3:
                        try: return int(parts[2])*10000 + int(parts[1])*100 + int(parts[0])
                        except: pass
                if '-' in s:
                    parts = s.split('-')
                    if len(parts) == 3:
                        try: return int(parts[0])*10000 + int(parts[1])*100 + int(parts[2])
                        except: pass
                return 0

            best_rows = {}
            for r in rows:
                p = str(r.get('poliza') or '')
                if not p: continue

                if p not in best_rows:
                    best_rows[p] = r
                else:
                    curr = best_rows[p]
                    if _to_int(r.get('vig_hasta')) > _to_int(curr.get('vig_hasta')):
                        best_rows[p] = r
                    elif _to_int(r.get('vig_hasta')) == _to_int(curr.get('vig_hasta')):
                        if _to_int(r.get('vig_desde')) > _to_int(curr.get('vig_desde')):
                            best_rows[p] = r

            new_rows = []
            seen = set()
            for r in rows:
                p = str(r.get('poliza') or '')
                if not p:
                    new_rows.append(r)
                    continue
                if p not in seen:
                    seen.add(p)
                    new_rows.append(best_rows[p])
            rows = new_rows

        rows = _enriquecer_con_ultima_renovacion(rows, cur)

        cur.close()
        cnx.close()
    except Exception:
        rows = []
        total = 0
        page_num = 1
        per_page_num = 10
        pages = 1
        for r in rows:
            r['ren_vig_desde'] = r.get('ren_vig_desde') or ''
            r['ren_vig_hasta'] = r.get('ren_vig_hasta') or ''

    return {
        'rows': rows,
        'total': total,
        'page': page_num,
        'per_page': per_page_num,
        'pages': pages,
    }


def get_polizas_anuladas() -> dict:
    rows = []
    try:
        from models.db import get_connection
        from flask import session
        from utils.rbac import Roles

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        rls_filter = ""
        rls_params = []
        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            cur.execute("SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s", (user,))
            u_row = cur.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else user) or user
            rls_filter = " AND (p.usuario_registro = %s OR p.usuario_registro = %s OR p.sub_agente = %s OR p.sub_agente = %s) "
            rls_params = [user, nombre_usuario, user, nombre_usuario]

        use_sp = (rls_filter == "")
        if use_sp:
            try:
                cur.execute("CALL sp_list_polizas_anuladas()")
                rows = cur.fetchall() or []
                try:
                    while cur.nextset(): pass
                except: pass
            except Exception:
                use_sp = False
            if use_sp:
                try:
                    base_ids = set()
                    for r in (rows or []):
                        try:
                            base_ids.add(int(r.get('idPoliza')))
                        except Exception:
                            pass

                    sql_inactivas = """
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
                                CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
                                CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
                                p.recibo
                            ) AS recibo,
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
                            p.asegurada
                        FROM polizas p
                        INNER JOIN clientes c ON c.idCliente = p.cliente_id
                        WHERE p.activo = 0
                        ORDER BY p.creado_en DESC
                    """
                    cur.execute(sql_inactivas)
                    extra = cur.fetchall() or []
                    if extra:
                        if not rows:
                            rows = []
                        for r in extra:
                            try:
                                rid = int(r.get('idPoliza'))
                            except Exception:
                                rid = None
                            if rid is None or rid not in base_ids:
                                rows.append(r)
                except Exception:
                    pass

        if not use_sp:
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
                        CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
                        p.recibo
                    ) AS recibo,
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
                    p.asegurada
                FROM polizas p
                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                WHERE (p.anulado = 1 OR p.activo = 0)
            """ + rls_filter + """
                ORDER BY p.creado_en DESC
            """
            cur.execute(sql, tuple(rls_params))
            rows = cur.fetchall() or []

        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''
            if 'recibo' not in r:
                r['recibo'] = ''

        try:
            ids = []
            for r in (rows or []):
                pid = r.get('idPoliza')
                if pid is None:
                    continue
                try:
                    ids.append(int(pid))
                except Exception:
                    continue

            if ids:
                ph = ",".join(["%s"] * len(ids))
                cur.execute(f"""
                    SELECT 
                        idPoliza,
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                            recibo
                        ) AS recibo
                    FROM polizas
                    WHERE idPoliza IN ({ph})
                """, tuple(ids))
                rec_rows = cur.fetchall() or []
                rec_map = {}
                for rr in rec_rows:
                    try:
                        rec_map[int(rr.get('idPoliza'))] = rr.get('recibo') or ''
                    except Exception:
                        pass
                for r in (rows or []):
                    try:
                        r['recibo'] = rec_map.get(int(r.get('idPoliza')), r.get('recibo') or '')
                    except Exception:
                        r['recibo'] = r.get('recibo') or ''
        except Exception:
            pass

        cur.close()
        cnx.close()
    except Exception:
        rows = []

    return {
        'title': 'Pólizas Anuladas',
        'rows': rows
    }

def get_polizas_anuladas_filtered(
    q: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    page: int | None = 1,
    per_page: int | None = 15,
) -> dict:
    rows: list[dict] = []
    total = 0
    page_num = 1
    per_page_num = 15
    pages = 1
    try:
        from models.db import get_connection
        from flask import session
        from utils.rbac import Roles

        try:
            page_num = int(page or 1)
        except Exception:
            page_num = 1
        try:
            per_page_num = int(per_page or 15)
        except Exception:
            per_page_num = 15
        if page_num < 1:
            page_num = 1
        if per_page_num < 1:
            per_page_num = 15
        if per_page_num > 200:
            per_page_num = 200

        offset = (page_num - 1) * per_page_num

        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        rls_sql = ""
        rls_params: list = []
        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            cur.execute("SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s", (user,))
            u_row = cur.fetchone()
            nombre_usuario = (u_row.get('nombre') if u_row else user) or user
            rls_sql = " AND (p.usuario_registro = %s OR p.usuario_registro = %s OR p.sub_agente = %s OR p.sub_agente = %s) "
            rls_params = [user, nombre_usuario, user, nombre_usuario]

        where_sql = " WHERE (p.anulado = 1 OR p.activo = 0) "
        params: list = []
        if q:
            like = f"%{q}%"
            where_sql += """
              AND (
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                  p.poliza
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
                  p.recibo
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                  c.razon_social
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.asegurado, @SIS_KEY) AS CHAR),
                  p.asegurado
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.asegurada), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.asegurada, @SIS_KEY) AS CHAR),
                  p.asegurada
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.ramo), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.ramo, @SIS_KEY) AS CHAR),
                  p.ramo
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.cia), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.cia, @SIS_KEY) AS CHAR),
                  p.cia
                )) LIKE %s OR
                TRIM(COALESCE(
                  CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
                  CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
                  p.nro
                )) LIKE %s
              )
            """
            params.extend([like, like, like, like, like, like, like, like])
        if desde:
            where_sql += " AND p.vig_desde >= %s "
            params.append(desde)
        if hasta:
            where_sql += " AND p.vig_hasta <= %s "
            params.append(hasta)
        where_sql += rls_sql
        params.extend(rls_params)

        count_sql = "SELECT COUNT(*) AS total FROM polizas p INNER JOIN clientes c ON c.idCliente = p.cliente_id " + where_sql
        cur.execute(count_sql, tuple(params))
        total_row = cur.fetchone() or {}
        try:
            total = int(total_row.get('total', 0) or 0)
        except Exception:
            total = 0
        pages = max(1, (total + per_page_num - 1) // per_page_num) if per_page_num > 0 else 1
        if page_num > pages:
            page_num = pages
            offset = (page_num - 1) * per_page_num

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
                    CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
                    p.recibo
                ) AS recibo,
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
                p.asegurada
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
        """ + where_sql + " ORDER BY p.creado_en DESC LIMIT %s OFFSET %s"

        page_params = list(params)
        page_params.extend([per_page_num, offset])
        cur.execute(sql, tuple(page_params))
        rows = cur.fetchall() or []
        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''

        cur.close()
        cnx.close()
    except Exception:
        rows = []
        total = 0
        page_num = 1
        per_page_num = 15
        pages = 1

    return {
        'rows': rows,
        'total': total,
        'page': page_num,
        'per_page': per_page_num,
        'pages': pages,
    }
