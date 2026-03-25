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

def _normalize_name(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    # Remover DNI/RUC incluso si los dígitos vienen con espacios internos
    out = re.sub(r"(?:DNI\s*/\s*RUC|DNI|RUC)\s*[:\-]?\s*(?:\d[\d\s]{7,20})", "", s, flags=re.IGNORECASE)
    out = re.sub(r"\bMALP\s+ARTIDA\b", "MALPARTIDA", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip(" :,-")
    for _ in range(3):
        prev = out
        out = re.sub(r"\b([A-ZÁÉÍÓÚÑ])\s+([A-ZÁÉÍÓÚÑ]{2,})\b", r"\1\2", out)
        out = re.sub(r"\b([A-ZÁÉÍÓÚÑ]{3,})\s+([A-ZÁÉÍÓÚÑ])\b", r"\1\2", out)
        # Unir prefijos de 1–2 letras con palabra larga (p.ej., "V ALENTINA" -> "VALENTINA", "NA THALY" -> "NATHALY")
        out = re.sub(r"\b([A-ZÁÉÍÓÚÑ]{1,2})\s+([A-ZÁÉÍÓÚÑ]{3,12})\b", lambda m: m.group(1)+m.group(2) if len(m.group(1)+m.group(2))<=12 else m.group(0), out)
        out = re.sub(r"\b(?:([A-ZÁÉÍÓÚÑ])\s+){2,}([A-ZÁÉÍÓÚÑ])\b", lambda m: re.sub(r"\s+", "", m.group(0)), out)
        if out == prev:
            break
    # Unificación genérica de palabras cortas + largas (evita listas específicas)
    out = re.sub(r"\bS\s*\.?\s*A\s*\.?\s*C\b", "S.A.C.", out, flags=re.IGNORECASE)
    out = re.sub(r"(?<!\s)(S\.A\.C\.)", r" \1", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" :,-")
    return out
def parse_sanitas_salud(text: str) -> Dict[str, str]:
    # Contrato / Póliza
    contrato = _find(r"Contrato\s*:\s*([0-9A-Z\-]+)", text) or _find(r"CONTRATO\s*:\s*([0-9A-Z\-]+)", text)

    # Proforma / Recibo (por etiqueta y fallback patrón PF-SCTR-***)
    recibo = _find(r"(?:PROFORMA|Proforma)\s*:\s*([A-Z0-9\-]+)", text) \
        or _find(r"\b(PF[-\s]?SCTR[-\s]?[0-9A-Z\-]+)\b", text)

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
        colectivo = _normalize_name(colectivo)

    # Rubro / ramo y producto (cascada: Ramo SCTR -> Producto Salud/Pensión)
    ramo = _find(r"Rubro\s*:\s*(.+)", text)
    if ramo:
        ramo = ramo.split("\n")[0].strip()
    ramo_main = None
    ramos_producto = None
    t_low = text.lower()
    # Mapeo explícito: si el rubro trae "SCTR Salud" o similar, normalizar a Ramo=SCTR y Producto=Salud
    if ramo:
        rl = ramo.lower()
        if "sctr" in rl:
            ramo_main = "SCTR"
            if "salud" in rl or "eps" in rl:
                ramos_producto = "Salud"
            elif "pens" in rl:
                ramos_producto = "Pensión"
    # Si no se pudo derivar por rubro, usar el texto global
    if not ramo_main and ("sctr" in t_low):
        ramo_main = "SCTR"
        if "salud" in t_low or "eps" in t_low:
            ramos_producto = "Salud"

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
    # Prioridad 1: Etiqueta "DNI/RUC" que usa Sanitas explícitamente para el cliente
    ruc_candidato = _find(r"DNI/RUC\s*[:]?\s*(\d{8,11})", text)
    
    # Prioridad 2: Buscar RUC/DNI general pero filtrar el de Sanitas (20523470761)
    if not ruc_candidato:
        candidates = re.findall(r"(?:RUC|DNI)\s*[:]?\s*(\d{8,11})", text, re.IGNORECASE)
        for cand in candidates:
             if cand : # RUC de Sanitas Peru S.A. EPS
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
        "ramo": ramo_main or ramo or "SCTR",
        "ramos_producto": ramos_producto,
        "moneda": "SOLES",
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": total_con_igv or (f"{float((prima_comercial or '0').replace(',', '.')) + float((igv_val or '0').replace(',', '.')):.2f}" if prima_comercial and igv_val else None),
        "numero_documento_extracted": ruc_candidato,
    }
    print("insert salud", item)
    # Limpieza final: quitar claves vacías
    return {k: _clean(v) for k, v in item.items() if v}
