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
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

def parse_protecta_pension(text: str) -> Dict[str, str]:
    # Contrato / Póliza
    contrato = _find(r"Contrato\s*:\s*([0-9A-Z\-]+)", text) or _find(r"CONTRATO\s*:\s*([0-9A-Z\-]+)", text)

    # Proforma / Recibo (por etiqueta y fallback patrón PF/AC-SCTR-***)
    recibo = _find(r"(?:PROFORMA|Proforma)\s*:\s*([A-Z0-9\-/]+)", text) \
        or _find(r"\b((?:PF|AC)[-\s]?SCTR[-\s]?[0-9A-Z\-]+)\b", text)
    # Fallback adicional: buscar el código junto al encabezado “AVISO DE COBRANZA”
    if not recibo:
        m_aviso = re.search(r"AVISO\s+DE\s+COBRANZA.*?\b([A-Z]{2}\s*-\s*SCTR\s*-\s*[0-9A-Z\-]+)\b", text, re.IGNORECASE | re.DOTALL)
        if m_aviso:
            # Normalizar espacios alrededor de guiones
            code = re.sub(r"\s*-\s*", "-", m_aviso.group(1))
            recibo = code

    # Vigencia: Desde ... hasta ...
    m_vig = re.search(r"Vigencia\s*:\s*Desde\s*([0-9]{2}/[0-9]{2}/[0-9]{4}).*?hasta\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text, re.IGNORECASE | re.DOTALL)
    inicio_vigencia = m_vig.group(1) if m_vig else _find(r"Desde\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    vencimiento = m_vig.group(2) if m_vig else _find(r"Hasta\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Fecha vencimiento del encabezado (último día de pago)
    fecha_vencimiento = _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Fecha emisión y vencimiento (superior derecho)
    fecha_emision = _find(r"FECHA\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    fecha_vencimiento = _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Contratante / Colectivo
    colectivo = _find(r"Contratante\s*:\s*(.+)", text) or _find(r"CONTRATANTE\s*:\s*(.+)", text)
    if colectivo:
        colectivo = colectivo.split("\n")[0].strip()

    # Rubro / ramo
    ramo = _find(r"Rubro\s*:\s*(.+)", text)
    if ramo:
        ramo = ramo.split("\n")[0].strip()

    # Concepto: IMPORTE / IGV / TOTAL
    importe = _money(_find(r"CONCEPTO.*?SCTR.*?IMPORTE\s*([0-9\.,]+)", text)) or _money(_find(r"\bIMPORTE\b\s*([0-9\.,]+)", text))
    igv_val = _money(_find(r"\bIGV\b\s*([0-9\.,]+)", text))
    total_con_igv = _money(_find(r"\bTOTAL\b\s*([0-9\.,]+)", text))

    # Derivar prima comercial si falta
    prima_comercial = importe
    if not prima_comercial and total_con_igv and igv_val:
        try:
            tc = float(total_con_igv.replace(',', '.'))
            igv = float(igv_val.replace(',', '.'))
            prima_comercial = f"{(tc - igv):.2f}"  # 94.40 - 14.40 = 80.00
        except Exception:
            pass

    # Extraer RUC/DNI del cliente
    # Prioridad 1: Etiqueta "DNI/RUC" que usa Protecta explícitamente para el cliente
    ruc_candidato = _find(r"DNI/RUC\s*[:]?\s*(\d{8,11})", text)
    
    # Prioridad 2: Buscar RUC/DNI general pero filtrar el de Protecta (20517207331)
    if not ruc_candidato:
        candidates = re.findall(r"(?:RUC|DNI)\s*[:]?\s*(\d{8,11})", text, re.IGNORECASE)
        for cand in candidates:
             if cand != "20517207331": # RUC de Protecta Security
                 ruc_candidato = cand
                 break

    item = {
        "numero_poliza": _find(r"Contrato\s*:\s*([0-9A-Z\-]+)", text) or _find(r"CONTRATO\s*:\s*([0-9A-Z\-]+)", text),
        "contrato_nro": _find(r"Contrato\s*:\s*([0-9A-Z\-]+)", text) or _find(r"CONTRATO\s*:\s*([0-9A-Z\-]+)", text),
        "recibo": recibo,
        "colectivo_asegurado": colectivo,
        "inicio_vigencia": inicio_vigencia,
        "vencimiento": vencimiento,
        "fecha_emision": fecha_emision or "",
        "ultimo_dia_pago": fecha_vencimiento,
        "fecha_vencimiento": fecha_vencimiento or vencimiento or "",  # usar encabezado "Vencimiento"
        "ramo": ramo or "SCTR Salud",
        "moneda": "SOLES",
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": total_con_igv or (f"{float((prima_comercial or '0').replace(',', '.')) + float((igv_val or '0').replace(',', '.')):.2f}" if prima_comercial and igv_val else None),
        "numero_documento_extracted": ruc_candidato,
    }
    print("item", item)
    # Limpieza final: quitar claves vacías
    return {k: _clean(v) for k, v in item.items() if v}