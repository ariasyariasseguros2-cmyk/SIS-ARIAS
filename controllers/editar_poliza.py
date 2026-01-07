from models.db import get_connection
from datetime import datetime

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
        cnx = get_connection()
        cur = cnx.cursor()
        
        # Prepare parameters matching sp_update_poliza order
        params = (
            data.get('idPoliza'),
            data.get('asegurado'),
            data.get('cia'),
            data.get('ramo'),
            data.get('poliza'),
            data.get('moneda'),
            _parse_date(data.get('vig_desde')),
            _parse_date(data.get('vig_hasta')),
            data.get('sub_agente'),
            data.get('ejecutivo'),
            data.get('asegurada'),
            data.get('motivo'),
            data.get('prima_comercial') or 0,
            data.get('prima_neta') or 0,
            data.get('prima_comercial_igv') or 0,
            data.get('prima_total') or 0,
            data.get('porc_compania') or 0,
            data.get('imp_compania') or 0,
            data.get('porc_subagente') or 0,
            data.get('imp_subagente') or 0,
            data.get('ramos_producto'),
            data.get('tipo_doc'),
            data.get('estado')
        )
        
        cur.execute("""CALL sp_update_poliza(
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s
        )""", params)
        
        cnx.commit()
        cur.close()
        cnx.close()
        return {'ok': True}
    except Exception as e:
        print(f"Error updating poliza: {e}")
        return {'ok': False, 'error': str(e)}
