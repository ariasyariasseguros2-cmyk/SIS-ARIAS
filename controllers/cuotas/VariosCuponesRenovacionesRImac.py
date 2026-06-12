import re
from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import (
    _normalize_date_token,
    _normalize_importe_text,
)


def _normalize_moneda(value: str | None, moneda_default: str | None = None) -> str:
    token = (value or moneda_default or "").strip().upper()
    token = token.replace(" ", "")
    if "US$" in token or "USD" in token or "DOLAR" in token or "DÓLAR" in token:
        return "US$"
    if "S/" in token or "SOL" in token:
        return "S/."
    return (moneda_default or "").strip()


def extract_cronograma_cuotas_renovaciones_rimac(
    text: str | None, moneda_default: str | None = None
) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    anchor_re = re.compile(r"CRONOGRAMA\s+DE\s+PAGO", re.IGNORECASE)
    m_anchor = anchor_re.search(normalized)
    if not m_anchor:
        return []

    section = normalized[m_anchor.start() : m_anchor.start() + 8000]
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]
    if not lines:
        return []

    data_lines: List[str] = []
    header_found = False
    for ln in lines:
        up = ln.upper()
        if "CRONOGRAMA DE PAGO" in up:
            continue
        if "NRO. RECIBO" in up and "FECHA DE OBLIGACIÓN DE PAGO" in up:
            header_found = True
            continue
        if not header_found:
            continue
        if "CONDICIONES GENERALES" in up or "OBSERVACIONES" in up:
            break
        data_lines.append(ln)

    if not data_lines:
        data_lines = lines

    cuotas: List[Dict[str, object]] = []
    seen = set()

    row_line_re = re.compile(
        r"^\s*(?P<recibo>\d{6,20})\s+"
        r"(?P<moneda>SOLES|S\/\.?|S\/|US\$|USD|D[ÓO]LARES)\s+"
        r"(?P<importe>\(?\s*(?:[-−–—]\s*)?\d[\d\.,]*\s*\)?)\s+"
        r"(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)\s+"
        r"(?P<situacion>[A-ZÁÉÍÓÚÑ ]+)$",
        re.IGNORECASE,
    )

    for ln in data_lines:
        m = row_line_re.search(ln)
        if not m:
            continue

        recibo = (m.group("recibo") or "").strip()
        if not recibo or recibo in seen:
            continue
        seen.add(recibo)

        cuotas.append(
            {
                "numero_cuota": len(cuotas) + 1,
                "cupon": recibo,
                "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                "importe": _normalize_importe_text(m.group("importe")),
                "moneda": _normalize_moneda(m.group("moneda"), moneda_default),
                "factura": "",
                "fecha_pago": "",
                "situacion_recibo": re.sub(r"\s+", " ", m.group("situacion") or "").strip().upper(),
            }
        )

    if cuotas:
        return cuotas

    flat = re.sub(r"\s+", " ", section).strip()
    row_flat_re = re.compile(
        r"(?P<recibo>\d{6,20})\s+"
        r"(?P<moneda>SOLES|S\/\.?|S\/|US\$|USD|D[ÓO]LARES)\s+"
        r"(?P<importe>\(?\s*(?:[-−–—]\s*)?\d[\d\.,]*\s*\)?)\s+"
        r"(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)\s+"
        r"(?P<situacion>PENDIENTE|PAGADO|VENCIDO|ANULADO|CANCELADO)",
        re.IGNORECASE,
    )

    for m in row_flat_re.finditer(flat):
        recibo = (m.group("recibo") or "").strip()
        if not recibo or recibo in seen:
            continue
        seen.add(recibo)
        cuotas.append(
            {
                "numero_cuota": len(cuotas) + 1,
                "cupon": recibo,
                "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                "importe": _normalize_importe_text(m.group("importe")),
                "moneda": _normalize_moneda(m.group("moneda"), moneda_default),
                "factura": "",
                "fecha_pago": "",
                "situacion_recibo": re.sub(r"\s+", " ", m.group("situacion") or "").strip().upper(),
            }
        )

    return cuotas
