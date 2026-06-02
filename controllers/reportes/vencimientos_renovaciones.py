from flask import Blueprint, request, jsonify, session
from models.db import get_connection
from utils.rbac import Roles

bp = Blueprint('reporte_vencimientos', __name__, url_prefix='/api/reportes')

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
    
    # Handle empty strings as None for dates
    if not fecha_desde: fecha_desde = None
    if not fecha_hasta: fecha_hasta = None
    if not estado: estado = None
    
    # Debug print
    print(f"Reporte Vencimientos Params: user='{usuario}', ejecutivo='{ejecutivo}', estado='{estado}', ramo='{ramo}', desde={fecha_desde}, hasta={fecha_hasta}")

    data = get_vencimientos(usuario, estado, fecha_desde, fecha_hasta, ramo)

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
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # usuario puede ser una lista separada por comas, el SP debe manejarlo o aquí procesarlo?
        # El SP lo manejará con FIND_IN_SET si le paso un string
        cursor.callproc('sp_reporte_vencimientos', (usuario, estado, fecha_desde, fecha_hasta, ramo))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
            
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching vencimientos: {e}")
        return []
