from flask import request, jsonify, session, current_app
from models.db import get_connection
from datetime import datetime, date
import traceback
import mysql.connector
import re
import time
import uuid


def _mask_value(value, head=2, tail=2):
    s = '' if value is None else str(value)
    if len(s) <= head + tail:
        return '*' * len(s)
    return f"{s[:head]}***{s[-tail:]}"


def _safe_edit_payload(data):
    # Solo campos utiles para diagnostico (sin exponer datos completos).
    return {
        'idCliente': data.get('idCliente') or data.get('id'),
        'tipo_documento': (data.get('tipo_documento') or data.get('tipoDocumento') or data.get('tipo_doc') or ''),
        'numero_documento_mask': _mask_value(data.get('numero_documento') or data.get('nro_documento') or data.get('numeroDocumento') or data.get('num_documento') or ''),
        'razon_social_len': len(str(data.get('razon_social') or data.get('razonSocial') or '')),
        'subagente': data.get('subagente', ''),
        'estado': data.get('estado', ''),
        'has_telefono': bool(str(data.get('telefono', '')).strip()),
        'has_email': bool(str(data.get('email', '')).strip()),
        'keys': sorted(list(data.keys()))
    }

def _find_duplicate_cliente_id(conn, id_cliente, numero_documento):
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT c.idCliente
            FROM clientes c
            WHERE c.idCliente <> %s
              AND COALESCE(c.activo, 1) = 1
              AND (
                    CONVERT(
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR(100) CHARACTER SET utf8mb4),
                            CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR(100) CHARACTER SET utf8mb4),
                            CONVERT(c.numero_documento USING utf8mb4)
                        )
                        USING utf8mb4
                    ) COLLATE utf8mb4_unicode_ci
                  ) = CONVERT(%s USING utf8mb4) COLLATE utf8mb4_unicode_ci
            LIMIT 1
            """,
            (id_cliente, numero_documento)
        )
        row = cur.fetchone()
        cur.close()
        return (row or {}).get('idCliente')
    except Exception:
        return None


def _direct_update_cliente(
    conn,
    id_cliente,
    razon_social,
    tipo_documento,
    numero_documento,
    telefono,
    celular,
    telefono_sec,
    subagente,
    id_productor,
    email,
    direccion,
    departamento,
    provincia,
    distrito,
    estado,
    tipo_persona,
    profesion,
    fecha_ingreso,
    fecha_nacimiento,
    licencia_num,
    licencia_venc,
    grupo_economico,
    giro_negocio,
    referencia,
    recomendado_por,
    recibir_notificaciones,
    contacto_nombre,
    contacto_email,
    contacto_telefono,
    usuario_actual
):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE clientes
        SET razon_social = CASE
                              WHEN %s IS NULL OR TRIM(%s) = '' THEN razon_social
                              ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                           END,
            tipo_documento = %s,
            numero_documento = CASE
                                  WHEN %s IS NULL OR TRIM(%s) = '' THEN numero_documento
                                  ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                               END,
            telefono = CASE
                          WHEN %s IS NULL OR TRIM(%s) = '' THEN telefono
                          ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                       END,
            celular = %s,
            telefono_sec = %s,
            subagente = %s,
            idProductor = %s,
            email = CASE
                       WHEN %s IS NULL OR TRIM(%s) = '' THEN email
                       ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                    END,
            direccion = %s,
            departamento = %s,
            provincia = %s,
            distrito = %s,
            estado = %s,
            tipo_persona = %s,
            profesion = %s,
            fecha_ingreso = %s,
            fecha_nacimiento = %s,
            licencia_num = %s,
            licencia_venc = %s,
            grupo_economico = %s,
            giro_negocio = %s,
            referencia = %s,
            recomendado_por = %s,
            recibir_notificaciones = %s,
            contacto_nombre = %s,
            contacto_email = %s,
            contacto_telefono = %s,
            usuario_modificacion = %s,
            fecha_modificacion = NOW()
        WHERE idCliente = %s
        """,
        (
            razon_social, razon_social, razon_social,
            tipo_documento,
            numero_documento, numero_documento, numero_documento,
            telefono, telefono, telefono,
            celular,
            telefono_sec,
            subagente,
            id_productor,
            email, email, email,
            direccion,
            departamento,
            provincia,
            distrito,
            estado,
            tipo_persona,
            profesion,
            fecha_ingreso,
            fecha_nacimiento,
            licencia_num,
            licencia_venc,
            grupo_economico,
            giro_negocio,
            referencia,
            recomendado_por,
            recibir_notificaciones,
            contacto_nombre,
            contacto_email,
            contacto_telefono,
            usuario_actual,
            id_cliente,
        )
    )
    cur.close()


def editar_cliente_route():
    """Ruta para editar un cliente existente"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

    req_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    started = time.perf_counter()

    try:
        # Obtener usuario de la sesión
        usuario_actual = session.get('user', 'SISTEMA')
        role_name = session.get('role_name')

        # Soporta JSON y form-data para evitar fallas por diferencias de despliegue/proxy.
        data = request.get_json(silent=True) or request.form.to_dict()

        current_app.logger.info(
            "[clientes.edit][%s] inicio user=%s role=%s content_type=%s payload=%s",
            req_id,
            usuario_actual,
            role_name,
            request.content_type,
            _safe_edit_payload(data or {})
        )


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

        current_app.logger.info("[clientes.edit][%s] idCliente=%s", req_id, id_cliente)

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
                current_app.logger.warning(
                    "[clientes.edit][%s] denegado ownership idCliente=%s owner=%s user=%s",
                    req_id,
                    id_cliente,
                    (row or {}).get('subagente'),
                    usuario_actual
                )
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
                current_app.logger.info("[clientes.edit][%s] idProductor_resuelto=%s subagente=%s", req_id, id_productor, subagente)
            except Exception as e:
                current_app.logger.exception("[clientes.edit][%s] error_resolviendo_idProductor subagente=%s", req_id, subagente)
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

        try:
            current_app.logger.info("[clientes.edit][%s] call sp_update_cliente args_len=%s", req_id, len(args))
            sp_started = time.perf_counter()
            cursor.callproc('sp_update_cliente', args)
            conn.commit()
            current_app.logger.info(
                "[clientes.edit][%s] sp_update_cliente ok elapsed_ms=%.2f",
                req_id,
                (time.perf_counter() - sp_started) * 1000
            )
        except mysql.connector.Error as db_err:
            conn.rollback()
            msg = str(db_err)
            current_app.logger.error(
                "[clientes.edit][%s] mysql_error errno=%s sqlstate=%s msg=%s",
                req_id,
                getattr(db_err, 'errno', None),
                getattr(db_err, 'sqlstate', None),
                msg
            )

            # Algunos entornos restringen metadata y/o tienen una firma antigua del SP.
            if getattr(db_err, 'errno', None) == 1318:
                m = re.search(r"expects\s+(\d+)\s+arguments", msg, re.IGNORECASE)
                if m:
                    expected = int(m.group(1))
                    if 0 < expected < len(args):
                        try:
                            retry_cursor = conn.cursor()
                            current_app.logger.warning(
                                "[clientes.edit][%s] retry_sp_update_cliente expected_args=%s",
                                req_id,
                                expected
                            )
                            retry_cursor.callproc('sp_update_cliente', args[:expected])
                            conn.commit()
                            retry_cursor.close()
                            return jsonify({
                                'status': 'success',
                                'message': 'Cliente actualizado correctamente',
                                'id_productor_used': id_productor,
                                'request_id': req_id
                            })
                        except mysql.connector.Error as retry_err:
                            conn.rollback()
                            msg = str(retry_err)
                            current_app.logger.error(
                                "[clientes.edit][%s] mysql_retry_error errno=%s sqlstate=%s msg=%s",
                                req_id,
                                getattr(retry_err, 'errno', None),
                                getattr(retry_err, 'sqlstate', None),
                                msg
                            )

            if 'El numero_documento ya existe' in msg or 'Duplicate entry' in msg:
                try:
                    current_app.logger.warning(
                        "[clientes.edit][%s] duplicate_doc attempting_direct_update",
                        req_id
                    )
                    _direct_update_cliente(
                        conn,
                        id_cliente=id_cliente,
                        razon_social=razon_social,
                        tipo_documento=tipo_documento,
                        numero_documento=numero_documento,
                        telefono=data.get('telefono', ''),
                        celular=data.get('celular', ''),
                        telefono_sec=data.get('telefono_sec', ''),
                        subagente=data.get('subagente', ''),
                        id_productor=id_productor,
                        email=data.get('email', ''),
                        direccion=data.get('direccion', ''),
                        departamento=data.get('departamento', ''),
                        provincia=data.get('provincia', ''),
                        distrito=data.get('distrito', ''),
                        estado=data.get('estado', 'Vigente'),
                        tipo_persona=tipo_persona,
                        profesion=data.get('profesion', ''),
                        fecha_ingreso=fecha_ingreso,
                        fecha_nacimiento=fecha_nacimiento,
                        licencia_num=licencia_num,
                        licencia_venc=licencia_venc,
                        grupo_economico=data.get('grupo_economico', ''),
                        giro_negocio=data.get('giro_negocio', ''),
                        referencia=data.get('referencia', ''),
                        recomendado_por=data.get('recomendado_por', ''),
                        recibir_notificaciones=recibir_notificaciones,
                        contacto_nombre=data.get('contacto_nombre', ''),
                        contacto_email=data.get('contacto_email', ''),
                        contacto_telefono=data.get('contacto_telefono', ''),
                        usuario_actual=usuario_actual
                    )
                    conn.commit()
                    return jsonify({
                        'status': 'success',
                        'message': 'Cliente actualizado correctamente',
                        'id_productor_used': id_productor,
                        'request_id': req_id,
                        'used_fallback_update': True
                    })
                except mysql.connector.Error as fallback_err:
                    conn.rollback()
                    fallback_msg = str(fallback_err)
                    dup_id = _find_duplicate_cliente_id(conn, id_cliente, numero_documento)
                    if 'Duplicate entry' in fallback_msg:
                        return jsonify({
                            'status': 'error',
                            'message': 'No se puede guardar porque la base de datos aun tiene un indice UNIQUE en numero_documento',
                            'duplicate_idCliente': dup_id
                        }), 400
                    return jsonify({
                        'status': 'error',
                        'message': 'Error al actualizar el cliente',
                        'duplicate_idCliente': dup_id
                    }), 500

            if 'Cliente no encontrado' in msg:
                return jsonify({
                    'status': 'error',
                    'message': 'Cliente no encontrado'
                }), 404

            if 'Incorrect number of arguments' in msg or getattr(db_err, 'errno', None) == 1318:
                return jsonify({
                    'status': 'error',
                    'message': 'SP desactualizado en produccion (firma distinta). Actualiza sp_update_cliente.'
                }), 500

            raise
        finally:
            cursor.close()
            conn.close()

        return jsonify({
            'status': 'success',
            'message': 'Cliente actualizado correctamente',
            'id_productor_used': id_productor,
            'request_id': req_id
        })

    except Exception as e:
        current_app.logger.exception("[clientes.edit][%s] unhandled_exception", req_id)
        return jsonify({
            'status': 'error',
            'message': f'Error al actualizar el cliente: {str(e)}',
            'request_id': req_id
        }), 500
    finally:
        current_app.logger.info(
            "[clientes.edit][%s] fin total_elapsed_ms=%.2f",
            req_id,
            (time.perf_counter() - started) * 1000
        )


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
