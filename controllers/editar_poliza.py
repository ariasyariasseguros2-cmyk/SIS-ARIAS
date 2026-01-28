from models.db import get_connection
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
        
        row = None
        # Try SP first
        try:
            cur.execute("CALL sp_get_poliza_by_id(%s)", (poliza_id,))
            row = cur.fetchone()
            try:
                while cur.nextset(): pass
            except: pass
        except Exception:
            pass
            
        # Fallback if SP missing or failed
        if not row:
             cur.execute("""
                SELECT 
                    p.*,
                    c.razon_social AS cliente_razon_social,
                    c.tipo_documento AS cliente_tipo_documento,
                    c.numero_documento AS cliente_numero_documento,
                    c.telefono AS cliente_telefono
                FROM polizas p
                INNER JOIN clientes c ON c.idCliente = p.cliente_id
                WHERE p.idPoliza = %s
             """, (poliza_id,))
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
            None, # p_pdf_path, no soportado en este form por ahora
            session.get('user') # p_usuario_edicion
        )
        
        # Updated call with 4 new parameters at the end (nro, forma_pago, recibo, pdf_path, usuario_edicion)
        cur.execute("""CALL sp_update_poliza(
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )""", params)
        
        cnx.commit()
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        print(f"Error updating poliza: {e}")
        return {'ok': False, 'error': str(e)}
