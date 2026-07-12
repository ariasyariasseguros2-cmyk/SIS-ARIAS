from flask import Blueprint, render_template, request, jsonify, session
from models.db import get_connection
from utils.rbac import Roles
import traceback

bp = Blueprint('reporte_anulados', __name__)


def get_reporte_anulados(search='', desde=None, hasta=None):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_reporte_anulados_general', [search or None, desde or None, hasta or None])
        rows = []
        for result in cursor.stored_results():
            rows = result.fetchall()
        cursor.close()
        conn.close()

        for r in rows:
            if r.get('fecha_anulacion') and hasattr(r['fecha_anulacion'], 'strftime'):
                r['fecha_anulacion'] = r['fecha_anulacion'].strftime('%d/%m/%Y %H:%M')
        return rows
    except Exception as e:
        print(f"Error fetching reporte anulados: {e}")
        traceback.print_exc()
        return []


@bp.route('/reportes/reporte-anulados', methods=['GET'])
def index():
    return render_template('view/reportes/reporte-anulados.html')


@bp.route('/api/reportes/anulados', methods=['GET'])
def api_search():
    if 'user' not in session:
        return {'ok': False, 'error': 'No autenticado'}, 401
    if session.get('role_name') == Roles.SUB_AGENTE:
        return {'ok': False, 'error': 'No autorizado'}, 403

    search = request.args.get('search', '').strip()
    desde = request.args.get('desde', '').strip() or None
    hasta = request.args.get('hasta', '').strip() or None

    data = get_reporte_anulados(search, desde, hasta)
    return jsonify({'data': data})
