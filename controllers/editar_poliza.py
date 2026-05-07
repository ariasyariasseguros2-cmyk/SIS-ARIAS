from models.db import get_connection, get_encrypt_key
from datetime import datetime
from flask import session

def _parse_date(d_str):
    if not d_str: return None
    try:
        # Intenta formato dd/mm/yyyy
        return datetime.strptime(d_str, '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        # Si falla, asume que ya es yyyy-mm-dd o inválido, devuelve tal cual
        return d_str

def get_poliza_data(poliza_id):
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        k = get_encrypt_key()
        cur.execute("""
            SELECT
                p.idPoliza,
                p.cliente_id,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), %s) AS CHAR),
                         CAST(AES_DECRYPT(p.asegurado, %s) AS CHAR),
                         p.asegurado) AS asegurado,
                p.cia,
                p.ramo,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.poliza), %s) AS CHAR),
                         CAST(AES_DECRYPT(p.poliza, %s) AS CHAR),
                         p.poliza) AS poliza,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), %s) AS CHAR),
                         CAST(AES_DECRYPT(p.recibo, %s) AS CHAR),
                         p.recibo) AS recibo,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.contrato_nro), %s) AS CHAR),
                         CAST(AES_DECRYPT(p.contrato_nro, %s) AS CHAR),
                         p.contrato_nro) AS contrato_nro,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.nro), %s) AS CHAR),
                         CAST(AES_DECRYPT(p.nro, %s) AS CHAR),
                         p.nro) AS nro,
                p.moneda,
                p.fecha_emision,
                p.vig_desde,
                p.vig_hasta,
                p.ultimo_dia_pago,
                p.fecha_vencimiento,
                p.tipo_vigencia,
                p.endosatario,
                p.forma_pago,
                p.sub_agente,
                p.ejecutivo,
                p.tipo_doc,
                p.asegurada,
                p.motivo,
                p.prima_comercial,
                p.prima_neta,
                p.prima_comercial_igv,
                p.prima_total,
                p.porc_compania,
                p.imp_compania,
                p.porc_subagente,
                p.imp_subagente,
                p.ramos_producto,
                p.estado,
                p.usuario_registro,
                p.usuario_edicion,
                p.creado_en,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), %s) AS CHAR),
                         CAST(AES_DECRYPT(c.razon_social, %s) AS CHAR),
                         c.razon_social) AS cliente_razon_social,
                c.tipo_documento AS cliente_tipo_documento,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), %s) AS CHAR),
                         CAST(AES_DECRYPT(c.numero_documento, %s) AS CHAR),
                         c.numero_documento) AS cliente_numero_documento,
                COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.telefono), %s) AS CHAR),
                         CAST(AES_DECRYPT(c.telefono, %s) AS CHAR),
                         c.telefono) AS cliente_telefono
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
            WHERE p.idPoliza = %s
        """, (k, k, k, k, k, k, k, k, k, k, k, k, k, k, k, k, poliza_id))
        row = cur.fetchone()

        cur.close()
        cnx.close()
        
        if row:
            # Normalize dates: ensure they are datetime objects or strings if needed.
            # Currently the view uses strftime, so we prefer keeping them as date objects.
            # If they are strings (from DB driver), we might need to parse them, 
            # but usually mysql-connector returns date objects.
            pass
            
            # Formats for specific fields if needed
            
        return row
    except Exception as e:
        print(f"Error getting poliza data: {e}")
        return None

def update_poliza(data):
    try:
        pid = data.get('idPoliza')
        if not pid:
            return {'ok': False, 'error': 'ID de Póliza no proporcionado'}

        # Obtener datos existentes para preservar campos no enviados
        current = get_poliza_data(pid)
        if not current:
            return {'ok': False, 'error': 'Póliza no encontrada'}

        cnx = get_connection()
        cur = cnx.cursor()

        try:
            recibo_new = data.get('recibo') if 'recibo' in data else None
            if isinstance(recibo_new, str):
                recibo_new = recibo_new.strip()
            recibo_curr = (current.get('recibo') or '')
            if isinstance(recibo_curr, str):
                recibo_curr = recibo_curr.strip()

            cliente_id_new = data.get('cliente_id') if 'cliente_id' in data else None
            cliente_id_final = cliente_id_new if cliente_id_new not in (None, '') else current.get('cliente_id')

            if recibo_new:
                if str(recibo_new) != str(recibo_curr):
                    cur.execute(
                        """
                        SELECT 1
                        FROM polizas
                        WHERE cliente_id = %s
                          AND idPoliza <> %s
                          AND activo = 1
                          AND (anulado = 0 OR anulado IS NULL)
                          AND TRIM(COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                                CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                                recibo
                              )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                        LIMIT 1
                        """,
                        (cliente_id_final, pid, recibo_new),
                    )
                    if cur.fetchone():
                        cur.close()
                        cnx.close()
                        return {'ok': False, 'error': f'El recibo ya existe para este cliente: {recibo_new}'}
        except Exception:
            pass
        
        # Helper: si la clave está en data, usar su valor (None si vacío).
        # Si no está, usar valor actual de DB.
        def val(key, default=None):
            if key in data:
                v = data[key]
                # Convertir cadena vacía a None para la BD
                return v if v != '' else None
            return current.get(key, default)

        def date_val(key_data, key_curr):
            if key_data in data:
                return _parse_date(data[key_data])
            d = current.get(key_curr)
            if hasattr(d, 'strftime'):
                return d.strftime('%Y-%m-%d')
            return d

        params = (
            pid,
            val('asegurado'),
            val('cia'),
            val('ramo'),
            val('poliza'),
            val('moneda'),
            date_val('fecha_emision', 'fecha_emision'),
            date_val('vig_desde', 'vig_desde'),
            date_val('vig_hasta', 'vig_hasta'),
            val('sub_agente'),
            val('ejecutivo'),
            val('asegurada'), # descripcion
            val('motivo'),    # tipoVigencia
            val('prima_comercial'),
            val('prima_neta'),
            val('prima_comercial_igv'),
            val('prima_total'),
            val('porc_compania'),
            val('imp_compania'),
            val('porc_subagente'),
            val('imp_subagente'),
            val('ramos_producto'),
            val('tipo_doc'),
            val('estado'),
            val('nro_operacion', 'nro'), # Mapeo data['nro_operacion'] -> DB['nro']
            val('tipo_pago', 'forma_pago'), # Mapeo data['tipo_pago'] -> DB['forma_pago']
            val('recibo', 'recibo'), # Nuevo campo recibo (usado como primera cuota)
            val('tipo_vigencia'), # Nuevo
            val('endosatario'),   # Nuevo
            val('pdf_url'),       # p_pdf_path
            session.get('user') # p_usuario_edicion
        )
        
        # Updated call with 4 new parameters at the end (nro, forma_pago, recibo, pdf_path, usuario_edicion)
        cur.execute("""CALL sp_update_poliza(
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )""", params)
        
        cnx.commit()

        try:
            nuevo_cliente_id = val('cliente_id', current.get('cliente_id'))
            if nuevo_cliente_id:
                cu_cli = cnx.cursor()
                cu_cli.execute(
                    "UPDATE polizas SET cliente_id = %s WHERE idPoliza = %s",
                    (nuevo_cliente_id, pid)
                )
                cnx.commit()
                cu_cli.close()
        except Exception:
            pass

        try:
            enc_vals = {
                'asegurado': val('asegurado'),
                'poliza': val('poliza'),
                'recibo': val('recibo'),
                'contrato_nro': val('contrato_nro') if 'contrato_nro' in data else current.get('contrato_nro'),
                'nro': val('nro_operacion', 'nro')
            }
            keys = get_encrypt_key()
            cu2 = cnx.cursor()
            cu2.execute("""
                UPDATE polizas SET
                  asegurado = CASE WHEN %s IS NULL THEN asegurado ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                  poliza = CASE WHEN %s IS NULL THEN poliza ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                  recibo = CASE WHEN %s IS NULL THEN recibo ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                  contrato_nro = CASE WHEN %s IS NULL THEN contrato_nro ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                  nro = CASE WHEN %s IS NULL THEN nro ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END
                WHERE idPoliza = %s
            """, (
                enc_vals['asegurado'], enc_vals['asegurado'], keys,
                enc_vals['poliza'], enc_vals['poliza'], keys,
                enc_vals['recibo'], enc_vals['recibo'], keys,
                enc_vals['contrato_nro'], enc_vals['contrato_nro'], keys,
                enc_vals['nro'], enc_vals['nro'], keys,
                pid
            ))
            cnx.commit()
            cu2.close()
        except Exception:
            pass
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        print(f"Error updating poliza: {e}")
        return {'ok': False, 'error': str(e)}
