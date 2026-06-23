import traceback

from flask import Blueprint, request, jsonify, session
import mysql.connector
from models.db import get_connection
from utils.rbac import Roles
from utils.financiamiento_grupal_reportes import enrich_rows_with_fg_metadata

bp = Blueprint('reporte_vencimientos', __name__, url_prefix='/api/reportes')


def _collect_cursor_rows(cursor):
    rows = []
    try:
        if getattr(cursor, 'with_rows', False):
            rows = cursor.fetchall() or []
    except Exception:
        rows = []

    while True:
        try:
            has_next = cursor.nextset()
        except Exception:
            break
        if not has_next:
            break
        try:
            if getattr(cursor, 'with_rows', False):
                next_rows = cursor.fetchall() or []
                if next_rows:
                    rows = next_rows
        except Exception:
            continue

    return rows


def _run_vencimientos_call(cursor, params):
    cursor.execute(
        "CALL sp_reporte_vencimientos(%s, %s, %s, %s, %s)",
        params,
    )
    return _collect_cursor_rows(cursor)


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
    session_ejecutivo = _get_session_ejecutivo_nombre()
    
    # Handle empty strings as None for dates
    if not fecha_desde: fecha_desde = None
    if not fecha_hasta: fecha_hasta = None
    if not estado: estado = None
    if not ejecutivo and role != Roles.BROKER and session_ejecutivo:
        ejecutivo = session_ejecutivo
    
    # Debug print
    print(f"Reporte Vencimientos Params: user='{usuario}', ejecutivo='{ejecutivo}', estado='{estado}', ramo='{ramo}', desde={fecha_desde}, hasta={fecha_hasta}")

    data = get_vencimientos(usuario, estado, fecha_desde, fecha_hasta, ramo)
    enrich_rows_with_fg_metadata(data, poliza_id_keys=("idPoliza", "poliza_id"))

    # Adjuntar ejecutivo y filtrar por ejecutivo (sin tocar el SP)
    if data:
        try:
            ids = []
            for r in data:
                try:
                    pid = int(r.get('idPoliza')) if isinstance(r, dict) and r.get('idPoliza') is not None else None
                except Exception:
                    pid = None
                if pid is not None:
                    ids.append(pid)
            ids = sorted(set(ids))

            if ids:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                chunk = 900
                exec_map = {}
                doc_map = {}
                for i in range(0, len(ids), chunk):
                    batch = ids[i:i + chunk]
                    placeholders = ",".join(["%s"] * len(batch))
                    cur.execute(
                        f"""
                        SELECT
                            p.idPoliza,
                            p.ejecutivo,
                            TRIM(
                                COALESCE(
                                    CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR),
                                    CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR),
                                    c.numero_documento,
                                    ''
                                )
                            ) AS numero_documento
                        FROM polizas p
                        LEFT JOIN clientes c ON c.idCliente = p.cliente_id
                        WHERE p.idPoliza IN ({placeholders})
                        """,
                        tuple(batch),
                    )
                    for row in cur.fetchall() or []:
                        exec_map[row.get('idPoliza')] = row.get('ejecutivo')
                        doc_map[row.get('idPoliza')] = (row.get('numero_documento') or '').strip()
                cur.close()
                conn.close()

                for r in data:
                    try:
                        pid = int(r.get('idPoliza')) if r.get('idPoliza') is not None else None
                    except Exception:
                        pid = None
                    r['ejecutivo'] = exec_map.get(pid) if pid is not None else None
                    if pid is not None:
                        doc = doc_map.get(pid) or ''
                        if doc:
                            r['numero_documento'] = doc
        except Exception as e:
            print(f"[vencimientos] error attach ejecutivo: {e}")

    if ejecutivo:
        selected = [p.strip() for p in str(ejecutivo).split(",") if p.strip()]
        if selected:
            sel_set = set(selected)
            data = [r for r in (data or []) if (r.get('ejecutivo') or '') in sel_set]

    if role == Roles.OPERADOR:
        # Eliminar columnas de comisiones
        for row in data:
            keys_to_remove = [k for k in row.keys() if 'comision' in k.lower()]
            for k in keys_to_remove:
                row.pop(k, None)

    return jsonify(data)

def get_vencimientos(usuario, estado, fecha_desde=None, fecha_hasta=None, ramo=''):
    params = (usuario, estado, fecha_desde, fecha_hasta, ramo)
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
                    (usuario, estado, fecha_desde, fecha_hasta, ramo)
                )
                results = []
                for result in cursor.stored_results():
                    fetched = result.fetchall() or []
                    if fetched:
                        results = fetched
                return results
        except Exception as fallback_error:
            print(f"[vencimientos] fallback callproc fallo: {fallback_error}")
            traceback.print_exc()
        return []
    except Exception as e:
        print(f"[vencimientos] error no controlado: {e}")
        traceback.print_exc()
        return []
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
