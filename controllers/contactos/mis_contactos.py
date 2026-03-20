from flask import request


def list_mis_contactos():
    """Retorna un dict con 'clientes' (lista de dicts) y 'search_query' para la plantilla.
    Busca en la columna razon_social usando búsqueda case-insensitive en MySQL.
    Limita resultados a 50 (con query) o 20 (sin query).
    """
    from models.db import get_connection
    import re

    q = request.args.get('q', '') or ''
    q = q.strip()

    clientes = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        if q:
            q_like = f"%{q}%"
            # Búsqueda case-insensitive usando LOWER
            sql = (
                "SELECT razon_social, numero_documento, telefono, email "
                "FROM clientes "
                "WHERE activo = 1 AND LOWER(razon_social) LIKE LOWER(%s) "
                "ORDER BY razon_social ASC "
                "LIMIT 50"
            )
            cur.execute(sql, (q_like,))
        else:
            sql = (
                "SELECT razon_social, numero_documento, telefono, email "
                "FROM clientes "
                "WHERE activo = 1 "
                "ORDER BY razon_social ASC "
                "LIMIT 20"
            )
            cur.execute(sql)

        rows = cur.fetchall() or []
        cur.close()
        cnx.close()

        for r in rows:
            telefono = r.get('telefono') or ''
            email = r.get('email') or ''
            
            clientes.append({
                'razon_social': r.get('razon_social') or '',
                'numero_documento': r.get('numero_documento') or '',
                'telefono': telefono,
                'email': email if email else ''
            })
    except Exception as e:
        print(f"[ERROR] list_mis_contactos: {e}")
        clientes = []

    return {'clientes': clientes, 'search_query': q}

