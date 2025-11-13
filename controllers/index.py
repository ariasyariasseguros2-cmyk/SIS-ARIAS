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
    }
    # Unión para lookahead a “la próxima etiqueta”
    next_union = '|'.join(labels.values())

    def grab(label_pat):
        # Captura hasta la próxima etiqueta o fin de línea/texto
        rx = rf'{label_pat}\s*:\s*(.+?)(?=\s*(?:{next_union})\s*:|\n|$)'
        m = re.search(rx, sanitized, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    extracted = {
        'poliza': grab(labels['poliza']),
        'ramo': grab(labels['ramo']),
        'vigencia_desde': grab(labels['vigencia_desde']),
        'vigencia_hasta': grab(labels['vigencia_hasta']),
        'sede': grab(labels['sede']),
        'contratante': grab(labels['contratante']),
        'direccion': grab(labels['direccion']),
        'codigo_sbs': grab(labels['codigo_sbs']),
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

    return extracted

def parse_pdf_fields_fitz(file_path):
    doc = fitz.open(file_path)
    text = ""
    if doc.page_count > 0:
        page = doc[0]
        # Extrae el texto “plano” de la página (sin artefactos cid)
        text = page.get_text("text")
    doc.close()

    # Normaliza espacios y saltos
    text = text or ""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)

    extracted = {}

    def grab(pattern):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else None

    # Capturas por línea; incluye variantes como "Poliza :" del recuadro derecho
    extracted['poliza'] = grab(r'^(?:P[oó]?liza\s*N(?:ro|[°º])\s*:\s*|Poliza\s*:\s*)(\d+)')
    extracted['ramo'] = grab(r'^Ramo\s*:\s*(.+)')
    extracted['vigencia_desde'] = grab(r'^Vigencia\s*desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['vigencia_hasta'] = grab(r'^Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    extracted['sede'] = grab(r'^Sede\(s\)\s*:\s*(.+)')
    extracted['contratante'] = grab(r'^Contratante\s*:\s*(.+)')
    extracted['direccion'] = grab(r'^Direcci[oó]?n\s*:\s*(.+)')
    extracted['codigo_sbs'] = grab(r'^(?:C[oó]?digo|Codigo)\s*SBS\s*:\s*([A-Z0-9]+)')

    # Limpia y compacta
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