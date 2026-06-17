import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from controllers.addMapfre import parse_mapfre


MAPFRE_RUC = "20418896915"


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _canon(text: str) -> str:
    return re.sub(r"\s+", " ", text or "")


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    match = re.search(pattern, text or "", flags)
    return match.group(1).strip() if match else None


def _money(value: Optional[str]) -> Optional[str]:
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
    elif "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")

    try:
        amount = float(raw)
        if negative:
            amount = -abs(amount)
        return f"{amount:.2f}"
    except Exception:
        return f"-{raw}" if negative else raw


def _normalize_currency(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    token = str(value).strip().upper()
    if "US" in token or "USD" in token or "DOLAR" in token:
        return "US$"
    if "S/" in token or "SOL" in token or token == "PEN":
        return "S/"
    return token


def _map_forma_pago(value: Optional[str]) -> Optional[str]:
    raw = _clean(value)
    if not raw:
        return None

    token = raw.upper().replace(" ", "")
    aliases = {
        "1MEO": "MENSUAL",
        "MENSUAL": "MENSUAL",
        "ANUAL": "ANUAL",
        "SEMESTRAL": "SEMESTRAL",
        "TRIMESTRAL": "TRIMESTRAL",
        "BIMESTRAL": "BIMESTRAL",
        "QUINCENAL": "QUINCENAL",
        "UNICO": "UNICO",
        "UNICA": "UNICO",
    }
    return aliases.get(token, raw)


def _pick_client_document(text: str) -> Optional[str]:
    dni = _find(r"\bDNI\s*[:.]?\s*(\d{8})\b", text)
    if dni:
        return dni

    for ruc in re.findall(r"\b(10\d{9}|20\d{9})\b", text or ""):
        if ruc != MAPFRE_RUC:
            return ruc
    return None


def _extract_nombre(text: str) -> Optional[str]:
    block = _find(
        r"DATOS\s+DEL\s+CONTRATANTE[\s\S]{0,250}?NOMBRE\s+(?:DNI|RUC)\s+([A-ZÁÉÍÓÚÑ ]+?)\s+\d{8,11}\s+DIRECCI[ÓO]N\b",
        text,
    )
    if block:
        return re.sub(r"\s+", " ", block).strip()

    block = _find(
        r"DATOS\s+DEL\s+CONTRATANTE[\s\S]{0,500}?NOMBRE\s+(.+?)(?:\s+(?:DNI|RUC)\b|\s+DIRECCI[ÓO]N\b)",
        text,
    )
    if block:
        return re.sub(r"\s+", " ", block).strip()

    block = _find(
        r"Señor\(a\)\(rta\)\(es\)\s*:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ ]+?)\s+(?:DNI|RUC)\b",
        text,
    )
    if block:
        return re.sub(r"\s+", " ", block).strip()

    block = _find(
        r"ASEGURADO\s+([A-ZÁÉÍÓÚÑa-záéíóúñ ]+?)(?:\s+FECHA\s+REMESA|\s+DOC\.\s+IDENTIDAD\b|\s+VIGENCIA\b)",
        text,
    )
    if block:
        return re.sub(r"\s+", " ", block).strip()

    return None


def _extract_direccion(text: str) -> Optional[str]:
    direccion = _find(
        r"DIRECCI[ÓO]N\s+(.+?)(?:\s+FEC\.\s+NACIMIENTO\b|\s+EMAIL\b|\s+TEL[ÉE]FONO\b)",
        text,
    )
    if direccion:
        return re.sub(r"\s+", " ", direccion).strip()
    return None


def _extract_dates(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    date_pat = r"(\d{2}/\d{2}/\d{4})"

    vig_block = re.search(
        rf"VIGENCIA\s+DESDE\s+HASTA\s+{date_pat}(?:\s+\d{{2}}:\d{{2}}\s*Hrs\.)?\s+{date_pat}",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    inicio = (
        (vig_block.group(1) if vig_block else None)
        or
        _find(rf"VIGENCIA\s+DESDE\s+{date_pat}", text)
        or _find(rf"DESDE\s+{date_pat}\s+HASTA", text)
    )
    fin = (
        (vig_block.group(2) if vig_block else None)
        or
        _find(rf"VIGENCIA\s+HASTA\s+{date_pat}", text)
        or _find(rf"HASTA\s+{date_pat}(?:\s+\d{{2}}:\d{{2}})?", text)
    )

    emision = None
    cond_idx = (text or "").upper().find("CONDICIONES PARTICULARES")
    if cond_idx != -1:
        frag = (text or "")[cond_idx: cond_idx + 2200]
        emision = (
            _find(rf"\bEmisi[oó]n\b\s+\d+\s+{date_pat}", frag)
            or _find(rf"\bTIPO\s+DE\s+MOVIMIENTO[\s\S]{{0,500}}?\bEmisi[oó]n\b\s+\d+\s+{date_pat}", frag)
            or _find(rf"F\.?\s*EMISI[ÓO]N\s*[:.]?\s*{date_pat}", frag)
            or _find(rf"F\.?\s*EMISI[ÓO]N[^\d]{{0,40}}{date_pat}", frag)
        )

    emision = (
        emision
        or _find(rf"F\.?\s*EMISI[ÓO]N\s*[:.]?\s*{date_pat}", text)
        or _find(rf"F\.?\s*EMISI[ÓO]N[^\d]{{0,40}}{date_pat}", text)
        or _find(rf"FECHA\s+DE\s+EMISI[ÓO]N\s*[:.]?\s*{date_pat}", text)
    )

    fecha_pago = (
        _find(rf"FECHA\s+DE\s+PAGO\s*[:.]?\s*{date_pat}", text)
        or _find(rf"F\.?\s*DE\s+PAGO\s*[:.]?\s*{date_pat}", text)
        or _find(rf"FECHA\s+OBLIGACI[ÓO]N\s+(?:DE\s+)?PAGO\s*[:.]?\s*{date_pat}", text)
    )

    if inicio:
        item["inicio_vigencia"] = inicio
    if fin:
        item["vencimiento"] = fin
        item["fecha_vencimiento"] = fin
    if emision:
        item["fecha_emision"] = emision
    if fecha_pago:
        item["ultimo_dia_pago"] = fecha_pago
        item["fecha_vecimiento"] = fecha_pago

    if not item.get("fecha_vecimiento") and emision:
        try:
            due = datetime.strptime(emision, "%d/%m/%Y") + timedelta(days=15)
            item["fecha_vecimiento"] = due.strftime("%d/%m/%Y")
        except Exception:
            pass

    return item


def _extract_numero_poliza(text: str) -> Optional[str]:
    return (
        _find(r"\bP[ÓO]LIZA\s+COLECTIVO(?:\s+NRO\.\s+RIESGO)?\s+(\d{8,15})\b", text)
        or _find(r"\bPOLIZA\s+SUPLEMENTO(?:\s+CORREDOR\s+IMPORTE)?\s+(\d{8,15})\s+\d+\b", text)
        or
        _find(r"\bP[ÓO]LIZA\s+(\d{8,15})\b", text)
        or _find(r"\bP[ÓO]LIZA\s*[:.]?\s*(\d{8,15})\b", text)
        or _find(r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\s*[:.]?\s*(\d{8,15})\b", text)
    )


def _extract_recibo(text: str, poliza: Optional[str]) -> Optional[str]:
    candidates = [
        _find(r"\bRECIBO\s+(\d{6,12})\b", text),
        _find(r"\bRECIBO\s*[:.]?\s*(\d{6,12})\b", text),
        _find(r"\bPRUEBA\s+DE\s+LA\s+CANCELACION\s+DE[\s\S]{0,120}?\b(\d{6,12})\b", text),
    ]

    for candidate in candidates:
        if candidate and candidate != poliza:
            return candidate

    return None


def _extract_primas(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    flat = _canon(text)

    prima_comercial = (
        _money(_find(r"Prima\s+Comercial(?!\s*\+)\s*(\(?\s*[-]?\s*[\d,]+\.\d{2}\s*\)?)", text))
        or _money(_find(r"Prima\s+Comercial(?!\s*\+)\s*(\(?\s*[-]?\s*[\d,]+\.\d{2}\s*\)?)", flat))
    )
    prima_con_igv = (
        _money(_find(r"Prima\s+Comercial\s*\+\s*I\.?\s*G\.?\s*V\.?\s*(\(?\s*[-]?\s*[\d,]+\.\d{2}\s*\)?)", text))
        or _money(_find(r"Prima\s+Comercial\s*\+\s*I\.?\s*G\.?\s*V\.?\s*(\(?\s*[-]?\s*[\d,]+\.\d{2}\s*\)?)", flat))
        or _money(_find(r"TOTAL\s+S\/\s*(\(?\s*[-]?\s*[\d,]+\.\d{2}\s*\)?)", flat))
    )

    if prima_comercial:
        item["prima_comercial"] = prima_comercial
    if prima_con_igv:
        item["prima_comercial_igv"] = prima_con_igv
        item["prima_total"] = prima_con_igv

    return item


def _extract_comision_compania(text: str) -> Optional[str]:
    flat = _canon(text)
    patterns = [
        r"IMPORTE\s+DE\s+LA\s+COMISI[ÓO]N\s*([0-9\.,]+)",
        r"IMPORTE\s+DE\s+LA\s+COMISI[ÓO]\s*N\s*([0-9\.,]+)",
        r"IMPORTE\s+DE\s+LA\s+COMISION\s*([0-9\.,]+)",
        r"IMPORTE\s+DE\s+LA\s+COMISIO\s*N\s*([0-9\.,]+)",
    ]
    for pat in patterns:
        val = _money(_find(pat, flat))
        if val:
            return val
    return None


def parse_mapfre_poliza_sap(text: str) -> Dict[str, str]:
    """
    Parser para la poliza Mapfre "Seguro contra Accidentes Personales".
    Usa el parser general como base y refuerza los campos que cambian en este formato.
    """
    text_norm = re.sub(r"\r\n?", "\n", text or "")
    flat = _canon(text_norm)

    item: Dict[str, str] = dict(parse_mapfre(text_norm) or {})

    numero_poliza = _extract_numero_poliza(text_norm) or item.get("numero_poliza")
    item["numero_poliza"] = numero_poliza

    recibo = _extract_recibo(text_norm, numero_poliza) or item.get("recibo")
    if recibo and recibo != numero_poliza:
        item["recibo"] = recibo

    nombre = _extract_nombre(text_norm)
    if nombre:
        item["colectivo_asegurado"] = nombre
        item["asegurado"] = nombre

    direccion = _extract_direccion(text_norm)
    if direccion:
        item["direccion"] = direccion

    doc_cliente = _pick_client_document(text_norm)
    if doc_cliente:
        item["numero_documento_extracted"] = doc_cliente

    fechas = _extract_dates(text_norm)
    item.update({key: value for key, value in fechas.items() if value})

    forma_pago = (
        _find(r"FORMA\s+DE\s+PAGO\s+([A-Z0-9/]+)", text_norm)
        or _find(r"FORMA\s+DE\s+PAGO\s*[:.]?\s*([A-Z0-9/ ]+)", flat)
        or _find(r"\b(1MEO|MENSUAL|ANUAL|SEMESTRAL|TRIMESTRAL|BIMESTRAL|QUINCENAL|UNICO)\b", text_norm)
        or item.get("forma_pago")
    )
    forma_pago = _map_forma_pago(forma_pago)
    if forma_pago:
        item["forma_pago"] = forma_pago

    moneda = (
        _find(r"Moneda\s*:\s*(S\/\.?|S\/|SOLES|US\$|USD|D[ÓO]LARES|PEN)", text_norm)
        or _find(r"MONEDA\s*[:.]?\s*(S\/\.?|S\/|SOLES|US\$|USD|D[ÓO]LARES|PEN)", text_norm)
        or _find(r"MONEDA\s+([A-Z/$\.]+)", text_norm)
        or _find(r"MONEDA\s*[:.]?\s*([A-Z/$\.]+)", flat)
        or item.get("moneda")
    )
    moneda = _normalize_currency(moneda)
    if moneda:
        item["moneda"] = moneda

    primas = _extract_primas(text_norm)
    item.update(primas)

    comision = _extract_comision_compania(text_norm)
    if comision:
        item["comision_compania_importe"] = comision
        item["importe_comision"] = comision

    if re.search(r"ACCIDENTES\s+PERSONALES", flat, re.IGNORECASE):
        item["ramo"] = "ACCIDENTES PERSONALES"

    if not item.get("fecha_vencimiento") and item.get("vencimiento"):
        item["fecha_vencimiento"] = item["vencimiento"]
    if not item.get("fecha_vecimiento"):
        item["fecha_vecimiento"] = item.get("ultimo_dia_pago") or item.get("fecha_vencimiento")

    return {key: _clean(value) for key, value in item.items() if value}


def addPolizaMapfreSAP(filepath: str) -> dict:
    try:
        import fitz

        with fitz.open(filepath) as doc:
            chunks = []
            for page_index in range(doc.page_count):
                try:
                    chunks.append(doc.load_page(page_index).get_text() or "")
                except Exception:
                    pass
        return parse_mapfre_poliza_sap("\n".join(chunks))
    except Exception:
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(filepath)
            chunks = []
            for page in reader.pages:
                try:
                    chunks.append(page.extract_text() or "")
                except Exception:
                    pass
            return parse_mapfre_poliza_sap("\n".join(chunks))
        except Exception:
            return {}
