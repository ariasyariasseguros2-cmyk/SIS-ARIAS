from flask import session, request
from models.db import get_connection
import json

def hard_delete_cliente_route():
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        if isinstance(data, str):
            data = json.loads(data)
        if not data:
            data = {}

        id_cliente = data.get('idCliente')
        if not id_cliente:
            return {'ok': False, 'errors': ['ID de cliente requerido']}, 400

        cnx = get_connection()
        if not cnx:
            return {'ok': False, 'errors': ['Error de conexión a BD']}, 500

        cursor = cnx.cursor()
        # Eliminar cuotas relacionadas (via poliza_id en polizas del cliente)
        cursor.execute(
            "DELETE c FROM cuotas c "
            "INNER JOIN polizas p ON c.poliza_id = p.idPoliza "
            "WHERE p.cliente_id = %s",
            (id_cliente,)
        )
        # Eliminar registros relacionados con polizas del cliente
        cursor.execute(
            "DELETE pa FROM poliza_anulaciones pa "
            "INNER JOIN polizas p ON pa.poliza_id = p.idPoliza "
            "WHERE p.cliente_id = %s",
            (id_cliente,)
        )
        # Eliminar polizas del cliente
        cursor.execute("DELETE FROM polizas WHERE cliente_id = %s", (id_cliente,))
        # Eliminar cliente
        cursor.execute("DELETE FROM clientes WHERE idCliente = %s", (id_cliente,))
        affected = cursor.rowcount
        cnx.commit()
        cursor.close()
        cnx.close()

        if affected > 0:
            return {'ok': True}, 200
        return {'ok': False, 'errors': ['Cliente no encontrado']}, 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'ok': False, 'errors': [str(e)]}, 500
