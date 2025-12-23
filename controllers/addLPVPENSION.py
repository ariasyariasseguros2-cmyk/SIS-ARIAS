# NUEVO: parser específico para La Positiva – Vida Ley
import re
from typing import Optional, Dict
from datetime import datetime, timedelta

def _find(pattern: str, text: str, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    # Normalizar whitespace y currency, y unificar separadores para no perder decimales
    s2 = re.sub(r"\s+", "", s).replace("S/", "").replace("s/", "")
    if "," in s2 and "." in s2:
        s3 = s2.replace(",", "")
    elif "," in s2 and "." not in s2:
        s3 = s2.replace(".", "").replace(",", ".")
    else:
        s3 = s2
    m = re.search(r"([0-9]+(?:\.[0-9]{2})?)", s3)
    return f"{float(m.group(1)):.2f}" if m else None

# NUEVO: tomar la última coincidencia cuando hay múltiples bloques en el PDF
def _find_last(pattern: str, text: str, flags=re.IGNORECASE):
    ms = list(re.finditer(pattern, text, flags))
    return ms[-1].group(1).strip() if ms else None

def parse_positiva_Pension(text: str) -> Dict[str, str]:
    t_low = text.lower()

    # Encabezados: Proforma / Póliza / Contrato
    numero_proforma = (
        _find(r"N[úu]mero\s+de\s+Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
        or _find(r"\bProforma\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"N[úu]mero\s+de\s+Proforma\s*([0-9A-Z\-]+)", text)
        or _find(r"\bN[úu]mero\s*Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
    )
    poliza_nro = (
        _find(r"P[oó]liza\s*Nro\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"P[oó]liza\s*N°\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", text)
    )
    contrato_nro = _find(r"Contrato\s+Nro\s*:\s*([0-9A-Z\-]+)", text)

    # Vigencias: usar la última coincidencia por si hay múltiples bloques
    vig_desde = _find_last(r"Vigencia Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    vig_hasta = _find_last(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    # Capturar variantes de “Vencimiento”
    pago_venc = (
        _find_last(r"Vencimiento\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Fecha\s+de\s+Vencimiento\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Vencimiento\s+(?:Proforma|Recibo)\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    fecha_venc = pago_venc

    moneda = _find(r"Moneda\s*:\s*([A-Za-z]+)", text)
    emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Asegurado / Contratante
    contratante = _find(r"Contratante\s*:\s*(.+)", text)
    asegurado = _find(r"Asegurado\s*:\s*(.+)", text)
    colectivo_asegurado = (asegurado or contratante)

    # Ramo: preferir el campo explícito; si no, inferir por texto
    ramo = _find(r"Ramo\s*:\s*(.+)", text)
    if not ramo:
        if "pension" in t_low:
            ramo = "SCTR PENSION"
        elif "salud" in t_low or "eps" in t_low:
            ramo = "SCTR SALUD"
        else:
            ramo = "La Positiva"

    # Conceptos: capturas y prioridades (usar última coincidencia del bloque)
    sobrevivencia = _money(_find_last(r"Sobrevivencia[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE))
    costos_emision = _money(_find_last(r"Costos?\s+de\s+Emisi[oó]n[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE)) or \
                     _money(_find_last(r"Costos?\s+Emisi[oó]n[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE))
    prima_comercial_inclusive = _money(_find(r"Prima\s+Comercial[\s\S]*?Incluye[\s\S]*?Emisi[oó]n[\s\S]*?(?:[:=]|\s)?\s*(?:S?\/)?\s*([0-9\., ]+)", text))
    igv_val = _money(_find(r"(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text))
    prima_comercial_igv = _money(_find(r"Prima\s+Comercial\s*\+\s*IGV[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text))
    prima_total_alt = _money(_find(r"(?:Importe\s+Total|Total\s+a\s+Pagar|Total)[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text))

    # NUEVO: captura por filas del cuadro (más robusta frente a saltos de línea/columnas)
    for m in re.finditer(
        r"(Sobrevivencia|Costos?\s+de\s+Emisi[oó]n|Impuesto\s+General\s+a\s+las\s+Ventas)[\s:]*S?\/?\s*([0-9\., ]+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        label = m.group(1).lower()
        amount = _money(m.group(2))
        if "sobrevivencia" in label:
            sobrevivencia = sobrevivencia or amount
        elif "costos" in label:
            costos_emision = costos_emision or amount
        elif "impuesto" in label or "igv" in label:
            igv_val = igv_val or amount

    # Fallback: si no hay 'Importe Total' explícito, dedúcelo de (Comercial+IGV) - IGV
    if not prima_total_alt and prima_comercial_igv and igv_val:
        try:
            prima_total_alt = f"{float(prima_comercial_igv) - float(igv_val):.2f}"
        except Exception:
            pass

    # NUEVO: si falta 'costos_emision' y hay 'prima_total_alt' + 'sobrevivencia', derivarlo
    if not costos_emision and prima_total_alt and sobrevivencia:
        try:
            costos_emision = f"{float(prima_total_alt) - float(sobrevivencia):.2f}"
        except Exception:
            pass

    # NUEVO: Prima Neta = Sobrevivencia
    prima_neta = sobrevivencia

    # Prima Comercial (sin IGV) a partir de Prima Neta + Costos de Emisión
    if prima_neta and costos_emision:
        try:
            prima_comercial = f"{float(prima_neta) + float(costos_emision):.2f}"
        except Exception:
            prima_comercial = prima_comercial_inclusive or prima_total_alt or prima_neta
    else:
        prima_comercial = prima_comercial_inclusive or prima_total_alt or prima_neta

    # Prima Comercial + IGV (capturada o calculada)
    if not prima_comercial_igv:
        base = prima_comercial
        if base and igv_val:
            try:
                prima_comercial_igv = f"{float(base) + float(igv_val):.2f}"
            except Exception:
                prima_comercial_igv = base

    # Fallback fechas: si falta último día de pago, calcular emision + 15
    def _add_days(date_str: Optional[str], days: int) -> Optional[str]:
        try:
            if not date_str: return None
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    # NUEVO: Último día de pago = fin de vigencia + 15; si no hay, emisión + 15; luego el campo capturado
    ultimo_por_vigencia = _add_days(emision, 15) if emision else None
    ultimo_por_emision = _add_days(emision, 15) if emision else None
    pago_venc = ultimo_por_vigencia or ultimo_por_emision or pago_venc

    # Preferir el último día de pago como 'fecha_vencimiento'; si no, usar fin de vigencia
    fecha_venc = pago_venc or vig_hasta

    item = {
        "numero_poliza": poliza_nro or contrato_nro,
        "contrato_nro": contrato_nro,
        "recibo": numero_proforma,
        "colectivo_asegurado": colectivo_asegurado,
        "inicio_vigencia": vig_desde,
        "vencimiento": vig_hasta,
        "moneda": moneda,
        "fecha_emision": emision,
        "ultimo_dia_pago": pago_venc,
        "fecha_vencimiento": fecha_venc,
        "prima_neta": prima_neta,
        # Mantener compatibilidad: 'prima_total' representa la comercial sin IGV
        "prima_total": prima_comercial,
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": prima_comercial_igv,
        "ramo": ramo,
    }
    print("item pension", item)
    return {k: v for k, v in item.items() if v}