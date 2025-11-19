from flask import Blueprint, redirect, url_for, session, render_template, request, current_app
from werkzeug.utils import secure_filename
import os
from controllers.addPoliza import allowed_file, parse_pdf_fields, parse_pdf_fields_fitz, get_rows, parse_pdf_items
from controllers.dashboard import get_dashboard_data

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

    # Fallback: otras secciones usan el dashboard con etiqueta de sección
    rows = get_rows()
    chart = get_dashboard_data()
    return render_template('view/dashboard.html', rows=rows, chart=chart, page=page)

@bp.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

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

    # Primero intentamos extraer por páginas (varios ítems)
    items = []
    if filename.lower().endswith('.pdf'):
        try:
            items = parse_pdf_items(save_path)
        except Exception:
            items = []

    if items and len(items) > 0:
        # Cuando hay múltiples secciones (Salud y Pensión), retornamos lista
        return {'filename': filename, 'items': items}, 200

    # Fallback: comportamiento anterior (un solo objeto)
    extracted = {}
    if filename.lower().endswith('.pdf'):
        try:
            extracted = parse_pdf_fields_fitz(save_path)
            extra2 = parse_pdf_fields(save_path)
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
        except Exception:
            extracted = parse_pdf_fields(save_path)
            # fallback del folio también en parse alterno
            if not extracted.get('folio_id'):
                cand = extracted.get('poliza') or extracted.get('contrato_nro')
                if cand:
                    extracted['folio_id'] = cand
                    extracted['folio_label'] = 'Contrato Nro' if extracted.get('contrato_nro') else 'Póliza N°'

    return {'filename': filename, 'fields': extracted}, 200


@bp.route('/clientes/add', methods=['POST'])
def clientes_add():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = (request.get_json(silent=True) or request.form.to_dict())
    from controllers.addcliente import save_cliente
    res = save_cliente(data)
    status = 200 if res.get('ok') else 400
    return res, status

