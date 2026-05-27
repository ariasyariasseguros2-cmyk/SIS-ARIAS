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

        if not rows and pol:
            try:
                cur.execute(
                    """
                    SELECT
                        p.idPoliza,
                        p.recibo,
                        p.recibo AS cupon,
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                            p.poliza
                        ) AS poliza,
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                            c.razon_social
                        ) AS contratante,
                        p.cia AS compania,
                        p.ramo,
                        p.tipo_doc AS tipo,
                        p.prima_comercial,
                        p.prima_neta,
                        p.prima_comercial_igv,
                        p.moneda,
                        DATE_FORMAT(p.fecha_vencimiento, '%d/%m/%Y') AS fecha_vencimiento,
                        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
                        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
                            p.nro
                        ) AS nro_operacion,
                        p.motivo AS motivo
                    FROM polizas p
                    INNER JOIN clientes c ON c.idCliente = p.cliente_id
                    WHERE (
                            CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                         OR CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR)            COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                         OR p.poliza COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                    )
                      AND p.activo = 1 AND (p.anulado = 0 OR p.anulado IS NULL)
                    ORDER BY p.vig_desde DESC
                    """,
                    (pol, pol, pol),
                )
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

    from datetime import date, datetime

    def parse_vig_inicio(v):
        if not v:
            return date.min
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        s = str(v).strip()
        if not s:
            return date.min
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y', '%Y/%m/%d'):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return date.min

    normalized.sort(key=lambda x: parse_vig_inicio(x.get('vig_inicio')), reverse=True)

    return {
        'title': 'Primas / Plan de Pagos',
        'rows': normalized,
        'details': details,
    }

def delete_prima_route():
    from flask import request, session
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        if not data:
            data = {}
        pid = data.get('idPrima') or data.get('idPoliza') or data.get('id')
        if not pid:
            return {'ok': False, 'errors': ['ID requerido']}, 400

        user_session = session.get('user', {})
        if isinstance(user_session, dict):
            usuario = user_session.get('username', 'sistema')
        elif isinstance(user_session, str):
            usuario = user_session
        else:
            usuario = 'sistema'

        from models.db import get_connection
        cnx = get_connection()
        if not cnx:
            return {'ok': False, 'errors': ['Error de conexión a BD']}, 500
        cur = cnx.cursor(dictionary=True)
        poliza_numero = None
        cupon_numero = None
        try:
            cur.execute(
                """
                SELECT
                    TRIM(
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                            CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                            poliza
                        )
                    ) AS poliza_numero,
                    TRIM(
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                            CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                            recibo
                        )
                    ) AS cupon_numero
                FROM polizas
                WHERE idPoliza = %s
                LIMIT 1
                """,
                (pid,),
            )
            r = cur.fetchone() or {}
            poliza_numero = (r.get('poliza_numero') or '').strip() or None
            cupon_numero = (r.get('cupon_numero') or '').strip() or None
        except Exception:
            poliza_numero = (data.get('poliza') or '').strip() or None
            cupon_numero = (data.get('aviso') or data.get('cupon') or '').strip() or None

        affected_rows = 0
        try:
            cur.execute(
                "UPDATE polizas SET activo = 0, usuario_edicion = %s WHERE idPoliza = %s AND activo = 1",
                (usuario, pid),
            )
            affected_rows = cur.rowcount or 0
        except Exception:
            affected_rows = 0

        cuotas_affected = 0
        if cupon_numero:
            try:
                if poliza_numero:
                    cur.execute(
                        """
                        UPDATE cuotas
                        SET activo = 0,
                            usuario_edicion = %s
                        WHERE activo = 1
                          AND (
                                (
                                    poliza_id = %s
                                    AND TRIM(
                                            COALESCE(
                                                CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                                CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                                cupon
                                            )
                                        ) COLLATE utf8mb4_0900_ai_ci = (%s COLLATE utf8mb4_0900_ai_ci)
                                )
                                OR (
                                    TRIM(
                                            COALESCE(
                                                CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                                CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                                poliza
                                            )
                                        ) COLLATE utf8mb4_0900_ai_ci = (%s COLLATE utf8mb4_0900_ai_ci)
                                    AND TRIM(
                                            COALESCE(
                                                CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                                CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                                cupon
                                            )
                                        ) COLLATE utf8mb4_0900_ai_ci = (%s COLLATE utf8mb4_0900_ai_ci)
                                )
                            )
                        """,
                        (usuario, pid, cupon_numero, poliza_numero, cupon_numero),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE cuotas
                        SET activo = 0,
                            usuario_edicion = %s
                        WHERE activo = 1
                          AND poliza_id = %s
                          AND TRIM(
                                COALESCE(
                                    CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                    CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                    cupon
                                )
                            ) COLLATE utf8mb4_0900_ai_ci = (%s COLLATE utf8mb4_0900_ai_ci)
                        """,
                        (usuario, pid, cupon_numero),
                    )
                cuotas_affected = (cur.rowcount or 0)
            except Exception:
                cuotas_affected = 0

        cnx.commit()
        cur.close()
        cnx.close()
        if affected_rows > 0 or cuotas_affected > 0:
            return {'ok': True}
        return {'ok': False, 'errors': ['No encontrado o ya eliminado']}, 404
    except Exception as e:
        return {'ok': False, 'errors': [str(e)]}, 500
