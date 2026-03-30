from flask import Blueprint, render_template, request, jsonify, send_file, current_app, session
from models.db import get_connection
from utils.rbac import Roles
import os
import zipfile
import io
import traceback
import mysql.connector.errors as mysql_errors

bp = Blueprint('reporte_archivos_poliza', __name__)

INITIAL_LIMIT = 1000000
SEARCH_LIMIT  = 1000000

def get_reporte_archivos(search='', limit=INITIAL_LIMIT):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Fix para los parámetros opcionales del SP: si el SP no acepta el segundo parámetro, llamar solo con search
        effective_search = search if (search and search.strip()) else '%'
        try:
            cursor.callproc('sp_reporte_archivos_resumen', [effective_search, limit + 1])
        except mysql_errors.ProgrammingError as e:
            if 'Incorrect number of arguments' in str(e) and 'expected 1' in str(e):
                cursor.callproc('sp_reporte_archivos_resumen', [effective_search])
            else:
                raise
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        cursor.close()
        conn.close()

        has_more = len(results) > limit
        if has_more:
            results = results[:limit]

        for r in results:
            if r.get('ultima_fecha') and hasattr(r['ultima_fecha'], 'strftime'):
                r['ultima_fecha'] = r['ultima_fecha'].strftime('%Y-%m-%dT%H:%M:%SZ')
        return results, has_more
    except Exception as e:
        print(f"Error fetching reporte archivos: {e}")
        traceback.print_exc()
        return [], False

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
        traceback.print_exc()
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
    search = request.args.get('search', '').strip()
    # Sin búsqueda → carga inicial limitada; con búsqueda → límite amplio
    limit = SEARCH_LIMIT if search else INITIAL_LIMIT
    data, has_more = get_reporte_archivos(search, limit)
    return jsonify({'data': data, 'has_more': has_more, 'limit': limit})

@bp.route('/api/reportes/download-zip', methods=['GET'])
def download_zip():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    if session.get('role_name') == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    search      = request.args.get('search', '')
    identificador = request.args.get('identificador', '')
    tipo_origen = request.args.get('tipo', '')
    poliza_num  = request.args.get('poliza', '')

    results = []
    if tipo_origen == 'CUOTA' and identificador:
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            if poliza_num:
                cursor.execute(
                    """SELECT pa.idArchivo, pa.ruta_archivo, pa.nombre_original
                       FROM poliza_archivos pa
                       INNER JOIN polizas p ON pa.poliza_id = p.idPoliza
                       WHERE pa.origen = 'CUOTA'
                         AND p.poliza = %s
                         AND pa.nombre_original LIKE %s
                       ORDER BY pa.creado_en DESC""",
                    (poliza_num, f'[CUOTA {identificador}] %',)
                )
            else:
                cursor.execute(
                    """SELECT idArchivo, ruta_archivo, nombre_original
                       FROM poliza_archivos
                       WHERE origen = 'CUOTA'
                         AND nombre_original LIKE %s
                       ORDER BY creado_en DESC""",
                    (f'[CUOTA {identificador}] %',)
                )
            results = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            results = []
    else:
        results = get_archivos_detalle(search, identificador, tipo_origen)

    if not results:
        return jsonify({'error': 'No se encontraron archivos'}), 404

    memory_file = io.BytesIO()
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            files_added = 0
            upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                                   os.path.join(current_app.root_path, 'uploads'))

            for row in results:
                file_path = row.get('ruta_archivo')
                if not file_path:
                    continue

                # Candidatos de ruta en orden de prioridad:
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
        traceback.print_exc()
        return jsonify({'error': 'Error generando archivo ZIP'}), 500


@bp.route('/api/reportes/archivos-detalle-completo', methods=['GET'])
def api_archivos_detalle_completo():
    """Devuelve los archivos del SP de detalle + los archivos extra (proforma/archivo_extra) de poliza_archivos."""
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    identificador = request.args.get('identificador', '').strip()
    tipo_origen   = request.args.get('tipo', '').strip()       # POLIZA | CUOTA
    poliza_id     = request.args.get('poliza_id', '').strip()

    # 1. Archivos del SP (CARGA_MASIVA y otros)
    archivos_sp = get_archivos_detalle('', identificador, tipo_origen)
    for a in archivos_sp:
        a['es_extra'] = False
        if a.get('creado_en') and hasattr(a['creado_en'], 'strftime'):
            a['creado_en'] = a['creado_en'].strftime('%d/%m/%Y %H:%M')

    # 2. Archivos extra de poliza_archivos (PROFORMA / ARCHIVO_EXTRA) — solo para POLIZA
    archivos_extra = []
    if tipo_origen == 'POLIZA' and poliza_id:
        try:
            conn = get_connection()
            cur  = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT idArchivo, ruta_archivo, nombre_original, origen, creado_en
                   FROM poliza_archivos
                   WHERE poliza_id = %s
                   ORDER BY creado_en DESC""",
                (int(poliza_id),)
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            for a in rows:
                if a.get('creado_en') and hasattr(a['creado_en'], 'strftime'):
                    a['creado_en'] = a['creado_en'].strftime('%d/%m/%Y %H:%M')
                a['es_extra'] = True
                a['identificador'] = identificador
                archivos_extra.append(a)
        except Exception as e:
            print(f"[archivos_detalle_completo] error extras: {e}")

    return jsonify({'ok': True, 'archivos': archivos_sp, 'archivos_extra': archivos_extra})


@bp.route('/api/reportes/search-contratantes', methods=['GET'])
def search_contratantes():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    if session.get('role_name') == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    busqueda = (request.args.get('busqueda') or '').strip()
    # Si no hay busqueda, devolver un listado por defecto (top 50 clientes activos)
    if not busqueda:
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT idCliente, razon_social, numero_documento FROM clientes WHERE activo = 1 ORDER BY razon_social ASC LIMIT 50")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return jsonify(rows)
        except Exception as e:
            print(f"Error buscando contratantes (defecto): {e}")
            traceback.print_exc()
            return jsonify([]), 500

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Buscar por numero_documento exacto y luego por razon_social parcial; devolver hasta 20 coincidencias
        cursor.execute("SELECT idCliente, razon_social, numero_documento FROM clientes WHERE numero_documento = %s LIMIT 1", (busqueda,))
        exact = cursor.fetchall()
        if exact:
            cursor.close()
            conn.close()
            return jsonify(exact)

        cursor.execute("SELECT idCliente, razon_social, numero_documento FROM clientes WHERE razon_social LIKE %s LIMIT 20", ('%'+busqueda+'%',))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        print(f"Error buscando contratantes: {e}")
        traceback.print_exc()
        return jsonify([]), 500


@bp.route('/api/reportes/download-zip-contratante', methods=['GET'])
def download_zip_contratante():
    """Descarga ZIP por cliente. Acepta cliente_id (preferido) o busqueda (legacy)."""
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    if session.get('role_name') == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    cliente_id = request.args.get('cliente_id')
    busqueda = (request.args.get('busqueda') or '').strip()

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if not cliente_id:
            if not busqueda:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Parametro cliente_id o busqueda requerido'}), 400
            # Intentar encontrar cliente por numero_documento exacto
            cursor.execute("SELECT idCliente, razon_social, numero_documento FROM clientes WHERE numero_documento = %s LIMIT 1", (busqueda,))
            cliente = cursor.fetchone()
            if not cliente:
                cursor.execute("SELECT idCliente, razon_social, numero_documento FROM clientes WHERE razon_social LIKE %s LIMIT 1", ('%'+busqueda+'%',))
                cliente = cursor.fetchone()
            if not cliente:
                cursor.close()
                conn.close()
                return jsonify({'error': 'No se encontró un contratante con la búsqueda dada'}), 404
            cliente_id = cliente['idCliente']

        # Recolectar todos los archivos (pólizas + cuotas) de poliza_archivos relacionados al cliente
        # Los archivos de cuotas se almacenan en poliza_archivos con origen='CUOTA'
        sql = '''
              SELECT pa.idArchivo,
                     CAST(pa.ruta_archivo AS CHAR CHARACTER SET utf8mb4) AS ruta_archivo,
                     CAST(pa.nombre_original AS CHAR CHARACTER SET utf8mb4) AS nombre_original
              FROM poliza_archivos pa
                       INNER JOIN polizas p ON pa.poliza_id = p.idPoliza
              WHERE p.cliente_id = %s
              '''
        cursor.execute(sql, (cliente_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return jsonify({'error': 'No se encontraron archivos para el contratante seleccionado'}), 404

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            files_added = 0
            upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads'))
            for row in rows:
                file_path = row.get('ruta_archivo')
                if not file_path:
                    continue
                candidates = [
                    os.path.join(upload_folder, file_path.lstrip('/\\')),
                    os.path.join(current_app.root_path, file_path.lstrip('/\\')),
                    os.path.join(current_app.root_path, 'static', file_path.lstrip('/\\')),
                ]
                final_path = next((p for p in candidates if os.path.exists(p)), None)
                if final_path:
                    arcname = f"{row.get('idArchivo')}_{row.get('nombre_original') or os.path.basename(file_path)}"
                    zf.write(final_path, arcname)
                    files_added += 1

            if files_added == 0:
                return jsonify({'error': 'Los archivos físicos no existen en el servidor'}), 404

        memory_file.seek(0)
        zip_name = f"contratante_{cliente_id}_archivos.zip"
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=zip_name)

    except Exception as e:
        print(f"Error descargando zip por contratante: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Error interno generando ZIP'}), 500

