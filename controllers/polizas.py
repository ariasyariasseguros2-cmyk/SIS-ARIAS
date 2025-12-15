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