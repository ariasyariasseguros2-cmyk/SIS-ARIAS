import re
from typing import Optional, Dict
from datetime import datetime

def _find(pattern: str, text: str, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    # Capturar número con separadores de miles y decimales
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]+)?)", s)
    if m:
        v = m.group(1).replace(",", "")
        try:
            return f"{float(v):.2f}"
        except:
            return v
    return None

def parse_positiva_vida_generales(text: str) -> Dict[str, str]:
    item = {}
    
    # Póliza
    poliza = (
        _find(r"P[oó]liza\s*N(?:ro\.?|[°º]|o)?\s*[:：]?\s*([0-9]{6,20})", text)
        or _find(r"\bP[oó]liza\b[\s\S]{0,100}?N(?:ro\.?|[°º]|o)\s*[:：]?\s*([0-9]{6,20})", text)
    )
    item['numero_poliza'] = poliza

    # Ramo
    ramo = _find(r"Ramo\s*[:：]\s*(.+)", text)
    item['ramo'] = ramo

    # Vigencias
    vig_inicio = _find(r"Vigencia-Inicio\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
    vig_fin = _find(r"T[ée]rmino\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
    
    if not vig_inicio:
        m_vig = re.search(r"vigencia\s*[:：]?\s*(?:del\s*)?(\d{2}/\d{2}/\d{4})\s*(?:al|a)\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if m_vig:
            vig_inicio = m_vig.group(1)
            vig_fin = m_vig.group(2)
            
    item['inicio_vigencia'] = vig_inicio
    item['vencimiento'] = vig_fin

    # Asegurado / Contratante
    # Prioridad 1: Datos del Asegurado -> Nombre o Razón Social
    asegurado = _find(r"Datos\s+del\s+Asegurado[\s\S]{0,100}?Nombre\s+o\s+Raz[oó]n\s+Social\s*[:：]\s*(.+)", text)
    # Prioridad 2: Datos del Contratante -> Nombre o Razón Social
    contratante = _find(r"Datos\s+del\s+Contratante[\s\S]{0,100}?Nombre\s+o\s+Raz[oó]n\s+Social\s*[:：]\s*(.+)", text)
    
    # Fallbacks generales
    if not asegurado:
        asegurado = _find(r"Asegurado\s*[:：]\s*(.+)", text)
    if not contratante:
        contratante = _find(r"Contratante\s*[:：]\s*(.+)", text)
        
    item['colectivo_asegurado'] = asegurado or contratante
    item['contratante'] = contratante

    # Moneda
    moneda = None
    # Buscar moneda cerca de las primas
    m_mon = re.search(r"Prima\s+Comercial[\s\S]{0,150}?(US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)", text, re.IGNORECASE)
    if m_mon:
        tok = re.sub(r"\s+", "", m_mon.group(1).upper())
        if "US" in tok or "USD" in tok or tok == "$" or "DOL" in tok:
            moneda = "US$"
        else:
            moneda = "S/"
    
    if not moneda:
        # Buscar "Moneda: ..."
        m_mon2 = re.search(r"Moneda\s*[:：]\s*([^\n]+)", text, re.IGNORECASE)
        if m_mon2:
            tok = m_mon2.group(1).upper()
            if "DOL" in tok or "US" in tok or "$" in tok:
                moneda = "US$"
            else:
                moneda = "S/"
                
    item['moneda'] = moneda

    # Primas
    # Prima Comercial
    pc = _find(r"Prima\s+Comercial[\s\S]{0,50}?(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*([0-9][0-9\.,]*)", text)
    item['prima_comercial'] = _money(pc)
    
    # Prima Comercial + IGV
    pc_igv = _find(r"Prima\s+Comercial\s*\+\s*IGV[\s\S]{0,50}?(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*([0-9][0-9\.,]*)", text)
    item['prima_comercial_igv'] = _money(pc_igv)

    # Fecha Emisión
    emision = _find(r"Emisi[oó]n\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
    item['fecha_emision'] = emision

    # Fecha Vencimiento (de la proforma/recibo)
    f_venc = _find(r"Fecha\s+de\s+Vencimiento\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
    item['fecha_vencimiento'] = f_venc

    return {k: v for k, v in item.items() if v}
