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

@bp.route('/vencimientos-renovaciones', methods=['GET'])
def api_vencimientos():
    usuario = request.args.get('usuario', '')
    estado = request.args.get('estado', '')
    
    data = get_vencimientos(usuario, estado)
    return jsonify(data)

def get_vencimientos(usuario, estado):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_reporte_vencimientos', (usuario, estado))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
            
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching vencimientos: {e}")
        return []
