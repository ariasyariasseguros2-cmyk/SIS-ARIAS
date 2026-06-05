import re
from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import _normalize_date_token, _normalize_importe_text


def extract_cronograma_cuotas_seguro_vehicular_rimac(
    text: str | None, moneda_default: str | None = None
) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    mon = (moneda_default or "").strip()
    if not mon:
        m_mon = re.search(r"\bMoneda\b\s*[:：]?\s*([^\r\n]+)", normalized, re.IGNORECASE)
        if m_mon:
            tok = (m_mon.group(1) or "").upper()
            if "DOLAR" in tok or "DÓLAR" in tok or "USD" in tok or "US$" in tok:
                mon = "US$"
            elif "SOL" in tok or "S/" in tok:
                mon = "S/."

    flat_all = re.sub(r"\s+", " ", normalized).strip()

    if not mon:
        if re.search(r"\bUS\s*\$", flat_all, re.IGNORECASE):
            mon = "US$"
        elif re.search(r"\bS\s*/\s*\.?\b|\bSOLES\b", flat_all, re.IGNORECASE):
            mon = "S/."

    anchor_re = re.compile(
        r"(Documentos\s+Generados|Documentos\s+Fecha\s+de|Generados\s+Vencimiento|N[°º]\s+Tipo\b)",
        re.IGNORECASE,
    )
    m_anchor = anchor_re.search(flat_all)
    section = flat_all[m_anchor.start() : m_anchor.start() + 40000] if m_anchor else flat_all

    end_re = re.compile(
        r"\bTotal\s+(?:US\s*\$|US\$|S/\.?)\b|\*\s*Prima\s+Neta\b|\b3\.\-\s*El\s+presente\b|\bEn\s+señal\s+de\s+conformidad\b",
        re.IGNORECASE,
    )
    m_end = end_re.search(section)
    if m_end:
        section = section[: m_end.start()]

    section = re.sub(r"(\d)(?=[A-Za-zÁÉÍÓÚÑ])", r"\1 ", section)

    cuotas: List[Dict[str, object]] = []
    seen = set()

    patterns = [
        re.compile(
            r"\b(?P<num>\d{1,3})[\s|¦│]+"
            r"(?:(?P<tipo>[A-Z]{1,6})[\s|¦│]+)?"
            r"(?P<doc>\d{6,25})[\s|¦│]+"
            r"(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)[\s|¦│]+"
            r"(?P<importe>\d[\d\.,]*)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<num>\d{1,3})[\s|¦│]+"
            r"(?:(?P<tipo>[A-Z]{1,6})[\s|¦│]+)?"
            r"(?P<doc>\d{6,25})[\s|¦│]+"
            r"(?P<importe>\d[\d\.,]*)[\s|¦│]+"
            r"(?P<fecha>\d{1,2}[/-]\d{1,2}[/-]\d{4})(?!\d)",
            re.IGNORECASE,
        ),
    ]

    for pat in patterns:
        for m in pat.finditer(section):
            doc = (m.group("doc") or "").strip()
            if not doc or doc in seen:
                continue
            seen.add(doc)
            numero_cuota = None
            try:
                numero_cuota = int((m.group("num") or "").strip())
            except Exception:
                numero_cuota = None
            cuotas.append(
                {
                    "numero_cuota": numero_cuota,
                    "cupon": doc,
                    "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
                    "importe": _normalize_importe_text(m.group("importe")),
                    "moneda": mon or (moneda_default or ""),
                    "factura": "",
                    "fecha_pago": "",
                }
            )

    cuotas.sort(key=lambda x: (x.get("numero_cuota") is None, x.get("numero_cuota") or 0))
    return cuotas
