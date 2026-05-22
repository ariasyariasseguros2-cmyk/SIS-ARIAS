import re
from datetime import datetime, timedelta
from typing import Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money_value(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2})?)", s)
    if not m:
        return None
    raw = m.group(1)
    if raw.count(",") == 1 and raw.count(".") == 0:
        raw = raw.replace(",", ".")
    raw = raw.replace(",", "")
    try:
        return f"{float(raw):.2f}"
    except Exception:
        return m.group(1)

def _normalize_moneda(moneda_raw: Optional[str]) -> Optional[str]:
    if not moneda_raw:
        return None
    up = re.sub(r"\s+", "", moneda_raw.replace("\u00A0", " ").upper())
    if not up:
        return None
    if "DOL" in up or "USD" in up or up.startswith("US$") or up == "$":
        return "US$"
    if "SOL" in up or up.startswith("S/") or up.startswith("S/.") or up == "PEN":
        return "S/"
    return moneda_raw.strip()

def _add_days_ddmmyyyy(date_str: Optional[str], days: int) -> Optional[str]:
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
    except Exception:
        return None

def parse_protecta_pension_emision(text: str) -> Dict[str, str]:
    """
    Parsea el texto extraído del PDF de Protecta Pensión Emisión.
    """
    
    # Prima Comercial
    # Ejemplo: PRIMA COMERCIAL: \n S/. 122.04
    prima_comercial = _money_value(_find(r"PRIMA COMERCIAL:\s*(?:S/\.)?\s*([\d\.,]+)", text))
    
    # Prima Comercial Total
    # Ejemplo: PRIMA COMERCIAL TOTAL: \n S/. 144.01
    prima_total = _money_value(_find(r"PRIMA COMERCIAL TOTAL:\s*(?:S/\.)?\s*([\d\.,]+)", text))
    
    # Póliza No.
    # Ejemplo: Póliza No.:   4000009113
    poliza = _find(r"Póliza No\.:\s*(\d+)", text)
    
    # Moneda del Contrato
    # Ejemplo: Moneda del Contrato:  Soles
    moneda = _normalize_moneda(_find(r"Moneda del Contrato:\s*([^\r\n]+)", text))
    
    # Fecha de Emisión
    # Ejemplo: Fecha de Emisión:    30/08/2025
    # También puede aparecer como "Fecha de Renovación" en renovaciones
    fecha_emision = _find(r"Fecha de Emisi[oó]n:\s*(\d{2}/\d{2}/\d{4})", text)
    if not fecha_emision:
         fecha_emision = _find(r"Fecha de Renovaci[oó]n:\s*(\d{2}/\d{2}/\d{4})", text)
    if not fecha_emision:
         # Fallback: buscar fecha sola si está cerca de "Lugar y Fecha"
         fecha_emision = _find(r"Lugar y Fecha.*?\s(\d{2}/\d{2}/\d{4})", text)
    
    # Vigencia de la Cobertura
    # Ejemplo: Vigencia de la Cobertura:  Desde: 01/09/2025 \n Hasta: 30/09/2025
    inicio_vigencia = _find(r"Vigencia de la Cobertura:.*?Desde:\s*(\d{2}/\d{2}/\d{4})", text)
    vencimiento = _find(r"Hasta:\s*(\d{2}/\d{2}/\d{4})", text)
    
    # Asegurados
    # Ejemplo: Asegurados: Trabajadores del Contratante declarados y \n registrados mensualmente a Protecta Security.
    asegurados = _find(r"Asegurados:\s*(.*?)(?=\n\s*\n|3\.|2\.|DATOS|$)", text)
    if asegurados:
        asegurados = re.sub(r'\s+', ' ', asegurados).strip()

    # Contratante y RUC
    # Buscamos el RUC que aparece después de la etiqueta "Contratante:"
    ruc_contratante = _find(r"Contratante:.*?(?:Ruc|RUC):\s*(\d{11})", text)
    nombre_contratante = _find(r"Contratante:\s*(.*?)\n", text)
    if ruc_contratante == "":
        others = re.findall(r"\b(10\d{9}|20\d{9})\b", text)
        for cand in others:
            if cand != ruc_contratante:
                ruc_contratante = cand
                break

    ramo_raw = _find(r"Ramo:\s*([^\r\n]+)", text) or ""
    ramo_up = ramo_raw.upper()
    ramo_main = "SCTR" if ("SCTR" in ramo_up) else ""
    ramos_producto = None
    if "PENS" in ramo_up:
        ramos_producto = "PENSIONES"
    elif "SALUD" in ramo_up or "EPS" in ramo_up:
        ramos_producto = "SALUD"

    fecha_emision_clean = _clean(fecha_emision)
    fecha_vencimiento_pago = _add_days_ddmmyyyy(fecha_emision_clean, 15) if fecha_emision_clean else None
    colectivo = _clean(nombre_contratante) or _clean(asegurados)

    return {
        "prima_neta": _clean(prima_comercial),
        "prima_comercial": _clean(prima_comercial),
        "prima_total": _clean(prima_total),
        "prima_comercial_igv": _clean(prima_total),
        "numero_poliza": _clean(poliza),
        "moneda": _clean(moneda),
        "fecha_emision": _clean(fecha_emision),
        "fecha_vencimiento": _clean(fecha_vencimiento_pago),
        "fecha_vecimiento": _clean(fecha_vencimiento_pago),
        "ultimo_dia_pago": _clean(fecha_vencimiento_pago),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),
        "colectivo_asegurado": _clean(colectivo),
        "ramo": _clean(ramo_main) or "SCTR",
        "ramos_producto": _clean(ramos_producto),
        "numero_documento_extracted": _clean(ruc_contratante),
        "contratante": _clean(nombre_contratante)
    }

