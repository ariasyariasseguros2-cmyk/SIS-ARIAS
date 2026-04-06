# módulo: controllers/cliente.py
from flask import session
from utils.rbac import Roles

def get_clientes_data():
    from models.db import get_connection, get_encrypt_key

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        key = get_encrypt_key()
        
        role = session.get('role_name')
        if role == Roles.SUB_AGENTE:
            user = session.get('user')
            query = """
                SELECT 
                    idCliente, 
                    fecha_registro, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                        razon_social
                    ) AS razon_social,
                    tipo_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                        CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                        numero_documento
                    ) AS numero_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR),
                        CAST(AES_DECRYPT(telefono, %s) AS CHAR),
                        telefono
                    ) AS telefono, 
                    subagente, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR),
                        CAST(AES_DECRYPT(email, %s) AS CHAR),
                        email
                    ) AS email, 
                    direccion 
                FROM clientes 
                WHERE activo = 1 AND subagente = %s
                ORDER BY idCliente DESC
            """
            cur.execute(query, (key, key, key, key, key, key, key, key, user))
        else:
            cur.execute("""
                SELECT 
                    idCliente, 
                    fecha_registro, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                        razon_social
                    ) AS razon_social,
                    tipo_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                        CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                        numero_documento
                    ) AS numero_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR),
                        CAST(AES_DECRYPT(telefono, %s) AS CHAR),
                        telefono
                    ) AS telefono, 
                    subagente, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR),
                        CAST(AES_DECRYPT(email, %s) AS CHAR),
                        email
                    ) AS email, 
                    direccion 
                FROM clientes 
                WHERE activo = 1
                ORDER BY idCliente DESC
            """, (key, key, key, key, key, key, key, key))
            
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
    from models.db import get_connection, get_encrypt_key

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        key = get_encrypt_key()
        
        role = session.get('role_name')
        if role == Roles.SUB_AGENTE:
            user = session.get('user')
            q_like = f"%{query}%"
            sql = """
                SELECT 
                    idCliente, 
                    fecha_registro, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                        razon_social
                    ) AS razon_social,
                    tipo_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                        CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                        numero_documento
                    ) AS numero_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR),
                        CAST(AES_DECRYPT(telefono, %s) AS CHAR),
                        telefono
                    ) AS telefono, 
                    subagente, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR),
                        CAST(AES_DECRYPT(email, %s) AS CHAR),
                        email
                    ) AS email, 
                    direccion 
                FROM clientes 
                WHERE activo = 1 
                  AND subagente = %s 
                  AND (
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR) LIKE %s
                        OR CAST(AES_DECRYPT(razon_social, %s) AS CHAR) LIKE %s
                        OR razon_social LIKE %s
                        OR CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR) LIKE %s
                        OR CAST(AES_DECRYPT(numero_documento, %s) AS CHAR) LIKE %s
                        OR numero_documento LIKE %s
                  )
                ORDER BY idCliente DESC
                LIMIT 50
            """
            cur.execute(sql, (
                key, key,          # razon_social proj
                key, key,          # numero_documento proj
                key, key,          # telefono proj
                key, key,          # email proj
                user,              # subagente
                key, q_like,       # WHERE: dec b64 razon_social LIKE
                key, q_like,       # WHERE: dec bin razon_social LIKE
                q_like,            # WHERE: plain razon_social LIKE
                key, q_like,       # WHERE: dec b64 numero_documento LIKE
                key, q_like,       # WHERE: dec bin numero_documento LIKE
                q_like             # WHERE: plain numero_documento LIKE
            ))
        else:
            q_like = f"%{query}%"
            sql = """
                SELECT 
                    idCliente, 
                    fecha_registro, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                        razon_social
                    ) AS razon_social,
                    tipo_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                        CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                        numero_documento
                    ) AS numero_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR),
                        CAST(AES_DECRYPT(telefono, %s) AS CHAR),
                        telefono
                    ) AS telefono, 
                    subagente,
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR),
                        CAST(AES_DECRYPT(email, %s) AS CHAR),
                        email
                    ) AS email,
                    direccion
                FROM clientes 
                WHERE activo = 1 
                  AND (
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR) LIKE %s
                        OR CAST(AES_DECRYPT(razon_social, %s) AS CHAR) LIKE %s
                        OR razon_social LIKE %s
                        OR CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR) LIKE %s
                        OR CAST(AES_DECRYPT(numero_documento, %s) AS CHAR) LIKE %s
                        OR numero_documento LIKE %s
                  )
                ORDER BY idCliente DESC
                LIMIT 50
            """
            cur.execute(sql, (
                key, key,            # razon_social proj
                key, key,            # numero_documento proj
                key, key,            # telefono proj
                key, key,            # email proj
                key, q_like,         # WHERE: dec b64 razon_social LIKE
                key, q_like,         # WHERE: dec bin razon_social LIKE
                q_like,              # WHERE: plain razon_social LIKE
                key, q_like,         # WHERE: dec b64 numero_documento LIKE
                key, q_like,         # WHERE: dec bin numero_documento LIKE
                q_like               # WHERE: plain numero_documento LIKE
            ))
            
        db_rows = cur.fetchall()
        try:
            while cur.nextset():
                pass
        except Exception:
            pass
        cur.close()
        cnx.close()

        # Ordenar por idCliente DESC si el SP no fuerza el orden y limitar a 50
        try:
            db_rows = sorted(db_rows, key=lambda r: (r.get('idCliente') or 0), reverse=True)[:50]
        except Exception:
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
    from models.db import get_connection, get_encrypt_key

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        key = get_encrypt_key()
        
        role = session.get('role_name')
        if role == Roles.SUB_AGENTE:
            user = session.get('user')
            cur.execute("""
                SELECT 
                    idCliente, 
                    fecha_registro, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                        razon_social
                    ) AS razon_social,
                    tipo_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                        CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                        numero_documento
                    ) AS numero_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR),
                        CAST(AES_DECRYPT(telefono, %s) AS CHAR),
                        telefono
                    ) AS telefono, 
                    subagente, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR),
                        CAST(AES_DECRYPT(email, %s) AS CHAR),
                        email
                    ) AS email, 
                    direccion, 
                    tipo_persona
                FROM clientes 
                WHERE activo = 0 AND subagente = %s
                ORDER BY idCliente DESC
            """, (key, key, key, key, key, key, key, key, user))
        else:
            cur.execute("""
                SELECT 
                    idCliente, 
                    fecha_registro, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR),
                        CAST(AES_DECRYPT(razon_social, %s) AS CHAR),
                        razon_social
                    ) AS razon_social,
                    tipo_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                        CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                        numero_documento
                    ) AS numero_documento, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR),
                        CAST(AES_DECRYPT(telefono, %s) AS CHAR),
                        telefono
                    ) AS telefono, 
                    subagente, 
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR),
                        CAST(AES_DECRYPT(email, %s) AS CHAR),
                        email
                    ) AS email, 
                    direccion, 
                    tipo_persona
                FROM clientes 
                WHERE activo = 0
                ORDER BY idCliente DESC
            """, (key, key, key, key, key, key, key, key))
            
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
