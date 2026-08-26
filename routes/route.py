from flask import Blueprint, redirect, url_for, session, render_template, request, current_app, send_from_directory, jsonify, send_file, abort, Response
from werkzeug.utils import secure_filename
import os
import re
import pytesseract
import hashlib
import json
import shutil
from utils.rbac import can_access_maestros, can_view_maestros, can_delete, can_edit, can_create, can_create_poliza, can_restore, can_hard_delete, Roles, get_role_scope, require_permission
from controllers.dashboard import get_dashboard_data, get_rows as get_dashboard_rows, get_dashboard_cards, get_distribution_by_group, get_pending_renewals_list
from datetime import datetime, timedelta
from controllers.reportes.vencimientos_renovaciones import bp as vencimientos_bp
from controllers.reportes.reporte_produccion import (
    get_reporte_produccion_rows,
    export_reporte_produccion,
    get_reporte_produccion_filters,
)
from controllers.addPoliza import lookup_commission_pct
from controllers.cuotas.VariosCuotasGenerales import extract_cronograma_cuotas_from_text as extract_cronograma_cuotas_general
from controllers.cuotas.VariosCuotasPositiva import extract_cronograma_cuotas_positiva
from controllers.cuotas.VariosCuotasPacifico import extract_cronograma_cuotas_pacifico
from models.db import get_connection

bp = Blueprint('main', __name__)


def _get_current_user_ejecutivo():
    username = (session.get('user') or '').strip()
    if not username:
        return ''

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.nombre
            FROM usuarios u
            LEFT JOIN ejecutivos e ON e.idEjecutivo = u.id_ejecutivo
            WHERE u.username = %s
            LIMIT 1
        """, (username,))
        row = cur.fetchone()
        return (row[0] or '').strip() if row and row[0] else ''
    except Exception:
        return ''
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass

# #region debug-point A:cuotas-route-helper
def _dbg_cuotas_route_slow(hypothesis_id: str, location: str, msg: str, data=None, run_id: str = 'pre-fix'):
    try:
        import urllib.request
        debug_url = 'http://127.0.0.1:7777/event'
        debug_session = 'cuotas-slow-load'
        try:
            with open('.dbg/cuotas-slow-load.env', 'r', encoding='utf-8') as f:
                content = f.read()
            for line in content.splitlines():
                if line.startswith('DEBUG_SERVER_URL='):
                    debug_url = line.split('=', 1)[1].strip() or debug_url
                elif line.startswith('DEBUG_SESSION_ID='):
                    debug_session = line.split('=', 1)[1].strip() or debug_session
        except Exception:
            pass
        payload = {
            "sessionId": debug_session,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "msg": f"[DEBUG] {msg}",
            "data": data or {},
        }
        urllib.request.urlopen(
            urllib.request.Request(
                debug_url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=1,
        ).read()
    except Exception:
        pass
# #endregion

@bp.route('/img/<path:filename>')
def serve_img(filename):
    img_dir = os.path.join(current_app.root_path, 'img')
    return send_from_directory(img_dir, filename)

@bp.route('/favicon.svg')
def favicon_svg():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="12" fill="#1F59A3"/>'
        '<text x="32" y="44" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="40" font-weight="700" fill="#ffffff">A</text>'
        '</svg>'
    )
    return Response(svg, mimetype='image/svg+xml')
@bp.route('/cuotas/extract', methods=['POST'])
def extract_cuota():
    if 'file' not in request.files:
        return {'ok': False, 'error': 'No file part'}, 400
    file = request.files['file']
    if file.filename == '':
        return {'ok': False, 'error': 'No selected file'}, 400
    
    if file:
        try:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            from controllers.cuotas.cuotas import extract_cuota_from_pdf
            data = extract_cuota_from_pdf(filepath)

            try:
                poliza = (request.form.get('poliza') or request.form.get('numero_poliza') or '').strip()
                poliza_id_raw = request.form.get('poliza_id') or request.form.get('idPrima') or ''
                poliza_id = None
                if poliza_id_raw:
                    try:
                        poliza_id = int(str(poliza_id_raw).strip())
                    except Exception:
                        poliza_id = None

                cliente_doc = ''
                if poliza_id or poliza:
                    cnx = get_connection()
                    cur = cnx.cursor(dictionary=True)
                    try:
                        if poliza_id:
                            cur.execute(
                                """
                                SELECT
                                    TRIM(
                                        COALESCE(
                                            CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR),
                                            CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR),
                                            c.numero_documento
                                        )
                                    ) AS numero_documento
                                FROM polizas p
                                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                                WHERE p.idPoliza = %s
                                LIMIT 1
                                """,
                                (poliza_id,),
                            )
                        else:
                            cur.execute(
                                """
                                SELECT
                                    TRIM(
                                        COALESCE(
                                            CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR),
                                            CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR),
                                            c.numero_documento
                                        )
                                    ) AS numero_documento
                                FROM polizas p
                                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                                WHERE (
                                        CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                                     OR CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR)            COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                                     OR p.poliza COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                                )
                                  AND p.activo = 1 AND (p.anulado = 0 OR p.anulado IS NULL)
                                ORDER BY p.vig_desde DESC
                                LIMIT 1
                                """,
                                (poliza, poliza, poliza),
                            )
                        row = cur.fetchone() or {}
                        cliente_doc = (row.get('numero_documento') or '').strip()
                    finally:
                        cur.close()
                        cnx.close()

                if isinstance(data, dict):
                    data['cliente_numero_documento'] = cliente_doc
            except Exception:
                pass
            
            # Clean up
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return {'ok': True, 'data': data}
        except Exception as e:
            return {'ok': False, 'error': str(e)}, 500
            
    return {'ok': False, 'error': 'Unknown error'}, 500

@bp.route('/cuotas/info', methods=['GET'])
def get_cuota_info():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    
    poliza = request.args.get('poliza')
    poliza_id = request.args.get('poliza_id') or request.args.get('idPrima')
    aviso = request.args.get('aviso')
    if not poliza:
        return {'ok': False, 'error': 'Missing poliza'}, 400
        
    from controllers.cuotas.cuotas import get_cuotas_data
    data = get_cuotas_data(None, poliza, poliza_id, aviso)
    
    # We are interested in the 'rows' part, specifically the first one if it exists.
    # This effectively allows pre-filling the modal with the "current" or "next" premium info found.
    row = {}
    if data.get('rows') and len(data['rows']) > 0:
        row = data['rows'][0]
        
    return {'ok': True, 'data': row}

def _normalize_importe_text(raw: str | None) -> str:
    txt0 = (raw or '').strip()
    if not txt0:
        return ''
    txt = txt0.replace('−', '-').replace('–', '-').replace('—', '-')
    is_paren_neg = False
    m_paren = re.match(r'^\((.*)\)$', txt)
    if m_paren:
        is_paren_neg = True
        txt = (m_paren.group(1) or '').strip()
    txt = re.sub(r'[^\d,.\-]', '', txt)
    if not txt:
        return ''
    is_neg = is_paren_neg or txt.startswith('-')
    txt = txt.replace('-', '')
    try:
        if '.' in txt and ',' in txt:
            if txt.rfind('.') > txt.rfind(','):
                txt = txt.replace(',', '')
            else:
                txt = txt.replace('.', '').replace(',', '.')
        elif txt.count('.') > 1 and ',' not in txt:
            parts = txt.split('.')
            txt = ''.join(parts[:-1]) + '.' + parts[-1]
        elif txt.count(',') > 1 and '.' not in txt:
            parts = txt.split(',')
            txt = ''.join(parts[:-1]) + '.' + parts[-1]
        elif ',' in txt:
            txt = txt.replace('.', '').replace(',', '.')
        num = float(txt)
        if is_neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return txt0

def _extract_cronograma_cuotas(text: str | None, moneda_default: str | None = None) -> list[dict]:
    if not text:
        return []

    normalized = (text or '').replace('\u00A0', ' ').replace('：', ':')
    normalized = re.sub(r'[ \t]+', ' ', normalized)

    section_match = re.search(
        r'Cronograma\s+de\s+Pago([\s\S]{0,2500})',
        normalized,
        re.IGNORECASE
    )
    section = section_match.group(1) if section_match else normalized
    lines = [re.sub(r'\s+', ' ', ln).strip() for ln in section.splitlines() if ln.strip()]

    cuotas = []
    seen = set()
    row_pattern = re.compile(
        r'(?P<orden>\d{1,2}/\d{1,2})\s+'
        r'(?P<fecha>\d{2}/\d{2}/\d{4})\s+'
        r'(?P<cupon>\d{6,20})\s+'
        r'(?P<importe>\(?\s*[-−–—]?\s*\d[\d\.,]*\)?)',
        re.IGNORECASE,
    )

    for ln in lines:
        if re.search(r'Monto total a pagar|Tasa de costo efectivo|Intereses de Financiaci|Sub\s*-\s*Total|^\s*Total\s*:?', ln, re.IGNORECASE):
            continue
        m = row_pattern.search(ln)
        if not m:
            continue

        cupon = (m.group('cupon') or '').strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)

        orden = (m.group('orden') or '').strip()
        numero_cuota = None
        try:
            numero_cuota = int(orden.split('/')[0])
        except Exception:
            numero_cuota = None

        cuotas.append({
            'numero_cuota': numero_cuota,
            'cupon': cupon,
            'fecha_vencimiento': (m.group('fecha') or '').strip(),
            'importe': _normalize_importe_text(m.group('importe')),
            'moneda': moneda_default or '',
            'factura': '',
            'fecha_pago': '',
        })

    return cuotas

@bp.route('/api/cuotas/list', methods=['GET'])
def api_cuotas_list():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    poliza = request.args.get('poliza', '').strip()
    aviso = request.args.get('aviso') or request.args.get('cupon')
    poliza_id = request.args.get('poliza_id') or request.args.get('idPrima')
    
    if not poliza:
        return {'ok': False, 'error': 'Missing poliza'}, 400
    from controllers.cuotas.cuotas import get_cuotas_data
    
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    
    data = get_cuotas_data(None, poliza, poliza_id, aviso, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    rows = data.get('rows') or []
    return jsonify({'ok': True, 'rows': rows})


@bp.route('/cuotas/save', methods=['POST'])
def save_cuota_route():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    
    data = request.json
    if not data:
        return {'ok': False, 'error': 'No data'}, 400
        
    # Add user context
    try:
        user_session = session.get('user')
        if isinstance(user_session, dict):
            usuario_username = user_session.get('username') or user_session.get('user') or user_session.get('name') or ''
        else:
            usuario_username = user_session or ''
        usuario_username = str(usuario_username).strip()
        usuario = usuario_username
        if usuario_username:
            try:
                cnx_u = get_connection()
                cur_u = cnx_u.cursor()
                cur_u.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
                    (usuario_username,),
                )
                urow = cur_u.fetchone()
                if urow and urow[0]:
                    usuario = urow[0]
                cur_u.close()
                cnx_u.close()
            except Exception:
                usuario = usuario_username
        data['usuario'] = usuario
    except Exception:
        data['usuario'] = session.get('user')
    
    from controllers.cuotas.cuotas import save_cuota
    result = save_cuota(data)
    success = result[0]
    msg = result[1] if len(result) > 1 else ''
    new_id = result[2] if len(result) > 2 else None

    if success:
        return {'ok': True, 'idCuota': new_id}
    return {'ok': False, 'error': msg or 'Error al guardar cuota'}, 400


@bp.route('/cuotas/update-cupon', methods=['POST'])
def update_cuota_cupon_route():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    data = request.get_json(force=True) or {}
    try:
        user_session = session.get('user')
        if isinstance(user_session, dict):
            usuario_username = user_session.get('username') or user_session.get('user') or user_session.get('name') or ''
        else:
            usuario_username = user_session or ''
        usuario_username = str(usuario_username).strip()
        usuario = usuario_username
        if usuario_username:
            try:
                cnx_u = get_connection()
                cur_u = cnx_u.cursor()
                cur_u.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
                    (usuario_username,),
                )
                urow = cur_u.fetchone()
                if urow and urow[0]:
                    usuario = urow[0]
                cur_u.close()
                cnx_u.close()
            except Exception:
                usuario = usuario_username
        data['usuario'] = usuario
    except Exception:
        data['usuario'] = session.get('user')
    from controllers.cuotas.cuotas import update_cuota_cupon
    success, msg = update_cuota_cupon(data)
    if not success:
        return {'ok': False, 'error': msg}, 400
    return {'ok': True}

@bp.route('/cuotas/delete', methods=['POST'])
def delete_cuota_route():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    data = request.json or {}
    cuota_id = data.get('idCuota')
    motivo = (data.get('motivo') or '').strip()
    if not motivo:
        return {'ok': False, 'error': 'El motivo de anulación es obligatorio'}, 400
    if len(motivo) > 200:
        return {'ok': False, 'error': 'El motivo supera 200 caracteres'}, 400

    user_session = session.get('user')
    if isinstance(user_session, dict):
        usuario = user_session.get('username') or user_session.get('user') or user_session.get('name') or ''
    else:
        usuario = user_session or ''
    usuario = str(usuario).strip()
    if usuario:
        try:
            cnx_u = get_connection()
            cur_u = cnx_u.cursor()
            cur_u.execute(
                "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
                (usuario,),
            )
            urow = cur_u.fetchone()
            if urow and urow[0]:
                usuario = urow[0]
            cur_u.close()
            cnx_u.close()
        except Exception:
            pass

    from controllers.cuotas.cuotas import delete_cuota
    success, msg, recibo = delete_cuota(cuota_id, motivo, usuario)

    if success:
        from utils.notify import notify_deletion
        notify_deletion(usuario, 'CUOTA', recibo, evento='anulacion', motivo=motivo)
        return {'ok': True}
    return {'ok': False, 'error': msg}, 400

@bp.route('/api/cuotas/upload-archivo', methods=['POST'])
def upload_cuota_archivo():
    """Guarda un archivo de cuota en uploads/cuotas/ y lo registra amarrado a la cuota."""
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    cuota_id      = request.form.get('cuota_id')
    poliza_id     = request.form.get('poliza_id')
    numero_poliza = request.form.get('numero_poliza', '')
    cupon         = request.form.get('cupon', '')

    print(f"[upload_cuota_archivo] cuota_id={cuota_id} poliza_id={poliza_id} cupon={cupon}")

    if not cuota_id:
        return jsonify({'ok': False, 'error': 'Falta cuota_id'}), 400

    if 'archivo' not in request.files:
        return jsonify({'ok': False, 'error': 'No se envió archivo (key=archivo)'}), 400

    file = request.files['archivo']
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Archivo vacío'}), 400

    try:
        import time
        original_filename = file.filename
        safe_name = secure_filename(original_filename)
        ts = int(time.time())
        disk_filename = f"{ts}_cuota{cuota_id}_{safe_name}"

        upload_folder = os.path.join(current_app.root_path, 'uploads', 'cuotas')
        os.makedirs(upload_folder, exist_ok=True)

        save_path = os.path.join(upload_folder, disk_filename)
        file.save(save_path)
        print(f"[upload_cuota_archivo] guardado en {save_path}, existe={os.path.exists(save_path)}")

        ruta_relativa = f"cuotas/{disk_filename}"
        usuario_username = session.get('user', '')
        usuario = usuario_username
        pid = int(poliza_id) if poliza_id and str(poliza_id).strip() not in ('', 'None') else None

        # Obtener datos de la póliza para completar metadatos; en financiamiento grupal poliza_id puede ser NULL.
        p_ramo = p_producto = p_cia = ''
        p_poliza = numero_poliza
        fg_id = None
        cnx = get_connection()
        cur = cnx.cursor()
        if pid is None:
            try:
                cur.execute(
                    """
                    SELECT
                        poliza_id,
                        financiamiento_grupal_id,
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                            poliza
                        ) AS poliza_plain
                    FROM cuotas
                    WHERE idCuota = %s AND activo = 1
                    """,
                    (int(cuota_id),)
                )
                prow = cur.fetchone()
                if prow:
                    if prow[0] not in (None, 0, ''):
                        pid = int(prow[0])
                    if len(prow) > 1 and prow[1] not in (None, 0, ''):
                        fg_id = int(prow[1])
                    if len(prow) > 2 and prow[2]:
                        p_poliza = prow[2]
            except Exception:
                pid = None
                fg_id = None
        if usuario_username:
            try:
                cur.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
                    (usuario_username,),
                )
                urow = cur.fetchone()
                if urow and urow[0]:
                    usuario = urow[0]
            except Exception:
                usuario = usuario_username
        if pid is not None:
            cur.execute("SELECT ramo, ramos_producto, cia, poliza FROM polizas WHERE idPoliza = %s", (pid,))
            prow = cur.fetchone()
            if prow:
                p_ramo     = prow[0] or ''
                p_producto = prow[1] or ''
                p_cia      = prow[2] or ''
                p_poliza   = prow[3] or numero_poliza
        elif fg_id:
            if not p_poliza:
                p_poliza = f"FG-{fg_id}"
        else:
            cur.close()
            cnx.close()
            return jsonify({'ok': False, 'error': 'La cuota no está asociada a una póliza/prima ni a un financiamiento grupal.'}), 400

        nombre_doc = f"[CUOTA {cupon}] {original_filename}" if cupon else original_filename

        numero_poliza_plain = (numero_poliza or '').strip() or (p_poliza or '')
        cur.execute(
            """INSERT INTO cuota_archivos
               (cuota_id, poliza_id, numero_poliza, cupon, ruta_archivo, nombre_original, usuario)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (int(cuota_id), pid, numero_poliza_plain, (cupon or '').strip() or None, ruta_relativa, nombre_doc, usuario)
        )
        new_archivo_id = cur.lastrowid
        cnx.commit()
        cur.close()
        cnx.close()
        print(f"[upload_cuota_archivo] registro en cuota_archivos idArchivo={new_archivo_id} cuota_id={cuota_id} ruta={ruta_relativa}")

        return jsonify({'ok': True, 'ruta': ruta_relativa, 'idArchivo': new_archivo_id}), 200

    except Exception as e:
        print(f"[upload_cuota_archivo] ERROR: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/cuotas/revert', methods=['POST'])
def revert_cuota_route():
    """Revierte una cuota: limpia sus datos y elimina solo sus archivos asociados."""
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    data = request.get_json(force=True) or {}
    cuota_id = data.get('idCuota') or data.get('id_cuota') or data.get('id')
    if not cuota_id:
        return {'ok': False, 'error': 'Falta idCuota'}, 400
    from controllers.cuotas.cuotas import revert_cuota
    success, msg = revert_cuota(cuota_id)
    if success:
        return {'ok': True}
    return {'ok': False, 'error': msg}, 400

@bp.route('/api/cuotas/archivos/<int:cuota_id>', methods=['GET'])
def get_cuota_archivos(cuota_id):
    """Lista los archivos de una cuota sin mezclar documentos de otras cuotas."""
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        resolved_poliza_id = None
        resolved_cuota_id = None
        resolved_cupon = ''
        try:
            cur.execute(
                """
                SELECT
                    poliza_id,
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR),
                        cupon
                    ) AS cupon_plain
                FROM cuotas
                WHERE idCuota = %s AND activo = 1
                """,
                (int(cuota_id),),
            )
            qrow = cur.fetchone() or {}
            resolved_poliza_id = qrow.get('poliza_id') or None
            if qrow:
                resolved_cuota_id = int(cuota_id)
                resolved_cupon = (qrow.get('cupon_plain') or '').strip()
        except Exception:
            resolved_poliza_id = None
        if resolved_poliza_id is None:
            resolved_poliza_id = int(cuota_id)

        cur.execute(
            """SELECT idArchivo, ruta_archivo, nombre_original, 'CUOTA' AS origen, creado_en
               FROM cuota_archivos
               WHERE cuota_id = %s
               ORDER BY creado_en DESC""",
            (int(resolved_cuota_id or cuota_id),)
        )
        rows = cur.fetchall() or []

        if not rows:
            if resolved_poliza_id is not None and resolved_cupon:
                cur.execute(
                    """
                    SELECT idArchivo, ruta_archivo, nombre_original, origen, creado_en
                    FROM poliza_archivos
                    WHERE poliza_id = %s
                      AND origen = 'CUOTA'
                      AND (
                          nombre_original LIKE %s
                          OR nombre_original LIKE %s
                      )
                    ORDER BY creado_en DESC
                    """,
                    (int(resolved_poliza_id), f'[CUOTA {resolved_cupon}] %', f'%{resolved_cupon}%')
                )
                rows = cur.fetchall() or []

        if not rows and resolved_poliza_id is not None:
            cur.execute(
                "SELECT COUNT(*) AS total FROM cuotas WHERE poliza_id = %s AND activo = 1",
                (int(resolved_poliza_id),)
            )
            qty_row = cur.fetchone() or {}
            total_cuotas = int(qty_row.get('total') or 0)
            if total_cuotas <= 1:
                cur.execute(
                    """SELECT idArchivo, ruta_archivo, nombre_original, origen, creado_en
                       FROM poliza_archivos
                       WHERE poliza_id = %s AND origen = 'CUOTA'
                       ORDER BY creado_en DESC""",
                    (int(resolved_poliza_id),)
                )
                rows = cur.fetchall() or []
            if not rows:
                cur.execute(
                    """SELECT idArchivo, ruta_archivo, nombre_original, origen, creado_en
                       FROM poliza_archivos
                       WHERE poliza_id = %s AND origen = 'CONVENIO_PAGO'
                       ORDER BY creado_en DESC""",
                    (int(resolved_poliza_id),)
                )
                rows = cur.fetchall() or []
        cur.close()
        cnx.close()
        for r in rows:
            if r.get('creado_en'):
                try:
                    from zoneinfo import ZoneInfo
                    src_tz = ZoneInfo('America/Mexico_City')
                    lima_tz = ZoneInfo('America/Lima')
                    dt = r['creado_en']
                    if getattr(dt, 'tzinfo', None) is None:
                        dt = dt.replace(tzinfo=src_tz)
                    r['creado_en'] = dt.astimezone(lima_tz).strftime('%d/%m/%Y %H:%M')
                except Exception:
                    r['creado_en'] = r['creado_en'].strftime('%d/%m/%Y %H:%M')
        return jsonify({'ok': True, 'archivos': rows})
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500


@bp.route('/api/cuotas/archivos/delete/<int:archivo_id>', methods=['DELETE'])
def delete_cuota_archivo(archivo_id):
    """Elimina un archivo de cuota del disco y de poliza_archivos."""
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT ruta_archivo, 'poliza_archivos' AS _tbl FROM poliza_archivos WHERE idArchivo = %s AND origen = 'CUOTA'", (archivo_id,))
        row = cur.fetchone()
        if not row:
            cur.execute("SELECT ruta_archivo, 'cuota_archivos' AS _tbl FROM cuota_archivos WHERE idArchivo = %s", (archivo_id,))
            row = cur.fetchone()
        if not row:
            cur.close()
            cnx.close()
            return {'ok': False, 'error': 'Archivo no encontrado'}, 404

        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads'))
        abs_path = os.path.join(upload_folder, row['ruta_archivo'].lstrip('/\\'))
        if os.path.exists(abs_path):
            os.remove(abs_path)

        if row.get('_tbl') == 'cuota_archivos':
            cur.execute("DELETE FROM cuota_archivos WHERE idArchivo = %s", (archivo_id,))
        else:
            cur.execute("DELETE FROM poliza_archivos WHERE idArchivo = %s", (archivo_id,))
        cnx.commit()
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500



@bp.route('/api/polizas/upload-archivo', methods=['POST'])
def upload_poliza_archivo():
    """Sube un archivo (proforma o extra) asociado a una póliza y registra en poliza_archivos."""
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    poliza_id = request.form.get('poliza_id')
    numero_poliza = request.form.get('numero_poliza', '')
    tipo_documento = request.form.get('tipo_documento', 'ARCHIVO_EXTRA')  # PROFORMA | ARCHIVO_EXTRA | CUOTA | CONVENIO_PAGO
    nombre_documento = request.form.get('nombre_documento', '').strip()
    cupon = (request.form.get('cupon') or request.form.get('cupón') or '').strip()

    if not poliza_id:
        return jsonify({'ok': False, 'error': 'Falta poliza_id'}), 400

    if 'archivo' not in request.files:
        return jsonify({'ok': False, 'error': 'No se envió archivo (key=archivo)'}), 400

    file = request.files['archivo']
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Archivo vacío'}), 400

    try:
        import time
        original_filename = file.filename
        safe_name = secure_filename(original_filename)
        ts = int(time.time())
        disk_filename = f"{ts}_poliza{poliza_id}_{safe_name}"

        upload_folder = os.path.join(current_app.root_path, 'uploads', 'polizas')
        os.makedirs(upload_folder, exist_ok=True)

        save_path = os.path.join(upload_folder, disk_filename)
        file.save(save_path)

        ruta_relativa = f"polizas/{disk_filename}"
        usuario_username = session.get('user', '')
        usuario = usuario_username
        nombre_final = nombre_documento or original_filename
        if tipo_documento == 'CUOTA' and cupon and nombre_final and not nombre_final.startswith('[CUOTA'):
            nombre_final = f"[CUOTA {cupon}] {nombre_final}"
        if tipo_documento == 'CONVENIO_PAGO' and nombre_final and not nombre_final.startswith('[CONVENIO]'):
            nombre_final = f"[CONVENIO] {nombre_final}"

        # Obtener datos de la póliza para guardar ramo, producto, compania
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        if usuario_username:
            try:
                cur.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s LIMIT 1",
                    (usuario_username,),
                )
                urow = cur.fetchone() or {}
                if urow.get('nombre'):
                    usuario = urow['nombre']
            except Exception:
                usuario = usuario_username
        cur.execute("SELECT ramo, ramos_producto, cia, poliza FROM polizas WHERE idPoliza = %s", (int(poliza_id),))
        prow = cur.fetchone() or {}

        cur.execute(
            """INSERT INTO poliza_archivos
               (poliza_id, numero_poliza, ruta_archivo, nombre_original, origen, ramo, producto, usuario, compania)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                int(poliza_id),
                numero_poliza or prow.get('poliza', ''),
                ruta_relativa,
                nombre_final,
                tipo_documento,
                prow.get('ramo', ''),
                prow.get('ramos_producto', ''),
                usuario,
                prow.get('cia', '')
            )
        )
        cnx.commit()
        new_id = cur.lastrowid
        cur.close()
        cnx.close()

        return jsonify({'ok': True, 'ruta': ruta_relativa, 'idArchivo': new_id, 'nombre': nombre_final}), 200

    except Exception as e:
        print(f"[upload_poliza_archivo] ERROR: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/polizas/archivos/<int:poliza_id>', methods=['GET'])
def get_poliza_archivos(poliza_id):
    """Lista los archivos guardados para una póliza."""
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            """SELECT idArchivo, ruta_archivo, nombre_original, origen, creado_en
               FROM poliza_archivos
               WHERE poliza_id = %s
               ORDER BY creado_en DESC""",
            (poliza_id,)
        )
        rows = cur.fetchall()
        cur.close()
        cnx.close()
        for r in rows:
            if r.get('creado_en'):
                try:
                    from zoneinfo import ZoneInfo
                    src_tz = ZoneInfo('America/Mexico_City')
                    lima_tz = ZoneInfo('America/Lima')
                    dt = r['creado_en']
                    if getattr(dt, 'tzinfo', None) is None:
                        dt = dt.replace(tzinfo=src_tz)
                    r['creado_en'] = dt.astimezone(lima_tz).strftime('%d/%m/%Y %H:%M')
                except Exception:
                    r['creado_en'] = r['creado_en'].strftime('%d/%m/%Y %H:%M')
        return jsonify({'ok': True, 'archivos': rows})
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500


@bp.route('/api/polizas/archivos/delete/<int:archivo_id>', methods=['DELETE'])
def delete_poliza_archivo(archivo_id):
    """Elimina un archivo de póliza del disco y de la tabla."""
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT ruta_archivo FROM poliza_archivos WHERE idArchivo = %s", (archivo_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            cnx.close()
            return {'ok': False, 'error': 'Archivo no encontrado'}, 404

        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads'))
        ruta = (row.get('ruta_archivo') or '').replace('\\', '/')
        while ruta.startswith('uploads/'):
            ruta = ruta[len('uploads/'):]
        abs_path = os.path.join(upload_folder, ruta.lstrip('/\\'))
        if os.path.exists(abs_path):
            os.remove(abs_path)
        else:
            name = secure_filename(os.path.basename(ruta))
            for known_sub in ['polizas', 'temp', 'cuotas', 'clientes', 'siniestros', 'soat']:
                candidate = os.path.join(upload_folder, known_sub, name)
                if os.path.isfile(candidate):
                    os.remove(candidate)
                    break

        cur.execute("DELETE FROM poliza_archivos WHERE idArchivo = %s", (archivo_id,))
        cnx.commit()
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500

@bp.route('/api/reportes/siniestros', methods=['GET'])
def api_reporte_siniestros_list():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401

    try:
        from controllers.reportes.reporte_siniestros import get_reporte_siniestros
        # Pasar filtros simples desde query params
        filters = {
            'fec_desde': request.args.get('fec_desde') or None,
            'fec_hasta': request.args.get('fec_hasta') or None,
            'texto': request.args.get('texto') or None,
            'poliza': request.args.get('poliza') or None,
        }
        data = get_reporte_siniestros(filters)
        if not data.get('ok'):
            return {'ok': False, 'error': data.get('error')}, 500
        return {'ok': True, 'rows': data.get('rows')}
    except Exception as e:
        current_app.logger.error(f"Error listando reporte siniestros: {e}")
        return {'ok': False, 'error': str(e)}, 500


@bp.route('/api/reportes/siniestros/export', methods=['GET'])
def api_reporte_siniestros_export():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401

    try:
        from controllers.reportes.reporte_siniestros import export_reporte_siniestros_pdf
        # Aceptar ids como lista separada por comas
        ids = request.args.get('ids')
        siniestro_ids = None
        if ids:
            try:
                siniestro_ids = [int(x) for x in ids.split(',') if x.strip()]
            except Exception:
                siniestro_ids = None

        inline = str(request.args.get('inline', '')).lower() in ('1', 'true', 'yes')

        result = export_reporte_siniestros_pdf(siniestro_ids=siniestro_ids, inline=inline)
        # Si result es (filepath, filename) devolver send_file
        if isinstance(result, tuple):
            filepath, filename = result
            return send_file(filepath, as_attachment=True, download_name=filename)
        # Si result es un Response, retornarlo directamente
        return result
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte siniestros: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500



@bp.route('/api/comisiones/lookup', methods=['GET'])
def lookup_comision_route():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401

    cia = request.args.get('cia')
    ramo = request.args.get('ramo')
    producto = request.args.get('producto')

    # Candidates for lookup: try producto first, then ramo
    candidates = []
    if producto: candidates.append(producto)
    if ramo: candidates.append(ramo)

    if not cia or not candidates:
        return {'ok': True, 'pct': None}

    try:
        cnx = get_connection()
        pct = lookup_commission_pct(cnx, cia, candidates)
        cnx.close()
        return {'ok': True, 'pct': pct}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

@bp.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Solo BROKER consulta métricas reales de gráficas; el resto ve la vista en estado cero.
    if session.get('role_name') == Roles.BROKER:
        rows = get_dashboard_rows()
        chart = get_dashboard_data()
        cards = get_dashboard_cards()
        distribution = get_distribution_by_group()
    else:
        rows = []
        chart = {
            'months': [],
            'totals': [],
            'daily_labels': [],
            'daily_income': [],
        }
        cards = get_dashboard_cards()
        distribution = {'generales': {'vigentes': 0, 'renovar': 0}, 'soat': {'vigentes': 0, 'renovar': 0}, 'personales': {'vigentes': 0, 'renovar': 0}}

    return render_template('view/dashboard.html', rows=rows, chart=chart, cards=cards, distribution=distribution)


@bp.route('/gestion', methods=['GET', 'POST'])
def gestion():
    if 'user' not in session:
        return redirect(url_for('login'))

    fecha_desde = request.args.get('fecha_desde') or request.form.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta') or request.form.get('fecha_hasta')
    orden_fechas = request.args.get('orden_fechas') or request.form.get('orden_fechas') or 'ASC'
    q = (request.args.get('q') or request.form.get('q') or '').strip() or None
    limit_raw = request.args.get('limit') or request.form.get('limit') or '20'
    try:
        limit = int(limit_raw) if limit_raw and limit_raw.lower() != 'todos' else None
    except Exception:
        limit = 20
    try:
        page_num = int(request.args.get('page') or request.form.get('page') or 1)
    except Exception:
        page_num = 1
    page_num = max(1, page_num)

    from controllers.gestion import get_gestion_rows
    data = get_gestion_rows(fecha_desde, fecha_hasta, orden_fechas, limit, page_num, q)
    rows = data.get('rows', [])
    total = data.get('total', 0)

    # Paginación
    if limit:
        pages = max(1, (total + limit - 1) // limit)
    else:
        pages = 1
    if pages > 0:
        page_num = max(1, min(page_num, pages))
    start_index = ((page_num - 1) * (limit or total)) + 1 if total > 0 else 0
    end_index = min(page_num * (limit or total), total) if total > 0 else 0
    pagination = {
        'page': page_num,
        'per_page': limit or total,
        'total': total,
        'pages': pages,
        'has_prev': page_num > 1,
        'has_next': page_num < pages,
        'start_index': start_index,
        'end_index': end_index
    }
    # Lista de páginas para los botones numerados
    page_numbers = list(range(1, pages + 1))

    from datetime import datetime
    today = datetime.utcnow().date().isoformat()

    return render_template(
        'view/gestion.html',
        rows=rows,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        orden_fechas=orden_fechas,
        limit=limit_raw,
        q=q,
        pagination=pagination,
        page_numbers=page_numbers,
        today=today
    )
from controllers.reportes.reporte_archivos_poliza import bp as reporte_archivos_bp
bp.register_blueprint(reporte_archivos_bp)

from controllers.reportes.reporte_anulados import bp as reporte_anulados_bp
bp.register_blueprint(reporte_anulados_bp)

bp.register_blueprint(vencimientos_bp)

from controllers.reportes.reporte_diario_routes import bp as reporte_diario_bp
bp.register_blueprint(reporte_diario_bp)

from controllers.cobranzas_estado_cuenta_cupones_routes import bp as cobranzas_estado_cuenta_cupones_bp
bp.register_blueprint(cobranzas_estado_cuenta_cupones_bp)


@bp.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    rows = get_dashboard_rows()
    chart = get_dashboard_data()
    cards = get_dashboard_cards()
    distribution = get_distribution_by_group()
    return render_template('view/dashboard.html', rows=rows, chart=chart, cards=cards, distribution=distribution)


@bp.route('/dashboard/renovaciones/<bucket>')
def dashboard_renovaciones(bucket):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    rows = get_pending_renewals_list(bucket)
    return jsonify({'ok': True, 'rows': rows})


@bp.route('/reportes/produccion', methods=['GET'])
@require_permission(lambda r: r in [Roles.BROKER, Roles.OPERADOR], response_mode='redirect')
def reporte_produccion_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    filters = get_reporte_produccion_filters()
    return render_template('view/reportes/reporte-produccion.html', page='reporte-produccion', filtros=filters)


def _validate_reporte_produccion_dates(filters: dict) -> str | None:
    vig_desde = filters.get('vig_desde')
    vig_hasta = filters.get('vig_hasta')

    if not vig_desde or not vig_hasta:
        return 'Debe seleccionar Desde y Hasta (Inicio Vigencia).'

    try:
        d_desde = datetime.strptime(vig_desde, '%Y-%m-%d').date()
        d_hasta = datetime.strptime(vig_hasta, '%Y-%m-%d').date()
    except Exception:
        return 'Formato de fecha inválido. Use YYYY-MM-DD.'

    if d_desde > d_hasta:
        return 'La fecha "Desde" no puede ser mayor que la fecha "Hasta".'

    return None


@bp.route('/api/reportes/produccion', methods=['GET'])
@require_permission(lambda r: r in [Roles.BROKER, Roles.OPERADOR], response_mode='json')
def api_reporte_produccion():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    filters = {
        'vig_desde': request.args.get('vig_desde') or None,
        'vig_hasta': request.args.get('vig_hasta') or None,
        'cia': request.args.get('cia') or None,
        'ramo': request.args.get('ramo') or None,
        'sub_agente': request.args.get('sub_agente') or None,
        'ejecutivo': request.args.get('ejecutivo') or None,
        'moneda': request.args.get('moneda') or None,
        'usuario': request.args.get('usuario') or None,
        'f_reg_desde': request.args.get('f_reg_desde') or None,
        'f_reg_hasta': request.args.get('f_reg_hasta') or None,
    }

    error = _validate_reporte_produccion_dates(filters)
    if error:
        return jsonify({'ok': False, 'error': error}), 400

    try:
        rows = get_reporte_produccion_rows(filters)
        return jsonify({'ok': True, 'rows': rows})
    except Exception as e:
        current_app.logger.error(f"Error en reporte produccion: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/reportes/produccion/export', methods=['GET'])
@require_permission(lambda r: r in [Roles.BROKER, Roles.OPERADOR], response_mode='json')
def api_reporte_produccion_export():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    filters = {
        'vig_desde': request.args.get('vig_desde') or None,
        'vig_hasta': request.args.get('vig_hasta') or None,
        'cia': request.args.get('cia') or None,
        'ramo': request.args.get('ramo') or None,
        'sub_agente': request.args.get('sub_agente') or None,
        'ejecutivo': request.args.get('ejecutivo') or None,
        'moneda': request.args.get('moneda') or None,
        'usuario': request.args.get('usuario') or None,
        'f_reg_desde': request.args.get('f_reg_desde') or None,
        'f_reg_hasta': request.args.get('f_reg_hasta') or None,
    }

    error = _validate_reporte_produccion_dates(filters)
    if error:
        return jsonify({'ok': False, 'error': error}), 400

    try:
        filepath, filename = export_reporte_produccion(filters)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte produccion: {e}")
        return jsonify({'ok': False, 'error': f"Error generando Excel: {str(e)}"}), 500


@bp.route('/api/reportes/produccion/export-pro', methods=['GET'])
@require_permission(lambda r: r in [Roles.BROKER, Roles.OPERADOR], response_mode='json')
def api_reporte_produccion_export_pro():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    filters = {
        'vig_desde': request.args.get('vig_desde') or None,
        'vig_hasta': request.args.get('vig_hasta') or None,
        'cia': request.args.get('cia') or None,
        'ramo': request.args.get('ramo') or None,
        'sub_agente': request.args.get('sub_agente') or None,
        'ejecutivo': request.args.get('ejecutivo') or None,
        'moneda': request.args.get('moneda') or None,
        'usuario': request.args.get('usuario') or None,
        'f_reg_desde': request.args.get('f_reg_desde') or None,
        'f_reg_hasta': request.args.get('f_reg_hasta') or None,
    }

    error = _validate_reporte_produccion_dates(filters)
    if error:
        return jsonify({'ok': False, 'error': error}), 400

    try:
        from controllers.reportes.reporte_produccion import export_reporte_produccion_pro

        filepath, filename = export_reporte_produccion_pro(filters)
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando reporte produccion pro: {e}")
        return jsonify({'ok': False, 'error': f"Error generando Excel Pro: {str(e)}"}), 500

@bp.route('/perfil')
def perfil_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/perfil.html')

@bp.route('/api/perfil/upload', methods=['POST'])
def perfil_upload():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    if 'foto' not in request.files:
        return jsonify({'ok': False, 'error': 'No se encontró el archivo'}), 400

    file = request.files['foto']
    if file.filename == '':
        return jsonify({'ok': False, 'error': 'Archivo sin nombre'}), 400

    if file:
        filename = secure_filename(file.filename)
        # Añadir timestamp para evitar caché y colisiones
        ext = os.path.splitext(filename)[1]
        new_filename = f"user_{session['user_id']}_{int(datetime.now().timestamp())}{ext}"
        
        # Guardar en static/uploads/perfiles/
        perfiles_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'perfiles')
        os.makedirs(perfiles_dir, exist_ok=True)
        save_path = os.path.join(perfiles_dir, new_filename)
        
        try:
            # Eliminar foto anterior si existe
            old_foto = session.get('foto_perfil')
            if old_foto:
                old_path = os.path.join(perfiles_dir, old_foto)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            file.save(save_path)
            
            # Actualizar en BD
            cnx = get_connection()
            cur = cnx.cursor()
            cur.execute("UPDATE usuarios SET foto_perfil = %s WHERE id = %s", (new_filename, session['user_id']))
            cnx.commit()
            cur.close()
            cnx.close()
            
            # Actualizar en sesión
            session['foto_perfil'] = new_filename
            
            return jsonify({'ok': True, 'foto_perfil': new_filename})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    return jsonify({'ok': False, 'error': 'Error desconocido'}), 500

@bp.route('/api/perfil/remove-photo', methods=['POST'])
def perfil_remove_photo():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    
    try:
        old_foto = session.get('foto_perfil')
        if old_foto:
            perfiles_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'perfiles')
            old_path = os.path.join(perfiles_dir, old_foto)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute("UPDATE usuarios SET foto_perfil = NULL WHERE id = %s", (session['user_id'],))
        cnx.commit()
        cur.close()
        cnx.close()
        
        session['foto_perfil'] = None
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/perfil/update-color', methods=['POST'])
def perfil_update_color():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    
    data = request.get_json()
    color = data.get('color')
    if not color:
        return jsonify({'ok': False, 'error': 'Color no proporcionado'}), 400
    
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute("UPDATE usuarios SET color_avatar = %s WHERE id = %s", (color, session['user_id'],))
        cnx.commit()
        cur.close()
        cnx.close()
        
        session['color_avatar'] = color
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/perfil/change-password', methods=['POST'])
def perfil_change_password():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    username = (data.get('username') or '').strip() or session.get('user')
    new_password = (data.get('new_password') or '').strip()

    if not username:
        return jsonify({'ok': False, 'error': 'Username no proporcionado'}), 400
    if username != session.get('user'):
        return jsonify({'ok': False, 'error': 'No autorizado'}), 403
    if not new_password:
        return jsonify({'ok': False, 'error': 'Nueva contraseña no proporcionada'}), 400
    if len(new_password) < 6:
        return jsonify({'ok': False, 'error': 'La contraseña debe tener al menos 6 caracteres'}), 400

    try:
        from models.db import load_settings
        from utils.crypto import encrypt_password

        cfg = load_settings() or {}
        key_phrase = cfg.get("key_encrypt_bd")
        salt = cfg.get("salt_encrypt", "SIS-ARIAS")

        password_encrypted = encrypt_password(new_password, key_phrase, salt)
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute("UPDATE usuarios SET password = %s WHERE username = %s", (password_encrypted, username))
        cnx.commit()
        updated = getattr(cur, "rowcount", 0) or 0
        cur.close()
        cnx.close()

        if updated <= 0:
            return jsonify({'ok': False, 'error': 'Usuario no encontrado'}), 404

        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/clientes/search', methods=['GET'])
def search_clientes_route():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401
    
    query = request.args.get('q', '').strip()
    if not query:
        return {'ok': True, 'rows': []}
        
    from controllers.clientes.cliente import search_clientes_data
    data = search_clientes_data(query)
    return {'ok': True, 'rows': data['rows']}

@bp.route('/menu/<page>', methods=['GET', 'POST'])
def menu_page(page):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Clientes → renderiza su plantilla dedicada con sus datos
    if page == 'clientes':
        from controllers.clientes.cliente import get_clientes_data
        data = get_clientes_data()

        # Pagination logic
        try:
            page_num = int(request.args.get('page') or 1)
        except ValueError:
            page_num = 1
        
        per_page = 20
        all_rows = data['rows']
        total = len(all_rows)
        pages = max(1, (total + per_page - 1) // per_page)
        
        # Ensure page_num is valid
        if pages > 0:
            page_num = max(1, min(page_num, pages))
        else:
            page_num = 1

        start = (page_num - 1) * per_page
        end = start + per_page
        sliced_rows = all_rows[start:end]

        pagination = {
            'page': page_num,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_prev': page_num > 1,
            'has_next': page_num < pages,
            'start_index': start + 1 if total > 0 else 0,
            'end_index': min(end, total)
        }

        from controllers.subagente import get_subagentes_abreviaciones

        subagentes_data = get_subagentes_abreviaciones()

        return render_template(
            'view/cliente/cliente.html',
            page='clientes',
            title=data['title'],
            rows=sliced_rows,
            filters=data['filters'],
            pagination=pagination,
            subagentes_abbrs=subagentes_data
        )
    # NUEVO: Reporte de Siniestros
    if page == 'reporte-siniestros':
        return render_template('view/reportes/reporte-siniestros.html', page='reporte-siniestros')

    # Clientes Anulados -> reutiliza la vista de clientes pero con datos anulados
    if page == 'clientes-anulados':
        from controllers.clientes.cliente import get_clientes_anulados_data
        data = get_clientes_anulados_data()

        try:
            page_num = int(request.args.get('page') or 1)
        except ValueError:
            page_num = 1

        per_page = 20
        all_rows = data['rows']
        total = len(all_rows)
        pages = max(1, (total + per_page - 1) // per_page)
        if pages > 0:
            page_num = max(1, min(page_num, pages))
        else:
            page_num = 1

        start = (page_num - 1) * per_page
        end = start + per_page
        sliced_rows = all_rows[start:end]

        pagination = {
            'page': page_num,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_prev': page_num > 1,
            'has_next': page_num < pages,
            'start_index': start + 1 if total > 0 else 0,
            'end_index': min(end, total)
        }

        from controllers.subagente import get_subagentes_abreviaciones
        subagentes_data = get_subagentes_abreviaciones()

        return render_template(
            'view/cliente/cliente.html',
            page='clientes-anulados',
            title=data['title'],
            rows=sliced_rows,
            filters=data['filters'],
            pagination=pagination,
            subagentes_abbrs=subagentes_data
        )
    if page == 'clientes-estado-cuenta':
        from controllers.clientes.estado_cuenta import get_estado_cuenta_data
        from datetime import datetime
        # Obtener filtros desde POST o GET (POST tiene prioridad)
        if request.method == 'POST':
            # Los filtros vienen desde el formulario POST
            filtros = request.form.to_dict()
        else:
            filtros = request.args.to_dict()

        data = get_estado_cuenta_data(filtros)
        return render_template(
            'view/cliente/estado-cuenta.html',
            page='clientes-estado-cuenta',
            cliente=data['cliente'],
            polizas=data['polizas'],
            totales=data['totales'],
            filtros_options=data['filtros_options'],
            filtros_aplicados=data['filtros_aplicados'],
            now=datetime.now()
        )

    if page == 'cobranzas-estado-cuenta':
        filtros = get_reporte_produccion_filters()
        return render_template(
            'view/cobranzas/estado-cuenta-cupones.html',
            page='cobranzas-estado-cuenta',
            filtros=filtros
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
            details=data.get('details', {}),
            highlight_id=request.args.get('highlight', type=int)
        )

    # NUEVO: Listado de pólizas con paginación (global: todas las pólizas)
    if page == 'listado-poliza':
        from controllers.polizas import get_polizas_all_paginated

        try:
            page_num = int(request.args.get('page') or 1)
        except Exception:
            page_num = 1
        try:
            per_page = int(request.args.get('per_page') or 10)
        except Exception:
            per_page = 10

        data = get_polizas_all_paginated(page=page_num, per_page=per_page)

        total = data.get('total', 0)
        pages = data.get('pages', 1)
        page_num = data.get('page', 1)
        per_page = data.get('per_page', 10)
        page_rows = data.get('rows', [])

        # Logic for pagination iterator (smart pagination)
        iter_pages = []
        left_edge = 1
        right_edge = 1
        left_current = 2
        right_current = 2
        
        last = 0
        for num in range(1, pages + 1):
            if num <= left_edge or \
               (num > pages - right_edge) or \
               (num >= page_num - left_current and num <= page_num + right_current):
                if last + 1 != num:
                    iter_pages.append(None) # Gap
                iter_pages.append(num)
                last = num

        pagination = {
            'page': page_num,
            'per_page': per_page,
            'total': total,
            'pages': pages,
            'has_prev': page_num > 1,
            'has_next': page_num < pages,
            'iter_pages': iter_pages
        }

        return render_template(
            'view/listado-poliza.html',
            page='listado-poliza',
            page_rows=page_rows,
            pagination=pagination
        )

    # REPORTE: Archivos Póliza
    if page == 'reporte-archivos-poliza':
        return render_template('view/reportes/reporte-archivos-poliza.html')

    # REPORTE: Anulados General (polizas, primas, recibos y cuotas anuladas)
    if page == 'reporte-anulados':
        return render_template('view/reportes/reporte-anulados.html')

    # REPORTE: Vencimientos y Renovaciones
    if page == 'vencimientos-renovaciones':
        return render_template(
            'view/reportes/vencimientos-renovaciones.html',
            current_ejecutivo=_get_current_user_ejecutivo(),
        )

    if page == 'polizas-anuladas':
        from controllers.polizas import get_polizas_anuladas
        data = get_polizas_anuladas()
        return render_template(
            'view/reportes/polizas-anuladas.html',
            page='polizas-anuladas',
            rows=data['rows']
        )

    if page == 'cuotas-anuladas':
        if session.get('role_name') != Roles.BROKER:
            return redirect(url_for('main.home'))
        return render_template(
            'view/reportes/cuotas-anuladas.html',
            page='cuotas-anuladas',
        )

    # Primas → plantilla dedicada
    if page == 'primas':
        from controllers.primas.primas import get_primas_data
        selected = session.get('selected_cliente') or {}
        numero_poliza = request.args.get('poliza') or None
        return_to = request.args.get('return') or request.args.get('return_to')
        data = get_primas_data(selected, numero_poliza)
        return render_template(
            'view/primas/primas.html',
            page='primas',
            title=data['title'],
            rows=data['rows'],
            details=data.get('details', {}),
            return_to=return_to
        )

    # NUEVO: Detalles de Póliza
    if page == 'detalles-poliza':
        from controllers.editar_poliza import get_poliza_data
        poliza_id = request.args.get('id')
        if not poliza_id:
            return redirect(url_for('main.menu_page', page='listado-poliza'))
        
        poliza = get_poliza_data(poliza_id)
        if not poliza:
            # Podríamos redirigir o mostrar error
            return redirect(url_for('main.menu_page', page='listado-poliza'))

        # Check for partial request (e.g. for modal)
        is_modal = request.args.get('partial') == 'true'

        return render_template(
            'view/Mostrar-detalles-poliza/detalles-poliza.html',
            page='detalles-poliza',
            poliza=poliza,
            is_modal=is_modal
        )

    # NUEVO: Detalles Primas
    if page == 'detalles-primas':
        from controllers.editar_poliza import get_poliza_data
        prima_id = request.args.get('id')
        if not prima_id:
            return redirect(url_for('main.menu_page', page='primas'))
        
        # Reutilizamos get_poliza_data ya que comparten tabla
        prima = get_poliza_data(prima_id)
        if not prima:
            return redirect(url_for('main.menu_page', page='primas'))

        # Check for partial request (e.g. for modal)
        is_modal = request.args.get('partial') == 'true'

        return render_template(
            'view/primas/Mostrar-detalles-primas.html',
            page='detalles-primas',
            prima=prima,
            is_modal=is_modal
        )

    if page == 'financiamiento-grupal':
        from controllers.financiamiento_grupal.financiacion_grupal import get_financiamiento_grupal_data
        data = get_financiamiento_grupal_data()
        return render_template(
            'view/financiamiento_grupal/Financiacion-Grupal.html',
            page='financiamiento-grupal',
            title=data['title'],
            rows=data['rows'],
            total_registros=data['total_registros'],
            total_importe=data['total_importe']
        )

    if page == 'financiamiento-grupal-avisos':
        from controllers.financiamiento_grupal.financiacion_grupal import get_financiamiento_grupal_avisos_data

        financiamiento_id = request.args.get('id')
        if not financiamiento_id:
            return redirect(url_for('main.menu_page', page='financiamiento-grupal'))

        data = get_financiamiento_grupal_avisos_data(financiamiento_id)
        if not data.get('detail'):
            return redirect(url_for('main.menu_page', page='financiamiento-grupal'))

        return render_template(
            'view/financiamiento_grupal/Financiacion-Grupal-Avisos.html',
            page='financiamiento-grupal-avisos',
            title=data['title'],
            detail=data['detail'],
            rows=data['rows'],
        )

    if page == 'financiamiento-grupal-cuotas':
        from controllers.cuotas.cuotas import get_cuotas_data

        financiamiento_id = request.args.get('id')
        if not financiamiento_id:
            return redirect(url_for('main.menu_page', page='financiamiento-grupal'))

        data = get_cuotas_data(financiamiento_id=financiamiento_id)
        if not data.get('encabezado', {}).get('financiamiento_grupal'):
            return redirect(url_for('main.menu_page', page='financiamiento-grupal'))

        return render_template(
            'view/cuotas/cuotas.html',
            page='financiamiento-grupal-cuotas',
            title=data['title'],
            encabezado=data['encabezado'],
            resumen=data['resumen'],
            rows=data['rows'],
            total_monto=data['total_monto'],
            es_financiamiento_grupal=data.get('es_financiamiento_grupal', False),
        )

    # Cuotas → plantilla dedicada
    if page == 'cuotas':
        import time
        from controllers.cuotas.cuotas import get_cuotas_data
        selected = session.get('selected_cliente') or {}
        numero_poliza = request.args.get('poliza') or None
        poliza_id = request.args.get('idPrima') or request.args.get('poliza_id')
        aviso = request.args.get('aviso')
        trace_id = f"route-cuotas-{int(time.time() * 1000)}"
        t_data = time.perf_counter()
        data = get_cuotas_data(selected, numero_poliza, poliza_id, aviso)
        # #region debug-point E:route-get-data-ms
        _dbg_cuotas_route_slow('E', 'routes/route.py:menu_page(page=cuotas)', 'Tiempo de get_cuotas_data en route', {
            "trace_id": trace_id,
            "poliza": numero_poliza,
            "poliza_id": poliza_id,
            "aviso": aviso,
            "rows": len(data.get('rows') or []),
            "elapsed_ms": round((time.perf_counter() - t_data) * 1000, 2),
        })
        # #endregion
        t_render = time.perf_counter()
        response = render_template(
            'view/cuotas/cuotas.html',
            page='cuotas',
            title=data['title'],
            encabezado=data['encabezado'],
            resumen=data['resumen'],
            rows=data['rows'],
            total_monto=data['total_monto'],
            es_financiamiento_grupal=data.get('es_financiamiento_grupal', False),
        )
        # #region debug-point E:route-render-ms
        _dbg_cuotas_route_slow('E', 'routes/route.py:menu_page(page=cuotas)', 'Tiempo de render_template cuotas', {
            "trace_id": trace_id,
            "elapsed_ms": round((time.perf_counter() - t_render) * 1000, 2),
        })
        # #endregion
        return response

    # Ajustadores (Maestros) - aceptar singular y plural para compatibilidad de URL
    if page in ('maestros-ajustadores', 'maestros-ajustador'):
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        from controllers.ajustadores.ajustadores import get_ajustadores
        rows = get_ajustadores() or []
        return render_template('view/ajustadores/ajustadores.html', page='maestros-ajustadores', title='Ajustadores', rows=rows)

    # Soporte para Productos (slug correcto y con typo del menú)
    if page in ('maestros-productos', 'maestros-prodcutos'):
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        # Cargamos filas si queremos pasar rows a la plantilla; la plantilla usa JS para consumo API
        from controllers.maestros.productos import get_productos
        rows = get_productos() or []
        return render_template('view/maestros/productos.html', page='maestros-productos', rows=rows)

    # Maestros: Compañías
    if page == 'maestros-companias':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        from controllers.compania import get_aseguradoras
        rows = get_aseguradoras() or []
        return render_template('view/maestros/companias.html', page='maestros-companias', rows=rows)

    # Maestros: Ejecutivos del Broker
    if page == 'maestros-ejecutivos':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        from controllers.ejecutivos import get_ejecutivos
        rows = get_ejecutivos() or []
        return render_template('view/maestros/ejecutivos.html', page='maestros-ejecutivos', rows=rows)

    # Maestros: Endosatarios
    if page == 'maestros-endosatarios':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        from controllers.endosatario.endosatario import get_endosatarios
        rows = get_endosatarios() or []
        return render_template('view/maestros/endosatarios.html', page='maestros-endosatarios', rows=rows)

    # Maestros: Sub Agentes
    if page == 'maestros-subagentes':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        from controllers.maestros.subagentes import get_subagentes
        rows = get_subagentes() or []
        return render_template('view/maestros/subagentes.html', page='maestros-subagentes', rows=rows)

    # Maestros: Vendedores (tabla agentes)
    if page == 'maestros-vendedores':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        from controllers.maestros.vendedores import get_vendedores
        rows = get_vendedores() or []
        return render_template('view/maestros/vendedores_list.html', page='maestros-vendedores', rows=rows)

    if page == 'maestros-vendedores-nuevo':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        return render_template(
            'view/maestros/vendedores_form.html',
            page='maestros-vendedores-nuevo',
            vendedor=None,
            action_url=url_for('main.save_vendedor')
        )

    if page == 'maestros-vendedores-editar':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        vid = request.args.get('id')
        if not vid:
            return redirect(url_for('main.menu_page', page='maestros-vendedores'))
        from controllers.maestros.vendedores import get_vendedor_by_id
        vendedor = get_vendedor_by_id(vid)
        if not vendedor:
            return redirect(url_for('main.menu_page', page='maestros-vendedores'))
        return render_template(
            'view/maestros/vendedores_form.html',
            page='maestros-vendedores-editar',
            vendedor=vendedor,
            action_url=url_for('main.update_vendedor', id=vid)
        )

    # Comisiones (listado, maestro)
    if page == 'maestros-comisiones':
        if not can_view_maestros(session.get('role_name')):
            return redirect(url_for('main.home'))
        try:
            from controllers.maestros.comisiones import get_comisiones
            rows = get_comisiones() or []
        except Exception:
            rows = []
        return render_template('view/maestros/comisiones.html', page='maestros-comisiones', rows=rows)

    # NUEVO: Editar Póliza
    if page == 'editar-poliza':
        from controllers.editar_poliza import get_poliza_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones
        from controllers.ejecutivos import get_ejecutivos
        from controllers.clientes.cliente import get_clientes_data
        from controllers.endosatario.endosatario import get_endosatarios # NUEVO
        from controllers.maestros.productos import get_productos # NUEVO

        poliza_id = request.args.get('id')
        if not poliza_id:
            return redirect(url_for('main.menu_page', page='listado-poliza'))
        
        poliza = get_poliza_data(poliza_id)
        if not poliza:
            return redirect(url_for('main.menu_page', page='listado-poliza'))

        is_modal = request.args.get('partial') == 'true'

        return render_template(
            'view/editar-poliza.html',
            is_modal=is_modal,
            poliza=poliza,
            ramos_abbrs=get_ramos(),
            productos_rows=get_productos(), # NUEVO
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),
            ejecutivos_rows=get_ejecutivos(),
            clientes_data=get_clientes_data(),
            endosatarios_rows=get_endosatarios() # NUEVO
        )

    # NUEVO: Editar Primas (Misma tabla que polizas pero diferente vista)
    if page == 'editar-primas':
        from controllers.editar_poliza import get_poliza_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones
        from controllers.clientes.cliente import get_clientes_data
        from controllers.endosatario.endosatario import get_endosatarios # NUEVO
        from controllers.maestros.productos import get_productos # NUEVO

        prima_id = request.args.get('id')
        if not prima_id:
            return redirect(url_for('main.menu_page', page='primas'))
        
        # Reuse get_poliza_data because Primas are Polizas rows
        prima = get_poliza_data(prima_id)
        if not prima:
            return redirect(url_for('main.menu_page', page='primas'))
        
        # Inject idPrima property if missing (it's actually idPoliza)
        if prima and 'idPrima' not in prima:
            prima['idPrima'] = prima.get('idPoliza')

        return render_template(
            'view/primas/editar-primas.html',
            prima=prima,
            # We pass similar helpers
            ramos_abbrs=get_ramos(),
            productos_rows=get_productos(), # NUEVO
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),
            clientes_data=get_clientes_data(),
            endosatarios_rows=get_endosatarios() # NUEVO
        )

    # NUEVO: Partial para Modal de Editar Primas
    if page == 'primas-editar-form':
        from controllers.editar_poliza import get_poliza_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones
        from controllers.clientes.cliente import get_clientes_data
        from controllers.endosatario.endosatario import get_endosatarios
        from controllers.maestros.productos import get_productos # NUEVO

        prima_id = request.args.get('id')
        # Si no hay ID, retornamos vacío o error, pero para el modal simplemente no cargará
        prima = None
        if prima_id:
            prima = get_poliza_data(prima_id)
            if prima and 'idPrima' not in prima:
                prima['idPrima'] = prima.get('idPoliza')

        # Reutilizamos editar-primas.html con flag is_modal=True
        return render_template(
            'view/primas/editar-primas.html',
            is_modal=True,
            prima=prima,
            ramos_abbrs=get_ramos(),
            productos_rows=get_productos(), # NUEVO
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),
            clientes_data=get_clientes_data(),
            endosatarios_rows=get_endosatarios()
        )

        # NUEVO: Avisos - Documentos
    if page == 'avisos':
        from controllers.editar_poliza import get_poliza_data
        from models.db import get_connection

        prima_id = request.args.get('id')
        if not prima_id:
             return redirect(url_for('main.menu_page', page='primas'))
        
        prima = get_poliza_data(prima_id)
        if not prima:
             return redirect(url_for('main.menu_page', page='primas'))

        # Listar todos los archivos desde poliza_archivos
        documents = []
        try:
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                """SELECT idArchivo, ruta_archivo, nombre_original, origen
                   FROM poliza_archivos
                   WHERE poliza_id = %s
                     AND (origen IS NULL OR UPPER(origen) <> 'CUOTA')
                   ORDER BY creado_en ASC, idArchivo ASC""",
                (prima_id,)
            )
            archivos = cur.fetchall()
            cur.close()
            cnx.close()
            for a in archivos:
                origen = (a.get('origen') or '').strip().upper()
                nombre = a['nombre_original'] or a['ruta_archivo']
                if origen == 'CONVENIO_PAGO' and nombre and not str(nombre).startswith('[CONVENIO]'):
                    nombre = f"[CONVENIO] {nombre}"
                if origen == 'CUOTA' and nombre and not str(nombre).startswith('[CUOTA'):
                    nombre = f"[CUOTA] {nombre}"
                documents.append({
                    'idArchivo': a['idArchivo'],
                    'name': nombre,
                    'url': url_for('main.serve_upload', filename=a['ruta_archivo'])
                })
        except Exception:
            pass

        return render_template(
            'view/avisos/avisos.html',
            page='avisos',
            prima=prima,
            documents=documents
        )

    # NUEVO: Detalles Avisos
    if page == 'detalles-avisos':
        from controllers.editar_poliza import get_poliza_data
        from models.db import get_connection

        prima_id = request.args.get('id')
        if not prima_id:
             return redirect(url_for('main.menu_page', page='avisos'))
        
        prima = get_poliza_data(prima_id)
        if not prima:
             return redirect(url_for('main.menu_page', page='avisos'))

        # Listar todos los archivos desde poliza_archivos
        documents = []
        try:
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                """SELECT idArchivo, ruta_archivo, nombre_original, origen
                   FROM poliza_archivos
                   WHERE poliza_id = %s
                     AND (origen IS NULL OR UPPER(origen) <> 'CUOTA')
                   ORDER BY creado_en ASC, idArchivo ASC""",
                (prima_id,)
            )
            archivos = cur.fetchall()
            cur.close()
            cnx.close()
            for a in archivos:
                origen = (a.get('origen') or '').strip().upper()
                nombre = a['nombre_original'] or a['ruta_archivo']
                if origen == 'CONVENIO_PAGO' and nombre and not str(nombre).startswith('[CONVENIO]'):
                    nombre = f"[CONVENIO] {nombre}"
                if origen == 'CUOTA' and nombre and not str(nombre).startswith('[CUOTA'):
                    nombre = f"[CUOTA] {nombre}"
                documents.append({
                    'idArchivo': a['idArchivo'],
                    'name': nombre,
                    'url': url_for('main.serve_upload', filename=a['ruta_archivo'])
                })
        except Exception:
            pass

        return render_template(
            'view/avisos/detalles-avisos.html',
            page='detalles-avisos',
            prima=prima,
            documents=documents
        )

    # NUEVO: Editar Avisos Form
    if page == 'avisos-editar-form':
        from controllers.editar_poliza import get_poliza_data
        from models.db import get_connection

        prima_id = request.args.get('id')
        if not prima_id:
             return redirect(url_for('main.menu_page', page='avisos'))
        
        prima = get_poliza_data(prima_id)
        if not prima:
             return redirect(url_for('main.menu_page', page='avisos'))

        # Listar todos los archivos desde poliza_archivos
        documents = []
        try:
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                """SELECT idArchivo, ruta_archivo, nombre_original, origen
                   FROM poliza_archivos
                   WHERE poliza_id = %s
                     AND (origen IS NULL OR UPPER(origen) <> 'CUOTA')
                   ORDER BY creado_en ASC, idArchivo ASC""",
                (prima_id,)
            )
            archivos = cur.fetchall()
            cur.close()
            cnx.close()
            for a in archivos:
                origen = (a.get('origen') or '').strip().upper()
                nombre = a['nombre_original'] or a['ruta_archivo']
                if origen == 'CONVENIO_PAGO' and nombre and not str(nombre).startswith('[CONVENIO]'):
                    nombre = f"[CONVENIO] {nombre}"
                if origen == 'CUOTA' and nombre and not str(nombre).startswith('[CUOTA'):
                    nombre = f"[CUOTA] {nombre}"
                documents.append({
                    'idArchivo': a['idArchivo'],
                    'name': nombre,
                    'url': url_for('main.serve_upload', filename=a['ruta_archivo'])
                })
        except Exception:
            pass

        return render_template(
            'view/avisos/editar-avisos.html',
            page='avisos-editar-form',
            prima=prima,
            documents=documents
        )


    # NUEVO: página “Añadir Póliza”
    if page == 'anadir-poliza':
        from controllers.addPoliza import get_rows
        from controllers.clientes.cliente import get_clientes_data
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones  # NUEVO
        from controllers.ejecutivos import get_ejecutivos               # NUEVO
        from controllers.endosatario.endosatario import get_endosatarios # NUEVO
        cli_data = get_clientes_data()
        selected = session.get('selected_cliente') or {}

        # Capturar contexto de retorno para botones "Volver"
        back_poliza_num = request.args.get('poliza') or request.args.get('nro_poliza') or None
        back_prima_id = request.args.get('idPrima') or request.args.get('prima_id') or request.args.get('id') or None
        back_return_to = request.args.get('return') or request.args.get('return_to') or None
        # Persistir en sesión si vienen por URL; si no, mantener lo anterior
        if back_poliza_num or back_prima_id or back_return_to:
            nav_ctx = session.get('anadir_poliza_nav') or {}
            if back_poliza_num: nav_ctx['poliza'] = back_poliza_num
            if back_prima_id: nav_ctx['idPrima'] = back_prima_id
            if back_return_to: nav_ctx['return_to'] = back_return_to
            session['anadir_poliza_nav'] = nav_ctx
        else:
            nav_ctx = session.get('anadir_poliza_nav') or {}

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
        # Autocompletar Ejecutivo por usuario si existe mapeo en BD y no viene en selected
        try:
            if not selected.get('ejecutivo') and session.get('user'):
                from models.db import get_connection
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.nombre
                    FROM usuarios u
                    LEFT JOIN ejecutivos e ON e.idEjecutivo = u.id_ejecutivo
                    WHERE u.username = %s
                    LIMIT 1
                """, (session.get('user'),))
                r = cur.fetchone()
                if r and r[0]:
                    selected['ejecutivo'] = r[0]
                    # Persistir en sesión para que JS también lo reciba siempre
                    prev_sel = session.get('selected_cliente') or {}
                    session['selected_cliente'] = {**prev_sel, **selected}
                cur.close()
                conn.close()
        except Exception as _:
            pass

        return render_template(
            'view/anadir.poliza.html',
            page= 'poliza',
            rows=get_rows(),
            clientes_rows=cli_data['rows'],
            selected=selected,
            ramos_abbrs=get_ramos(),
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),  # NUEVO
            ejecutivos_rows=get_ejecutivos(),                 # NUEVO
            endosatarios_rows=get_endosatarios(),             # NUEVO
            nav_ctx=nav_ctx                                   # Contexto de navegación para volver
        )

    # NUEVO: Reporte Diario (acepta 'reporte-diaro' por el slug del menú)
    if page in ('reporte-diario', 'reporte-diaro'):
        return render_template(
            'view/reporte-diario.dashboard.html',
            page='reporte-diario',
        )

    if page == 'reporte-gestion-diaria':
        filters = get_reporte_produccion_filters()
        return render_template(
            'view/reportes/reporte-gestion-diaria.html',
            page='reporte-gestion-diaria',
            filtros=filters,
        )

    if page == 'reporte-produccion':
        filters = get_reporte_produccion_filters()
        return render_template('view/reportes/reporte-produccion.html', page='reporte-produccion', filtros=filters)

    if page == 'clientes-cumpleanos':
        return render_template('view/cliente/reporte-cumpleaños.html')

    if page == 'solicitudes':
        from datetime import datetime as _dt_solicitudes
        from controllers.solicitudes.solicitudes import (
            get_solicitudes_rows, TIPO_OPERACION_OPTIONS, UBICACION_OPTIONS,
            PRIORIDAD_OPTIONS, MEDIO_OPTIONS,
        )
        from controllers.ramos import get_ramos
        from controllers.compania import get_aseguradoras
        from controllers.subagente import get_subagentes_abreviaciones
        from controllers.ejecutivos import get_ejecutivos

        q = (request.args.get('q') or '').strip() or None
        try:
            page_num = int(request.args.get('page') or 1)
        except ValueError:
            page_num = 1
        limit = 20

        data = get_solicitudes_rows(search=q, limit=limit, page=page_num)
        total = data['total']
        pages = max(1, (total + limit - 1) // limit)
        page_num = max(1, min(page_num, pages))
        pagination = {
            'page': page_num,
            'pages': pages,
            'total': total,
            'has_prev': page_num > 1,
            'has_next': page_num < pages,
            'start_index': (page_num - 1) * limit + 1 if total > 0 else 0,
            'end_index': min(page_num * limit, total),
        }

        return render_template(
            'view/solicitudes/solicitudes.html',
            page='solicitudes',
            rows=data['rows'],
            pagination=pagination,
            q=q,
            today=_dt_solicitudes.utcnow().date().isoformat(),
            tipo_operacion_options=TIPO_OPERACION_OPTIONS,
            ubicacion_options=UBICACION_OPTIONS,
            prioridad_options=PRIORIDAD_OPTIONS,
            medio_options=MEDIO_OPTIONS,
            ramos_abbrs=get_ramos(),
            aseguradoras_rows=get_aseguradoras(),
            subagentes_abbrs=get_subagentes_abreviaciones(),
            ejecutivos_rows=get_ejecutivos(),
            default_gestor=_get_current_user_ejecutivo(),
        )

    abort(404)


@bp.route('/api/reportes/cumpleanos', methods=['GET'])
def api_reporte_cumpleanos():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    mes = request.args.get('mes')
    estado = request.args.get('estado')
    dias = request.args.get('dias')
    orden = request.args.get('orden')
    try:
        from controllers.clientes.reporte_cumpleanios import get_cumpleanos_data
        rows = get_cumpleanos_data(mes=mes, estado=estado, dias=dias, orden=orden)
        return jsonify({'ok': True, 'rows': rows})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/upload/temp/delete', methods=['POST'])
def upload_temp_delete():
    """Elimina un archivo temporal de uploads/temp/ (se usa al limpiar el formulario)."""
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    data = request.get_json(silent=True) or {}
    filename = (data.get('filename') or '').strip()
    if not filename:
        return {'ok': False, 'error': 'Falta filename'}, 400
    # Prevenir path traversal: solo nombre de archivo, sin subdirectorios
    safe_name = os.path.basename(secure_filename(filename))
    if not safe_name:
        return {'ok': False, 'error': 'Nombre inválido'}, 400
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads'))
    temp_path = os.path.join(upload_folder, 'temp', safe_name)
    if os.path.isfile(temp_path):
        try:
            os.remove(temp_path)
            print(f"[upload_temp_delete] eliminado: {temp_path}")
        except Exception as e:
            print(f"[upload_temp_delete] error: {e}")
    return {'ok': True}


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

    # Guardar en subcarpeta 'temp' mientras sólo se extrae.
    # Se moverá a 'polizas' al confirmar "Guardar Pólizas".
    temp_folder = os.path.join(upload_folder, 'temp')
    os.makedirs(temp_folder, exist_ok=True)

    import time as _time_up
    filename = f"{int(_time_up.time())}_{secure_filename(file.filename)}"
    save_path = os.path.join(temp_folder, filename)
    file.save(save_path)
    try:
        exists = os.path.exists(save_path)
        print(f"[upload] saved to temp {save_path} exists={exists}")
    except Exception as e:
        print(f"[upload] error verifying save path: {e}")

    issuer = (request.form.get('issuer') or '').strip() or None
    pdf_password = (request.form.get('pdf_password') or '').strip() or None
    # Modo debug: si llega desde el cliente
    debug_enabled = (request.form.get('debug') == '1') or (request.args.get('debug') == '1')
    debug_logs = []
    def LOG(msg):
        # print(msg)
        if debug_enabled:
            debug_logs.append(str(msg))

    LOG(f'[upload] issuer={issuer} file={filename}')

    # Detectar PDF protegido con contraseña y solicitarla si no fue enviada
    def _pdf_is_encrypted(path: str) -> bool:
        try:
            import fitz
            with fitz.open(path) as doc:
                if getattr(doc, "is_encrypted", False):
                    return True
        except Exception:
            pass
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            if getattr(reader, "is_encrypted", False):
                return True
        except Exception:
            pass
        return False

    try:
        if _pdf_is_encrypted(save_path) and not pdf_password:
            return jsonify({
                'ok': False,
                'need_password': True,
                'filename': filename,
                'error': 'El PDF está protegido con contraseña',
                'debug': debug_logs,
            }), 423
    except Exception as _enc_e:
        LOG(f'[upload] encryption check error: {_enc_e}')

    items = []
    if filename.lower().endswith('.pdf'):
        try:
            items = parse_pdf_items_provider(save_path, issuer, pdf_password=pdf_password)
            detected_provider = getattr(parse_pdf_items_provider, "_last_provider", None)
            LOG(f'[upload] provider items count={len(items)}')
        except Exception as e:
            LOG(f'[upload] provider parse error: {e}')
            items = []
            detected_provider = None

    # Normalización: mapear variantes de claves a las usadas por la UI
    def _add_days_ddmmyyyy(date_str: str | None, days: int) -> str | None:
        try:
            if not date_str:
                return None
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    def _normalize_to_ui(it: dict) -> dict:
        cia_name = str(it.get("cia") or "").strip().lower()
        explicit_due_date = it.get("fecha_vecimiento") or it.get("fecha_vencimiento")
        fallback_due_date = it.get("vencimiento") or it.get("vigencia_hasta") or it.get("hasta") or it.get("expiracion")
        fecha_vencimiento_ui = explicit_due_date
        if not fecha_vencimiento_ui:
            # En Pacífico este campo es fecha de pago/cuota, no fin de vigencia.
            if "pac" not in cia_name:
                fecha_vencimiento_ui = fallback_due_date

        res = {
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
            "prima_total": it.get("prima_total") or it.get("prima_comercial_igv") or it.get("monto"),
            "prima_comercial_igv": it.get("prima_comercial_igv") or it.get("prima_total") or it.get("monto"),
            "comision_compania_pct": it.get("comision_compania_pct"),
            "comision_compania_importe": it.get("comision_compania_importe") or it.get("importe_comision") or it.get("importe_comisión"),
            "comision_subagente_pct": it.get("comision_subagente_pct"),
            "comision_subagente_importe": it.get("comision_subagente_importe"),
            "ramo": it.get("ramo") or it.get("doc_tipo"),
            "fecha_vencimiento": fecha_vencimiento_ui,
            "ramos_producto": it.get("ramos_producto") or it.get("producto"),
            "fecha_vecimiento": it.get("fecha_vecimiento"),
            "numero_documento_extracted": it.get("numero_documento_extracted"),
            # Campos extra para validación de cliente
            "contratante": it.get("contratante"),
            "razon_social": it.get("razon_social"),
            # Campos adicionales expandibles (Ver más) – passthrough si el parser los devuelve
            "flete": it.get("flete"),
            "fob": it.get("fob"),
            "sobreseguro": it.get("sobreseguro"),
            "nro_factura": it.get("nro_factura") or it.get("nrofactura") or it.get("numero_factura"),
            "descripcion": it.get("descripcion") or it.get("mercaderia") or it.get("mercancía"),
            "origen": it.get("origen"),
            "destino": it.get("destino"),
            "etd": it.get("etd"),
            "eta": it.get("eta"),
            "ip_ipl_ipf": it.get("ip_ipl_ipf") or it.get("ip_ipl_ipf_nro") or it.get("ip_ipl"),
            "proveedor": it.get("proveedor"),
            "ruta": it.get("ruta") or it.get("medio_transporte"),
            "puerto_embarque": it.get("puerto_embarque") or it.get("puerto"),
            "embalaje": it.get("embalaje"),
            "certificado": it.get("certificado"),
            # Factura / fecha pago (ya existen en pane)
            "factura": it.get("factura"),
            "fecha_pago": it.get("fecha_pago"),
        }
        try:
            mv = (res.get("moneda") or "").replace("\u00A0", " ").strip()
            up = mv.upper()
            compact = re.sub(r"\s+", "", up)
            if compact:
                if compact in {"US$", "USD", "$", "D"} or "DOL" in compact:
                    res["moneda"] = "US$"
                elif compact.startswith("S/") or compact.startswith("S/.") or compact in {"S", "PEN"} or "SOL" in compact:
                    res["moneda"] = "S/"
        except Exception:
            pass

        try:
            for k in (
                "prima_comercial",
                "prima_neta",
                "prima_total",
                "prima_comercial_igv",
                "comision_compania_importe",
                "comision_subagente_importe",
                "flete",
                "fob",
                "sobreseguro",
            ):
                raw_v = res.get(k)
                if raw_v is None:
                    continue
                norm_v = _normalize_importe_text(str(raw_v))
                if norm_v:
                    res[k] = norm_v
        except Exception:
            pass

        def _looks_like_insurer_name(name: str | None) -> bool:
            if not name:
                return False
            low = name.lower()
            tokens = [
                "la positiva",
                "positiva seguros",
                "positiva vida",
                "sanitas",
                "pacifico",
                "pacífico",
                "mapfre",
                "qualitas",
                "quálitas",
                "crecer seguros",
                "rimac",
            ]
            return any(t in low for t in tokens)

        aseg = (res.get("colectivo_asegurado") or "").strip()
        cont = (res.get("contratante") or "").strip()
        if aseg and _looks_like_insurer_name(aseg) and cont:
            res["colectivo_asegurado"] = cont

            # Limpieza defensiva: quitar DNI/RUC pegado en la misma línea del nombre
            try:
                nombre = (res.get("colectivo_asegurado") or "").strip()
                if nombre:
                    nombre = re.sub(r"\s*(?:DNI\s*/?\s*RUC|DNI|RUC)\s*[:\-]?\s*\d{8,11}.*$", "", nombre, flags=re.IGNORECASE).strip(" -:·.")
                    res["colectivo_asegurado"] = nombre
            except Exception:
                pass

        try:
            has_com = res.get("prima_comercial") is not None and str(res.get("prima_comercial") or "").strip() != ""
            has_net = res.get("prima_neta") is not None and str(res.get("prima_neta") or "").strip() != ""
            if has_com and not has_net:
                val_txt = _normalize_importe_text(str(res.get("prima_comercial") or ""))
                if val_txt:
                    val = float(val_txt)
                    res["prima_neta"] = f"{(val / 1.03):.2f}"
            elif has_net and not has_com:
                val_txt = _normalize_importe_text(str(res.get("prima_neta") or ""))
                if val_txt:
                    val = float(val_txt)
                    res["prima_comercial"] = f"{(val * 1.03):.2f}"
        except Exception:
            pass

        try:
            total_igv_raw = str(res.get("prima_comercial_igv") or "").strip()
            if total_igv_raw:
                total_igv_txt = _normalize_importe_text(total_igv_raw)
                total_igv = float(total_igv_txt) if total_igv_txt else 0.0
                if total_igv > 0:
                    expected = total_igv / 1.18
                    pc_raw = str(res.get("prima_comercial") or "").strip()
                    pc_txt = _normalize_importe_text(pc_raw) if pc_raw else ""
                    pc = float(pc_txt) if pc_txt else None
                    rel = (abs(pc - expected) / expected) if (pc is not None and expected > 0) else None
                    if pc is None or pc <= 0 or (rel is not None and rel > 0.20):
                        res["prima_comercial"] = f"{expected:.2f}"
                        res["prima_neta"] = f"{(expected / 1.03):.2f}"
        except Exception:
            pass

        # Regla de negocio de fechas (UI) deshabilitada: cálculo de último día de pago
        # cand = res.get("fecha_emision") or res.get("inicio_vigencia")
        # calc = _add_days_ddmmyyyy(cand, 15)
        # if not res.get("ultimo_dia_pago") and calc:
        #     res["ultimo_dia_pago"] = calc
        # if not res.get("fecha_vencimiento"):
        #     res["fecha_vencimiento"] = res.get("ultimo_dia_pago") or calc
        # if not res.get("fecha_vecimiento"):
        #     res["fecha_vecimiento"] = res.get("ultimo_dia_pago") or calc
    
        return res

    if items and len(items) > 0:
        LOG('[upload] Origen de datos: provider parser (items).')
        items_ui = [_normalize_to_ui(it) for it in items]
        pdf_text_full = ''
        try:
            pdf_text_full = _extract_text_fitz(save_path, password=pdf_password) or ''
        except Exception:
            pdf_text_full = ''
        if not pdf_text_full:
            try:
                pdf_text_full = _extract_text_pypdf2(save_path, password=pdf_password) or ''
            except Exception:
                pdf_text_full = ''

        def _clean_spaces(s: str | None) -> str:
            if not s:
                return ''
            try:
                s = s.replace("\u00A0", " ")
            except Exception:
                pass
            return re.sub(r"\s+", " ", str(s)).strip()

        def _clean_name(s: str | None) -> str:
            name = _clean_spaces(s)
            if not name:
                return ''
            try:
                name = re.sub(
                    r"\s*(?:DNI\s*/?\s*RUC|DNI|RUC)\s*[:\-]?\s*\d{8,11}.*$",
                    "",
                    name,
                    flags=re.IGNORECASE,
                ).strip(" -:·.")
            except Exception:
                pass
            return name

        def _looks_like_contact_or_noise(s: str | None) -> bool:
            txt = _clean_spaces(s)
            if not txt:
                return True
            low = txt.lower()
            noise_patterns = [
                r"\bweb\b",
                r"www\.",
                r"http",
                r"@",
                r"\btel(?:\.|:|\b)",
                r"\btelf(?:\.|:|\b)",
                r"\btelefono\b",
                r"\bteléfono\b",
                r"\bdirección(?:es)?\b",
                r"\bdireccion(?:es)?\b",
                r"\bdomicilio\b",
                r"\btelef[oó]nico\b",
                r"\belectr[oó]nico\b",
                r"\bcorreo\b",
                r"\bemail\b",
            ]
            if any(re.search(p, low) for p in noise_patterns):
                return True
            # Evitar que se tome como "asegurado" una cláusula/aviso del PDF
            clause_tokens = [
                "por lo que",
                "no cubrira",
                "no cubrirá",
                "no cubre",
                "reparacion",
                "reparación",
                "daños",
                "danos",
                "preexist",
                "inspeccion",
                "inspección",
                "de verificarse",
                "exclusion",
                "exclusión",
                "cobertura",
            ]
            if any(t in low for t in clause_tokens):
                return True
            # Nombres rara vez son oraciones con punto; esto suele indicar texto contractual.
            if "." in txt and len(txt) > 40:
                # Permitir abreviaturas societarias comunes (p.ej. "S.A.C.") que son normales en razón social.
                if not re.search(r"\bS\.A\.C\.?\b|\bS\.A\.A\.?\b|\bS\.A\.?\b|\bS\.R\.L\.?\b|\bE\.I\.R\.L\.?\b", txt, re.IGNORECASE):
                    return True
            if ":" in txt and len(txt) > 12:
                return True
            letters = len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", txt))
            if letters < 3:
                return True
            if len(txt) > 140:
                return True
            return False

        def _extract_best_name_from_pdf(txt: str | None) -> str:
            if not txt:
                return ''
            t = (txt or '').replace("\u00A0", " ")
            candidates: list[str] = []
            try:
                m = re.search(r"Señor\(a\)\.-\s*\n([^\n]{3,120})", t, flags=re.IGNORECASE)
                if m:
                    candidates.append(m.group(1))
            except Exception:
                pass
            try:
                m = re.search(r"\bHola\s+([^\n:]{3,120})\s*:", t, flags=re.IGNORECASE)
                if m:
                    candidates.append(m.group(1))
            except Exception:
                pass
            try:
                for m in re.finditer(r"^\s*(?:Cliente|Asegurado)\s*[:：]\s*([^\n]{3,120})", t, flags=re.IGNORECASE | re.MULTILINE):
                    candidates.append(m.group(1))
            except Exception:
                pass
            for c in candidates:
                c2 = _clean_name(c)
                if c2 and not _looks_like_contact_or_noise(c2):
                    return c2.upper()
            return ''

        def _normalize_moneda_value(v: str | None) -> str | None:
            if v is None:
                return None
            raw = _clean_spaces(v)
            if not raw:
                return None
            up = re.sub(r"\s+", "", raw.upper())
            if not up:
                return None
            if up.startswith("US$") or "USD" in up or "DOL" in up or up == "$":
                return "US$"
            if up.startswith("S/") or up.startswith("S/.") or "SOL" in up or up == "PEN":
                return "S/"
            return raw

        def _infer_moneda_from_pdf_any(txt: str | None) -> str | None:
            if not txt:
                return None
            t = (txt or '').replace("\u00A0", " ")
            m = re.search(r"\bMONEDA\b[\s:：]*([A-Za-zÁÉÍÓÚÑáéíóúñ$\./\s]{1,20})", t, re.IGNORECASE | re.DOTALL)
            if m:
                cand = re.sub(r"\s+", "", (m.group(1) or "").upper())
                if cand.startswith("US$") or cand.startswith("USD") or cand.startswith("$") or "DOL" in cand:
                    return "US$"
                if cand.startswith("S/") or cand.startswith("S/.") or cand.startswith("PEN") or "SOL" in cand:
                    return "S/"

            m2 = re.search(
                r"(?:Prima\s+Comercial|Prima\s+Total|TOTAL|IMPORTE\s*TOTAL)[\s\S]{0,260}?(US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)(?=\s|$)",
                t,
                re.IGNORECASE | re.DOTALL,
            )
            if m2:
                tok = re.sub(r"\s+", "", (m2.group(1) or "").upper())
                if tok.startswith("US$") or tok.startswith("USD") or tok == "$" or "DOL" in tok:
                    return "US$"
                return "S/"

            up = t.upper()
            idx_us = up.find("US$")
            idx_usd = re.search(r"\bUSD\b", up)
            idx_dol = re.search(r"\bDOL", up)
            idx_s = re.search(r"S\s*/\s*\.?|S\s*/|\bSOLES\b|\bPEN\b", up)
            dollar_idxs = [i for i in [
                idx_us if idx_us >= 0 else None,
                idx_usd.start() if idx_usd else None,
                idx_dol.start() if idx_dol else None,
            ] if i is not None]
            sol_idxs = [idx_s.start()] if idx_s else []
            if not dollar_idxs and not sol_idxs:
                return None
            return "US$" if (min(dollar_idxs) if dollar_idxs else 10**9) <= (min(sol_idxs) if sol_idxs else 10**9) else "S/"

        if pdf_text_full:
            inferred_moneda_any = _infer_moneda_from_pdf_any(pdf_text_full)
            inferred_name_any = _extract_best_name_from_pdf(pdf_text_full)
            try:
                prov_hint = str(detected_provider or '').lower()
            except Exception:
                prov_hint = ''
            is_positiva_like = ('positiva' in prov_hint) or ('lpv' in prov_hint)
            for it in items_ui:
                # Asegurado: evitar que se cuele texto de contacto (web/teléfono/dirección)
                current_name = _clean_name(it.get("colectivo_asegurado"))
                alt_name = _clean_name(it.get("contratante")) or _clean_name(it.get("razon_social"))
                best = ''
                if current_name and not _looks_like_contact_or_noise(current_name):
                    best = current_name
                elif alt_name and not _looks_like_contact_or_noise(alt_name):
                    best = alt_name
                elif inferred_name_any:
                    best = inferred_name_any
                if best:
                    it["colectivo_asegurado"] = best.upper()

                cur_norm = _normalize_moneda_value(it.get("moneda"))
                if cur_norm in {"S/", "US$"}:
                    it["moneda"] = cur_norm
                else:
                    it["moneda"] = (inferred_moneda_any if is_positiva_like else None) or cur_norm or it.get("moneda")
        # Rimac: garantizar UN solo ítem y priorizar póliza en formato '#### - #######'
        try:
            issuer_low = (issuer or '').lower()
        except Exception:
            issuer_low = ''
        if (detected_provider and 'rimac' in str(detected_provider)) or ('rimac' in issuer_low):
            def _score_rimac(it: dict) -> int:
                s = 0
                np = (it.get('numero_poliza') or it.get('poliza') or '').strip()
                # formato con guion
                if re.search(r"\b\d{2,6}\s*-\s*\d{5,12}\b", np):
                    s += 100
                # longitud mayor suele ser '2101 - 1618199' vs '1618199'
                s += min(len(np), 20)
                return s
            items_ui.sort(key=_score_rimac, reverse=True)
            items_ui = [items_ui[0]]
            LOG(f"[upload] rimac: reducido a un ítem: {items_ui[0].get('numero_poliza')}")

        if ((detected_provider or '') and 'rimac' in str(detected_provider)) or ((issuer or '').lower().find('rimac') != -1):
            def _score(it: dict) -> int:
                s = 0
                np = (it.get('numero_poliza') or it.get('poliza') or '').strip()
                if re.search(r"\b\d{2,6}\s*-\s*\d{5,12}\b", np):
                    s += 100
                s += min(len(np), 20)
                return s
            items_ui.sort(key=_score, reverse=True)
            items_ui = [items_ui[0]]
            LOG(f"[upload] rimac: forzado a un solo ítem")
        try:
            dash = r"(?:-|–|—|‑|−)"
            is_pos = False
            try:
                prov_s = str(detected_provider or '').lower()
            except Exception:
                prov_s = ''
            try:
                issuer_s = (issuer or '').lower()
            except Exception:
                issuer_s = ''
            if ('positiva' in prov_s) or ('positiva' in issuer_s) or ('lpv' in prov_s) or ('lpv' in issuer_s):
                is_pos = True

            def _infer_moneda_from_pdf(txt: str | None) -> str | None:
                if not txt:
                    return None
                t = (txt or '').replace('\u00A0', ' ')
                m = re.search(
                    r"\bMONEDA\b[\s:：]*([A-Za-zÁÉÍÓÚÑáéíóúñ$\./\s]{1,20})",
                    t,
                    re.IGNORECASE | re.DOTALL,
                )
                if m:
                    cand = re.sub(r"\s+", "", (m.group(1) or "").upper())
                    if cand.startswith("US$") or cand.startswith("USD") or cand.startswith("$") or "DOL" in cand:
                        return "US$"
                    if cand.startswith("S/") or cand.startswith("S/.") or cand.startswith("PEN") or "SOL" in cand:
                        return "S/"

                m2 = re.search(
                    r"Prima\s+Comercial[\s\S]{0,220}?(US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)(?=\s|$)",
                    t,
                    re.IGNORECASE | re.DOTALL,
                )
                if m2:
                    tok = re.sub(r"\s+", "", (m2.group(1) or "").upper())
                    if tok.startswith("US$") or tok.startswith("USD") or tok == "$" or "DOL" in tok:
                        return "US$"
                    return "S/"

                up = t.upper()
                idx_us = up.find("US$")
                idx_usd = re.search(r"\bUSD\b", up)
                idx_dol = re.search(r"\bDOL", up)
                idx_s = re.search(r"S\s*/\s*\.?|S\s*/|\bSOLES\b|\bPEN\b", up)
                dollar_idxs = [i for i in [
                    idx_us if idx_us >= 0 else None,
                    idx_usd.start() if idx_usd else None,
                    idx_dol.start() if idx_dol else None,
                ] if i is not None]
                sol_idxs = [idx_s.start()] if idx_s else []
                if not dollar_idxs and not sol_idxs:
                    return None
                return "US$" if (min(dollar_idxs) if dollar_idxs else 10**9) <= (min(sol_idxs) if sol_idxs else 10**9) else "S/"

            pdf_text = pdf_text_full or _extract_text_pypdf2(save_path, password=pdf_password)
            if pdf_text:
                inferred_moneda = _infer_moneda_from_pdf(pdf_text) if is_pos else None
                for it in items_ui:
                    if is_pos and inferred_moneda:
                        mv = (it.get('moneda') or '').replace('\u00A0', ' ').strip()
                        mv_up = re.sub(r"\s+", "", mv.upper())
                        if mv_up not in {"US$", "S/"}:
                            it['moneda'] = inferred_moneda
                        elif mv_up == "US$":
                            it['moneda'] = "US$"
                        elif mv_up == "S/":
                            it['moneda'] = "S/"
                    np = (it.get('numero_poliza') or it.get('poliza') or '').strip()
                    if not re.search(r"\b\d{2,6}\s*-\s*\d{5,12}\b", np):
                        m = re.search(r"(?:pol[ií]za|p[oó]liza)\s*N[°º]\s*[:：]?\s*([0-9]{2,6})(\s*" + dash + r"\s*)([0-9]{5,12})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if not m:
                            m = re.search(r"\bNro\.?\s*[:：]?\s*([0-9]{2,6})(\s*" + dash + r"\s*)([0-9]{5,12})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if m:
                            it['numero_poliza'] = f"{m.group(1)}{m.group(2)}{m.group(3)}"
                            if not it.get('certificado'):
                                it['certificado'] = m.group(3).strip()
                    if not it.get('certificado'):
                        mc = re.search(r"(?:pol[ií]za|p[oó]liza)\s*[:：]\s*([0-9]{2,10})\s*" + dash + r"\s*([0-9]{2,10})", pdf_text, re.IGNORECASE)
                        if mc:
                            it['certificado'] = mc.group(2).strip()
                    iv = (it.get('inicio_vigencia') or '').strip()
                    ve = (it.get('vencimiento') or '').strip()
                    mv_label_iv = re.search(r"vigencia\s*[-–—]?\s*inicio\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                    mv_label_ve = re.search(r"\bt(?:e|é)rmino\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                    if mv_label_iv and mv_label_ve:
                        it['inicio_vigencia'] = mv_label_iv.group(1).replace("-", "/")
                        it['vencimiento'] = mv_label_ve.group(1).replace("-", "/")
                    elif not (iv and ve):
                        mv = re.search(r"vigencia\s*[:：]?\s*(?:del\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s*(?:al|a\s*al|-\s*)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if not mv:
                            mv = re.search(r"\bdel\s*(\d{1,2}/\d{1,2}/\d{4})\s*(?:al|-\s*)\s*(\d{1,2}/\d{1,2}/\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if not mv:
                            mv = re.search(r"vigencia\s+(?:inicia|empieza|comienza)\s*(?:el\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})[\s\S]{0,200}?\b(?:y\s+)?(?:vence|venc(?:e|imiento)|finaliza|termina)\s*(?:el\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if mv:
                            it['inicio_vigencia'] = mv.group(1).replace("-", "/")
                            it['vencimiento'] = mv.group(2).replace("-", "/")
                    if not iv:
                        m_iv_ind = re.search(r"INICIO\s+DE\s+VIGENCIA\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if m_iv_ind:
                            it['inicio_vigencia'] = m_iv_ind.group(1).replace("-", "/")
                    if not ve:
                        m_fv_ind = re.search(r"FIN\s+DE\s+VIGENCIA\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})", pdf_text, re.IGNORECASE | re.DOTALL)
                        if m_fv_ind:
                            it['vencimiento'] = m_fv_ind.group(1).replace("-", "/")
                    fe_header = None
                    try:
                        mh = re.search(
                            r"FECHA\s+DE\s+EMISI[ÓO]N\s*[:：.]?\s*(?:\r?\n\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                            pdf_text,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if mh:
                            fe_header = mh.group(1).replace("-", "/")
                    except Exception:
                        fe_header = None
                    if fe_header:
                        fe_existing = (it.get('fecha_emision') or '').strip()
                        if not fe_existing:
                            it['fecha_emision'] = fe_header

                    fe = (it.get('fecha_emision') or '').strip()
                    if not fe:
                        meses = {
                            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
                            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
                            "setiembre": "09", "septiembre": "09", "octubre": "10",
                            "noviembre": "11", "diciembre": "12",
                        }
                        mwords = re.search(r"(?:Suscrito|Emitido|Expedido)[\s\S]{0,100}?(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+de[l]?\s+(\d{4})", pdf_text, re.IGNORECASE)
                        if not mwords:
                            mwords = re.search(r"(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo)\s*[,，]\s*(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+de[l]?\s+(\d{4})", pdf_text, re.IGNORECASE)
                        if not mwords:
                            mwords = re.search(r"\b(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+de\s+(\d{4})\b", pdf_text, re.IGNORECASE)
                        if mwords:
                            mon = mwords.group(2).lower()
                            mon_num = meses.get(mon)
                            if mon_num:
                                dd = f"{int(mwords.group(1)):02d}"
                                it['fecha_emision'] = f"{dd}/{mon_num}/{mwords.group(3)}"
        except Exception:
            pass
        # ===== PARSEO DE CAMPOS ADICIONALES (expandibles "Ver más") desde texto del PDF =====
        try:
            pdf_text_add = pdf_text_full or pdf_text or ''
            if pdf_text_add:
                def _norm_importe(v: str | None) -> str:
                    if not v:
                        return ''
                    raw = str(v).strip()
                    if not raw:
                        return ''
                    # Primero intento "cualquier dígito continuo con decimal" (más general), luego miles separados
                    m = re.search(r"([0-9]+(?:[.,][0-9]{1,4})?|[0-9]{1,3}(?:[.,\s][0-9]{3})+(?:[.,][0-9]{1,4})?)", raw)
                    if not m:
                        return ''
                    num = m.group(1)
                    has_comma = ',' in num
                    has_dot = '.' in num
                    if has_comma and has_dot:
                        if num.rfind(',') > num.rfind('.'):
                            num = num.replace('.', '').replace(',', '.')
                        else:
                            num = num.replace(',', '')
                    elif has_comma and not has_dot:
                        if re.search(r",\d{1,2}$", num):
                            num = num.replace(',', '.')
                        else:
                            num = num.replace(',', '')
                    cleaned = num.replace(' ', '')
                    try:
                        float(cleaned)
                        return cleaned
                    except Exception:
                        return ''

                lines = re.split(r"\r?\n", pdf_text_add)
                def _find_header_range(header_regex, stop_regex=None):
                    """Devuelve (start_idx, end_idx) dentro de lines donde se aplica un bloque encabezado."""
                    s = -1
                    e = len(lines)
                    for i, line in enumerate(lines):
                        if s < 0 and re.search(header_regex, line, re.IGNORECASE):
                            s = i
                            continue
                        if s >= 0 and stop_regex and re.search(stop_regex, line, re.IGNORECASE):
                            e = i
                            break
                    if s < 0:
                        return (-1, -1)
                    return (s, e)
                def _first_digit_line_in_range(sl, el, needs_date):
                    for i in range(sl, min(el, len(lines))):
                        ls = lines[i].strip()
                        if not ls or not ls[0].isdigit():
                            continue
                        if needs_date and not re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", ls):
                            continue
                        return lines[i]
                    return ''

                for it in items_ui:
                    txt = pdf_text_add

                    # --- A) Observaciones y comentarios (patrón label : valor) ---
                    if not it.get('proveedor'):
                        mp = re.search(r"(?:Proveedor|Proovedor|Supplier)\s*[:：]\s*([^\n\r]{3,180})", txt, re.IGNORECASE)
                        if mp: it['proveedor'] = mp.group(1).strip()
                    if not it.get('descripcion'):
                        md = re.search(r"(?:Mercader[ií]a|Mercancia|Description|Descripci[oó]n)\s*[:：]\s*([^\n\r]{2,260})", txt, re.IGNORECASE)
                        if md: it['descripcion'] = md.group(1).strip()
                    if not it.get('fob'):
                        mfob = re.search(r"(?:Valor\s+FOB|FOB)\s*[:：]?\s*(?:US\s*\$|US\$|USD|S\s*\/\.?|\$)?\s*([\d.,\s$US/]+)", txt, re.IGNORECASE)
                        if mfob: it['fob'] = _norm_importe(mfob.group(1))
                    if not it.get('flete'):
                        mf = re.search(r"(?:Valor\s+Flete|Flete|Freight)\s*[:：]?\s*(?:US\s*\$|US\$|USD|S\s*\/\.?|\$)?\s*([\d.,\s$US/]+)", txt, re.IGNORECASE)
                        if mf: it['flete'] = _norm_importe(mf.group(1))
                    if not it.get('sobreseguro'):
                        ms = re.search(r"(?:Sobreseguro|Overinsurance|Sobre\s*seguro)\s*[:：]?\s*(?:US\s*\$|US\$|USD|S\s*\/\.?|\$)?\s*([\d.,\s$US/]+)", txt, re.IGNORECASE)
                        if ms: it['sobreseguro'] = _norm_importe(ms.group(1))
                    # --- B) Línea resumen: FOB US$X - FLETE US$Y - SOBRESEGURO US$Z (siempre prioriza sobre líneas 0) ---
                    mline = re.search(
                        r"FOB\s*(?:US\s*\$|US\$|USD|S\s*\/\.?|\$)\s*([\d.,]+)\s*[\-–—]\s*"
                        r"FLETE\s*(?:US\s*\$|US\$|USD|S\s*\/\.?|\$)\s*([\d.,]+)\s*[\-–—]\s*"
                        r"SOBRESEGURO\s*(?:US\s*\$|US\$|USD|S\s*\/\.?|\$)\s*([\d.,]+)",
                        txt, re.IGNORECASE,
                    )
                    if mline:
                        fob_v = _norm_importe(mline.group(1))
                        fle_v = _norm_importe(mline.group(2))
                        sob_v = _norm_importe(mline.group(3))
                        if fob_v: it['fob'] = fob_v
                        if fle_v: it['flete'] = fle_v
                        if sob_v: it['sobreseguro'] = sob_v
                    # --- C) IP/IPL/IPF [N°] XXXX [DE FACTURA YYYYY + ZZZZZ] ---
                    if not it.get('ip_ipl_ipf') or not it.get('nro_factura'):
                        mip = re.search(
                            r"IP\s*/\s*IPL\s*/\s*IPF\s*(?:N\s*[°º]\s*)?([A-Za-z0-9\-]{2,25})[\s\S]{0,120}?"
                            r"(?:DE\s+)?FACTURA\s*([A-Za-z0-9\-\.+\s]{3,80}?)(?:\s*(?:\n|$|TASA|PRIMA|Póliza|POLIZA|Itinerario|Declaración))",
                            txt, re.IGNORECASE,
                        )
                        if mip:
                            if not it.get('ip_ipl_ipf'): it['ip_ipl_ipf'] = mip.group(1).strip()
                            if not it.get('nro_factura'):
                                f_raw = re.sub(r"\s+", " ", mip.group(2)).strip(" :：.-")
                                it['nro_factura'] = f_raw
                        else:
                            if not it.get('ip_ipl_ipf'):
                                m2 = re.search(r"IP\s*/\s*IPL\s*/\s*IPF\s*(?:N\s*[°º]\s*)?([A-Za-z0-9\-]{2,25})", txt, re.IGNORECASE)
                                if m2: it['ip_ipl_ipf'] = m2.group(1).strip()
                            if not it.get('nro_factura'):
                                m3 = re.search(
                                    r"N\s*[°º]\s*(?:DE\s+)?FACTURA\s*[:：]?\s*([A-Za-z0-9\-\.+\s]{3,80}?)"
                                    r"(?:\s*(?:\n|$|TASA|PRIMA|Póliza|POLIZA|Itinerario|Declaración))",
                                    txt, re.IGNORECASE,
                                )
                                if m3:
                                    f_raw = re.sub(r"\s+", " ", m3.group(1)).strip(" :：.-")
                                    it['nro_factura'] = f_raw
                                else:
                                    m4 = re.search(r"FACTURA\s*[:：]?\s*([A-Za-z0-9\-\.+\s]{3,50}?)(?:\s*(?:\n|$|TASA|PRIMA|Póliza|POLIZA))", txt, re.IGNORECASE)
                                    if m4:
                                        f_raw = re.sub(r"\s+", " ", m4.group(1)).strip(" :：.-")
                                        it['nro_factura'] = f_raw

                    # --- D) ITINERARIO DE TRANSPORTES (regex anclados, NO depende de separadores de columna) ---
                    itinerario_date = ''
                    origen_raw = ''
                    destino_raw = ''
                    if not it.get('origen') or not it.get('destino') or not it.get('etd'):
                        # 1) Fecha F.Salida: primera fecha después del encabezado Itinerario
                        m_fs = re.search(
                            r"Itinerario\s+de\s+Transportes[\s\S]{0,400}?Etapa\s+F\.Salida\s+Origen[\s\S]{0,200}?(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                            txt, re.IGNORECASE,
                        )
                        if m_fs:
                            itinerario_date = m_fs.group(1).replace('-', '/').strip()
                        # 2) Origen: patrón "CIUDAD-PAIS" (DELHI-INDIA, etc.) que aparece JUSTO después de itinerario_date
                        #    O bien: "CIUDAD PAIS" (dos tokens en MAYUS, antes de "PERU").
                        if not origen_raw:
                            m_orig = re.search(
                                r"Itinerario\s+de\s+Transportes[\s\S]{0,400}?Etapa\s+F\.Salida\s+Origen[\s\S]{0,300}?"
                                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+([A-Z][A-ZÁÉÍÓÚÑ0-9\.\-]*[ \-][A-Z][A-ZÁÉÍÓÚÑ]+)\s+(PERU[^\n\r]{2,120}?)(?:\s{1,}-|Ruta|Declaración|Deducible|Etapa|Embalaje|Medio|$)",
                                txt, re.IGNORECASE,
                            )
                            if m_orig:
                                origen_raw = re.sub(r"\s+", " ", m_orig.group(2)).strip()
                                dest = re.sub(r"\s+", " ", m_orig.group(3)).strip()
                                dest = re.sub(r"\s*(DESTINO|Medio\s+de\s+Transporte|Medio)\s*$", "", dest, flags=re.IGNORECASE).strip()
                                dest = re.sub(r"\s*-\s*(Ruta|Declaración|Deducible|Etapa|Embalaje|Suma).*$", "", dest, flags=re.IGNORECASE).strip()
                                dest = re.sub(r"\s+(Ruta|Declaración|Deducible|Etapa|Embalaje|Suma|%|Descripción).*$", "", dest, flags=re.IGNORECASE).strip()
                                destino_raw = dest
                        # Fallback: buscar "DELHI-INDIA" / "LIMA-PERU" tipo pattern + "PERU..." hasta el "Medio"
                        if not origen_raw:
                            m2 = re.search(
                                r"([A-Z][A-ZÁÉÍÓÚÑ0-9]+\s*-\s*[A-ZÁÉÍÓÚÑ]{2,})\s+(PERU[^\n\r]{2,120}?)(?:\s{1,}-|Ruta|Declaración|Deducible|Etapa|Embalaje|Medio|$)",
                                txt, re.IGNORECASE,
                            )
                            if m2:
                                origen_raw = re.sub(r"\s+", " ", m2.group(1)).strip()
                                dest = re.sub(r"\s+", " ", m2.group(2)).strip()
                                dest = re.sub(r"\s*(DESTINO|Medio\s+de\s+Transporte|Medio)\s*$", "", dest, flags=re.IGNORECASE).strip()
                                dest = re.sub(r"\s*-\s*(Ruta|Declaración|Deducible|Etapa|Embalaje|Suma).*$", "", dest, flags=re.IGNORECASE).strip()
                                dest = re.sub(r"\s+(Ruta|Declaración|Deducible|Etapa|Embalaje|Suma|%|Descripción).*$", "", dest, flags=re.IGNORECASE).strip()
                                destino_raw = dest
                        # Fallback 2: línea de tabla explícita "Etapa F.Salida Origen Destino Medio..."
                        # Captura: <fecha> <CIUDAD-PAIS> <PERU-XXXX> resto=Medio
                        if not origen_raw or not destino_raw:
                            m3 = re.search(
                                r"Itinerario[\s\S]{0,500}?"
                                r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+"
                                r"([A-ZÁÉÍÓÚÑ0-9]{2,}(?:\s*[-\s]\s*[A-ZÁÉÍÓÚÑ0-9]{2,}){1,3})\s+"
                                r"(PERU[\w\s.\-]{1,80}?)(?:\s{2,}[A-ZÁÉÍÓÚÑ]|$)",
                                txt, re.IGNORECASE | re.MULTILINE,
                            )
                            if m3:
                                if not origen_raw:
                                    origen_raw = re.sub(r"\s+", " ", m3.group(2)).strip()
                                if not destino_raw:
                                    d = re.sub(r"\s+", " ", m3.group(3)).strip()
                                    d = re.sub(r"\s+(Ruta|Declaración|Deducible|Etapa|Embalaje|Suma|Medio|%|Descripción).*$", "", d, flags=re.IGNORECASE).strip()
                                    destino_raw = d
                                if itinerario_date == '':
                                    itinerario_date = m3.group(1).replace('-', '/').strip()
                        # Fallback 3: token CIUDAD-PAIS (QINGDAO-CHINA) + token siguiente que empiece por PERU
                        if not origen_raw or not destino_raw:
                            m4 = re.search(
                                r"([A-ZÁÉÍÓÚÑ]{3,}\s*-\s*[A-ZÁÉÍÓÚÑ]{2,})(?:\s+[A-ZÁÉÍÓÚÑ]{3,}\s*-\s*[A-ZÁÉÍÓÚÑ]{2,}){0,2}"
                                r"[\s\S]{0,80}?"
                                r"(PERU[\w.\-]{1,60}(?:\s+[A-ZÁÉÍÓÚÑ.]{1,30}){0,2})",
                                txt, re.IGNORECASE,
                            )
                            if m4:
                                if not origen_raw:
                                    origen_raw = re.sub(r"\s+", " ", m4.group(1)).strip()
                                if not destino_raw:
                                    destino_raw = re.sub(r"\s+", " ", m4.group(2)).strip()
                        # Asignar si no tenían valor (solo si se capturó algo útil)
                        if itinerario_date and not it.get('etd'):
                            it['etd'] = itinerario_date
                        if origen_raw and not it.get('origen'):
                            it['origen'] = origen_raw
                        if destino_raw and not it.get('destino'):
                            it['destino'] = destino_raw
                        # Fallback labels (siempre al final)
                        if not it.get('origen'):
                            mo = re.search(r"(?:Origen|Origin|Lugar\s+de\s+Salida)\s*[:：]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ0-9\-\.\s/]{2,90})", txt, re.IGNORECASE)
                            if mo: it['origen'] = mo.group(1).strip()
                        if not it.get('destino'):
                            md2 = re.search(r"(?:Destino|Destination|Lugar\s+de\s+Destino|Llegada)\s*[:：]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ0-9\-\.\s/]{2,90})", txt, re.IGNORECASE)
                            if md2: it['destino'] = md2.group(1).strip()
                        if not it.get('etd'):
                            mf = re.search(r"(?:F\.?\s*Salida|Fecha\s+de\s+Salida|ETD)\s*[:：]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", txt, re.IGNORECASE)
                            if mf: it['etd'] = mf.group(1).replace('-', '/').strip()
                        if not it.get('eta'):
                            meta = re.search(r"(?:F\.?\s*Llegada|Fecha\s+de\s+Llegada|ETA|Arribo)\s*[:：]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", txt, re.IGNORECASE)
                            if meta: it['eta'] = meta.group(1).replace('-', '/').strip()
                    origen_r = (it.get('origen') or '').strip()
                    ciudad_origen = ''
                    pais_origen = ''
                    if origen_r:
                        msp = re.split(r"\s*[-–—/]\s*", origen_r, maxsplit=1)
                        if len(msp) == 2:
                            ciudad_origen = msp[0].strip().upper()
                            pais_origen = msp[1].strip().upper()
                        else:
                            ciudad_origen = origen_r.upper()
                            pais_origen = origen_r.upper()
                    # Puerto de Embarque = ciudad (DELHI)
                    if not it.get('puerto_embarque'):
                        if ciudad_origen:
                            it['puerto_embarque'] = ciudad_origen
                        elif origen_r:
                            it['puerto_embarque'] = origen_r.upper()
                    # ASIGNACIÓN FINAL EXACTA (como usuario pide):
                    # ETD := fecha F.Salida (05/07/2026)   [ya está en it['etd'] si hubo match]
                    # ETA := pais Origen (INDIA)
                    if pais_origen:
                        it['eta'] = pais_origen
                    # Ruta (label "Ruta  Aereo")
                    if not it.get('ruta'):
                        mr = re.search(r"Ruta\s+([^\n\r]{2,90})", txt, re.IGNORECASE)
                        if mr:
                            it['ruta'] = mr.group(1).strip()
                        else:
                            mr2 = re.search(r"Medio\s+de\s+Transporte\s*[:：]?\s*([^\n\r]{1,90})", txt, re.IGNORECASE)
                            if mr2:
                                val = mr2.group(1).strip()
                                if val and val != '-': it['ruta'] = val

                    # --- E) DECLARACIÓN DE MERCADERÍAS: extraer embalaje por token standalone (no column-split) ---
                    if not it.get('descripcion') or not it.get('embalaje'):
                        # Descripción ya viene de "Mercadería : MOTO" (fallback)
                        # Embalaje: encontrar palabra ADECUADO/CARTON/MADERA/PALLET/CONTENEDOR etc. o Embalaje : XXXX
                        if not it.get('embalaje'):
                            me = re.search(r"(?:Embalaje|Packaging)\s*[:：]?\s*([A-ZÁÉÍÓÚÑa-záéíóúñ]{3,30})", txt, re.IGNORECASE)
                            if me:
                                em = me.group(1).strip()
                                if em.lower() not in {'-', 'n/a', 'ninguna', 'no'}: it['embalaje'] = em.upper()
                        if not it.get('embalaje'):
                            # buscar token standalone ADECUADO repetido (La Positiva lo muestra 2 veces)
                            m_stand = re.search(r"\b(ADECUADO|CART[ÓO]N|MADERA|PALLET|CONTENEDOR|CAJAS?|FIBERBOARD|STRETCH)\b", txt, re.IGNORECASE)
                            if m_stand:
                                it['embalaje'] = m_stand.group(1).upper()
                        if not it.get('descripcion'):
                            # "MOTO" / "AUTOPARTES" standalone después de mercadería
                            md3 = re.search(r"Declaraci[oó]n\s+de\s+Mercader[\s\S]{0,300}?\b(MOTO|AUTOPARTES|REPUESTOS|TEXTILES|ALIMENTOS|FARMACOS|QU[IÍ]MICOS|EQUIPOS?)\b", txt, re.IGNORECASE)
                            if md3: it['descripcion'] = md3.group(1).strip().upper()
        except Exception as e:
            LOG(f"[upload] campos_adicionales parse error: {e}")

        try:
            moneda_cuotas = ''
            if items_ui:
                moneda_cuotas = (items_ui[0].get('moneda') or '').strip()
            cuotas_extraidas = []
            prov_norm = str(detected_provider or '').lower()
            pdf_low = pdf_text_full.lower()
            
            # Prioridad: Si el texto dice POSITIVA, usar ese extractor
            if ('positiva' in prov_norm) or ('lpv' in prov_norm) or ('la positiva' in pdf_low):
                cuotas_extraidas = extract_cronograma_cuotas_positiva(pdf_text_full, moneda_cuotas)
            elif ('pacifico' in prov_norm) or ('pacifico' in pdf_low):
                cuotas_extraidas = extract_cronograma_cuotas_pacifico(pdf_text_full, moneda_cuotas)
            
            if not cuotas_extraidas:
                cuotas_extraidas = extract_cronograma_cuotas_general(pdf_text_full, moneda_cuotas)
            if cuotas_extraidas:
                LOG(f"[upload] cronograma detectado: {len(cuotas_extraidas)} cuota(s)")
                try:
                    LOG(f"[upload] cronograma primera cuota: {cuotas_extraidas[0]}")
                except Exception:
                    pass
                if len(items_ui) == 1:
                    items_ui[0]['cuotas'] = cuotas_extraidas
                    if not items_ui[0].get('fecha_vencimiento'):
                        items_ui[0]['fecha_vencimiento'] = cuotas_extraidas[0].get('fecha_vencimiento') or ''
                else:
                    poliza_to_cuotas = {}
                    for cuota in cuotas_extraidas:
                        poliza_to_cuotas.setdefault((items_ui[0].get('numero_poliza') or '').strip(), []).append(cuota)
                    for it in items_ui:
                        poliza_key = (it.get('numero_poliza') or '').strip()
                        if poliza_key in poliza_to_cuotas:
                            it['cuotas'] = poliza_to_cuotas[poliza_key]
                            if not it.get('fecha_vencimiento') and it['cuotas']:
                                it['fecha_vencimiento'] = it['cuotas'][0].get('fecha_vencimiento') or ''
            else:
                LOG("[upload] cronograma NO detectado")
        except Exception as e:
            LOG(f"[upload] cronograma parse error: {e}")
        LOG(f"[upload] fechas normalizadas: {[(x.get('ultimo_dia_pago'), x.get('vencimiento')) for x in items_ui]}")

        # Regla final: SIEMPRE recalcular fecha_vencimiento (pago) = fecha_emision + 15.
        # Nunca usar vencimiento (fin cobertura) como fecha de pago.
        try:
            for it in items_ui:
                fe_val = (it.get('fecha_emision') or '').strip()
                iv_val = (it.get('inicio_vigencia') or '').strip()
                udp_val = (it.get('ultimo_dia_pago') or '').strip()
                fvec_val = (it.get('fecha_vecimiento') or '').strip()
                pago_calc = udp_val or fvec_val or _add_days_ddmmyyyy(fe_val, 15) or _add_days_ddmmyyyy(iv_val, 15)
                if pago_calc:
                    it['fecha_vencimiento'] = pago_calc
                    if not fvec_val:
                        it['fecha_vecimiento'] = pago_calc
                    if not udp_val:
                        it['ultimo_dia_pago'] = pago_calc
        except Exception:
            pass

        # Dedupe por combinación clave y descartar muy vacíos
        unique = []
        seen = set()
        for it in items_ui:
            key = f"{it.get('numero_poliza') or ''}|{it.get('ramo') or ''}|{(it.get('ramos_producto') or it.get('producto') or '').strip()}"
            is_meaningful = any(it.get(k) for k in ['numero_poliza', 'colectivo_asegurado', 'moneda', 'prima_comercial_igv'])
            if not is_meaningful:
                LOG(f"[upload] descartado item vacío: {it}")
                continue
            if key in seen:
                LOG(f"[upload] item duplicado (clave={key}) descartado")
                continue
            seen.add(key)
            unique.append(it)

        provider_final = detected_provider
        try:
            if not provider_final:
                if 'rimac' in pdf_low:
                    provider_final = 'rimac'
                elif ('pacifico' in pdf_low) or ('pacífico' in pdf_low):
                    provider_final = 'pacifico'
                elif 'sanitas' in pdf_low:
                    provider_final = 'sanitas'
                elif ('la positiva' in pdf_low) or ('positiva' in pdf_low) or ('lpv' in pdf_low):
                    provider_final = 'positiva'
                elif 'mapfre' in pdf_low:
                    provider_final = 'mapfre'
                elif ('qualitas' in pdf_low) or ('quálitas' in pdf_low):
                    provider_final = 'qualitas'
                elif issuer:
                    provider_final = issuer
        except Exception:
            provider_final = detected_provider

        return {'filename': filename, 'items': unique, 'debug': debug_logs, 'provider': provider_final}, 200

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
    # Derivar Prima Neta desde Prima Comercial en el fallback (fields)
    try:
        pc = extracted.get('prima_comercial') or extracted.get('prima_total') or extracted.get('monto')
        if pc:
            val = float(str(pc).replace(',', '.').replace(' ', ''))
            extracted['prima_neta'] = f"{(val / 1.03):.2f}"
    except Exception:
        pass

    # NUEVO: si solo vino prima_neta, derive prima_comercial
    try:
        pn = extracted.get('prima_neta')
        if pn and not extracted.get('prima_comercial'):
            val = float(str(pn).replace(',', '.').replace(' ', ''))
            extracted['prima_comercial'] = f"{(val * 1.03):.2f}"
    except Exception:
        pass

    # Cálculo de ultimo_dia_pago deshabilitado
    # try:
    #     if not extracted.get('ultimo_dia_pago'):
    #         try:
    #             cand = extracted.get('fecha_emision') or extracted.get('inicio_vigencia')
    #             calc = _add_days_ddmmyyyy(cand, 15)
    #             if calc:
    #                 extracted['ultimo_dia_pago'] = calc
    #                 extracted['fecha_vencimiento'] = calc
    #                 extracted['fecha_vecimiento'] = calc
    #         except Exception:
    #             pass
    #         try:
    #             cand = extracted.get('fecha_emision') or extracted.get('inicio_vigencia')
    #             calc = _add_days_ddmmyyyy(cand, 15)
    #             if calc:
    #                 extracted['fecha_vencimiento'] = calc
    #                 extracted['fecha_vecimiento'] = calc
    #         except Exception:
    #             pass
    # except Exception:
    #     pass

    # Ajuste de fechas:
    # PRIMERO: fecha de pago (vence pago) = ultimo_dia_pago o fecha_emision + 15.
    # LUEGO (fallback solo si no existe fecha de pago): fecha_vencimiento = fin de vigencia.
    try:
        fe_val_fb = (extracted.get('fecha_emision') or '').strip()
        iv_val_fb = (extracted.get('inicio_vigencia') or '').strip()
        udp_val_fb = (extracted.get('ultimo_dia_pago') or '').strip()
        fvec_val_fb = (extracted.get('fecha_vecimiento') or '').strip()
        pago_calc_fb = udp_val_fb or fvec_val_fb or _add_days_ddmmyyyy(fe_val_fb, 15) or _add_days_ddmmyyyy(iv_val_fb, 15)
        if pago_calc_fb:
            extracted['fecha_vencimiento'] = pago_calc_fb
            if not fvec_val_fb:
                extracted['fecha_vecimiento'] = pago_calc_fb
            if not udp_val_fb:
                extracted['ultimo_dia_pago'] = pago_calc_fb
        else:
            # Fallback extremo: si no hay fecha de pago, usar fin de vigencia
            if not extracted.get('fecha_vencimiento'):
                fv = (extracted.get('vencimiento')
                      or extracted.get('vigencia_hasta')
                      or extracted.get('hasta')
                      or extracted.get('expiracion'))
                if fv:
                    extracted['fecha_vencimiento'] = fv
    except Exception:
        pass

    provider_final = detected_provider
    try:
        pdf_text_full = _extract_text_fitz(save_path, password=pdf_password) or ''
        pdf_low = pdf_text_full.lower()
        if not provider_final:
            if 'rimac' in pdf_low:
                provider_final = 'rimac'
            elif ('pacifico' in pdf_low) or ('pacífico' in pdf_low):
                provider_final = 'pacifico'
            elif 'sanitas' in pdf_low:
                provider_final = 'sanitas'
            elif ('la positiva' in pdf_low) or ('positiva' in pdf_low) or ('lpv' in pdf_low):
                provider_final = 'positiva'
            elif 'mapfre' in pdf_low:
                provider_final = 'mapfre'
            elif issuer:
                provider_final = issuer
        prov_norm = str(provider_final or '').lower()
        moneda_cuotas = (extracted.get('moneda') or '').strip()
        cuotas_extraidas = []

        if ('positiva' in prov_norm) or ('lpv' in prov_norm) or ('la positiva' in pdf_low):
            cuotas_extraidas = extract_cronograma_cuotas_positiva(pdf_text_full, moneda_cuotas)
        elif ('pacifico' in prov_norm) or ('pacifico' in pdf_low):
            cuotas_extraidas = extract_cronograma_cuotas_pacifico(pdf_text_full, moneda_cuotas)
        elif ('mapfre' in prov_norm) or ('mapfre' in pdf_low):
            try:
                from controllers.cuotas.VariosCuponGeneralesMapfre import extract_cronograma_cuotas_mapfre
                cuotas_extraidas = extract_cronograma_cuotas_mapfre(pdf_text_full, moneda_cuotas)
            except Exception:
                cuotas_extraidas = []
        if not cuotas_extraidas:
            cuotas_extraidas = extract_cronograma_cuotas_general(pdf_text_full, moneda_cuotas)

        if cuotas_extraidas:
            extracted['cuotas'] = cuotas_extraidas
            if not extracted.get('fecha_vencimiento'):
                extracted['fecha_vencimiento'] = cuotas_extraidas[0].get('fecha_vencimiento') or ''
            if not extracted.get('fecha_vecimiento'):
                extracted['fecha_vecimiento'] = cuotas_extraidas[0].get('fecha_vencimiento') or ''
    except Exception:
        pass

    return {'filename': filename, 'fields': extracted, 'debug': debug_logs, 'provider': provider_final}, 200


@bp.route('/clientes/add', methods=['POST'])
@require_permission(can_create, response_mode='json')
def clientes_add():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    # Manejar upload de archivo si existe
    data = {}
    if request.files or request.form:
         # Si es multipart/form-data, los campos están en form
         data = request.form.to_dict()
    else:
         # Si es JSON puro
         data = request.get_json(silent=True) or {}

    pdf_file = request.files.get('pdf_file')
    if pdf_file and pdf_file.filename:
         from werkzeug.utils import secure_filename
         import os
         import time
         
         filename = secure_filename(pdf_file.filename)
         # Usar timestamp para evitar colisiones
         ts = int(time.time())
         filename = f"{ts}_{filename}"
         
         upload_folder = os.path.join(current_app.root_path, 'uploads', 'clientes')
         os.makedirs(upload_folder, exist_ok=True)
         
         save_path = os.path.join(upload_folder, filename)
         pdf_file.save(save_path)
         
         data['pdf_path'] = f"clientes/{filename}"

    from controllers.clientes.addcliente import save_cliente
    res = save_cliente(data)
    status = 200 if res.get('ok') else 400
    return res, status


@bp.route('/solicitudes/add', methods=['POST'])
@require_permission(can_create, response_mode='json')
def solicitudes_add():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = request.form.to_dict()
    usuario_actual = session.get('user', 'SISTEMA')

    from controllers.solicitudes.solicitudes import save_solicitud, add_archivo
    res = save_solicitud(data, usuario_actual)
    if not res.get('ok'):
        return res, 400

    archivos = [f for f in request.files.getlist('archivos') if f and f.filename]
    if archivos:
        import time
        upload_folder = os.path.join(current_app.root_path, 'uploads', 'solicitudes')
        os.makedirs(upload_folder, exist_ok=True)
        for f in archivos:
            filename = secure_filename(f.filename)
            filename = f"{res['id']}_{int(time.time())}_{filename}"
            f.save(os.path.join(upload_folder, filename))
            add_archivo(res['id'], f"solicitudes/{filename}", f.filename, usuario_actual)

    if res.get('para'):
        from utils.notify import notify_solicitud
        template_params = {
            'numero_ti': res['numero_ti'],
            'asunto': res['asunto'],
            'tipo_operacion': data.get('tipo_operacion', ''),
            'fecha_solicitud': data.get('fecha_solicitud', ''),
            'prioridad': data.get('prioridad', ''),
            'medio': data.get('medio', ''),
            'ubicacion': data.get('ubicacion', ''),
            'gestor': data.get('gestor', ''),
            'cliente': data.get('cliente', ''),
            'compania': data.get('compania', ''),
            'ramo': data.get('ramo', ''),
            'poliza': data.get('poliza', ''),
            'numero_tramite_cia': data.get('numero_tramite_cia', ''),
            'subagente': data.get('subagente', ''),
            'ejecutivo': data.get('ejecutivo', ''),
            'motivo': data.get('motivo', ''),
            'contenido': data.get('contenido', ''),
            'registrado_por': usuario_actual,
            'message': (
                f"Solicitud {res['asunto']}\n"
                f"Tipo: {data.get('tipo_operacion', '')}\n"
                f"Cliente: {data.get('cliente', '')}\n"
                f"Motivo: {data.get('motivo', '')}\n\n"
                f"{data.get('contenido', '')}"
            ),
        }
        notify_solicitud(res['para'], res['cc'], template_params)

    return res, 200


@bp.route('/solicitudes/<int:idSolicitud>/anular', methods=['POST'])
@require_permission(can_delete, response_mode='json')
def solicitudes_anular(idSolicitud):
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.solicitudes.solicitudes import anular_solicitud
    res = anular_solicitud(idSolicitud)
    status = 200 if res.get('ok') else 400
    return res, status


@bp.route('/api/subagentes', methods=['GET'])
def api_get_subagentes():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.subagente import get_subagentes_abreviaciones
    subagentes = get_subagentes_abreviaciones()
    return {'ok': True, 'subagentes': subagentes}, 200


@bp.route('/api/ubigeos/departamentos', methods=['GET'])
def api_get_departamentos():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.maestros.ubigeos import get_departamentos
    departamentos = get_departamentos()
    return {'ok': True, 'departamentos': departamentos}, 200


@bp.route('/api/ubigeos/provincias', methods=['GET'])
def api_get_provincias():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    departamento = (request.args.get('departamento') or '').strip()
    if not departamento:
        return {'ok': False, 'errors': ['El parametro departamento es obligatorio']}, 400

    from controllers.maestros.ubigeos import get_provincias
    provincias = get_provincias(departamento)
    return {'ok': True, 'provincias': provincias}, 200


@bp.route('/api/ubigeos/distritos', methods=['GET'])
def api_get_distritos():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    departamento = (request.args.get('departamento') or '').strip()
    provincia = (request.args.get('provincia') or '').strip()
    if not departamento or not provincia:
        return {'ok': False, 'errors': ['Los parametros departamento y provincia son obligatorios']}, 400

    from controllers.maestros.ubigeos import get_distritos
    distritos = get_distritos(departamento, provincia)
    return {'ok': True, 'distritos': distritos}, 200


@bp.route('/api/clientes/documento-lookup', methods=['GET'])
def api_clientes_documento_lookup():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    from controllers.clientes.documento_lookup import consultar_documento_route
    return consultar_documento_route()

# ---- Ajustadores API ----
@bp.route('/ajustadores/list', methods=['GET'])
def ajustadores_list():
    """Devuelve la lista de ajustadores en formato JSON"""
    from controllers.ajustadores.ajustadores import get_ajustadores
    try:
#soporte para paginacion
        try:
            page = int(request.args.get('page') or 1)
        except Exception:
            page = 1
        per_page_arg = request.args.get('per_page')
        per_page = None
        if per_page_arg and str(per_page_arg).lower() != 'all':
            try:
                per_page = int(per_page_arg)
            except Exception:
                per_page = 20

        rows = get_ajustadores() or []
        total = len(rows)

        # Default per_page if not provided
        if per_page is None:
            per_page = 20

        # If explicit 'all' requested, return full set
        if per_page_arg and str(per_page_arg).lower() == 'all':
            return jsonify({'ok': True, 'rows': rows, 'total': total, 'page': 1, 'per_page': 'all', 'pages': 1}), 200

        pages = max(1, (total + per_page - 1) // per_page) if per_page > 0 else 1
        page = max(1, min(page, pages)) if pages > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        sliced = rows[start:end]

        return jsonify({'ok': True, 'rows': sliced, 'total': total, 'page': page, 'per_page': per_page, 'pages': pages}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/ajustadores/add', methods=['POST'])
def ajustadores_add():
    """Inserta un ajustador (requiere sesión)."""
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401

    data = request.get_json(silent=True) or {}
    # Inyectar usuario si se requiere en la lógica del SP
    data['usuario'] = session.get('user')

    from controllers.ajustadores.ajustadores import insert_ajustador
    res = insert_ajustador(data)
    status = 200 if res.get('ok') else 400
    return res, status

@bp.route('/api/clientes/buscar', methods=['GET'])
def api_buscar_clientes():
    """Busca clientes por nombre, RUC o DNI"""
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.estado_cuenta import buscar_clientes
    search_term = request.args.get('q', '').strip()

    if search_term and len(search_term) < 2:
        return jsonify({'ok': False, 'message': 'Mínimo 2 caracteres'}), 400

    clientes = buscar_clientes(search_term)
    return jsonify({'ok': True, 'clientes': clientes}), 200


@bp.route('/api/financiamiento-grupal/options', methods=['GET'])
def api_financiamiento_grupal_options():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    from controllers.financiamiento_grupal.financiacion_grupal import get_financiamiento_grupal_form_options
    data = get_financiamiento_grupal_form_options()
    return jsonify({'ok': True, **data}), 200


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>', methods=['GET'])
def api_financiamiento_grupal_detail(financiamiento_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    from controllers.financiamiento_grupal.financiacion_grupal import get_financiamiento_grupal_item
    result = get_financiamiento_grupal_item(financiamiento_id)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/create', methods=['POST'])
def api_financiamiento_grupal_create():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json(silent=True) or {}
    saved_abs_path = ''
    if not payload:
        payload = request.form.to_dict() or {}
    file = request.files.get('convenio_pdf')
    if file and file.filename:
        try:
            import time

            original_filename = file.filename
            safe_name = secure_filename(original_filename)
            disk_filename = f"{int(time.time())}_fg_{safe_name}"
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'financiamiento_grupal')
            os.makedirs(upload_folder, exist_ok=True)
            saved_abs_path = os.path.join(upload_folder, disk_filename)
            file.save(saved_abs_path)
            payload['documento_ruta_archivo'] = f"financiamiento_grupal/{disk_filename}"
            payload['documento_nombre_original'] = original_filename
        except Exception as exc:
            return jsonify({'ok': False, 'error': f'No se pudo guardar el PDF del financiamiento: {exc}'}), 400
    payload['usuario'] = session.get('user') or ''

    from controllers.financiamiento_grupal.financiacion_grupal import insert_financiamiento_grupal
    result = insert_financiamiento_grupal(payload)
    if not result.get('ok') and saved_abs_path:
        try:
            if os.path.exists(saved_abs_path):
                os.remove(saved_abs_path)
        except Exception:
            pass
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>/update', methods=['POST'])
def api_financiamiento_grupal_update(financiamiento_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json(silent=True) or {}
    saved_abs_path = ''
    if not payload:
        payload = request.form.to_dict() or {}
    file = request.files.get('convenio_pdf')
    if file and file.filename:
        try:
            import time

            original_filename = file.filename
            safe_name = secure_filename(original_filename)
            disk_filename = f"{int(time.time())}_fg_{safe_name}"
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'financiamiento_grupal')
            os.makedirs(upload_folder, exist_ok=True)
            saved_abs_path = os.path.join(upload_folder, disk_filename)
            file.save(saved_abs_path)
            payload['documento_ruta_archivo'] = f"financiamiento_grupal/{disk_filename}"
            payload['documento_nombre_original'] = original_filename
        except Exception as exc:
            return jsonify({'ok': False, 'error': f'No se pudo guardar el PDF del financiamiento: {exc}'}), 400
    payload['usuario'] = session.get('user') or ''

    from controllers.financiamiento_grupal.financiacion_grupal import update_financiamiento_grupal
    result = update_financiamiento_grupal(financiamiento_id, payload)
    if not result.get('ok') and saved_abs_path:
        try:
            if os.path.exists(saved_abs_path):
                os.remove(saved_abs_path)
        except Exception:
            pass
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>/remove', methods=['DELETE'])
def api_financiamiento_grupal_remove(financiamiento_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    from controllers.financiamiento_grupal.financiacion_grupal import remove_financiamiento_grupal
    result = remove_financiamiento_grupal(financiamiento_id)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>/avisos', methods=['GET'])
def api_financiamiento_grupal_avisos_list(financiamiento_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    from controllers.financiamiento_grupal.financiacion_grupal import list_financiamiento_grupal_avisos
    result = list_financiamiento_grupal_avisos(financiamiento_id)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>/avisos/candidatos', methods=['GET'])
def api_financiamiento_grupal_avisos_candidates(financiamiento_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    from controllers.financiamiento_grupal.financiacion_grupal import list_financiamiento_grupal_avisos_candidates
    result = list_financiamiento_grupal_avisos_candidates(financiamiento_id)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>/avisos/add', methods=['POST'])
def api_financiamiento_grupal_avisos_add(financiamiento_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    payload = request.get_json(silent=True) or {}
    poliza_id = payload.get('poliza_id')
    from controllers.financiamiento_grupal.financiacion_grupal import add_financiamiento_grupal_aviso
    result = add_financiamiento_grupal_aviso(financiamiento_id, poliza_id)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/api/financiamiento-grupal/<int:financiamiento_id>/avisos/remove/<int:item_id>', methods=['DELETE'])
def api_financiamiento_grupal_avisos_remove(financiamiento_id, item_id):
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    from controllers.financiamiento_grupal.financiacion_grupal import remove_financiamiento_grupal_aviso
    result = remove_financiamiento_grupal_aviso(financiamiento_id, item_id)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@bp.route('/clientes/extract-pdf', methods=['POST'])
def clientes_extract_pdf():
    """Endpoint para extraer información de cliente desde un PDF."""
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    if 'pdf_file' not in request.files:
        return {'ok': False, 'errors': ['No se envió ningún archivo PDF']}, 400

    file = request.files['pdf_file']

    if file.filename == '':
        return {'ok': False, 'errors': ['Nombre de archivo vacío']}, 400

    if not file.filename.lower().endswith('.pdf'):
        return {'ok': False, 'errors': ['El archivo debe ser un PDF']}, 400

    try:
        # Guardar archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_' + filename)
        file.save(temp_path)

        # Procesar PDF
        from controllers.clientes.pdf_extractor import process_pdf_file
        result = process_pdf_file(temp_path)

        # Eliminar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass

        if result.get('ok'):
            return {'ok': True, 'data': result.get('data', {}), 'debug': result.get('raw_text', '')}, 200
        else:
            return {'ok': False, 'errors': [result.get('error', 'Error procesando PDF')]}, 400

    except Exception as e:
        current_app.logger.error(f'Error en extract-pdf: {e}')
        return {'ok': False, 'errors': [str(e)]}, 500


# =====================================================
# RUTAS PARA CARGA MASIVA DE SOAT
# =====================================================
@bp.route('/carga-masiva-soat', methods=['GET'])
def carga_masiva_soat():
    """Renderiza la página de carga masiva de SOAT"""
    if 'user' not in session:
        return redirect(url_for('login'))

    from controllers.soat.carga_masiva import get_soat_upload_history, get_ultima_fecha_emision_soat
    fechas = get_ultima_fecha_emision_soat()
    historial_cargas = get_soat_upload_history(current_app.config['UPLOAD_FOLDER'], limit=20)

    return render_template(
        'view/carga_masiva_soat.html',
        page='carga-masiva-soat',
        ultima_fecha_emision_bd=fechas.get('ultima_fecha_emision_bd'),
        cargar_desde_sugerido=fechas.get('cargar_desde_sugerido'),
        historial_cargas=historial_cargas
    )


@bp.route('/carga-masiva-soat/upload', methods=['POST'])
def carga_masiva_soat_upload():
    """Procesa el archivo Excel de carga masiva"""
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    if 'excel_file' not in request.files:
        return {'ok': False, 'errors': ['No se envió ningún archivo']}, 400

    file = request.files['excel_file']

    if file.filename == '':
        return {'ok': False, 'errors': ['Nombre de archivo vacío']}, 400

    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return {'ok': False, 'errors': ['El archivo debe ser un Excel (.xlsx o .xls)']}, 400

    # Obtener flag de preview (default: False)
    preview_str = request.form.get('preview', 'false')
    preview = preview_str.lower() == 'true'

    try:
        # Guardar archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_soat_' + filename)
        file.save(temp_path)

        # Procesar Excel
        from controllers.soat.carga_masiva import process_soat_excel, get_soat_upload_history, get_ultima_fecha_emision_soat, save_soat_upload_history
        result = process_soat_excel(temp_path, session.get('user'), preview=preview)
        historial_cargas = save_soat_upload_history(
            upload_folder=current_app.config['UPLOAD_FOLDER'],
            source_file_path=temp_path,
            original_filename=file.filename,
            usuario=session.get('user'),
            preview=preview,
            result=result,
        )

        # Eliminar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass

        if result.get('ok'):
            fechas = get_ultima_fecha_emision_soat()
            return {
                'ok': True,
                'clientes_nuevos': result.get('clientes_nuevos', 0),
                'clientes_existentes': result.get('clientes_existentes', 0),
                'polizas_insertadas': result.get('polizas_insertadas', 0),
                'polizas_anuladas': result.get('polizas_anuladas', 0),
                'polizas_existentes': result.get('polizas_existentes', 0),
                'polizas_recibo_existentes': result.get('polizas_recibo_existentes', 0),
                'cuotas_insertadas': result.get('cuotas_insertadas', 0),
                'cuotas_existentes': result.get('cuotas_existentes', 0),
                'polizas_insertadas_soles': result.get('polizas_insertadas_soles', 0),
                'polizas_insertadas_dolares': result.get('polizas_insertadas_dolares', 0),
                'polizas_anuladas_soles': result.get('polizas_anuladas_soles', 0),
                'polizas_anuladas_dolares': result.get('polizas_anuladas_dolares', 0),
                'cuotas_insertadas_soles': result.get('cuotas_insertadas_soles', 0),
                'cuotas_insertadas_dolares': result.get('cuotas_insertadas_dolares', 0),
                'cuotas_importe_soles': result.get('cuotas_importe_soles', 0),
                'cuotas_importe_dolares': result.get('cuotas_importe_dolares', 0),
                'filas_excel_soles': result.get('filas_excel_soles', 0),
                'filas_excel_dolares': result.get('filas_excel_dolares', 0),
                'importe_excel_soles': result.get('importe_excel_soles', 0),
                'importe_excel_dolares': result.get('importe_excel_dolares', 0),
                'polizas_moneda_actualizadas': result.get('polizas_moneda_actualizadas', 0),
                'cuotas_moneda_actualizadas': result.get('cuotas_moneda_actualizadas', 0),
                'polizas_activo_actualizadas': result.get('polizas_activo_actualizadas', 0),
                'cuotas_activo_actualizadas': result.get('cuotas_activo_actualizadas', 0),
                'fecha_emision_excel_min': result.get('fecha_emision_excel_min'),
                'fecha_emision_excel_max': result.get('fecha_emision_excel_max'),
                'ultima_fecha_emision_bd': fechas.get('ultima_fecha_emision_bd'),
                'cargar_desde_sugerido': fechas.get('cargar_desde_sugerido'),
                'historial_cargas': historial_cargas,
                'errors': result.get('errors', [])
            }, 200
        else:
            return {
                'ok': False,
                'errors': result.get('errors', ['Error desconocido']),
                'historial_cargas': historial_cargas
            }, 400

    except Exception as e:
        current_app.logger.error(f'Error en carga masiva SOAT: {e}')
        return {'ok': False, 'errors': [str(e)]}, 500


@bp.route('/carga-masiva-soat/plantilla', methods=['GET'])
@require_permission(lambda r: r in [Roles.BROKER, Roles.OPERADOR], response_mode='redirect')
def descargar_plantilla_soat():
    """Descarga la plantilla de Excel para carga masiva"""
    if 'user' not in session:
        return redirect(url_for('login'))

    # Directorio de plantillas
    plantillas_dir = os.path.join(current_app.root_path, 'static', 'plantillas')

    return send_from_directory(
        plantillas_dir,
        'plantilla_carga_masiva_soat.xls',
        as_attachment=True
    )


@bp.route('/carga-masiva-soat/historial/<filename>', methods=['GET'])
@require_permission(lambda r: r in [Roles.BROKER, Roles.OPERADOR], response_mode='redirect')
def descargar_historial_carga_soat(filename):
    if 'user' not in session:
        return redirect(url_for('login'))

    safe_name = os.path.basename(secure_filename(filename))
    history_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'soat_historial', 'files')
    return send_from_directory(history_dir, safe_name, as_attachment=True, download_name=safe_name)

# =====================================================
# FIN RUTAS CARGA MASIVA
# =====================================================



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
        'subagente': payload.get('subagente') or payload.get('subAgente'),
        # 'motivo': payload.get('motivo'),
        'ramos_producto': payload.get('ramos_producto'),
        'idCliente': payload.get('idCliente')
    }
    session['selected_cliente'] = selected
    return {'ok': True}, 200


@bp.route('/notificaciones/poliza/<int:poliza_id>/abrir', methods=['GET'])
def open_polizas_from_notification(poliza_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("""
            SELECT
                c.idCliente,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS razon_social,
                c.tipo_documento,
                c.numero_documento,
                c.telefono,
                COALESCE(c.subagente, p.sub_agente, '') AS subagente
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
            WHERE p.idPoliza = %s AND p.activo = 1 AND p.anulado = 0
            LIMIT 1
        """, (poliza_id,))
        row = cur.fetchone() or {}
        cur.close()
        cnx.close()

        if not row:
            return redirect(url_for('main.menu_page', page='listado-poliza'))

        session['selected_cliente'] = {
            'idCliente':   row.get('idCliente'),
            'nombre':      row.get('razon_social'),
            'razon_social': row.get('razon_social'),
            'tipo_doc':    row.get('tipo_documento'),
            'n_doc':       row.get('numero_documento'),
            'tel':         row.get('telefono'),
            'subagente':   row.get('subagente'),
        }
        return redirect(url_for('main.menu_page', page='polizas', highlight=poliza_id))
    except Exception as e:
        print(f"[notifications.open_polizas] {e}")
        return redirect(url_for('main.menu_page', page='listado-poliza'))

@bp.route('/api/polizas/search', methods=['GET'])
def api_polizas_search():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401

    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'general')
    filter_type = request.args.get('filter', '').strip()

    # Filtros rápidos: vigentes / vencen-mes
    if filter_type in ('vigentes', 'vencen-mes'):
        from controllers.polizas_search import filter_polizas_rapido
        data = filter_polizas_rapido(filter_type)
        return jsonify({'ok': True, 'rows': data['rows']})

    from controllers.polizas_search import search_polizas_global
    data = search_polizas_global(query, search_type)

    return jsonify({'ok': True, 'rows': data['rows']})

@bp.route('/api/polizas/cliente-from-poliza', methods=['GET'])
def api_cliente_from_poliza():
    if 'user' not in session:
        return {'ok': False, 'error': 'Unauthorized'}, 401

    poliza_id = request.args.get('id', '').strip()
    if not poliza_id:
        return jsonify({'ok': False, 'error': 'Falta id'}), 400

    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("""
            SELECT
                c.idCliente,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS razon_social,
                COALESCE(c.tipo_documento, '') AS tipo_doc,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR),
                    c.numero_documento
                ) AS n_doc,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.telefono), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.telefono, @SIS_KEY) AS CHAR),
                    c.telefono
                ) AS tel,
                COALESCE(c.subagente, p.sub_agente, '') AS subagente,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                    p.poliza
                ) AS numero_poliza
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
            WHERE p.idPoliza = %s AND p.activo = 1
            LIMIT 1
        """, (poliza_id,))
        row = cur.fetchone()
        cur.close()
        cnx.close()

        if not row:
            return jsonify({'ok': False, 'error': 'Póliza no encontrada'}), 404

        session['selected_cliente'] = {
            'idCliente': row['idCliente'],
            'nombre': row['razon_social'],
            'razon_social': row['razon_social'],
            'tipo_doc': row['tipo_doc'],
            'n_doc': row['n_doc'],
            'tel': row['tel'],
            'subagente': row['subagente'],
        }

        # Guardar contexto de navegación para los botones "Volver" en Añadir Póliza
        nav_ctx = session.get('anadir_poliza_nav') or {}
        _pol = (row.get('numero_poliza') or '').strip()
        if _pol:
            nav_ctx['poliza'] = _pol
        nav_ctx['return_to'] = 'listado-poliza'
        nav_ctx['return_from_poliza_id'] = poliza_id
        session['anadir_poliza_nav'] = nav_ctx

        return jsonify({'ok': True, 'redirect': '/menu/anadir-poliza'})
    except Exception as e:
        print(f'[api_cliente_from_poliza] {e}')
        return jsonify({'ok': False, 'error': 'Error interno'}), 500


@bp.route('/api/comisiones/default', methods=['GET'])
def api_comisiones_default():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    cia = (request.args.get('cia') or '').strip()
    producto = (request.args.get('producto') or '').strip()
    ramo = (request.args.get('ramo') or '').strip()
    ramos_producto = (request.args.get('ramos_producto') or '').strip()

    def cia_to_col(cia_txt: str | None) -> str | None:
        if not cia_txt:
            return None
        s = (str(cia_txt) or '').strip().lower()
        if 'qualitas' in s or 'quálitas' in s:
            return 'qualitas'
        if 'grandia' in s:
            return 'grandia_eps'
        if 'mapfre' in s:
            return 'mapfre'
        if 'pacif' in s:
            return 'pacifico'
        if 'sanitas' in s:
            return 'sanitas'
        if 'protecta' in s:
            return 'protecta'
        if 'crecer' in s:
            return 'crecer'
        if 'positiva' in s or 'lpv' in s or 'la positiva' in s:
            if 'eps' in s:
                return 'pos_eps'
            if 'vida' in s:
                return 'pos_vsr'
            return 'pos_sr'
        if 'ohio' in s:
            return 'ohio_natural'
        return None

    col = cia_to_col(cia)
    # Ajuste: si es LPV/Positiva, utilizar ramos_producto/ramo/producto para elegir columna
    try:
        s = (cia or '').strip().lower()
        is_lpv = ('lpv' in s) or ('positiva' in s) or ('la positiva' in s)
        if is_lpv:
            cand_join = ' '.join([(producto or ''), (ramos_producto or ''), (ramo or '')]).strip().lower()
            if ('salud' in cand_join) or ('eps' in cand_join):
                col = 'pos_eps'
            elif 'vida' in cand_join:
                col = 'pos_vsr'
            elif 'pens' in cand_join:
                col = 'pos_sr'
    except Exception:
        pass
    if not col:
        return {'ok': True, 'pct': None}

    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        candidates = [producto, ramos_producto, ramo]
        pct_val = None
        for cand in candidates:
            val = (cand or '').strip().upper()
            if not val:
                continue
            cur.execute(
                """
                SELECT
                  pos_eps, pos_vsr, pos_sr, pacifico, sanitas, protecta, mapfre, crecer, ohio_natural, grandia_eps, qualitas, factor
                FROM comisiones_temp
                WHERE UPPER(producto_abrev) = %s
                   OR UPPER(producto) = %s
                   OR UPPER(ramo_abreviacion) = %s
                   OR UPPER(ramo_nombre) = %s
                LIMIT 1
                """,
                (val, val, val, val)
            )
            rowc = cur.fetchone()
            if rowc:
                pct = rowc.get(col)
                if pct is not None:
                    pct_val = float(pct)
                    break
                fac = rowc.get('factor')
                if fac is not None:
                    pct_val = float(fac)
                    break
        cur.close()
        cnx.close()
        return {'ok': True, 'pct': pct_val}
    except Exception as e:
        try:
            cur.close()
        except Exception:
            pass
        try:
            cnx.close()
        except Exception:
            pass
        return {'ok': False, 'errors': [str(e)]}, 500


# Listar todas las comisiones (para modal en añadir póliza)
@bp.route('/api/comisiones/list', methods=['GET'])
def api_comisiones_list():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    try:
        from controllers.maestros.comisiones import get_comisiones
        rows = get_comisiones() or []
        return {'ok': True, 'rows': rows}
    except Exception as e:
        return {'ok': False, 'error': str(e)}, 500


# Refrescar comisiones desde Excel (RamoProducto.xlsx)
@bp.route('/api/comisiones/refresh', methods=['POST'])
def api_comisiones_refresh():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    try:
        # Importar utilidades de lectura/carga desde el módulo de Excel
        from ramoproductoexcel import (
            _load_dataframe,
            _upsert_ramos_y_productos,
            _insert_comisiones_temp,
            _refrescar_comisiones,
        )
        from models.db import get_connection

        df = _load_dataframe()
        if df is None or df.empty:
            return {'ok': False, 'errors': ['Hoja RamoProducto vacía o no encontrada']}, 400

        cnx = get_connection()
        try:
            # Asegurar productos y refrescar comisiones_temp/comisiones
            _upsert_ramos_y_productos(cnx, df)
            _insert_comisiones_temp(cnx, df)
            _refrescar_comisiones(cnx)
        finally:
            try:
                cnx.close()
            except Exception:
                pass
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'errors': [str(e)]}, 500


@bp.route('/api/maestros/comisiones', methods=['POST'])
@require_permission(can_access_maestros, response_mode='json')
def api_maestros_comisiones_save():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    mode = (data.get('mode') or '').lower()
    row_id = data.get('id')

    def _to_decimal(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return v
        s = str(v).strip().replace(',', '.')
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None

    ramo_nombre = (data.get('ramo_nombre') or '').strip()
    ramo_abreviacion = (data.get('ramo_abreviacion') or '').strip() or None
    ramo_codigo = (data.get('ramo_codigo') or '').strip() or None
    ramo_grupo = (data.get('ramo_grupo') or '').strip() or None
    producto = (data.get('producto') or '').strip()
    producto_abrev = (data.get('producto_abrev') or '').strip() or None
    producto_codigo = (data.get('producto_codigo') or '').strip() or None
    producto_grupo = (data.get('producto_grupo') or '').strip() or None
    pos_eps = _to_decimal(data.get('pos_eps'))
    pos_vsr = _to_decimal(data.get('pos_vsr'))
    pos_sr = _to_decimal(data.get('pos_sr'))
    pacifico = _to_decimal(data.get('pacifico'))
    sanitas = _to_decimal(data.get('sanitas'))
    protecta = _to_decimal(data.get('protecta'))
    mapfre = _to_decimal(data.get('mapfre'))
    crecer = _to_decimal(data.get('crecer'))
    ohio_natural = _to_decimal(data.get('ohio_natural'))
    grandia_eps = _to_decimal(data.get('grandia_eps'))
    qualitas = _to_decimal(data.get('qualitas'))
    factor = _to_decimal(data.get('factor'))

    if not ramo_nombre or not producto:
        return jsonify({'ok': False, 'error': 'Ramo y producto son requeridos'}), 400

    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()
        try:
            if mode == 'editar' and row_id:
                cur_prev = cnx.cursor(dictionary=True)
                cur_prev.execute(
                    """
                    SELECT ramo_nombre, producto
                    FROM comisiones_temp
                    WHERE id=%s
                    """,
                    (row_id,),
                )
                prev = cur_prev.fetchone()
                cur_prev.close()
                prev_ramo = (prev.get('ramo_nombre') if prev else None) or ramo_nombre
                prev_producto = (prev.get('producto') if prev else None) or producto
                cur.execute(
                    """
                    UPDATE ramos
                    SET nombre=%s,
                        abreviacion=%s,
                        codigo=%s,
                        grupo=%s
                    WHERE nombre=%s
                    """,
                    (ramo_nombre, ramo_abreviacion, ramo_codigo, ramo_grupo, prev_ramo),
                )
                cur.execute(
                    "SELECT idRamo FROM ramos WHERE nombre=%s",
                    (ramo_nombre,),
                )
                r = cur.fetchone()
                ramo_id = r[0] if r else None
                if ramo_id:
                    cur.execute(
                        """
                        UPDATE productos
                        SET nombre=%s,
                            codigo=%s,
                            grupo=%s
                        WHERE idRamo=%s AND nombre=%s
                        """,
                        (producto, producto_codigo, producto_grupo, ramo_id, prev_producto),
                    )
                cur.execute(
                    """
                    UPDATE comisiones_temp
                    SET ramo_nombre=%s,
                        ramo_abreviacion=%s,
                        ramo_codigo=%s,
                        ramo_grupo=%s,
                        producto=%s,
                        producto_abrev=%s,
                        producto_codigo=%s,
                        producto_grupo=%s,
                        pos_eps=%s,
                        pos_vsr=%s,
                        pos_sr=%s,
                        pacifico=%s,
                        sanitas=%s,
                        protecta=%s,
                        mapfre=%s,
                        crecer=%s,
                        ohio_natural=%s,
                        grandia_eps=%s,
                        qualitas=%s,
                        factor=%s
                    WHERE id=%s
                    """,
                    (
                        ramo_nombre,
                        ramo_abreviacion,
                        ramo_codigo,
                        ramo_grupo,
                        producto,
                        producto_abrev,
                        producto_codigo,
                        producto_grupo,
                        pos_eps,
                        pos_vsr,
                        pos_sr,
                        pacifico,
                        sanitas,
                        protecta,
                        mapfre,
                        crecer,
                        ohio_natural,
                        grandia_eps,
                        qualitas,
                        factor,
                        row_id,
                    ),
                )
            else:
                ramo_id = None
                cur.execute(
                    """
                    INSERT INTO ramos (nombre, abreviacion, codigo, grupo, estado)
                    VALUES (%s, %s, %s, %s, 'Activo')
                    ON DUPLICATE KEY UPDATE
                        abreviacion = VALUES(abreviacion),
                        codigo = COALESCE(VALUES(codigo), codigo),
                        grupo = COALESCE(VALUES(grupo), grupo),
                        estado = VALUES(estado),
                        idRamo = LAST_INSERT_ID(idRamo)
                    """,
                    (ramo_nombre, ramo_abreviacion, ramo_codigo, ramo_grupo),
                )
                cur.execute("SELECT LAST_INSERT_ID()")
                r = cur.fetchone()
                if r:
                    ramo_id = r[0]
                if ramo_id and producto:
                    cur.execute(
                        """
                        INSERT INTO productos (idRamo, nombre, codigo, grupo)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            codigo = VALUES(codigo),
                            grupo = VALUES(grupo),
                            id_producto = LAST_INSERT_ID(id_producto)
                        """,
                        (ramo_id, producto, producto_codigo, producto_grupo),
                    )
                cur.execute(
                    """
                    INSERT INTO comisiones_temp (
                        ramo_nombre,
                        ramo_abreviacion,
                        ramo_codigo,
                        ramo_grupo,
                        producto,
                        producto_abrev,
                        producto_codigo,
                        producto_grupo,
                        pos_eps,
                        pos_vsr,
                        pos_sr,
                        pacifico,
                        sanitas,
                        protecta,
                        mapfre,
                        crecer,
                        ohio_natural,
                        grandia_eps,
                        qualitas,
                        factor
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        ramo_nombre,
                        ramo_abreviacion,
                        ramo_codigo,
                        ramo_grupo,
                        producto,
                        producto_abrev,
                        producto_codigo,
                        producto_grupo,
                        pos_eps,
                        pos_vsr,
                        pos_sr,
                        pacifico,
                        sanitas,
                        protecta,
                        mapfre,
                        crecer,
                        ohio_natural,
                        grandia_eps,
                        qualitas,
                        factor,
                    ),
                )
                row_id = cur.lastrowid
            cnx.commit()
            return jsonify({'ok': True, 'id': int(row_id) if row_id else None})
        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if cnx:
                    cnx.close()
            except Exception:
                pass
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/polizas/save', methods=['POST'])
@require_permission(can_create_poliza, response_mode='json')
def polizas_save():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    # Support both JSON and multipart/form-data (for attachments)
    if request.files or request.form.get('json_data'):
        import json
        try:
            payload = json.loads(request.form.get('json_data', '{}'))
        except:
            payload = {}
        anexos = request.files.getlist('anexos')
        facturas = request.files.getlist('facturas')
        facturas_by_index = {}
        facturas_by_cuota = {}
        try:
            for key in request.files.keys():
                if key.startswith('facturas_cuota_'):
                    try:
                        _, _, row_idx, cuota_idx = key.split('_', 3)
                        row_idx = int(row_idx)
                        cuota_idx = int(cuota_idx)
                        facturas_by_cuota.setdefault(row_idx, {})[cuota_idx] = request.files.getlist(key)
                    except Exception:
                        pass
                elif key.startswith('facturas_'):
                    try:
                        idx = int(key.split('_', 1)[1])
                        facturas_by_index[idx] = request.files.getlist(key)
                    except Exception:
                        pass
        except Exception:
            facturas_by_index = {}
            facturas_by_cuota = {}
    else:
        payload = request.get_json(silent=True) or {}
        anexos = []
        facturas = []
        facturas_by_index = {}
        facturas_by_cuota = {}

    items = payload.get('items') or []
    selected = payload.get('selected') or session.get('selected_cliente') or {}

    # Sincroniza la sesión con el subagente seleccionado (y demás campos)
    prev = session.get('selected_cliente') or {}
    if selected:
        session['selected_cliente'] = {**prev, **selected}

    # Mover el PDF de temp/ a polizas/ ahora que el usuario confirmó guardar
    pdf_filename = (selected or {}).get('pdf_filename')
    if pdf_filename:
        import shutil as _shutil
        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads'))
        temp_path = os.path.join(upload_folder, 'temp', pdf_filename)
        polizas_folder = os.path.join(upload_folder, 'polizas')
        os.makedirs(polizas_folder, exist_ok=True)
        dest_path = os.path.join(polizas_folder, pdf_filename)
        if os.path.exists(temp_path) and not os.path.exists(dest_path):
            try:
                _shutil.move(temp_path, dest_path)
                print(f"[polizas_save] PDF movido de temp/ a polizas/: {pdf_filename}")
            except Exception as _e:
                print(f"[polizas_save] No se pudo mover el PDF: {_e}")
        elif os.path.exists(temp_path) and os.path.exists(dest_path):
            # Ya existe en destino, solo eliminar el temp
            try:
                os.remove(temp_path)
            except Exception:
                pass

    from controllers.addPoliza import save_polizas
    res = save_polizas(
        items,
        selected,
        anexos=anexos,
        facturas=facturas,
        facturas_by_index=facturas_by_index,
        facturas_by_cuota=facturas_by_cuota,
    )
    if not res.get('ok'):
        current_app.logger.error('polizas_save error: %s', res.get('errors'))
    status = 200 if res.get('ok') else 400
    return res, status


def poliza_owner_from_request(*args, **kwargs):
    try:
        data_tmp = request.get_json(silent=True) or request.form.to_dict()
        pid = data_tmp.get('idPoliza') or data_tmp.get('idPrima') or data_tmp.get('id')
        if not pid:
            return None
        from controllers.polizas import get_poliza_owner_by_id
        return get_poliza_owner_by_id(pid)
    except Exception:
        return None


def cliente_owner_from_request(*args, **kwargs):
    try:
        data_tmp = request.get_json(silent=True) or request.form.to_dict()
        cid = data_tmp.get('idCliente') or kwargs.get('idCliente')
        if not cid:
            return None
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT subagente, usuario_registro FROM clientes WHERE idCliente=%s LIMIT 1", (cid,))
        row = cur.fetchone() or {}
        cur.close()
        cnx.close()
        return row.get('subagente') or row.get('usuario_registro')
    except Exception:
        return None


def siniestro_owner_from_request(*args, **kwargs):
    try:
        sid = kwargs.get('id')
        if not sid:
            data_tmp = request.get_json(silent=True) or request.form.to_dict()
            sid = data_tmp.get('id')
        if not sid:
            return None
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("""
            SELECT s.usuario_registro, p.sub_agente
            FROM siniestros s
            LEFT JOIN polizas p ON p.poliza = s.poliza
            WHERE s.id = %s
            LIMIT 1
        """, (sid,))
        row = cur.fetchone() or {}
        cur.close()
        cnx.close()
        return row.get('usuario_registro') or row.get('sub_agente')
    except Exception:
        return None


@bp.route('/polizas/update', methods=['POST'])
@require_permission(can_edit, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def polizas_update():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401


    data = request.get_json(silent=True) or request.form.to_dict()
    from controllers.editar_poliza import update_poliza
    res = update_poliza(data)
    status = 200 if res.get('ok') else 400
    return res, status

# NUEVO: Endpoint para actualizar Primas (que en realidad son pólizas)
@bp.route('/primas/update', methods=['POST'])
@require_permission(can_edit, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def primas_update():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = request.get_json(silent=True) or request.form.to_dict()
    # Mapeo de campos de Primas a Pólizas
    # La UI envía idPrima, pero el controlador espera idPoliza
    if 'idPrima' in data:
        data['idPoliza'] = data.pop('idPrima')

    pid_pre = data.get('idPoliza')
    pid_int_pre = None
    try:
        pid_int_pre = int(pid_pre) if pid_pre is not None else None
    except Exception:
        pid_int_pre = None

    old_importe = None
    if pid_int_pre is not None:
        try:
            cnx_pre = get_connection()
            cur_pre = cnx_pre.cursor()
            cur_pre.execute(
                "SELECT prima_comercial_igv FROM polizas WHERE idPoliza = %s LIMIT 1",
                (pid_int_pre,),
            )
            row_pre = cur_pre.fetchone()
            if row_pre:
                old_importe = row_pre[0]
            cur_pre.close()
            cnx_pre.close()
        except Exception:
            old_importe = None

    # Reutilizamos el controlador de pólizas ya que comparten tabla
    from controllers.editar_poliza import update_poliza
    res = update_poliza(data)
    status = 200 if res.get('ok') else 400
    if res.get('ok'):
        poliza = (data.get('poliza') or '').strip()
        cupon = (data.get('recibo') or data.get('aviso') or '').strip()
        if cupon.lower() in ('none', 'null'):
            cupon = ''
        importe = data.get('prima_comercial_igv')
        pid = data.get('idPoliza')
        user_session = session.get('user')
        if isinstance(user_session, dict):
            usuario = user_session.get('username') or user_session.get('user') or user_session.get('name')
        else:
            usuario = user_session

        def _to_bool(v):
            if isinstance(v, bool):
                return v
            if v is None:
                return False
            s = str(v).strip().lower()
            return s in ('1', 'true', 't', 'yes', 'y', 'on')

        def _parse_num(v):
            if v is None:
                return None
            try:
                s = str(v).replace(',', '').strip()
                if not s:
                    return None
                return float(s)
            except Exception:
                return None

        should_update_cuotas = None
        if 'update_cuotas' in data:
            should_update_cuotas = _to_bool(data.get('update_cuotas'))
        else:
            old_n = _parse_num(old_importe)
            new_n = _parse_num(importe)
            if old_n is not None and new_n is not None:
                should_update_cuotas = abs(old_n - new_n) >= 0.005
            else:
                should_update_cuotas = False

        if pid and importe and poliza and cupon and should_update_cuotas:
            from controllers.editar_poliza import _parse_date
            from controllers.cuotas.cuotas import update_cuota_cupon
            try:
                pid_int = int(pid)
            except Exception:
                pid_int = None
            if pid_int is None:
                return res, status
            vig_desde = _parse_date(data.get('vig_desde')) if data.get('vig_desde') else None
            vig_hasta = _parse_date(data.get('vig_hasta')) if data.get('vig_hasta') else None
            if vig_desde and vig_hasta and str(vig_desde) > str(vig_hasta):
                vig_desde, vig_hasta = vig_hasta, vig_desde
            try:
                cnx = get_connection()
                cur = cnx.cursor()
                row = None
                cur.execute(
                    """
                    SELECT idCuota, poliza_id
                    FROM cuotas
                    WHERE activo = 1
                      AND poliza_id = %s
                      AND TRIM(
                            COALESCE(
                                CONVERT(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) USING utf8mb4),
                                CONVERT(AES_DECRYPT(cupon, @SIS_KEY) USING utf8mb4),
                                cupon
                            )
                          ) COLLATE utf8mb4_0900_ai_ci = (TRIM(%s) COLLATE utf8mb4_0900_ai_ci)
                    ORDER BY fecha_vencimiento ASC, idCuota ASC
                    LIMIT 1
                    """,
                    (pid_int, cupon.strip()),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        """
                        SELECT idCuota, poliza_id
                        FROM cuotas
                        WHERE activo = 1
                          AND (poliza_id IS NULL OR poliza_id = 0)
                          AND TRIM(
                                COALESCE(
                                    CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4),
                                    CONVERT(AES_DECRYPT(poliza, @SIS_KEY) USING utf8mb4),
                                    poliza
                                )
                              ) COLLATE utf8mb4_0900_ai_ci = (TRIM(%s) COLLATE utf8mb4_0900_ai_ci)
                          AND TRIM(
                                COALESCE(
                                    CONVERT(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) USING utf8mb4),
                                    CONVERT(AES_DECRYPT(cupon, @SIS_KEY) USING utf8mb4),
                                    cupon
                                )
                              ) COLLATE utf8mb4_0900_ai_ci = (TRIM(%s) COLLATE utf8mb4_0900_ai_ci)
                          AND (
                            %s IS NULL OR %s IS NULL
                            OR (fecha_vencimiento >= %s AND fecha_vencimiento <= %s)
                          )
                        ORDER BY fecha_vencimiento ASC, idCuota ASC
                        LIMIT 1
                        """,
                        (poliza, cupon.strip(), vig_desde, vig_hasta, vig_desde, vig_hasta),
                    )
                    row = cur.fetchone()
                cur.close()
                cuota_id = row[0] if row and row[0] else None
                cuota_poliza_id = row[1] if row and len(row) > 1 else None
                if cuota_id and (cuota_poliza_id is None or int(cuota_poliza_id or 0) == 0):
                    try:
                        cur2 = cnx.cursor()
                        cur2.execute(
                            "UPDATE cuotas SET poliza_id = %s WHERE idCuota = %s AND (poliza_id IS NULL OR poliza_id = 0)",
                            (pid_int, cuota_id),
                        )
                        cur2.close()
                        cnx.commit()
                    except Exception:
                        try:
                            cnx.rollback()
                        except Exception:
                            pass
                cnx.close()
                if cuota_id:
                    payload = {
                        'idCuota': cuota_id,
                        'importe': importe,
                        'usuario': usuario,
                        'cupon': cupon.strip(),
                    }
                    update_cuota_cupon(payload)
            except Exception:
                pass
    return res, status

@bp.route('/primas/delete', methods=['POST'])
@require_permission(can_delete, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def primas_delete():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    from controllers.primas.primas import delete_prima_route
    return delete_prima_route()

@bp.route('/api/polizas/renovar', methods=['POST'])
@require_permission(can_create_poliza, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def polizas_renovar():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    data = request.get_json(silent=True) or {}

    # Construir payload para update_poliza
    # Se mantienen los datos financieros existentes (no se resetean a 0)
    update_payload = {
        'idPoliza': data.get('idPoliza'),
        'cia': data.get('compania'),
        'ramos_producto': data.get('producto'),
        'poliza': data.get('poliza'),
        'vig_hasta': data.get('vig_fin'),
        'ramo': data.get('ramo'),
        'motivo': data.get('tipo_vigencia'), # mapeado a 'motivo'
        'vig_desde': data.get('vig_inicio'),
        'fecha_emision': data.get('fecha_emision'),

        # Al no enviar claves de primas, el controlador usará los valores actuales de la BD
    }

    from controllers.editar_poliza import update_poliza
    res = update_poliza(update_payload)
    status = 200 if res.get('ok') else 400
    return res, status


# Util: permitir archivos
def allowed_file(filename: str) -> bool:
    ext = (filename or '').rsplit('.', 1)[-1].lower()
    return ext in {'pdf', 'jpg', 'jpeg', 'png'}

# -------- Extracción de texto (PyMuPDF y fallback) --------
def _clean_cid_text(text: str | None) -> str:
    """Convierte (cid:N) → chr(N) Latin-1. Limpia texto de PyPDF2 con fuentes no embebidas."""
    if not text:
        return text or ""
    return re.sub(r"\(cid:(\d+)\)", lambda m: chr(int(m.group(1))), text)

def _looks_like_bad_pdf_text(text: str | None) -> bool:
    if not text:
        return True
    sample = (text or "")[:4000]
    if not sample.strip():
        return True
    control_count = sum(1 for ch in sample if ord(ch) < 32 and ch not in "\n\r\t")
    cid_count = sample.lower().count("(cid:")
    printable_count = sum(1 for ch in sample if ch.isalnum())
    ratio_control = control_count / max(len(sample), 1)
    ratio_printable = printable_count / max(len(sample), 1)
    return ratio_control > 0.10 or cid_count >= 3 or ratio_printable < 0.20

def _configure_tesseract_cmd(pytesseract_module) -> None:
    try:
        current_cmd = getattr(pytesseract_module.pytesseract, "tesseract_cmd", "") or ""
        if current_cmd and os.path.exists(current_cmd):
            return
    except Exception:
        pass

    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
    ]
    for candidate in candidate_paths:
        if candidate and os.path.exists(candidate):
            pytesseract_module.pytesseract.tesseract_cmd = candidate
            return

def _extract_text_ocr_fitz(path: str, password: str | None = None) -> str:
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image

        _configure_tesseract_cmd(pytesseract)

        text_chunks = []
        with fitz.open(path) as doc:
            try:
                if getattr(doc, "is_encrypted", False):
                    if password:
                        ok = doc.authenticate(password)
                        if not ok:
                            return ""
                    else:
                        return ""
            except Exception:
                pass
            for page in doc:
                # Usa escala moderada y grises para bajar bastante el tiempo de OCR.
                pix = page.get_pixmap(dpi=0, colorspace=fitz.csGRAY, alpha=False)
                img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                text_chunks.append(pytesseract.image_to_string(img, lang="spa+eng") or "")
        return "\n".join(text_chunks)
    except Exception:
        return ""

def _extract_text_fitz(path: str, password: str | None = None) -> str:
    try:
        import fitz  # PyMuPDF
        text_chunks = []
        with fitz.open(path) as doc:
            try:
                if getattr(doc, "is_encrypted", False):
                    if password:
                        ok = doc.authenticate(password)
                        if not ok:
                            return ""
                    else:
                        return ""
            except Exception:
                pass
            for page in doc:
                text_chunks.append(page.get_text())
        return "\n".join(text_chunks)
    except Exception:
        return _extract_text_pypdf2(path, password)

def _extract_text_pages_fitz(path: str, password: str | None = None) -> list[str]:
    try:
        import fitz  # PyMuPDF
        pages: list[str] = []
        with fitz.open(path) as doc:
            try:
                if getattr(doc, "is_encrypted", False):
                    if password:
                        ok = doc.authenticate(password)
                        if not ok:
                            return []
                    else:
                        return []
            except Exception:
                pass
            for page in doc:
                pages.append(page.get_text() or "")
        return pages
    except Exception:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return [(p.extract_text() or "") for p in pdf.pages]
        except Exception:
            return []

def _extract_text_pypdf2(path: str, password: str | None = None) -> str:
    try:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                parts = []
                for page in pdf.pages:
                    txt = page.extract_text() or ""
                    parts.append(txt)
                if parts:
                    return "\n".join(parts)
        except Exception:
            pass
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        try:
            if getattr(reader, "is_encrypted", False):
                if password:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        return ""
                else:
                    return ""
        except Exception:
            pass
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
        if not numero_proforma:
            try:
                from controllers.addPositivaGenerales import extract_proforma_numero_positiva
                numero_proforma = extract_proforma_numero_positiva(blk)
            except Exception:
                pass
        # Soporta “Póliza Nº:” con número en la siguiente línea
        poliza_nro = (
            _find(r"P[oó]liza\s*N(?:ro|°|º)?\s*[:\n]\s*([0-9A-Z\-]+)", blk)
            or _find(r"P[oó]liza\s*N[°º]\s*[:\n]\s*([0-9A-Z\-]+)", blk)
            or _find(r"P[oó]liza\s*Nro\s*[:\n]\s*([0-9A-Z\-]+)", blk)
            or _find(r"P[oó]liza\s*N°\s*[:\n]\s*([0-9A-Z\-]+)", blk)
        )
        contrato_nro = _find(r"Contrato\s+Nro\s*:\s*([0-9A-Z\-]+)", blk)
        # Vigencias: soporta “Vigencia-Inicio:” y “Término:” (guion normal/en dash/em dash, “:” o “：”, fecha en misma o siguiente línea)
        vig_desde = (
            _find(r"Vigencia Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
            or _find(r"Vigencia[-\s]?Inicio\s*[:\n]\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        )
        vig_hasta = (
            _find(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
            or _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
            or _find(r"T[ée]rmino\s*[:\n]\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        )
        moneda = None
        try:
            from controllers.addPositivaGenerales import extract_moneda_positiva
            moneda = extract_moneda_positiva(blk)
        except Exception:
            moneda = _find(r"Moneda\s*:\s*([A-Za-z$]+)", blk)
        
        emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)
        ramo = _find(r"Ramo\s*:\s*(.+)", blk)
        contratante = _find(r"Contratante\s*:\s*(.+)", blk)
        asegurado = _find(r"Asegurado\s*:\s*(.+)", blk)
        
        # Fallback para Asegurado en Datos del Asegurado / Nombre o Razón Social
        if not asegurado or 'Datos' in asegurado:
             m_aseg = re.search(r"Datos\s+del\s+Asegurado[\s\S]{0,100}?Nombre\s+o\s+Raz[oó]n\s+Social\s*:\s*(.+)", blk, re.IGNORECASE)
             if m_aseg:
                 asegurado = m_aseg.group(1).strip()

        forma_pago = _find(r"Forma de Pago\s*:\s*(.+)", blk)
        ultimo_dia = _find(r"[ÚU]ltimo d[ií]a de Pago\s*:?[\s]*([0-9]{2}/[0-9]{2}/[0-9]{4})", blk)

        prima_total = _money(_find(r"Prima Total\s*(?:S\/?|US\$)?\s*([0-9\.,]+)", blk))
        igv_val = _money(_find(r"Impuesto General a las Ventas\s*(?:S\/?|US\$)?\s*([0-9\.,]+)", blk))
        sobrevivencia = _money(_find(r"Sobrevivencia.*?(?:S\/?|US\$)?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        costos_emision = _money(_find(r"Costos?\s+de\s+Emisi[oó]n.*?(?:S\/?|US\$)?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        igv_val = igv_val or _money(_find(r"IGV.*?(?:S\/?|US\$)?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))
        total_plus_igv_line = _money(_find(r"Prima\s+Comercial\s*\+\s*IGV.*?(?:S\/?|US\$)?\s*([0-9\.,]+)", blk, flags=re.IGNORECASE | re.DOTALL))

        prima_comercial = _money(_find(r"Prima Comercial\s*(?:S\/?|US\$)?\s*([0-9\.,]+)", blk)) or prima_total
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

def _quarantine_parser_failure(path: str, provider: str, reason: str, details: dict | None = None, text_head: str | None = None) -> str | None:
    try:
        base = os.path.join(current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'uploads')), 'quarantine', provider or 'unknown')
        os.makedirs(base, exist_ok=True)
        with open(path, 'rb') as f:
            data = f.read()
        h = hashlib.sha256(data).hexdigest()[:12]
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        safe_name = secure_filename(os.path.basename(path)) or 'archivo.pdf'
        dest_name = f"{ts}_{h}_{safe_name}"
        dest_path = os.path.join(base, dest_name)
        if not os.path.exists(dest_path):
            shutil.copy2(path, dest_path)
        meta = {
            'provider': provider,
            'reason': reason,
            'details': details or {},
            'saved_at': ts,
            'source_name': os.path.basename(path),
            'sha256_12': h,
        }
        if text_head:
            meta['text_head'] = text_head[:600]
        with open(dest_path + '.meta.json', 'w', encoding='utf-8') as mf:
            json.dump(meta, mf, ensure_ascii=False, indent=2)
        return dest_path
    except Exception as e:
        try:
            current_app.logger.error(f"[parser-quarantine] error: {e}")
        except Exception:
            print(f"[parser-quarantine] error: {e}")
        return None

def _missing_fields(item: dict | None, required: list[str]) -> list[str]:
    if not item:
        return required
    missing = []
    for key in required:
        val = (item.get(key) or '').strip() if isinstance(item.get(key), str) else item.get(key)
        if not val:
            missing.append(key)
    return missing

def _load_mapfre_sap_parser():
    import importlib.util

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser_path = os.path.join(project_root, 'controllers', 'addPolizaMapfreS-A-P.py')
    spec = importlib.util.spec_from_file_location('controllers.addPolizaMapfreSAP_hyphen', parser_path)
    if not spec or not spec.loader:
        raise ImportError(f"No se pudo cargar el parser Mapfre SAP: {parser_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser = getattr(module, 'parse_mapfre_poliza_sap', None)
    if not callable(parser):
        raise AttributeError("No se encontro `parse_mapfre_poliza_sap` en addPolizaMapfreS-A-P.py")
    return parser

def parse_pdf_items_provider(path: str, issuer: str | None = None, pdf_password: str | None = None):
    text = _extract_text_fitz(path, password=pdf_password)
    used_ocr = False
    pypdf2_fallback = None
    if _looks_like_bad_pdf_text(text):
        raw_pypdf2 = _extract_text_pypdf2(path, password=pdf_password)
        text = _clean_cid_text(raw_pypdf2)
        pypdf2_fallback = text
        print(f"[DEBUG TEXT HEAD PYPDF2] {text[:600]!r}")
    else:
        print(f"[DEBUG TEXT HEAD] {text[:600]!r}")
    if _looks_like_bad_pdf_text(text):
        ocr_text = _extract_text_ocr_fitz(path, password=pdf_password)
        print(f"[DEBUG TEXT HEAD OCR] {ocr_text[:600]!r}")
        if ocr_text and ocr_text.strip():
            text = ocr_text
            used_ocr = True
        elif pypdf2_fallback and pypdf2_fallback.strip():
            # OCR vacío: usar texto PyPDF2 limpiado (CIDs ya resueltos)
            text = pypdf2_fallback
            print("[DEBUG] OCR vacío, usando PyPDF2 limpiado")

    if used_ocr:
        page_texts = [text] if text and text.strip() else []
    else:
        page_texts = _extract_text_pages_fitz(path, password=pdf_password)
        page_texts = [p for p in (page_texts or []) if p and p.strip()]

    t = text.lower()
    prov = (issuer or "").strip().lower() or None
    low = (text or "").lower()

    # Normalizar slugs del selector si vino algo como 'rimac-seguros'
    if prov:
        try:
            pnorm = re.sub(r"[^a-z]", "", prov)
        except Exception:
            pnorm = prov.replace("-", "").replace("_", "")
        if "rimac" in pnorm:
            prov = "rimac"
        elif "qualitas" in pnorm:
            prov = "qualitas"
        elif "mapfre" in pnorm and "vidaley" in pnorm:
            prov = "mapfre-vida-ley"
        elif "pacifico" in pnorm and "salud" in pnorm:
            prov = "pacifico_salud"
        elif "grandia" in pnorm and ("eps" in pnorm or "salud" in pnorm):
            prov = "grandia-eps"
        elif "positiva" in pnorm and "vidaley" in pnorm:
            prov = "lpv-vida-ley"
        elif "positiva" in pnorm and "pension" in pnorm:
            prov = "lpv-pension"
        elif "positiva" in pnorm and "salud" in pnorm:
            prov = "lpv-salud"

    if prov:
        try:
            pnorm = re.sub(r"[^a-z]", "", prov)
        except Exception:
            pnorm = prov.replace("-", "").replace("_", "")
        if "rimac" in pnorm:
            prov = "rimac"
        elif "qualitas" in pnorm:
            prov = "qualitas"
        elif "mapfre" in pnorm and "vidaley" in pnorm:
            prov = "mapfre-vida-ley"
        elif "pacifico" in pnorm and "salud" in pnorm:
            prov = "pacifico_salud"
        elif "grandia" in pnorm and ("eps" in pnorm or "salud" in pnorm):
            prov = "grandia-eps"
        elif "positiva" in pnorm and "vidaley" in pnorm:
            prov = "lpv-vida-ley"
        elif "positiva" in pnorm and "pension" in pnorm:
            prov = "lpv-pension"
        elif "positiva" in pnorm and "salud" in pnorm:
            prov = "lpv-salud"

    if prov == "rimac":
        strong_rimac = (
            ("rimac seguros" in low) or ("rímac seguros" in low) or ("web vehiculos" in low)
            or re.search(r"\bNro\.?\s*[:：]?\s*\d{3,6}\s*[-–—]\s*\d{5,12}\b", text, re.IGNORECASE)
            or re.search(r"pol[ií]za\s*\d{3,6}\s*[-–—]\s*\d{5,12}", text, re.IGNORECASE)
        )
        if not strong_rimac:
            prov = None

    if not prov:
        # detección básica por contenido
        # Primero: Vida Ley de Mapfre por patrones de contenido
        if re.search(r"\bmapfre\b", t) and (
            re.search(r"\bvida\s+ley\b", t) or
            re.search(r"decreto\s+legislativo\s*n?\s*688", t) or
            "d.l.688" in t
        ):
            prov = "mapfre-vida-ley"
        # NUEVO: Mapfre Equipo de Contratistas (y Responsabilidad Civil / Hidrocarburos)
        elif re.search(r"\bmapfre\b", t) and (
            re.search(r"equipo\s+de\s+contratistas", t) or
            re.search(r"responsabilidad\s+civil", t) or
            re.search(r"hidrocarburos", t)
        ):
            prov = "mapfre-equipo-contratistas"

        # NUEVO: Mapfre Vehicular (Detection relaxed)
        elif ("mapfre" in t or "20418896915" in t) and (
            re.search(r"seguro\s+vehicular", t) or
            re.search(r"vehicular\s+full", t) or
            "suplemento de seguro vehicular" in t
        ):
            print("DEBUG: DETECTADO MAPFRE VEHICULAR")
            prov = "mapfre-vehicular"

        elif re.search(r"\bmapfre\b", t) and re.search(r"\bsuplemento\s+de\b", t) and not re.search(r"seguro\s+vehicular", t):
            prov = "mapfre-endoso-generales"

        elif "la positiva" in t:
            prov = "positiva"
        elif "mapfre-vida-ley" in t:
            prov = "mapfre-vida-ley"

        elif "mapfre" in t or re.search(r"vencimiento\s+de\s+aplicaci[oó]n", t) or re.search(r"inicio\s+de\s+vigencia\s+aplicaci[oó]n", t):
            prov = "mapfre"
        elif "lpv-vida-ley" in t:
            prov = "lpv-vida-ley"
        elif "lpv-pension" in t:
            prov = "lpv-pension"
        elif "lpv-salud" in t:
            prov = "lpv-salud"
        elif ("qualitas" in t) or ("quálitas" in t):
            prov = "qualitas"
        # QUITADO: no detectar 'lpv-vida-ley', 'lpv-pension', 'lpv-salud' por contenido del PDF
        # Estos slugs deben venir desde el 'issuer' del cliente (UI).
        # NUEVO: preferir Crecer si aparece, aunque también figure 'sanitasperu'
        elif "crecer seguros" in t or re.search(r"\bcrecer\b", t):
            prov = "crecer"
        # NUEVO: Grandia EPS (prioridad sobre Protecta, porque puede contener links de protectasecurity.pe)
        elif re.search(r"\bgrandia\b", t) and re.search(r"\beps\b", t):
            prov = "grandia-eps"
        # NUEVO: detectar Protecta ANTES que Sanitas (por pasarela de pago Sanitas en PDFs de Protecta)
        # Se agregan RUC y Código SBS de Protecta para mayor robustez
        elif (
            ("protectasecurity.pe" in t)
            or ("protecta security" in t)
            or ("20517207331" in t)
            or ("vi2097700027" in t)
            or re.search(r"\bprotecta\b\s+security\b", t)
        ):
            prov = "protecta"
        # NUEVO: detectar Protecta por título específico (SCTR Pensiones)
        elif "condiciones particulares" in t and "pensiones" in t and (("protectasecurity.pe" in t) or ("protecta security" in t) or ("20517207331" in t) or ("vi2097700027" in t)):
            prov = "protecta"
        elif (
            re.search(r"\bcontrato\s+no\.", t)
            and "anexo" in t
            and re.search(r"denominaci[oó]n\s+social", t)
            and "consolidado de primas" in t
            and "prima neta" in t
            and "prima total" in t
        ):
            prov = "grandia-eps"
        elif "sanitas" in t:
            prov = "sanitas"
        elif (re.search(r"\br[íi]mac\b", t) or "rimac seguros" in t or "rímac seguros" in t) or re.search(r"\bNro\.?\s*[:：]?\s*\d{3,6}\s*[-–—]\s*\d{5,12}\b", t) or re.search(r"pol[ií]za\s*\d{3,6}\s*-\s*\d{5,12}", t):
            prov = "rimac"
        elif "pacifico" in t or "pacífico" in t:
                prov = "pacifico"
        elif "vida-ley-crecer" in t:
                prov = "vida-ley-crecer"
        else:
                prov = ""


    # Backstop: corregir proveedor si el contenido lo indica claramente
    # Evita ruta equivocada cuando el UI envió 'proctecta/protecta/positiva' erróneamente.
    # Priorizar La Positiva si aparece claramente
    is_positiva_strong = ("la positiva" in low) or ("positiva seguros" in low)

    is_positiva_acc_personales = bool(
        is_positiva_strong
        and (
            re.search(r"p[óo]liza\s+de\s+seguro\s+de\s+accidentes\s+personales", low)
            or re.search(r"\baccidentes\s+personales\b", low)
        )
    )
    if is_positiva_acc_personales and prov != "vida-ley-crecer":
        prov = "positiva"
        print("[provider] override: La Positiva Accidentes Personales -> prov=positiva")
    
    if prov in ('proctecta', 'protecta', 'positiva', 'sanitas', None) and not is_positiva_strong:
        if ("grandia" in low and "eps" in low):
            prov = 'grandia-eps'
        elif ('pacifico' in low or 'pacífico' in low):
            prov = 'pacifico'
        elif ("protectasecurity.pe" in t) or ("protecta security" in t) or ("20517207331" in t) or ("vi2097700027" in t) or re.search(r"\bprotecta\b\s+security\b", t):
             prov = 'protecta'

    # NUEVO: Detectar Crecer Seguros explícitamente (prioridad sobre Positiva/Sanitas)
    # Respetar si ya viene como vida-ley-crecer
    if prov != "vida-ley-crecer" and ("crecer seguros" in t or re.search(r"\bcrecer\b", t)):
        # Si detectamos Vida Ley en el contenido, forzamos el proveedor correcto
        if "vida ley" in t or "decreto legislativo" in t:
             prov = "vida-ley-crecer"
        else:
             prov = "crecer"

    # Forzar Rimac si aparecen señales claras del encabezado Rimac Generales
    # (ej.: "Web Vehiculos" y "Póliza #### - #######"), incluso si antes se clasificó erróneamente
    if (
        (not is_positiva_acc_personales)
        and (
            (re.search(r"\br[íi]mac\b", t) or "rimac seguros" in t or "rímac seguros" in t or re.search(r"pol[ií]za\s*\d{2,6}\s*[-–—]\s*\d{5,12}", t))
            and (re.search(r"\bContratante\b", t, re.IGNORECASE) or re.search(r"\bNro\.?\b", t, re.IGNORECASE))
        )
    ):
        prov = "rimac"

    # NUEVO: si vino 'pacifico' o 'positiva' desde UI pero el contenido dice 'sanitas', fuerza Sanitas
    # Se añade guardia para NO cambiar a Sanitas si realmente es Protecta (que puede tener links a sanitasperu.com)
    is_protecta_likely = (
        "protecta" in t or
        "protecta security" in t or
        re.search(r"p\s*r\s*o\s*t\s*e\s*c\s*t\s*a", t) or
        "20517207331" in t or
        "vi2097700027" in t
    )

    if prov in ('pacifico', 'positiva', 'protecta') and 'sanitas' in low and not is_protecta_likely:
        prov = 'sanitas'

    # NUEVO: Forzar Pacifico si se detecta Multisalud o RUC Pacifico (corrige falsos positivos de Mapfre)
    if "multisalud" in t or "20332970411" in t or "pacifico seguros" in t:
        prov = "pacifico"

    # NUEVO: si vino 'positiva' (o cualquier otro) pero el contenido dice 'MAPFRE', fuerza Mapfre
    # (corrige falsos positivos donde 'la positiva' aparece en textos legales de Mapfre)
    # IMPORTANTE: No entrar si ya se detectó mapfre-equipo-contratistas, mapfre-vehicular o mapfre-vida-ley para evitar downgrades
    if prov not in {"mapfre", "mapfre-equipo-contratistas", "mapfre-vehicular", "mapfre-vida-ley", "pacifico"} and (
        "mapfre" in t or
        re.search(r"vencimiento\s+de\s+aplicaci[oó]n", t) or
        re.search(r"inicio\s+de\s+vigencia\s+aplicaci[oó]n", t)
    ):
        # Asegurarse que no sea Vida Ley si tiene indicadores específicos
        if "vida ley" in t or "decreto legislativo" in t:
             prov = "mapfre-vida-ley"
        # NUEVO: Equipo de Contratistas
        elif re.search(r"equipo\s+de\s+contratistas", t) or re.search(r"responsabilidad\s+civil", t) or re.search(r"hidrocarburos", t):
             prov = "mapfre-equipo-contratistas"
        else:
             prov = "mapfre"

    # Enrutamiento por proveedor (prioriza 'prov' si está presente)
    items: List[Dict[str, str]] = []
    parse_pdf_items_provider._last_provider = prov
    if prov == 'pacifico':
        try:
            pac_pages = page_texts if page_texts else [text]
            pac_pages_low = [(p or "").lower() for p in pac_pages]
            pac_text_low = (text or "").lower()
            pac_detection_blocks = pac_pages_low + ([pac_text_low] if pac_text_low.strip() else [])

            has_generales_v2 = any(
                (
                    re.search(r"aviso\s+de\s+cobranza", pl)
                    or (
                        re.search(r"prima\s+comercial", pl)
                        and (re.search(r"multiriesgo", pl) or re.search(r"forma\s+de\s+pago", pl))
                    )
                )
                and re.search(r"p[oó]liza", pl)
                for pl in pac_detection_blocks
            )

            has_exclusion = (not has_generales_v2) and any(
                re.search(r"\bvida\s+ley\b", pl)
                or re.search(r"liquidaci[oó]n\s+de\s+prima", pl)
                or re.search(r"factura\s+electr[óo]nica", pl)
                or re.search(r"\bpensi[oó]n\b", pl)
                for pl in pac_pages_low
            )
            if has_generales_v2 and not has_exclusion:
                print("[provider] pacifico -> generales V4/V3/V2")
                from controllers.addPolizaPacificoGenerales_V4 import addPolizaPacificoGenerales_V4
                from controllers.addPolizaPacificoGenerales_V3 import addPolizaPacificoGenerales_V3
                from controllers.addPacificoGenerales_V2 import addPacificoGenerales_V2

                data = addPolizaPacificoGenerales_V4(path)
                if not data or data.get('error') or not data.get('poliza'):
                    print("[provider] pacifico -> fallback V3")
                    data = addPolizaPacificoGenerales_V3(path)
                if not data or data.get('error') or not data.get('poliza'):
                    print("[provider] pacifico -> fallback V2")
                    data = addPacificoGenerales_V2(path)

                if data and not data.get('error') and data.get('poliza'):
                    it = {
                        'cia': 'Pacífico',
                        'numero_poliza': data.get('poliza'),
                        'recibo': data.get('recibo', ''),  # Added field
                        'colectivo_asegurado': data.get('asegurado'),  # Added field
                        'inicio_vigencia': data.get('inicio'),
                        'vencimiento': data.get('fin'),
                        'fecha_emision': data.get('emision'),  # Added field
                        'ultimo_dia_pago': data.get('fecha_pago'), # Added field
                        'fecha_vencimiento': data.get('fecha_pago'), # Added field
                        'prima_neta': str(data.get('prima_neta', '')),
                        'prima_total': str(data.get('total', '')),
                        'prima_comercial_igv': str(data.get('total', '')),
                        'prima_comercial': str(data.get('prima_neta', '')),
                        'comision_compania_importe': str(data.get('comision_compania_importe', '')),
                        'importe_comision': str(data.get('comision_compania_importe', '')),
                        'moneda': data.get('moneda'),
                        'ramo': data.get('ramo') or '',
                        'ramos_producto': data.get('producto')
                    }

                    # Ensure prima comercial is set correctly if total exists
                    if data.get('total'):
                        it['prima_total'] = str(data.get('total', ''))
                    items.append(it)
        except Exception as e:
            print(f"[provider] pacifico parse error: {e}")

        if items:
            return items

        pac_pages = page_texts if page_texts else [text]
        pac_pages_low = [(p or "").lower() for p in pac_pages]

        vida_pages = [
            pac_pages[i] for i, pl in enumerate(pac_pages_low)
            if re.search(r"\bvida\s+ley\b", pl) or re.search(r"\bcondicionado\b", pl)
        ]
        factura_pages = [
            pac_pages[i] for i, pl in enumerate(pac_pages_low)
            if re.search(r"factura\s+electr[óo]nica", pl)
            or re.search(r"entidad\s+prestadora\s+de\s+salud", pl)
            or re.search(r"\beps\b", pl)
        ]
        liquid_pages = [
            pac_pages[i] for i, pl in enumerate(pac_pages_low)
            if re.search(r"liquidaci[oó]n\s+de\s+prima", pl)
            or re.search(r"total\s+a\s+cobrar", pl)
            or re.search(r"\baccidentes\s+de\s+trabajo\b", pl)
        ]

        if vida_pages:
            try:
                from controllers.addPacificoVidaLey import parse_pacifico_vidaley
                it = parse_pacifico_vidaley("\n".join(vida_pages))
                return [it] if it else []
            except Exception as e:
                print(f"[provider] pacifico-vida-ley parse error: {e}")

        if liquid_pages:
            liquid_text = "\n".join(liquid_pages)
        else:
            liquid_text = ""
        if factura_pages:
            factura_text = "\n".join(factura_pages)
        else:
            factura_text = ""

        out: List[Dict[str, str]] = []

        if liquid_text:
            try:
                is_sctr_pension_local = (
                    (re.search(r"\bsctr\b", liquid_text, re.IGNORECASE) or re.search(r"\baccidentes\s+de\s+trabajo\b", liquid_text, re.IGNORECASE))
                    and (re.search(r"\bpensi[oó]n\b", liquid_text, re.IGNORECASE) or re.search(r"\bpensiones\b", liquid_text, re.IGNORECASE) or re.search(r"\baccidentes\s+de\s+trabajo\b", liquid_text, re.IGNORECASE))
                )
                if is_sctr_pension_local:
                    import importlib
                    pac_mod = importlib.import_module('controllers.addPacifico')
                    pac_mod = importlib.reload(pac_mod)
                    it = pac_mod.parse_pacifico_pension(liquid_text)
                else:
                    from controllers.addPacifico import parse_pacifico_convenio
                    it = parse_pacifico_convenio(liquid_text)
                if it:
                    out.append(it)
            except Exception as e:
                print(f"[provider] pacifico liquid parse error: {e}")

        if factura_text:
            try:
                from controllers.addPacificoSalud import parse_pacifico_salud
                it = parse_pacifico_salud(factura_text)
                if it:
                    out.append(it)
            except Exception as e:
                print(f"[provider] pacifico salud parse error: {e}")

        if out:
            return out

        try:
            is_vida_ley = re.search(r'\bvida\s+ley\b', low) or re.search(r'\bcondicionado', low)
            is_factura_eps = (
                re.search(r"entidad\s+prestadora\s+de\s+salud", low)
                or re.search(r"factura\s+electr[óo]nica", low)
            )
            is_sctr_pension = (
                (re.search(r"\bsctr\b", low) or re.search(r"\baccidentes\s+de\s+trabajo\b", low))
                and (re.search(r"\bpensi[oó]n\b", low) or re.search(r"\bpensiones\b", low) or re.search(r"\baccidentes\s+de\s+trabajo\b", low))
                and not is_factura_eps
            )
            is_sctr_salud = (
                (re.search(r"\bsctr\b", low) and (re.search(r"\bsalud\b", low) or is_factura_eps or re.search(r"\beps\b", low)))
                or is_factura_eps
            )
            is_multisalud = re.search(r'multisalud', low) or re.search(r'aviso\s+de\s+cobranza', low)

            if is_multisalud:
                return []
            if is_vida_ley:
                from controllers.addPacificoVidaLey import parse_pacifico_vidaley
                it = parse_pacifico_vidaley(text)
                return [it] if it else []
            if is_sctr_pension:
                import importlib
                pac_mod = importlib.import_module('controllers.addPacifico')
                pac_mod = importlib.reload(pac_mod)
                it = pac_mod.parse_pacifico_pension(text)
                return [it] if it else []
            if is_sctr_salud:
                from controllers.addPacificoSalud import parse_pacifico_salud
                it = parse_pacifico_salud(text)
                return [it] if it else []
            from controllers.addPacifico import parse_pacifico_convenio
            it = parse_pacifico_convenio(text)
            return [it] if it else []
        except Exception as e:
            print(f"[provider] pacifico parse fallback error: {e}")
            return []

    print(f"[provider] detectado: {prov}")

    if prov == "qualitas":
        try:
            from controllers.addPolizaQualitasGenerales import parse_qualitas_generales
            item = parse_qualitas_generales(text)
        except Exception as e:
            _quarantine_parser_failure(path, 'qualitas', 'exception', {'error': str(e)}, text_head=text)
            print(f"[provider] qualitas parse error: {e}")
            return []
        missing = _missing_fields(item, ['numero_poliza', 'colectivo_asegurado', 'inicio_vigencia', 'vencimiento'])
        if missing:
            _quarantine_parser_failure(path, 'qualitas', 'missing_fields', {'missing': missing}, text_head=text)
        return [item] if item else []

    if prov == "mapfre-endoso-generales":
        try:
            from controllers.addMapfreEndosoGenerales import parse_mapfre_endoso_generales
            item = parse_mapfre_endoso_generales(text)
        except Exception as e:
            _quarantine_parser_failure(path, 'mapfre-endoso-generales', 'exception', {'error': str(e)}, text_head=text)
            print(f"[provider] mapfre-endoso-generales parse error: {e}")
            return []
        missing = _missing_fields(item, ['numero_poliza', 'colectivo_asegurado', 'inicio_vigencia', 'vencimiento'])
        if missing:
            _quarantine_parser_failure(path, 'mapfre-endoso-generales', 'missing_fields', {'missing': missing}, text_head=text)
        return [item] if item else []

    if prov == "mapfre":
        if re.search(r"equipo\s+de\s+contratistas", low) or re.search(r"responsabilidad\s+civil", low) or re.search(r"hidrocarburos", low):
            print("ENTRANDO A PARSER EQUIPO CONTRATISTAS (desde bloque mapfre - regex extendido)")
            from controllers.addMapfreEquipoContratistas_4 import parse_mapfre_equipo_contratistas_4
            item = parse_mapfre_equipo_contratistas_4(text)

            if not item or not item.get('numero_poliza') or not item.get('colectivo_asegurado') or not item.get('inicio_vigencia'):
                print("[provider] mapfre equipo contratistas V4 incompleto, intentando V3/V1/V2")
                from controllers.addMapfreEquipoContratistas_3 import parse_mapfre_equipo_contratistas_3
                item = parse_mapfre_equipo_contratistas_3(text)

                if not item or not item.get('numero_poliza') or not item.get('colectivo_asegurado') or not item.get('inicio_vigencia'):
                    print("[provider] mapfre equipo contratistas V3 incompleto, intentando V1/V2")
                    from controllers.addMapfreEquipoContratistas import parse_mapfre_equipo_contratistas
                    item = parse_mapfre_equipo_contratistas(text)

                    if not item or not item.get('numero_poliza') or not item.get('colectivo_asegurado') or not item.get('inicio_vigencia'):
                        print("[provider] mapfre equipo contratistas V1 incompleto, intentando V2")
                        try:
                            from controllers.addMapfreEquipoContratistas_2 import parse_mapfre_equipo_contratistas_2
                            item2 = parse_mapfre_equipo_contratistas_2(text)
                            if item2 and item2.get('numero_poliza'):
                                item = item2
                                print("[provider] mapfre equipo contratistas V2 exitoso")
                        except Exception as e:
                            print(f"[provider] mapfre equipo contratistas V2 error: {e}")

            print("[provider] mapfre equipo contratistas item:", item)
            return [item] if item else []

        hint_acc_personales_mapfre = (
            re.search(r"P[ÓO]LIZA\s+DE\s+SEGURO\s+DE\s+SEGURO\s+CONTRA\s+ACCIDENTES\s+PERSONALES", text, re.IGNORECASE)
            or re.search(r"P[ÓO]LIZA\s+DE\s+SEGURO\s+DE\s+ACCIDENTES\s+PERSONALES", text, re.IGNORECASE)
            or (
                re.search(r"\bACCIDENTES\s+PERSONALES\b", text, re.IGNORECASE)
                and re.search(r"\bMAPFRE\b", text, re.IGNORECASE)
            )
        )
        if hint_acc_personales_mapfre:
            try:
                parse_mapfre_poliza_sap = _load_mapfre_sap_parser()
                item_mapfre_sap = parse_mapfre_poliza_sap(text)
                if item_mapfre_sap and item_mapfre_sap.get("numero_poliza"):
                    print("[provider] mapfre-accidentes-personales item:", item_mapfre_sap)
                    return [item_mapfre_sap]
                print("[provider] mapfre-accidentes-personales sin numero_poliza, fallback a parser general")
            except Exception as e:
                print(f"[provider] mapfre-accidentes-personales parse error: {e}")

        if (
            re.search(r"\bsuplemento\s+de\s+salud\b", low)
            and (
                re.search(r"carta\s+de\s+renovaci[oó]n", low)
                or re.search(r"\btipo\s+renovaci[oó]n\b", low)
                or re.search(r"\bimporte\s+comisi[oó]n\b", low)
            )
        ):
            try:
                from controllers.addRenovacioMapfre import parse_renovacio_mapfre
                item_renovacion = parse_renovacio_mapfre(text)
                if item_renovacion and item_renovacion.get("numero_poliza"):
                    print("[provider] mapfre renovacion salud item:", item_renovacion)
                    return [item_renovacion]
            except Exception as e:
                print(f"[provider] mapfre renovacion salud parse error: {e}")

        if re.search(r"\bsuplemento\s+de\b", low) and not re.search(r"seguro\s+vehicular", low):
            try:
                from controllers.addMapfreEndosoGenerales import parse_mapfre_endoso_generales
                it_endoso = parse_mapfre_endoso_generales(text)
                if it_endoso and it_endoso.get("numero_poliza"):
                    return [it_endoso]
            except Exception:
                pass


        from controllers.addMapfre import parse_mapfre
        try:
            item = parse_mapfre(text)
        except Exception as e:
            _quarantine_parser_failure(path, 'mapfre', 'exception', {'error': str(e)}, text_head=text)
            print(f"[provider] mapfre parse error: {e}")
            return []
        print("[provider] mapfre item pension:", item)
        missing = _missing_fields(item, ['numero_poliza', 'colectivo_asegurado', 'inicio_vigencia', 'vencimiento'])
        if missing:
            _quarantine_parser_failure(path, 'mapfre', 'missing_fields', {'missing': missing}, text_head=text)
        return [item] if item else []
    if prov == "mapfre-vida-ley":
        try:
            from controllers.addMapfreVidaLeyv2 import parse_mapfre_vidaley_v2
            item = parse_mapfre_vidaley_v2(text)
        except Exception as e:
            item = None
            _quarantine_parser_failure(path, 'mapfre-vida-ley', 'exception_v2', {'error': str(e)}, text_head=text)
        # Aceptar ítem de v2 si al menos trae número de póliza; si no, fallback a v3 (formato "VIGENCIA DESDE/HASTA") y luego v1
        if not item or not item.get('numero_poliza'):
            try:
                from controllers.addMapfreVidaLeyv3 import parse_mapfre_vidaley_v3
                item = parse_mapfre_vidaley_v3(text)
            except Exception as e:
                item = None
                _quarantine_parser_failure(path, 'mapfre-vida-ley', 'exception_v3', {'error': str(e)}, text_head=text)
        if not item or not item.get('numero_poliza'):
            try:
                from controllers.addMapfreVidaLey import parse_mapfre_vidaley
                item = parse_mapfre_vidaley(text)
            except Exception as e:
                _quarantine_parser_failure(path, 'mapfre-vida-ley', 'exception_v1', {'error': str(e)}, text_head=text)
                print(f"[provider] mapfre-vida-ley parse error: {e}")
                return []
        print("[provider] mapfre-vida-ley item:", item)
        missing = _missing_fields(item, ['numero_poliza', 'colectivo_asegurado', 'inicio_vigencia', 'vencimiento'])
        if missing:
            _quarantine_parser_failure(path, 'mapfre-vida-ley', 'missing_fields', {'missing': missing}, text_head=text)
        return [item] if item else []

    # La Positiva (EPS/Vida/Seguros)
    if prov in {"positiva", ""}:
        # Detectar Póliza 3D (Deshonestidad, Desaparición y Destrucción)
        hint_3d = (
            re.search(r"P[ÓO]LIZA\s+DE\s+SEGURO\s+DE\s+3D\b", text, re.IGNORECASE) or
            re.search(r"deshonestidad[,\s]+desaparici[oó]n\s+y\s+destrucci[oó]n", text, re.IGNORECASE) or
            re.search(r"\bRAMO\s*[:：]?\s*3D\b", text, re.IGNORECASE)
        )
        if hint_3d:
            try:
                from controllers.addPOLIZA_3D_EPS import parse_poliza_3d_eps
                item_3d = parse_poliza_3d_eps(text)
                if item_3d and item_3d.get('numero_poliza'):
                    print("[provider] positiva-3d item:", item_3d)
                    return [item_3d]
            except Exception as e:
                print(f"[provider] error en addPOLIZA_3D_EPS: {e}")



        # Detectar Vida Ley por contenido dentro de La Positiva
        hint_vidaley = (
            re.search(r"\bvida\s+ley\b", text, re.IGNORECASE) or
            re.search(r"decreto\s+legislativo\s*n?\s*688", text, re.IGNORECASE) or
            ("d.l.688" in t)
        )
        if hint_vidaley:
            from controllers.addLPVLEY import parse_positiva_vidaley
            item = parse_positiva_vidaley(text)
            print("[provider] positiva-vida-ley item:", item)
            return [item] if item else []
        
        # NUEVO: Si es Responsabilidad Civil o Transportes, priorizar el nuevo parser robusto
        hint_generales = (
            re.search(r"RESPONSABILIDAD\s+CIVIL", text, re.IGNORECASE) or
            re.search(r"TRANSPORTES", text, re.IGNORECASE)
        )
        if hint_generales:
            try:
                from controllers.addPositivaVidaGenerales import parse_positiva_vida_generales
                item_vg = parse_positiva_vida_generales(text)
                if item_vg and item_vg.get('numero_poliza'):
                    print("[provider] positiva-generales (RC/TR) item:", item_vg)
                    return [item_vg]
            except Exception as e:
                print(f"[provider] error en addPositivaVidaGenerales (RC/TR): {e}")

        # Endoso de Declaración tiene prioridad sobre Renovación (la palabra "renovación"
        # puede aparecer en el cuerpo legal del PDF de declaración y causar falso positivo)
        hint_endoso_declaracion = re.search(
            r"Endoso\s+de\s+Declaraci[oó]n\s+N[°º]", text, re.IGNORECASE
        )
        if hint_endoso_declaracion:
            try:
                from controllers.addLPVPensionDeclaracion import parse_lpv_pension_declaracion
                items_decl = parse_lpv_pension_declaracion(text)
                if items_decl:
                    print("[provider] positiva-endoso-declaracion items:", items_decl)
                    return items_decl
            except Exception as e:
                print(f"[provider] error en addLPVPensionDeclaracion: {e}")

        hint_endoso_renov = re.search(r"ENDOSO\s+DE\s+RENOVACI[ÓO]N", text, re.IGNORECASE)
        if hint_endoso_renov:
            try:
                from controllers.addPolizaEndosoRenovacionGene import parse_positiva_endoso_renovacion_generales
                item_er = parse_positiva_endoso_renovacion_generales(text)
                if item_er and item_er.get('numero_poliza'):
                    print("[provider] positiva-endoso-renovacion item:", item_er)
                    return [item_er]
            except Exception as e:
                print(f"[provider] error en addPolizaEndosoRenovacionGene: {e}")

        hint_acc_personales = (
            re.search(r"P[ÓO]LIZA\s+DE\s+SEGURO\s+DE\s+ACCIDENTES\s+PERSONALES", text, re.IGNORECASE)
            or re.search(r"\bACCIDENTES\s+PERSONALES\b", text, re.IGNORECASE)
        )
        if hint_acc_personales:
            try:
                from controllers.addPositivaAccidentesPersonales import parse_positiva_accidentes_personales
                item_ap = parse_positiva_accidentes_personales(text)
                if item_ap and item_ap.get('numero_poliza'):
                    print("[provider] positiva-accidentes-personales item:", item_ap)
                    return [item_ap]
            except Exception as e:
                print(f"[provider] error en addPositivaAccidentesPersonales: {e}")

        # Separar SCTR Salud vs Pensión por contenido
        hint_sctr = re.search(r"\bsctr\b", text, re.IGNORECASE)
        has_salud = re.search(r"\beps\b", text, re.IGNORECASE) or re.search(r"\bsalud\b", text, re.IGNORECASE)
        has_pension = re.search(r"\bpensi[o\u00f3]n\b", text, re.IGNORECASE)

        if hint_sctr or has_salud or has_pension:
            # NUEVO: si hay ambos, parsear y devolver dos ítems
            if has_salud and has_pension:
                from controllers.addLPVSALUD import parse_positiva_Salud
                from controllers.addLPVPENSION import parse_positiva_Pension
                item_salud = parse_positiva_Salud(text)
                item_pension = parse_positiva_Pension(text)
                print("[provider] positiva-sctr ambos -> salud:", item_salud, "pension:", item_pension)
                items = []
                if item_salud: items.append(item_salud)
                if item_pension: items.append(item_pension)
                try:
                    from controllers.addPositivaGenerales import extract_proforma_numero_positiva, extract_numero_poliza_positiva
                    proforma = extract_proforma_numero_positiva(text)
                    poliza = extract_numero_poliza_positiva(text)
                    if proforma:
                        for it in items:
                            if isinstance(it, dict) and not (it.get('recibo') or '').strip():
                                it['recibo'] = proforma
                    if poliza:
                        for it in items:
                            if isinstance(it, dict) and not (it.get('numero_poliza') or '').strip():
                                it['numero_poliza'] = poliza
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_razon_social, extract_razon_social_strict, _clean_company_name
                    name = extract_razon_social_strict(text) or extract_razon_social(text)
                    name = _clean_company_name(name) or name
                    if name:
                        rx = re.compile(r"\b(bajo|alto|mediano|medio)\s+riesgo\b", re.IGNORECASE)
                        long_text_re = re.compile(r"[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")
                        for it in items:
                            cur = (it.get('colectivo_asegurado') or it.get('asegurado') or '').strip()
                            if not cur or rx.search(cur) or long_text_re.search(cur) or 'incumplimiento' in cur.lower():
                                it['colectivo_asegurado'] = name
                except Exception:
                    pass
                return items
            if has_salud:
                from controllers.addLPVSALUD import parse_positiva_Salud
                item = parse_positiva_Salud(text)
                try:
                    from controllers.addPositivaGenerales import extract_proforma_numero_positiva, extract_numero_poliza_positiva
                    proforma = extract_proforma_numero_positiva(text)
                    poliza = extract_numero_poliza_positiva(text)
                    if proforma and isinstance(item, dict) and not (item.get('recibo') or '').strip():
                        item['recibo'] = proforma
                    if poliza and isinstance(item, dict) and not (item.get('numero_poliza') or '').strip():
                        item['numero_poliza'] = poliza
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_vigencias_positiva
                    vig = extract_vigencias_positiva(text)
                    if vig and isinstance(item, dict):
                        if vig.get('inicio_vigencia') and not (item.get('inicio_vigencia') or '').strip():
                            item['inicio_vigencia'] = vig['inicio_vigencia']
                        if vig.get('vencimiento') and not (item.get('vencimiento') or '').strip():
                            item['vencimiento'] = vig['vencimiento']
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_razon_social, extract_razon_social_strict, _clean_company_name
                    name = extract_razon_social_strict(text) or extract_razon_social(text)
                    name = _clean_company_name(name) or name
                    if name:
                        rx = re.compile(r"\b(bajo|alto|mediano|medio)\s+riesgo\b", re.IGNORECASE)
                        long_text_re = re.compile(r"[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")
                        cur = (item or {}).get('colectivo_asegurado') or ''
                        if (not cur.strip()) or rx.search(cur) or long_text_re.search(cur) or 'incumplimiento' in cur.lower():
                            item['colectivo_asegurado'] = name
                except Exception:
                    pass
                print("[provider] positiva-sctr-salud item:", item)
                return [item] if item else []
            elif has_pension:
                from controllers.addLPVPENSION import parse_positiva_Pension
                item = parse_positiva_Pension(text)
                try:
                    from controllers.addPositivaGenerales import extract_proforma_numero_positiva, extract_numero_poliza_positiva
                    proforma = extract_proforma_numero_positiva(text)
                    poliza = extract_numero_poliza_positiva(text)
                    if proforma and isinstance(item, dict) and not (item.get('recibo') or '').strip():
                        item['recibo'] = proforma
                    if poliza and isinstance(item, dict) and not (item.get('numero_poliza') or '').strip():
                        item['numero_poliza'] = poliza
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_vigencias_positiva
                    vig = extract_vigencias_positiva(text)
                    if vig and isinstance(item, dict):
                        if vig.get('inicio_vigencia') and not (item.get('inicio_vigencia') or '').strip():
                            item['inicio_vigencia'] = vig['inicio_vigencia']
                        if vig.get('vencimiento') and not (item.get('vencimiento') or '').strip():
                            item['vencimiento'] = vig['vencimiento']
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_razon_social, extract_razon_social_strict, _clean_company_name
                    name = extract_razon_social_strict(text) or extract_razon_social(text)
                    name = _clean_company_name(name) or name
                    if name:
                        rx = re.compile(r"\b(bajo|alto|mediano|medio)\s+riesgo\b", re.IGNORECASE)
                        long_text_re = re.compile(r"[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")
                        cur = (item or {}).get('colectivo_asegurado') or ''
                        if (not cur.strip()) or rx.search(cur) or long_text_re.search(cur) or 'incumplimiento' in cur.lower():
                            item['colectivo_asegurado'] = name
                except Exception:
                    pass
                print("[provider] positiva-sctr-pension item:", item)
                return [item] if item else []
            else:
                # Ambiguo: por ahora cae en Pensión (comportamiento previo)
                from controllers.addLPVPENSION import parse_positiva_Pension
                item = parse_positiva_Pension(text)
                try:
                    from controllers.addPositivaGenerales import extract_proforma_numero_positiva, extract_numero_poliza_positiva
                    proforma = extract_proforma_numero_positiva(text)
                    poliza = extract_numero_poliza_positiva(text)
                    if proforma and isinstance(item, dict) and not (item.get('recibo') or '').strip():
                        item['recibo'] = proforma
                    if poliza and isinstance(item, dict) and not (item.get('numero_poliza') or '').strip():
                        item['numero_poliza'] = poliza
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_vigencias_positiva
                    vig = extract_vigencias_positiva(text)
                    if vig and isinstance(item, dict):
                        if vig.get('inicio_vigencia') and not (item.get('inicio_vigencia') or '').strip():
                            item['inicio_vigencia'] = vig['inicio_vigencia']
                        if vig.get('vencimiento') and not (item.get('vencimiento') or '').strip():
                            item['vencimiento'] = vig['vencimiento']
                except Exception:
                    pass
                try:
                    from controllers.addPositivaGenerales import extract_razon_social, extract_razon_social_strict, _clean_company_name
                    name = extract_razon_social_strict(text) or extract_razon_social(text)
                    name = _clean_company_name(name) or name
                    if name:
                        rx = re.compile(r"\b(bajo|alto|mediano|medio)\s+riesgo\b", re.IGNORECASE)
                        long_text_re = re.compile(r"[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")
                        cur = (item or {}).get('colectivo_asegurado') or ''
                        if (not cur.strip()) or rx.search(cur) or long_text_re.search(cur) or 'incumplimiento' in cur.lower():
                            item['colectivo_asegurado'] = name
                except Exception:
                    pass
                print("[provider] positiva-sctr item:", item)
                return [item] if item else []
        
        # Intentar con el nuevo parser robusto para Vida/Generales
        try:
            from controllers.addPositivaVidaGenerales import parse_positiva_vida_generales
            item_vg = parse_positiva_vida_generales(text)
            if item_vg and item_vg.get('numero_poliza') and item_vg.get('colectivo_asegurado'):
                print("[provider] positiva-vida-generales item:", item_vg)
                return [item_vg]
        except Exception as e:
            print(f"[provider] error en addPositivaVidaGenerales: {e}")

        items = _parse_positiva(text)
        try:
            from controllers.addPositivaGenerales import extract_razon_social, extract_razon_social_strict, _clean_company_name
            name = extract_razon_social_strict(text) or extract_razon_social(text)
            name = _clean_company_name(name) or name
            if name:
                risk_re = re.compile(r"\b(bajo|alto|mediano|medio)\s+riesgo\b", re.IGNORECASE)
                long_text_re = re.compile(r"[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")
                for it in items:
                    current = (it.get('colectivo_asegurado') or it.get('asegurado') or '').strip()
                    if not current or risk_re.search(current) or long_text_re.search(current) or 'incumplimiento' in current.lower():
                        it['colectivo_asegurado'] = name
        except Exception:
            pass
        return items

    # Sanitas (EPS Salud / SCTR)
    if prov == "sanitas":
        from controllers.addSanitasSalud import parse_sanitas_salud
        item = parse_sanitas_salud(text)
        print("[provider] sanitas salud item:", item)
        return [item] if item else []

    if prov == "grandia-eps":
        from controllers.addGrandiaEpsV2 import parse_grandia_eps_v2
        from controllers.addGrandiaEps import parse_grandia_eps as parse_grandia_eps_v1
        item = parse_grandia_eps_v2(text)
        if _missing_fields(item, ["numero_poliza", "colectivo_asegurado", "prima_neta"]):
            item = parse_grandia_eps_v1(text)
        print("[provider] grandia eps item:", item)
        return [item] if item else []

    if prov == "rimac":
        hint_v3 = re.search(r"fecha\s+(?:de\s+)?emisi[oó]n\s*[:：]?\s*\d{4}-\d{2}-\d{2}", text, re.IGNORECASE)
        hint_v2 = re.search(r"\bNro\.?\s*[:：]?\s*\d{3,6}\s*[-–—]\s*\d{5,12}\b", text, re.IGNORECASE) or re.search(r"pol[ií]za\s*nro", text, re.IGNORECASE) or re.search(r"poliza\s+anual\s+de\s+transportes", text, re.IGNORECASE)
        if hint_v3:
            try:
                from controllers.addRimacGenerales_V3 import parse_rimac_generales as parse_rimac_generales_v3
                item_v3 = parse_rimac_generales_v3(text)
                ok_v3 = item_v3 and re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", str(item_v3.get('fecha_emision') or ''))
                if ok_v3:
                    print("[provider] rimac V3 item:", item_v3)
                    return [item_v3]
            except Exception as e:
                print("[provider] rimac V3 error:", e)
        if hint_v2:
            try:
                from controllers.addRimacGenerales_V2 import parse_rimac_generales as parse_rimac_generales_v2
                item_v2 = parse_rimac_generales_v2(text)
                ok_v2 = item_v2 and re.search(r"\b\d{3,6}\s*-\s*\d{5,12}\b", str(item_v2.get('numero_poliza') or ''))
                if ok_v2:
                    print("[provider] rimac V2 item:", item_v2)
                    return [item_v2]
            except Exception as e:
                print("[provider] rimac V2 error:", e)
        from controllers.addRimacGenerales import parse_rimac_generales
        item = parse_rimac_generales(text)
        print("[provider] rimac item:", item)
        return [item] if item else []

    # NUEVO: Protecta Pensión
    if prov in {"protecta", "proctecta"}:
        hint_vidaley = (
            re.search(r"\bvida\s+ley\b", low)
            or re.search(r"decreto\s+legislativo\s*n?\s*688", low)
            or ("d.l.688" in low)
            or re.search(r"\bseguro\s+de\s+vida\s+ley\b", low)
        )
        if hint_vidaley:
            from controllers.addProctectaVidaLey import parse_protecta_vidaley
            item = parse_protecta_vidaley(text)
            print("[provider] protecta vida ley item:", item)
            return [item] if item else []

        # Detectar si es Emisión (SCTR Pensiones con Prima Comercial)
        # Excluir 'aviso de cobranza' para que vaya al parser estándar (addProctectaPension)
        if "prima comercial" in low and "pension" in low and "aviso de cobranza" not in low:
             from controllers.addProctectaPensionEmision import parse_protecta_pension_emision
             item = parse_protecta_pension_emision(text)
             print("[provider] protecta pension emision item:", item)
             return [item] if item else []

        from controllers.addProctectaPension import parse_protecta_pension
        item = parse_protecta_pension(text)
        return [item] if item else []
    # NUEVO: Crecer Pensión
    if prov == "crecer":
        from controllers.addCrecerPension import parse_crecer_pension
        item = parse_crecer_pension(text)
        print("[provider] crecer pension item:", item)
        return [item] if item else []
    if prov == "pacifico":
        import importlib
        pac_mod = importlib.import_module('controllers.addPacifico')
        pac_mod = importlib.reload(pac_mod)
        pac_vl_mod = importlib.import_module('controllers.addPacificoVidaLey')
        pac_vl_mod = importlib.reload(pac_vl_mod)
        from controllers.addPacifico import parse_pacifico_pension
        from controllers.addPacificoVidaLey import parse_pacifico_vidaley  # NUEVO
        print("[provider] branch: pacifico; texto (head 600):", text[:600].replace("\n", "\\n"))
        # Detectar Vida Ley por contenido
        hint_vidaley = re.search(r"\bvida\s+ley\b", text, re.IGNORECASE) or re.search(r"decreto\s+legislativo\s*n?\s*688", text, re.IGNORECASE)
        item = pac_vl_mod.parse_pacifico_vidaley(text) if hint_vidaley else pac_mod.parse_pacifico_pension(text)
        item = parse_pacifico_vidaley(text) if hint_vidaley else parse_pacifico_pension(text)
        print("[provider] pacifico item:", item)
        return [item] if item else []
    # NUEVO: Pacifico Salud
    if prov == "pacifico_salud":
        from controllers.addPacificoSalud import parse_pacifico_salud
        item = parse_pacifico_salud(text)
        print("[provider] pacifico_salud item:", item)
        return [item] if item else []

    if prov == "vida-ley-crecer":
        from controllers.addCrecerVidaLey import parse_crecer_vidaley
        # NUEVO: Variante pocos datos
        from controllers.addCrecer_vida_ley_pocos_datos import parse_crecer_vidaley_pocos_datos

        if "DATOS DE LA POLIZA DE SEGURO" in text or "Prima Comercial + IGV" in text:
            item = parse_crecer_vidaley_pocos_datos(text)
            print("[provider] vida-ley-crecer (pocos datos) item:", item)
            return [item] if item else []

        item = parse_crecer_vidaley(text)
        print("[provider] vida-ley-crecer item:", item)
        return [item] if item else []

    # NUEVO: LPV Vida Ley
    if prov == "lpv-vida-ley":
        from controllers.addLPVLEY import parse_positiva_vidaley
        item = parse_positiva_vidaley(text)
        print("[provider] lpv-vida-ley item:", item)
        return [item] if item else []
    # NUEVO: LPV Pension
    if prov == "mapfre-equipo-contratistas":
        print("ENTRANDO A PARSER EQUIPO CONTRATISTAS (prov mapfre-equipo-contratistas)")
        from controllers.addMapfreEquipoContratistas_4 import parse_mapfre_equipo_contratistas_4
        item = parse_mapfre_equipo_contratistas_4(text)

        if not item or not item.get('numero_poliza') or not item.get('colectivo_asegurado') or not item.get('inicio_vigencia'):
            print("[provider] mapfre-equipo-contratistas V4 incompleto, intentando V3/V1/V2")
            from controllers.addMapfreEquipoContratistas_3 import parse_mapfre_equipo_contratistas_3
            item = parse_mapfre_equipo_contratistas_3(text)

            if not item or not item.get('numero_poliza') or not item.get('colectivo_asegurado') or not item.get('inicio_vigencia'):
                print("[provider] mapfre-equipo-contratistas V3 incompleto, intentando V1/V2")
                from controllers.addMapfreEquipoContratistas import parse_mapfre_equipo_contratistas
                item = parse_mapfre_equipo_contratistas(text)

                if not item or not item.get('numero_poliza') or not item.get('colectivo_asegurado') or not item.get('inicio_vigencia'):
                    print("[provider] mapfre-equipo-contratistas V1 incompleto, intentando V2")
                    try:
                        from controllers.addMapfreEquipoContratistas_2 import parse_mapfre_equipo_contratistas_2
                        item2 = parse_mapfre_equipo_contratistas_2(text)
                        if item2 and item2.get('numero_poliza'):
                            item = item2
                            print("[provider] mapfre-equipo-contratistas V2 exitoso")
                    except Exception as e:
                        print(f"[provider] mapfre-equipo-contratistas V2 error: {e}")

        print("[provider] mapfre-equipo-contratistas item:", item)
        return [item] if item else []

    # NUEVO: Mapfre Vehicular
    if prov == "mapfre-vehicular":
        print("ENTRANDO A PARSER MAPFRE VEHICULAR")
        from controllers.addMapfreVehicular import parse_mapfre_vehicular
        item = parse_mapfre_vehicular(text)
        print("[provider] mapfre-vehicular item:", item)
        return [item] if item else []

    if prov == "lpv-pension":
        from controllers.addLPVPENSION import parse_positiva_Pension
        item = parse_positiva_Pension(text)
        print("[provider] lpv-pension item:", item)
        return [item] if item else []
    # NUEVO: LPV Salud
    if prov == "lpv-salud":
        from controllers.addLPVSALUD import parse_positiva_Salud
        item = parse_positiva_Salud(text)
        print("[provider] lpv-salud item:", item)
        parse_pdf_items_provider._last_provider = prov
        return [item] if item else []
    parse_pdf_items_provider._last_provider = prov
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
    items = parse_pdf_items_provider(path, None)
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

# NUEVO: ruta para servir PDFs subidos desde UPLOAD_FOLDER
@bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    folder = current_app.config.get('UPLOAD_FOLDER')
    static_folder = current_app.static_folder

    # Normalizar separadores
    filename = filename.replace('\\', '/')

    # Si la ruta guardada en BD trae el prefijo redundante "uploads/" quitarlo.
    # Esto ocurre con registros antiguos que almacenaron "uploads/polizas/xxx"
    # y el blueprint ya añade "/uploads/" en la URL.
    while filename.startswith('uploads/'):
        filename = filename[len('uploads/'):]

    # Compatibilidad: algunos registros guardaron "static/...".
    while filename.startswith('static/'):
        filename = filename[len('static/'):]

    # Separar subcarpeta(s) y nombre de archivo
    parts = filename.split('/')
    name  = secure_filename(parts[-1])      # solo el nombre final, sin slashes
    sub   = '/'.join(parts[:-1]) if len(parts) > 1 else ''

    ALLOWED_SUBS = {'polizas', 'clientes', 'cuotas', 'siniestros', 'soat', 'logo', 'exports', 'temp', ''}

    # 1. Ruta directa: subcarpeta + nombre
    if sub.split('/')[0] in ALLOWED_SUBS or sub == '':
        target_dir = os.path.join(folder, sub) if sub else folder
        full_path  = os.path.join(target_dir, name)
        if os.path.isfile(full_path):
            return send_from_directory(target_dir, name, as_attachment=False)

    # 2. Fallback: buscar el nombre en todas las subcarpetas conocidas
    for known_sub in ['polizas', 'temp', 'cuotas', 'clientes', 'siniestros', 'soat']:
        candidate = os.path.join(folder, known_sub, name)
        if os.path.isfile(candidate):
            return send_from_directory(os.path.join(folder, known_sub), name, as_attachment=False)

    # 3. Fallback: raíz de uploads
    root_path = os.path.join(folder, name)
    if os.path.isfile(root_path):
        return send_from_directory(folder, name, as_attachment=False)

    # 4. Fallback: recursos en static (ej. img/logo-aasnet.png usado en seeds/tests)
    if filename.startswith('img/'):
        static_rel = filename.replace('\\', '/').lstrip('/')
    else:
        static_rel = f"img/{name}"
    static_candidate = os.path.join(static_folder, static_rel)
    if os.path.isfile(static_candidate):
        static_dir = os.path.dirname(static_candidate)
        static_name = os.path.basename(static_candidate)
        return send_from_directory(static_dir, static_name, as_attachment=False)

    return {'error': 'Archivo no encontrado', 'path': os.path.join(folder, filename)}, 404


# Búsqueda rápida en PDF por texto, devolviendo la primera página donde aparece
@bp.route('/api/pdf/search', methods=['GET'])
def api_pdf_search():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    filename = (request.args.get('filename') or '').strip()
    query = (request.args.get('q') or '').strip()
    if not filename or not query:
        return jsonify({'ok': False, 'error': 'Parámetros inválidos'}), 400
    folder = current_app.config.get('UPLOAD_FOLDER')
    filename = filename.replace('\\', '/')
    while filename.startswith('uploads/'):
        filename = filename[len('uploads/'):]
    name = secure_filename(os.path.basename(filename))
    candidates = [
        os.path.join(folder, 'temp', name),
        os.path.join(folder, 'polizas', name),
        os.path.join(folder, name),
    ]
    path = next((p for p in candidates if os.path.isfile(p)), None)
    if not path:
        return jsonify({'ok': False, 'error': 'Archivo no encontrado'}), 404
    page_num = None
    try:
        try:
            import fitz
            doc = fitz.open(path)
            q_raw = query
            q_norm = re.sub(r'\s+', '', q_raw)
            pat = None
            if '-' in q_raw:
                parts = [s.strip() for s in q_raw.split('-', 1)]
                pat = re.compile(r'\b' + re.escape(parts[0]) + r'\s*[-–—‑−]?\s*' + re.escape(parts[1]) + r'\b', re.IGNORECASE)
            for i in range(doc.page_count):
                txt = doc.load_page(i).get_text() or ''
                up = txt
                if q_raw and q_raw in up:
                    page_num = i + 1
                    break
                if pat and pat.search(up):
                    page_num = i + 1
                    break
                if q_norm and re.sub(r'\s+', '', up).lower().find(q_norm.lower()) != -1:
                    page_num = i + 1
                    break
            doc.close()
        except Exception:
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            q_raw = query
            q_norm = re.sub(r'\s+', '', q_raw)
            pat = None
            if '-' in q_raw:
                parts = [s.strip() for s in q_raw.split('-', 1)]
                pat = re.compile(r'\b' + re.escape(parts[0]) + r'\s*[-–—‑−]?\s*' + re.escape(parts[1]) + r'\b', re.IGNORECASE)
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ''
                up = txt
                if q_raw and q_raw in up:
                    page_num = i + 1
                    break
                if pat and pat.search(up):
                    page_num = i + 1
                    break
                if q_norm and re.sub(r'\s+', '', up).lower().find(q_norm.lower()) != -1:
                    page_num = i + 1
                    break
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    if not page_num:
        return jsonify({'ok': True, 'page': None}), 200
    return jsonify({'ok': True, 'page': page_num}), 200


# dentro de routes/route.py (añadir el nuevo endpoint API)
@bp.route('/api/aseguradoras', methods=['GET'])
def api_aseguradoras():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    from controllers.compania import get_aseguradoras
    rows = get_aseguradoras() or []
    return {'ok': True, 'rows': rows}, 200

#Metodos para editar y ver detalle de clienes.
@bp.route('/clientes/edit', methods=['POST'])
@require_permission(can_edit, response_mode='json', ownership_check_fn=cliente_owner_from_request)
def clientes_edit():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.editcliente import editar_cliente_route
    return editar_cliente_route()


@bp.route('/clientes/detalle/<int:idCliente>', methods=['GET'])
def clientes_detalle(idCliente):
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.editcliente import get_cliente_detalle_route
    return get_cliente_detalle_route(idCliente)

@bp.route('/clientes/delete', methods=['POST'])
@require_permission(can_delete, response_mode='json', ownership_check_fn=cliente_owner_from_request)
def clientes_delete():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.deletecliente import eliminar_cliente_route
    return eliminar_cliente_route()

@bp.route('/clientes/restore', methods=['POST'])
@require_permission(can_restore, response_mode='json', ownership_check_fn=cliente_owner_from_request)
def clientes_restore():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401

    from controllers.clientes.restorecliente import restaurar_cliente_route
    return restaurar_cliente_route()

@bp.route('/clientes/hard-delete', methods=['POST'])
@require_permission(can_hard_delete, response_mode='json', ownership_check_fn=cliente_owner_from_request)
def clientes_hard_delete():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    from controllers.clientes.harddelete_cliente import hard_delete_cliente_route
    return hard_delete_cliente_route()

@bp.route('/polizas/hard-delete', methods=['POST'])
@require_permission(can_hard_delete, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def polizas_hard_delete():
    if 'user' not in session:
        return {'ok': False, 'errors': ['No autenticado']}, 401
    from controllers.harddelete_poliza import hard_delete_poliza_route
    return hard_delete_poliza_route()

@bp.route('/cuotas/hard-delete', methods=['POST'])
@require_permission(can_hard_delete, response_mode='json')
def cuotas_hard_delete():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.cuotas.cuotas import hard_delete_cuota
    data = request.json or {}
    cuota_id = data.get('idCuota')
    success, msg, recibo = hard_delete_cuota(cuota_id)
    if success:
        from utils.notify import notify_deletion
        user_session = session.get('user')
        usuario = user_session.get('username') if isinstance(user_session, dict) else (user_session or 'sistema')
        notify_deletion(usuario, 'CUOTA', recibo, evento='eliminacion')
        return {'ok': True}
    return {'ok': False, 'error': msg}, 400

@bp.route('/clientes/estado-cuenta/export', methods=['GET'])
def export_estado_cuenta():

    fmt = request.args.get('format', 'xlsx').lower()

    from controllers.clientes.estado_cuenta import export_estado_cuenta_data

    try:
        if fmt == 'pdf':
            filepath, filename = export_estado_cuenta_data(request.args, fmt='pdf')
            return send_from_directory(directory=os.path.dirname(filepath), path=os.path.basename(filepath), as_attachment=True, download_name=filename)
        else:
            filepath, filename = export_estado_cuenta_data(request.args, fmt='xlsx')
            return send_from_directory(directory=os.path.dirname(filepath), path=os.path.basename(filepath), as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.exception('Error exporting estado de cuenta')
        return jsonify({'ok': False, 'error': str(e)}), 500

# Siniestros routes
@bp.route('/api/siniestros', methods=['GET'])
def api_list_siniestros():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import list_siniestros
    return list_siniestros()

@bp.route('/api/siniestros/poliza', methods=['GET'])
def api_list_siniestros_poliza():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import list_siniestros_por_poliza
    return list_siniestros_por_poliza()

@bp.route('/api/siniestros/<int:id>', methods=['GET'])
def api_get_siniestro(id):
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import get_siniestro_by_id
    return get_siniestro_by_id(id)

@bp.route('/api/siniestros', methods=['POST'])
@require_permission(can_create, response_mode='json')
def api_insert_siniestro():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    from controllers.siniestros.siniestros_controller import insert_siniestro
    return insert_siniestro()

@bp.route('/api/siniestros/<int:id>', methods=['PUT'])
@require_permission(can_edit, response_mode='json', ownership_check_fn=siniestro_owner_from_request)
def api_update_siniestro(id):
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import update_siniestro
    return update_siniestro(id)

@bp.route('/api/siniestros/grupo-ramo', methods=['GET'])     ##1513 linea
def api_get_grupo_ramo_poliza():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import get_grupo_ramo_poliza
    return get_grupo_ramo_poliza()

# Ruta para servir los formularios HTML de siniestros
@bp.route('/templates/view/siniestros/<filename>')
def serve_siniestro_form(filename):
    """Sirve los archivos HTML de formularios de siniestros"""
    try:
        # Ruta absoluta a la carpeta templates
        templates_dir = os.path.join(current_app.root_path, 'templates', 'view', 'siniestros')
        return send_from_directory(templates_dir, filename)
    except Exception as e:
        return f'Error al cargar formulario: {str(e)}', 404

@bp.route('/api/siniestros/<int:id>', methods=['DELETE'])
@require_permission(can_delete, response_mode='json', ownership_check_fn=siniestro_owner_from_request)
def api_delete_siniestro(id):
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    from controllers.siniestros.siniestros_controller import delete_siniestro
    return delete_siniestro(id)

@bp.route('/api/siniestros/<int:id>/pdf', methods=['GET'])
def api_generar_pdf_siniestro(id):
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import generar_pdf_siniestro
    return generar_pdf_siniestro(id)

@bp.route('/api/siniestros/buscar', methods=['POST'])
def api_buscar_siniestros():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    from controllers.siniestros.siniestros_controller import buscar_siniestros
    return buscar_siniestros()

@bp.route('/menu/siniestros-poliza', methods=['GET'])
def menu_siniestros_poliza():
    if 'user' not in session:
        return redirect(url_for('login'))

    poliza = request.args.get('poliza', '')

    contratante = ''
    cia = ''
    ramo = ''
    asegurada = ''
    if poliza:
        try:
            from models.db import get_connection
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT 
                    COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR), c.razon_social) AS contratante,
                    COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR), p.asegurado) AS asegurado,
                    p.cia,
                    p.ramo,
                    p.asegurada
                FROM polizas p
                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                WHERE AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) = %s OR p.poliza = %s
                LIMIT 1
            """
            cursor.execute(query, (poliza, poliza))
            poliza_data = cursor.fetchone()

            if poliza_data:
                contratante = poliza_data.get('contratante') or poliza_data.get('asegurado') or ''
                cia = poliza_data.get('cia') or ''
                ramo = poliza_data.get('ramo') or poliza_data.get('asegurada') or ''
                asegurada = poliza_data.get('asegurada') or ''

            cursor.close()
            connection.close()
        except Exception as e:
            print(f"Error getting poliza details: {e}")

    return render_template(
        'view/siniestros/siniestros_poliza.html',
        poliza=poliza,
        contratante=contratante,
        cia=cia,
        ramo=ramo,
        asegurada=asegurada
    )

@bp.route('/menu/siniestros', methods=['GET'])
def menu_siniestros():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/siniestros/siniestros_lista.html')

@bp.route('/menu/mis-contactos', methods=['GET'])
def list_mis_contactos():
    if 'user' not in session:
        return redirect(url_for('main.home'))
    # Importar el controlador que obtiene los datos (alias para evitar choque de nombres)
    from controllers.contactos.mis_contactos import list_mis_contactos as _ctrl_list
    data = _ctrl_list() or {}
    clientes = data.get('clientes', [])
    search_query = data.get('search_query', '')
    return render_template('view/contactos/mis-contactos.html', page='mis-contactos', clientes=clientes, search_query=search_query)


@bp.route('/menu/mis-contactos/search', methods=['GET'])
def api_mis_contactos_search():
    """Endpoint JSON para búsqueda en tiempo real de mis contactos.
    Retorna lista de objetos { razon_social, telefono, email } (hasta 50).
    """
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    try:
        from controllers.contactos.mis_contactos import list_mis_contactos as ctrl
        data = ctrl() or {}
        clientes = data.get('clientes', [])
        return jsonify(clientes)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ==========================
# de preferencia toda la seccion de maestros quevaya aqui debajo
# ==========================

@bp.route('/menu/maestros-clases', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_clases():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/clases.html', page='maestros-clases')

@bp.route('/menu/maestros-usos', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_usos():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/usos.html', page='maestros-usos')

@bp.route('/menu/maestros-marcas', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_marcas():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/marcas.html', page='maestros-marcas')

@bp.route('/menu/maestros-modelos', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_modelos():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/modelos.html', page='maestros-modelos')

@bp.route('/menu/maestros-ramos', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_ramos():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/ramos.html', page='maestros-ramos')

@bp.route('/menu/maestros-productos', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_productos():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/productos.html', page='maestros-productos')

@bp.route('/menu/maestros-soat', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_maestros_soat():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/soat.html', page='maestros-soat')

@bp.route('/api/maestros/soat', methods=['GET'])
@require_permission(can_view_maestros, response_mode='json')
def api_maestros_soat():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        page = 1
        per_page = 10

    from controllers.maestros.soat import get_soat_conf
    rows = get_soat_conf()
    
    total = len(rows)
    # Paginación en memoria (si el dataset crece mucho, mover a SQL LIMIT/OFFSET)
    if per_page > 0:
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        end = start + per_page
        sliced = rows[start:end]
    else:
        # per_page <= 0 significa "todo"
        pages = 1
        page = 1
        sliced = rows

    return jsonify({
        'ok': True, 
        'rows': sliced, 
        'total': total, 
        'page': page, 
        'pages': pages, 
        'per_page': per_page
    })

@bp.route('/api/maestros/soat/update', methods=['POST'])
@require_permission(can_access_maestros, response_mode='json')
def api_maestros_soat_update():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    row_id = data.get('id')
    tipo_soat_id = data.get('tipo_soat_id')
    tasa_aas = data.get('tasa_aas')
    tasa_vendedor = data.get('tasa_vendedor')
    tasa_final_override = data.get('tasa_final_override')
    
    if row_id is None:
        return jsonify({'ok': False, 'error': 'Missing ID'}), 400

    from controllers.maestros.soat import update_soat_conf
    
    # Validar valores numéricos
    try:
        val_aas = float(tasa_aas) if tasa_aas is not None and tasa_aas != '' else 0.0
        val_vendedor = float(tasa_vendedor) if tasa_vendedor is not None and tasa_vendedor != '' else 0.0
        
        if tasa_final_override == '' or tasa_final_override is None:
            val_override = None
        else:
            val_override = float(tasa_final_override)
    except ValueError:
        return jsonify({'ok': False, 'error': 'Invalid numeric values'}), 400

    if update_soat_conf(row_id, tipo_soat_id, val_aas, val_vendedor, val_override):
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False, 'error': 'Failed to update database'}), 500

@bp.route('/menu/produccion-soat', methods=['GET'])
@require_permission(can_view_maestros, response_mode='redirect')
def menu_produccion_soat():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('view/maestros/produccion_soat.html', page='maestros-produccion-soat')

@bp.route('/api/produccion-soat', methods=['GET'])
@require_permission(can_view_maestros, response_mode='json')
def api_produccion_soat():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    try:
        page     = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        page, per_page = 1, 20

    search      = request.args.get('search', '').strip()
    fecha_desde = request.args.get('fecha_desde', None)
    fecha_hasta = request.args.get('fecha_hasta', None)

    from controllers.maestros.produccion_soat import get_produccion_soat
    data = get_produccion_soat(
        page=page,
        per_page=per_page,
        search=search,
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None
    )

    total    = data['total']
    rows     = data['rows']
    totales  = data['totales']
    pages    = max(1, (total + per_page - 1) // per_page) if per_page > 0 else 1

    # Convertir Decimal/date a tipos serializables
    import decimal, datetime
    def serialize(obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return obj

    rows_clean    = [{k: serialize(v) for k, v in r.items()} for r in rows]
    totales_clean = {k: serialize(v) for k, v in (totales or {}).items()}

    return jsonify({
        'ok': True,
        'rows': rows_clean,
        'total': total,
        'page': page,
        'pages': pages,
        'per_page': per_page,
        'totales': totales_clean
    })


@bp.route('/api/produccion-soat/export', methods=['GET'])
@require_permission(can_view_maestros, response_mode='json')
def api_produccion_soat_export():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    search      = request.args.get('search', '').strip()
    fecha_desde = request.args.get('fecha_desde', None)
    fecha_hasta = request.args.get('fecha_hasta', None)

    try:
        from controllers.maestros.produccion_soat import export_produccion_soat_excel
        filepath, filename = export_produccion_soat_excel(
            search=search,
            fecha_desde=fecha_desde or None,
            fecha_hasta=fecha_hasta or None
        )
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Error exportando produccion soat: {e}")
        return jsonify({'ok': False, 'error': f"Error generando Excel: {str(e)}"}), 500




@bp.route('/menu/maestros-usuarios', methods=['GET'])
@require_permission(can_access_maestros, response_mode='redirect')
def menu_maestros_usuarios():
    if 'user' not in session:
        return redirect(url_for('login'))
    from controllers.maestros.usuarios import get_usuarios, get_roles
    from controllers.ejecutivos import get_ejecutivos
    usuarios = get_usuarios()
    roles = get_roles()
    ejecutivos = get_ejecutivos() or []
    return render_template('view/maestros/usuarios.html', page='maestros-usuarios', usuarios=usuarios, roles=roles, ejecutivos=ejecutivos)

@bp.route('/api/maestros/usuarios/rol', methods=['POST'])
@require_permission(can_access_maestros, response_mode='json')
def api_maestros_usuarios_rol():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')
    role_id = data.get('role_id')
    
    if not user_id or not role_id:
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
        
    from controllers.maestros.usuarios import update_usuario_rol
    if update_usuario_rol(user_id, role_id):
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False, 'error': 'Failed to update role'}), 500

@bp.route('/api/maestros/usuarios/ejecutivo', methods=['POST'])
@require_permission(can_access_maestros, response_mode='json')
def api_maestros_usuarios_ejecutivo():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')
    ejecutivo_id = data.get('ejecutivo_id')
    
    if not user_id:
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
        
    from controllers.maestros.usuarios import update_usuario_ejecutivo
    if update_usuario_ejecutivo(user_id, ejecutivo_id or None):
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False, 'error': 'Failed to update ejecutivo'}), 500

@bp.route('/api/maestros/<entidad>', methods=['GET', 'POST'])
@require_permission(can_view_maestros, response_mode='json')
def api_maestros_list_create(entidad):
    """API básico para maestros: listar (GET) y crear (POST).
    Entidades soportadas: clases, usos, marcas, modelos
    """
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    entidad = (entidad or '').lower()

    # LISTAR
    if request.method == 'GET':
        # Soporte de paginación: ?page=1&per_page=20  o per_page=all para todo
        try:
            try:
                page = int(request.args.get('page') or 1)
            except Exception:
                page = 1
            per_page_arg = request.args.get('per_page')
            per_page = None
            if per_page_arg and str(per_page_arg).lower() != 'all':
                try:
                    per_page = int(per_page_arg)
                except Exception:
                    per_page = 20
            # Obtener rows desde controlador
            if entidad == 'clases':
                from controllers.maestros.clases import get_clases
                rows = get_clases() or []
            elif entidad == 'usos':
                from controllers.maestros.usos import get_usos
                rows = get_usos() or []
            elif entidad == 'marcas':
                from controllers.maestros.marcas import get_marcas
                rows = get_marcas() or []
            elif entidad == 'modelos':
                from controllers.maestros.modelos import get_modelos
                rows = get_modelos() or []
            elif entidad == 'ramos':
                from controllers.maestros.ramos import get_ramos
                rows = get_ramos() or []
            elif entidad == 'productos':
                from controllers.maestros.productos import get_productos
                rows = get_productos() or []
            else:
                rows = []

            total = len(rows)
            # Si per_page es None => devolver paginado por defecto 20
            if per_page is None:
                per_page = 20

            # Si se solicitó "all" explícitamente, devolver lista completa para compatibilidad
            if per_page_arg and str(per_page_arg).lower() == 'all':
                return jsonify({'ok': True, 'rows': rows, 'total': total, 'page': 1, 'per_page': 'all', 'pages': 1})

            pages = max(1, (total + per_page - 1) // per_page) if per_page > 0 else 1
            page = max(1, min(page, pages)) if pages > 0 else 1
            start = (page - 1) * per_page
            end = start + per_page
            sliced = rows[start:end]

            return jsonify({'ok': True, 'rows': sliced, 'total': total, 'page': page, 'per_page': per_page, 'pages': pages})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    # CREAR (POST)
    if not can_access_maestros(session.get('role_name')):
        return jsonify({'ok': False, 'error': 'No autorizado'}), 403
    data = request.get_json(silent=True) or {}
    try:
        if entidad == 'clases':
            from controllers.maestros.clases import insert_clase
            nid = insert_clase(data.get('nombre'), data.get('costo_soat'))
            return jsonify({'ok': True, 'id': nid})
        if entidad == 'usos':
            from controllers.maestros.usos import insert_uso
            nid = insert_uso(data.get('nombre'))
            return jsonify({'ok': True, 'id': nid})
        if entidad == 'marcas':
            from controllers.maestros.marcas import insert_marca
            nid = insert_marca(data.get('nombre'))
            return jsonify({'ok': True, 'id': nid})
        if entidad == 'modelos':
            from controllers.maestros.modelos import insert_modelo
            # marca_id puede venir como string; controlador debe manejarlo
            nid = insert_modelo(data.get('marca_id'), data.get('nombre'))
            return jsonify({'ok': True, 'id': nid})
        if entidad == 'ramos':
            from controllers.maestros.ramos import insert_ramo
            nid = insert_ramo(data.get('nombre'), data.get('abreviacion'), data.get('codigo'), data.get('grupo'))
            return jsonify({'ok': True, 'id': nid})
        if entidad == 'productos':
            from controllers.maestros.productos import insert_producto
            nid = insert_producto(data.get('idRamo') or data.get('ramo_id') or data.get('ramo'), data.get('nombre'), data.get('codigo'), data.get('grupo'))
            return jsonify({'ok': True, 'id': nid})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

    return jsonify({'ok': False, 'error': 'Entidad no soportada'}), 400

@bp.route('/api/polizas/anular', methods=['POST'])
@require_permission(can_restore, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def api_polizas_anular():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    data = request.get_json(silent=True) or {}
    pid = data.get('idPoliza')
    motivo = (data.get('motivo') or '').strip()
    fecha_anulacion = data.get('fechaAnulacion') or None
    if not pid:
        return jsonify({'ok': False, 'error': 'ID requerido'}), 400
    if not motivo:
        return jsonify({'ok': False, 'error': 'Motivo requerido'}), 400
    if len(motivo) > 200:
        return jsonify({'ok': False, 'error': 'El motivo supera 200 caracteres'}), 400
    if fecha_anulacion:
        try:
            from datetime import datetime
            datetime.strptime(fecha_anulacion, '%Y-%m-%d')
        except Exception:
            return jsonify({'ok': False, 'error': 'Fecha de anulación inválida'}), 400
    try:
        from models.db import get_connection
        cnx = get_connection()
        try:
            cur = cnx.cursor(buffered=True)
        except TypeError:
            cur = cnx.cursor()

        # El SP a veces no reporta bien sus affected_rows vía stored_results(); en vez de
        # confiar solo en ese conteo, guardamos el estado real de "anulado" antes de tocar
        # nada para poder distinguir "ya estaba anulada" de "la acabamos de anular".
        cur.execute("SELECT anulado FROM polizas WHERE idPoliza=%s", (pid,))
        _before_row = cur.fetchone()
        was_anulado_before = bool(_before_row and _before_row[0])

        try:
            cur.execute(
                "CALL sp_anular_poliza(%s,%s,%s,%s)",
                (pid, session.get('user'), motivo, fecha_anulacion)
            )
            affected = 0
            try:
                for result in cur.stored_results():
                    row = result.fetchone()
                    if row is not None:
                        try:
                            # row can be tuple or dict depending on cursor
                            affected = int(row[0])
                        except Exception:
                            try:
                                affected = int(row.get('affected_rows', 0))
                            except Exception:
                                affected = 0
                # Drain any remaining result sets
                while cur.nextset():
                    pass
            except Exception:
                pass
            cur.execute(
                "CALL sp_anular_cuotas_por_poliza(%s,%s)",
                (pid, session.get('user'))
            )
            try:
                for result in cur.stored_results():
                    row = result.fetchone()
                    if row is not None:
                        try:
                            int(row[0])
                        except Exception:
                            try:
                                int(row.get('affected_rows', 0))
                            except Exception:
                                pass
                while cur.nextset():
                    pass
            except Exception:
                pass
            cnx.commit()
            if affected > 0:
                pol_num = None
                try:
                    cur.execute("""
                        SELECT TRIM(COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                            poliza
                        )) FROM polizas WHERE idPoliza = %s LIMIT 1
                    """, (pid,))
                    pol_row = cur.fetchone()
                    pol_num = (pol_row[0] if pol_row else None) or None
                except Exception:
                    pol_num = None
                cur.close()
                cnx.close()
                from utils.notify import notify_deletion
                notify_deletion(session.get('user'), 'PÓLIZA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                return jsonify({'ok': True})
            # Fallback si el SP retornó 0 afectados: verificar estado y aplicar UPDATE directo
            cur.execute("SELECT anulado, activo FROM polizas WHERE idPoliza=%s", (pid,))
            st = cur.fetchone()
            if st is None:
                cur.close()
                cnx.close()
                return jsonify({'ok': False, 'error': 'Póliza no encontrada'}), 400
            # Intentar actualizar directamente conservando la lógica
            cur.execute(
                "UPDATE polizas SET anulado=1, estado='ANULADA', motivo=%s, usuario_edicion=%s WHERE idPoliza=%s AND (anulado=0 OR anulado IS NULL) AND (activo=1 OR activo IS NULL)",
                (motivo, session.get('user'), pid)
            )
            affected_update = cur.rowcount
            if affected_update > 0:
                try:
                    cur.execute(
                        "INSERT INTO poliza_anulaciones (poliza_id, poliza_numero, usuario, motivo, fecha_anulacion) "
                        "SELECT idPoliza, poliza, %s, %s, COALESCE(%s, CURDATE()) FROM polizas WHERE idPoliza=%s",
                        (session.get('user'), motivo, fecha_anulacion, pid)
                    )
                except Exception:
                    pass
            pol_num = None
            try:
                cur.execute("""
                    SELECT TRIM(
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                            poliza
                        )
                    ) AS poliza_num
                    FROM polizas
                    WHERE idPoliza = %s
                    LIMIT 1
                """, (pid,))
                pol_row = cur.fetchone()
                pol_num = (pol_row[0] if pol_row else None) or None
            except Exception:
                pol_num = None
            if pol_num:
                cur.execute("""
                    UPDATE cuotas
                    SET activo = 0,
                        anular = 0,
                        usuario_edicion = %s
                    WHERE poliza_id = %s
                       OR TRIM(COALESCE(
                           CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                           CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                           poliza
                       )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                """, (session.get('user'), pid, pol_num))
            else:
                cur.execute(
                    "UPDATE cuotas SET activo=0, anular=0, usuario_edicion=%s WHERE poliza_id=%s",
                    (session.get('user'), pid)
                )
            cnx.commit()
            ok = affected_update > 0
            cur.close()
            cnx.close()
            if ok:
                from utils.notify import notify_deletion
                notify_deletion(session.get('user'), 'PÓLIZA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                return jsonify({'ok': True})
            # Comprobación idempotente: si ya está anulada, consideramos éxito
            cnx = get_connection()
            try:
                cur = cnx.cursor(buffered=True)
            except TypeError:
                cur = cnx.cursor()
            cur.execute("SELECT anulado FROM polizas WHERE idPoliza=%s", (pid,))
            st2 = cur.fetchone()
            cur.close()
            cnx.close()
            try:
                already = (int(st2[0]) == 1) if st2 is not None else False
            except Exception:
                try:
                    already = (int(st2.get('anulado', 0)) == 1)
                except Exception:
                    already = False
            if already:
                if was_anulado_before:
                    print(f'[anular] idPoliza/idPrima {pid} ya estaba anulado, no se reenvía alerta')
                else:
                    from utils.notify import notify_deletion
                    notify_deletion(session.get('user'), 'PÓLIZA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                return jsonify({'ok': True, 'status': 'already_anulled'})
            return jsonify({'ok': False, 'error': 'No se pudo anular'}), 400
        except Exception:
            try:
                cur.execute(
                    "UPDATE polizas SET anulado=1, estado='ANULADA', motivo=%s, usuario_edicion=%s WHERE idPoliza=%s AND activo=1 AND anulado=0",
                    (motivo, session.get('user'), pid)
                )
                affected_update = cur.rowcount
                if affected_update > 0:
                    try:
                        cur.execute(
                            "INSERT INTO poliza_anulaciones (poliza_id, poliza_numero, usuario, motivo, fecha_anulacion) "
                            "SELECT idPoliza, poliza, %s, %s, COALESCE(%s, CURDATE()) FROM polizas WHERE idPoliza=%s",
                            (session.get('user'), motivo, fecha_anulacion, pid)
                        )
                    except Exception:
                        pass
                pol_num = None
                try:
                    cur.execute("""
                        SELECT TRIM(
                            COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                poliza
                            )
                        ) AS poliza_num
                        FROM polizas
                        WHERE idPoliza = %s
                        LIMIT 1
                    """, (pid,))
                    pol_row = cur.fetchone()
                    pol_num = (pol_row[0] if pol_row else None) or None
                except Exception:
                    pol_num = None
                if pol_num:
                    cur.execute("""
                        UPDATE cuotas
                        SET activo = 0,
                            anular = 0,
                            usuario_edicion = %s
                        WHERE poliza_id = %s
                           OR TRIM(COALESCE(
                               CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                               CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                               poliza
                           )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                    """, (session.get('user'), pid, pol_num))
                else:
                    cur.execute(
                        "UPDATE cuotas SET activo=0, anular=0, usuario_edicion=%s WHERE poliza_id=%s",
                        (session.get('user'), pid)
                    )
                cnx.commit()
                ok = affected_update > 0
                cur.close()
                cnx.close()
                if ok:
                    from utils.notify import notify_deletion
                    notify_deletion(session.get('user'), 'PÓLIZA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                    return jsonify({'ok': True})
                # Comprobación idempotente: ya anulada
                cnx = get_connection()
                try:
                    cur = cnx.cursor(buffered=True)
                except TypeError:
                    cur = cnx.cursor()
                cur.execute("SELECT anulado FROM polizas WHERE idPoliza=%s", (pid,))
                st2 = cur.fetchone()
                cur.close()
                cnx.close()
                try:
                    already = (int(st2[0]) == 1) if st2 is not None else False
                except Exception:
                    try:
                        already = (int(st2.get('anulado', 0)) == 1)
                    except Exception:
                        already = False
                if already:
                    if was_anulado_before:
                        print(f'[anular] idPoliza {pid} ya estaba anulado, no se reenvía alerta')
                    else:
                        from utils.notify import notify_deletion
                        notify_deletion(session.get('user'), 'PÓLIZA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                    return jsonify({'ok': True, 'status': 'already_anulled'})
                return jsonify({'ok': False, 'error': 'No se pudo anular'}), 400
            except Exception as e:
                try:
                    cur.close()
                    cnx.close()
                except Exception:
                    pass
                return jsonify({'ok': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/primas/anular', methods=['POST'])
@require_permission(can_restore, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def api_primas_anular():
    """Anula una prima específica (fila en polizas) y solo sus cuotas ligadas,
    sin anular la póliza padre ni otras primas del mismo número de póliza."""
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    data = request.get_json(silent=True) or {}
    pid = data.get('idPrima') or data.get('idPoliza')
    motivo = (data.get('motivo') or '').strip()
    fecha_anulacion = data.get('fechaAnulacion') or None
    if not pid:
        return jsonify({'ok': False, 'error': 'ID requerido'}), 400
    if not motivo:
        return jsonify({'ok': False, 'error': 'Motivo requerido'}), 400
    if len(motivo) > 200:
        return jsonify({'ok': False, 'error': 'El motivo supera 200 caracteres'}), 400
    if fecha_anulacion:
        try:
            from datetime import datetime
            datetime.strptime(fecha_anulacion, '%Y-%m-%d')
        except Exception:
            return jsonify({'ok': False, 'error': 'Fecha de anulación inválida'}), 400
    try:
        from models.db import get_connection
        cnx = get_connection()
        try:
            cur = cnx.cursor(buffered=True)
        except TypeError:
            cur = cnx.cursor()

        # Ver nota en api_polizas_anular: el SP no siempre reporta bien affected_rows,
        # así que guardamos el estado real antes de tocar nada.
        cur.execute("SELECT prima_anulada FROM polizas WHERE idPoliza=%s", (pid,))
        _before_row = cur.fetchone()
        was_anulado_before = bool(_before_row and _before_row[0])

        try:
            cur.execute(
                "CALL sp_anular_prima(%s, %s, %s, %s)",
                (pid, session.get('user'), motivo, fecha_anulacion)
            )
            affected = 0
            try:
                for result in cur.stored_results():
                    row = result.fetchone()
                    if row is not None:
                        try:
                            affected = int(row[0])
                        except Exception:
                            try:
                                affected = int(row.get('affected_rows', 0))
                            except Exception:
                                affected = 0
                while cur.nextset():
                    pass
            except Exception:
                pass
            cnx.commit()
            if affected > 0:
                pol_num = None
                try:
                    cur.execute("""
                        SELECT TRIM(COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                            CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                            poliza
                        )) FROM polizas WHERE idPoliza = %s LIMIT 1
                    """, (pid,))
                    pol_row = cur.fetchone()
                    pol_num = (pol_row[0] if pol_row else None) or None
                except Exception:
                    pol_num = None
                cur.close()
                cnx.close()
                from utils.notify import notify_deletion
                notify_deletion(session.get('user'), 'PRIMA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                return jsonify({'ok': True})
            # Fallback: verificar si ya estaba anulada (idempotente)
            cur.execute("SELECT prima_anulada, activo FROM polizas WHERE idPoliza=%s", (pid,))
            st = cur.fetchone()
            if st is None:
                cur.close()
                cnx.close()
                return jsonify({'ok': False, 'error': 'Prima no encontrada'}), 400
            try:
                already = (int(st[0]) == 1) if st is not None else False
            except Exception:
                try:
                    already = (int(st.get('prima_anulada', 0)) == 1)
                except Exception:
                    already = False
            pol_num = None
            try:
                cur.execute("""
                    SELECT TRIM(COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                        CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                        poliza
                    )) FROM polizas WHERE idPoliza = %s LIMIT 1
                """, (pid,))
                pol_row = cur.fetchone()
                pol_num = (pol_row[0] if pol_row else None) or None
            except Exception:
                pol_num = None
            cur.close()
            cnx.close()
            if already:
                if was_anulado_before:
                    print(f'[anular] idPrima {pid} ya estaba anulado, no se reenvía alerta')
                else:
                    from utils.notify import notify_deletion
                    notify_deletion(session.get('user'), 'PRIMA', pol_num or f'ID {pid}', evento='anulacion', motivo=motivo)
                return jsonify({'ok': True, 'status': 'already_anulled'})
            return jsonify({'ok': False, 'error': 'No se pudo anular la prima'}), 400
        except Exception as e:
            try:
                cnx.rollback()
                cur.close()
                cnx.close()
            except Exception:
                pass
            return jsonify({'ok': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/maestros/<entidad>/<int:id_>', methods=['DELETE'])
@require_permission(can_access_maestros, response_mode='json')
def api_maestros_delete(entidad, id_):
    """Eliminar registro maestro por entidad e id."""
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    entidad = (entidad or '').lower()
    try:
        if entidad == 'clases':
            from controllers.maestros.clases import delete_clase
            deleted = delete_clase(id_)
            return jsonify({'ok': True, 'deleted': deleted})
        if entidad == 'usos':
            from controllers.maestros.usos import delete_uso
            deleted = delete_uso(id_)
            return jsonify({'ok': True, 'deleted': deleted})
        if entidad == 'marcas':
            from controllers.maestros.marcas import delete_marca
            deleted = delete_marca(id_)
            return jsonify({'ok': True, 'deleted': deleted})
        if entidad == 'modelos':
            from controllers.maestros.modelos import delete_modelo
            deleted = delete_modelo(id_)
            return jsonify({'ok': True, 'deleted': deleted})
        if entidad == 'ajustadores' or entidad == 'ajustador':
            from controllers.ajustadores.ajustadores import delete_ajustador
            deleted = delete_ajustador(id_)
            return jsonify({'ok': True, 'deleted': deleted})
        if entidad == 'ramos':
            from controllers.maestros.ramos import delete_ramo
            deleted = delete_ramo(id_)
            return jsonify({'ok': True, 'deleted': deleted})
        if entidad == 'productos':
            from controllers.maestros.productos import delete_producto
            deleted = delete_producto(id_)
            return jsonify({'ok': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

    return jsonify({'ok': False, 'error': 'Entidad no soportada'}), 400

@bp.route('/api/polizas/restaurar', methods=['POST'])
@require_permission(can_restore, response_mode='json', ownership_check_fn=poliza_owner_from_request)
def api_polizas_restaurar():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    data = request.get_json(silent=True) or {}
    pid = data.get('idPoliza')
    if not pid:
        return jsonify({'ok': False, 'error': 'ID requerido'}), 400
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()
        try:
            cur.execute("CALL sp_restore_poliza(%s,%s)", (pid, session.get('user')))
            affected = 0
            try:
                for result in cur.stored_results():
                    row = result.fetchone()
                    if row is not None:
                        try:
                            affected = int(row[0])
                        except Exception:
                            try:
                                affected = int(row.get('affected_rows', 0))
                            except Exception:
                                affected = 0
                while cur.nextset():
                    pass
            except Exception:
                pass
            cnx.commit()
            if affected > 0:
                try:
                    cur.execute("""
                        SELECT TRIM(
                            COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                poliza
                            )
                        ) AS poliza_num
                        FROM polizas
                        WHERE idPoliza = %s
                        LIMIT 1
                    """, (pid,))
                    pol_row = cur.fetchone()
                    pol_num = (pol_row[0] if pol_row else None) or None
                    if pol_num:
                        cur.execute("""
                            UPDATE cuotas
                            SET activo = 1,
                                anular = 1,
                                usuario_edicion = %s
                            WHERE activo = 0
                              AND (
                                poliza_id = %s
                                OR TRIM(COALESCE(
                                    CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                    CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                    poliza
                                )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                              )
                        """, (session.get('user'), pid, pol_num))
                        cnx.commit()
                except Exception:
                    pass
                cur.close()
                cnx.close()
                return jsonify({'ok': True})
            # Fallback cuando SP devuelve 0 afectados
            cur.execute("SELECT anulado, activo FROM polizas WHERE idPoliza=%s", (pid,))
            st = cur.fetchone()
            if st is None:
                cur.close()
                cnx.close()
                return jsonify({'ok': False, 'error': 'Póliza no encontrada'}), 400
            cur.execute(
                "UPDATE polizas SET anulado=0, activo=1, estado='VIGENTE', usuario_edicion=%s WHERE idPoliza=%s AND (anulado=1 OR activo=0)",
                (session.get('user'), pid)
            )
            cnx.commit()
            ok = cur.rowcount > 0
            if ok:
                try:
                    cur.execute("""
                        SELECT TRIM(
                            COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                poliza
                            )
                        ) AS poliza_num
                        FROM polizas
                        WHERE idPoliza = %s
                        LIMIT 1
                    """, (pid,))
                    pol_row = cur.fetchone()
                    pol_num = (pol_row[0] if pol_row else None) or None
                    if pol_num:
                        cur.execute("""
                            UPDATE cuotas
                            SET activo = 1,
                                anular = 1,
                                usuario_edicion = %s
                            WHERE activo = 0
                              AND (
                                poliza_id = %s
                                OR TRIM(COALESCE(
                                    CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                    CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                    poliza
                                )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                              )
                        """, (session.get('user'), pid, pol_num))
                        cnx.commit()
                except Exception:
                    pass
            cur.close()
            cnx.close()
            if ok:
                return jsonify({'ok': True})
            # Comprobación idempotente: si ya está restaurada, éxito
            cnx = get_connection()
            cur = cnx.cursor()
            cur.execute("SELECT anulado FROM polizas WHERE idPoliza=%s", (pid,))
            st2 = cur.fetchone()
            cur.close()
            cnx.close()
            try:
                already = (int(st2[0]) == 0) if st2 is not None else False
            except Exception:
                try:
                    already = (int(st2.get('anulado', 1)) == 0)
                except Exception:
                    already = False
            if already:
                return jsonify({'ok': True, 'status': 'already_restored'})
            return jsonify({'ok': False, 'error': 'No se pudo restaurar'}), 400
        except Exception:
            try:
                cur.execute(
                    "UPDATE polizas SET anulado=0, activo=1, estado='VIGENTE', usuario_edicion=%s WHERE idPoliza=%s AND (anulado=1 OR activo=0)",
                    (session.get('user'), pid)
                )
                cnx.commit()
                ok = cur.rowcount > 0
                if ok:
                    try:
                        cur.execute("""
                            SELECT TRIM(
                                COALESCE(
                                    CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                    CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                    poliza
                                )
                            ) AS poliza_num
                            FROM polizas
                            WHERE idPoliza = %s
                            LIMIT 1
                        """, (pid,))
                        pol_row = cur.fetchone()
                        pol_num = (pol_row[0] if pol_row else None) or None
                        if pol_num:
                            cur.execute("""
                                UPDATE cuotas
                                SET activo = 1,
                                    anular = 1,
                                    usuario_edicion = %s
                                WHERE activo = 0
                                  AND (
                                    poliza_id = %s
                                    OR TRIM(COALESCE(
                                        CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                        CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                        poliza
                                    )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                                  )
                            """, (session.get('user'), pid, pol_num))
                            cnx.commit()
                    except Exception:
                        pass
                cur.close()
                cnx.close()
                if ok:
                    return jsonify({'ok': True})
                # Comprobación idempotente
                cnx = get_connection()
                cur = cnx.cursor()
                cur.execute("SELECT anulado FROM polizas WHERE idPoliza=%s", (pid,))
                st2 = cur.fetchone()
                cur.close()
                cnx.close()
                try:
                    already = (int(st2[0]) == 0) if st2 is not None else False
                except Exception:
                    try:
                        already = (int(st2.get('anulado', 1)) == 0)
                    except Exception:
                        already = False
                if already:
                    return jsonify({'ok': True, 'status': 'already_restored'})
                return jsonify({'ok': False, 'error': 'No se pudo restaurar'}), 400
            except Exception as e:
                try:
                    cur.close()
                    cnx.close()
                except Exception:
                    pass
                return jsonify({'ok': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/polizas/anuladas', methods=['GET'])
def api_polizas_anuladas_list():
    if 'user' not in session:
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    q = request.args.get('q') or None
    desde = request.args.get('desde') or None
    hasta = request.args.get('hasta') or None
    page = request.args.get('page') or 1
    per_page = request.args.get('per_page') or 15
    try:
        from controllers.polizas import get_polizas_anuladas_filtered
        data = get_polizas_anuladas_filtered(q, desde, hasta, page=page, per_page=per_page)
        return jsonify({
            'ok': True,
            'rows': data.get('rows', []),
            'total': data.get('total', 0),
            'page': data.get('page', 1),
            'per_page': data.get('per_page', 15),
            'pages': data.get('pages', 1),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/cuotas/anuladas', methods=['GET'])
@require_permission(lambda r: r == Roles.BROKER, response_mode='json')
def api_cuotas_anuladas_list():
    q = request.args.get('q') or None
    desde = request.args.get('desde') or None
    hasta = request.args.get('hasta') or None
    page = request.args.get('page') or 1
    per_page = request.args.get('per_page') or 15
    try:
        from controllers.cuotas.cuotas import get_cuotas_anuladas_filtered
        data = get_cuotas_anuladas_filtered(q, desde, hasta, page=page, per_page=per_page)
        return jsonify({
            'ok': True,
            'rows': data.get('rows', []),
            'total': data.get('total', 0),
            'page': data.get('page', 1),
            'per_page': data.get('per_page', 15),
            'pages': data.get('pages', 1),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/maestros/vendedores/save', methods=['POST'])
@require_permission(can_create, response_mode='redirect')
def save_vendedor():
    if 'user' not in session:
        return redirect(url_for('login'))
    codigo_agente   = (request.form.get('codigo_agente') or '').strip()
    nombre_vendedor = (request.form.get('nombre_vendedor') or '').strip()
    tipo_menor      = request.form.get('tipo_menor') or '0'
    tipo_regular    = request.form.get('tipo_regular') or '0'
    if not codigo_agente or not nombre_vendedor:
        return redirect(url_for('main.menu_page', page='maestros-vendedores'))
    from controllers.maestros.vendedores import insertar_vendedor
    insertar_vendedor(codigo_agente, nombre_vendedor, tipo_menor, tipo_regular)
    return redirect(url_for('main.menu_page', page='maestros-vendedores'))


@bp.route('/maestros/vendedores/<int:id>/update', methods=['POST'])
@require_permission(can_edit, response_mode='redirect')
def update_vendedor(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    codigo_agente   = (request.form.get('codigo_agente') or '').strip()
    nombre_vendedor = (request.form.get('nombre_vendedor') or '').strip()
    tipo_menor      = request.form.get('tipo_menor') or '0'
    tipo_regular    = request.form.get('tipo_regular') or '0'
    estado          = request.form.get('estado') or 'ACTIVO'
    from controllers.maestros.vendedores import actualizar_vendedor
    actualizar_vendedor(id, codigo_agente, nombre_vendedor, tipo_menor, tipo_regular, estado)
    return redirect(url_for('main.menu_page', page='maestros-vendedores'))


@bp.route('/maestros/vendedores/<int:id>/delete', methods=['POST'])
@require_permission(can_delete, response_mode='redirect')
def delete_vendedor(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    from controllers.maestros.vendedores import eliminar_vendedor
    eliminar_vendedor(id)
    return redirect(url_for('main.menu_page', page='maestros-vendedores'))


@bp.route('/FacturaVentas')
def factura_ventas():
    return render_template('view/FacturaVentas.html')




