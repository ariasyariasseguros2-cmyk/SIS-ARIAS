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

def parse_crecer_pension(text: str) -> Dict[str, str]:
    # Contrato / Póliza
    contrato = _find(r"Contrato\s*:\s*([0-9A-Z\-]+)", text) or _find(r"CONTRATO\s*:\s*([0-9A-Z\-]+)", text)

    # Proforma / Recibo: Proforma explícita, PF-SCTR y NUEVO: CS-SCTR-***
    recibo = _find(r"(?:PROFORMA|Proforma)\s*:\s*([A-Z0-9\-]+)", text) \
        or _find(r"\b(PF[-\s]?SCTR[-\s]?[0-9A-Z\-]+)\b", text) \
        or _find(r"\b(CS[-\s]?SCTR[-\s]?[0-9A-Z\-]+)\b", text)

    # Vigencia: Desde ... hasta ...
    m_vig = re.search(r"Vigencia\s*:\s*Desde\s*([0-9]{2}/[0-9]{2}/[0-9]{4}).*?hasta\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text, re.IGNORECASE | re.DOTALL)
    inicio_vigencia = m_vig.group(1) if m_vig else _find(r"Desde\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    vencimiento = m_vig.group(2) if m_vig else _find(r"Hasta\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Fecha emisión y último día de pago (superior derecho)
    fecha_emision = _find(r"FECHA\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    ultimo_dia_pago = _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Contratante / Colectivo
    colectivo = _find(r"Contratante\s*:\s*(.+)", text) or _find(r"CONTRATANTE\s*:\s*(.+)", text)
    if colectivo:
        colectivo = colectivo.split("\n")[0].strip()

    # Rubro / ramo
    ramo = _find(r"Rubro\s*:\s*(.+)", text)
    if ramo:
        ramo = ramo.split("\n")[0].strip()
    ramo_main: Optional[str] = None
    ramos_producto: Optional[str] = None
    t_low = text.lower()
    if ramo:
        rl = ramo.lower()
        if "sctr" in rl:
            ramo_main = "SCTR"
            if "salud" in rl or "eps" in rl:
                ramos_producto = "Salud"
            elif "pens" in rl:
                ramos_producto = "Pensión"
    if not ramo_main and "sctr" in t_low:
        ramo_main = "SCTR"
        if "salud" in t_low or "eps" in t_low:
            ramos_producto = "Salud"
        elif "pens" in t_low:
            ramos_producto = "Pensión"

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
            prima_comercial = f"{(tc - igv):.2f}"
        except Exception:
            pass

    # Extraer RUC del cliente
    # Prioridad 1: Buscar etiqueta "DNI/RUC" seguida de un número (formato específico de Crecer)
    ruc_candidato = _find(r"DNI/RUC\s*[:]?\s*(\d{8,11})", text)

    # Ignorar el RUC de la propia compañía si se captura por error
    if ruc_candidato and ruc_candidato.strip() == "20600098633":
        ruc_candidato = None

    # Prioridad 2: Buscar etiqueta "RUC" si no se halló DNI/RUC, filtrando el de Crecer (20600098633)
    if not ruc_candidato:
        candidates_ruc = re.findall(r"RUC\s*[:]?\s*(\d{11})", text, re.IGNORECASE)
        for cand in candidates_ruc:
            cand = cand.strip()
            if cand and cand != "20600098633":
                ruc_candidato = cand
                break
                
    # Fallback: Buscar cualquier número de 11 dígitos que empiece con 10 o 20
    if not ruc_candidato:
        all_candidates = re.findall(r"\b(10\d{9}|20\d{9})\b", text)
        for cand in all_candidates:
            cand = cand.strip()
            if cand and cand != "20600098633":
                ruc_candidato = cand
                break

    item = {
        "numero_poliza": contrato,
        "contrato_nro": contrato,
        "recibo": recibo,
        "colectivo_asegurado": colectivo,
        "inicio_vigencia": inicio_vigencia,
        "vencimiento": vencimiento,
        "fecha_emision": fecha_emision,
        "ultimo_dia_pago": ultimo_dia_pago,  # toma el “Vencimiento:” del encabezado superior
        "ramo": ramo_main or ramo,
        "ramos_producto": ramos_producto,
        "moneda": "SOLES",
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": total_con_igv or (f"{float((prima_comercial or '0').replace(',', '.')) + float((igv_val or '0').replace(',', '.')):.2f}" if prima_comercial and igv_val else None),
        "fecha_vencimiento": ultimo_dia_pago or None,  # reflejar en columna “Fecha Vencimiento” de la UI
        "numero_documento_extracted": ruc_candidato,
    }
    print("item crecer pension", item)
    # Limpieza final: quitar claves vacías
    return {k: _clean(v) for k, v in item.items() if v}
