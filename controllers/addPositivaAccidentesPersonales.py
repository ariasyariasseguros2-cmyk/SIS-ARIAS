import re
from typing import Dict, Optional


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text or "", flags)
    return m.group(1).strip() if m else None


def parse_positiva_accidentes_personales(text: str) -> Dict[str, str]:
    from controllers.addPositivaGenerales import (
        _clean_company_name,
        extract_agenciamiento_positiva,
        extract_moneda_positiva,
        extract_numero_poliza_positiva,
        extract_primas_positiva,
        extract_proforma_numero_positiva,
        extract_razon_social,
        extract_razon_social_strict,
        extract_vigencias_positiva,
    )

    t = text or ""
    item: Dict[str, str] = {}

    poliza = (
        extract_numero_poliza_positiva(t)
        or _find(r"P[oó]liza\s*N(?:ro\.?|[°º]|o)?\s*[:：]?\s*([0-9]{6,20})\b", t)
        or _find(r"\bP[oó]liza\b[^\n\r]{0,140}?N[°ºo]\s*([0-9]{6,20})\b", t)
    )
    if poliza:
        item["numero_poliza"] = poliza

    proforma = extract_proforma_numero_positiva(t) or _find(r"Proforma\s*N(?:ro\.?|[°º]|o)?\s*[:：]?\s*([0-9]{6,20})\b", t)
    if proforma:
        item["recibo"] = proforma

    ramo = _find(r"Ramo\s*[:：]\s*([^\n\r]+)", t)
    if ramo:
        item["ramo"] = ramo
    elif re.search(r"\bACCIDENTES\s+PERSONALES\b", t, re.IGNORECASE):
        item["ramo"] = "ACCIDENTES PERSONALES"

    vig = extract_vigencias_positiva(t) or {}
    if vig.get("inicio_vigencia"):
        item["inicio_vigencia"] = vig["inicio_vigencia"]
    if vig.get("vencimiento"):
        item["vencimiento"] = vig["vencimiento"]

    pago_venc = _find(r"Fecha\s+de\s+Vencimiento\s*[:：]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", t)
    if pago_venc:
        item["ultimo_dia_pago"] = pago_venc

    moneda = extract_moneda_positiva(t)
    if moneda:
        item["moneda"] = moneda

    primas = extract_primas_positiva(t) or {}
    if primas.get("prima_comercial"):
        item["prima_comercial"] = primas["prima_comercial"]
    if primas.get("prima_comercial_igv"):
        item["prima_comercial_igv"] = primas["prima_comercial_igv"]

    ag = extract_agenciamiento_positiva(t) or {}
    if ag.get("monto"):
        item["comision_compania_importe"] = ag["monto"]
    if ag.get("registro"):
        item["comision_registro"] = ag["registro"]

    name = extract_razon_social_strict(t) or extract_razon_social(t)
    name = _clean_company_name(name) or name
    if name:
        item["colectivo_asegurado"] = name

    direccion = _find(r"Direcci[oó]n\s*:\s*([^\n\r]+)", t)
    if direccion:
        item["direccion"] = direccion

    return {k: v for k, v in item.items() if v}


def addPositivaAccidentesPersonales(filepath: str) -> dict:
    try:
        import fitz

        with fitz.open(filepath) as doc:
            txt = []
            for i in range(doc.page_count):
                try:
                    txt.append(doc.load_page(i).get_text() or "")
                except Exception:
                    pass
        return parse_positiva_accidentes_personales("\n".join(txt))
    except Exception:
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(filepath)
            out = []
            for page in reader.pages:
                try:
                    out.append(page.extract_text() or "")
                except Exception:
                    pass
            return parse_positiva_accidentes_personales("\n".join(out))
        except Exception:
            return {}
