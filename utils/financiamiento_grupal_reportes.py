import re
from datetime import datetime

from models.db import get_connection


FG_POLIZA_RE = re.compile(r"^\s*FG-(\d+)\s*$", re.IGNORECASE)



def _format_fg_date_display(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%d/%m/%Y")
        except Exception:
            pass
    text = str(value).strip()
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return text[:10]

def get_fg_cuotas_map(financiamiento_ids):
    fg_ids = _normalize_int_ids(financiamiento_ids)
    if not fg_ids:
        return {}

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        placeholders = ",".join(["%s"] * len(fg_ids))
        cursor.execute(
            f"""
            SELECT
                c.idCuota,
                c.financiamiento_grupal_id,
                c.numero_cuota,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(c.cupon), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(c.cupon, @SIS_KEY) AS CHAR),
                    c.cupon
                ) AS cupon,
                c.fecha_vencimiento,
                c.moneda,
                c.importe,
                c.fecha_pago,
                c.factura,
                c.observacion
            FROM cuotas c
            WHERE c.activo = 1
              AND c.financiamiento_grupal_id IN ({placeholders})
            ORDER BY c.financiamiento_grupal_id ASC, c.numero_cuota ASC, c.fecha_vencimiento ASC, c.idCuota ASC
            """,
            tuple(fg_ids),
        )
        out = {}
        for row in cursor.fetchall() or []:
            fg_id = row.get("financiamiento_grupal_id")
            try:
                fg_id = int(fg_id or 0)
            except Exception:
                fg_id = 0
            if fg_id <= 0:
                continue
            out.setdefault(fg_id, []).append(row)
        return out
    except Exception:
        return {}
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        
        
def expand_estado_cuenta_fg_rows(rows):
    items = rows or []
    fg_ids = []
    for row in items:
        if not isinstance(row, dict):
            continue
        try:
            fg_id = int(row.get("financiamiento_grupal_id") or 0)
        except Exception:
            fg_id = 0
        if fg_id > 0:
            fg_ids.append(fg_id)

    cuotas_map = get_fg_cuotas_map(fg_ids)
    if not cuotas_map:
        return items

    expanded = []
    seen_fg = set()
    for row in items:
        if not isinstance(row, dict):
            expanded.append(row)
            continue
        try:
            fg_id = int(row.get("financiamiento_grupal_id") or 0)
        except Exception:
            fg_id = 0
        if fg_id <= 0:
            expanded.append(row)
            continue
        if fg_id in seen_fg:
            continue
        seen_fg.add(fg_id)
        cuotas = cuotas_map.get(fg_id) or []
        if not cuotas:
            expanded.append(row)
            continue

        for cuota in cuotas:
            item = dict(row)
            fecha_pago = _format_fg_date_display(cuota.get("fecha_pago"))
            factura = str(cuota.get("factura") or "").strip()
            pagado = bool(fecha_pago or factura)
            item["idCuota"] = cuota.get("idCuota")
            item["poliza"] = f"FG-{fg_id}"
            item["cupon"] = str(cuota.get("cupon") or "").strip() or str(cuota.get("numero_cuota") or "")
            item["fecha_venc"] = _format_fg_date_display(cuota.get("fecha_vencimiento"))
            item["fecha_pago"] = fecha_pago
            item["factura"] = factura
            item["moneda"] = cuota.get("moneda") or item.get("moneda")
            item["monto_cta_cobrar"] = cuota.get("importe") or 0
            item["monto_cta_pagar"] = 0 if pagado else (cuota.get("importe") or 0)
            item["estado"] = "PAGADO" if pagado else "PENDIENTE"
            item["es_financiamiento_grupal"] = True
            item["financiamiento_grupal_id"] = fg_id
            item["poliza_fg_prefijo"] = "FG-"
            item["poliza_fg_numero"] = str(fg_id)
            expanded.append(item)

    return expanded

def _normalize_int_ids(values):
    ids = []
    seen = set()
    for raw_value in values or []:
        try:
            value = int(raw_value or 0)
        except Exception:
            value = 0
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        ids.append(value)
    return ids


def parse_financiamiento_grupal_id(poliza_value):
    poliza = str(poliza_value or "").strip()
    match = FG_POLIZA_RE.match(poliza)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def split_fg_poliza(poliza_value):
    fg_id = parse_financiamiento_grupal_id(poliza_value)
    if not fg_id:
        return "", ""
    return "FG-", str(fg_id)


def get_fg_metadata_maps(financiamiento_ids=None, poliza_ids=None):
    fg_ids = _normalize_int_ids(financiamiento_ids)
    policy_ids = _normalize_int_ids(poliza_ids)

    if not fg_ids and not policy_ids:
        return {}, {}

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        poliza_expr = """
            TRIM(
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
                    p.poliza
                )
            )
        """
        filters = []
        params = []
        if fg_ids:
            fg_placeholders = ",".join(["%s"] * len(fg_ids))
            filters.append(f"i.financiamiento_grupal_id IN ({fg_placeholders})")
            params.extend(fg_ids)
        if policy_ids:
            policy_placeholders = ",".join(["%s"] * len(policy_ids))
            filters.append(f"i.poliza_id IN ({policy_placeholders})")
            params.extend(policy_ids)
        cursor.execute(
            f"""
            SELECT
                i.financiamiento_grupal_id,
                i.poliza_id,
                {poliza_expr} AS poliza_relacionada
            FROM financiamiento_grupal_avisos i
            INNER JOIN polizas p
                ON p.idPoliza = i.poliza_id
            WHERE i.activo = 1
              AND p.activo = 1
              AND ({' OR '.join(filters)})
            ORDER BY i.financiamiento_grupal_id ASC, {poliza_expr} ASC
            """,
            tuple(params),
        )
        fg_to_polizas = {}
        poliza_to_fg = {}
        for row in cursor.fetchall() or []:
            fg_id = row.get("financiamiento_grupal_id")
            poliza_id = row.get("poliza_id")
            poliza_relacionada = (row.get("poliza_relacionada") or "").strip()
            try:
                fg_id = int(fg_id or 0)
            except Exception:
                fg_id = 0
            try:
                poliza_id = int(poliza_id or 0)
            except Exception:
                poliza_id = 0
            if fg_id <= 0:
                continue
            fg_to_polizas.setdefault(fg_id, [])
            if poliza_relacionada and poliza_relacionada not in fg_to_polizas[fg_id]:
                fg_to_polizas[fg_id].append(poliza_relacionada)
            if poliza_id > 0 and poliza_id not in poliza_to_fg:
                poliza_to_fg[poliza_id] = fg_id
        fg_to_polizas_text = {fg_id: ", ".join(values) for fg_id, values in fg_to_polizas.items()}
        return fg_to_polizas_text, poliza_to_fg
    except Exception:
        return {}, {}
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_fg_related_polizas_map(financiamiento_ids):
    fg_map, _ = get_fg_metadata_maps(financiamiento_ids=financiamiento_ids)
    return fg_map


def enrich_rows_with_fg_metadata(rows, poliza_key="poliza", poliza_id_keys=None, fg_id_keys=None):
    items = rows or []
    poliza_id_keys = poliza_id_keys or ("idPoliza", "poliza_id")
    fg_id_keys = fg_id_keys or ("financiamiento_grupal_id",)
    fg_ids = []
    poliza_ids = []
    for row in items:
        if not isinstance(row, dict):
            continue
        fg_id = None
        for fg_key in fg_id_keys:
            try:
                fg_id = int(row.get(fg_key) or 0)
            except Exception:
                fg_id = 0
            if fg_id > 0:
                break
            fg_id = None
        if not fg_id:
            fg_id = parse_financiamiento_grupal_id(row.get(poliza_key))
        if fg_id:
            fg_ids.append(fg_id)
        for poliza_id_key in poliza_id_keys:
            try:
                poliza_id = int(row.get(poliza_id_key) or 0)
            except Exception:
                poliza_id = 0
            if poliza_id > 0:
                poliza_ids.append(poliza_id)
                break

    fg_map, poliza_to_fg = get_fg_metadata_maps(financiamiento_ids=fg_ids, poliza_ids=poliza_ids)

    for row in items:
        if not isinstance(row, dict):
            continue
        poliza_raw = row.get(poliza_key)
        fg_id = None
        for fg_key in fg_id_keys:
            try:
                fg_id = int(row.get(fg_key) or 0)
            except Exception:
                fg_id = 0
            if fg_id > 0:
                break
            fg_id = None
        if not fg_id:
            fg_id = parse_financiamiento_grupal_id(poliza_raw)
        if not fg_id:
            for poliza_id_key in poliza_id_keys:
                try:
                    poliza_id = int(row.get(poliza_id_key) or 0)
                except Exception:
                    poliza_id = 0
                if poliza_id > 0 and poliza_id in poliza_to_fg:
                    fg_id = poliza_to_fg[poliza_id]
                    break
        prefijo_fg, numero_fg = split_fg_poliza(poliza_raw)
        if fg_id and not numero_fg:
            prefijo_fg, numero_fg = "FG-", str(fg_id)
        row["es_financiamiento_grupal"] = bool(fg_id)
        row["financiamiento_grupal_id"] = fg_id
        row["poliza_fg_prefijo"] = prefijo_fg
        row["poliza_fg_numero"] = numero_fg
        row["polizas_relacionadas"] = fg_map.get(fg_id, "") if fg_id else ""

    return items
