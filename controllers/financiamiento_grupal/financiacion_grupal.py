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


def get_financiamiento_grupal_avisos_data(financiamiento_id):
    cnx = None
    cur = None
    detail = None

    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0

    if financiamiento_id <= 0:
        return {
            "title": "Primas / Plan de Pagos",
            "detail": None,
            "rows": [],
        }

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
            WHERE fg.id_financiamiento_grupal = %s
              AND fg.activo = 1
            LIMIT 1
            """,
            (financiamiento_id,),
        )
        detail = cur.fetchone()
    except Exception as exc:
        print(f"Error fetching financiamiento grupal avisos data: {exc}")
        detail = None
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

    if detail:
        detail["importe_formatted"] = _format_amount(detail.get("importe"))

    return {
        "title": "Primas / Plan de Pagos",
        "detail": detail,
        "rows": [],
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


def list_financiamiento_grupal_avisos(financiamiento_id):
    cnx = None
    cur = None
    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0

    if financiamiento_id <= 0:
        return {"ok": False, "error": "ID de financiamiento inválido.", "rows": []}

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                i.id_item,
                p.idPoliza,
                p.recibo AS aviso,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                    p.poliza
                ) AS poliza,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS contratante,
                p.cia AS compania,
                p.ramo,
                p.tipo_doc AS tipo,
                p.moneda,
                p.prima_comercial,
                p.prima_neta,
                COALESCE(p.prima_comercial_igv, p.prima_total) AS prima_total,
                DATE_FORMAT(p.vig_desde, '%%d-%%m-%%Y') AS vig_inicio,
                DATE_FORMAT(p.vig_hasta, '%%d-%%m-%%Y') AS vig_fin,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
                    p.nro
                ) AS nro_operacion,
                p.motivo
            FROM financiamiento_grupal_avisos i
            INNER JOIN polizas p ON p.idPoliza = i.poliza_id
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
            WHERE i.financiamiento_grupal_id = %s
              AND i.activo = 1
            ORDER BY i.id_item DESC
            """,
            (financiamiento_id,),
        )
        rows = cur.fetchall() or []
    except Exception as exc:
        msg = str(exc)
        if "financiamiento_grupal_avisos" in msg and ("doesn't exist" in msg or "does not exist" in msg or "no such table" in msg):
            msg = "Falta crear la tabla financiamiento_grupal_avisos en la base de datos."
        return {"ok": False, "error": msg, "rows": []}
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

    normalized = []
    for r in rows:
        normalized.append(
            {
                "id_item": r.get("id_item"),
                "idPoliza": r.get("idPoliza"),
                "aviso": r.get("aviso") or "",
                "poliza": r.get("poliza") or "",
                "contratante": r.get("contratante") or "",
                "compania": r.get("compania") or "",
                "ramo": r.get("ramo") or "",
                "tipo": r.get("tipo") or "",
                "moneda": r.get("moneda") or "",
                "prima_comercial": _format_amount(r.get("prima_comercial")),
                "prima_neta": _format_amount(r.get("prima_neta")),
                "prima_total": _format_amount(r.get("prima_total")),
                "vig_inicio": r.get("vig_inicio") or "",
                "vig_fin": r.get("vig_fin") or "",
                "nro_operacion": r.get("nro_operacion") or "",
                "motivo": r.get("motivo") or "",
            }
        )

    return {"ok": True, "rows": normalized}


def list_financiamiento_grupal_avisos_candidates(financiamiento_id):
    cnx = None
    cur = None
    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0

    if financiamiento_id <= 0:
        return {"ok": False, "error": "ID de financiamiento inválido.", "rows": []}

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                fg.cliente_id,
                NULLIF(TRIM(cp.nombre_corto), '') AS compania_corto,
                NULLIF(TRIM(cp.nombre), '') AS compania_nombre
            FROM financiamiento_grupal fg
            INNER JOIN companias cp ON cp.id_compania = fg.compania_id
            WHERE fg.id_financiamiento_grupal = %s AND fg.activo = 1
            LIMIT 1
            """,
            (financiamiento_id,),
        )
        fg = cur.fetchone() or {}
        cliente_id = int(fg.get("cliente_id") or 0)
        compania_corto = (fg.get("compania_corto") or "").strip()
        compania_nombre = (fg.get("compania_nombre") or "").strip()

        if cliente_id <= 0:
            return {"ok": True, "rows": []}

        compania_like = f"%{compania_corto}%" if compania_corto else "%"
        compania_nombre_like = f"%{compania_nombre}%" if compania_nombre else "%"
        cur.execute(
            """
            SELECT
                p.idPoliza,
                p.recibo AS aviso,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                    p.poliza
                ) AS poliza,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
                    c.razon_social
                ) AS contratante,
                p.cia AS compania,
                p.ramo,
                p.tipo_doc AS tipo,
                p.moneda,
                p.prima_comercial,
                p.prima_neta,
                COALESCE(p.prima_comercial_igv, p.prima_total) AS prima_total,
                DATE_FORMAT(p.vig_desde, '%%d-%%m-%%Y') AS vig_inicio,
                DATE_FORMAT(p.vig_hasta, '%%d-%%m-%%Y') AS vig_fin
            FROM polizas p
            INNER JOIN clientes c ON c.idCliente = p.cliente_id
            WHERE p.activo = 1
              AND (p.anulado = 0 OR p.anulado IS NULL)
              AND COALESCE(p.prima_anulada, 0) = 0
              AND p.cliente_id = %s
              AND (
                    (%s = '' AND %s = '')
                 OR LOWER(TRIM(p.cia)) = LOWER(TRIM(%s))
                 OR LOWER(TRIM(p.cia)) LIKE LOWER(TRIM(%s))
                 OR LOWER(TRIM(p.cia)) = LOWER(TRIM(%s))
                 OR LOWER(TRIM(p.cia)) LIKE LOWER(TRIM(%s))
              )
              AND NOT EXISTS (
                SELECT 1
                FROM financiamiento_grupal_avisos i
                WHERE i.financiamiento_grupal_id = %s
                  AND i.poliza_id = p.idPoliza
                  AND i.activo = 1
              )
            ORDER BY p.vig_desde DESC
            LIMIT 300
            """,
            (
                cliente_id,
                compania_corto,
                compania_nombre,
                compania_corto,
                compania_like,
                compania_nombre,
                compania_nombre_like,
                financiamiento_id,
            ),
        )
        rows = cur.fetchall() or []
    except Exception as exc:
        msg = str(exc)
        if "financiamiento_grupal_avisos" in msg and ("doesn't exist" in msg or "does not exist" in msg or "no such table" in msg):
            msg = "Falta crear la tabla financiamiento_grupal_avisos en la base de datos."
        return {"ok": False, "error": msg, "rows": []}
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

    normalized = []
    for r in rows:
        normalized.append(
            {
                "idPoliza": r.get("idPoliza"),
                "aviso": r.get("aviso") or "",
                "poliza": r.get("poliza") or "",
                "vig_inicio": r.get("vig_inicio") or "",
                "vig_fin": r.get("vig_fin") or "",
                "moneda": r.get("moneda") or "",
                "prima_comercial": _format_amount(r.get("prima_comercial")),
                "prima_neta": _format_amount(r.get("prima_neta")),
                "prima_total": _format_amount(r.get("prima_total")),
                "contratante": r.get("contratante") or "",
                "compania": r.get("compania") or "",
                "ramo": r.get("ramo") or "",
                "tipo": r.get("tipo") or "",
            }
        )

    return {"ok": True, "rows": normalized}


def add_financiamiento_grupal_aviso(financiamiento_id, poliza_id):
    cnx = None
    cur = None
    try:
        financiamiento_id = int(financiamiento_id or 0)
        poliza_id = int(poliza_id or 0)
    except Exception:
        return {"ok": False, "error": "Parámetros inválidos."}

    if financiamiento_id <= 0 or poliza_id <= 0:
        return {"ok": False, "error": "Parámetros inválidos."}

    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                fg.cliente_id,
                NULLIF(TRIM(cp.nombre_corto), '') AS compania_corto,
                NULLIF(TRIM(cp.nombre), '') AS compania_nombre
            FROM financiamiento_grupal fg
            INNER JOIN companias cp ON cp.id_compania = fg.compania_id
            WHERE fg.id_financiamiento_grupal = %s AND fg.activo = 1
            LIMIT 1
            """,
            (financiamiento_id,),
        )
        fg = cur.fetchone() or {}
        cliente_id = int(fg.get("cliente_id") or 0)
        compania_corto = (fg.get("compania_corto") or "").strip()
        compania_nombre = (fg.get("compania_nombre") or "").strip()
        if cliente_id <= 0:
            return {"ok": False, "error": "Financiamiento no encontrado."}

        cur.execute(
            """
            SELECT idPoliza, cliente_id, cia
            FROM polizas
            WHERE idPoliza = %s AND activo = 1
            LIMIT 1
            """,
            (poliza_id,),
        )
        p = cur.fetchone() or {}
        if not p:
            return {"ok": False, "error": "Póliza no encontrada."}
        if int(p.get("cliente_id") or 0) != cliente_id:
            return {"ok": False, "error": "La póliza no pertenece al cliente del financiamiento."}
        cia = str(p.get("cia") or "").strip().lower()
        corto = compania_corto.lower() if compania_corto else ""
        nombre = compania_nombre.lower() if compania_nombre else ""
        if (corto or nombre) and cia:
            ok_compania = False
            if corto:
                ok_compania = ok_compania or (cia == corto) or (corto in cia) or (cia in corto)
            if nombre:
                ok_compania = ok_compania or (cia == nombre) or (nombre in cia) or (cia in nombre)
            if not ok_compania:
                return {"ok": False, "error": "La póliza no pertenece a la compañía del financiamiento."}

        cur.execute(
            """
            INSERT INTO financiamiento_grupal_avisos (financiamiento_grupal_id, poliza_id, activo)
            VALUES (%s, %s, 1)
            """,
            (financiamiento_id, poliza_id),
        )
        cnx.commit()
        return {"ok": True, "id_item": cur.lastrowid}
    except Exception as exc:
        try:
            if cnx:
                cnx.rollback()
        except Exception:
            pass
        msg = str(exc)
        if "financiamiento_grupal_avisos" in msg and ("doesn't exist" in msg or "does not exist" in msg or "no such table" in msg):
            msg = "Falta crear la tabla financiamiento_grupal_avisos en la base de datos."
        if "uk_fg_avisos_fin_poliza" in msg or "Duplicate entry" in msg:
            msg = "La póliza ya fue agregada a este financiamiento."
        return {"ok": False, "error": msg}
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


def remove_financiamiento_grupal_aviso(financiamiento_id, item_id):
    cnx = None
    cur = None
    try:
        financiamiento_id = int(financiamiento_id or 0)
        item_id = int(item_id or 0)
    except Exception:
        return {"ok": False, "error": "Parámetros inválidos."}

    if financiamiento_id <= 0 or item_id <= 0:
        return {"ok": False, "error": "Parámetros inválidos."}

    try:
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute(
            """
            UPDATE financiamiento_grupal_avisos
            SET activo = 0
            WHERE id_item = %s AND financiamiento_grupal_id = %s
            """,
            (item_id, financiamiento_id),
        )
        cnx.commit()
        if cur.rowcount == 0:
            return {"ok": False, "error": "Registro no encontrado."}
        return {"ok": True}
    except Exception as exc:
        try:
            if cnx:
                cnx.rollback()
        except Exception:
            pass
        msg = str(exc)
        if "financiamiento_grupal_avisos" in msg and ("doesn't exist" in msg or "does not exist" in msg or "no such table" in msg):
            msg = "Falta crear la tabla financiamiento_grupal_avisos en la base de datos."
        return {"ok": False, "error": msg}
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
