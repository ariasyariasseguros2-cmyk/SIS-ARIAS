from models.db import get_connection


def get_produccion_soat(page=1, per_page=20, search='', fecha_desde=None, fecha_hasta=None):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        offset = (page - 1) * per_page

        where_clauses = ["p.ramo LIKE '%SOAT%'", "p.anulado = 0"]
        params = []

        if search:
            where_clauses.append(
                "(p.poliza LIKE %s OR p.recibo LIKE %s OR p.contrato_nro LIKE %s "
                "OR p.codigo_agente LIKE %s OR p.ejecutivo LIKE %s)"
            )
            s = f"%{search}%"
            params += [s, s, s, s, s]

        if fecha_desde:
            where_clauses.append("p.vig_hasta >= %s")
            params.append(fecha_desde)

        if fecha_hasta:
            where_clauses.append("p.vig_hasta <= %s")
            params.append(fecha_hasta)

        where_sql = " AND ".join(where_clauses)

        # Total
        cur.execute(f"SELECT COUNT(*) AS total FROM polizas p WHERE {where_sql}", params)
        total = cur.fetchone()['total']

        # Datos
        query = f"""
            SELECT
                p.idPoliza,
                p.poliza,
                p.recibo,
                p.contrato_nro                          AS planilla,
                p.codigo_agente                         AS codigo,
                p.ejecutivo                             AS vendedor,
                p.prima_neta,
                p.prima_comercial_igv,
                p.porc_compania,
                p.imp_compania,
                p.porc_subagente,
                p.imp_subagente,
                ROUND(COALESCE(p.imp_compania,0) - COALESCE(p.imp_subagente,0), 2) AS produccion_neta,
                p.vig_desde,
                p.vig_hasta,
                p.cia,
                p.asegurado,
                p.estado
            FROM polizas p
            WHERE {where_sql}
            ORDER BY p.creado_en DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [per_page, offset])
        rows = cur.fetchall()

        # Totales generales
        cur.execute(f"""
            SELECT
                ROUND(SUM(COALESCE(prima_neta,0)), 2)          AS total_prima_neta,
                ROUND(SUM(COALESCE(prima_comercial_igv,0)), 2) AS total_prima_igv,
                ROUND(SUM(COALESCE(imp_compania,0)), 2)        AS total_imp_compania,
                ROUND(SUM(COALESCE(imp_subagente,0)), 2)       AS total_imp_subagente,
                ROUND(SUM(COALESCE(imp_compania,0) - COALESCE(imp_subagente,0)), 2) AS total_produccion_neta
            FROM polizas p
            WHERE {where_sql}
        """, params)
        totales = cur.fetchone()

        return {
            'rows': rows,
            'total': total,
            'totales': totales
        }
    except Exception as e:
        print(f"Error en get_produccion_soat: {e}")
        return {'rows': [], 'total': 0, 'totales': {}}
    finally:
        cur.close()
        conn.close()


