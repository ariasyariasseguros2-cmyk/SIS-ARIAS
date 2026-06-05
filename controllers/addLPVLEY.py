# NUEVO: parser específico para La Positiva – Vida Ley
import re
from typing import Optional, Dict
from datetime import datetime, timedelta

def _find(pattern: str, text: str, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    raw0 = str(s).strip()
    raw = raw0.replace("−", "-").replace("–", "-").replace("—", "-")
    m = re.search(r"(\(?\s*(?:-\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:-\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)", raw)
    tok = m.group(1).strip() if m else raw
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

# NUEVO: tomar la última coincidencia cuando hay múltiples bloques en el PDF
def _find_last(pattern: str, text: str, flags=re.IGNORECASE):
    ms = list(re.finditer(pattern, text, flags))
    return ms[-1].group(1).strip() if ms else None

def _extract_ruc(text: str) -> Optional[str]:
    pivots = [m.start() for m in re.finditer(r"(Contratante|Asegurado|N[úu]mero\s+de\s+Proforma|Proforma|P[óo]liza|Contrato|Datos\s+del\s+Recibo|Proforma\s+de\s+Pago)", text, re.IGNORECASE)]
    rucs_matches = list(re.finditer(r"R\.?U\.?C\.?[\s:\.]*(\d{11})", text, re.IGNORECASE))
    if rucs_matches:
        if pivots:
            best = min(rucs_matches, key=lambda m: min((d for d in [(m.start() - p) for p in pivots] if d >= 0), default=abs(m.start() - pivots[0])))
            return best.group(1)
        if len(rucs_matches) > 1:
            return rucs_matches[1].group(1)
        return rucs_matches[0].group(1)
    generic = list(re.finditer(r"\b(10\d{9}|20\d{9})\b", text))
    if generic:
        if pivots:
            best = min(generic, key=lambda m: min((d for d in [(m.start() - p) for p in pivots] if d >= 0), default=abs(m.start() - pivots[0])))
            return best.group(1)
        if len(generic) > 1:
            return generic[1].group(1)
        return generic[0].group(1)
    return None
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
    
    ruc_candidato = _extract_ruc(text)

    ramo = (_find(r"Ramo\s*:\s*(.+)", text) or "Vida Ley")

    ramo_main = "VIDA - LEY"
    ramos_producto: Optional[str] = None
    t_low = text.lower()

    producto_val = _find(r"Producto\s*:\s*([^\n]+)", text)
    if producto_val:
        p_low = producto_val.lower()
        if "trabajador" in p_low or "trabajadores" in p_low:
            ramos_producto = "OBRERO"
        elif "empleado" in p_low or "empleados" in p_low:
            ramos_producto = "EMPLEADOS"

    if not ramos_producto:
        if "trabajador" in t_low or "trabajadores" in t_low:
            ramos_producto = "OBRERO"
        elif "empleado" in t_low or "empleados" in t_low:
            ramos_producto = "EMPLEADOS"

    # Conceptos: “Prima” y “IGV/Impuesto”
    prima_line = _find(r"\bPrima\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
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

    # Preferir la fecha de emisión + 15 días como 'fecha_vencimiento'; si falta, usar último día de pago o fin de vigencia
    fecha_venc = _add_days(emision, 15) or pago_venc or vig_hasta
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
        "ramo": ramo_main or ramo,
        "ramos_producto": ramos_producto,
        "numero_documento_extracted": ruc_candidato,
    }
    print("item vida ley", item)
    # Limpia entradas vacías
    return {k: v for k, v in item.items() if v}
