from flask import Blueprint, redirect, url_for, session, render_template, request, current_app
from werkzeug.utils import secure_filename
import os


bp = Blueprint('main', __name__)


@bp.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    rows = get_rows()
    chart = get_dashboard_data()
    return render_template('view/dashboard.html', rows=rows, chart=chart)

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    rows = get_rows()
    chart = get_dashboard_data()
    return render_template('view/dashboard.html', rows=rows, chart=chart)

@bp.route('/menu/<page>')
def menu_page(page):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Clientes → renderiza su plantilla dedicada con sus datos
    if page == 'clientes':
        from controllers.cliente import get_clientes_data
        data = get_clientes_data()
        return render_template(
            'view/cliente/cliente.html',
            page='clientes',
            title=data['title'],
            rows=data['rows'],
            filters=data['filters']
        )

    # Pólizas → plantilla dedicada
    if page == 'polizas':
        from controllers.polizas import get_polizas_data
        # Tomar la selección almacenada en sesión (sin exponer en la URL)
        selected = session.get('selected_cliente') or {}
        data = get_polizas_data(selected)
        return render_template(
            'view/polizas.html',
            page='polizas',
            title=data['title'],
            rows=data['rows'],
            details=data.get('details', {})
        )

    # NUEVO: página “Añadir Póliza”
    if page == 'anadir-poliza':
        from controllers.addPoliza import get_rows
        from controllers.cliente import get_clientes_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones  # NUEVO
        from controllers.ejecutivos import get_ejecutivos               # NUEVO
        cli_data = get_clientes_data()
        selected = session.get('selected_cliente') or {}

        # Hidratar datos faltantes del cliente seleccionado
        if not selected.get('subagente'):
            match = None
            sel_doc = (selected.get('n_doc') or '').strip()
            sel_name = (selected.get('razon_social') or selected.get('nombre') or '').strip()
            for c in cli_data['rows']:
                if sel_doc and c.get('n_doc') == sel_doc:
                    match = c
                    break
                if not match and sel_name and c.get('razon_social') == sel_name:
                    match = c
            if match:
                selected['subagente'] = match.get('subagente')
                # Completar nombre si faltaba
                selected['razon_social'] = selected.get('razon_social') or match.get('razon_social')

        return render_template(
            'view/anadir.poliza.html',
            rows=get_rows(),
            clientes_rows=cli_data['rows'],
            selected=selected,
            ramos_abbrs=get_ramos(),
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),  # NUEVO
            ejecutivos_rows=get_ejecutivos()                  # NUEVO
        )

    # Fallback: otras secciones usan el dashboard con etiqueta de sección
    rows = get_rows()
    chart = get_dashboard_data()
    return render_template('view/dashboard.html', rows=rows, chart=chart, page=page)

@bp.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        # En llamadas XHR, devolver JSON claro en vez de redirect HTML
        return {'error': 'No autenticado'}, 401

    if 'file' not in request.files:
        return {'error': 'No se envió archivo'}, 400

    file = request.files['file']
    if file.filename == '':
        return {'error': 'Nombre de archivo vacío'}, 400

    if not allowed_file(file.filename):
        return {'error': 'Tipo de archivo no permitido'}, 400

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    filename = secure_filename(file.filename)
    save_path = os.path.join(upload_folder, filename)
    os.makedirs(upload_folder, exist_ok=True)
    file.save(save_path)

    issuer = (request.form.get('issuer') or '').strip() or None
    # Modo debug: si llega desde el cliente
    debug_enabled = (request.form.get('debug') == '1') or (request.args.get('debug') == '1')
    debug_logs = []
    def LOG(msg):
        print(msg)
        if debug_enabled:
            debug_logs.append(str(msg))

    LOG(f'[upload] issuer={issuer} file={filename}')

    items = []
    if filename.lower().endswith('.pdf'):
        try:
            items = parse_pdf_items_provider(save_path, issuer)
            LOG(f'[upload] provider items count={len(items)}')
        except Exception as e:
            LOG(f'[upload] provider parse error: {e}')
            items = []

    # Normalización: mapear variantes de claves a las usadas por la UI
    def _normalize_to_ui(it: dict) -> dict:
        return {
            "numero_poliza": it.get("numero_poliza") or it.get("poliza") or it.get("folio_id") or it.get("contrato_nro"),
            "recibo": it.get("recibo") or it.get("numero_proforma") or it.get("nro_tramite"),
            "colectivo_asegurado": it.get("colectivo_asegurado") or it.get("asegurado") or it.get("contratante"),
            "inicio_vigencia": it.get("inicio_vigencia") or it.get("vigencia_desde"),
            "vencimiento": it.get("vencimiento") or it.get("vigencia_hasta") or it.get("hasta"),
            "moneda": it.get("moneda"),
            "fecha_emision": it.get("fecha_emision") or it.get("emision"),
            "forma_pago": it.get("forma_pago"),
            "ultimo_dia_pago": it.get("ultimo_dia_pago"),
            "prima_comercial": it.get("prima_comercial"),
            "prima_neta": it.get("prima_neta"),
            "prima_total": it.get("prima_total") or it.get("monto"),
            "prima_comercial_igv": it.get("prima_comercial_igv") or it.get("prima_total") or it.get("monto"),
            "ramo": it.get("ramo") or it.get("doc_tipo"),  # <- REACTIVADO
        }

    if items and len(items) > 0:
        LOG('[upload] Origen de datos: provider parser (items).')
        items_ui = [_normalize_to_ui(it) for it in items]

        # Dedupe por combinación clave y descartar muy vacíos
        unique = []
        seen = set()
        for it in items_ui:
            key = f"{it.get('numero_poliza') or ''}|{it.get('recibo') or ''}|{it.get('ramo') or ''}"
            is_meaningful = any(it.get(k) for k in ['numero_poliza', 'recibo', 'colectivo_asegurado', 'moneda', 'prima_comercial_igv'])
            if not is_meaningful:
                LOG(f"[upload] descartado item vacío: {it}")
                continue
            if key in seen:
                LOG(f"[upload] item duplicado (clave={key}) descartado")
                continue
            seen.add(key)
            unique.append(it)

        return {'filename': filename, 'items': unique, 'debug': debug_logs}, 200

    # Fallback: comportamiento anterior (un solo objeto)
    extracted = {}
    if filename.lower().endswith('.pdf'):
        try:
            extracted = parse_pdf_fields_fitz(save_path)
            LOG(f'[upload] fitz fields keys={list(extracted.keys())}')
            extra2 = parse_pdf_fields(save_path)
            LOG(f'[upload] fallback fields keys={list(extra2.keys())}')
            for k, v in extra2.items():
                cur = extracted.get(k)
                if (cur is None or cur == '') and (v is not None and v != ''):
                    extracted[k] = v
            # fallback del folio en servidor
            if not extracted.get('folio_id'):
                cand = extracted.get('poliza') or extracted.get('contrato_nro')
                if cand:
                    extracted['folio_id'] = cand
                    extracted['folio_label'] = 'Contrato Nro' if extracted.get('contrato_nro') else 'Póliza N°'
        except Exception as e:
            LOG(f'[upload] parse error (fitz/pypdf2): {e}')
            extracted = parse_pdf_fields(save_path)
            # fallback del folio también en parse alterno
            if not extracted.get('folio_id'):
                cand = extracted.get('poliza') or extracted.get('contrato_nro')
                if cand:
                    extracted['folio_id'] = cand
                    extracted['folio_label'] = 'Contrato Nro' if extracted.get('contrato_nro') else 'Póliza N°'

    return {'filename': filename, 'fields': extracted, 'debug': debug_logs}, 200


@bp.route('/clientes/add', methods=['POST'])
def clientes_add():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = (request.get_json(silent=True) or request.form.to_dict())
    from controllers.addcliente import save_cliente
    res = save_cliente(data)
    status = 200 if res.get('ok') else 400
    return res, status


@bp.route('/clientes/select', methods=['POST'])
def clientes_select():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    payload = request.get_json(silent=True) or request.form.to_dict()
    selected = {
        'nombre': payload.get('nombre') or payload.get('razon_social'),
        'razon_social': payload.get('razon_social'),
        'tipo_doc': payload.get('tipo_doc') or payload.get('doc') or payload.get('tipo_documento'),
        'n_doc': payload.get('n_doc') or payload.get('numero_documento'),
        'tel': payload.get('tel') or payload.get('telefono'),
        # Acepta subagente con ambos nombres de campo
        'subagente': payload.get('subagente') or payload.get('subAgente'),
    }
    session['selected_cliente'] = selected
    return {'ok': True}, 200

@bp.route('/polizas/save', methods=['POST'])
def polizas_save():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    payload = request.get_json(silent=True) or {}
    items = payload.get('items') or []
    selected = payload.get('selected') or session.get('selected_cliente') or {}

    # Sincroniza la sesión con el subagente seleccionado (y demás campos)
    prev = session.get('selected_cliente') or {}
    if selected:
        session['selected_cliente'] = {**prev, **selected}

    from controllers.addPoliza import save_polizas
    res = save_polizas(items, selected)
    status = 200 if res.get('ok') else 400
    return res, status


# Util: permitir archivos
def allowed_file(filename: str) -> bool:
    ext = (filename or '').rsplit('.', 1)[-1].lower()
    return ext in {'pdf', 'jpg', 'jpeg', 'png'}

# -------- Extracción de texto (PyMuPDF y fallback) --------
def _extract_text_fitz(path: str) -> str:
    try:
        import fitz  # PyMuPDF
        text_chunks = []
        with fitz.open(path) as doc:
            for page in doc:
                text_chunks.append(page.get_text())
        return "\n".join(text_chunks)
    except Exception:
        return _extract_text_pypdf2(path)

def _extract_text_pypdf2(path: str) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception:
        return ""

# -------- Parser por proveedor --------
import re
from typing import List, Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _number(s: Optional[str]) -> Optional[str]:
    if not s: return None
    m = re.search(r"([0-9][0-9\.\-\/ ]+)", s)
    return m.group(1).strip() if m else s

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

def _parse_mapfre(text: str) -> Dict[str, str]:
    item = {}
    item['numero_poliza'] = _find(r"POLIZA\s*:?\s*([0-9A-Z\-]+)", text) or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", text)

    # Recibo desde CONCEPTO y fallback
    recibo_concept = _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*([0-9]+)", text)
    # Fallback anterior: factura o recibo estándar
    recibo_top = _find(r"FACTURA\s+ELECTRONICA\s*\n([A-Z0-9\- ]+)", text) or _find(r"Recibo\s*:?[\s\n]*([0-9A-Z\- ]+)", text)
    item['recibo'] = recibo_concept or recibo_top

    item['colectivo_asegurado'] = _find(r"CONTRATANTE\s*:\s*(.+)", text) or _find(r"Asegurado\s*:\s*(.+)", text)

    # Vigencias: captura en bloque (entre DESDE … HASTA …) y fallback
    m_vig = re.search(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4}).*?HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text, re.IGNORECASE | re.DOTALL)
    if m_vig:
        item['inicio_vigencia'] = m_vig.group(1)
        item['vencimiento'] = m_vig.group(2)
    else:
        item['inicio_vigencia'] = _find(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        item['vencimiento'] = _find(r"HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    item['moneda'] = _find(r"MONEDA\s*:\s*([A-Za-z]+)", text) or _find(r"Moneda\s*:\s*([A-Za-z]+)", text)
    item['fecha_emision'] = _find(r"FECHA\s+EMISION\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text) or _find(r"Emision\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    item['forma_pago'] = _find(r"Forma de Pago\s*:\s*(.+)", text)
    item['ultimo_dia_pago'] = _find(r"Ultimo d[ií]a de Pago\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Ramo desde la línea de CONCEPTO
    ramo_concept = _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*[0-9]+\.?\s*(.+?)(?:\n|$)", text)
    item['ramo'] = ramo_concept

    # Conceptos
    prima = _find(r"Prima Comercial\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    igv = _find(r"(?:Impuesto Gral\.? A Las Ventas|IGV)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    total = _find(r"(?:Importe Total|Total)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    item['prima_comercial'] = prima or _money(_find(r"Prima\s*Total\s*[:]*\s*([0-9\.,]+)", text))
    item['prima_comercial_igv'] = total or (f"{float(prima.replace(',', '.')) + float(igv.replace(',', '.')):.2f}" if prima and igv else None)

    return {k: _clean(v) for k, v in item.items() if v}

def _parse_positiva(text: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    # Partir el PDF en bloques por títulos conocidos
    markers = [r"PROFORMA DE PAGO", r"Proforma de Cobertura \(Cobro\)", r"PROFORMA DE COBERTURA \(Cobro\)"]
    positions = []
    for pat in markers:
        for m in re.finditer(pat, text, re.IGNORECASE):
            positions.append(m.start())
    positions = sorted(set(positions))
    blocks = []
    if positions:
        for i, start in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            blocks.append(text[start:end])
    else:
        blocks = [text]

    def _sum(a: str | None, b: str | None) -> str | None:
        try:
            return f"{float((a or '0').replace(',', '.')) + float((b or '0').replace(',', '.')):.2f}"
        except Exception:
            return None

    for blk in blocks:
        numero_proforma = _find(r"N[uú]mero de Proforma\s*:\s*([0-9A-Z\-]+)", blk)
        poliza_nro = _find(r"P[oó]liza\s*Nro\s*:\s*([0-9A-Z\-]+)", blk) or _find(r"P[oó]liza\s*N°\s*:\s*([0-9A-Z\-]+)", blk) or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", blk)
        contrato_nro = _find(r"Contrato\s+Nro\s*:\s*([0-9A-Z\-]+)", blk)
        vig_desde = _find(r"Vigencia Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        vig_hasta = _find(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk) or _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        moneda = _find(r"Moneda\s*:\s*([A-Za-z]+)", blk)
        emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        ramo = _find(r"Ramo\s*:\s*(.+)", blk)
        contratante = _find(r"Contratante\s*:\s*(.+)", blk)
        asegurado = _find(r"Asegurado\s*:\s*(.+)", blk)
        forma_pago = _find(r"Forma de Pago\s*:\s*(.+)", blk)
        ultimo_dia = _find(r"[ÚU]ltimo d[ií]a de Pago\s*:?[\s]*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)

        prima_total = _money(_find(r"Prima Total\s*S?\/?\s*([0-9\.,]+)", blk))
        igv_val = _money(_find(r"Impuesto General a las Ventas\s*S?\/?\s*([0-9\.,]+)", blk))
        sobrevivencia = _money(_find(r"Sobrevivencia.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        costos_emision = _money(_find(r"Costos?\s+de\s+Emisi[oó]n.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        igv_val = igv_val or _money(_find(r"IGV.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        total_plus_igv_line = _money(_find(r"Prima\s+Comercial\s*\+\s*IGV.*?S?\/?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))

        prima_comercial = _money(_find(r"Prima Comercial\s*S?\/?\s*([0-9\.,]+)", blk)) or prima_total
        if not prima_comercial and (sobrevivencia or costos_emision):
            prima_comercial = _sum(sobrevivencia, costos_emision)

        total_con_igv = None
        if total_plus_igv_line:
            total_con_igv = total_plus_igv_line
        elif prima_comercial and igv_val:
            total_con_igv = _sum(prima_comercial, igv_val)
        elif prima_total and igv_val:
            total_con_igv = _sum(prima_total, igv_val)

        item = {
            'numero_poliza': poliza_nro or contrato_nro,
            'contrato_nro': contrato_nro,
            'recibo': numero_proforma,
            'colectivo_asegurado': asegurado or contratante,
            'inicio_vigencia': vig_desde,
            'vencimiento': vig_hasta,
            'moneda': moneda,
            'fecha_emision': emision,
            'forma_pago': forma_pago,
            'ultimo_dia_pago': ultimo_dia,
            'prima_comercial': prima_comercial or prima_total,
            'prima_comercial_igv': total_con_igv or prima_total,
            'ramo': ramo
        }
        items.append({k: _clean(v) for k, v in item.items() if v})

    return items

def parse_pdf_items_provider(path: str, issuer: Optional[str] = None) -> List[Dict[str, str]]:
    text = _extract_text_fitz(path)
    prov = (issuer or "").lower()
    if not prov:
        prov = "positiva" if "la positiva" in text.lower() else ("mapfre" if "mapfre" in text.lower() else "")

    if prov == "mapfre":
        item = _parse_mapfre(text)
        return [item] if item else []
    # La Positiva (EPS/Vida/Seguros)
    if prov in {"positiva", ""}:
        return _parse_positiva(text)
    return []

def parse_pdf_fields_fitz(path: str) -> Dict[str, str]:
    # Devuelve un único objeto (fallback)
    items = parse_pdf_items_provider(path)
    return items[0] if items else {}

def parse_pdf_fields(path: str) -> Dict[str, str]:
    # Fallback simple: intenta más patrones sobre todo el texto
    text = _extract_text_pypdf2(path)
    if not text:
        return {}
    items = parse_pdf_items_provider(path)
    return items[0] if items else {}

# -------- Opcional: usar PDF.co si configuras la API key --------
def parse_pdf_fields_pdfco(path: str) -> Dict[str, str]:
    import os, requests
    api_key = os.getenv("PDFCO_API_KEY")  # <- FIX: variable correcta
    if not api_key:
        return {}
    # Sube archivo en crudo con inline=true para obtener texto y luego aplicar patrones
    url = "https://api.pdf.co/v1/pdf/convert/to/text"
    files = {'file': open(path, 'rb')}
    payload = {'inline': True}
    headers = {'x-api-key': api_key}
    try:
        r = requests.post(url, data=payload, files=files, headers=headers, timeout=30)
        txt = r.text or ""
        # Reutiliza los parsers sobre el texto
        # Nota: aquí uso el parser La Positiva/Mapfre por patrones
        # (puedes expandir con reglas adicionales si aparecen más variantes)
        prov = "positiva" if "la positiva" in txt.lower() else ("mapfre" if "mapfre" in txt.lower() else "")
        if prov == "mapfre":
            return _parse_mapfre(txt)
        return (_parse_positiva(txt) or [{}])[0]
    except Exception:
        return {}


@bp.route('/dashboard/notes', methods=['GET', 'POST'])
def dashboard_notes():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    notes_path = os.path.join(current_app.root_path, 'plaintext', 'dashboard_notes.txt')
    os.makedirs(os.path.dirname(notes_path), exist_ok=True)

    if request.method == 'GET':
        try:
            with open(notes_path, 'r', encoding='utf-8') as f:
                return {'ok': True, 'notes': f.read()}, 200
        except Exception:
            return {'ok': True, 'notes': ''}, 200

    data = request.get_json(silent=True) or request.form.to_dict()
    content = data.get('notes') or ''
    try:
        with open(notes_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {'ok': True}, 200
    except Exception as e:
        return {'ok': False, 'errors': [str(e)]}, 500

