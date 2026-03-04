from flask import Blueprint, render_template, request, jsonify, send_file, current_app, session
from models.db import get_connection
from utils.rbac import Roles
import os
import zipfile
import io

bp = Blueprint('reporte_archivos_poliza', __name__)

def get_reporte_archivos(search=''):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_reporte_archivos_resumen', [search])
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        cursor.close()
        conn.close()
        # serializar datetimes
        for r in results:
            if r.get('ultima_fecha') and hasattr(r['ultima_fecha'], 'strftime'):
                r['ultima_fecha'] = r['ultima_fecha'].strftime('%Y-%m-%dT%H:%M:%S')
        return results
    except Exception as e:
        print(f"Error fetching reporte archivos: {e}")
        return []

def get_archivos_detalle(search='', identificador='', tipo_origen=''):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_reporte_archivos_detalle', [search, identificador, tipo_origen])
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching detalle archivos: {e}")
        return []

@bp.route('/reportes/reporte-archivos-poliza', methods=['GET'])
def index():
    return render_template('view/reportes/reporte-archivos-poliza.html')

@bp.route('/api/reportes/archivos-poliza', methods=['GET'])
def api_search():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    if session.get('role_name') == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403
    search = request.args.get('search', '')
    data = get_reporte_archivos(search)
    return jsonify(data)

@bp.route('/api/reportes/download-zip', methods=['GET'])
def download_zip():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    if session.get('role_name') == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    search      = request.args.get('search', '')
    identificador = request.args.get('identificador', '')
    tipo_origen = request.args.get('tipo', '')   # POLIZA or CUOTA

    results = get_archivos_detalle(search, identificador, tipo_origen)

    if not results:
        return jsonify({'error': 'No se encontraron archivos'}), 404

    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            files_added = 0
            upload_folder = current_app.config.get('UPLOAD_FOLDER',
                os.path.join(current_app.root_path, 'static', 'uploads'))

            for row in results:
                file_path = row['ruta_archivo']

                # Candidatos de ruta en orden de prioridad:
                # 1. Relativo a UPLOAD_FOLDER  (ej: cuotas/archivo.pdf  o  polizas/archivo.pdf)
                # 2. Relativo a root_path       (legacy: static/uploads/polizas/archivo.pdf)
                # 3. Relativo a root_path/static (doble prefijo legacy)
                candidates = [
                    os.path.join(upload_folder, file_path.lstrip('/\\')),
                    os.path.join(current_app.root_path, file_path.lstrip('/\\')),
                    os.path.join(current_app.root_path, 'static', file_path.lstrip('/\\')),
                ]

                final_path = next((p for p in candidates if os.path.exists(p)), None)

                if final_path:
                    arcname = f"{row['idArchivo']}_{row['nombre_original'] or os.path.basename(file_path)}"
                    zf.write(final_path, arcname)
                    files_added += 1

            if files_added == 0:
                return jsonify({'error': 'Los archivos físicos no existen en el servidor'}), 404

        memory_file.seek(0)
        zip_name = f"archivos_{identificador or 'resultados'}.zip"

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name
        )
    except Exception as e:
        print(f"Error generating zip: {e}")
        return jsonify({'error': 'Error generando archivo ZIP'}), 500

