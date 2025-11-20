def get_polizas_data(selected: dict | None = None) -> dict:
    rows = []
    details = {}
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        numero = (selected or {}).get('n_doc') or (selected or {}).get('numero_documento')
        if numero:
            cur.execute("CALL sp_list_polizas_por_numero(%s)", (numero,))
            rows = cur.fetchall() or []
            details = {
                'nombre_completo': (selected.get('razon_social') or selected.get('nombre') or ''),
                'tipo_documento': selected.get('tipo_doc') or '',
                'numero_documento': numero,
                'telefono': selected.get('tel') or '',
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