from flask import request


def list_mis_contactos():
    """Retorna un dict con 'clientes' (lista de dicts) y 'search_query' para la plantilla.
    Busca en la columna razon_social usando búsqueda case-insensitive en MySQL.
    Limita resultados a 50.
    """
    from models.db import get_connection

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
                "SELECT razon_social,numero_documento,telefono, email "
                "FROM clientes "
                "WHERE activo = 1 AND LOWER(razon_social) LIKE LOWER(%s) "
                "ORDER BY razon_social ASC "
                "LIMIT 50"
            )
            cur.execute(sql, (q_like,))
        else:
            cur.execute(
                "SELECT razon_social,numero_documento, telefono, email "
                "FROM clientes "
                "WHERE activo = 1 "
                "ORDER BY razon_social ASC "
                "LIMIT 20"
            )

        rows = cur.fetchall() or []
        cur.close()
        cnx.close()

        for r in rows:
            clientes.append({
                'razon_social': r.get('razon_social') or '',
                'numero_documento': r.get('numero_documento') or '',
                'telefono': r.get('telefono') or '',
                'email': r.get('email') or ''
            })
    except Exception:
        clientes = []

    return {'clientes': clientes, 'search_query': q}

