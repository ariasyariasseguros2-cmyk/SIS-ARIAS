# módulo: controllers/cliente.py
from flask import session
from utils.rbac import Roles

def get_clientes_data():
    from models.db import get_connection

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        role = session.get('role_name')
        if role == Roles.SUB_AGENTE:
            # RLS: Filtrar por subagente (username)
            user = session.get('user')
            query = """
                SELECT idCliente, fecha_registro, razon_social, tipo_documento, numero_documento, 
                       telefono, subagente, email, direccion 
                FROM clientes 
                WHERE activo = 1 AND subagente = %s
                ORDER BY idCliente ASC
            """
            cur.execute(query, (user,))
        else:
            cur.execute("""
                SELECT idCliente, fecha_registro, razon_social, tipo_documento, numero_documento, 
                       telefono, subagente, email, direccion 
                FROM clientes 
                WHERE activo = 1
                ORDER BY idCliente ASC
            """)
            
        db_rows = cur.fetchall()
        try:
            while cur.nextset():
                pass
        except Exception:
            pass
        cur.close()
        cnx.close()

        for dr in db_rows:
            fec = dr.get('fecha_registro')
            fec_str = fec.strftime('%d-%m-%Y') if hasattr(fec, 'strftime') else (str(fec) if fec else '')
            rows.append({
                'idCliente': dr.get('idCliente'),
                'fec_reg': fec_str,
                'razon_social': dr.get('razon_social'),
                'doc': dr.get('tipo_documento'),
                'n_doc': dr.get('numero_documento'),
                'tel': dr.get('telefono'),
                'subagente': dr.get('subagente'),
                'email': dr.get('email'),
                'direccion': dr.get('direccion'),
            })
    except Exception:
        rows = []

    filters = {
        "orders": ["F. Reg.", "Razón Social", "Doc", "N.Doc", "Tel", "Email", "Subagente", "Dirección"]
    }
    return {"rows": rows, "filters": filters, "title": "Clientes"}


def search_clientes_data(query):
    from models.db import get_connection

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        role = session.get('role_name')
        if role == Roles.SUB_AGENTE:
            # RLS: Buscar solo en sus clientes
            user = session.get('user')
            q_like = f"%{query}%"
            sql = """
                SELECT idCliente, fecha_registro, razon_social, tipo_documento, numero_documento, 
                       telefono, subagente, email, direccion 
                FROM clientes 
                WHERE activo = 1 
                  AND subagente = %s 
                  AND (razon_social LIKE %s OR numero_documento LIKE %s)
                ORDER BY idCliente ASC
                LIMIT 50
            """
            cur.execute(sql, (user, q_like, q_like))
        else:
            cur.execute("CALL sp_buscar_cliente(%s)", (query,))
            
        db_rows = cur.fetchall()
        try:
            while cur.nextset():
                pass
        except Exception:
            pass
        cur.close()
        cnx.close()

        # Limitar resultados en Python si el SP no tiene LIMIT
        db_rows = db_rows[:50]

        for dr in db_rows:
            fec = dr.get('fecha_registro')
            fec_str = fec.strftime('%d-%m-%Y') if hasattr(fec, 'strftime') else (str(fec) if fec else '')
            rows.append({
                'idCliente': dr.get('idCliente'),
                'fec_reg': fec_str,
                'razon_social': dr.get('razon_social'),
                'doc': dr.get('tipo_documento'),
                'n_doc': dr.get('numero_documento'),
                'tel': dr.get('telefono'),
                'subagente': dr.get('subagente'),
                'email': dr.get('email'),
                'direccion': dr.get('direccion'),
            })
    except Exception:
        rows = []

    return {"rows": rows}


# Nueva función: listar clientes anulados (activo = 0)
def get_clientes_anulados_data():
    from models.db import get_connection

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        role = session.get('role_name')
        if role == Roles.SUB_AGENTE:
            # RLS: Filtrar anulados por subagente
            user = session.get('user')
            cur.execute("SELECT idCliente, fecha_registro, razon_social, tipo_documento, numero_documento, telefono, subagente, email, direccion, tipo_persona FROM clientes WHERE activo = 0 AND subagente = %s ORDER BY idCliente ASC", (user,))
        else:
            # No hay SP específico en el schema para anulados, hacemos SELECT directo
            cur.execute("SELECT idCliente, fecha_registro, razon_social, tipo_documento, numero_documento, telefono, subagente, email, direccion, tipo_persona FROM clientes WHERE activo = 0 ORDER BY idCliente ASC")
            
        db_rows = cur.fetchall()
        cur.close()
        cnx.close()

        for dr in db_rows:
            fec = dr.get('fecha_registro')
            fec_str = fec.strftime('%d-%m-%Y') if hasattr(fec, 'strftime') else (str(fec) if fec else '')
            rows.append({
                'idCliente': dr.get('idCliente'),
                'fec_reg': fec_str,
                'razon_social': dr.get('razon_social'),
                'doc': dr.get('tipo_documento'),
                'n_doc': dr.get('numero_documento'),
                'tel': dr.get('telefono'),
                'subagente': dr.get('subagente'),
                'email': dr.get('email'),
                'direccion': dr.get('direccion'),
            })
    except Exception:
        rows = []

    filters = {
        "orders": ["F. Reg.", "Razón Social", "Doc", "N.Doc", "Tel", "Email", "Subagente", "Dirección"]
    }
    return {"rows": rows, "filters": filters, "title": "Clientes Anulados"}
