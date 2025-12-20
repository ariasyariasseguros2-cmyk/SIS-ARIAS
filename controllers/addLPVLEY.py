# NUEVO: parser específico para La Positiva – Vida Ley
import re
from typing import Optional, Dict

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
    pago_venc = _find_last(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    vig_hasta = _find_last(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    moneda = _find(r"Moneda\s*:\s*([A-Za-z]+)", text)
    emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Asegurado/Contratante
    contratante = _find(r"Contratante\s*:\s*(.+)", text)
    asegurado = _find(r"Asegurado\s*:\s*(.+)", text)
    colectivo_asegurado = (asegurado or contratante)

    # Ramo/marca de Vida Ley
    ramo = (_find(r"Ramo\s*:\s*(.+)", text) or "Vida Ley")

    # Conceptos: “Prima” y “IGV/Impuesto”
    prima_line = _find(r"\bPrima\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    prima_comercial = _money(prima_line)

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
        "prima_comercial": prima_comercial,
        "ramo": ramo,
    }
    # Limpia entradas vacías
    return {k: v for k, v in item.items() if v}