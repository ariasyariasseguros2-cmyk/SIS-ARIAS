from flask import Blueprint, request, jsonify
from models.db import get_connection

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
    usuario = request.args.get('usuario', '')
    estado = request.args.get('estado', '')
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    ramo = request.args.get('ramo', '')
    
    # Handle empty strings as None
    if not fecha_desde: fecha_desde = None
    if not fecha_hasta: fecha_hasta = None
    
    data = get_vencimientos(usuario, estado, fecha_desde, fecha_hasta, ramo)
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
