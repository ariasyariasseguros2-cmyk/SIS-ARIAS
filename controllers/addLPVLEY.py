# NUEVO: parser específico para La Positiva – Vida Ley
import re
from typing import Optional, Dict
from datetime import datetime, timedelta

def _find(pattern: str, text: str, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

# NUEVO: tomar la última coincidencia cuando hay múltiples bloques en el PDF
def _find_last(pattern: str, text: str, flags=re.IGNORECASE):
    ms = list(re.finditer(pattern, text, flags))
    return ms[-1].group(1).strip() if ms else None

def parse_positiva_vidaley(text: str) -> Dict[str, str]:
    # Encabezados del PDF de Proforma de Cobertura (Cobro)
    numero_proforma = (
        _find(r"N[úu]mero\s+de\s+Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
        or _find(r"\bProforma\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"N[úu]mero\s+de\s+Proforma\s*([0-9A-Z\-]+)", text)
        or _find(r"\bN[úu]mero\s*Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
    )
    poliza_nro = (_find(r"P[oó]liza\s*Nro\s*:\s*([0-9A-Z\-]+)", text)
                  or _find(r"P[oó]liza\s*N°\s*:\s*([0-9A-Z\-]+)", text)
                  or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", text))

    # Usar la última coincidencia para evitar capturar bloques anteriores
    vig_desde = _find_last(r"Vigencia Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    # “Vencimiento” (fecha de pago) y “Hasta” (fin de vigencia)
    pago_venc = (
        _find_last(r"Vencimiento\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Fecha\s+de\s+Vencimiento\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Vencimiento\s+(?:Proforma|Recibo)\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    fecha_venc = pago_venc
    vig_hasta = _find_last(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    moneda = _find(r"Moneda\s*:\s*([A-Za-z]+)", text)
    emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Asegurado/Contratante
    contratante = _find(r"Contratante\s*:\s*(.+)", text)
    asegurado = _find(r"Asegurado\s*:\s*(.+)", text)
    colectivo_asegurado = (asegurado or contratante)
    
    # Extraer RUC (11 dígitos) o DNI (8 dígitos) asociado al contratante o asegurado
    # Lógica de proximidad: Buscar RUC más cercano a campos clave (Contratante, Proforma, etc.)
    # para evitar capturar el RUC de la aseguradora (cabecera) de forma automática.
    
    ruc_candidato = None
    
    # Encontrar pivotes que indican el inicio de los datos del cliente/póliza
    pivots_iter = re.finditer(r"(?:Contratante|Asegurado|Proforma|P[oó]liza|Contrato)\s*[:]", text, re.IGNORECASE)
    pivots = [m.start() for m in pivots_iter]
    
    # Prioridad 1: Buscar explícitamente RUC (11 dígitos) con etiqueta "R.U.C."
    rucs_matches = list(re.finditer(r"R\.?U\.?C\.?[\s:\.]*(\d{11})", text, re.IGNORECASE))
    
    if rucs_matches:
        if pivots:
            first_pivot = pivots[0]
            rucs_after = [m for m in rucs_matches if m.start() >= first_pivot]
            if rucs_after:
                ruc_candidato = rucs_after[0].group(1)
            else:
                best_match = min(rucs_matches, key=lambda m: min(abs(m.start() - p) for p in pivots))
                ruc_candidato = best_match.group(1)
        else:
            if len(rucs_matches) > 1:
                ruc_candidato = rucs_matches[1].group(1)
            else:
                ruc_candidato = rucs_matches[0].group(1)
    
    # Prioridad 2: Buscar explícitamente DNI (8 dígitos) si no hay RUC
    if not ruc_candidato:
        dnis_matches = list(re.finditer(r"D\.?N\.?I\.?[\s:\.]*(\d{8})", text, re.IGNORECASE))
        if dnis_matches:
            if pivots:
                first_pivot = pivots[0]
                dnis_after = [m for m in dnis_matches if m.start() >= first_pivot]
                if dnis_after:
                    ruc_candidato = dnis_after[0].group(1)
                else:
                    best_match = min(dnis_matches, key=lambda m: min(abs(m.start() - p) for p in pivots))
                    ruc_candidato = best_match.group(1)
            else:
                ruc_candidato = dnis_matches[0].group(1)

    # Prioridad 3: Fallback a búsqueda genérica de RUC (empieza con 10 o 20)
    if not ruc_candidato:
        generic_matches = list(re.finditer(r"\b(10\d{9}|20\d{9})\b", text))
        if generic_matches:
            if pivots:
                first_pivot = pivots[0]
                gen_after = [m for m in generic_matches if m.start() >= first_pivot]
                if gen_after:
                    ruc_candidato = gen_after[0].group(1)
                else:
                     best_match = min(generic_matches, key=lambda m: min(abs(m.start() - p) for p in pivots))
                     ruc_candidato = best_match.group(1)
            else:
                if len(generic_matches) > 1:
                    ruc_candidato = generic_matches[1].group(1)
                else:
                    ruc_candidato = generic_matches[0].group(1)

    # Ramo/marca de Vida Ley
    ramo = (_find(r"Ramo\s*:\s*(.+)", text) or "Vida Ley")

    # Conceptos: “Prima” y “IGV/Impuesto”
    prima_line = _find(r"\bPrima\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    prima_comercial = _money(prima_line)
    
    # Fallback fechas: si falta último día de pago, calcular emision + 15
    def _add_days(date_str: Optional[str], days: int) -> Optional[str]:
        try:
            if not date_str: return None
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    # NUEVO: Último día de pago = fin de vigencia + 15; si no hay, emisión + 15; luego el campo capturado
    ultimo_por_vigencia = _add_days(emision, 20) if emision else None
    ultimo_por_emision = _add_days(emision, 20) if emision else None
    pago_venc = ultimo_por_vigencia or ultimo_por_emision or pago_venc

    # Preferir el último día de pago como 'fecha_vencimiento'; si no, usar fin de vigencia
    fecha_venc = pago_venc or vig_hasta
    item = {
        "numero_poliza": poliza_nro,
        "recibo": numero_proforma,
        "colectivo_asegurado": colectivo_asegurado,
        "inicio_vigencia": vig_desde,
        # Fin de vigencia debe ser “Hasta”; si falta, usar “Vencimiento”
        "vencimiento": vig_hasta or pago_venc,
        "moneda": moneda,
        "fecha_emision": emision,
        "ultimo_dia_pago": pago_venc,  # fecha de pago
        "fecha_vencimiento": fecha_venc,
        "prima_comercial": prima_comercial,
        "ramo": ramo,
        "numero_documento_extracted": ruc_candidato,
    }
    print("item vida ley", item)
    # Limpia entradas vacías
    return {k: v for k, v in item.items() if v}