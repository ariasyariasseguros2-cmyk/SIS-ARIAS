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

def get_cuotas_data(
    selected: dict | None = None,
    numero_poliza: str | None = None,
    poliza_id: int | str | None = None,
    aviso: str | None = None,
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

                rows = [{
                    'cupon': pr.get('cupon') or pr.get('recibo') or '',
                    'fecha_vencimiento': format_date_custom(pr.get('fecha_vencimiento') or pr.get('vig_fin')),
                    'moneda': pr.get('moneda') or '',
                    'importe': pr.get('importe') or pr.get('prima_comercial_igv') or pr.get('prima_total') or pr.get('prima_neta') or '',
                    'fecha_pago': '',
                    'factura': '',
                    'observacion': '',
                }]

            try:
                cuota_rows: List[Dict[str, str]] = []
                target_prima_id = None
                if resumen['prima_id'] is not None:
                    target_prima_id = resumen['prima_id']
                elif prima_id_int is not None:
                    target_prima_id = prima_id_int

                if target_prima_id is not None:
                    cur.execute(
                        """
                        SELECT
                            idCuota,
                            cupon,
                            DATE_FORMAT(fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
                            moneda,
                            FORMAT(importe, 2) AS importe,
                            DATE_FORMAT(fecha_pago, '%d-%m-%Y') AS fecha_pago,
                            factura,
                            observacion
                        FROM cuotas
                        WHERE poliza_id = %s
                        ORDER BY fecha_vencimiento ASC, idCuota ASC
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
                    cur.execute("CALL sp_list_cuotas_por_poliza(%s)", (poliza,))
                    cuota_rows = cur.fetchall() or []
                    try:
                        while cur.nextset():
                            pass
                    except Exception:
                        pass

                if cuota_rows:
                    rows = []
                    for c in cuota_rows:
                        rows.append({
                            'cupon': c.get('cupon') or '',
                            'fecha_vencimiento': format_date_custom(c.get('fecha_vencimiento')),
                            'moneda': c.get('moneda') or '',
                            'importe': c.get('importe') or '',
                            'fecha_pago': format_date_custom(c.get('fecha_pago')),
                            'factura': c.get('factura') or '',
                            'observacion': c.get('observacion') or '',
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
    if not rows:
        rows = [{
            'cupon': '806822909',
            'fecha_vencimiento': '16-12-2025',
            'moneda': 'S/.',
            'importe': '96.29',
            'fecha_pago': '02-12-2025',
            'factura': 'F05-01070444',
            'observacion': ''
        }]

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

        cur.execute(
            "SELECT IFNULL(MAX(numero_cuota), 0) + 1 FROM cuotas WHERE poliza = %s AND cupon = %s",
            (poliza, cupon)
        )
        row = cur.fetchone()
        numero_cuota = row[0] if row and row[0] is not None else 1

        factura = val_or_none(data.get('factura'))
        if factura:
            cur.execute("SELECT 1 FROM cuotas WHERE factura = %s LIMIT 1", (factura,))
            if cur.fetchone():
                cur.close()
                cnx.close()
                return False, "El número de factura ya existe."

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
                numero_cuota
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
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
        return True, ""
    except Exception as e:
        print(f"Error saving cuota: {e}")
        err_msg = str(e)
        if "El número de factura ya existe" in err_msg:
             return False, "El número de factura ya existe."
        return False, err_msg

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

        # Moneda
        moneda_val = find_val(r'(?:MONEDA)\s*[:.]?\s*([A-Za-z]+)', text)
        data['moneda'] = moneda_val if moneda_val else 'S/.'

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
       
       # Moneda
       data['moneda'] = 'S/.' # Default for Sanitas or extract if needed

       # Observación: Contrato o Referencia de pago
       contrato = find_val(r'Contrato\s*[:.]?\s*(\d+)', text)
       if contrato:
            data['observacion'] = f"Contrato: {contrato}"

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
        data['factura'] = find_val(r'(?:FACTURA|NRO\.?\s*FAC|F0\d+-\d+)\s*[:.]?\s*([FfEeBb]\d{2,3}-\d+)', text)
        if not data['factura']:
             m_fac = re.search(r'([FfEeBb]\d{2,3}-\d{5,8})', text)
             if m_fac:
                 data['factura'] = m_fac.group(1)

        # 5. Fecha Pago (Default to Emision if not found)
        if not data['fecha_pago']:
            data['fecha_pago'] = find_val(r'(?:PAGADO|FECHA\s*PAGO|EMISI[ÓO]N)\s*[:.]?\s*(\d{2}[/-]\d{2}[/-]\d{4})', text)

        # 6. Moneda (Default to S/.)
        if not data['moneda']:
            moneda_val = find_val(r'(?:MONEDA)\s*[:.]?\s*([A-Za-z]+)', text)
            data['moneda'] = moneda_val if moneda_val else 'S/.'

    return data
