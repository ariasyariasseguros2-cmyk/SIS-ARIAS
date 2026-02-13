from flask import Blueprint, render_template, request, jsonify, send_file, current_app, abort, session, redirect, url_for
from models.db import get_connection
from utils.rbac import Roles
import os
import zipfile
import io

bp = Blueprint('reporte_archivos_cliente', __name__)


def get_client_files(cliente_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT idArchivo, ruta_archivo, nombre_original, creado_en FROM cliente_archivos WHERE cliente_id = %s ORDER BY creado_en DESC"
        cursor.execute(sql, (cliente_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error fetching client files: {e}")
        return []


@bp.route('/reportes/reporte-archivos-cliente')
def index():
    # Require session
    if 'user' not in session:
        return redirect(url_for('login'))
    # Expect cliente_id as query param
    cliente_id = request.args.get('cliente_id')
    return render_template('view/reportes/reporte-archivos-cliente.html', cliente_id=cliente_id)


@bp.route('/api/reportes/archivos-cliente', methods=['GET'])
def api_client_files():
    if 'user' not in session:
        return jsonify([]), 401

    # SUB AGENTE: Blocked (Only allowed 'estado de cuenta' and 'producción')
    # Unless this is considered part of account management?
    # User said "Reporte estado de cuenta y producción". This is "Reporte Archivos Cliente".
    # Blocking to be safe and consistent with other reports.
    if session.get('role_name') == Roles.SUB_AGENTE:
        return jsonify([]), 403

    cliente_id = request.args.get('cliente_id')
    if not cliente_id:
        return jsonify([])
    rows = get_client_files(cliente_id)
    return jsonify(rows)


@bp.route('/reportes/archivo-cliente')
def serve_client_file():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session.get('role_name') == Roles.SUB_AGENTE:
        abort(403)

    # Serve a single file (for iframe viewer)
    idArchivo = request.args.get('idArchivo') or request.args.get('id')
    if not idArchivo:
        abort(404)
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT ruta_archivo, nombre_original FROM cliente_archivos WHERE idArchivo = %s', (idArchivo,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            abort(404)

        file_path = row.get('ruta_archivo')
        # Resolve robustly like other controller
        abs_path_root = os.path.join(current_app.root_path, file_path.lstrip('/\\'))
        abs_path_static = os.path.join(current_app.root_path, 'static', file_path.lstrip('/\\'))
        final_path = None
        if os.path.exists(abs_path_root):
            final_path = abs_path_root
        elif os.path.exists(abs_path_static):
            final_path = abs_path_static

        if not final_path:
            abort(404)

        # Use send_file; let browser display if PDF
        return send_file(final_path, as_attachment=False)
    except Exception as e:
        print(f"Error serving client file: {e}")
        abort(500)


@bp.route('/api/reportes/download-zip-cliente', methods=['GET'])
def download_zip_cliente():
    if 'user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    
    if session.get('role_name') == Roles.SUB_AGENTE:
        return jsonify({'error': 'No autorizado'}), 403

    cliente_id = request.args.get('cliente_id')
    if not cliente_id:
        return jsonify({'error': 'cliente_id requerido'}), 400

    results = get_client_files(cliente_id)
    if not results:
        return jsonify({'error': 'No se encontraron archivos'}), 404

    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            files_added = 0
            for row in results:
                file_path = row['ruta_archivo']
                abs_path_root = os.path.join(current_app.root_path, file_path.lstrip('/\\'))
                abs_path_static = os.path.join(current_app.root_path, 'static', file_path.lstrip('/\\'))
                final_path = None
                if os.path.exists(abs_path_root):
                    final_path = abs_path_root
                elif os.path.exists(abs_path_static):
                    final_path = abs_path_static

                if final_path:
                    arcname = f"{row['idArchivo']}_{row.get('nombre_original') or os.path.basename(file_path)}"
                    zf.write(final_path, arcname)
                    files_added += 1

            if files_added == 0:
                return jsonify({'error': 'Los archivos físicos no existen en el servidor'}), 404

        memory_file.seek(0)
        zip_name = f"cliente_archivos_{cliente_id}.zip"
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name
        )
    except Exception as e:
        print(f"Error generating zip for client: {e}")
        return jsonify({'error': 'Error generando archivo ZIP'}), 500


@bp.route('/reportes/archivo-cliente/download')
def download_client_file():
    # Descarga un archivo como attachment. Acepta idArchivo (preferido) o cliente_id (último archivo)
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session.get('role_name') == Roles.SUB_AGENTE:
        abort(403)

    idArchivo = request.args.get('idArchivo') or request.args.get('id')
    cliente_id = request.args.get('cliente_id')

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if idArchivo:
            cursor.execute('SELECT ruta_archivo, nombre_original FROM cliente_archivos WHERE idArchivo = %s', (idArchivo,))
        elif cliente_id:
            cursor.execute('SELECT ruta_archivo, nombre_original FROM cliente_archivos WHERE cliente_id = %s ORDER BY creado_en DESC LIMIT 1', (cliente_id,))
        else:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Se requiere idArchivo o cliente_id'}), 400

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return jsonify({'error': 'Archivo no encontrado'}), 404

        file_path = row.get('ruta_archivo')
        nombre = row.get('nombre_original') or os.path.basename(file_path or '')

        abs_path_root = os.path.join(current_app.root_path, file_path.lstrip('/\\'))
        abs_path_static = os.path.join(current_app.root_path, 'static', file_path.lstrip('/\\'))
        final_path = None
        if os.path.exists(abs_path_root):
            final_path = abs_path_root
        elif os.path.exists(abs_path_static):
            final_path = abs_path_static

        if not final_path:
            return jsonify({'error': 'Archivo físico no encontrado en el servidor'}), 404

        return send_file(final_path, as_attachment=True, download_name=nombre)
    except Exception as e:
        print(f"Error descargando archivo cliente: {e}")
        return jsonify({'error': 'Error interno al descargar archivo'}), 500

