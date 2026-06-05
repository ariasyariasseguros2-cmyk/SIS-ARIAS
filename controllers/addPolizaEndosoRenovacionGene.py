import re
from typing import Optional, Dict


def _money(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    txt = str(raw).strip().replace("−", "-").replace("–", "-").replace("—", "-")
    neg = False
    m_paren = re.match(r"^\((.*)\)$", txt)
    if m_paren:
        neg = True
        txt = (m_paren.group(1) or "").strip()
    if re.search(r"-\s*\d", txt):
        neg = True
    txt = re.sub(r"[^\d,.\-]", "", txt)
    if not txt:
        return None
    if "-" in txt:
        neg = True
    txt = txt.replace("-", "")
    if "," in txt and "." in txt:
        if txt.rfind(",") > txt.rfind("."):
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    else:
        if txt.count(",") == 1 and txt.count(".") == 0:
            txt = txt.replace(",", ".")
        else:
            txt = txt.replace(",", "")
    try:
        num = float(txt)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return None


def _find(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    val = (m.group(1) or "").strip()
    return val or None


def _find_money_near(label_pattern: str, text: str, window: int = 220) -> Optional[str]:
    m = re.search(label_pattern, text, re.IGNORECASE)
    if not m:
        return None
    seg = text[m.end(): m.end() + max(0, int(window))]
    m2 = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})", seg)
    return _money(m2.group(1)) if m2 else None


def _infer_moneda(text: str) -> Optional[str]:
    m = re.search(
        r"(?:Prima\s+Comercial|Prima\s+Comercial\s*\+\s*IGV|Moneda)[\s\S]{0,180}?(US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    tok = re.sub(r"\s+", "", (m.group(1) or "").upper())
    if tok.startswith("US$") or "USD" in tok or tok == "$" or "DOL" in tok:
        return "US$"
    return "S/"


def _extract_nombre_razon_social(text: str) -> Optional[str]:
    m = re.search(r"Nombre\s+o\s+Raz[oó]n\s+Social\s*:\s*([^\n\r]{3,180})", text, re.IGNORECASE)
    if m:
        v = re.sub(r"\s+", " ", (m.group(1) or "").strip())
        return v or None
    m2 = re.search(r"Datos\s+del\s+Contratante[\s\S]{0,400}?Nombre\s+o\s+Raz[oó]n\s+Social\s*:\s*([^\n\r]{3,180})", text, re.IGNORECASE)
    if m2:
        v = re.sub(r"\s+", " ", (m2.group(1) or "").strip())
        return v or None
    return None


def parse_positiva_endoso_renovacion_generales(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    t = (text or "").replace("\u00A0", " ")

    item["numero_poliza"] = (
        _find(r"P[oó]liza\s*N[°ºo]\s*[:：]?\s*([0-9]{6,20})\b", t)
        or _find(r"P[oó]liza\s*N[°ºo]\s*([0-9]{6,20})\b", t)
        or _find(r"\bP[oó]liza\b[\s\S]{0,80}?([0-9]{6,20})\b", t)
    )

    item["ramo"] = (
        _find(r"Ramo\s*:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ \-]{3,80})", t)
        or _find(r"\bP[oó]liza\s+de\s+Seguro\s+de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ \-]{3,80})", t)
    )

    item["recibo"] = (
        _find(r"Proforma\s+Nro\.?\s*([0-9]{6,20})\b", t)
        or _find(r"Proforma\s+N[°ºo]\s*[:：]?\s*([0-9]{6,20})\b", t)
        or _find(r"N[uú]mero\s+de\s+Proforma\s*[:：]?\s*([0-9]{6,20})\b", t)
    )

    item["fecha_vencimiento"] = _find(r"Fecha\s+de\s+Vencimiento\s*:\s*(\d{2}/\d{2}/\d{4})", t)

    vig_inicio = _find(r"Vigencia-?Inicio\s*:\s*(\d{2}/\d{2}/\d{4})", t) or _find(r"vigencia\s+inicia\s+el\s+(\d{2}/\d{2}/\d{4})", t)
    vig_fin = _find(r"T[ée]rmino\s*:\s*(\d{2}/\d{2}/\d{4})", t) or _find(r"vence\s+el\s+(\d{2}/\d{2}/\d{4})", t)
    item["inicio_vigencia"] = vig_inicio
    item["vencimiento"] = vig_fin

    item["colectivo_asegurado"] = _extract_nombre_razon_social(t)

    item["moneda"] = _infer_moneda(t)

    item["prima_comercial"] = _find_money_near(r"Prima\s+Comercial(?!\s*\+)", t, window=260)
    item["prima_comercial_igv"] = _find_money_near(r"Prima\s+Comercial\s*\+\s*IGV", t, window=260)

    m_com = re.search(
        r"Registro\s*[:：]?\s*[A-Z0-9]{3,10}[\s\S]{0,80}?"
        r"Monto\s*(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)?\s*"
        r"([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})\b",
        t,
        re.IGNORECASE,
    )
    if m_com:
        item["comision_compania_importe"] = _money(m_com.group(1))

    return {k: v for k, v in item.items() if v}

