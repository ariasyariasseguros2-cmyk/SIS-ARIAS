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
    """Obtiene un siniestro por ID con todos sus datos (incluyendo JSON)"""
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

        # Convertir fechas DATE a string ISO format y parsear JSON
        from datetime import date
        import json

        for key, value in siniestro.items():
            if isinstance(value, date):
                siniestro[key] = value.isoformat()
            # Parsear campos JSON de vuelta a objetos
            elif key in ['datos_vehiculo', 'datos_denuncia', 'datos_conductor', 'datos_copiloto', 'datos_tercero', 'gastos_presentados']:
                if value:
                    try:
                        siniestro[key] = json.loads(value)
                    except:
                        siniestro[key] = None

        return jsonify(siniestro), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def insert_siniestro():
    """Inserta un nuevo siniestro usando el SP específico según el grupo"""
    try:
        data = request.json
        usuario = session.get('user', 'sistema')
        grupo_ramo = data.get('grupo_ramo')

        import json

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Preparar campos JSON como strings JSON o NULL
        def json_or_null(value):
            if value and (isinstance(value, dict) or isinstance(value, list)):
                return json.dumps(value)
            return None

        siniestro_id = None

        # Llamar al SP específico según el grupo
        if grupo_ramo == 'RRGG':
            params = [
                data.get('poliza'),
                data.get('cia'),
                data.get('ramo'),
                data.get('contratante'),
                data.get('asegurado'),
                data.get('fec_presentacion_broker'),
                data.get('fec_aviso_cia'),
                data.get('fec_stro'),
                data.get('hora_siniestro'),
                data.get('quien_reporta'),
                data.get('email'),
                data.get('telefonos'),
                data.get('lugar_siniestro'),
                data.get('causa'),
                data.get('descripcion_hechos'),
                data.get('siniestro_no'),
                data.get('ejecutivo_cia'),
                data.get('estado', 'PENDIENTE'),
                data.get('liquidador_ajustador'),
                data.get('conductor'),
                data.get('tercero'),
                data.get('comisaria'),
                data.get('numero_denuncia'),
                data.get('fec_denuncia_policial'),
                data.get('fec_entrega_doc_ajustador'),
                data.get('fec_entrega_doc_cia'),
                data.get('fec_cia_consentido'),
                data.get('numero_ajuste'),
                data.get('moneda', 'US$'),
                data.get('monto_siniestro', 0.00),
                data.get('deducible', 0.00),
                data.get('descripcion_deducible'),
                data.get('total_indemnizar', 0.00),
                data.get('fec_pago'),
                data.get('forma_pago'),
                data.get('numero_cheque'),
                data.get('banco'),
                data.get('numero_factura'),
                data.get('monto_pagar_factura', 0.00),
                data.get('fec_vencimiento_factura'),
                data.get('fec_pago_factura'),
                usuario
            ]
            cursor.callproc('sp_insert_siniestro_rrgg', params)

        elif grupo_ramo == 'VEHICULOS':
            params = [
                data.get('poliza'),
                data.get('cia'),
                data.get('ramo'),
                data.get('contratante'),
                data.get('asegurado'),
                data.get('fec_notificacion_broker'),
                data.get('fec_stro'),
                data.get('hora_siniestro'),
                data.get('quien_reporta'),
                data.get('email'),
                data.get('telefonos'),
                data.get('hora_contacto'),
                data.get('hora_culminacion'),
                data.get('lugar_siniestro'),
                data.get('causa'),
                data.get('tipo_atencion'),
                data.get('fec_presentacion_cia'),
                data.get('siniestro_no'),
                data.get('ejecutivo_cia'),
                data.get('estado', 'PENDIENTE'),
                data.get('situacion'),
                data.get('moneda', 'US$'),
                data.get('monto_siniestro', 0.00),
                data.get('deducible', 0.00),
                data.get('descripcion_deducible'),
                data.get('total_indemnizar', 0.00),
                data.get('fec_pago'),
                data.get('forma_pago'),
                data.get('numero_cheque'),
                data.get('banco'),
                data.get('numero_factura'),
                data.get('monto_pagar_factura', 0.00),
                data.get('fec_vencimiento_factura'),
                data.get('fec_pago_factura'),
                json_or_null(data.get('vehiculo')),
                json_or_null(data.get('denuncia')),
                json_or_null(data.get('conductor')),
                json_or_null(data.get('copiloto')),
                json_or_null(data.get('tercero')),
                usuario
            ]
            cursor.callproc('sp_insert_siniestro_vehiculos', params)

        elif grupo_ramo == 'RRHH':
            params = [
                data.get('poliza'),
                data.get('cia'),
                data.get('ramo'),
                data.get('contratante'),
                data.get('asegurado'),
                data.get('fec_presentacion_broker'),
                data.get('fec_atencion_medica'),
                data.get('fec_aviso_cia'),
                data.get('fec_presentacion_cia'),
                data.get('fec_cia_consentido'),
                data.get('quien_reporta'),
                data.get('email'),
                data.get('telefonos'),
                data.get('tipo_persona'),
                data.get('titular'),
                data.get('paciente'),
                data.get('diagnostico'),
                data.get('siniestro_no'),
                data.get('ejecutivo_cia'),
                data.get('estado', 'PENDIENTE'),
                data.get('moneda', 'US$'),
                data.get('monto_siniestro', 0.00),
                data.get('deducible', 0.00),
                data.get('descripcion_deducible'),
                data.get('coaseguro', 0.00),
                data.get('no_cubierto', 0.00),
                data.get('total_indemnizar', 0.00),
                data.get('fec_pago'),
                data.get('forma_pago'),
                data.get('numero_cheque'),
                data.get('banco'),
                data.get('numero_factura'),
                data.get('monto_pagar_factura', 0.00),
                data.get('fec_vencimiento_factura'),
                data.get('fec_pago_factura'),
                json_or_null(data.get('gastos')),
                usuario
            ]
            cursor.callproc('sp_insert_siniestro_rrhh', params)

        else:
            return jsonify({'error': f'Grupo de ramo no soportado: {grupo_ramo}'}), 400

        for result in cursor.stored_results():
            inserted = result.fetchone()

        siniestro_id = inserted['id']

        # Insertar documentos si existen
        if data.get('documentos'):
            for doc in data.get('documentos', []):
                cursor.callproc('sp_insert_documento_siniestro', [
                    siniestro_id,
                    doc.get('documento'),
                    doc.get('confirmacion', 'NO')
                ])
                for _ in cursor.stored_results():
                    pass

        # Insertar bitácora si existe
        if data.get('bitacora'):
            for bit in data.get('bitacora', []):
                cursor.callproc('sp_insert_bitacora_siniestro', [
                    siniestro_id,
                    bit.get('comentario'),
                    bit.get('prox_fecha'),
                    bit.get('gestion_a'),
                    usuario
                ])
                for _ in cursor.stored_results():
                    pass

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({
            'message': 'Siniestro creado exitosamente',
            'id': siniestro_id
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def update_siniestro(siniestro_id):
    """Actualiza un siniestro usando el SP específico según el grupo"""
    try:
        data = request.json
        usuario = session.get('user', 'sistema')
        grupo_ramo = data.get('grupo_ramo')

        import json

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Preparar campos JSON como strings JSON o NULL
        def json_or_null(value):
            if value and (isinstance(value, dict) or isinstance(value, list)):
                return json.dumps(value)
            return None

        # Llamar al SP específico según el grupo
        if grupo_ramo == 'RRGG':
            params = [
                siniestro_id,
                data.get('poliza'),
                data.get('cia'),
                data.get('ramo'),
                data.get('contratante'),
                data.get('asegurado'),
                data.get('fec_presentacion_broker'),
                data.get('fec_aviso_cia'),
                data.get('fec_stro'),
                data.get('hora_siniestro'),
                data.get('quien_reporta'),
                data.get('email'),
                data.get('telefonos'),
                data.get('lugar_siniestro'),
                data.get('causa'),
                data.get('descripcion_hechos'),
                data.get('siniestro_no'),
                data.get('ejecutivo_cia'),
                data.get('estado', 'PENDIENTE'),
                data.get('liquidador_ajustador'),
                data.get('conductor'),
                data.get('tercero'),
                data.get('comisaria'),
                data.get('numero_denuncia'),
                data.get('fec_denuncia_policial'),
                data.get('fec_entrega_doc_ajustador'),
                data.get('fec_entrega_doc_cia'),
                data.get('fec_cia_consentido'),
                data.get('numero_ajuste'),
                data.get('moneda', 'US$'),
                data.get('monto_siniestro', 0.00),
                data.get('deducible', 0.00),
                data.get('descripcion_deducible'),
                data.get('total_indemnizar', 0.00),
                data.get('fec_pago'),
                data.get('forma_pago'),
                data.get('numero_cheque'),
                data.get('banco'),
                data.get('numero_factura'),
                data.get('monto_pagar_factura', 0.00),
                data.get('fec_vencimiento_factura'),
                data.get('fec_pago_factura'),
                usuario
            ]
            cursor.callproc('sp_update_siniestro_rrgg', params)

        elif grupo_ramo == 'VEHICULOS':
            params = [
                siniestro_id,
                data.get('poliza'),
                data.get('cia'),
                data.get('ramo'),
                data.get('contratante'),
                data.get('asegurado'),
                data.get('fec_notificacion_broker'),
                data.get('fec_stro'),
                data.get('hora_siniestro'),
                data.get('quien_reporta'),
                data.get('email'),
                data.get('telefonos'),
                data.get('hora_contacto'),
                data.get('hora_culminacion'),
                data.get('lugar_siniestro'),
                data.get('causa'),
                data.get('tipo_atencion'),
                data.get('fec_presentacion_cia'),
                data.get('siniestro_no'),
                data.get('ejecutivo_cia'),
                data.get('estado', 'PENDIENTE'),
                data.get('situacion'),
                data.get('moneda', 'US$'),
                data.get('monto_siniestro', 0.00),
                data.get('deducible', 0.00),
                data.get('descripcion_deducible'),
                data.get('total_indemnizar', 0.00),
                data.get('fec_pago'),
                data.get('forma_pago'),
                data.get('numero_cheque'),
                data.get('banco'),
                data.get('numero_factura'),
                data.get('monto_pagar_factura', 0.00),
                data.get('fec_vencimiento_factura'),
                data.get('fec_pago_factura'),
                json_or_null(data.get('vehiculo')),
                json_or_null(data.get('denuncia')),
                json_or_null(data.get('conductor')),
                json_or_null(data.get('copiloto')),
                json_or_null(data.get('tercero')),
                usuario
            ]
            cursor.callproc('sp_update_siniestro_vehiculos', params)

        elif grupo_ramo == 'RRHH':
            params = [
                siniestro_id,
                data.get('poliza'),
                data.get('cia'),
                data.get('ramo'),
                data.get('contratante'),
                data.get('asegurado'),
                data.get('fec_presentacion_broker'),
                data.get('fec_atencion_medica'),
                data.get('fec_aviso_cia'),
                data.get('fec_presentacion_cia'),
                data.get('fec_cia_consentido'),
                data.get('quien_reporta'),
                data.get('email'),
                data.get('telefonos'),
                data.get('tipo_persona'),
                data.get('titular'),
                data.get('paciente'),
                data.get('diagnostico'),
                data.get('siniestro_no'),
                data.get('ejecutivo_cia'),
                data.get('estado', 'PENDIENTE'),
                data.get('moneda', 'US$'),
                data.get('monto_siniestro', 0.00),
                data.get('deducible', 0.00),
                data.get('descripcion_deducible'),
                data.get('coaseguro', 0.00),
                data.get('no_cubierto', 0.00),
                data.get('total_indemnizar', 0.00),
                data.get('fec_pago'),
                data.get('forma_pago'),
                data.get('numero_cheque'),
                data.get('banco'),
                data.get('numero_factura'),
                data.get('monto_pagar_factura', 0.00),
                data.get('fec_vencimiento_factura'),
                data.get('fec_pago_factura'),
                json_or_null(data.get('gastos')),
                usuario
            ]
            cursor.callproc('sp_update_siniestro_rrhh', params)

        else:
            return jsonify({'error': f'Grupo de ramo no soportado: {grupo_ramo}'}), 400

        for result in cursor.stored_results():
            affected = result.fetchone()

        connection.commit()
        cursor.close()
        connection.close()

        if affected['affected_rows'] == 0:
            return jsonify({'error': 'Siniestro no encontrado'}), 404

        return jsonify({'message': 'Siniestro actualizado exitosamente'}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
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


def get_grupo_ramo_poliza():
    """
    Obtiene el grupo del ramo de una póliza
    """
    try:
        poliza = request.args.get('poliza')

        if not poliza:
            return jsonify({'error': 'Número de póliza requerido'}), 400

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Consulta para obtener el grupo del ramo de la póliza
        query = """
                SELECT
                    p.poliza,
                    p.ramo AS nombre_ramo,
                    r.idRamo,
                    r.nombre,
                    r.grupo,
                    r.abreviacion,
                    r.codigo
                FROM polizas p
                         LEFT JOIN ramos r ON p.ramo = r.nombre
                WHERE p.poliza = %s
                    LIMIT 1 \
                """

        cursor.execute(query, (poliza,))
        resultado = cursor.fetchone()

        cursor.close()
        connection.close()

        if not resultado:
            return jsonify({'error': 'Póliza no encontrada'}), 404

        if not resultado.get('grupo'):
            return jsonify({
                'poliza': resultado['poliza'],
                'ramo': resultado['nombre_ramo'],
                'grupo': 'NO_DEFINIDO',
                'mensaje': 'El ramo de esta póliza no tiene un grupo definido'
            }), 200

        return jsonify({
            'poliza': resultado['poliza'],
            'ramo': resultado['nombre_ramo'],
            'grupo': resultado['grupo'],
            'idRamo': resultado['idRamo'],
            'abreviacion': resultado.get('abreviacion'),
            'codigo': resultado.get('codigo')
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
