from flask import Blueprint, request, jsonify
from models.db import get_connection

bp = Blueprint('reporte_vencimientos', __name__, url_prefix='/api/reportes')

@bp.route('/vencimientos-renovaciones', methods=['GET'])
def api_vencimientos():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        return jsonify({'error': 'Fechas requeridas'}), 400
        
    data = get_vencimientos(fecha_inicio, fecha_fin)
    return jsonify(data)

def get_vencimientos(fecha_inicio, fecha_fin):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_reporte_vencimientos', (fecha_inicio, fecha_fin))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
            
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching vencimientos: {e}")
        return []

