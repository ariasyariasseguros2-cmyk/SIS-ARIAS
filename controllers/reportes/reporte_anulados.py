from flask import Blueprint, render_template, request, jsonify, session
from models.db import get_connection
from utils.rbac import Roles
import traceback

bp = Blueprint('reporte_anulados', __name__)


def get_reporte_anulados(search='', desde=None, hasta=None):
    debug = {'params_recibidos': {'search': search, 'desde': desde, 'hasta': hasta}}
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # A que BD/usuario esta pegando realmente esta conexion: env vars pueden
        # sobreescribir appsettings.json en produccion sin que se note.
        cursor.execute("SELECT DATABASE() AS db, CURRENT_USER() AS db_user, @@hostname AS db_host")
        debug['conexion'] = cursor.fetchone()

        # Conteos crudos, sin pasar por el SP, para descartar que el SP este
        # filtrando de mas (compara esto contra lo que ves en los otros reportes).
        cursor.execute("SELECT COUNT(*) AS n FROM polizas WHERE anulado = 1")
        debug['polizas_anulado_1'] = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) AS n FROM polizas WHERE prima_anulada = 1")
        debug['polizas_prima_anulada_1'] = cursor.fetchone()['n']
        cursor.execute("SELECT COUNT(*) AS n FROM cuotas WHERE activo = 0")
        debug['cuotas_activo_0'] = cursor.fetchone()['n']
        cursor.execute("""
            SELECT COUNT(*) AS n FROM information_schema.ROUTINES
            WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_TYPE = 'PROCEDURE'
              AND ROUTINE_NAME = 'sp_reporte_anulados_general'
        """)
        debug['sp_existe'] = cursor.fetchone()['n'] > 0

        cursor.callproc('sp_reporte_anulados_general', [search or None, desde or None, hasta or None])

        rows = []
        result_sets = 0
        for result in cursor.stored_results():
            result_sets += 1
            rows = result.fetchall()
        debug['result_sets'] = result_sets
        debug['row_count'] = len(rows)

        cursor.close()
        conn.close()

        for r in rows:
            if r.get('fecha_anulacion') and hasattr(r['fecha_anulacion'], 'strftime'):
                r['fecha_anulacion'] = r['fecha_anulacion'].strftime('%d/%m/%Y %H:%M')
        return rows, None, debug
    except Exception as e:
        print(f"Error fetching reporte anulados: {e}")
        traceback.print_exc()
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass
        return [], f"{type(e).__name__}: {e}", debug


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

    data, db_error, debug = get_reporte_anulados(search, desde, hasta)
    # debug/db_error: temporal para diagnosticar el reporte en blanco en
    # produccion (ver consola del navegador, F12). Quitar cuando se resuelva.
    return jsonify({'data': data, 'db_error': db_error, 'debug': debug})
