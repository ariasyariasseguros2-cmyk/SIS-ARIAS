import re
from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import (
    _normalize_date_token,
    _normalize_importe_text,
)


def extract_cronograma_cuotas_mapfre(
    text: str | None, moneda_default: str | None = None
) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    mon = (moneda_default or "").strip()
    if not mon:
        m_mon = re.search(
            r"Moneda\s*[:：]?\s*(US\s*\$|US\$|USD|DOLARES|DÓLARES|S\s*/\s*\.?|S/|SOLES)",
            normalized,
            re.IGNORECASE,
        )
        if m_mon:
            tok = (m_mon.group(1) or "").upper().replace(" ", "")
            if "US" in tok or "DOLAR" in tok or "USD" in tok:
                mon = "US$"
            elif "S/" in tok or "SOL" in tok:
                mon = "S/."

    header_match = re.search(
        r"(?:CRONOGRAMA\s+DE\s+PAGO|NRO\.?\s*RECIBO)\s*[:：]?\s*([\s\S]{0,5000})",
        normalized,
        re.IGNORECASE,
    )
    section = header_match.group(1) if header_match else normalized
    end_match = re.search(r"(?:TCEA|TEA|TASA\s+DE\s+COSTO\s+EFECTIVO)\b", section, re.IGNORECASE)
    if end_match:
        section = section[: end_match.start()]

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]

    cuotas: List[Dict[str, object]] = []
    seen = set()

    row_re = re.compile(
        r"^(?P<cupon>\d{6,20})\s+"
        r"(?P<moneda>[A-ZÁÉÍÓÚÑ/$.]{2,20})\s+"
        r"(?P<importe>\d[\d\.,]*)\s+"
        r"(?P<fecha>\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(?P<estado>[A-ZÁÉÍÓÚÑ]{3,20})\b",
        re.IGNORECASE,
    )

    for ln in lines:
        if re.search(r"NRO\.?\s*RECIBO|MONEDA|IMPORTE|FECHA|SITUACI", ln, re.IGNORECASE):
            continue
        m = row_re.search(ln)
        if not m:
            continue
        cupon = (m.group("cupon") or "").strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)
        moneda_row = (m.group("moneda") or "").strip().upper()
        moneda_out = mon
        if "DOLAR" in moneda_row or "DÓLAR" in moneda_row or "USD" in moneda_row or "US$" in moneda_row:
            moneda_out = "US$"
        elif moneda_row.startswith("S") or "SOL" in moneda_row:
            moneda_out = "S/."

        cuotas.append(
            {
                "numero_cuota": len(cuotas) + 1,
                "cupon": cupon,
                "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                "importe": _normalize_importe_text(m.group("importe")),
                "moneda": moneda_out or (moneda_default or ""),
                "factura": "",
                "fecha_pago": "",
            }
        )

    if cuotas:
        return cuotas

    tokens = [t for t in re.split(r"\s+", section) if t]
    i = 0
    while i < len(tokens):
        if not re.fullmatch(r"\d{6,20}", tokens[i]):
            i += 1
            continue
        cupon = tokens[i]
        i += 1
        if i >= len(tokens):
            break

        moneda_tok = tokens[i]
        i += 1
        if i >= len(tokens):
            break

        importe_tok = tokens[i]
        i += 1
        if i >= len(tokens):
            break

        fecha_tok = tokens[i]
        i += 1
        if i >= len(tokens):
            break

        estado_tok = tokens[i]
        i += 1

        if not re.search(r"\d", importe_tok):
            continue
        if not re.search(r"\d{1,2}/\d{1,2}/\d{4}", fecha_tok):
            continue

        if cupon in seen:
            continue
        seen.add(cupon)

        moneda_row = (moneda_tok or "").strip().upper()
        moneda_out = mon
        if "DOLAR" in moneda_row or "DÓLAR" in moneda_row or "USD" in moneda_row or "US$" in moneda_row:
            moneda_out = "US$"
        elif moneda_row.startswith("S") or "SOL" in moneda_row:
            moneda_out = "S/."

        cuotas.append(
            {
                "numero_cuota": len(cuotas) + 1,
                "cupon": cupon,
                "fecha_vencimiento": _normalize_date_token(fecha_tok),
                "importe": _normalize_importe_text(importe_tok),
                "moneda": moneda_out or (moneda_default or ""),
                "factura": "",
                "fecha_pago": "",
            }
        )

    return cuotas

