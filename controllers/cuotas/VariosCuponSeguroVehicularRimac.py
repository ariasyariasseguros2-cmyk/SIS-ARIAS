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
    has_explicit_num = False

    importe_re = r"\(?\s*(?:[-−–—]\s*)?\d[\d\.,]*\s*\)?"
    date_re = r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"

    patterns = [
        re.compile(
            r"\b(?P<num>(?:[1-9]|[1-5]\d|60))[\s|¦│]+"
            r"(?:(?P<tipo>[A-Z]{1,6})[\s|¦│]+)?"
            r"(?P<doc>\d{6,25})[\s|¦│]+"
            rf"(?P<fecha>{date_re})(?!\d)[\s|¦│]+"
            rf"(?P<importe>{importe_re})",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<num>(?:[1-9]|[1-5]\d|60))[\s|¦│]+"
            r"(?:(?P<tipo>[A-Z]{1,6})[\s|¦│]+)?"
            r"(?P<doc>\d{6,25})[\s|¦│]+"
            rf"(?P<importe>{importe_re})[\s|¦│]+"
            rf"(?P<fecha>{date_re})(?!\d)",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?P<doc>\d{{6,25}})[\s|¦│]+"
            rf"(?P<fecha>{date_re})(?!\d)[\s|¦│]+"
            rf"(?P<importe>{importe_re})",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?P<doc>\d{{6,25}})[\s|¦│]+"
            rf"(?P<importe>{importe_re})[\s|¦│]+"
            rf"(?P<fecha>{date_re})(?!\d)",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?P<doc_a>\d{{3,4}})[\s|¦│]+(?P<doc_b>\d{{4,22}})[\s|¦│]+"
            rf"(?P<fecha>{date_re})(?!\d)[\s|¦│]+"
            rf"(?P<importe>{importe_re})",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?P<doc_a>\d{{3,4}})[\s|¦│]+(?P<doc_b>\d{{4,22}})[\s|¦│]+"
            rf"(?P<importe>{importe_re})[\s|¦│]+"
            rf"(?P<fecha>{date_re})(?!\d)",
            re.IGNORECASE,
        ),
    ]

    for pat in patterns:
        for m in pat.finditer(section):
            doc = (m.groupdict().get("doc") or "").strip()
            if not doc:
                da = (m.groupdict().get("doc_a") or "").strip()
                db = (m.groupdict().get("doc_b") or "").strip()
                if da and db:
                    doc = f"{da}{db}"
            if not doc or doc in seen:
                continue
            seen.add(doc)
            numero_cuota = None
            num_raw = (m.groupdict().get("num") or "").strip()
            if num_raw:
                try:
                    numero_cuota = int(num_raw)
                    has_explicit_num = True
                except Exception:
                    numero_cuota = None
            if numero_cuota is None:
                numero_cuota = len(cuotas) + 1
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

    if cuotas:
        filtered: List[Dict[str, object]] = []
        for c in cuotas:
            doc = str(c.get("cupon") or "").strip()
            if not doc:
                continue
            if len(doc) >= 9:
                filtered.append(c)
                continue
            same_row_has_longer = False
            for o in cuotas:
                odoc = str(o.get("cupon") or "").strip()
                if len(odoc) <= len(doc):
                    continue
                if not odoc.endswith(doc):
                    continue
                if (o.get("fecha_vencimiento") or "") != (c.get("fecha_vencimiento") or ""):
                    continue
                if (o.get("importe") or "") != (c.get("importe") or ""):
                    continue
                same_row_has_longer = True
                break
            if not same_row_has_longer:
                filtered.append(c)
        cuotas = filtered

    cuotas.sort(key=lambda x: (x.get("numero_cuota") is None, x.get("numero_cuota") or 0))
    if cuotas and not has_explicit_num:
        for i, c in enumerate(cuotas, start=1):
            c["numero_cuota"] = i
    return cuotas
