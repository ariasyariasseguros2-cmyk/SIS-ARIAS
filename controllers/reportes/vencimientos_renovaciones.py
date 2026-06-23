import traceback

from flask import Blueprint, request, jsonify, session
import mysql.connector
from models.db import get_connection
from utils.rbac import Roles
from utils.financiamiento_grupal_reportes import enrich_rows_with_fg_metadata

bp = Blueprint('reporte_vencimientos', __name__, url_prefix='/api/reportes')


def _collect_cursor_results(cursor):
    results = []
    try:
        if getattr(cursor, 'with_rows', False):
            results.append(cursor.fetchall() or [])
    except Exception:
        results = []

    while True:
        try:
            has_next = cursor.nextset()
        except Exception:
            break
        if not has_next:
            break
        try:
            if getattr(cursor, 'with_rows', False):
                results.append(cursor.fetchall() or [])
        except Exception:
            continue

    return results


def _run_vencimientos_call(cursor, params):
    cursor.execute(
        "CALL sp_reporte_vencimientos(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        params,
    )
    results = _collect_cursor_results(cursor)
    total = 0
    rows = []
    if results:
        first = results[0] or []
        if first and isinstance(first[0], dict):
            try:
                total = int(first[0].get('total') or 0)
            except Exception:
                total = 0
    if len(results) > 1:
        rows = results[1] or []
    return {'rows': rows, 'total': total}


def _get_session_ejecutivo_nombre():
    username = (session.get('user') or '').strip()
    if not username:
        return ''

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(e.nombre), ''), '')
            FROM usuarios u
            LEFT JOIN ejecutivos e ON e.idEjecutivo = u.id_ejecutivo
            WHERE u.username = %s
            LIMIT 1
            """,
            (username,),
        )
        row = cur.fetchone()
        return (row[0] or '').strip() if row and row[0] else ''
    except Exception:
        return ''
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

@bp.route('/usuarios', methods=['GET'])
def api_usuarios():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT DISTINCT TRIM(p.usuario_registro) AS usuario
            FROM polizas p
            WHERE p.activo = 1
              AND (p.anulado = 0 OR p.anulado IS NULL)
              AND COALESCE(p.prima_anulada, 0) = 0
              AND p.usuario_registro IS NOT NULL
              AND TRIM(p.usuario_registro) <> ''
            ORDER BY TRIM(p.usuario_registro) ASC
            """
        )
        rows = cursor.fetchall() or []
        cursor.close()
        conn.close()
        return jsonify([{"username": r.get("usuario"), "nombre": r.get("usuario")} for r in rows])
    except Exception as e:
        print(f"Error fetching usuarios: {e}")
        return jsonify([]), 500

@bp.route('/ramos', methods=['GET'])
def api_ramos():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_listar_ramos')
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify(results)
    except Exception as e:
        print(f"Error fetching ramos: {e}")
        return jsonify([]), 500

@bp.route('/ejecutivos', methods=['GET'])
def api_ejecutivos():
    try:
        from controllers.ejecutivos import get_ejecutivos
        rows = get_ejecutivos() or []
        out = []
        for r in rows:
            if isinstance(r, dict):
                nombre = (r.get('nombre') or '').strip()
            else:
                nombre = ''
            if not nombre:
                continue
            out.append({'nombre': nombre})
        out = sorted(out, key=lambda x: x.get('nombre', ''))
        return jsonify(out)
    except Exception as e:
        print(f"Error fetching ejecutivos: {e}")
        return jsonify([]), 500

@bp.route('/vencimientos-renovaciones', methods=['GET'])
def api_vencimientos():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    role = session.get('role_name')
    if role == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    usuario = request.args.get('usuario', '').strip()
    ejecutivo = request.args.get('ejecutivo', '').strip()
    estado = request.args.get('estado', '').strip()
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    ramo = request.args.get('ramo', '').strip()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int) or 1
    limit = request.args.get('limit', 20, type=int) or 20
    session_ejecutivo = _get_session_ejecutivo_nombre()
    page = max(1, page)
    limit = max(1, min(limit, 200))
    
    # Handle empty strings as None for dates
    if not fecha_desde: fecha_desde = None
    if not fecha_hasta: fecha_hasta = None
    if not estado: estado = None
    if not ejecutivo and role != Roles.BROKER and session_ejecutivo:
        ejecutivo = session_ejecutivo
    
    # Debug print
    print(f"Reporte Vencimientos Params: user='{usuario}', ejecutivo='{ejecutivo}', estado='{estado}', ramo='{ramo}', q='{search}', page={page}, limit={limit}, desde={fecha_desde}, hasta={fecha_hasta}")

    result = get_vencimientos(usuario, ejecutivo, estado, fecha_desde, fecha_hasta, ramo, search, page, limit)
    data = result.get('rows', [])
    total = int(result.get('total') or 0)
    enrich_rows_with_fg_metadata(data, poliza_id_keys=("idPoliza", "poliza_id"))

    if role == Roles.OPERADOR:
        # Eliminar columnas de comisiones
        for row in data:
            keys_to_remove = [k for k in row.keys() if 'comision' in k.lower()]
            for k in keys_to_remove:
                row.pop(k, None)

    pages = max(1, (total + limit - 1) // limit) if total else 1
    return jsonify({
        'rows': data,
        'total': total,
        'page': page,
        'per_page': limit,
        'pages': pages,
    })

def get_vencimientos(usuario, ejecutivo, estado, fecha_desde=None, fecha_hasta=None, ramo='', search='', page=1, limit=20):
    offset = max(0, (max(1, page) - 1) * max(1, limit))
    params = (usuario, ejecutivo, estado, fecha_desde, fecha_hasta, ramo, search, limit, offset)
    conn = None
    cursor = None
    try:
        conn = get_connection(read_timeout=180, write_timeout=180)
        try:
            conn.ping(reconnect=True, attempts=1, delay=0)
        except Exception:
            pass
        cursor = conn.cursor(dictionary=True)

        # En algunos entornos productivos, execute("CALL ...") devuelve resultados
        # de forma más consistente que callproc() con mysql-connector.
        results = _run_vencimientos_call(cursor, params)
        return results
    except mysql.connector.Error as e:
        print(f"[vencimientos] execute CALL fallo: {e}")
        traceback.print_exc()

        if getattr(e, 'errno', None) in (2006, 2013):
            retry_conn = None
            retry_cursor = None
            try:
                retry_conn = get_connection(read_timeout=180, write_timeout=180)
                try:
                    retry_conn.ping(reconnect=True, attempts=1, delay=0)
                except Exception:
                    pass
                retry_cursor = retry_conn.cursor(dictionary=True)
                return _run_vencimientos_call(retry_cursor, params)
            except Exception as retry_error:
                print(f"[vencimientos] retry execute CALL fallo: {retry_error}")
                traceback.print_exc()
            finally:
                if retry_cursor is not None:
                    try:
                        retry_cursor.close()
                    except Exception:
                        pass
                if retry_conn is not None:
                    try:
                        retry_conn.close()
                    except Exception:
                        pass

        try:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

            if conn is not None and getattr(conn, "is_connected", lambda: False)():
                cursor = conn.cursor(dictionary=True)
                cursor.callproc(
                    'sp_reporte_vencimientos',
                    (usuario, ejecutivo, estado, fecha_desde, fecha_hasta, ramo, search, limit, offset)
                )
                stored = [result.fetchall() or [] for result in cursor.stored_results()]
                total = 0
                rows = []
                if stored:
                    first = stored[0] or []
                    if first and isinstance(first[0], dict):
                        try:
                            total = int(first[0].get('total') or 0)
                        except Exception:
                            total = 0
                if len(stored) > 1:
                    rows = stored[1] or []
                return {'rows': rows, 'total': total}
        except Exception as fallback_error:
            print(f"[vencimientos] fallback callproc fallo: {fallback_error}")
            traceback.print_exc()
        return {'rows': [], 'total': 0}
    except Exception as e:
        print(f"[vencimientos] error no controlado: {e}")
        traceback.print_exc()
        return {'rows': [], 'total': 0}
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
