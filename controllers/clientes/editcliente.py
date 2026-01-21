from flask import request, jsonify, session
from models.db import get_connection
from datetime import datetime, date
import traceback

def editar_cliente_route():
    """Ruta para editar un cliente existente"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

    try:
        data = request.get_json()

        # Validar que se recibió el ID del cliente
        if not data or 'idCliente' not in data:
            return jsonify({
                'status': 'error',
                'message': 'ID de cliente no proporcionado'
            }), 400

        id_cliente = data['idCliente']

        # Validar campos requeridos
        required_fields = ['razon_social', 'tipo_documento', 'numero_documento']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'El campo {field} es requerido'
                }), 400

        # Convertir fechas vacías a None
        fecha_ingreso = data.get('fecha_ingreso') if data.get('fecha_ingreso') else None
        fecha_nacimiento = data.get('fecha_nacimiento') if data.get('fecha_nacimiento') else None
        licencia_venc = data.get('licencia_venc') if data.get('licencia_venc') else None
        ultimo_siniestro = data.get('ultimo_siniestro') if data.get('ultimo_siniestro') else None

        # Convertir valores numéricos
        recibir_notificaciones = 1 if data.get('recibir_notificaciones') in [True, 1, '1', 'true'] else 0
        tipo_persona = int(data.get('tipo_persona', 0)) if data.get('tipo_persona') else None
        siniestros_reportados = int(data.get('siniestros_reportados', 0)) if data.get('siniestros_reportados') else None

        # Obtener idProductor basado en la abreviación del subagente
        id_productor = None
        subagente = data.get('subagente', '').strip()
        if subagente:
            try:
                temp_conn = get_connection()
                temp_cursor = temp_conn.cursor(dictionary=True)
                temp_cursor.callproc('sp_get_idProductor_por_abreviacion', [subagente])
                for result in temp_cursor.stored_results():
                    row = result.fetchone()
                    if row and 'idProductor' in row:
                        id_productor = row['idProductor']
                temp_cursor.close()
                temp_conn.close()
            except Exception as e:
                print(f"Error obteniendo idProductor: {str(e)}")
                # Si no se puede obtener, intentar usar el que viene en los datos
                id_productor = int(data.get('idProductor')) if data.get('idProductor') else None

        # Obtener conexión y llamar al procedimiento almacenado
        conn = get_connection()
        cursor = conn.cursor()

        cursor.callproc('sp_update_cliente', [
            id_cliente,
            data.get('razon_social'),
            data.get('tipo_documento'),
            data.get('numero_documento'),
            data.get('telefono', ''),
            data.get('celular', ''),
            data.get('telefono_sec', ''),
            data.get('subagente', ''),
            id_productor,
            data.get('email', ''),
            data.get('direccion', ''),
            data.get('departamento', ''),
            data.get('provincia', ''),
            data.get('distrito', ''),
            data.get('estado', 'Vigente'),
            tipo_persona,
            data.get('profesion', ''),
            fecha_ingreso,
            fecha_nacimiento,
            data.get('licencia_num', ''),
            licencia_venc,
            data.get('grupo_economico', ''),
            data.get('giro_negocio', ''),
            data.get('referencia', ''),
            data.get('recomendado_por', ''),
            recibir_notificaciones,
            data.get('contacto_nombre', ''),
            data.get('contacto_email', ''),
            data.get('contacto_telefono', ''),
            data.get('referencias_interes', ''),
            data.get('notas', ''),
            siniestros_reportados,
            ultimo_siniestro,
            data.get('detalle_siniestros', ''),
            data.get('preferencias', '')
        ])

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'status': 'success',
            'message': 'Cliente actualizado correctamente',
            'id_productor_used': id_productor
        })

    except Exception as e:
        print(f"Error al editar cliente: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Error al actualizar el cliente: {str(e)}'
        }), 500


def get_cliente_detalle_route(idCliente):
    """Obtener los detalles de un cliente para editar"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc('sp_get_cliente_por_id', [idCliente])

        cliente = None
        for result in cursor.stored_results():
            cliente = result.fetchone()

        cursor.close()
        conn.close()

        if not cliente:
            return jsonify({
                'status': 'error',
                'message': 'Cliente no encontrado'
            }), 404

        # Convertir fechas a string formato ISO
        for field in ['fecha_ingreso', 'fecha_nacimiento', 'licencia_venc', 'ultimo_siniestro']:
            if cliente.get(field):
                if isinstance(cliente[field], (datetime, date)):
                    cliente[field] = cliente[field].strftime('%Y-%m-%d')

        return jsonify({
            'status': 'success',
            'data': cliente
        })

    except Exception as e:
        print(f"Error al obtener cliente: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener el cliente: {str(e)}'
        }), 500
