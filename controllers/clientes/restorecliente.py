# módulo: controllers/clientes/restorecliente.py
from flask import session, request
from models.db import get_connection
import json


def restaurar_cliente_route():
    """Endpoint para restaurar (activar) un cliente"""
    try:
        # Obtener datos del request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        # Si data es un string, parsearlo
        if isinstance(data, str):
            data = json.loads(data)

        if not data:
            data = {}

        id_cliente = data.get('idCliente') or data.get('id')

        if not id_cliente:
            return {'ok': False, 'errors': ['ID de cliente requerido']}, 400

        # Obtener usuario de la sesión
        user_session = session.get('user', {})
        if isinstance(user_session, dict):
            usuario = user_session.get('username', 'sistema')
        elif isinstance(user_session, str):
            usuario = user_session
        else:
            usuario = 'sistema'

        cnx = get_connection()
        if not cnx:
            return {'ok': False, 'errors': ['Error de conexión a BD']}, 500

        cursor = cnx.cursor()

        # Ejecutar el procedimiento almacenado
        cursor.callproc('sp_restore_cliente', [id_cliente, usuario])

        # Obtener el resultado (affected_rows)
        affected_rows = 0
        for result in cursor.stored_results():
            row = result.fetchone()
            if row:
                affected_rows = row[0]

        cnx.commit()
        cursor.close()
        cnx.close()

        if affected_rows > 0:
            return {'ok': True, 'message': 'Cliente restaurado correctamente'}, 200
        else:
            return {'ok': False, 'errors': ['Cliente no encontrado o ya estaba activo']}, 404

    except Exception as e:
        print(f"Error en restaurar_cliente_route: {e}")
        import traceback
        traceback.print_exc()
        return {'ok': False, 'errors': [str(e)]}, 500
