from flask import Blueprint, request, jsonify, session
from models.db import get_connection
from utils.rbac import Roles

bp = Blueprint('reporte_vencimientos', __name__, url_prefix='/api/reportes')

@bp.route('/usuarios', methods=['GET'])
def api_usuarios():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_listar_usuarios')
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify(results)
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

@bp.route('/vencimientos-renovaciones', methods=['GET'])
def api_vencimientos():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401

    role = session.get('role_name')
    if role == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    usuario = request.args.get('usuario', '').strip()
    estado = request.args.get('estado', '').strip()
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    ramo = request.args.get('ramo', '').strip()
    
    # Handle empty strings as None for dates
    if not fecha_desde: fecha_desde = None
    if not fecha_hasta: fecha_hasta = None
    
    # Debug print
    print(f"Reporte Vencimientos Params: user='{usuario}', estado='{estado}', ramo='{ramo}', desde={fecha_desde}, hasta={fecha_hasta}")

    data = get_vencimientos(usuario, estado, fecha_desde, fecha_hasta, ramo)

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
