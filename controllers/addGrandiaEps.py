import re
from typing import Dict, Optional


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    raw0 = str(s).strip()
    raw = raw0.replace("−", "-").replace("–", "-").replace("—", "-")
    m = re.search(r"(\(?\s*(?:[-−–—]\s*)?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d{2})?\s*\)?)", raw)
    if not m:
        return None
    tok = m.group(1).strip()
    neg = False
    mp = re.match(r"^\((.*)\)$", tok)
    if mp:
        neg = True
        tok = (mp.group(1) or "").strip()
    if re.match(r"^\s*[-−–—]\s*", tok):
        neg = True
    tok = re.sub(r"[^\d,\.]", "", tok)
    if not tok:
        return None
    if "." in tok and "," in tok:
        tok = tok.replace(",", "")
    elif "," in tok and "." not in tok:
        tok = tok.replace(",", ".")
    try:
        num = float(tok)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return f"-{tok}" if (neg and tok) else tok


def parse_grandia_eps(text: str) -> Dict[str, str]:
    contrato = _find(r"CONTRATO\s*(?:NO\.?|NRO\.?|N°|Nº)\s*[:.]?\s*([0-9]{5,}(?:-[0-9A-Z]+)?)", text)

    m_vig = re.search(
        r"VIGENCIA\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})\s*(?:al|hasta|-|–|—)\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    inicio_vigencia = m_vig.group(1) if m_vig else None
    vencimiento = m_vig.group(2) if m_vig else None

    colectivo = _find(r"Denominaci[oó]n\s+Social\s*:\s*([\s\S]*?)\bRUC\b", text)
    if colectivo:
        colectivo = re.sub(r"\s+", " ", _clean(colectivo)).strip("“”\"' :-")
        colectivo = colectivo.replace("'", "").replace('"', "")

    ruc = _find(r"\bRUC\s*(?:No\.?|Nro\.?|N°|Nº)?\s*[:.]?\s*(\d{11})\b", text)

    prima_neta = _money(_find(r"Prima\s+Neta\s*:\s*(.+)", text))
    igv_val = _money(_find(r"(?:Impuesto\s+)?IGV(?:\s*\(\s*18%\s*\))?\s*:\s*(.+)", text))
    prima_total = _money(_find(r"Prima\s+Total\s*:\s*(.+)", text))

    prima_comercial = prima_neta
    if not prima_comercial and prima_total and igv_val:
        try:
            prima_comercial = f"{float(prima_total) - float(igv_val):.2f}"
        except Exception:
            prima_comercial = None

    item = {
        "numero_poliza": contrato,
        "contrato_nro": contrato,
        "colectivo_asegurado": colectivo,
        "inicio_vigencia": inicio_vigencia,
        "vencimiento": "",
        "fecha_vencimiento": "",
        "ultimo_dia_pago": "",
        "ramo": "SCTR",
        "ramos_producto": "Salud",
        "moneda": "SOLES",
        "prima_comercial": prima_comercial,
        "prima_neta": prima_neta,
        "prima_total": prima_total,
        "prima_comercial_igv": prima_total,
        "numero_documento_extracted": ruc,
    }
    return {k: _clean(v) for k, v in item.items() if v}
