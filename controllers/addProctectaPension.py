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
    m = re.search(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)", raw)
    tok = (m.group(1).strip() if m else raw)
    neg = False
    mp = re.match(r"^\((.*)\)$", tok)
    if mp:
        neg = True
        tok = (mp.group(1) or "").strip()
    if re.match(r"^\s*-\s*", tok):
        neg = True
    tok = re.sub(r"[^\d,\.]", "", tok)
    if not tok:
        return None
    if "," in tok and "." in tok:
        if tok.rfind(",") > tok.rfind("."):
            tok = tok.replace(".", "").replace(",", ".")
        else:
            tok = tok.replace(",", "")
    elif "," in tok and "." not in tok:
        tok = tok.replace(".", "").replace(",", ".")
    else:
        tok = tok.replace(",", "")
    try:
        num = float(tok)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return f"-{tok}" if (neg and tok) else tok

def parse_protecta_pension(text: str) -> Dict[str, str]:
    # Contrato / Póliza
    # Se añade robustez para espacios y caracteres
    contrato = _find(r"Contrato\s*[:]\s*([\w\-]+)", text) or _find(r"CONTRATO\s*[:]\s*([\w\-]+)", text)

    # Proforma / Recibo (por etiqueta y fallback patrón PF/AC-SCTR-***)
    recibo = _find(r"(?:PROFORMA|Proforma)\s*[:]\s*([A-Z0-9\-/]+)", text) \
        or _find(r"\b((?:PF|AC)[-\s]?SCTR[-\s]?[0-9A-Z\-]+)\b", text)
    
    # Fallback adicional: buscar el código junto al encabezado “AVISO DE COBRANZA”
    if not recibo:
        m_aviso = re.search(r"AVISO\s+DE\s+COBRANZA.*?\b([A-Z]{2}\s*-\s*SCTR\s*-\s*[0-9A-Z\-]+)\b", text, re.IGNORECASE | re.DOTALL)
        if m_aviso:
            # Normalizar espacios alrededor de guiones
            code = re.sub(r"\s*-\s*", "-", m_aviso.group(1))
            recibo = code

    # Vigencia: Desde ... hasta ...
    # Se divide en dos búsquedas para mayor seguridad ante saltos de línea
    inicio_vigencia = _find(r"Desde\s*(\d{2}/\d{2}/\d{4})", text)
    vencimiento = _find(r"hasta\s*(\d{2}/\d{2}/\d{4})", text)
    
    if not inicio_vigencia or not vencimiento:
        m_vig = re.search(r"Vigencia\s*[:]\s*Desde\s*(\d{2}/\d{2}/\d{4}).*?hasta\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE | re.DOTALL)
        if m_vig:
            inicio_vigencia = m_vig.group(1)
            vencimiento = m_vig.group(2)

    # Fecha vencimiento del encabezado (último día de pago)
    # Se busca tanto 'Vencimiento:' como 'VCTO DE CIP' si fuera necesario
    fecha_vencimiento = _find(r"Vencimiento\s*[:]\s*(\d{2}/\d{2}/\d{4})", text)
    if not fecha_vencimiento:
        fecha_vencimiento = _find(r"VCTO\s+DE\s+CIP\s*(\d{2}/\d{2}/\d{4})", text)

    # Fecha emisión (superior derecho)
    fecha_emision = _find(r"FECHA\s*[:]\s*(\d{2}/\d{2}/\d{4})", text)

    # Contratante / Colectivo
    colectivo = _find(r"Contratante\s*[:]\s*(.+)", text) or _find(r"CONTRATANTE\s*[:]\s*(.+)", text)
    if colectivo:
        colectivo = colectivo.split("\n")[0].strip()

    # Rubro / ramo
    ramo = _find(r"Rubro\s*[:]\s*(.+)", text)
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
    # Mejorado para buscar por etiqueta de fila (PRIMA COMERCIAL, PRIMA TOTAL)
    # Patrón general: Label + Espacios + Numero
    
    # Prima Comercial
    prima_comercial = _money(_find(r"PRIMA\s+COMERCIAL\s*(\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d+)*\s*\)?)", text))
    
    # IGV
    igv_val = _money(_find(r"\bIGV\b\s*(\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d+)*\s*\)?)", text))
    
    # Prima Total
    total_con_igv = _money(_find(r"PRIMA\s+TOTAL\s*(\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d+)*\s*\)?)", text))
    
    # Fallback si falla la búsqueda directa (a veces el texto se extrae desordenado)
    if not prima_comercial:
        # Intentar buscar bajo columna IMPORTE si existe esa estructura
        prima_comercial = _money(_find(r"CONCEPTO.*?SCTR.*?IMPORTE\s*(\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d+)*\s*\)?)", text))

    if not total_con_igv:
        total_con_igv = _money(_find(r"\bTOTAL\b\s*(\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d+)*\s*\)?)", text))

    # Derivar prima comercial si falta pero tenemos total e IGV
    if not prima_comercial and total_con_igv and igv_val:
        try:
            tc = float(total_con_igv.replace(',', '.'))
            igv = float(igv_val.replace(',', '.'))
            prima_comercial = f"{(tc - igv):.2f}"
        except Exception:
            pass
    
    # Si aun falta prima_comercial, usar prima_total como fallback (asumiendo exento o error)
    if not prima_comercial and total_con_igv:
        # Solo si IGV es 0 o no se encontró
        if not igv_val or igv_val == '0.00':
             prima_comercial = total_con_igv

    # Extraer RUC/DNI del cliente
    # Prioridad 1: Etiqueta "DNI/RUC" que usa Protecta explícitamente para el cliente
    ruc_candidato = _find(r"DNI/RUC\s*[:]?\s*(\d{8,11})", text)
    
    # Prioridad 2: Buscar RUC/DNI general pero filtrar el de Protecta (20517207331)
    if not ruc_candidato:
        candidates = re.findall(r"(?:RUC|DNI)\s*[:]?\s*(\d{8,11})", text, re.IGNORECASE)
        for cand in candidates:
             if cand != "20517207331" and cand != "20601964482": # Filtrar RUCs conocidos de la aseguradora si los hubiera
                 if cand != "20517207331":
                    ruc_candidato = cand
                    break

    item = {
        "numero_poliza": contrato,
        "contrato_nro": contrato,
        "recibo": recibo,
        "colectivo_asegurado": colectivo,
        "inicio_vigencia": inicio_vigencia,
        "vencimiento": vencimiento,
        "fecha_emision": fecha_emision or "",
        "ultimo_dia_pago": fecha_vencimiento,
        "fecha_vencimiento": fecha_vencimiento or vencimiento or "",
        "ramo": ramo_main or ramo or "SCTR",
        "ramos_producto": ramos_producto,
        "moneda": "SOLES",
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": total_con_igv or (f"{float((prima_comercial or '0').replace(',', '.')) + float((igv_val or '0').replace(',', '.')):.2f}" if prima_comercial and igv_val else None),
        "numero_documento_extracted": ruc_candidato,
    }
    print("item sctr pension", item)
    # Limpieza final: quitar claves vacías
    return {k: _clean(v) for k, v in item.items() if v}
