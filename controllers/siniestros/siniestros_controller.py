from flask import jsonify, request, session
from models.db import get_connection

from reportlab.lib.units import inch
LOGO_MAX_W = 1.8 * inch
LOGO_MAX_H = 1.0 * inch
LOGO_TOP_MARGIN = 0.15 * inch
HEADER_EXTRA = 0.15 * inch  # espacio extra para evitar solapamiento

def list_siniestros_por_poliza():
	try:
		poliza = request.args.get('poliza')

		if not poliza:
			return jsonify({'error': 'Número de póliza requerido'}), 400

		connection = get_connection()
		cursor = connection.cursor(dictionary=True)


		cursor.execute("""
			SELECT
				id, grupo_ramo, contratante, poliza, cia, ramo, fec_stro,
				causa, siniestro_no, monto_siniestro, estado, ejecutivo_cia, placa,
				fecha_registro AS creado_en
			FROM siniestros
			WHERE poliza = %s AND eliminado = 0
			ORDER BY fec_stro DESC
		""", (poliza,))
		siniestros = cursor.fetchall()

		# Serializar fechas a string ISO
		from datetime import date, datetime
		for s in siniestros:
			for k, v in s.items():
				if isinstance(v, (date, datetime)):
					s[k] = v.isoformat()

		cursor.close()
		connection.close()

		return jsonify(siniestros), 200

	except Exception as e:
		return jsonify({'error': str(e)}), 500


def list_siniestros():
	try:
		from utils.rbac import Roles
		connection = get_connection()
		cursor = connection.cursor(dictionary=True)

		# RLS Logic
		rls_filter = ""
		rls_params = []
		if session.get('role_name') == Roles.SUB_AGENTE:
			user = session.get('user')
			# Get user's full name for sub_agente match
			cursor.execute("SELECT nombre FROM usuarios WHERE username = %s", (user,))
			u_row = cursor.fetchone()
			nombre_usuario = u_row['nombre'] if u_row else user
			
			# Filter by creator or assigned sub_agente (via polizas join)
			# Siniestros has poliza (varchar), polizas has poliza (varchar)
			rls_filter = """
				AND (
					s.usuario_registro = %s 
					OR EXISTS (
						SELECT 1 FROM polizas p 
						WHERE p.poliza = s.poliza 
						AND (p.sub_agente = %s OR p.usuario_registro = %s)
					)
				)
			"""
			rls_params = [user, nombre_usuario, user]

		# Use SQL directly instead of SP to support RLS
		sql = f"""
			SELECT
				s.id, s.grupo_ramo, s.contratante, s.poliza, s.cia, s.ramo, s.fec_stro,
				s.causa, s.siniestro_no, s.monto_siniestro, s.estado, s.ejecutivo_cia, s.placa, s.fecha_registro AS creado_en
			FROM siniestros s
			WHERE s.eliminado = 0 {rls_filter}
			ORDER BY s.fecha_registro DESC
		"""
		
		cursor.execute(sql, tuple(rls_params))
		siniestros = cursor.fetchall()

		# Serializar fechas a string ISO
		from datetime import date, datetime
		for s in siniestros:
			for k, v in s.items():
				if isinstance(v, (date, datetime)):
					s[k] = v.isoformat()

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

		# Añadir aliases y rellenar placa desde datos_vehiculo si falta
		try:
			# Mapeos seguros para compatibilidad con frontend
			alias_map = {
				'vehiculo': 'datos_vehiculo',
				'denuncia': 'datos_denuncia',
				'conductor': 'datos_conductor',
				'copiloto': 'datos_copiloto',
				'tercero': 'datos_tercero',
				'gastos': 'gastos_presentados'
			}

			for alias, original in alias_map.items():
				if siniestro.get(alias) is None and siniestro.get(original) is not None:
					siniestro[alias] = siniestro.get(original)


			if not siniestro.get('placa') and siniestro.get('datos_vehiculo') and isinstance(siniestro.get('datos_vehiculo'), dict):
				placa = siniestro['datos_vehiculo'].get('placa') or siniestro['datos_vehiculo'].get('placa_vehiculo')
				if placa:
					siniestro['placa'] = placa
		except Exception:
			# No queremos romper la respuesta por un fallo aquí
			pass

		return jsonify(siniestro), 200

	except Exception as e:
		return jsonify({'error': str(e)}), 500


def insert_siniestro():
	"""Inserta un nuevo siniestro usando el SP específico según el grupo"""
	try:
		data = request.json
		usuario = session.get('user', 'sistema')
		grupo_ramo = data.get('grupo_ramo') or 'OTROS'

		import json

		connection = get_connection()
		cursor = connection.cursor(dictionary=True)

		# Preparar campos JSON como strings JSON o NULL
		def json_or_null(value):
			if value and (isinstance(value, dict) or isinstance(value, list)):
				return json.dumps(value)
			return None

		siniestro_id = None

		# Resolver poliza_id desde número de póliza (requerido NOT NULL en tabla)
		numero_poliza = data.get('poliza')
		poliza_id = None
		if numero_poliza:
			cursor.execute("SELECT idPoliza FROM polizas WHERE poliza = %s AND activo = 1 LIMIT 1", (numero_poliza,))
			row_poliza = cursor.fetchone()
			if row_poliza:
				poliza_id = row_poliza['idPoliza']
		if not poliza_id:
			return jsonify({'error': f'No se encontró la póliza: {numero_poliza}'}), 400

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

		# Nuevo manejo para OTROS: usar SPs especializados
		elif grupo_ramo == 'OTROS':
			params = [
				data.get('poliza'),
				data.get('cia'),
				data.get('ramo'),
				data.get('contratante'),
				data.get('asegurado'),
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
				data.get('moneda', 'LOCAL'),
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
				json_or_null(data.get('gastos')),
				usuario
			]
			cursor.callproc('sp_insert_siniestro_otros', params)

		else:
			return jsonify({'error': f'Grupo de ramo no soportado: {grupo_ramo}'}), 400

		for result in cursor.stored_results():
			inserted = result.fetchone()

		siniestro_id = inserted['id']

		# Actualizar poliza_id (los SPs no lo incluyen, se resuelve aquí)
		cursor.execute("UPDATE siniestros SET poliza_id = %s WHERE id = %s", (poliza_id, siniestro_id))

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
		grupo_ramo = data.get('grupo_ramo') or 'OTROS'

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
				data.get('fec_stro'),
				data.get('causa'),
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

		# Nuevo manejo OTROS
		elif grupo_ramo == 'OTROS':
			params = [
				siniestro_id,
				data.get('poliza'),
				data.get('cia'),
				data.get('ramo'),
				data.get('contratante'),
				data.get('asegurado'),
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
				data.get('moneda', 'LOCAL'),
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
				json_or_null(data.get('gastos')),
				usuario
			]
			cursor.callproc('sp_update_siniestro_otros', params)

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
		from utils.rbac import Roles
		texto = request.json.get('texto', '')

		connection = get_connection()
		cursor = connection.cursor(dictionary=True)

		# RLS Logic
		rls_filter = ""
		rls_params = []
		if session.get('role_name') == Roles.SUB_AGENTE:
			user = session.get('user')
			# Get user's full name for sub_agente match
			cursor.execute("SELECT nombre FROM usuarios WHERE username = %s", (user,))
			u_row = cursor.fetchone()
			nombre_usuario = u_row['nombre'] if u_row else user
			
			rls_filter = """
				AND (
					s.usuario_registro = %s 
					OR EXISTS (
						SELECT 1 FROM polizas p 
						WHERE p.poliza = s.poliza 
						AND (p.sub_agente = %s OR p.usuario_registro = %s)
					)
				)
			"""
			rls_params = [user, nombre_usuario, user]

		# Use SQL directly instead of SP to support RLS and Search
		term = f"%{texto}%"
		sql = f"""
			SELECT
				s.id, s.grupo_ramo, s.contratante, s.poliza, s.cia, s.ramo, s.fec_stro,
				s.causa, s.siniestro_no, s.monto_siniestro, s.estado, s.ejecutivo_cia, s.placa, s.fecha_registro AS creado_en
			FROM siniestros s
			WHERE s.eliminado = 0
			AND (
				s.poliza LIKE %s OR
				s.contratante LIKE %s OR
				s.asegurado LIKE %s OR
				s.siniestro_no LIKE %s OR
				s.placa LIKE %s OR
				s.cia LIKE %s
			)
			{rls_filter}
			ORDER BY s.fecha_registro DESC
			LIMIT 100
		"""
		
		# Combine params: search params * 6 + rls_params
		params = [term] * 6 + rls_params
		
		cursor.execute(sql, tuple(params))
		siniestros = cursor.fetchall()

		# Serializar fechas a string ISO
		from datetime import date, datetime
		for s in siniestros:
			for k, v in s.items():
				if isinstance(v, (date, datetime)):
					s[k] = v.isoformat()

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


def generar_pdf_siniestro(siniestro_id):
    """Genera un PDF del siniestro según su grupo"""
    from flask import send_file
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO
    import json
    from datetime import date

    try:
        # Obtener datos del siniestro
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

        # Parsear campos JSON y fechas
        for key, value in siniestro.items():
            if isinstance(value, date):
                siniestro[key] = value.isoformat()
            elif key in ['datos_vehiculo', 'datos_denuncia', 'datos_conductor', 'datos_copiloto', 'datos_tercero', 'gastos_presentados']:
                if value:
                    try:
                        siniestro[key] = json.loads(value)
                    except:
                        siniestro[key] = None

        # Crear PDF en memoria
        buffer = BytesIO()

        # Generar PDF según el grupo
        grupo = siniestro.get('grupo_ramo', 'OTROS')

        if grupo == 'VEHICULOS':
            _generar_pdf_vehiculos(buffer, siniestro)
        elif grupo == 'RRGG':
            _generar_pdf_rrgg(buffer, siniestro)
        elif grupo == 'RRHH':
            _generar_pdf_rrhh(buffer, siniestro)
        else:
            _generar_pdf_generico(buffer, siniestro)

        buffer.seek(0)

        filename = f"Siniestro_{siniestro.get('siniestro_no') or siniestro_id}.pdf"

        # Permitir servir inline si el frontend lo solicita con ?inline=1
        try:
            inline_flag = str(request.args.get('inline', '')).lower() in ('1', 'true', 'yes')
        except Exception:
            inline_flag = False

        if inline_flag:
            # En modo inline enviamos el PDF para que el navegador lo muestre en pestaña
            resp = send_file(buffer, mimetype='application/pdf', as_attachment=False)
            try:
                # Añadir cabecera explícita para instructar al navegador a mostrar inline
                resp.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            except Exception:
                pass
            return resp
        else:
            # Comportamiento original: forzar descarga
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _insert_logo(canvas, doc):
    from flask import current_app
    import os
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader

    try:
        logo_path = os.path.join(current_app.root_path, 'static', 'uploads', 'logo', 'Logo-banner.png')

        if not (os.path.exists(logo_path) and os.access(logo_path, os.R_OK)):
            return

        reader = ImageReader(logo_path)
        iw, ih = reader.getSize()  # ancho, alto en píxeles o unidades internas

        # Evitar división por cero
        if iw == 0 or ih == 0:
            return

        aspect = float(ih) / float(iw)

        draw_w = LOGO_MAX_W
        draw_h = draw_w * aspect

        if draw_h > LOGO_MAX_H:
            draw_h = LOGO_MAX_H
            draw_w = draw_h / aspect


        # Usar márgenes coherentes con las constantes definidas arriba
        right_margin = 0.15 * inch
        top_margin = LOGO_TOP_MARGIN

        x = doc.pagesize[0] - draw_w - right_margin
        y = doc.pagesize[1] - draw_h - top_margin


        canvas.drawImage(logo_path, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
    except Exception as e:
        print(f"Error al dibujar logo en header: {e}")
        return


def _generar_pdf_vehiculos(buffer, siniestro):
    """Genera PDF para siniestros de VEHICULOS"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER

    # Reservar espacio en el header para el logo (evita solapamiento en páginas siguientes)
    # Compact layout: utilizar ancho menor y márgenes reducidos
    header_reserved = LOGO_MAX_H + LOGO_TOP_MARGIN + HEADER_EXTRA
    doc = SimpleDocTemplate(buffer, pagesize=(7.5*inch, 11*inch), topMargin=header_reserved, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
    elements = []
    styles = getSampleStyleSheet()

    # Estilos personalizados (más compactos)
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=4,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    normal_small = ParagraphStyle('NormalSmall', parent=styles['Normal'], fontSize=8, spaceAfter=2)

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )

    # Anchos dinámicos para etiquetas/valores (label/value)
    label_w = 1.4 * inch
    value_w = doc.width - label_w

    # Encabezado
    elements.append(Paragraph("ARIAS & ARIAS CORREDORES DE SEGUROS SAC.", title_style))
    elements.append(Paragraph(f"Código: {siniestro.get('siniestro_no', '')}", normal_small))
    elements.append(Spacer(1, 0.15*inch))

    # Título principal
    elements.append(Paragraph("INFORME TÉCNICO DE ACCIDENTE DE TRÁNSITO", title_style))
    elements.append(Spacer(1, 0.12*inch))

    # REPORTE DE SINIESTRO
    if any([siniestro.get('hora_siniestro'), siniestro.get('fec_stro'), siniestro.get('quien_reporta')]):
        subtitle_para = Paragraph("REPORTE DE SINIESTRO", subtitle_style)
        data = []

        if siniestro.get('hora_siniestro'):
            data.append(['Hora', siniestro['hora_siniestro']])
        if siniestro.get('fec_stro'):
            data.append(['Fecha', siniestro['fec_stro']])
        if siniestro.get('quien_reporta'):
            data.append(['Quien reporta', siniestro['quien_reporta']])
        if siniestro.get('lugar_siniestro'):
            data.append(['Lugar', siniestro['lugar_siniestro']])
        if siniestro.get('telefonos'):
            data.append(['Teléfono', siniestro['telefonos']])
        if siniestro.get('hora_contacto'):
            data.append(['Contactos', siniestro['hora_contacto']])
        if siniestro.get('causa'):
            data.append(['Caso', siniestro['causa']])
        if siniestro.get('hora_culminacion'):
            data.append(['Hora culminación', siniestro['hora_culminacion']])
        if siniestro.get('tipo_atencion'):
            data.append(['Situación del evento', siniestro['tipo_atencion']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            # Añadir bordes y evitar cortar filas entre páginas
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DEL CLIENTE
    if any([siniestro.get('asegurado'), siniestro.get('cia'), siniestro.get('poliza')]):
        subtitle_para = Paragraph("INFORMACIÓN DEL CLIENTE", subtitle_style)
        data = []

        if siniestro.get('asegurado'):
            data.append(['Asegurado', siniestro['asegurado']])
        if siniestro.get('cia'):
            data.append(['Cia. de Seguros', siniestro['cia']])
        if siniestro.get('poliza'):
            data.append(['Nro. de Póliza', siniestro['poliza']])

        vehiculo = siniestro.get('datos_vehiculo') or {}
        if vehiculo.get('placa'):
            data.append(['Placa', vehiculo['placa']])
        elif siniestro.get('placa'):
            data.append(['Placa', siniestro['placa']])

        if siniestro.get('situacion'):
            data.append(['Conductor', siniestro['situacion']])

        denuncia = siniestro.get('datos_denuncia') or {}
        if denuncia.get('comisaria'):
            data.append(['Comisaría', denuncia['comisaria']])
        if siniestro.get('causa'):
            data.append(['Motivo', siniestro['causa']])
        if siniestro.get('fec_stro'):
            data.append(['Fecha', siniestro['fec_stro']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DEL VEHÍCULO
    vehiculo = siniestro.get('datos_vehiculo') or {}
    if any(vehiculo.values() if vehiculo else []):
        subtitle_para = Paragraph("INFORMACIÓN DEL VEHÍCULO", subtitle_style)
        data = []

        if vehiculo.get('propietario'):
            data.append(['Propietario', vehiculo['propietario']])
        if vehiculo.get('placa'):
            data.append(['Placa', vehiculo['placa']])
        if vehiculo.get('marca'):
            data.append(['Marca', vehiculo['marca']])
        if vehiculo.get('modelo'):
            data.append(['Modelo', vehiculo['modelo']])
        if vehiculo.get('motor'):
            data.append(['Motor', vehiculo['motor']])
        if vehiculo.get('anio'):
            data.append(['Año', str(vehiculo['anio'])])
        if vehiculo.get('color'):
            data.append(['Color', vehiculo['color']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DE LA INDEMNIZACIÓN (AGREGADO para VEHÍCULOS)
    if any([siniestro.get('monto_siniestro'), siniestro.get('deducible'), siniestro.get('total_indemnizar'), siniestro.get('fec_pago')]):
        subtitle_para = Paragraph("INFORMACIÓN DE LA INDEMNIZACIÓN", subtitle_style)
        data = []

        moneda = siniestro.get('moneda', 'USD')

        if siniestro.get('monto_siniestro') is not None:
            try:
                val = float(siniestro.get('monto_siniestro', 0))
                data.append(['Monto Siniestro', f"{moneda} {val:,.2f}"])
            except Exception:
                data.append(['Monto Siniestro', str(siniestro.get('monto_siniestro'))])

        if siniestro.get('deducible') is not None:
            try:
                val = float(siniestro.get('deducible', 0))
                data.append(['Deducible', f"{moneda} {val:,.2f}"])
            except Exception:
                data.append(['Deducible', str(siniestro.get('deducible'))])

        if siniestro.get('total_indemnizar') is not None:
            try:
                val = float(siniestro.get('total_indemnizar', 0))
                data.append(['Total Indemnizar', f"{moneda} {val:,.2f}"])
            except Exception:
                data.append(['Total Indemnizar', str(siniestro.get('total_indemnizar'))])

        if siniestro.get('fec_pago'):
            data.append(['Fecha de Pago', siniestro.get('fec_pago')])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DE LA DENUNCIA
    denuncia = siniestro.get('datos_denuncia') or {}
    if any(denuncia.values() if denuncia else []):
        subtitle_para = Paragraph("INFORMACIÓN DE LA DENUNCIA", subtitle_style)
        data = []

        if denuncia.get('comisaria'):
            data.append(['Comisaría', denuncia['comisaria']])
        if denuncia.get('numero_denuncia'):
            data.append(['Nro. denuncia', denuncia['numero_denuncia']])
        if denuncia.get('dosaje_etilico'):
            data.append(['Dosaje', denuncia['dosaje_etilico']])
        if denuncia.get('fec_denuncia'):
            data.append(['Fecha denuncia policial', denuncia['fec_denuncia']])
        if denuncia.get('departamento'):
            data.append(['Departamento', denuncia['departamento']])
        if denuncia.get('provincia'):
            data.append(['Provincia', denuncia['provincia']])
        if denuncia.get('distrito'):
            data.append(['Distrito', denuncia['distrito']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DEL CONDUCTOR
    conductor = siniestro.get('datos_conductor') or {}
    if any(conductor.values() if conductor else []):
        subtitle_para = Paragraph("INFORMACIÓN DEL CONDUCTOR", subtitle_style)
        data = []

        if conductor.get('nombre'):
            data.append(['Nombre', conductor['nombre']])
        if conductor.get('documento_identidad'):
            data.append(['Documento de identidad', conductor['documento_identidad']])
        if conductor.get('fec_nacimiento'):
            data.append(['Fecha de nacimiento', conductor['fec_nacimiento']])
        if conductor.get('licencia_conducir'):
            data.append(['Licencia de conducir', conductor['licencia_conducir']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # Footer
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("E-mail: info@ariasyarias.com", footer_style))
    elements.append(Paragraph("1", footer_style))

    doc.build(elements, onFirstPage=_insert_logo, onLaterPages=_insert_logo)


def _generar_pdf_rrgg(buffer, siniestro):
    """Genera PDF para siniestros de RRGG"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER

    # Compact header reserve y margins
    header_reserved = LOGO_MAX_H + LOGO_TOP_MARGIN + HEADER_EXTRA
    doc = SimpleDocTemplate(buffer, pagesize=(7.5*inch, 11*inch), topMargin=header_reserved, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=4,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    normal_small = ParagraphStyle('NormalSmall', parent=styles['Normal'], fontSize=8, spaceAfter=2)

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )

    label_w = 1.4 * inch
    value_w = doc.width - label_w

    # Encabezado
    elements.append(Paragraph("ARIAS & ARIAS CORREDORES DE SEGUROS SAC.", title_style))
    elements.append(Paragraph(f"Código: {siniestro.get('siniestro_no', '')}", normal_small))
    elements.append(Spacer(1, 0.15*inch))

    elements.append(Paragraph("SINIESTRO DE RIESGOS GENERALES", title_style))
    elements.append(Paragraph(f"Registrado el: {siniestro.get('fec_stro', '')}", normal_small))
    elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DEL SINIESTRO
    if any([siniestro.get('siniestro_no'), siniestro.get('cia'), siniestro.get('contratante')]):
        subtitle_para = Paragraph("INFORMACIÓN DEL SINIESTRO", subtitle_style)
        data = []

        if siniestro.get('siniestro_no'):
            data.append(['No. Siniestro', siniestro['siniestro_no']])
        if siniestro.get('cia'):
            data.append(['Cia. de Seguros', siniestro['cia']])
        if siniestro.get('ejecutivo_cia'):
            data.append(['Ejecutivo Cía.', siniestro['ejecutivo_cia']])
        if siniestro.get('contratante'):
            data.append(['Contratante', siniestro['contratante']])
        if siniestro.get('poliza'):
            data.append(['Póliza', siniestro['poliza']])
        if siniestro.get('ramo'):
            data.append(['Ramo', siniestro['ramo']])
        if siniestro.get('quien_reporta'):
            data.append(['Contacto', siniestro['quien_reporta']])
        if siniestro.get('fec_presentacion_broker'):
            data.append(['Fecha Ocurrencia', siniestro['fec_presentacion_broker']])
        if siniestro.get('fec_aviso_cia'):
            data.append(['Fecha Aviso Cía.', siniestro['fec_aviso_cia']])
        if siniestro.get('liquidador_ajustador'):
            data.append(['Ajustador', siniestro['liquidador_ajustador']])
        if siniestro.get('lugar_siniestro'):
            data.append(['Ubicación del Siniestro', siniestro['lugar_siniestro']])
        if siniestro.get('causa'):
            data.append(['Causal', siniestro['causa']])
        if siniestro.get('estado'):
            data.append(['Estado', siniestro['estado']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DE LA INDEMNIZACIÓN
    if any([siniestro.get('monto_siniestro'), siniestro.get('deducible'), siniestro.get('total_indemnizar')]):
        subtitle_para = Paragraph("INFORMACIÓN DE LA INDEMNIZACIÓN", subtitle_style)
        data = []

        moneda = siniestro.get('moneda', 'USD')
        if siniestro.get('monto_siniestro'):
            data.append(['Importe Siniestro', f"{moneda} {float(siniestro['monto_siniestro']):,.2f}"])
        if siniestro.get('deducible'):
            data.append(['Deducible', f"{moneda} {float(siniestro['deducible']):,.2f}"])
        if siniestro.get('total_indemnizar'):
            data.append(['Importe Indemnización', f"{moneda} {float(siniestro['total_indemnizar']):,.2f}"])
        if siniestro.get('fec_pago'):
            data.append(['Fecha de Pago', siniestro['fec_pago']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # Descripción de hechos
    if siniestro.get('descripcion_hechos'):
        elements.append(Spacer(1, 0.12*inch))
        elements.append(Paragraph(siniestro['descripcion_hechos'], normal_small))
        elements.append(Spacer(1, 0.12*inch))

    # SEGUIMIENTO
    if siniestro.get('liquidador_ajustador') or siniestro.get('estado'):
        subtitle_para = Paragraph("SEGUIMIENTO", subtitle_style)
        data = []
        data.append(['Fecha', 'Comentario', 'Próx Fecha', 'Gestión a'])
        data.append(['Atentamente', '', '', ''])

        # tabla de 4 columnas compacta (dos pares label/value por fila)
        half = doc.width / 2
        col1_label = 1.1 * inch
        col3_label = 1.1 * inch
        table = Table(data, colWidths=[col1_label, half - col1_label, col3_label, half - col3_label])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('NOSPLIT', (0, 0), (-1, -1)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        elements.append(KeepTogether([subtitle_para, table]))
        elements.append(Spacer(1, 0.12*inch))

    # Footer
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("ARIAS & ARIAS CORREDORES DE SEGUROS SAC.", footer_style))
    elements.append(Paragraph(f"Código: {siniestro.get('siniestro_no', '')}", footer_style))
    elements.append(Spacer(1, 0.05*inch))
    elements.append(Paragraph("E-mail: info@ariasyarias.com", footer_style))

    doc.build(elements, onFirstPage=_insert_logo, onLaterPages=_insert_logo)


def _generar_pdf_rrhh(buffer, siniestro):
    """Genera PDF para siniestros de RRHH (Salud)"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER

    # Compact header reserve y margins
    header_reserved = LOGO_MAX_H + LOGO_TOP_MARGIN + HEADER_EXTRA
    doc = SimpleDocTemplate(buffer, pagesize=(7.5*inch, 11*inch), topMargin=header_reserved, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=4,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    normal_small = ParagraphStyle('NormalSmall', parent=styles['Normal'], fontSize=8, spaceAfter=2)

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )

    label_w = 1.4 * inch
    value_w = doc.width - label_w

    # Encabezado
    elements.append(Paragraph("ARIAS & ARIAS CORREDORES DE SEGUROS SAC.", title_style))
    elements.append(Paragraph(f"Código: {siniestro.get('siniestro_no', '')}", normal_small))
    elements.append(Spacer(1, 0.15*inch))

    elements.append(Paragraph("SINIESTRO DE SALUD", title_style))
    elements.append(Paragraph(f"Registrado el: {siniestro.get('fec_stro', '')}", normal_small))
    elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DEL SINIESTRO
    if any([siniestro.get('siniestro_no'), siniestro.get('cia'), siniestro.get('contratante')]):
        subtitle_para = Paragraph("INFORMACIÓN DEL SINIESTRO", subtitle_style)
        data = []

        if siniestro.get('siniestro_no'):
            data.append(['No. Siniestro', siniestro['siniestro_no']])
        if siniestro.get('cia'):
            data.append(['Cia. de Seguros', siniestro['cia']])
        if siniestro.get('ejecutivo_cia'):
            data.append(['Ejecutivo Cía.', siniestro['ejecutivo_cia']])
        if siniestro.get('contratante'):
            data.append(['Contratante', siniestro['contratante']])
        if siniestro.get('asegurado'):
            data.append(['Asegurado', siniestro['asegurado']])
        if siniestro.get('poliza'):
            data.append(['Póliza', siniestro['poliza']])
        if siniestro.get('ramo'):
            data.append(['Ramo', siniestro['ramo']])
        if siniestro.get('fec_stro'):
            data.append(['Fecha Ocurrencia', siniestro['fec_stro']])
        if siniestro.get('fec_aviso_cia'):
            data.append(['Fecha Aviso Cía.', siniestro['fec_aviso_cia']])
        if siniestro.get('lugar_siniestro'):
            data.append(['Lugar Atención', siniestro['lugar_siniestro']])
        if siniestro.get('diagnostico'):
            data.append(['Diagnóstico', siniestro['diagnostico']])
        if siniestro.get('causa'):
            data.append(['Causa', siniestro['causa']])
        if siniestro.get('estado'):
            data.append(['Estado', siniestro['estado']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # GASTOS PRESENTADOS
    gastos = siniestro.get('gastos_presentados') or []
    if gastos and isinstance(gastos, list) and len(gastos) > 0:
        elements.append(Paragraph("GASTOS PRESENTADOS", subtitle_style))
        data = [['Concepto', 'Monto']]

        total_gastos = 0
        for gasto in gastos:
            if isinstance(gasto, dict):
                concepto = gasto.get('concepto', '')
                monto = gasto.get('monto', 0)
                if concepto:
                    data.append([concepto, f"{siniestro.get('moneda', 'USD')} {float(monto):,.2f}"])
                    total_gastos += float(monto)

        if len(data) > 1:
            data.append(['TOTAL', f"{siniestro.get('moneda', 'USD')} {total_gastos:,.2f}"])

            table = Table(data, colWidths=[doc.width - (1.2*inch), 1.2*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('NOSPLIT', (0, 0), (-1, -1))
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DE LA INDEMNIZACIÓN
    if any([siniestro.get('monto_siniestro'), siniestro.get('deducible'), siniestro.get('coaseguro')]):
        subtitle_para = Paragraph("INFORMACIÓN DE LA INDEMNIZACIÓN", subtitle_style)
        data = []

        moneda = siniestro.get('moneda', 'USD')
        if siniestro.get('monto_siniestro'):
            data.append(['Monto Total', f"{moneda} {float(siniestro['monto_siniestro']):,.2f}"])
        if siniestro.get('deducible'):
            data.append(['Deducible', f"{moneda} {float(siniestro['deducible']):,.2f}"])
        if siniestro.get('coaseguro'):
            data.append(['Coaseguro', f"{moneda} {float(siniestro['coaseguro']):,.2f}"])
        if siniestro.get('no_cubierto'):
            data.append(['No Cubierto', f"{moneda} {float(siniestro['no_cubierto']):,.2f}"])
        if siniestro.get('total_indemnizar'):
            data.append(['Total Indemnización', f"{moneda} {float(siniestro['total_indemnizar']):,.2f}"])
        if siniestro.get('fec_pago'):
            data.append(['Fecha de Pago', siniestro['fec_pago']])

        if data:
            table = Table(data, colWidths=[label_w, value_w])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('NOSPLIT', (0, 0), (-1, -1)),
                ('BOX', (0,0), (-1,-1), 0.5, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            elements.append(KeepTogether([subtitle_para, table]))
            elements.append(Spacer(1, 0.12*inch))

    # Descripción de hechos
    if siniestro.get('descripcion_hechos'):
        elements.append(Spacer(1, 0.12*inch))
        elements.append(Paragraph(siniestro['descripcion_hechos'], normal_small))
        elements.append(Spacer(1, 0.12*inch))

    # SEGUIMIENTO
    if siniestro.get('liquidador_ajustador') or siniestro.get('estado'):
        subtitle_para = Paragraph("SEGUIMIENTO", subtitle_style)
        data = []
        data.append(['Fecha', 'Comentario', 'Próx Fecha', 'Gestión a'])
        data.append(['Atentamente', '', '', ''])

        # tabla de 4 columnas compacta (dos pares label/value por fila)
        half = doc.width / 2
        col1_label = 1.1 * inch
        col3_label = 1.1 * inch
        table = Table(data, colWidths=[col1_label, half - col1_label, col3_label, half - col3_label])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('NOSPLIT', (0, 0), (-1, -1)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        elements.append(KeepTogether([subtitle_para, table]))
        elements.append(Spacer(1, 0.12*inch))

    # Footer
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("ARIAS & ARIAS CORREDORES DE SEGUROS SAC.", footer_style))
    elements.append(Paragraph(f"Código: {siniestro.get('siniestro_no', '')}", footer_style))
    elements.append(Spacer(1, 0.05*inch))
    elements.append(Paragraph("E-mail: info@ariasyarias.com", footer_style))

    doc.build(elements, onFirstPage=_insert_logo, onLaterPages=_insert_logo)


def _generar_pdf_generico(buffer, siniestro):
    """Genera PDF genérico para otros tipos de siniestros"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER


    header_reserved = LOGO_MAX_H + LOGO_TOP_MARGIN + HEADER_EXTRA
    doc = SimpleDocTemplate(buffer, pagesize=(7.5*inch, 11*inch), topMargin=header_reserved, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=4,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    normal_small = ParagraphStyle('NormalSmall', parent=styles['Normal'], fontSize=8, spaceAfter=2)

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )

    label_w = 1.4 * inch
    value_w = doc.width - label_w

    # Encabezado
    elements.append(Paragraph("ARIAS & ARIAS CORREDORES DE SEGUROS SAC.", title_style))
    elements.append(Paragraph(f"Código: {siniestro.get('siniestro_no', '')}", normal_small))
    elements.append(Spacer(1, 0.15*inch))

    elements.append(Paragraph("REPORTE DE SINIESTRO", title_style))
    elements.append(Paragraph(f"Registrado el: {siniestro.get('fec_stro', '')}", normal_small))
    elements.append(Spacer(1, 0.12*inch))

    # INFORMACIÓN DEL SINIESTRO
    subtitle_para = Paragraph("INFORMACIÓN DEL SINIESTRO", subtitle_style)
    data = []

    if siniestro.get('siniestro_no'):
        data.append(['No. Siniestro', siniestro['siniestro_no']])
    if siniestro.get('cia'):
        data.append(['Cia. de Seguros', siniestro['cia']])
    if siniestro.get('contratante'):
        data.append(['Contratante', siniestro['contratante']])
    if siniestro.get('asegurado'):
        data.append(['Asegurado', siniestro['asegurado']])
    if siniestro.get('poliza'):
        data.append(['Póliza', siniestro['poliza']])
    if siniestro.get('ramo'):
        data.append(['Ramo', siniestro['ramo']])
    if siniestro.get('fec_stro'):
        data.append(['Fecha Siniestro', siniestro['fec_stro']])
    if siniestro.get('lugar_siniestro'):
        data.append(['Lugar', siniestro['lugar_siniestro']])
    if siniestro.get('causa'):
        data.append(['Causa', siniestro['causa']])
    if siniestro.get('estado'):
        data.append(['Estado', siniestro['estado']])

    if data:
        table = Table(data, colWidths=[label_w, value_w])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('NOSPLIT', (0, 0), (-1, -1)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        elements.append(KeepTogether([subtitle_para, table]))
        elements.append(Spacer(1, 0.12*inch))

    # Descripción
    if siniestro.get('descripcion_hechos'):
        elements.append(Paragraph("DESCRIPCIÓN", subtitle_style))
        elements.append(Paragraph(siniestro['descripcion_hechos'], normal_small))
        elements.append(Spacer(1, 0.12*inch))

    # SEGUIMIENTO
    if siniestro.get('liquidador_ajustador') or siniestro.get('estado'):
        subtitle_para = Paragraph("SEGUIMIENTO", subtitle_style)
        data = []
        data.append(['Fecha', 'Comentario', 'Próx Fecha', 'Gestión a'])
        data.append(['Atentamente', '', '', ''])

        # tabla de 4 columnas compacta (dos pares label/value por fila)
        half = doc.width / 2
        col1_label = 1.1 * inch
        col3_label = 1.1 * inch
        table = Table(data, colWidths=[col1_label, half - col1_label, col3_label, half - col3_label])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('NOSPLIT', (0, 0), (-1, -1)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        elements.append(KeepTogether([subtitle_para, table]))
        elements.append(Spacer(1, 0.12*inch))

    # Footer
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("E-mail: info@ariasyarias.com", footer_style))
    elements.append(Paragraph("1", footer_style))

    doc.build(elements, onFirstPage=_insert_logo, onLaterPages=_insert_logo)
