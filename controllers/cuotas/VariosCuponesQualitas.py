import re
from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import _normalize_date_token, _normalize_importe_text


def extract_cronograma_cuotas_qualitas(text: str | None, moneda_default: str | None = None) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    section_match = re.search(
        r"Cronograma\s+de\s+Pago([\s\S]{0,5000})",
        normalized,
        re.IGNORECASE,
    )
    section = section_match.group(1) if section_match else normalized

    end_match = re.search(
        r"(OFICINA\s+DE\s+ATENCI[ÓO]N|CORREDOR:|MATRICULA\s+SBS:|IMPORTANTE|CONDICIONES)",
        section,
        re.IGNORECASE,
    )
    if end_match:
        section = section[: end_match.start()]

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]
    if not lines:
        return []

    cuotas: List[Dict[str, object]] = []
    seen = set()

    row_pattern = re.compile(
        r"(?P<num>\d{1,2})\s*/\s*(?P<total>\d{1,2})\s+"
        r"(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+"
        r"(?P<cupon>\d{6,20})\s+"
        r"(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )

    header_re = re.compile(
        r"Orden|Fecha\s+de\s+Vencimiento|N[úu]mero\s+de\s+Recibo|Importe\s+a\s+Pagar|AUTO\s+P[ÓO]LIZA",
        re.IGNORECASE,
    )
    data_lines = [ln for ln in lines if not header_re.search(ln)]

    for ln in data_lines:
        m = row_pattern.search(ln)
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
        return cuotas

    flat = " ".join(data_lines)
    for m in row_pattern.finditer(flat):
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

    return cuotas
