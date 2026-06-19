from flask import request
from models.db import get_connection

def hard_delete_poliza_route():
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        if not data:
            data = {}

        id_poliza = data.get('idPoliza')
        if not id_poliza:
            return {'ok': False, 'errors': ['ID de póliza requerido']}, 400

        cnx = get_connection()
        if not cnx:
            return {'ok': False, 'errors': ['Error de conexión a BD']}, 500

        cursor = cnx.cursor()
        # Eliminar cuotas de la póliza
        cursor.execute("DELETE FROM cuotas WHERE poliza_id = %s", (id_poliza,))
        # Eliminar registro de anulaciones
        cursor.execute("DELETE FROM poliza_anulaciones WHERE poliza_id = %s", (id_poliza,))
        # Eliminar la póliza
        cursor.execute("DELETE FROM polizas WHERE idPoliza = %s", (id_poliza,))
        affected = cursor.rowcount
        cnx.commit()
        cursor.close()
        cnx.close()

        if affected > 0:
            return {'ok': True}, 200
        return {'ok': False, 'errors': ['Póliza no encontrada']}, 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'ok': False, 'errors': [str(e)]}, 500
