from flask import Blueprint, redirect, url_for, session, render_template, request, current_app
from werkzeug.utils import secure_filename
import os
from controllers.index import allowed_file, parse_pdf_fields, parse_pdf_fields_fitz, get_rows

bp = Blueprint('main', __name__)


@bp.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    rows = get_rows()
    return render_template('view/index.html', rows=rows)

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

    extracted = {}
    if filename.lower().endswith('.pdf'):
        try:
            extracted = parse_pdf_fields_fitz(save_path)
            extra2 = parse_pdf_fields(save_path)
            for k, v in extra2.items():
                if not extracted.get(k) and v:
                    extracted[k] = v
        except Exception:
            extracted = parse_pdf_fields(save_path)

    # Cambia 'fields' -> 'extracted' para coincidir con el frontend histórico
    return {'filename': filename, 'extracted': extracted}, 200

