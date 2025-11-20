import re
from pdfminer.high_level import extract_text
import fitz  # PyMuPDF

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_pdf_fields(file_path):
    # Extrae texto y aplica regex para capturar los campos solicitados
    raw = extract_text(file_path) or ''
    raw = raw.replace('\x0c', '\n')

    # Limpia tokens "(cid:xxx)" y normaliza espacios/saltos
    sanitized = re.sub(r'\(cid:\d+\)', '', raw)
    sanitized = re.sub(r'[ \t]+', ' ', sanitized)
    sanitized = re.sub(r'\s*\n\s*', '\n', sanitized)

    # Etiquetas tolerantes a variaciones (acentos/letras perdidas)
    labels = {
        'poliza': r'(?:P\w*li?za)\s*N(?:ro|[°º])',
        'ramo': r'Ra?mo',
        'vigencia_desde': r'Vigencia\s*desde',
        'vigencia_hasta': r'Hasta',
        'sede': r'Sede(?:\(s\))?',
        'contratante': r'Contrata\w*',
        'direccion': r'Direcci\w*n',
        'codigo_sbs': r'C\w*digo\s*SBS',
        # añadidas/ajustadas
        'localidad': r'(?:Localidad|Provincia)',
        'distrito': r'Distrito',
        'telefonos_lbl': r'Tel[eé]fonos?',
        'gestor': r'Gestor',
        'moneda_lbl': r'Moneda',
        'departamento_lbl': r'Departamento',
        # NUEVO: asegurado
        'asegurado': r'Asegura\w*',
    }
    # Unión para lookahead a “la próxima etiqueta”
    next_union = '|'.join(labels.values())

    # Sustituye el “grab” para capturar solo una línea por campo
    def grab_line(label_pat):
        rx = rf'{label_pat}\s*:\s*([^\n]+)'
        m = re.search(rx, sanitized, re.IGNORECASE)
        return m.group(1).strip() if m else None

    extracted = {
        'poliza': grab_line(labels['poliza']),
        'ramo': grab_line(labels['ramo']),
        'vigencia_desde': grab_line(labels['vigencia_desde']),
        'vigencia_hasta': grab_line(labels['vigencia_hasta']),
        'sede': grab_line(labels['sede']),
        'contratante': grab_line(labels['contratante']),
        'direccion': grab_line(labels['direccion']),
        'codigo_sbs': grab_line(labels['codigo_sbs']),
        # NUEVO: asegurado
        'asegurado': grab_line(labels['asegurado']),
        # nuevos campos
        'numero_proforma': None,
        'ruc': None,
        'emision': None,
        'nro_tramite': None,
        'moneda': None,
        'telefonos': None,
        'distrito': None,
        'provincia': None,
        'departamento': None,
        'monto': None,
        'prima_total': None,
        'prima_neta': None,
        'porc_subagente': None,
        'porc_compania': None,
        # alias para la UI
        'hasta': None,
        # NUEVO: soporte de Salud
        'contrato_nro': None,
        'doc_tipo': None,
        'folio_id': None,
        'folio_label': None,
    }

    # Fallbacks adicionales (por si el valor es solo números/fechas)
    if not extracted['poliza']:
        m = re.search(r'(?:P\w*li?za)\s*N(?:ro|[°º])\s*:\s*([0-9]+)', sanitized, re.IGNORECASE)
        extracted['poliza'] = m.group(1) if m else None

    # Post-proceso: compacta espacios y recorta campos muy largos
    for k, v in list(extracted.items()):
        if isinstance(v, str):
            v = re.sub(r'\s+', ' ', v).strip()
            if k in ('sede', 'direccion') and len(v) > 250:
                v = v[:250] + '…'
            extracted[k] = v

    # Extras del encabezado y recuadro de recibo
    def find(pat):
        m = re.search(pat, sanitized, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    # helper para probar varios patrones y devolver el primero que calce
    def find_first(patterns):
        for pat in patterns:
            m = re.search(pat, sanitized, re.IGNORECASE | re.DOTALL)
            if m:
                return m.group(1).strip()
        return None

    # Número de Proforma (soporta "Número de Proforma" y "N° Proforma")
    extracted['numero_proforma'] = find_first([
        r'Número\s+de\s+Proforma\s*:\s*([0-9]{6,})',
        r'N[°o]\s*Proforma\s*:\s*([0-9]{6,})',
        r'Proforma\s*N(?:ro|[°º])\s*:\s*([0-9]{6,})'
    ])

    # RUC: capturar solo dígitos (8–11); tolera “doble :” y salto de línea
    m_ruc = re.search(
        r'R\.?U\.?C\.?\s*:\s*(?:\s*:)?\s*(?:\n\s*)?([0-9]{8,11})',
        sanitized,
        re.IGNORECASE
    )
    extracted['ruc'] = m_ruc.group(1).strip() if m_ruc else None
    extracted['emision'] = find(r'Emisi[óo]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    # Nro. Trámite: múltiples variantes soportadas (incluye "Trámite / Operación")
    extracted['nro_tramite'] = find_first([
        r'(?:Nro\.?|N[°º.]|No\.?)\s*(?:de\s*)?Tr[aá]mite\s*:\s*([^\n]+)',
        r'Tr[aá]mite\s*N(?:ro|[°º])\s*:\s*([^\n]+)',
        r'Tr[aá]mite\s*/\s*Operaci[oó]n\s*:\s*([^\n]+)',
        r'Nro\s*Tr[aá]mite\s*[.:]\s*([^\n]+)',
        r'Tr[aá]mite\s*:\s*([^\n]+)'
    ])
    # NUEVO: Contrato Nro (SCTR Salud)
    extracted['contrato_nro'] = find_first([
        r'Contrato\s*N(?:ro|[°º])\s*:\s*([^\n]+)',
        r'Contrato\s*Nro\.?\s*:\s*([^\n]+)'
    ])
    extracted['moneda'] = find(r'Moneda\s*:\s*([^\n]+)')
    extracted['telefonos'] = find(r'Tel[eé]fonos?\s*:\s*([^\n]+)')

    # Distrito (formatos con 1 o 2 paréntesis)
    m_dist = re.search(r'Distrito\s*:\s*([^\n]+)', sanitized, re.IGNORECASE)
    if m_dist:
        dist_raw = m_dist.group(1).strip()
        parts = re.findall(r'\(([^)]+)\)', dist_raw)
        base = re.sub(r'\s*\([^)]+\)\s*', '', dist_raw).strip()  # ej. "PUCALLPA" / "YARINACOCHA"
        if len(parts) >= 2:
            # 2+ paréntesis: primero = distrito, último = departamento
            extracted['distrito'] = parts[0].strip() or base
            extracted['departamento'] = parts[-1].strip()
        elif len(parts) == 1:
            # 1 paréntesis: base es el distrito, paréntesis es el departamento
            extracted['distrito'] = base or parts[0].strip()
            extracted['departamento'] = parts[0].strip()
        else:
            extracted['distrito'] = base or None

    # Provincia desde Localidad
    extracted['provincia'] = find_first([
        r'Localidad\s*:\s*([^\n]+)',
        r'Provincia\s*:\s*([^\n]+)'
    ])

    # Importes: Prima Comercial + IGV (total) y Prima Comercial (neta)
    def parse_amount(num_str):
        # normaliza "659.23" o "659,23" a float
        s = num_str.replace(',', '.')
        try:
            return round(float(s), 2)
        except:
            return None

    # Total: acepta "Prima Comercial + IGV" o "Prima Total"
    m_total = re.search(
        r'(?:Prima\s+Comercial\s*\+\s*IGV|Prima\s+Total)\s*.*?S/?\s*([\d\.,]+)',
        sanitized,
        re.IGNORECASE | re.DOTALL
    )
    if m_total:
        total_val = parse_amount(m_total.group(1))
        if total_val is not None:
            extracted['prima_total'] = f'{total_val:.2f}'
            extracted['monto'] = f'{total_val:.2f}'

    # Neta: intenta "Prima Comercial" sin "+ IGV"
    m_neta = re.search(
        r'Prima\s+Comercial(?!\s*\+).*?S/?\s*([\d\.,]+)',
        sanitized,
        re.IGNORECASE | re.DOTALL
    )
    if m_neta:
        net_val = parse_amount(m_neta.group(1))
        if net_val is not None:
            extracted['prima_neta'] = f'{net_val:.2f}'

    # Si no hay prima_neta pero hay IGV y total, calcular neta = total - IGV
    if not extracted['prima_neta'] and extracted['prima_total']:
        m_igv = re.search(
            r'(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)\s*.*?S/?\s*([\d\.,]+)',
            sanitized,
            re.IGNORECASE | re.DOTALL
        )
        if m_igv:
            igv_val = parse_amount(m_igv.group(1))
            tot_val = parse_amount(extracted['prima_total'])
            if igv_val is not None and tot_val is not None:
                net_val = round(tot_val - igv_val, 2)
                extracted['prima_neta'] = f'{net_val:.2f}'

    # Porcentajes de comisión
    extracted['porc_subagente'] = find(r'(?:Sub[\s\-]?agente|Subagente)[^%\n]*?(\d+(?:[.,]\d+)?)\s*%')
    extracted['porc_compania'] = find(r'(?:Compa[nñ][ií]a|Compañ[ií]a)[^%\n]*?(\d+(?:[.,]\d+)?)\s*%')

    # Alias “Hasta” para el frontend
    extracted['hasta'] = extracted.get('vigencia_hasta') or extracted.get('hasta')

    # Post-proceso: compactar espacios SOLO si hay string; si no, queda vacío
    for k, v in list(extracted.items()):
        if isinstance(v, str):
            v = re.sub(r'\s+', ' ', v).strip()
            extracted[k] = v

    # Determinar tipo de documento por Ramo
    ramo_upper = (extracted.get('ramo') or '').upper()
    if 'SCTR SALUD' in ramo_upper:
        extracted['doc_tipo'] = 'SALUD'
    elif 'SCTR PENSION' in ramo_upper or 'VIDA LEY' in ramo_upper or 'VIDA' in ramo_upper:
        extracted['doc_tipo'] = 'VIDA'

    # Seleccionar folio_id y folio_label: Póliza N° o Contrato Nro
    if extracted.get('poliza'):
        extracted['folio_id'] = extracted['poliza']
        extracted['folio_label'] = 'Póliza N°'
    elif extracted.get('contrato_nro'):
        extracted['folio_id'] = extracted['contrato_nro']
        extracted['folio_label'] = 'Contrato Nro'

    return extracted

def parse_pdf_fields_fitz(file_path):
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text("text") for page in doc)
    doc.close()

    text = text or ""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)

    extracted = {}

    def grab(pattern):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else None

    # Unión de etiquetas para lookahead
    labels = {
        'localidad': r'Localidad',
        'distrito': r'Distrito',
        'telefonos_lbl': r'Tel[eé]fonos?',
        'gestor': r'Gestor',
        'moneda_lbl': r'Moneda',
        'sede': r'Sede\(s\)',
        'contratante': r'Contratante',
        'direccion': r'Direcci[oó]?n',
        'vigencia_hasta': r'Hasta',
        # nuevas/ajustadas
        'provincia_lbl': r'(?:Localidad|Provincia)',
        'departamento_lbl': r'Departamento',
    }
    next_union = '|'.join(labels.values())

    def grab_until_next(label_pat):
        rx = rf'{label_pat}\s*:\s*(.*?)(?=\s*(?:{next_union})\s*:|\n|$)'
        m = re.search(rx, text, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    # Capturas “una línea”
    extracted['poliza'] = grab(r'(?:P[oó]?liza\s*N(?:ro|[°º])\s*:\s*|Poliza\s*:\s*)([^\n]+)')
    extracted['ramo'] = grab(r'Ramo\s*:\s*([^\n]+)')
    extracted['vigencia_desde'] = grab(r'Vigencia\s*desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['vigencia_hasta'] = grab(r'Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    # Fallbacks específicos para DESDE/HASTA sin “:”
    if not extracted.get('vigencia_desde'):
        m_desde = re.search(r'\bDESDE\b\s*[:\-]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', text, re.IGNORECASE)
        if m_desde:
            extracted['vigencia_desde'] = m_desde.group(1).strip()
    if not extracted.get('vigencia_hasta'):
        m_hasta = re.search(r'\bHASTA\b\s*[:\-]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', text, re.IGNORECASE)
        if m_hasta:
            extracted['vigencia_hasta'] = m_hasta.group(1).strip()
        else:
            m_vig_hasta = re.search(r'Vigencia\s*hasta\s*[:\-]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', text, re.IGNORECASE)
            if m_vig_hasta:
                extracted['vigencia_hasta'] = m_vig_hasta.group(1).strip()
    # Alias “Hasta” para el frontend
    extracted['hasta'] = extracted.get('vigencia_hasta') or extracted.get('hasta')
    extracted['sede'] = grab_until_next(labels['sede'])
    extracted['contratante'] = grab_until_next(labels['contratante'])
    extracted['direccion'] = grab_until_next(labels['direccion'])
    # NUEVO: asegurado
    extracted['asegurado'] = grab_until_next(labels['asegurado'])
    extracted['codigo_sbs'] = grab(r'(?:C[oó]?digo|Codigo)\s*SBS\s*:\s*([^\n]+)')

    # Nuevos campos (una línea)
    # Número de Proforma (más tolerante)
    extracted['numero_proforma'] = (
        grab(r'Número\s+de\s+Proforma\s*:\s*([0-9]{6,})')
        or grab(r'N[°o]\s*Proforma\s*:\s*([0-9]{6,})')
        or grab(r'Proforma\s*N(?:ro|[°º])\s*:\s*([0-9]{6,})')
    )

    # RUC: solo dígitos; tolera “doble :” y salto de línea
    m_ruc = re.search(
        r'R\.?U\.?C\.?\s*:\s*(?:\s*:)?\s*(?:\n\s*)?([0-9]{8,11})',
        text,
        re.IGNORECASE
    )
    extracted['ruc'] = m_ruc.group(1).strip() if m_ruc else None
    extracted['emision'] = grab(r'Emisi[óo]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    # Nro. Trámite: variantes (incluye "Trámite / Operación")
    extracted['nro_tramite'] = (
        grab(r'(?:Nro\.?|N[°º.]|No\.?)\s*(?:de\s*)?Tr[aá]mite\s*:\s*([^\n]+)') or
        grab(r'Tr[aá]mite\s*N(?:ro|[°º])\s*:\s*([^\n]+)') or
        grab(r'Tr[aá]mite\s*/\s*Operaci[oó]n\s*:\s*([^\n]+)') or
        grab(r'Nro\s*Tr[aá]mite\s*[.:]\s*([^\n]+)') or
        grab(r'Tr[aá]mite\s*:\s*([^\n]+)')
    )
    # NUEVO: Contrato Nro (SCTR Salud)
    extracted['contrato_nro'] = (
        grab(r'Contrato\s*N(?:ro|[°º])\s*:\s*([^\n]+)') or
        grab(r'Contrato\s*Nro\.?\s*:\s*([^\n]+)')
    )
    extracted['moneda'] = grab_until_next(labels['moneda_lbl'])
    extracted['telefonos'] = grab_until_next(labels['telefonos_lbl'])

    # Distrito (1 o 2 paréntesis) y Provincia
    dist_raw = grab_until_next(labels['distrito'])
    if dist_raw:
        parts = re.findall(r'\(([^)]+)\)', dist_raw)
        base = re.sub(r'\s*\([^)]+\)\s*', '', dist_raw).strip()
        if len(parts) >= 2:
            extracted['distrito'] = parts[0].strip() or base
            extracted['departamento'] = parts[-1].strip()
        elif len(parts) == 1:
            extracted['distrito'] = base or parts[0].strip()
            extracted['departamento'] = parts[0].strip()
        else:
            extracted['distrito'] = base or None

    extracted['provincia'] = grab_until_next(labels['provincia_lbl'])

    # Importes (se mantienen con parsing numérico)
    def parse_amount(num_str):
        s = (num_str or '').replace(',', '.')
        try:
            return round(float(s), 2)
        except:
            return None

    # Total: acepta "Prima Comercial + IGV" o "Prima Total"
    m_total = re.search(
        r'(?:Prima\s+Comercial\s*\+\s*IGV|Prima\s+Total)\s*.*?S/?\s*([\d\.,]+)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if m_total:
        total_val = parse_amount(m_total.group(1))
        if total_val is not None:
            extracted['prima_total'] = f'{total_val:.2f}'
            extracted['monto'] = f'{total_val:.2f}'

    # Neta: intenta "Prima Comercial" sin "+ IGV"
    m_neta = re.search(
        r'Prima\s+Comercial(?!\s*\+).*?S/?\s*([\d\.,]+)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if m_neta:
        net_val = parse_amount(m_neta.group(1))
        if net_val is not None:
            extracted['prima_neta'] = f'{net_val:.2f}'

    # Calcular neta si solo hay Total e IGV
    if not extracted.get('prima_neta') and extracted.get('prima_total'):
        m_igv = re.search(
            r'(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)\s*.*?S/?\s*([\d\.,]+)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if m_igv:
            igv_val = parse_amount(m_igv.group(1))
            tot_val = parse_amount(extracted['prima_total'])
            if igv_val is not None and tot_val is not None:
                extracted['prima_neta'] = f'{(tot_val - igv_val):.2f}'

    extracted['porc_subagente'] = grab(r'(?:Sub[\s\-]?agente|Subagente)[^%\n]*?(\d+(?:[.,]\d+)?)\s*%')
    extracted['porc_compania'] = grab(r'(?:Compa[nñ][ií]a|Compañ[ií]a)[^%\n]*?(\d+(?:[.,]\d+)?)\s*%')

    # Alias “Hasta”
    extracted['hasta'] = extracted.get('vigencia_hasta') or extracted.get('hasta')

    # Limpieza final
    for k, v in list(extracted.items()):
        if isinstance(v, str):
            v = re.sub(r'\s+', ' ', v).strip()
            # Normalización: corregir “CALLARIA” -> “CALLERIA”
            if isinstance(extracted.get('distrito'), str) and extracted['distrito'].upper() == 'CALLARIA':
                extracted['distrito'] = 'CALLERIA'
            extracted[k] = v

    # Determinar tipo de documento por Ramo
    ramo_upper = (extracted.get('ramo') or '').upper()
    if 'SCTR SALUD' in ramo_upper:
        extracted['doc_tipo'] = 'SALUD'
    elif 'SCTR PENSION' in ramo_upper or 'VIDA LEY' in ramo_upper or 'VIDA' in ramo_upper:
        extracted['doc_tipo'] = 'VIDA'

    # Seleccionar folio_id y folio_label: Póliza N° o Contrato Nro
    if extracted.get('poliza'):
        extracted['folio_id'] = extracted['poliza']
        extracted['folio_label'] = 'Póliza N°'
    elif extracted.get('contrato_nro'):
        extracted['folio_id'] = extracted['contrato_nro']
        extracted['folio_label'] = 'Contrato Nro'

    return extracted

def get_rows():
    # Proveer filas para la tabla de index.html
    return [
        {'id': 1, 'nombre': 'Ejemplo A', 'estado': 'Activo'},
        {'id': 2, 'nombre': 'Ejemplo B', 'estado': 'Pendiente'},
        {'id': 3, 'nombre': 'Ejemplo C', 'estado': 'Inactivo'},
    ]

def parse_text_fields_block(text):
    # Parser “por bloque de texto” (una página), reutiliza la lógica de parse_pdf_fields_fitz
    text = text or ""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)

    extracted = {}

    def grab(pattern):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else None

    labels = {
        'localidad': r'Localidad',
        'distrito': r'Distrito',
        'telefonos_lbl': r'Tel[eé]fonos?',
        'gestor': r'Gestor',
        'moneda_lbl': r'Moneda',
        'sede': r'Sede\(s\)',
        'contratante': r'Contratante',
        'direccion': r'Direcci[oó]?n',
        'vigencia_hasta': r'Hasta',
        'provincia_lbl': r'(?:Localidad|Provincia)',
        'departamento_lbl': r'Departamento',
        # NUEVO: asegurado
        'asegurado': r'Asegurado',
    }
    next_union = '|'.join(labels.values())

    def grab_until_next(label_pat):
        rx = rf'{label_pat}\s*:\s*(.*?)(?=\s*(?:{next_union})\s*:|\n|$)'
        m = re.search(rx, text, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    extracted['poliza'] = grab(r'(?:P[oó]?liza\s*N(?:ro|[°º])\s*:\s*|Poliza\s*:\s*)([^\n]+)')
    extracted['ramo'] = grab(r'Ramo\s*:\s*([^\n]+)')
    extracted['vigencia_desde'] = grab(r'Vigencia\s*desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['vigencia_hasta'] = grab(r'Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['sede'] = grab_until_next(labels['sede'])
    extracted['contratante'] = grab_until_next(labels['contratante'])
    extracted['direccion'] = grab_until_next(labels['direccion'])
    # NUEVO: asegurado
    extracted['asegurado'] = grab_until_next(labels['asegurado'])
    extracted['codigo_sbs'] = grab(r'(?:C[oó]?digo|Codigo)\s*SBS\s*:\s*([^\n]+)')

    extracted['numero_proforma'] = (
        grab(r'Número\s+de\s+Proforma\s*:\s*([0-9]{6,})')
        or grab(r'N[°o]\s*Proforma\s*:\s*([0-9]{6,})')
        or grab(r'Proforma\s*N(?:ro|[°º])\s*:\s*([0-9]{6,})')
    )

    m_ruc = re.search(
        r'R\.?U\.?C\.?\s*:\s*(?:\s*:)?\s*(?:\n\s*)?([0-9]{8,11})',
        text,
        re.IGNORECASE
    )
    extracted['ruc'] = m_ruc.group(1).strip() if m_ruc else None
    extracted['emision'] = grab(r'Emisi[óo]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['nro_tramite'] = (
        grab(r'(?:Nro\.?|N[°º.]|No\.?)\s*(?:de\s*)?Tr[aá]mite\s*:\s*([^\n]+)') or
        grab(r'Tr[aá]mite\s*N(?:ro|[°º])\s*:\s*([^\n]+)') or
        grab(r'Tr[aá]mite\s*/\s*Operaci[oó]n\s*:\s*([^\n]+)') or
        grab(r'Nro\s*Tr[aá]mite\s*[.:]\s*([^\n]+)') or
        grab(r'Tr[aá]mite\s*:\s*([^\n]+)')
    )
    extracted['contrato_nro'] = (
        grab(r'Contrato\s*N(?:ro|[°º])\s*:\s*([^\n]+)') or
        grab(r'Contrato\s*Nro\.?\s*:\s*([^\n]+)')
    )
    extracted['moneda'] = grab_until_next(labels['moneda_lbl'])
    extracted['telefonos'] = grab_until_next(labels['telefonos_lbl'])

    dist_raw = grab_until_next(labels['distrito'])
    if dist_raw:
        parts = re.findall(r'\(([^)]+)\)', dist_raw)
        base = re.sub(r'\s*\([^)]+\)\s*', '', dist_raw).strip()
        if len(parts) >= 2:
            extracted['distrito'] = parts[0].strip() or base
            extracted['departamento'] = parts[-1].strip()
        elif len(parts) == 1:
            extracted['distrito'] = base or parts[0].strip()
            extracted['departamento'] = parts[0].strip()
        else:
            extracted['distrito'] = base or None

    extracted['provincia'] = grab_until_next(labels['provincia_lbl'])

    def parse_amount(num_str):
        s = (num_str or '').replace(',', '.')
        try:
            return round(float(s), 2)
        except:
            return None

    m_total = re.search(
        r'(?:Prima\s+Comercial\s*\+\s*IGV|Prima\s+Total)\s*.*?S/?\s*([\d\.,]+)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if m_total:
        total_val = parse_amount(m_total.group(1))
        if total_val is not None:
            extracted['prima_total'] = f'{total_val:.2f}'
            extracted['monto'] = f'{total_val:.2f}'

    m_neta = re.search(
        r'Prima\s+Comercial(?!\s*\+).*?S/?\s*([\d\.,]+)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if m_neta:
        net_val = parse_amount(m_neta.group(1))
        if net_val is not None:
            extracted['prima_neta'] = f'{net_val:.2f}'

    if not extracted.get('prima_neta') and extracted.get('prima_total'):
        m_igv = re.search(
            r'(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)\s*.*?S/?\s*([\d\.,]+)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if m_igv:
            igv_val = parse_amount(m_igv.group(1))
            tot_val = parse_amount(extracted['prima_total'])
            if igv_val is not None and tot_val is not None:
                extracted['prima_neta'] = f'{(tot_val - igv_val):.2f}'

    extracted['porc_subagente'] = grab(r'(?:Sub[\s\-]?agente|Subagente)[^%\n]*?(\d+(?:[.,]\d+)?)\s*%')
    extracted['porc_compania'] = grab(r'(?:Compa[nñ][ií]a|Compañ[ií]a)[^%\n]*?(\d+(?:[.,]\d+)?)\s*%')

    extracted['hasta'] = extracted.get('vigencia_hasta') or extracted.get('hasta')

    for k, v in list(extracted.items()):
        if isinstance(v, str):
            v = re.sub(r'\s+', ' ', v).strip()
            if isinstance(extracted.get('distrito'), str) and extracted['distrito'].upper() == 'CALLARIA':
                extracted['distrito'] = 'CALLERIA'
            extracted[k] = v

    ramo_upper = (extracted.get('ramo') or '').upper()
    if 'SCTR SALUD' in ramo_upper:
        extracted['doc_tipo'] = 'SALUD'
    elif 'SCTR PENSION' in ramo_upper or 'VIDA LEY' in ramo_upper or 'VIDA' in ramo_upper:
        extracted['doc_tipo'] = 'VIDA'

    if extracted.get('poliza'):
        extracted['folio_id'] = extracted['poliza']
        extracted['folio_label'] = 'Póliza N°'
    elif extracted.get('contrato_nro'):
        extracted['folio_id'] = extracted['contrato_nro']
        extracted['folio_label'] = 'Contrato Nro'

    return extracted

# NUEVO: helper para eliminar duplicados quedándose con el que tiene más información
def dedupe_items(items):
    def canonical_id(it):
        folio = (it.get('folio_id') or it.get('poliza') or it.get('contrato_nro') or it.get('numero_proforma') or '').strip()
        tipo = (it.get('doc_tipo') or '').upper().strip()
        return f'{tipo}|{folio}' if folio else ''

    def completeness_score(it):
        score = 0
        for k, v in it.items():
            if k in ('folio_label',):
                continue
            if isinstance(v, str):
                if v.strip():
                    score += 1
            elif v is not None:
                score += 1
        return score

    best_map = {}
    order_keys = []
    noid_counter = 0

    for it in items:
        key = canonical_id(it)
        if not key:
            tmp_key = ('__noid__', noid_counter)
            noid_counter += 1
            best_map[tmp_key] = it
            order_keys.append(tmp_key)
            continue

        if key not in best_map:
            best_map[key] = it
            order_keys.append(key)
        else:
            if completeness_score(it) > completeness_score(best_map[key]):
                best_map[key] = it

    result = [best_map[k] for k in order_keys]
    return result

def parse_pdf_items(file_path):
    # Devuelve una lista de registros, uno por página/sección
    doc = fitz.open(file_path)
    items = []
    try:
        for page in doc:
            text = page.get_text("text") or ""
            ex = parse_text_fields_block(text)
            has_any = any([
                (ex.get('ramo') or '').strip(),
                (ex.get('poliza') or '').strip(),
                (ex.get('contrato_nro') or '').strip(),
                (ex.get('numero_proforma') or '').strip(),
            ])
            if has_any:
                items.append(ex)
    finally:
        doc.close()
    # NUEVO: aplicar deduplicación por (doc_tipo, folio/póliza/contrato/proforma)
    items = dedupe_items(items)
    return items

def detect_issuer(text):
    t = (text or "").upper()
    if "MAPFRE" in t and ("ENTIDAD PRESTADORA" in t or "FACTURA ELECTRONICA" in t):
        return "MAPFRE"
    if "LA POSITIVA" in t and "EPS" in t:
        return "LA_POSITIVA_EPS"
    if "LA POSITIVA" in t and "VIDA" in t:
        return "LA_POSITIVA_VIDA"
    if "LA POSITIVA" in t and "SEGUROS" in t:
        return "LA_POSITIVA_SEGUROS"
    return None

def _parse_mapfre_page(text):
    base = parse_text_fields_block(text)
    def grab(pat):
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else None
    m = re.search(r'FECHA\s+EMISI[óo]N\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', text, re.IGNORECASE)
    if m: base['emision'] = m.group(1).strip()
    m = re.search(r'POLI?ZA\s*:\s*([0-9A-Z\-]+)', text, re.IGNORECASE)
    if m and not base.get('poliza'): base['poliza'] = m.group(1).strip()
    m = re.search(r'\bDESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', text, re.IGNORECASE)
    if m and not base.get('vigencia_desde'): base['vigencia_desde'] = m.group(1).strip()
    m = re.search(r'\bHASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', text, re.IGNORECASE)
    if m and not base.get('vigencia_hasta'): base['vigencia_hasta'] = m.group(1).strip()
    m = re.search(r'CONTRATANTE\s*:\s*([^\n]+)', text, re.IGNORECASE)
    if m and not base.get('contratante'): base['contratante'] = m.group(1).strip()
    m = re.search(r'DIRECCI[óo]N\s*:\s*([^\n]+)', text, re.IGNORECASE)
    if m and not base.get('direccion'): base['direccion'] = m.group(1).strip()
    ramo = grab(r'(Seguro\s+De\s+SCTR\s+(SALUD|PENSI[óo]N)|SCTR\s+(SALUD|PENSI[óo]N)|VIDA\s+LEY)')
    if ramo and not base.get('ramo'): base['ramo'] = ramo
    def parse_amount(s):
        s = (s or '').replace(',', '.')
        try: return round(float(s), 2)
        except: return None
    m_neta = re.search(r'Prima\s+Comercial\s+S/?\s*([\d\.,]+)', text, re.IGNORECASE)
    if m_neta:
        v = parse_amount(m_neta.group(1))
        if v is not None: base['prima_neta'] = f'{v:.2f}'
    m_igv = re.search(r'(Impuesto\s+Gral\.?\s*(?:A\s+Las\s+Ventas)?|IGV)\s+S/?\s*([\d\.,]+)', text, re.IGNORECASE)
    m_total = re.search(r'(Importe\s+Total|Total)\s+S/?\s*([\d\.,]+)', text, re.IGNORECASE)
    if m_total:
        tv = parse_amount(m_total.group(2))
        if tv is not None:
            base['prima_total'] = f'{tv:.2f}'
            base['monto'] = f'{tv:.2f}'
            if not base.get('prima_neta') and m_igv:
                igv = parse_amount(m_igv.group(2))
                if igv is not None: base['prima_neta'] = f'{(tv - igv):.2f}'
    ru = re.search(r'R\.?U\.?C\.?\s*:?[\s\n]*([0-9]{8,11})', text, re.IGNORECASE)
    if ru: base['ruc'] = ru.group(1).strip()
    base['hasta'] = base.get('vigencia_hasta') or base.get('hasta')
    r = (base.get('ramo') or '').upper()
    if 'SALUD' in r: base['doc_tipo'] = 'SALUD'
    elif 'VIDA' in r or 'PENSI' in r: base['doc_tipo'] = 'VIDA'
    if base.get('poliza') and not base.get('folio_id'):
        base['folio_id'] = base['poliza']; base['folio_label'] = 'Póliza N°'
    return base

def _parse_la_positiva_page(text):
    base = parse_text_fields_block(text)
    r = (base.get('ramo') or '').upper()
    if 'SALUD' in r: base['doc_tipo'] = 'SALUD'
    elif 'VIDA' in r or 'PENSION' in r or 'VIDA LEY' in r: base['doc_tipo'] = 'VIDA'
    if base.get('poliza') and not base.get('folio_id'):
        base['folio_id'] = base['poliza']; base['folio_label'] = 'Póliza N°'
    elif base.get('contrato_nro') and not base.get('folio_id'):
        base['folio_id'] = base['contrato_nro']; base['folio_label'] = 'Contrato Nro'
    return base

def parse_provider_page(text, issuer=None):
    prov = issuer or detect_issuer(text)
    if prov == "MAPFRE":
        return _parse_mapfre_page(text)
    if prov in ("LA_POSITIVA_EPS", "LA_POSITIVA_VIDA", "LA_POSITIVA_SEGUROS"):
        return _parse_la_positiva_page(text)
    return parse_text_fields_block(text)

def parse_pdf_items_provider(file_path, issuer=None):
    doc = fitz.open(file_path)
    items = []
    try:
        for page in doc:
            text = page.get_text("text") or ""
            ex = parse_provider_page(text, issuer)
            has_any = any([
                (ex.get('ramo') or '').strip(),
                (ex.get('poliza') or '').strip(),
                (ex.get('contrato_nro') or '').strip(),
                (ex.get('numero_proforma') or '').strip(),
            ])
            if has_any:
                items.append(ex)
    finally:
        doc.close()
    items = dedupe_items(items)
    return items

# función nueva para guardar las filas del tablero
def save_polizas(items: list[dict], selected: dict) -> dict:
    from models.db import get_connection
    numero_documento = (selected.get('n_doc') or selected.get('numero_documento') or '').strip()
    if not numero_documento:
        return {'ok': False, 'errors': ['Falta numero_documento del cliente seleccionado']}

    saved = 0
    errors = []
    cnx = None
    cur = None
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        for it in items:
            def norm(key, default=''):
                val = (it.get(key) or default)
                return str(val).strip()

            def to_date(val):
                v = (val or '').strip()
                # convierte 'dd/mm/yyyy' -> 'yyyy-mm-dd' si aplica
                import re
                m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', v)
                if m:
                    return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
                return v or None

            def to_num(val):
                s = str(val or '').replace(',', '.').strip()
                try:
                    return float(s)
                except:
                    return None

            cur.execute(
                "CALL sp_insert_poliza_por_numero(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    numero_documento,
                    norm('asegurado'),
                    norm('porc_compania'),
                    norm('ramo'),
                    norm('producto'),
                    norm('poliza'),
                    norm('contrato_nro'),
                    norm('nro'),
                    norm('moneda'),
                    to_date(it.get('vigencia_desde') or it.get('vig_desde')),
                    to_date(it.get('hasta') or it.get('vigencia_hasta') or it.get('vig_hasta')),
                    norm('subagente') or (selected.get('subagente') or ''),
                    to_num(it.get('asegurada') or it.get('monto')),
                    to_num(it.get('prima_neta')),
                    to_num(it.get('prima_total')),
                    to_num(it.get('porc_subagente')),
                    to_num(it.get('porc_compania')),
                )
            )
            saved += 1
        cnx.commit()
        while cur.nextset():
            pass
        return {'ok': True, 'saved': saved}
    except Exception as e:
        errors.append(str(e))
        return {'ok': False, 'errors': errors, 'saved': saved}
    finally:
        try:
            cur and cur.close()
            cnx and cnx.close()
        except:
            pass