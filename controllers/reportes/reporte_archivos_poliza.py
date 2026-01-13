
from flask import Blueprint, render_template, request, jsonify
from models.db import get_connection

bp = Blueprint('reporte_archivos_poliza', __name__)

def get_reporte_archivos(search=''):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_reporte_archivos_poliza', [search])
        
        # MySQL Connector/Python returns results from callproc differently
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
            
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error fetching reporte archivos: {e}")
        return []

@bp.route('/reportes/reporte-archivos-poliza', methods=['GET'])
def index():
    return render_template('view/reportes/reporte-archivos-poliza.html')

@bp.route('/api/reportes/archivos-poliza', methods=['GET'])
def api_search():
    search = request.args.get('search', '')
    data = get_reporte_archivos(search)
    return jsonify(data)
