from flask import request, jsonify, session
from models.db import get_connection
from datetime import datetime, date
import traceback

def editar_cliente_route():
    """Ruta para editar un cliente existente"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

    try:
        # Obtener usuario de la sesión
        usuario_actual = session.get('user', 'SISTEMA')
        role_name = session.get('role_name')

        # Soporta JSON y form-data para evitar fallas por diferencias de despliegue/proxy.
        data = request.get_json(silent=True) or request.form.to_dict()


        if not data:
            return jsonify({
                'status': 'error',
                'message': 'ID de cliente no proporcionado'
            }), 400

        id_cliente = data.get('idCliente') or data.get('id')
        if not id_cliente:
            return jsonify({
                'status': 'error',
                'message': 'ID de cliente no proporcionado'
            }), 400

        # Compatibilidad de nombres de campos entre versiones (local/prod).
        tipo_documento = (
            data.get('tipo_documento')
            or data.get('tipoDocumento')
            or data.get('tipo_doc')
            or ''
        )
        numero_documento = (
            data.get('numero_documento')
            or data.get('nro_documento')
            or data.get('numeroDocumento')
            or data.get('num_documento')
            or ''
        )
        razon_social = data.get('razon_social') or data.get('razonSocial') or ''

        # RBAC: Verificar propiedad para SUB AGENTE
        from utils.rbac import Roles
        if role_name == Roles.SUB_AGENTE:
            # Verificar si el cliente pertenece al subagente
            conn_check = get_connection()
            cur_check = conn_check.cursor(dictionary=True)
            cur_check.execute("SELECT subagente FROM clientes WHERE idCliente = %s", (id_cliente,))
            row = cur_check.fetchone()
            cur_check.close()
            conn_check.close()
            
            if not row or row['subagente'] != usuario_actual:
                 return jsonify({
                    'status': 'error',
                    'message': 'No tiene permiso para editar este cliente'
                }), 403
            
            # Forzar que no se cambie el subagente
            data['subagente'] = usuario_actual

        # Validar campos requeridos
        required_pairs = [
            ('razon_social', razon_social),
            ('tipo_documento', tipo_documento),
            ('numero_documento', numero_documento),
        ]
        for field_name, field_value in required_pairs:
            if not str(field_value).strip():
                return jsonify({
                    'status': 'error',
                    'message': f'El campo {field_name} es requerido'
                }), 400

        # Convertir fechas vacías a None
        fecha_ingreso = data.get('fecha_ingreso') if data.get('fecha_ingreso') else None
        fecha_nacimiento = data.get('fecha_nacimiento') if data.get('fecha_nacimiento') else None
        licencia_venc = data.get('licencia_venc') if data.get('licencia_venc') else None

        # Convertir valores numéricos
        recibir_notificaciones = 1 if data.get('recibir_notificaciones') in [True, 1, '1', 'true'] else 0
        tipo_persona = int(data.get('tipo_persona', 0)) if data.get('tipo_persona') else None

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

        # Tomar el valor enviado en licenciaConducir (puede ser combinado 'CATEGORIA | NUM')
        # Para mantener el mismo comportamiento que el endpoint de creación, guardamos tal cual el texto
        licencia_conducir_raw = str(data.get('licenciaConducir', '') or '').strip()
        # Si no se envió licenciaConducir, soportar campo legacy licencia_num
        licencia_num = licencia_conducir_raw or str(data.get('licencia_num', '') or '').strip()

        # Obtener conexión y llamar al procedimiento almacenado
        conn = get_connection()
        cursor = conn.cursor()

        # Preparar argumentos en el orden que el procedimiento espera
        args = (
            id_cliente,
            razon_social,
            tipo_documento,
            numero_documento,
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
            licencia_num,
            licencia_venc,
            data.get('grupo_economico', ''),
            data.get('giro_negocio', ''),
            data.get('referencia', ''),
            data.get('recomendado_por', ''),
            recibir_notificaciones,
            data.get('contacto_nombre', ''),
            data.get('contacto_email', ''),
            data.get('contacto_telefono', ''),
            usuario_actual
        )

        # ajustar el call al sp
        try:
            temp_cursor = conn.cursor()
            try:
                temp_cursor.execute("SELECT COUNT(*) FROM information_schema.parameters WHERE specific_name = 'sp_update_cliente' AND routine_schema = DATABASE()")
                row = temp_cursor.fetchone()
                param_count = int(row[0]) if row and row[0] is not None else None
            except Exception:
                param_count = None
            finally:
                temp_cursor.close()

            if param_count is None or param_count >= len(args):
                cursor.callproc('sp_update_cliente', args)
            else:
                cursor.callproc('sp_update_cliente', args[:param_count])
        except Exception as e:
            print(f"Error llamando sp_update_cliente: {e}")
            raise

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

        # RBAC: Verificar propiedad para SUB AGENTE
        from utils.rbac import Roles
        if session.get('role_name') == Roles.SUB_AGENTE:
            if cliente.get('subagente') != session.get('user'):
                return jsonify({
                    'status': 'error',
                    'message': 'No tiene permiso para ver este cliente'
                }), 403

        # Convertir fechas a string formato ISO
        for field in ['fecha_ingreso', 'fecha_nacimiento', 'licencia_venc']:
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
