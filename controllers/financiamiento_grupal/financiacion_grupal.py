import calendar
from datetime import datetime
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from models.db import get_connection

# #region debug-point F:report-helper
def _dbg_fg_cuotas(hypothesis_id: str, location: str, msg: str, data=None, run_id: str = 'pre'):
    try:
        import json
        import urllib.request
        debug_url = 'http://127.0.0.1:7777/event'
        debug_session = 'fg-cuotas-routing'
        try:
            with open('.dbg/fg-cuotas-routing.env', 'r', encoding='utf-8') as f:
                content = f.read()
            for line in content.splitlines():
                if line.startswith('DEBUG_SERVER_URL='):
                    debug_url = line.split('=', 1)[1].strip() or debug_url
                elif line.startswith('DEBUG_SESSION_ID='):
                    debug_session = line.split('=', 1)[1].strip() or debug_session
        except Exception:
            pass
        payload = {
            "sessionId": debug_session,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "msg": f"[DEBUG] {msg}",
            "data": data or {},
        }
        urllib.request.urlopen(
            urllib.request.Request(
                debug_url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=1,
        ).read()
    except Exception:
        pass
# #endregion


def _format_amount(value):
    try:
        return "{:,.2f}".format(float(value or 0))
    except Exception:
        return "0.00"


def _parse_date(value):
    s = str(value or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def _format_date_display(value):
    parsed = _parse_date(value)
    if parsed:
        return parsed.strftime("%d/%m/%Y")
    return str(value or "")


def _add_months(base_date, months_to_add):
    month_index = (base_date.month - 1) + months_to_add
    year = base_date.year + month_index // 12
    month = (month_index % 12) + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return base_date.replace(year=year, month=month, day=day)


def _increment_coupon(value, step):
    s = str(value or "").strip()
    if not s:
        return str(step + 1)

    start = len(s)
    while start > 0 and s[start - 1].isdigit():
        start -= 1

    if start == len(s):
        return s if step == 0 else f"{s}-{step + 1}"

    prefix = s[:start]
    numeric_part = s[start:]
    next_value = int(numeric_part) + step
    return f"{prefix}{str(next_value).zfill(len(numeric_part))}"


def _split_total_amount(total_value, total_parts):
    total_decimal = Decimal(str(total_value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parts = max(1, int(total_parts or 1))
    base = (total_decimal / Decimal(parts)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    amounts = [base for _ in range(parts)]
    remainder = (total_decimal - (base * parts)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cent = Decimal("0.01")
    idx = 0
    while remainder > Decimal("0.00"):
        amounts[idx] = (amounts[idx] + cent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        remainder = (remainder - cent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        idx = (idx + 1) % parts
    return amounts


def _build_financiamiento_grupal_cuotas(financiamiento_id, primer_cupon, numero_cupones, fecha_primer_vencimiento, moneda, importe):
    cuotas = []
    total_cupones = max(1, int(numero_cupones or 1))
    fecha_base = _parse_date(fecha_primer_vencimiento)
    if not fecha_base:
        raise ValueError("La fecha del primer vencimiento es inválida.")

    importe_cuota = Decimal(str(importe or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    poliza_ref = f"FG-{financiamiento_id}"

    for idx in range(total_cupones):
        fecha_venc = _add_months(fecha_base, idx)
        cuotas.append(
            {
                "poliza": poliza_ref,
                "cupon": _increment_coupon(primer_cupon, idx),
                "fecha_vencimiento": fecha_venc.strftime("%Y-%m-%d"),
                "moneda": (moneda or "").strip().upper() or "USD",
                "importe": importe_cuota,
                "numero_cuota": idx + 1,
            }
        )
    return cuotas


def _load_financiamiento_grupal_cuotas_rows(cur, financiamiento_id, poliza_ref):
    try:
        cur.execute(
            """
            SELECT
                idCuota,
                numero_cuota,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR),
                    cupon
                ) AS cupon,
                DATE_FORMAT(fecha_vencimiento, '%Y-%m-%d') AS fecha_vencimiento,
                moneda,
                importe,
                DATE_FORMAT(fecha_pago, '%Y-%m-%d') AS fecha_pago,
                factura,
                observacion
            FROM cuotas
            WHERE activo = 1
              AND (
                    financiamiento_grupal_id = %s
                 OR (
                        financiamiento_grupal_id IS NULL
                    AND TRIM(
                            COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                CAST(poliza AS CHAR CHARACTER SET utf8mb4)
                            )
                        ) COLLATE utf8mb4_bin = CAST(%s AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_bin
                    )
              )
            ORDER BY numero_cuota ASC, fecha_vencimiento ASC, idCuota ASC
            """,
            (financiamiento_id, poliza_ref),
        )
        return cur.fetchall() or []
    except Exception as exc:
        if "Unknown column 'financiamiento_grupal_id'" not in str(exc):
            raise
        cur.execute(
            """
            SELECT
                idCuota,
                numero_cuota,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR),
                    cupon
                ) AS cupon,
                DATE_FORMAT(fecha_vencimiento, '%Y-%m-%d') AS fecha_vencimiento,
                moneda,
                importe,
                DATE_FORMAT(fecha_pago, '%Y-%m-%d') AS fecha_pago,
                factura,
                observacion
            FROM cuotas
            WHERE activo = 1
              AND TRIM(
                    COALESCE(
                        CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                        CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                        CAST(poliza AS CHAR CHARACTER SET utf8mb4)
                    )
                  ) COLLATE utf8mb4_bin = CAST(%s AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_bin
            ORDER BY numero_cuota ASC, fecha_vencimiento ASC, idCuota ASC
            """,
            (poliza_ref,),
        )
        return cur.fetchall() or []


def _insert_financiamiento_grupal_cuotas_rows(
    cur,
    financiamiento_id,
    nombre,
    primer_cupon,
    numero_cupones,
    fecha_primer_vencimiento,
    moneda,
    importe,
    usuario,
):
    cuotas_generadas = _build_financiamiento_grupal_cuotas(
        financiamiento_id,
        primer_cupon,
        numero_cupones,
        fecha_primer_vencimiento,
        moneda,
        importe,
    )
    observacion = f"Financiamiento grupal: {nombre}"

    for cuota in cuotas_generadas:
        try:
            cur.execute(
                """
                INSERT INTO cuotas (
                    poliza_id,
                    financiamiento_grupal_id,
                    poliza,
                    cupon,
                    fecha_vencimiento,
                    moneda,
                    importe,
                    fecha_pago,
                    factura,
                    observacion,
                    usuario_registro,
                    numero_cuota,
                    activo
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
                """,
                (
                    None,
                    financiamiento_id,
                    cuota["poliza"],
                    cuota["cupon"],
                    cuota["fecha_vencimiento"],
                    cuota["moneda"],
                    cuota["importe"],
                    None,
                    None,
                    observacion,
                    usuario,
                    cuota["numero_cuota"],
                ),
            )
        except Exception as exc:
            if "Unknown column 'financiamiento_grupal_id'" not in str(exc):
                raise
            cur.execute(
                """
                INSERT INTO cuotas (
                    poliza_id,
                    poliza,
                    cupon,
                    fecha_vencimiento,
                    moneda,
                    importe,
                    fecha_pago,
                    factura,
                    observacion,
                    usuario_registro,
                    numero_cuota,
                    activo
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
                """,
                (
                    None,
                    cuota["poliza"],
                    cuota["cupon"],
                    cuota["fecha_vencimiento"],
                    cuota["moneda"],
                    cuota["importe"],
                    None,
                    None,
                    observacion,
                    usuario,
                    cuota["numero_cuota"],
                ),
            )
        cuota_id = cur.lastrowid
        try:
            cur.execute(
                """
                UPDATE cuotas
                SET poliza = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)),
                    cupon = CASE
                        WHEN %s IS NULL THEN NULL
                        ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                    END
                WHERE idCuota = %s
                """,
                (cuota["poliza"], cuota["cupon"], cuota["cupon"], cuota_id),
            )
        except Exception:
            pass


def _sync_financiamiento_grupal_cuotas(cur, detail, usuario=None):
    if not detail:
        return

    financiamiento_id = int(detail.get("id_financiamiento_grupal") or 0)
    if financiamiento_id <= 0:
        return

    poliza_ref = f"FG-{financiamiento_id}"
    current_rows = _load_financiamiento_grupal_cuotas_rows(cur, financiamiento_id, poliza_ref)
    expected_rows = _build_financiamiento_grupal_cuotas(
        financiamiento_id,
        detail.get("primer_cupon"),
        detail.get("numero_cupones"),
        detail.get("fecha_primer_vencimiento"),
        detail.get("moneda"),
        detail.get("importe"),
    )

    def normalize_current(row):
        return {
            "numero_cuota": int(row.get("numero_cuota") or 0),
            "cupon": str(row.get("cupon") or "").strip(),
            "fecha_vencimiento": str(row.get("fecha_vencimiento") or "").strip(),
            "moneda": str(row.get("moneda") or "").strip().upper(),
            "importe": Decimal(str(row.get("importe") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        }

    def normalize_expected(row):
        return {
            "numero_cuota": int(row.get("numero_cuota") or 0),
            "cupon": str(row.get("cupon") or "").strip(),
            "fecha_vencimiento": str(row.get("fecha_vencimiento") or "").strip(),
            "moneda": str(row.get("moneda") or "").strip().upper(),
            "importe": Decimal(str(row.get("importe") or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        }

    current_signature = [normalize_current(r) for r in current_rows]
    expected_signature = [normalize_expected(r) for r in expected_rows]

    if current_signature == expected_signature:
        return

    # Si ya existen las mismas cuotas del grupo, corrige importes/fechas/cupones
    # usando el importe del financiamiento, preservando factura y fecha de pago.
    if current_rows and len(current_rows) == len(expected_rows):
        current_ids = [int(r.get("idCuota") or 0) for r in current_rows]
        if all(current_ids):
            for current_row, expected_row in zip(current_rows, expected_rows):
                observacion_actual = str(current_row.get("observacion") or "").strip()
                observacion_default = f"Financiamiento grupal: {detail.get('financiamiento_grupal') or ''}".strip()
                observacion_final = observacion_actual or observacion_default
                cur.execute(
                    """
                    UPDATE cuotas
                    SET financiamiento_grupal_id = %s,
                        poliza = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)),
                        cupon = CASE
                            WHEN %s IS NULL THEN NULL
                            ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                        END,
                        fecha_vencimiento = %s,
                        moneda = %s,
                        importe = %s,
                        numero_cuota = %s,
                        observacion = %s,
                        usuario_edicion = COALESCE(%s, usuario_edicion)
                    WHERE idCuota = %s
                    """,
                    (
                        financiamiento_id,
                        expected_row.get("poliza"),
                        expected_row.get("cupon"),
                        expected_row.get("cupon"),
                        expected_row.get("fecha_vencimiento"),
                        expected_row.get("moneda"),
                        expected_row.get("importe"),
                        expected_row.get("numero_cuota"),
                        observacion_final,
                        usuario,
                        int(current_row.get("idCuota")),
                    ),
                )
            return

    safe_to_rebuild = all(
        not (r.get("fecha_pago") or "").strip()
        and not (r.get("factura") or "").strip()
        and "financiamiento grupal" in str(r.get("observacion") or "").lower()
        for r in current_rows
    )

    if current_rows and not safe_to_rebuild:
        return

    if current_rows:
        ids = [int(r.get("idCuota")) for r in current_rows if r.get("idCuota")]
        if ids:
            placeholders = ",".join(["%s"] * len(ids))
            params = [usuario] + ids
            cur.execute(
                f"""
                UPDATE cuotas
                SET activo = 0,
                    usuario_edicion = %s
                WHERE idCuota IN ({placeholders})
                """,
                tuple(params),
            )

    _insert_financiamiento_grupal_cuotas_rows(
        cur,
        financiamiento_id,
        detail.get("financiamiento_grupal") or "",
        detail.get("primer_cupon"),
        detail.get("numero_cupones"),
        detail.get("fecha_primer_vencimiento"),
        detail.get("moneda"),
        detail.get("importe"),
        usuario,
    )


def _set_regular_cuotas_active_by_poliza(cur, poliza_id, active_value, usuario=None):
    try:
        poliza_id = int(poliza_id or 0)
    except Exception:
        poliza_id = 0
    if poliza_id <= 0:
        return

    active_value = 1 if int(active_value or 0) else 0
    usuario_value = (usuario or "").strip() or None
    cur.execute(
        """
        UPDATE cuotas
        SET activo = %s,
            usuario_edicion = COALESCE(%s, usuario_edicion)
        WHERE poliza_id = %s
          AND (financiamiento_grupal_id IS NULL OR financiamiento_grupal_id = 0)
        """,
        (active_value, usuario_value, poliza_id),
    )


def _sync_financiamiento_grupal_related_regular_cuotas(cur, financiamiento_id, usuario=None):
    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0
    if financiamiento_id <= 0:
        return

    cur.execute(
        """
        SELECT poliza_id
        FROM financiamiento_grupal_avisos
        WHERE financiamiento_grupal_id = %s
          AND activo = 1
          AND poliza_id IS NOT NULL
        """,
        (financiamiento_id,),
    )
    linked_rows = cur.fetchall() or []
    for row in linked_rows:
        poliza_id = row.get("poliza_id") if isinstance(row, dict) else None
        _set_regular_cuotas_active_by_poliza(cur, poliza_id, 0, usuario)


def _recalc_financiamiento_grupal_importe_from_avisos(cur, financiamiento_id, usuario=None):
    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0
    if financiamiento_id <= 0:
        return {"ok": False, "error": "ID inválido."}

    cur.execute(
        """
        SELECT poliza_id
        FROM financiamiento_grupal_avisos
        WHERE financiamiento_grupal_id = %s
          AND activo = 1
          AND poliza_id IS NOT NULL
        """,
        (financiamiento_id,),
    )
    polizas_rows = cur.fetchall() or []
    poliza_ids = [int(r.get("poliza_id") or 0) for r in polizas_rows if (r.get("poliza_id") or 0)]
    poliza_ids = [pid for pid in poliza_ids if pid > 0]
    if not poliza_ids:
        return {"ok": True, "importe": None, "moneda": None}

    placeholders = ",".join(["%s"] * len(poliza_ids))
    cur.execute(
        f"""
        SELECT
            p.moneda,
            SUM(COALESCE(p.prima_comercial_igv, p.prima_total, 0)) AS total
        FROM polizas p
        WHERE p.idPoliza IN ({placeholders})
          AND p.activo = 1
        GROUP BY p.moneda
        """,
        tuple(poliza_ids),
    )
    sums = cur.fetchall() or []
    if not sums:
        return {"ok": True, "importe": None, "moneda": None}
    if len(sums) > 1:
        monedas = ", ".join([str(r.get("moneda") or "").strip() for r in sums if (r.get("moneda") or "").strip()])
        return {"ok": False, "error": f"Las pólizas tienen distintas monedas: {monedas}."}

    moneda = (sums[0].get("moneda") or "").strip()
    total = sums[0].get("total") or 0
    usuario_value = (usuario or "").strip() or None
    cur.execute(
        """
        UPDATE financiamiento_grupal
        SET importe = %s,
            moneda = CASE WHEN %s <> '' THEN %s ELSE moneda END,
            usuario_modificacion = COALESCE(%s, usuario_modificacion)
        WHERE id_financiamiento_grupal = %s
          AND activo = 1
        """,
        (total, moneda, moneda, usuario_value, financiamiento_id),
    )
    return {"ok": True, "importe": total, "moneda": moneda}


def _load_financiamiento_grupal_detail_for_sync(cur, financiamiento_id):
    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0
    if financiamiento_id <= 0:
        return None

    cur.execute(
        """
        SELECT
            id_financiamiento_grupal,
            nombre AS financiamiento_grupal,
            numero_cupones,
            moneda,
            importe,
            primer_cupon,
            DATE_FORMAT(fecha_primer_vencimiento, '%Y-%m-%d') AS fecha_primer_vencimiento
        FROM financiamiento_grupal
        WHERE id_financiamiento_grupal = %s
          AND activo = 1
        LIMIT 1
        """,
        (financiamiento_id,),
    )
    return cur.fetchone()


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
                DATE_FORMAT(fg.fecha_primer_vencimiento, '%d/%m/%Y') AS fecha_primer_vencimiento
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
                DATE_FORMAT(fg.fecha_primer_vencimiento, '%d/%m/%Y') AS fecha_primer_vencimiento
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

        if not new_id:
            raise ValueError("No se pudo obtener el ID del financiamiento grupal.")

        _insert_financiamiento_grupal_cuotas_rows(
            cur,
            new_id,
            nombre,
            primer_cupon,
            numero_cupones,
            fecha_primer_vencimiento,
            moneda,
            importe,
            usuario,
        )

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


def get_financiamiento_grupal_cuotas_data(financiamiento_id):
    cnx = None
    cur = None
    detail = None
    rows = []

    try:
        financiamiento_id = int(financiamiento_id or 0)
    except Exception:
        financiamiento_id = 0

    if financiamiento_id <= 0:
        return {"title": "Cuotas", "detail": None, "rows": [], "total_monto": "0.00"}

    try:
        # #region debug-point F:fg-cuotas-entry
        _dbg_fg_cuotas('F', 'controllers/financiamiento_grupal/financiacion_grupal.py:get_financiamiento_grupal_cuotas_data', 'Entrada get_financiamiento_grupal_cuotas_data', {"financiamiento_id": financiamiento_id})
        # #endregion
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
                DATE_FORMAT(fg.fecha_primer_vencimiento, '%d/%m/%Y') AS fecha_primer_vencimiento
            FROM financiamiento_grupal fg
            INNER JOIN clientes c ON c.idCliente = fg.cliente_id
            INNER JOIN companias cp ON cp.id_compania = fg.compania_id
            WHERE fg.id_financiamiento_grupal = %s
              AND fg.activo = 1
            LIMIT 1
            """,
            (financiamiento_id,),
        )
        detail = cur.fetchone()
        # #region debug-point F:fg-cuotas-detail
        _dbg_fg_cuotas('F', 'controllers/financiamiento_grupal/financiacion_grupal.py:get_financiamiento_grupal_cuotas_data', 'Resultado consulta cabecera FG', {"financiamiento_id": financiamiento_id, "detail_ok": bool(detail), "detail_nombre": (detail or {}).get("financiamiento_grupal"), "cliente": (detail or {}).get("cliente"), "compania": (detail or {}).get("compania")})
        # #endregion

        if detail:
            # #region debug-point F:fg-cuotas-before-sync
            _dbg_fg_cuotas('F', 'controllers/financiamiento_grupal/financiacion_grupal.py:get_financiamiento_grupal_cuotas_data', 'Antes de sincronizar cuotas FG', {"financiamiento_id": financiamiento_id})
            # #endregion
            _sync_financiamiento_grupal_related_regular_cuotas(cur, financiamiento_id)
            _sync_financiamiento_grupal_cuotas(cur, detail)
            cnx.commit()
            poliza_ref = f"FG-{financiamiento_id}"
            raw_rows = _load_financiamiento_grupal_cuotas_rows(cur, financiamiento_id, poliza_ref)
            # #region debug-point F:fg-cuotas-after-load
            _dbg_fg_cuotas('F', 'controllers/financiamiento_grupal/financiacion_grupal.py:get_financiamiento_grupal_cuotas_data', 'Cuotas FG cargadas', {"financiamiento_id": financiamiento_id, "poliza_ref": poliza_ref, "rows": len(raw_rows or [])})
            # #endregion
            for idx, row in enumerate(raw_rows, start=1):
                rows.append(
                    {
                        "idCuota": row.get("idCuota"),
                        "secuencia": idx,
                        "numero_cuota": row.get("numero_cuota") or idx,
                        "cupon": row.get("cupon") or "",
                        "fecha_vencimiento": _format_date_display(row.get("fecha_vencimiento") or ""),
                        "moneda": row.get("moneda") or (detail.get("moneda") or ""),
                        "importe": _format_amount(row.get("importe")),
                        "fecha_pago": _format_date_display(row.get("fecha_pago") or "") if row.get("fecha_pago") else "",
                        "factura": row.get("factura") or "",
                        "observacion": row.get("observacion") or "",
                    }
                )
    except Exception as exc:
        # #region debug-point F:fg-cuotas-error
        _dbg_fg_cuotas('F', 'controllers/financiamiento_grupal/financiacion_grupal.py:get_financiamiento_grupal_cuotas_data', 'Error en carga de cuotas FG', {"financiamiento_id": financiamiento_id, "error": str(exc)})
        # #endregion
        print(f"Error fetching financiamiento grupal cuotas data: {exc}")
        detail = None
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

    if detail:
        detail["importe_formatted"] = _format_amount(detail.get("importe"))
        detail["fecha_primer_vencimiento"] = _format_date_display(detail.get("fecha_primer_vencimiento"))

    total_monto = _format_amount(sum(Decimal(str(r.get("importe") or "0").replace(",", "")) for r in rows))
    return {
        "title": f"Cuotas - {detail.get('financiamiento_grupal')}" if detail else "Cuotas",
        "detail": detail,
        "rows": rows,
        "total_monto": total_monto,
    }


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
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
                    p.recibo
                ) AS aviso,
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
                DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
                DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
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
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
                    p.recibo
                ) AS aviso,
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
                DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
                DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin
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
        usuario = None
        try:
            usuario = cnx.user
        except Exception:
            usuario = None
        _set_regular_cuotas_active_by_poliza(cur, poliza_id, 0, usuario)
        detail = _load_financiamiento_grupal_detail_for_sync(cur, financiamiento_id) or {}
        _sync_financiamiento_grupal_cuotas(cur, detail, usuario)
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
        cur = cnx.cursor(dictionary=True)
        cur.execute(
            """
            SELECT poliza_id
            FROM financiamiento_grupal_avisos
            WHERE id_item = %s AND financiamiento_grupal_id = %s
            LIMIT 1
            """,
            (item_id, financiamiento_id),
        )
        current_item = cur.fetchone() or {}
        poliza_id = int(current_item.get("poliza_id") or 0)
        cur.execute(
            """
            UPDATE financiamiento_grupal_avisos
            SET activo = 0
            WHERE id_item = %s AND financiamiento_grupal_id = %s
            """,
            (item_id, financiamiento_id),
        )
        if cur.rowcount == 0:
            cnx.rollback()
            return {"ok": False, "error": "Registro no encontrado."}
        usuario = None
        try:
            usuario = cnx.user
        except Exception:
            usuario = None
        _set_regular_cuotas_active_by_poliza(cur, poliza_id, 1, usuario)
        detail = _load_financiamiento_grupal_detail_for_sync(cur, financiamiento_id) or {}
        _sync_financiamiento_grupal_cuotas(cur, detail, usuario)
        cnx.commit()
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
