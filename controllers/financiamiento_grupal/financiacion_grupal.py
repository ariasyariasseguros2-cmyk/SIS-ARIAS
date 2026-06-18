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


def get_financiamiento_grupal_form_options():
    cnx = None
    cur = None
    clientes = []
    companias = []
    monedas = [
        {"id": "PEN", "nombre": "PEN"},
        {"id": "USD", "nombre": "USD"},
    ]

    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        cur.execute(
            """
            SELECT
                idCliente AS id,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(razon_social, @SIS_KEY) AS CHAR),
                    razon_social
                ) AS nombre
            FROM clientes
            WHERE activo = 1
            ORDER BY nombre ASC
            """
        )
        clientes = cur.fetchall() or []

        cur.execute(
            """
            SELECT
                id_compania AS id,
                COALESCE(NULLIF(TRIM(nombre_corto), ''), nombre) AS nombre
            FROM companias
            ORDER BY nombre ASC
            """
        )
        companias = cur.fetchall() or []
    except Exception as exc:
        print(f"Error loading financiamiento grupal options: {exc}")
        clientes = []
        companias = []
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

    return {
        "clientes": clientes,
        "companias": companias,
        "monedas": monedas,
    }


def insert_financiamiento_grupal(payload):
    cnx = None
    cur = None
    try:
        nombre = (payload.get("nombre") or "").strip()
        cliente_id = int(payload.get("cliente_id") or 0)
        compania_id = int(payload.get("compania_id") or 0)
        moneda = (payload.get("moneda") or "").strip().upper()
        numero_cupones = int(payload.get("numero_cupones") or 0)
        primer_cupon = (payload.get("primer_cupon") or "").strip() or None
        importe = float(payload.get("importe") or 0)
        fecha_primer_vencimiento = (payload.get("fecha_primer_vencimiento") or "").strip()
        usuario = (payload.get("usuario") or "").strip() or None

        if not nombre:
            return {"ok": False, "error": "El nombre de financiamiento es obligatorio."}
        if cliente_id <= 0:
            return {"ok": False, "error": "Debe seleccionar un cliente."}
        if compania_id <= 0:
            return {"ok": False, "error": "Debe seleccionar una compañía."}
        if not moneda:
            return {"ok": False, "error": "Debe seleccionar una moneda."}
        if numero_cupones <= 0:
            return {"ok": False, "error": "El número de cupones debe ser mayor a cero."}
        if not primer_cupon:
            return {"ok": False, "error": "El primer cupón es obligatorio."}
        if importe <= 0:
            return {"ok": False, "error": "El importe debe ser mayor a cero."}
        if not fecha_primer_vencimiento:
            return {"ok": False, "error": "La fecha del primer vencimiento es obligatoria."}

        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute(
            "CALL sp_insert_financiamiento_grupal(%s,%s,%s,%s,%s,%s,%s,%s,@p_new_id)",
            (
                nombre,
                cliente_id,
                compania_id,
                moneda,
                numero_cupones,
                primer_cupon,
                importe,
                fecha_primer_vencimiento,
            ),
        )
        while cur.nextset():
            pass

        if usuario:
            try:
                cur.execute(
                    """
                    UPDATE financiamiento_grupal
                    SET usuario_creacion = %s, usuario_modificacion = %s
                    WHERE id_financiamiento_grupal = LAST_INSERT_ID()
                    """,
                    (usuario, usuario),
                )
            except Exception:
                pass

        cur.execute("SELECT @p_new_id")
        row = cur.fetchone()
        new_id = int(row[0]) if row and row[0] else None
        cnx.commit()
        return {"ok": True, "id": new_id}
    except Exception as exc:
        try:
            if cnx:
                cnx.rollback()
        except Exception:
            pass
        return {"ok": False, "error": str(exc)}
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
