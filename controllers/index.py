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
        # añadidas para poder cortar valores
        'localidad': r'Localidad',
        'distrito': r'Distrito',
        'telefonos_lbl': r'Tel[eé]fonos?',
        'gestor': r'Gestor',
        'moneda_lbl': r'Moneda',
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

    extracted['numero_proforma'] = find(r'Número\s+de\s+Proforma\s*:\s*([^\n]+)')
    # RUC: soporta que el valor esté en la línea siguiente al “:”
    m_ruc = re.search(r'R\.?U\.?C\.?\s*:\s*(?:\n\s*)?([0-9]{8,})', sanitized, re.IGNORECASE)
    extracted['ruc'] = m_ruc.group(1).strip() if m_ruc else None
    extracted['emision'] = find(r'Emisi[óo]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['nro_tramite'] = find(r'Nro\.?\s*Tr[aá]mite\s*:\s*([^\n]+)')
    extracted['moneda'] = find(r'Moneda\s*:\s*([^\n]+)')
    extracted['telefonos'] = find(r'Tel[eé]fonos?\s*:\s*([^\n]+)')

    # Distrito (con posible departamento entre paréntesis)
    m_dist = re.search(r'Distrito\s*:\s*([^\n]+)', sanitized, re.IGNORECASE)
    if m_dist:
        dist_raw = m_dist.group(1).strip()
        m_dept = re.search(r'\(([^)]+)\)', dist_raw)
        extracted['departamento'] = m_dept.group(1).strip() if m_dept else None
        extracted['distrito'] = re.sub(r'\s*\([^)]+\)\s*', '', dist_raw).strip() or None

    # Provincia desde Localidad
    extracted['provincia'] = find(r'Localidad\s*:\s*([^\n]+)')

    # Importes: Prima Comercial + IGV (total) y Prima Comercial (neta)
    def parse_amount(num_str):
        # normaliza "659.23" o "659,23" a float
        s = num_str.replace(',', '.')
        try:
            return round(float(s), 2)
        except:
            return None

    m_total = re.search(r'Prima\s+Comercial\s*\+\s*IGV.*?S/\s*([\d\.,]+)', sanitized, re.IGNORECASE | re.DOTALL)
    if m_total:
        total_val = parse_amount(m_total.group(1))
        if total_val is not None:
            extracted['prima_total'] = f'{total_val:.2f}'
            extracted['monto'] = f'{total_val:.2f}'

    m_neta = re.search(r'Prima\s+Comercial(?!\s*\+).*?S/\s*([\d\.,]+)', sanitized, re.IGNORECASE | re.DOTALL)
    if m_neta:
        net_val = parse_amount(m_neta.group(1))
        if net_val is not None:
            extracted['prima_neta'] = f'{net_val:.2f}'

    # Si no hay prima_neta pero hay IGV y total, calcular neta = total - IGV
    if not extracted['prima_neta'] and extracted['prima_total']:
        m_igv = re.search(r'(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)\s*.*?S/\s*([\d\.,]+)', sanitized, re.IGNORECASE | re.DOTALL)
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
    extracted['sede'] = grab_until_next(labels['sede'])
    extracted['contratante'] = grab_until_next(labels['contratante'])
    extracted['direccion'] = grab_until_next(labels['direccion'])
    extracted['codigo_sbs'] = grab(r'(?:C[oó]?digo|Codigo)\s*SBS\s*:\s*([^\n]+)')

    # Nuevos campos (una línea)
    extracted['numero_proforma'] = grab(r'Número\s+de\s+Proforma\s*:\s*([^\n]+)')
    extracted['ruc'] = grab(r'R\.?U\.?C\.?\s*:\s*([^\n]+)')
    extracted['emision'] = grab(r'Emisi[óo]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['nro_tramite'] = grab(r'Nro\.?\s*Tr[aá]mite\s*:\s*([^\n]+)')
    extracted['moneda'] = grab_until_next(labels['moneda_lbl'])
    extracted['telefonos'] = grab_until_next(labels['telefonos_lbl'])

    # Distrito y Provincia con lookahead
    dist_raw = grab_until_next(labels['distrito'])
    if dist_raw:
        m_dept = re.search(r'\(([^)]+)\)', dist_raw)
        extracted['departamento'] = m_dept.group(1).strip() if m_dept else None
        extracted['distrito'] = re.sub(r'\s*\([^)]+\)\s*', '', dist_raw).strip() or None

    extracted['provincia'] = grab_until_next(labels['localidad'])

    # Importes (se mantienen con parsing numérico)
    def parse_amount(num_str):
        s = (num_str or '').replace(',', '.')
        try:
            return round(float(s), 2)
        except:
            return None

    m_total = re.search(r'Prima\s+Comercial\s*\+\s*IGV.*?S/\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
    if m_total:
        total_val = parse_amount(m_total.group(1))
        if total_val is not None:
            extracted['prima_total'] = f'{total_val:.2f}'
            extracted['monto'] = f'{total_val:.2f}'

    m_neta = re.search(r'Prima\s+Comercial(?!\s*\+).*?S/\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
    if m_neta:
        net_val = parse_amount(m_neta.group(1))
        if net_val is not None:
            extracted['prima_neta'] = f'{net_val:.2f}'

    if not extracted.get('prima_neta') and extracted.get('prima_total'):
        m_igv = re.search(r'(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)\s*.*?S/\s*([\d\.,]+)', text, re.IGNORECASE | re.DOTALL)
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
            extracted[k] = v
    return extracted

def get_rows():
    # Proveer filas para la tabla de index.html
    return [
        {'id': 1, 'nombre': 'Ejemplo A', 'estado': 'Activo'},
        {'id': 2, 'nombre': 'Ejemplo B', 'estado': 'Pendiente'},
        {'id': 3, 'nombre': 'Ejemplo C', 'estado': 'Inactivo'},
    ]