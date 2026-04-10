from flask import request
from models.db import get_encrypt_key


def list_mis_contactos():
    """Retorna un dict con 'clientes' (lista de dicts) y 'search_query' para la plantilla.
    Busca en la columna razon_social usando búsqueda case-insensitive en MySQL.
    Limita resultados a 50 (con query) o 20 (sin query).
    """
    from models.db import get_connection

    q = request.args.get('q', '') or ''
    q = q.strip()

    clientes = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        key = get_encrypt_key()

        select_clause = (
            "SELECT "
            "COALESCE(CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR), CAST(AES_DECRYPT(razon_social, %s) AS CHAR), razon_social) AS razon_social, "
            "COALESCE(CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR), CAST(AES_DECRYPT(numero_documento, %s) AS CHAR), numero_documento) AS numero_documento, "
            "COALESCE(CAST(AES_DECRYPT(FROM_BASE64(telefono), %s) AS CHAR), CAST(AES_DECRYPT(telefono, %s) AS CHAR), telefono) AS telefono, "
            "COALESCE(CAST(AES_DECRYPT(FROM_BASE64(email), %s) AS CHAR), CAST(AES_DECRYPT(email, %s) AS CHAR), email) AS email "
            "FROM clientes "
        )
        select_params = (key, key, key, key, key, key, key, key)

        if q:
            q_like = f"%{q}%"
            sql = (
                select_clause
                + "WHERE activo = 1 "
                + "AND LOWER(COALESCE(CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR), CAST(AES_DECRYPT(razon_social, %s) AS CHAR), razon_social)) LIKE LOWER(%s) "
                + "ORDER BY razon_social ASC "
                + "LIMIT 50"
            )
            cur.execute(sql, select_params + (key, key, q_like))
        else:
            sql = (
                select_clause
                + "WHERE activo = 1 "
                + "ORDER BY razon_social ASC "
                + "LIMIT 20"
            )
            cur.execute(sql, select_params)

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
    except Exception as e:
        print(f"[ERROR] list_mis_contactos: {e}")
        clientes = []

    return {'clientes': clientes, 'search_query': q}
