from flask import jsonify, request, session
from models.db import get_connection

def list_siniestros_por_poliza():
    try:
        poliza = request.args.get('poliza')

        if not poliza:
            return jsonify({'error': 'Número de póliza requerido'}), 400

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_list_siniestros_por_poliza', [poliza])

        for result in cursor.stored_results():
            siniestros = result.fetchall()

        cursor.close()
        connection.close()

        return jsonify(siniestros), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def list_siniestros():
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_list_siniestros')

        for result in cursor.stored_results():
            siniestros = result.fetchall()

        cursor.close()
        connection.close()

        return jsonify(siniestros), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_siniestro_by_id(siniestro_id):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_get_siniestro_by_id', [siniestro_id])

        siniestro = None
        for result in cursor.stored_results():
            siniestro = result.fetchone()

        cursor.close()
        connection.close()

        if not siniestro:
            return jsonify({'error': 'Siniestro no encontrado'}), 404

        # Convertir fechas DATE a string ISO format
        from datetime import date
        for key, value in siniestro.items():
            if isinstance(value, date):
                siniestro[key] = value.isoformat()

        return jsonify(siniestro), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def insert_siniestro():
    try:
        data = request.json
        usuario = session.get('user', 'sistema')

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_insert_siniestro', [
            data.get('contratante'),
            data.get('poliza'),
            data.get('cia'),
            data.get('fec_stro'),
            data.get('causa'),
            data.get('siniestro_no'),
            data.get('provision', 0.00),
            data.get('estado', 'PENDIENTE'),
            data.get('ejec'),
            data.get('ramo'),
            data.get('placa'),
            data.get('fec_gestion'),
            data.get('prox_gestion'),
            usuario
        ])

        for result in cursor.stored_results():
            inserted = result.fetchone()

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({
            'message': 'Siniestro creado exitosamente',
            'id': inserted['id']
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def update_siniestro(siniestro_id):
    try:
        data = request.json
        usuario = session.get('user', 'sistema')

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_update_siniestro', [
            siniestro_id,
            data.get('contratante'),
            data.get('poliza'),
            data.get('cia'),
            data.get('fec_stro'),
            data.get('causa'),
            data.get('siniestro_no'),
            data.get('provision', 0.00),
            data.get('estado'),
            data.get('ejec'),
            data.get('ramo'),
            data.get('placa'),
            data.get('fec_gestion'),
            data.get('prox_gestion'),
            usuario
        ])

        for result in cursor.stored_results():
            affected = result.fetchone()

        connection.commit()
        cursor.close()
        connection.close()

        if affected['affected_rows'] == 0:
            return jsonify({'error': 'Siniestro no encontrado'}), 404

        return jsonify({'message': 'Siniestro actualizado exitosamente'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def delete_siniestro(siniestro_id):
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_delete_siniestro', [siniestro_id])

        for result in cursor.stored_results():
            affected = result.fetchone()

        connection.commit()
        cursor.close()
        connection.close()

        if affected['affected_rows'] == 0:
            return jsonify({'error': 'Siniestro no encontrado'}), 404

        return jsonify({'message': 'Siniestro eliminado exitosamente'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def buscar_siniestros():
    try:
        texto = request.json.get('texto', '')

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.callproc('sp_buscar_siniestros', [texto])

        for result in cursor.stored_results():
            siniestros = result.fetchall()

        cursor.close()
        connection.close()

        return jsonify(siniestros), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
