import re
from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import _normalize_date_token, _normalize_importe_text


def extract_cronograma_cuotas_renovacion_rimac(text: str | None, moneda_default: str | None = None) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    anchor_re = re.compile(
        r"(Forma\s+de\s+Pago\b|Detalle\s+de\s+Vencimientos|Documentos\s+Generados|PAGO\s+FRACCIONADO)",
        re.IGNORECASE,
    )
    m_anchor = anchor_re.search(normalized)
    section = normalized[m_anchor.start() : m_anchor.start() + 12000] if m_anchor else normalized

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]
    if not lines:
        return []

    data_lines = lines
    flat = " ".join(data_lines) if data_lines else " ".join(lines)
    flat = re.sub(r"\s+", " ", flat).strip()

    cuotas: List[Dict[str, object]] = []
    seen = set()

    row_line_re = re.compile(
        r"^\s*(?P<num>\d{1,3})\s+(?P<tipo>[A-Z]{1,6})\s+(?P<cupon>\d{6,20})\s+(?P<importe>\d[\d\.,]*)\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)",
        re.IGNORECASE,
    )
    for ln in data_lines:
        m = row_line_re.search(ln)
        if not m:
            continue
        cupon = (m.group("cupon") or "").strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)
        numero_cuota = None
        try:
            numero_cuota = int((m.group("num") or "").strip())
        except Exception:
            numero_cuota = None
        cuotas.append(
            {
                "numero_cuota": numero_cuota,
                "cupon": cupon,
                "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                "importe": _normalize_importe_text(m.group("importe")),
                "moneda": moneda_default or "",
                "factura": "",
                "fecha_pago": "",
            }
        )

    if cuotas:
        cuotas.sort(key=lambda x: (x.get("numero_cuota") is None, x.get("numero_cuota") or 0))
        return cuotas

    patterns = [
        re.compile(
            r"\b(?P<num>\d{1,3})\s+(?P<tipo>[A-Z]{1,6})\s+(?P<cupon>\d{6,20})\s+(?P<importe>\d[\d\.,]*)\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<num>\d{1,3})\s+(?P<cupon>\d{6,20})\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)\s+(?P<importe>\d[\d\.,]*)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<num>\d{1,3})\s+(?:[A-Z]{1,6}\s+)?(?P<cupon>\d{6,20})\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)\s+(?P<importe>\d[\d\.,]*)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<num>\d{1,3})\s+(?:[A-Z]{1,6}\s+)?(?P<cupon>\d{6,20})\s+(?P<importe>\d[\d\.,]*)\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)",
            re.IGNORECASE,
        ),
    ]

    for pat in patterns:
        for m in pat.finditer(flat):
            cupon = (m.group("cupon") or "").strip()
            if not cupon or cupon in seen:
                continue
            seen.add(cupon)

            numero_cuota = None
            try:
                numero_cuota = int((m.group("num") or "").strip())
            except Exception:
                numero_cuota = None

            cuotas.append(
                {
                    "numero_cuota": numero_cuota,
                    "cupon": cupon,
                    "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                    "importe": _normalize_importe_text(m.group("importe")),
                    "moneda": moneda_default or "",
                    "factura": "",
                    "fecha_pago": "",
                }
            )

        if cuotas:
            break

    if cuotas:
        cuotas.sort(key=lambda x: (x.get("numero_cuota") is None, x.get("numero_cuota") or 0))
        return cuotas

    num_date_amount = re.compile(
        r"\b(?P<num>\d{1,3})\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)\s+(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )
    numbers = [m.group("cupon") for m in re.finditer(r"\b\d{6,20}\b", flat)]
    nda = list(num_date_amount.finditer(flat))
    if numbers and nda:
        used = set()
        for idx, m in enumerate(nda):
            if idx >= len(numbers):
                break
            cupon = numbers[idx]
            if cupon in seen or cupon in used:
                continue
            used.add(cupon)
            numero_cuota = None
            try:
                numero_cuota = int((m.group("num") or "").strip())
            except Exception:
                numero_cuota = None
            cuotas.append(
                {
                    "numero_cuota": numero_cuota,
                    "cupon": cupon,
                    "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                    "importe": _normalize_importe_text(m.group("importe")),
                    "moneda": moneda_default or "",
                    "factura": "",
                    "fecha_pago": "",
                }
            )
        if cuotas:
            cuotas.sort(key=lambda x: (x.get("numero_cuota") is None, x.get("numero_cuota") or 0))
            return cuotas

    fallback_pat = re.compile(
        r"\b(?P<cupon>\d{6,20})\s+(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)\s+(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )
    for m in fallback_pat.finditer(flat):
        cupon = (m.group("cupon") or "").strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)
        cuotas.append(
            {
                "numero_cuota": len(cuotas) + 1,
                "cupon": cupon,
                "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                "importe": _normalize_importe_text(m.group("importe")),
                "moneda": moneda_default or "",
                "factura": "",
                "fecha_pago": "",
            }
        )

    return cuotas
