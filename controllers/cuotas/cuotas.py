from typing import Dict, List, Tuple
from datetime import date, datetime


def _parse_decimal(value):
    if value is None or value == '':
        return None
    try:
        import re
        txt = str(value).strip()
        if not txt:
            return None
        m = re.search(r'[-+]?\d[\d.,]*', txt)
        if not m:
            return None
        raw = (m.group(0) or '').strip()
        if not raw:
            return None
        if raw.startswith('+'):
            raw = raw[1:]

        last_dot = raw.rfind('.')
        last_comma = raw.rfind(',')
        if last_dot == -1 and last_comma == -1:
            return float(raw)
        if last_dot > last_comma:
            cleaned = raw.replace(',', '')
        elif last_comma > last_dot:
            cleaned = raw.replace('.', '').replace(',', '.')
        else:
            sep_idx = max(last_dot, last_comma)
            int_part = ''.join(ch for ch in raw[:sep_idx] if (ch.isdigit() or ch == '-'))
            dec_part = ''.join(ch for ch in raw[sep_idx + 1:] if ch.isdigit())
            cleaned = f"{int_part}.{dec_part}" if dec_part else int_part

        if cleaned.count('.') > 1:
            sign = ''
            if cleaned.startswith('-'):
                sign = '-'
                cleaned = cleaned[1:]
            parts = cleaned.split('.')
            int_part = ''.join(parts[:-1]).replace('.', '').replace(',', '')
            dec_part = parts[-1]
            cleaned = f"{sign}{int_part}.{dec_part}" if dec_part else f"{sign}{int_part}"
        return float(cleaned)
    except Exception:
        return None


def format_date_custom(d):
    """Format date to DD/MM/YYYY"""
    if not d:
        return ''
    if isinstance(d, (date, datetime)):
        return d.strftime('%d/%m/%Y')
    
    s = str(d).strip()
    # Handle YYYY-MM-DD
    if '-' in s:
        parts = s.split('-')
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    
    # Handle DD-MM-YYYY -> DD/MM/YYYY
    if '-' in s:
        return s.replace('-', '/')
        
    return s

def parse_date_input(date_str):
    """Ensure date is in YYYY-MM-DD format for SQL comparison"""
    if not date_str:
        return None
    s = str(date_str).strip()
    # Handle DD/MM/YYYY
    if '/' in s:
        parts = s.split('/')
        if len(parts) == 3:
            # Check if first part is year (YYYY/MM/DD)
            if len(parts[0]) == 4:
                 return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            # Assume DD/MM/YYYY -> YYYY-MM-DD
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    # Handle YYYY-MM-DD (already correct, or needs verification)
    return s

def get_cuotas_data(
    selected: dict | None = None,
    numero_poliza: str | None = None,
    poliza_id: int | str | None = None,
    aviso: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> Dict[str, object]:
    poliza = (numero_poliza or (selected or {}).get('poliza') or (selected or {}).get('numero_poliza') or '').strip()
    aviso_str = (str(aviso).strip() if aviso is not None else "")
    if aviso_str.lower() in ("", "null", "none"):
        aviso_str = ""
    rows: List[Dict[str, str]] = []
    encabezado = {
        'contratante': '',
        'numero_documento': '',
        'poliza': poliza or '',
        'compania': '',
        'ramo': ''
    }
    resumen = {
        'aviso_cob': '',
        'vig_inicio': '',
        'vig_fin': '',
        'tipo_doc': '',
        'concepto': 'EMISION',
        'prima_id': None,
        'moneda': '',
    }

    # Try DB-backed primas to populate cuotas context
    try:
        if poliza:
            from models.db import get_connection
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            cur.execute("CALL sp_list_primas_por_poliza(%s)", (poliza,))
            prima_rows = cur.fetchall() or []
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass

            selected_prima = None
            prima_id_int = None
            if poliza_id is not None:
                try:
                    prima_id_int = int(poliza_id)
                except Exception:
                    prima_id_int = None

            if prima_rows:
                for pr in prima_rows:
                    if prima_id_int is not None and (pr.get('idPoliza') == prima_id_int or str(pr.get('idPoliza')) == str(prima_id_int)):
                        selected_prima = pr
                        break
                if selected_prima is None and aviso_str:
                    aviso_clean = aviso_str
                    if aviso_clean:
                        for pr in prima_rows:
                            rec = (pr.get('recibo') or pr.get('cupon') or pr.get('aviso') or pr.get('nro_aviso') or '').strip()
                            if rec == aviso_clean:
                                selected_prima = pr
                                break
                if selected_prima is None:
                    selected_prima = prima_rows[0]

                pr = selected_prima
                encabezado['contratante'] = pr.get('contratante') or ''
                encabezado['compania'] = pr.get('compania') or pr.get('cia') or ''
                encabezado['ramo'] = pr.get('ramo') or ''
                resumen['aviso_cob'] = pr.get('recibo') or pr.get('aviso') or pr.get('nro_aviso') or ''
                resumen['vig_inicio'] = format_date_custom(pr.get('vig_inicio'))
                resumen['vig_fin'] = format_date_custom(pr.get('vig_fin'))
                resumen['tipo_doc'] = pr.get('tipo') or pr.get('tipo_mov') or ''
                resumen['concepto'] = pr.get('motivo') or resumen['concepto']
                resumen['prima_id'] = pr.get('idPoliza') or None
                resumen['moneda'] = pr.get('moneda') or ''

                try:
                    target_poliza_id = resumen.get('prima_id')
                    if target_poliza_id:
                        cur.execute(
                            """
                            SELECT
                                TRIM(
                                    COALESCE(
                                        CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR),
                                        CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR),
                                        c.numero_documento
                                    )
                                ) AS numero_documento
                            FROM polizas p
                            INNER JOIN clientes c ON c.idCliente = p.cliente_id
                            WHERE p.idPoliza = %s
                            LIMIT 1
                            """,
                            (target_poliza_id,),
                        )
                        cli_row = cur.fetchone() or {}
                        encabezado['numero_documento'] = (cli_row.get('numero_documento') or '').strip()
                        try:
                            while cur.nextset():
                                pass
                        except Exception:
                            pass
                except Exception:
                    encabezado['numero_documento'] = encabezado.get('numero_documento') or ''

                # No pre-filled demo row; tabla queda vacía si no hay cuotas reales

            try:
                cuota_rows: List[Dict[str, str]] = []
                target_prima_id = None
                if prima_id_int is not None:
                    target_prima_id = prima_id_int
                elif aviso_str and resumen['prima_id'] is not None:
                    target_prima_id = resumen['prima_id']

                if target_prima_id is not None:
                    vig_inicio_sql = None
                    vig_fin_sql = None
                    try:
                        vig_inicio_sql = parse_date_input(resumen.get('vig_inicio'))
                        vig_fin_sql = parse_date_input(resumen.get('vig_fin'))
                    except Exception:
                        vig_inicio_sql = None
                        vig_fin_sql = None

                    cur.execute(
                        """
                        SELECT
                            c.idCuota,
                            c.numero_cuota,
                            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR), c.cupon) AS cupon,
                            DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                            FORMAT(c.importe, 2) AS importe,
                            DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                            c.factura,
                            c.observacion,
                            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), p.recibo) AS aviso_cobranza,
                            p.tipo_doc
                        FROM cuotas c
                        LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                        WHERE c.activo = 1
                          AND c.poliza_id = %s
                        ORDER BY c.fecha_vencimiento ASC, c.idCuota ASC
                        """,
                        (target_prima_id,),
                    )
                    cuota_rows = cur.fetchall() or []
                    try:
                        while cur.nextset():
                            pass
                    except Exception:
                        pass

                    if (not cuota_rows) and poliza:
                        cur.execute(
                            """
                            SELECT
                                c.idCuota,
                                c.numero_cuota,
                                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR), c.cupon) AS cupon,
                                DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                                FORMAT(c.importe, 2) AS importe,
                                DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                                c.factura,
                                c.observacion,
                                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), p.recibo) AS aviso_cobranza,
                                p.tipo_doc
                            FROM cuotas c
                            LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                            WHERE c.activo = 1
                              AND (c.poliza_id IS NULL OR c.poliza_id = 0)
                              AND (
                                CAST(AES_DECRYPT(FROM_BASE64(c.poliza), @SIS_KEY) AS CHAR) = %s
                                OR c.poliza = %s
                              )
                              AND (
                                %s IS NULL OR %s IS NULL
                                OR (
                                  c.fecha_vencimiento >= %s
                                  AND c.fecha_vencimiento < DATE_ADD(%s, INTERVAL 1 DAY)
                                )
                              )
                            ORDER BY c.fecha_vencimiento ASC, c.idCuota ASC
                            """,
                            (poliza, poliza, vig_inicio_sql, vig_fin_sql, vig_inicio_sql, vig_fin_sql),
                        )
                        cuota_rows = cur.fetchall() or []
                        try:
                            while cur.nextset():
                                pass
                        except Exception:
                            pass
                else:
                    sql_query = """
                        SELECT
                            c.idCuota,
                            c.numero_cuota,
                            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR), c.cupon) AS cupon,
                            DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                            FORMAT(c.importe, 2) AS importe,
                            DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                            c.factura,
                            c.observacion,
                            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), p.recibo) AS aviso_cobranza,
                            p.tipo_doc
                        FROM cuotas c
                        LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                        WHERE (
                          CAST(AES_DECRYPT(FROM_BASE64(c.poliza), @SIS_KEY) AS CHAR) = %s
                          OR c.poliza = %s
                        )
                          AND c.activo = 1
                    """
                    params = [poliza, poliza]

                    if fecha_desde or fecha_hasta:
                          f_desde = parse_date_input(fecha_desde)
                          f_hasta = parse_date_input(fecha_hasta)
                          start_date = f_desde if f_desde else '1900-01-01'
                          end_date = f_hasta if f_hasta else '2900-12-31'
                          sql_query += " AND (p.vig_hasta BETWEEN %s AND %s) "
                          params.append(start_date)
                          params.append(end_date)
                    
                    # Sanity Check: Exclude receipts incorrectly linked to wrong renewal period
                    # Increased to 400 days to allow receipts due significantly after policy end (e.g. data anomalies or long extensions)
                    sql_query += " AND (p.vig_hasta IS NULL OR c.fecha_vencimiento <= DATE_ADD(p.vig_hasta, INTERVAL 400 DAY)) "

                    sql_query += " ORDER BY c.fecha_vencimiento ASC, c.idCuota ASC "

                    cur.execute(sql_query, tuple(params))
                    cuota_rows = cur.fetchall() or []
                    try:
                        while cur.nextset():
                            pass
                    except Exception:
                        pass
                    if (not cuota_rows) and aviso and str(aviso).strip().lower() not in ('null', 'none', ''):
                        try:
                            cur.execute(
                                """
                                SELECT
                                    c.idCuota,
                                    c.numero_cuota,
                                    COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR), c.cupon) AS cupon,
                                    DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                                    FORMAT(c.importe, 2) AS importe,
                                    DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                                    c.factura,
                                    c.observacion,
                                    COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), p.recibo) AS aviso_cobranza,
                                    p.tipo_doc
                                FROM cuotas c
                                LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                                WHERE c.activo = 1
                                  AND (
                                        TRIM(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR), c.cupon)) = TRIM(%s)
                                        OR TRIM(c.factura) = TRIM(%s)
                                      )
                                ORDER BY c.fecha_vencimiento ASC, c.idCuota ASC
                                """,
                                (aviso, aviso),
                            )
                            cuota_rows = cur.fetchall() or []
                            try:
                                while cur.nextset():
                                    pass
                            except Exception:
                                pass
                        except Exception:
                            cuota_rows = []

                if cuota_rows:
                    rows = []
                    for i, c in enumerate(cuota_rows, start=1):
                        rows.append({
                            'idCuota': c.get('idCuota'),
                            'numero_cuota': c.get('numero_cuota'),
                            'secuencia': i,
                            'cupon': c.get('cupon') or '',
                            'fecha_vencimiento': format_date_custom(c.get('fecha_vencimiento')),
                            'importe': c.get('importe') or '',
                            'fecha_pago': format_date_custom(c.get('fecha_pago')),
                            'factura': c.get('factura') or '',
                            'observacion': c.get('observacion') or '',
                            'aviso_cobranza': c.get('aviso_cobranza') or '',
                            'tipo_doc': c.get('tipo_doc') or '',
                        })
            except Exception as e:
                print(f"Error fetching cuotas list: {e}")

            cur.close()
            cnx.close()
    except Exception:
        pass

    if not encabezado['contratante']:
        encabezado = {
            'contratante': 'MASGO ARQUITECTOS E INGENIEROS SAC',
            'poliza': poliza or '7607866',
            'compania': 'LA POSITIVA S.A. ENTIDAD PRESTADORA DE SALUD',
            'ramo': 'SCTR - SALUD'
        }
    if not resumen['vig_inicio']:
        resumen.update({
            'aviso_cob': resumen['aviso_cob'] or '806822909',
            'vig_inicio': '25/11/2025',
            'vig_fin': '25/12/2025',
            'tipo_doc': resumen['tipo_doc'] or 'Emisión',
            'concepto': resumen['concepto'] or 'EMISION'
        })
    # No fallback demo rows; when there are no cuotas, keep the table empty

    def _to_float(s: str) -> float:
        try:
            if not s: return 0.0
            # Remove currency symbols and separators
            # Keep digits, dots and minus sign
            import re
            clean = re.sub(r'[^\d.-]', '', str(s).replace(',', ''))
            return float(clean)
        except Exception:
            return 0.0
    
    total_val = sum(_to_float(r['importe']) for r in rows)
    total_monto = "{:,.2f}".format(total_val)

    return {
        'title': 'Cuotas',
        'encabezado': encabezado,
        'resumen': resumen,
        'rows': rows,
        'total_monto': total_monto
    }

def save_cuota(data: Dict[str, object]) -> Tuple[bool, str]:
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()

        def val_or_none(v):
            if v is None:
                return None
            if isinstance(v, str) and not v.strip():
                return None
            return v

        poliza = (data.get('poliza') or '').strip()
        cupon = val_or_none(data.get('cupon'))
        if isinstance(cupon, str):
            cupon = cupon.strip() or None

        if cupon:
            cur.execute(
                """
                SELECT 1
                FROM cuotas
                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                  AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) USING utf8mb4), cupon) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                  AND activo = 1
                LIMIT 1
                """,
                (poliza, cupon),
            )
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El cupón ya existe para esta póliza.", None

        factura = val_or_none(data.get('factura'))
        if isinstance(factura, str):
            factura = factura.strip() or None

        importe_input = val_or_none(data.get('importe'))
        importe_val = None
        if importe_input is not None:
            importe_val = _parse_decimal(importe_input)
            if importe_val is None:
                cur.close()
                cnx.close()
                return False, "Importe inválido.", None

        poliza_id = None
        prima_raw = data.get('prima_id') or data.get('poliza_id') or data.get('idPrima')
        if prima_raw is not None:
            try:
                poliza_id = int(prima_raw)
            except Exception:
                poliza_id = None

        if poliza_id is None:
            cur.execute(
                """
                SELECT idPoliza
                FROM polizas
                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                ORDER BY creado_en DESC
                LIMIT 1
                """,
                (poliza,),
            )
            row = cur.fetchone()
            if row:
                poliza_id = row[0]

        cia = None
        if poliza_id is not None:
            cur.execute("SELECT cia FROM polizas WHERE idPoliza = %s LIMIT 1", (poliza_id,))
            rcia = cur.fetchone()
            cia = (rcia[0] if rcia else None)
        if cia is None and poliza:
            cur.execute(
                """
                SELECT cia
                FROM polizas
                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci)
                      = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                ORDER BY creado_en DESC
                LIMIT 1
                """,
                (poliza,),
            )
            rcia2 = cur.fetchone()
            cia = (rcia2[0] if rcia2 else None)

        if factura:
            if cupon:
                if cia:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        INNER JOIN polizas p ON p.idPoliza = q.poliza_id
                        WHERE q.activo = 1
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(p.cia, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                        LIMIT 1
                        """,
                        (factura, poliza, cupon, cia),
                    )
                else:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        WHERE q.activo = 1
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                        LIMIT 1
                        """,
                        (factura, poliza, cupon),
                    )
            else:
                if cia:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        INNER JOIN polizas p ON p.idPoliza = q.poliza_id
                        WHERE q.activo = 1
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND (q.cupon IS NULL OR TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon)) = '')
                          AND TRIM(COALESCE(p.cia, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                        LIMIT 1
                        """,
                        (factura, poliza, cia),
                    )
                else:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        WHERE q.activo = 1
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND (q.cupon IS NULL OR TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon)) = '')
                        LIMIT 1
                        """,
                        (factura, poliza),
                    )
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El número de factura ya existe.", None

        # Calcular numero_cuota (basado en póliza, no cupón)
        if poliza_id:
            cur.execute(
                "SELECT IFNULL(MAX(numero_cuota), 0) + 1 FROM cuotas WHERE poliza_id = %s",
                (poliza_id,)
            )
        else:
            cur.execute(
                """
                SELECT IFNULL(MAX(numero_cuota), 0) + 1 
                FROM cuotas 
                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                """,
                (poliza,)
            )
        row = cur.fetchone()
        numero_cuota = row[0] if row and row[0] is not None else 1

        cur.execute(
            """
            INSERT INTO cuotas (
                poliza_id,
                poliza,
                cupon,
                fecha_vencimiento,
                moneda,
                importe,
                fecha_pago,
                factura,
                observacion,
                usuario_registro,
                numero_cuota,
                activo
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, 1
            )
            """,
            (
                poliza_id,
                poliza,
                cupon,
                (data.get('fecha_vencimiento') or date.today().strftime('%Y-%m-%d')),
                data.get('moneda', 'S/.'),
                importe_val,
                val_or_none(data.get('fecha_pago')),
                factura,
                val_or_none(data.get('observacion')),
                data.get('usuario'),
                numero_cuota,
            ),
        )
        # Capturar AQUÍ antes de cualquier otro execute que lo pise
        new_id = cur.lastrowid
        try:
            cur.execute(
                "UPDATE cuotas SET poliza = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)), cupon = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)) WHERE idCuota = %s",
                (poliza, cupon, new_id)
            )
        except Exception:
            pass

        target_poliza_id = poliza_id
        if target_poliza_id is None:
            try:
                cur.execute(
                    """
                    SELECT idPoliza
                    FROM polizas
                    WHERE TRIM(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR), poliza)) = TRIM(%s)
                    ORDER BY creado_en DESC
                    LIMIT 1
                    """,
                    (poliza,),
                )
                row = cur.fetchone()
                if row:
                    target_poliza_id = row[0]
            except Exception:
                target_poliza_id = None

        if target_poliza_id is not None:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM cuotas
                WHERE poliza_id = %s
                  AND (
                    fecha_pago IS NULL
                    OR factura IS NULL OR factura = ''
                  )
                  AND activo = 1
                """,
                (target_poliza_id,),
            )
            row = cur.fetchone()
            pendientes = row[0] if row and row[0] is not None else 0
            nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'PAGADO'
            cur.execute(
                "UPDATE polizas SET estado = %s WHERE idPoliza = %s",
                (nuevo_estado, target_poliza_id),
            )

        cnx.commit()
        cur.close()
        cnx.close()
        return True, "", new_id
    except Exception as e:
        print(f"Error saving cuota: {e}")
        err_msg = str(e)
        if "El número de factura ya existe" in err_msg:
             return False, "El número de factura ya existe.", None
        return False, err_msg, None


def update_cuota_cupon(data: Dict[str, object]) -> Tuple[bool, str]:
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()

        def val_or_none(v):
            if v is None:
                return None
            if isinstance(v, str) and not v.strip():
                return None
            return v

        cuota_id_raw = data.get('idCuota') or data.get('id_cuota') or data.get('id')
        if cuota_id_raw is None:
            cur.close()
            cnx.close()
            return False, "Falta id de cuota."
        try:
            cuota_id = int(cuota_id_raw)
        except Exception:
            cur.close()
            cnx.close()
            return False, "Id de cuota inválido."

        cur.execute(
            """
            SELECT COALESCE(CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR), poliza) AS poliza,
                   COALESCE(CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR), cupon) AS cupon,
                   poliza_id,
                   fecha_vencimiento,
                   importe,
                   fecha_pago,
                   factura,
                   observacion
            FROM cuotas
            WHERE idCuota = %s
            """,
            (cuota_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            cnx.close()
            return False, "Cuota no encontrada."

        poliza_actual = (row[0] or '').strip()
        cupon_actual = (row[1] or '').strip()
        poliza_id_actual = row[2]
        fecha_venc_actual = row[3]
        importe_actual = row[4]
        fecha_pago_actual = row[5]
        factura_actual = row[6]
        observacion_actual = row[7]

        cupon_nuevo_val = data.get('cupon')
        if cupon_nuevo_val is None:
            cupon_nuevo = cupon_actual
        else:
            cupon_nuevo = (str(cupon_nuevo_val) if cupon_nuevo_val is not None else '').strip() or None

        fecha_venc_nueva = val_or_none(data.get('fecha_vencimiento')) or fecha_venc_actual
        importe_nuevo = importe_actual
        importe_input = data.get('importe')
        if importe_input is not None and (not isinstance(importe_input, str) or importe_input.strip() != ''):
            parsed = _parse_decimal(importe_input)
            if parsed is None:
                cur.close()
                cnx.close()
                return False, "Importe inválido."
            importe_nuevo = parsed
        fecha_pago_nueva = val_or_none(data.get('fecha_pago')) or fecha_pago_actual
        factura_nueva = val_or_none(data.get('factura')) or factura_actual
        if isinstance(factura_nueva, str):
            factura_nueva = factura_nueva.strip() or None
        observacion_nueva = val_or_none(data.get('observacion')) or observacion_actual

        if cupon_nuevo and cupon_nuevo != cupon_actual:
            cur.execute(
                """
                SELECT 1
                FROM cuotas
                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                  AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) USING utf8mb4), cupon) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                  AND idCuota <> %s
                  AND activo = 1
                LIMIT 1
                """,
                (poliza_actual, cupon_nuevo, cuota_id),
            )
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El nuevo cupón ya existe para esta póliza."

        if factura_nueva and factura_nueva != factura_actual:
            cia = None
            if poliza_id_actual is not None:
                cur.execute("SELECT cia FROM polizas WHERE idPoliza = %s LIMIT 1", (poliza_id_actual,))
                rcia = cur.fetchone()
                cia = (rcia[0] if rcia else None)
            if cia is None:
                try:
                    cur.execute(
                        """
                        SELECT cia
                        FROM polizas
                        WHERE TRIM(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR), poliza)) = TRIM(%s)
                          AND (
                                %s IS NULL
                                OR TRIM(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR), recibo)) = TRIM(%s)
                              )
                        ORDER BY creado_en DESC
                        LIMIT 1
                        """,
                        (poliza_actual, cupon_nuevo, cupon_nuevo),
                    )
                    rcia2 = cur.fetchone()
                    cia = (rcia2[0] if rcia2 else None)
                except Exception:
                    cia = None

            if cupon_nuevo:
                if cia:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        INNER JOIN polizas p ON p.idPoliza = q.poliza_id
                        WHERE q.activo = 1
                          AND q.idCuota <> %s
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(p.cia, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                        LIMIT 1
                        """,
                        (cuota_id, factura_nueva, poliza_actual, cupon_nuevo, cia),
                    )
                else:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        WHERE q.activo = 1
                          AND q.idCuota <> %s
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                        LIMIT 1
                        """,
                        (cuota_id, factura_nueva, poliza_actual, cupon_nuevo),
                    )
            else:
                if cia:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        INNER JOIN polizas p ON p.idPoliza = q.poliza_id
                        WHERE q.activo = 1
                          AND q.idCuota <> %s
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND (q.cupon IS NULL OR TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon)) = '')
                          AND TRIM(COALESCE(p.cia, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                        LIMIT 1
                        """,
                        (cuota_id, factura_nueva, poliza_actual, cia),
                    )
                else:
                    cur.execute(
                        """
                        SELECT 1
                        FROM cuotas q
                        WHERE q.activo = 1
                          AND q.idCuota <> %s
                          AND TRIM(COALESCE(q.factura, '')) COLLATE utf8mb4_0900_ai_ci
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.poliza), @SIS_KEY) USING utf8mb4), q.poliza) COLLATE utf8mb4_0900_ai_ci)
                              = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                          AND (q.cupon IS NULL OR TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) USING utf8mb4), q.cupon)) = '')
                        LIMIT 1
                        """,
                        (cuota_id, factura_nueva, poliza_actual),
                    )
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El número de factura ya existe."

        usuario = val_or_none(data.get('usuario'))

        cur.execute(
            """
            UPDATE cuotas
            SET cupon = COALESCE(TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)), %s),
                fecha_vencimiento = %s,
                importe = %s,
                fecha_pago = %s,
                factura = %s,
                observacion = %s,
                usuario_registro = COALESCE(%s, usuario_registro)
            WHERE idCuota = %s
            """,
            (
                cupon_nuevo,
                cupon_nuevo,
                fecha_venc_nueva,
                importe_nuevo,
                fecha_pago_nueva,
                factura_nueva,
                observacion_nueva,
                usuario,
                cuota_id,
            ),
        )

        target_poliza_id = poliza_id_actual
        if target_poliza_id is None:
            try:
                cur.execute(
                    """
                    SELECT idPoliza
                    FROM polizas
                    WHERE TRIM(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR), poliza)) = TRIM(%s)
                      AND TRIM(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR), recibo)) = TRIM(%s)
                    ORDER BY creado_en DESC
                    LIMIT 1
                    """,
                    (poliza_actual, cupon_nuevo),
                )
                row2 = cur.fetchone()
                if row2:
                    target_poliza_id = row2[0]
            except Exception:
                target_poliza_id = None

        if target_poliza_id is not None:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM cuotas
                WHERE poliza_id = %s
                  AND (
                    fecha_pago IS NULL
                    OR factura IS NULL OR factura = ''
                  )
                  AND activo = 1
                """,
                (target_poliza_id,),
            )
            row3 = cur.fetchone()
            pendientes = row3[0] if row3 and row3[0] is not None else 0
            nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'CANCELADO'
            cur.execute(
                "UPDATE polizas SET estado = %s WHERE idPoliza = %s",
                (nuevo_estado, target_poliza_id),
            )

        cnx.commit()
        cur.close()
        cnx.close()
        return True, ""
    except Exception as e:
        print(f"Error updating cuota cupon: {e}")
        return False, str(e)

def delete_cuota(cuota_id: int) -> Tuple[bool, str]:
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()
        
        # Get poliza_id before deleting to update status later
        cur.execute("SELECT poliza_id FROM cuotas WHERE idCuota = %s", (cuota_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            cnx.close()
            return False, "Cuota no encontrada"
            
        poliza_id = row[0]
        
        # Soft delete
        cur.execute("UPDATE cuotas SET activo = 0 WHERE idCuota = %s", (cuota_id,))
        
        # Update poliza status
        if poliza_id:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM cuotas
                WHERE poliza_id = %s
                  AND (fecha_pago IS NULL OR factura IS NULL OR factura = '')
                  AND activo = 1
                """,
                (poliza_id,),
            )
            r = cur.fetchone()
            pendientes = r[0] if r else 0
            nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'PAGADO'
            cur.execute(
                "UPDATE polizas SET estado = %s WHERE idPoliza = %s",
                (nuevo_estado, poliza_id),
            )
            
        cnx.commit()
        cur.close()
        cnx.close()
        return True, ""
    except Exception as e:
        print(f"Error deleting cuota: {e}")
        return False, str(e)

def extract_cuota_from_pdf(filepath: str) -> Dict[str, str]:
    import re
    text = ""
    try:
        import pdfplumber
        pages_text: List[str] = []
        ocr_page_indexes: List[int] = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(page_text)
                else:
                    pages_text.append("")
                    ocr_page_indexes.append(i)

        if ocr_page_indexes:
            try:
                import fitz
                import pytesseract
                from PIL import Image

                doc = fitz.open(filepath)
                for i in ocr_page_indexes:
                    p = doc.load_page(i)
                    pix = p.get_pixmap(dpi=220, alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(img, lang="spa+eng") or ""
                    pages_text[i] = ocr_text
                doc.close()
            except Exception:
                pass

        text = "\n".join(pages_text) + "\n"
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        except Exception:
            return {}
    except Exception as e:
        print(f"Error extracting text: {e}")
        return {}

    def _normalize_pdf_text(t: str) -> str:
        t = t.replace('\ufeff', '')
        t = t.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
        t = t.replace('\xa0', ' ').replace('\u00ad', '')
        t = t.replace('：', ':')
        return t
    text = _normalize_pdf_text(text)
    text_upper = text.upper()
    try:
        import unicodedata
        def _fold(s: str) -> str:
            return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
        text_fold_upper = _fold(text).upper()
    except Exception:
        text_fold_upper = text_upper
    
    data = {
        'cupon': '',
        'fecha_vencimiento': '',
        'importe': '',
        'factura': '',
        'fecha_pago': '',
        'observacion': '',
        'numero_documento_contratante': '',
        'cuotas': []
    }

    def extract_numero_documento() -> str:
        patterns = [
            r'\bRUC\s*(?:N[°ºO]?\s*)?[:\-]?\s*(\d{11})\b',
            r'\bR\.?\s*U\.?\s*C\.?\s*(?:N[°ºO]?\s*)?[:\-]?\s*(\d{11})\b',
        ]
        for pat in patterns:
            m = re.search(pat, text_fold_upper, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        m = re.search(r'\bDNI\s*(?:N[°ºO]?\s*)?[:\-]?\s*(\d{8})\b', text_fold_upper, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return ''

    data['numero_documento_contratante'] = extract_numero_documento()

    # Regex Helpers
    def find_val(pattern, txt):
        m = re.search(pattern, txt, re.IGNORECASE)
        return m.group(1).strip() if m else ''
    def normalize_date_token(s: str) -> str:
        if not s:
            return ''
        # Colapsar espacios y normalizar separadores en fechas tipo dd/mm/yyyy
        t = re.sub(r'\s*/\s*', '/', s)
        t = re.sub(r'\s*-\s*', '-', t)
        t = re.sub(r'\s+', ' ', t).strip()
        # Aceptar variante con guiones
        m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', t)
        if m:
            dd = m.group(1).zfill(2)
            mm = m.group(2).zfill(2)
            yyyy = m.group(3)
            return f"{dd}/{mm}/{yyyy}"
        return t
    def find_date_after(label_regex: str, txt: str) -> str:
        # Busca el label y captura hasta 120 caracteres siguientes, tolerando saltos y celdas
        m = re.search(label_regex + r'[:：]?\s*(?:\r?\n|\s{0,10})?([\s\S]{0,120})', txt, re.IGNORECASE | re.DOTALL)
        if not m:
            return ''
        tail = m.group(1) or ''
        m2 = re.search(r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', tail)
        return normalize_date_token(m2.group(1)) if m2 else ''

    # --- Detección de Proveedor ---
    is_crecer = 'CRECER' in text_upper and 'SEGUROS' in text_upper
    is_protecta = 'PROTECTA' in text_fold_upper
    is_sanitas = ('SANITAS' in text_fold_upper) and (not is_protecta)
    is_positiva = 'LA POSITIVA' in text_upper
    is_qualitas = ('QUALITAS' in text_fold_upper) or ('QUÁLITAS' in text_upper) or ('QUÁLITAS' in text_fold_upper)
    is_mapfre = 'MAPFRE' in text_fold_upper

    if is_protecta:
        m_fac = re.search(r'(F\d{3}\s*-\s*\d+)', text, re.IGNORECASE)
        if m_fac:
            data['factura'] = m_fac.group(1).replace(' ', '')

        if not data['fecha_vencimiento']:
            data['fecha_vencimiento'] = find_val(r'Fecha\s+de\s+Vencimiento\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
        if not data['fecha_vencimiento']:
            data['fecha_vencimiento'] = find_val(r'(?:VENCIMIENTO|VENCE|VIGENCIA\s*HASTA)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

        if not data['fecha_pago']:
            raw_emision = find_val(
                r'Fecha\s+de\s+Emisi[óo]n\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
                text,
            )
            if not raw_emision:
                raw_emision = find_date_after(r'Fecha\s+de\s+Emisi\S*n', text)
            if not raw_emision:
                raw_emision = find_date_after(r'Fecha\s+Emisi\S*n', text)
            if not raw_emision:
                raw_emision = find_date_after(r'FECHA\s+DE\s+EMISI\S*N', text)
            if not raw_emision:
                raw_emision = find_date_after(r'FECHA\s+EMISI\S*N', text)
            if not raw_emision:
                m_em = re.search(r'Emisi\S*n[\s\S]{0,80}?(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', text, re.IGNORECASE)
                if m_em:
                    raw_emision = m_em.group(1)
            if raw_emision:
                data['fecha_pago'] = normalize_date_token(raw_emision)
        if not data['fecha_pago']:
            raw_vig = find_date_after(r'Vigencia', text)
            if not raw_vig:
                raw_vig = find_date_after(r'Vigenc\S*', text)
            if not raw_vig:
                m_range = re.search(
                    r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})\s*(?:al|a)\s*(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})',
                    text,
                    re.IGNORECASE,
                )
                if m_range:
                    raw_vig = m_range.group(1)
            if raw_vig:
                data['fecha_pago'] = normalize_date_token(raw_vig)

        moneda_val = find_val(r'MONEDA\s*[:.]?\s*([A-Za-z]+)', text)
        if moneda_val:
            data['moneda'] = 'S/.' if moneda_val.upper().startswith('SOLE') or moneda_val.upper().startswith('SOL') else moneda_val
        else:
            data['moneda'] = data.get('moneda') or 'S/.'

    elif is_crecer:
        # Lógica específica para Crecer Seguros
        
        # Factura: F### - ########
        m_fac = re.search(r'(F\d{3}\s*-\s*\d+)', text, re.IGNORECASE)
        if m_fac:
            data['factura'] = m_fac.group(1).replace(' ', '') 

        # Cupón: Proforma (Prioridad) — deshabilitado por solicitud
        # data['cupon'] = find_val(r'(?:PROFORMA|Proforma|N[úu]mero\s+de\s+Proforma)\s*[:.]?\s*([0-9A-Z\-]+)', text)

        # Fecha Vencimiento
        data['fecha_vencimiento'] = find_val(r'(?:VENCIMIENTO|VENCE|VIGENCIA\s*HASTA)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

        # Importe Total: deshabilitado por solicitud
        
        # Fecha Pago
        data['fecha_pago'] = find_val(r'FECHA\s+DE\s+EMISI[ÓO]N\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

        # Póliza para observación
        poliza = find_val(r'N[úu]mero\s+de\s+p[óo]liza\s*[:.]?\s*([0-9A-Z\-]+)', text)
        if poliza:
            data['observacion'] = f"Póliza: {poliza}"

    elif is_positiva:
        # Lógica específica para La Positiva
        # Factura/Recibo: F038-00422654
        m_fac = re.search(r'(F\d{3,4}\s*-\s*\d{5,8})', text, re.IGNORECASE)
        if m_fac:
            data['factura'] = m_fac.group(1).replace(' ', '')
        # Cupón / Proforma
        data['cupon'] = find_val(r'(?:N[°º]?\s*PROFORMA)\s*[:.]?\s*([0-9A-Z\-]+)', text)
        # Fecha Vencimiento (VENC. DOC.)
        if not data['fecha_vencimiento']:
            data['fecha_vencimiento'] = find_val(r'(?:VENC\.?\s*DOC\.?|VENCIMIENTO|VENCE)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)
        # Fecha de Pago: Fecha de Emisión
        if not data['fecha_pago']:
            data['fecha_pago'] = find_val(r'Fecha\s+de\s+Emisi[óo]n\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)
        # Moneda
        moneda_val = find_val(r'MONEDA\s*[:.]?\s*([A-Za-z]+)', text)
        if moneda_val:
            data['moneda'] = 'S/.' if moneda_val.upper().startswith('SOLE') else moneda_val
        else:
            data['moneda'] = data.get('moneda') or 'S/.'
        # Importe total: deshabilitado por solicitud

    elif is_qualitas:
        # Boleta / Factura electrónica Qualitas (Ej: BA02-18416)
        m_fac = re.search(
            r"(?:BOLETA\s+DE\s+VENTA\s+ELECTR[ÓO]NICA|FACTURA\s+ELECTR[ÓO]NICA)[\s\S]{0,120}?\b([A-Z]{1,3}\d{2}\s*-\s*\d{4,10})\b",
            text_fold_upper,
            re.IGNORECASE | re.DOTALL,
        )
        if not m_fac:
            m_fac = re.search(r"\b([A-Z]{1,3}\d{2}\s*-\s*\d{4,10})\b", text_fold_upper, re.IGNORECASE)
        if m_fac:
            data["factura"] = m_fac.group(1).replace(" ", "")

        raw_emision = find_val(
            r"Fecha\s+Emisi[óo]n\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            text,
        )
        if not raw_emision:
            raw_emision = find_val(
                r"FECHA\s+EMISI[ÓO]N\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                text,
            )
        if not raw_emision:
            raw_emision = find_val(
                r"FECHA\s+DE\s+EMISI[ÓO]N\s*[:.]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                text,
            )
        if not raw_emision:
            raw_emision = find_date_after(r"Fecha\s+Emisi\S*n", text)
        if raw_emision:
            data["fecha_pago"] = format_date_custom(raw_emision)

        moneda_val = find_val(r"Moneda\s*[:.]?\s*([A-Za-zÁÉÍÓÚÑ ]+)", text)
        if moneda_val:
            m = moneda_val.upper()
            if "DOLAR" in m or "DÓLAR" in m or "USD" in m:
                data["moneda"] = "US$"
            elif "SOL" in m:
                data["moneda"] = "S/."

        poliza_ref = find_val(r"PAGO\s+DE\s+P[ÓO]LIZA\s+(\d{6,14})", text)
        recibo_ref = find_val(r"RECIBO\s+(\d{6,20})", text)
        cuota_ref = find_val(r"CUOTA\s+(\d{1,3})", text)
        obs_parts = []
        if poliza_ref:
            obs_parts.append(f"Póliza {poliza_ref}")
        if recibo_ref:
            obs_parts.append(f"Recibo {recibo_ref}")
        if cuota_ref:
            obs_parts.append(f"Cuota {cuota_ref}")
        if obs_parts:
            data["observacion"] = " | ".join(obs_parts)

    elif is_mapfre:
        moneda_val = find_val(r"Moneda\s*[:.]?\s*([A-Za-zÁÉÍÓÚÑ$/\. ]+)", text)
        if moneda_val:
            m = moneda_val.upper()
            if "DOLAR" in m or "DÓLAR" in m or "USD" in m or "US$" in m:
                data["moneda"] = "US$"
            elif "SOL" in m or "S/" in m:
                data["moneda"] = "S/."

    elif is_sanitas:
       # Lógica específica para Sanitas
       
       # Factura: Nro. F###-#######
       # Busca primero el patrón específico Fxxx-xxxxxxxx
       m_fac = re.search(r'(F\d{3}\s*-\s*\d+)', text, re.IGNORECASE)
       if not m_fac:
           # Fallback: buscar con prefijo Nro. o Factura
           m_fac = re.search(r'(?:Nro\.?|FACTURA\s+ELECTR[ÓO]NICA)\s*[:.]?\s*(F\d{3}[-\s]\d+)', text, re.IGNORECASE)
       
       if m_fac:
           data['factura'] = m_fac.group(1).replace(' ', '')

       # Importe Total: deshabilitado por solicitud

       raw_fp = find_val(r'Fecha\s+de\s+Emisi[óo]n\s*[:.]?\s*(?:\r?\n|\s{0,20})?(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', text)
       if not raw_fp:
           # Tolerar acentos corruptos o caracteres especiales: EMISI\S*N
           raw_fp = find_date_after(r'Fecha\s+de\s+Emisi\S*n', text)
       if not raw_fp:
           # Intento final con todo mayúsculas en el label
           raw_fp = find_date_after(r'FECHA\s+DE\s+EMISI\S*N', text)
       if not raw_fp:
           label_re = re.compile(r'FECHA\s+DE\s+EMISI\S*N', re.IGNORECASE)
           lines = text.splitlines()
           for i, line in enumerate(lines):
               if label_re.search(line):
                   m = re.search(r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', line)
                   if not m and i + 1 < len(lines):
                       m = re.search(r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', lines[i+1])
                   if not m and i + 2 < len(lines):
                       m = re.search(r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', lines[i+2])
                   if m:
                       raw_fp = m.group(1)
                       break
       if not raw_fp:
           # Fallback por texto plegado (sin tildes) y ventana global posterior al label
           mlabel = re.search(r'FECHA\s+DE\s+EMISION', text_fold_upper)
           if mlabel:
               start = mlabel.end()
               tail = text_fold_upper[start:start+600]
               mdate = re.search(r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', tail)
               if mdate:
                   raw_fp = mdate.group(1)
       if not raw_fp:
           # Último recurso: elegir la fecha mínima del documento (SANITAS típico: Emisión es la primera fecha en el bloque)
           all_dates = re.findall(r'(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', text)
           def _to_tuple(ds: str):
               n = normalize_date_token(ds)
               try:
                   dd, mm, yyyy = n.split('/')
                   return (int(yyyy), int(mm), int(dd)), n
               except Exception:
                   return (9999, 12, 31), n
           if all_dates:
               ordered = sorted((_to_tuple(d) for d in all_dates), key=lambda x: x[0])
               raw_fp = ordered[0][1]
       data['fecha_pago'] = normalize_date_token(raw_fp)

       # Observación: Contrato o Referencia de pago
       contrato = find_val(r'Contrato\s*[:.]?\s*(\d+)', text)
       if contrato:
            data['observacion'] = f"Contrato: {contrato}"

    elif is_positiva:
        m_fac = re.search(r'(?:FACTURA\s+ELECTR[ÓO]NICA[^A-Za-z0-9]*)?([FfEeBb]\d{2,3}\s*-\s*\d{5,8})', text, re.IGNORECASE | re.DOTALL)
        if m_fac:
            data['factura'] = m_fac.group(1).replace(' ', '')
        if not data['fecha_pago']:
            data['fecha_pago'] = find_val(r'Fecha\s+de\s+Emisi[óo]n\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

    # --- FALLBACK / GENERIC LOGIC (Runs if fields are still empty) ---

    # 1. Cupón: Proforma > Recibo > Operación — deshabilitado por solicitud
    # if not data['cupon']:
    #     data['cupon'] = find_val(r'(?:PROFORMA|Proforma|N[úu]mero\s+de\s+Proforma)\s*[:.]?\s*([0-9A-Z\-]+)', text)
    # if not data['cupon']:
    #     data['cupon'] = find_val(r'(?:RECIBO|CUP[ÓO]N|NRO\.?\s*OP|OPERACI[ÓO]N)\s*[:.]?\s*([0-9A-Z\-]+)', text)
    
    # 2. Fecha Vencimiento
    if not data['fecha_vencimiento']:
        data['fecha_vencimiento'] = find_val(r'(?:VENCIMIENTO|VENCE|VIGENCIA\s*HASTA|HASTA)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)
    
    # 3. Importe: deshabilitado por solicitud

    # 4. Factura
    if not data['factura']:
        data['factura'] = find_val(r'(?:FACTURA|NRO\.?\s*FAC|F0\d+\s*-\s*\d+)\s*[:.]?\s*([FfEeBb]\d{2,3}\s*-\s*\d+)', text)
        if not data['factura']:
            m_fac = re.search(r'([FfEeBb]\d{2,3}\s*(?:-\s*|N[°º]\s*)\d{5,8})', text, re.IGNORECASE)
            if not m_fac:
                m_fac = re.search(r'FACTURA\s+ELECTR[ÓO]NICA[^A-Za-z0-9]*([FfEeBb]\d{2,3}\s*(?:-\s*|N[°º]\s*)\d{5,8})', text, re.IGNORECASE | re.DOTALL)
            if m_fac:
                fac_val = m_fac.group(1)
                fac_val = re.sub(r'\s*N[°º]\s*', '-', fac_val, flags=re.IGNORECASE)
                data['factura'] = fac_val.replace(' ', '')

        # 5. Fecha Pago (Default to Emision if not found)
        if not data['fecha_pago']:
            raw = find_val(r'(?:PAGADO|FECHA\s*PAGO|EMISI[ÓO]N)\s*[:.]?\s*(?:\r?\n\s*)?(\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{4})', text)
            if not raw:
                raw = find_date_after(r'(?:PAGADO|FECHA\s*PAGO|EMISI[ÓO]N)', text)
            data['fecha_pago'] = normalize_date_token(raw)

    try:
        moneda_default = data.get('moneda') or 'S/.'
        cuotas = []
        try:
            from controllers.cuotas.VariosCuotasGenerales import extract_cronograma_cuotas_from_text as extract_general
            from controllers.cuotas.VariosCuotasPositiva import extract_cronograma_cuotas_positiva
            from controllers.cuotas.VariosCuotasPacifico import extract_cronograma_cuotas_pacifico
            from controllers.cuotas.VariosCuponGeneralesRimac import extract_cronograma_cuotas_rimac
            from controllers.cuotas.VariosCuponGeneralesMapfre import extract_cronograma_cuotas_mapfre
            from controllers.cuotas.RenovacionCuponRimac import extract_cronograma_cuotas_renovacion_rimac
            from controllers.cuotas.VariosCuponesRenovacionesRImac import (
                extract_cronograma_cuotas_renovaciones_rimac,
            )
            from controllers.cuotas.VariosCuponSeguroVehicularRimac import (
                extract_cronograma_cuotas_seguro_vehicular_rimac,
            )

            if re.search(
                r"(Documentos\s+Generados|Detalle\s+de\s+Vencimientos|PAGO\s+FRACCIONADO|Convenio\s+de\s+Pago)",
                text,
                re.IGNORECASE,
            ):
                try:
                    cuotas = extract_cronograma_cuotas_seguro_vehicular_rimac(text, moneda_default)
                except Exception:
                    cuotas = []

            if 'LA POSITIVA' in text_upper or 'POSITIVA' in text_upper:
                cuotas = extract_cronograma_cuotas_positiva(text, moneda_default)
            elif 'RIMAC' in text_upper:
                try:
                    if not cuotas and re.search(r"CRONOGRAMA\s+DE\s+PAGO", text, re.IGNORECASE):
                        cuotas = extract_cronograma_cuotas_renovaciones_rimac(text, moneda_default)
                except Exception:
                    cuotas = []
                try:
                    if not cuotas:
                        cuotas = extract_cronograma_cuotas_seguro_vehicular_rimac(text, moneda_default)
                except Exception:
                    cuotas = []
                try:
                    if not cuotas:
                        cuotas = extract_cronograma_cuotas_renovacion_rimac(text, moneda_default)
                except Exception:
                    cuotas = []
                if not cuotas:
                    cuotas = extract_cronograma_cuotas_rimac(text, moneda_default)
            elif is_mapfre:
                cuotas = extract_cronograma_cuotas_mapfre(text, moneda_default)
            elif 'PACIFICO' in text_fold_upper:
                cuotas = extract_cronograma_cuotas_pacifico(text, moneda_default)

            if not cuotas:
                cuotas = extract_general(text, moneda_default)
        except Exception:
            from controllers.cuotas.VariosCuotasGenerales import extract_cronograma_cuotas_from_text as extract_general
            cuotas = extract_general(text, moneda_default)

        if cuotas:
            data['cuotas'] = cuotas
            primera = cuotas[0]
            data['cupon'] = data['cupon'] or str(primera.get('cupon') or '')
            data['fecha_vencimiento'] = data['fecha_vencimiento'] or str(primera.get('fecha_vencimiento') or '')
            data['importe'] = data['importe'] or str(primera.get('importe') or '')
    except Exception as e:
        print(f"Error extracting multiple cuotas: {e}")

    return data
