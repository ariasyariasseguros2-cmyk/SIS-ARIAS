
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from models.db import get_connection
import os
import zipfile
import io

bp = Blueprint('reporte_archivos_poliza', __name__)

def get_reporte_archivos(search=''):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Call the summary SP for the table view
        cursor.callproc('sp_reporte_archivos_resumen', [search])
        
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
            
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching reporte archivos: {e}")
        return []

def get_archivos_detalle(search='', identificador='', tipo_origen=''):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Call the detailed SP for downloads
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
    search = request.args.get('search', '')
    data = get_reporte_archivos(search)
    return jsonify(data)

@bp.route('/api/reportes/download-zip', methods=['GET'])
def download_zip():
    search = request.args.get('search', '')
    identificador = request.args.get('identificador', '')
    tipo_origen = request.args.get('tipo', '') # POLIZA or CLIENTE
    
    # Use separate function to get actual files
    results = get_archivos_detalle(search, identificador, tipo_origen)
    
    if not results:
        return jsonify({'error': 'No se encontraron archivos'}), 404
        
    # Create ZIP
    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            files_added = 0
            for row in results:
                file_path = row['ruta_archivo']
                
                # Robust path resolution
                # 1. Try absolute path construction assuming relative to root
                abs_path_root = os.path.join(current_app.root_path, file_path.lstrip('/\\'))
                
                # 2. Try prepending 'static/' if not present (common issue with older uploads)
                abs_path_static = os.path.join(current_app.root_path, 'static', file_path.lstrip('/\\'))
                
                final_path = None
                if os.path.exists(abs_path_root):
                    final_path = abs_path_root
                elif os.path.exists(abs_path_static):
                    final_path = abs_path_static
                
                if final_path:
                    # Unique name in zip: id_filename
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

