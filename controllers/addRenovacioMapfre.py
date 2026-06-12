import re
from typing import Dict, Optional

from controllers.addMapfreRenovacion import parse_mapfre_renovacion

AMOUNT_TOKEN_RE = (
    r"(\(?\s*(?:[-−–—]\s*)?"
    r"(?:[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))"
    r"\s*\)?)"
)


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_amount(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = str(value).strip()
    raw = raw.replace("−", "-").replace("–", "-").replace("—", "-")
    negative = False
    paren_match = re.match(r"^\((.*)\)$", raw)
    if paren_match:
        negative = True
        raw = (paren_match.group(1) or "").strip()
    if raw.startswith("-"):
        negative = True
        raw = raw[1:].strip()
    raw = re.sub(r"[^\d,.]", "", raw)
    if not raw:
        return None

    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw and "." not in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")

    try:
        amount = float(raw)
        if negative:
            amount = -abs(amount)
        return f"{amount:.2f}"
    except Exception:
        return f"-{raw}" if negative and raw else raw


def _find_amount(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return _normalize_amount(match.group(1))


def _find_first(patterns, text: str) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean(match.group(1))
    return None


def parse_renovacio_mapfre(text: str) -> Dict[str, str]:
    """
    Parser para suplemento/renovacion Mapfre con foco en:
    - Prima Comercial
    - Importe comision
    """
    base = parse_mapfre_renovacion(text) or {}
    item: Dict[str, str] = dict(base)

    text_norm = re.sub(r"\r\n", "\n", text)
    flat = re.sub(r"\s+", " ", text_norm)

    fecha_emision = _find_first(
        [
            r"FECHA\s+DE\s+EMISI[ÓO]N\s*[:.]?\s*(\d{2}/\d{2}/\d{4})",
            r"FECHA\s+DE\s+EMISI[ÓO]N\s*[:.]?\s*\n+\s*(\d{2}/\d{2}/\d{4})",
            r"AE\d{6,}\s+(\d{2}/\d{2}/\d{4})",
            r"C[ÓO]DIGO\s+SBS[\s\S]{0,80}?(\d{2}/\d{2}/\d{4})",
            r"(\d{2}/\d{2}/\d{4})\s+CAPITAL\s+SOCIAL",
        ],
        text_norm,
    )
    if fecha_emision:
        item["fecha_emision"] = fecha_emision
        item["emision"] = fecha_emision

    numero_poliza = _find_first(
        [
            r"P[ÓO]LIZA\s*(?:N[°º]|NRO\.?|N[UÚ]MERO)?\s*[:.]?\s*(\d{8,})",
            r"P[ÓO]LIZA\s*(?:N[°º]|NRO\.?|N[UÚ]MERO)?\s*[:.]?\s*\n+\s*(\d{8,})",
        ],
        text_norm,
    )
    if numero_poliza:
        item["numero_poliza"] = numero_poliza

    asegurado = _find_first(
        [
            r"DATOS\s+DEL\s+ASEGURADO[\s\S]{0,260}?(?:INC|EXC|TITULAR|C[ÓO]NYUGE|CONYUGE|HIJO|HIJA|PADRE|MADRE)\s+([A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+){2,})\s+\d{7,12}\s+\d{2}[-/]\d{2}[-/]\d{4}",
            r"DATOS\s+DEL\s+ASEGURADO[\s\S]{0,260}?Nombres\s+y\s+Apellidos[\s\S]{0,200}?([A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+){2,})\s+\d{7,12}\s+\d{2}[-/]\d{2}[-/]\d{4}",
            r"DATOS\s+DEL\s+ASEGURADO[\s\S]{0,260}?([A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+){2,})\s+\d{7,12}\s+\d{2}[-/]\d{2}[-/]\d{4}",
        ],
        text_norm,
    )
    if asegurado:
        asegurado = re.sub(r"\s+", " ", asegurado).strip()
        asegurado = re.sub(
            r"^(?:INC|EXC|TITULAR|C[ÓO]NYUGE|CONYUGE|HIJO|HIJA|PADRE|MADRE)\s+",
            "",
            asegurado,
            flags=re.IGNORECASE,
        ).strip()
        item["asegurado"] = asegurado
        item["colectivo_asegurado"] = asegurado

    moneda = _find_first(
        [
            r"\bMONEDA\s*[:.]?\s*(US\$|USD|S\/\.?|S\/|SOLES|D[ÓO]LARES)\b",
            r"\b(US\$|USD)\b",
            r"\b(S\/\.?|S\/)\b",
        ],
        flat,
    )
    if moneda:
        moneda_up = moneda.upper().replace(" ", "")
        if "US$" in moneda_up or "USD" in moneda_up or "DÓLAR" in moneda_up or "DOLAR" in moneda_up:
            item["moneda"] = "US$"
        else:
            item["moneda"] = "S/"

    prima_comercial = (
        _find_amount(
            r"Prima\s+Comercial(?!\s*\+)\s*:?\s*(?:S\/\.?|S\/|US\$|USD)?\s*" + AMOUNT_TOKEN_RE,
            flat,
        )
        or _find_amount(
            r"PRIMAS?\s+IMPORTE.*?Prima\s+Comercial(?!\s*\+)\s*(?:S\/\.?|S\/|US\$|USD)?\s*" + AMOUNT_TOKEN_RE,
            flat,
        )
    )
    if prima_comercial:
        item["prima_comercial"] = prima_comercial

    prima_comercial_igv = (
        _find_amount(
            r"Prima\s+Comercial\s*\+\s*I\.?\s*G\.?\s*V\.?\s*:?\s*(?:S\/\.?|S\/|US\$|USD)?\s*" + AMOUNT_TOKEN_RE,
            flat,
        )
        or item.get("prima_comercial_igv")
    )
    if prima_comercial_igv:
        item["prima_comercial_igv"] = prima_comercial_igv

    importe_comision = (
        _find_amount(
            r"Importe\s+comisi[oó]n\s*:?\s*(?:S\/\.?|S\/|US\$|USD)?\s*" + AMOUNT_TOKEN_RE,
            flat,
        )
        or _find_amount(
            r"IMPORTE\s+COMISI[ÓO]N\s*(?:S\/\.?|S\/|US\$|USD)?\s*" + AMOUNT_TOKEN_RE,
            text_norm,
        )
    )
    if importe_comision:
        item["comision_compania_importe"] = importe_comision
        item["importe_comision"] = importe_comision

    return {key: _clean(value) for key, value in item.items() if value}
