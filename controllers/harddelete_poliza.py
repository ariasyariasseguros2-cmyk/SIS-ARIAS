from flask import request, session
from models.db import get_connection
from utils.notify import notify_deletion

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

        poliza_numero = None
        try:
            cursor.execute(
                """
                SELECT TRIM(
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                        CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                        poliza
                    )
                )
                FROM polizas WHERE idPoliza = %s LIMIT 1
                """,
                (id_poliza,),
            )
            row = cursor.fetchone()
            poliza_numero = (row[0] or '').strip() if row else None
        except Exception:
            poliza_numero = None

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
            user_session = session.get('user')
            usuario = user_session.get('username') if isinstance(user_session, dict) else (user_session or 'sistema')
            notify_deletion(usuario, 'PÓLIZA', poliza_numero or f'ID {id_poliza}', evento='eliminacion')
            return {'ok': True}, 200
        return {'ok': False, 'errors': ['Póliza no encontrada']}, 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'ok': False, 'errors': [str(e)]}, 500
