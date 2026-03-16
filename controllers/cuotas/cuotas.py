from typing import Dict, List, Tuple
from datetime import date, datetime


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
    rows: List[Dict[str, str]] = []
    encabezado = {
        'contratante': '',
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
                if selected_prima is None and aviso:
                    aviso_clean = str(aviso).strip()
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

                # No pre-filled demo row; tabla queda vacía si no hay cuotas reales

            try:
                cuota_rows: List[Dict[str, str]] = []
                target_prima_id = None
                if prima_id_int is not None:
                    target_prima_id = prima_id_int
                elif aviso and resumen['prima_id'] is not None:
                    target_prima_id = resumen['prima_id']

                if target_prima_id is not None:
                    cur.execute(
                        """
                        SELECT
                            c.idCuota,
                            c.numero_cuota,
                            c.cupon,
                            DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                            FORMAT(c.importe, 2) AS importe,
                            DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                            c.factura,
                            c.observacion,
                            p.recibo AS aviso_cobranza,
                            p.tipo_doc
                        FROM cuotas c
                        LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                        WHERE c.poliza_id = %s
                          AND c.activo = 1
                          -- Sanity Check: Exclude receipts incorrectly linked to wrong renewal period
                          AND (c.fecha_vencimiento <= DATE_ADD(p.vig_hasta, INTERVAL 400 DAY))
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
                else:
                    sql_query = """
                        SELECT
                            c.idCuota,
                            c.numero_cuota,
                            c.cupon,
                            DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                            FORMAT(c.importe, 2) AS importe,
                            DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                            c.factura,
                            c.observacion,
                            p.recibo AS aviso_cobranza,
                            p.tipo_doc
                        FROM cuotas c
                        LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                        WHERE c.poliza = %s
                          AND c.activo = 1
                    """
                    params = [poliza]

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
                    sql_query += " AND (c.fecha_vencimiento <= DATE_ADD(p.vig_hasta, INTERVAL 400 DAY)) "

                    sql_query += " ORDER BY c.fecha_vencimiento ASC, c.idCuota ASC "

                    cur.execute(sql_query, tuple(params))
                    cuota_rows = cur.fetchall() or []
                    try:
                        while cur.nextset():
                            pass
                    except Exception:
                        pass
                    if (not cuota_rows) and aviso:
                        try:
                            cur.execute(
                                """
                                SELECT
                                    c.idCuota,
                                    c.numero_cuota,
                                    c.cupon,
                                    DATE_FORMAT(c.fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                                    FORMAT(c.importe, 2) AS importe,
                                    DATE_FORMAT(c.fecha_pago, '%d-%m-%Y') AS fecha_pago,
                                    c.factura,
                                    c.observacion,
                                    p.recibo AS aviso_cobranza,
                                    p.tipo_doc
                                FROM cuotas c
                                LEFT JOIN polizas p ON p.idPoliza = c.poliza_id
                                WHERE c.activo = 1
                                  AND (
                                        TRIM(c.cupon) = TRIM(%s)
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
                    for c in cuota_rows:
                        rows.append({
                            'idCuota': c.get('idCuota'),
                            'numero_cuota': c.get('numero_cuota'),
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
            return float(str(s).replace(',', '.').replace('S/.', '').strip())
        except Exception:
            return 0.0
    total_monto = f"{sum(_to_float(r['importe']) for r in rows):.2f}"

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
        cupon = (data.get('cupon') or '').strip()

        if cupon:
            cur.execute(
                """
                SELECT 1
                FROM cuotas
                WHERE TRIM(poliza) = TRIM(%s)
                  AND TRIM(cupon) = TRIM(%s)
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
        if factura:
            cur.execute("SELECT 1 FROM cuotas WHERE factura = %s AND activo = 1 LIMIT 1", (factura,))
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El número de factura ya existe.", None

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
                WHERE TRIM(poliza) = TRIM(%s)
                  AND TRIM(recibo) = TRIM(%s)
                ORDER BY creado_en DESC
                LIMIT 1
                """,
                (poliza, cupon),
            )
            row = cur.fetchone()
            if row:
                poliza_id = row[0]

        # Calcular numero_cuota (basado en póliza, no cupón)
        if poliza_id:
            cur.execute(
                "SELECT IFNULL(MAX(numero_cuota), 0) + 1 FROM cuotas WHERE poliza_id = %s",
                (poliza_id,)
            )
        else:
            cur.execute(
                "SELECT IFNULL(MAX(numero_cuota), 0) + 1 FROM cuotas WHERE poliza = %s",
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
                data.get('fecha_vencimiento'),
                data.get('moneda', 'S/.'),
                data.get('importe'),
                val_or_none(data.get('fecha_pago')),
                factura,
                val_or_none(data.get('observacion')),
                data.get('usuario'),
                numero_cuota,
            ),
        )
        # Capturar AQUÍ antes de cualquier otro execute que lo pise
        new_id = cur.lastrowid

        target_poliza_id = poliza_id
        if target_poliza_id is None:
            try:
                cur.execute(
                    """
                    SELECT idPoliza
                    FROM polizas
                    WHERE TRIM(poliza) = TRIM(%s)
                      AND TRIM(recibo) = TRIM(%s)
                    ORDER BY creado_en DESC
                    LIMIT 1
                    """,
                    (poliza, cupon),
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
            nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'CANCELADO'
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
            SELECT poliza,
                   cupon,
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

        cupon_nuevo = (data.get('cupon') or cupon_actual or '').strip()
        if not cupon_nuevo:
            cur.close()
            cnx.close()
            return False, "El cupón no puede estar vacío."

        fecha_venc_nueva = val_or_none(data.get('fecha_vencimiento')) or fecha_venc_actual
        importe_nuevo = val_or_none(data.get('importe')) or importe_actual
        fecha_pago_nueva = val_or_none(data.get('fecha_pago')) or fecha_pago_actual
        factura_nueva = val_or_none(data.get('factura')) or factura_actual
        observacion_nueva = val_or_none(data.get('observacion')) or observacion_actual

        if cupon_nuevo != cupon_actual:
            cur.execute(
                """
                SELECT 1
                FROM cuotas
                WHERE TRIM(poliza) = TRIM(%s)
                  AND TRIM(cupon) = TRIM(%s)
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
            cur.execute(
                "SELECT 1 FROM cuotas WHERE factura = %s AND idCuota <> %s AND activo = 1 LIMIT 1",
                (factura_nueva, cuota_id),
            )
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El número de factura ya existe."

        usuario = val_or_none(data.get('usuario'))

        cur.execute(
            """
            UPDATE cuotas
            SET cupon = %s,
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
                    WHERE TRIM(poliza) = TRIM(%s)
                      AND TRIM(recibo) = TRIM(%s)
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
            nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'CANCELADO'
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
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
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

    # Normalizar texto
    text_upper = text.upper()
    
    data = {
        'cupon': '',
        'fecha_vencimiento': '',
        'importe': '',
        'factura': '',
        'fecha_pago': '',
        'observacion': ''
    }

    # Regex Helpers
    def find_val(pattern, txt):
        m = re.search(pattern, txt, re.IGNORECASE)
        return m.group(1).strip() if m else ''

    # --- Detección de Proveedor ---
    is_crecer = 'CRECER' in text_upper and 'SEGUROS' in text_upper
    is_sanitas = 'SANITAS' in text_upper
    is_positiva = 'LA POSITIVA' in text_upper

    if is_crecer:
        # Lógica específica para Crecer Seguros
        
        # Factura: F### - ########
        m_fac = re.search(r'(F\d{3}\s*-\s*\d+)', text, re.IGNORECASE)
        if m_fac:
            data['factura'] = m_fac.group(1).replace(' ', '') 

        # Cupón: Proforma (Prioridad)
        data['cupon'] = find_val(r'(?:PROFORMA|Proforma|N[úu]mero\s+de\s+Proforma)\s*[:.]?\s*([0-9A-Z\-]+)', text)

        # Fecha Vencimiento
        data['fecha_vencimiento'] = find_val(r'(?:VENCIMIENTO|VENCE|VIGENCIA\s*HASTA)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

        # Importe Total
        m_imp = re.search(r'IMPORTE\s+TOTAL.*?(?:S/|USD|\$)?\s*([\d,]+\.\d{2})', text, re.IGNORECASE | re.DOTALL)
        if m_imp:
             data['importe'] = m_imp.group(1).replace(',', '') 
        
        # Fecha Pago
        data['fecha_pago'] = find_val(r'FECHA\s+DE\s+EMISI[ÓO]N\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

        # Póliza para observación
        poliza = find_val(r'N[úu]mero\s+de\s+p[óo]liza\s*[:.]?\s*([0-9A-Z\-]+)', text)
        if poliza:
            data['observacion'] = f"Póliza: {poliza}"

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

       # Importe Total: Importe Total 164.07
       m_imp = re.search(r'Importe\s+Total\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
       if m_imp:
            data['importe'] = m_imp.group(1).replace(',', '')

       # Fecha Pago: Usar FECHA DE EMISIÓN
       data['fecha_pago'] = find_val(r'Fecha\s+de\s+Emisi[óo]n\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

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

    # 1. Cupón: Proforma > Recibo > Operación
    if not data['cupon']:
        data['cupon'] = find_val(r'(?:PROFORMA|Proforma|N[úu]mero\s+de\s+Proforma)\s*[:.]?\s*([0-9A-Z\-]+)', text)
    if not data['cupon']:
        data['cupon'] = find_val(r'(?:RECIBO|CUP[ÓO]N|NRO\.?\s*OP|OPERACI[ÓO]N)\s*[:.]?\s*([0-9A-Z\-]+)', text)
    
    # 2. Fecha Vencimiento
    if not data['fecha_vencimiento']:
        data['fecha_vencimiento'] = find_val(r'(?:VENCIMIENTO|VENCE|VIGENCIA\s*HASTA|HASTA)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)
    
    # 3. Importe
    if not data['importe']:
        # Try generic "Total" or "Importe"
        m_importe = re.search(r'(?:TOTAL|IMPORTE|MONTO|NETO\s*A\s*PAGAR)\s*[:.]?\s*(?:S/\.|USD|\$)?\s*([\d,]+\.?\d{2})', text, re.IGNORECASE)
        if m_importe:
            data['importe'] = m_importe.group(1).replace(',', '')

    # 4. Factura
    if not data['factura']:
        data['factura'] = find_val(r'(?:FACTURA|NRO\.?\s*FAC|F0\d+\s*-\s*\d+)\s*[:.]?\s*([FfEeBb]\d{2,3}\s*-\s*\d+)', text)
        if not data['factura']:
             m_fac = re.search(r'([FfEeBb]\d{2,3}\s*-\s*\d{5,8})', text)
             if m_fac:
                 data['factura'] = m_fac.group(1).replace(' ', '')

        # 5. Fecha Pago (Default to Emision if not found)
        if not data['fecha_pago']:
            data['fecha_pago'] = find_val(r'(?:PAGADO|FECHA\s*PAGO|EMISI[ÓO]N)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

    return data
