def get_primas_data(selected: dict | None = None, numero_poliza: str | None = None) -> dict:
    rows = []
    details = {
        'ejecutivo': '',
        'poliza': numero_poliza or (selected or {}).get('poliza') or (selected or {}).get('numero_poliza') or '',
        'asegurado': (selected or {}).get('razon_social') or (selected or {}).get('asegurado') or '',
        'vig_desde': '',
        'vig_hasta': '',
    }
    try:    
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        pol = details['poliza']
        cliente_id = (selected or {}).get('idCliente')

        # Intento por número de póliza
        if pol:
            try:
                cur.execute("CALL sp_list_primas_por_poliza(%s)", (pol,))
                rows = cur.fetchall() or []
                while cur.nextset():
                    pass
            except Exception:
                rows = rows

        # Intento por cliente
        if not rows and cliente_id:
            try:
                cur.execute("CALL sp_list_primas_por_cliente_id(%s)", (cliente_id,))
                rows = cur.fetchall() or []
                while cur.nextset():
                    pass
            except Exception:
                rows = rows

        # Si no hay poliza definida pero hay resultados, tomamos la poliza del primer resultado
        if not pol and rows:
            pol = rows[0].get('poliza') or rows[0].get('numero_poliza')
            if pol:
                details['poliza'] = pol

        # Encabezado de vigencia/ejecutivo si hay un SP disponible
        if pol:
            try:
                cur.execute("CALL sp_get_poliza_detalle_por_numero(%s)", (pol,))
                det = cur.fetchone() or {}
                while cur.nextset():
                    pass
                details['ejecutivo'] = det.get('ejecutivo') or det.get('Ejecutivo') or details['ejecutivo']
                details['asegurado'] = det.get('asegurado') or details['asegurado']
                details['vig_desde'] = det.get('vig_desde') or details['vig_desde']
                details['vig_hasta'] = det.get('vig_hasta') or details['vig_hasta']
            except Exception:
                pass

        cur.close()
        cnx.close()
    except Exception:
        rows = rows
        details = details

    # Normalización de claves a las usadas por la plantilla
    normalized = []
    for r in rows:
        normalized.append({
            # Aviso debe ser el recibo
            'aviso': r.get('recibo') or r.get('aviso') or r.get('nro_aviso'),
            'poliza': r.get('poliza') or r.get('numero_poliza'),
            'contratante': r.get('contratante'),
            'compania': r.get('compania') or r.get('cia'),
            'ramo': r.get('ramo'),
            'tipo': r.get('tipo') or r.get('tipo_mov'),
            'prima_comercial': r.get('prima_comercial'),
            'prima_neta': r.get('prima_neta'),
            # Total debe mostrar prima_comercial_igv
            'prima_total': r.get('prima_comercial_igv') or r.get('prima_total'),
            'vig_inicio': r.get('vig_inicio') or r.get('vig_desde'),
            'vig_fin': r.get('vig_fin') or r.get('vig_hasta'),
            'nro_operacion': r.get('nro_operacion') or r.get('operacion'),
            'motivo': r.get('motivo') or '',
            'pdf_url': r.get('pdf_url') or '',
            'idPrima': r.get('idPoliza') or r.get('idPrima') # idPoliza identifies the row
        })

    return {
        'title': 'Primas / Plan de Pagos',
        'rows': normalized,
        'details': details,
    }
