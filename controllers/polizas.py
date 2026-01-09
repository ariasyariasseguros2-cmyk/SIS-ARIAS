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

        cur.close()
        cnx.close()
    except Exception:
        rows = []
        details = {'nombre_completo': '', 'tipo_documento': '', 'numero_documento': '', 'telefono': ''}

    return {
        'title': 'Pólizas',
        'rows': rows,
        'details': details,
    }

# NUEVO: listar TODAS las pólizas (ignora cliente seleccionado)
def get_polizas_all() -> dict:
    rows = []
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        # Primero intentamos con el SP, si existe
        try:
            cur.execute("CALL sp_list_polizas_all()")
            rows = cur.fetchall() or []
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass
        except Exception:
            # Fallback directo si el SP no existe
            cur.execute("""
                SELECT 
                    c.razon_social AS contratante,
                    p.asegurado,
                    p.cia,
                    p.ramo,
                    p.ramos_producto AS producto,
                    p.poliza,
                    p.nro,
                    p.moneda,
                    DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
                    DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
                    p.sub_agente,
                    p.asegurada
                FROM polizas p
                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                ORDER BY p.creado_en DESC
            """)
            rows = cur.fetchall() or []

        # Normalizar 'producto' si hiciera falta
        for r in rows:
            r['producto'] = r.get('producto') or r.get('ramos_producto') or ''

        cur.close()
        cnx.close()
    except Exception:
        rows = []

    return {
        'title': 'Pólizas',
        'rows': rows,
        'details': {},  # listado global no necesita cabecera de cliente
    }