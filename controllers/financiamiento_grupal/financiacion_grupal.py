from models.db import get_connection


def _format_amount(value):
    try:
        return "{:,.2f}".format(float(value or 0))
    except Exception:
        return "0.00"


def get_financiamiento_grupal_data():
    cnx = None
    cur = None
    rows = []

    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                fg.id_financiamiento_grupal,
                fg.nombre AS financiamiento_grupal,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS cliente,
                COALESCE(NULLIF(TRIM(cp.nombre_corto), ''), cp.nombre) AS compania,
                fg.numero_cupones,
                fg.moneda,
                fg.importe,
                fg.primer_cupon,
                DATE_FORMAT(fg.fecha_primer_vencimiento, '%%d-%%m-%%Y') AS fecha_primer_vencimiento
            FROM financiamiento_grupal fg
            INNER JOIN clientes c
                ON c.idCliente = fg.cliente_id
            INNER JOIN companias cp
                ON cp.id_compania = fg.compania_id
            WHERE fg.activo = 1
            ORDER BY fg.id_financiamiento_grupal DESC
            """
        )
        rows = cur.fetchall() or []
    except Exception as exc:
        print(f"Error fetching financiamiento grupal: {exc}")
        rows = []
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if cnx:
                cnx.close()
        except Exception:
            pass

    total_importe = 0.0
    for row in rows:
        try:
            total_importe += float(row.get("importe") or 0)
        except Exception:
            pass
        row["importe_formatted"] = _format_amount(row.get("importe"))

    return {
        "title": "Financiamiento Grupal",
        "rows": rows,
        "total_registros": len(rows),
        "total_importe": _format_amount(total_importe),
    }
