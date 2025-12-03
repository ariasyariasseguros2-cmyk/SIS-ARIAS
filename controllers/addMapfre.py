import re
from typing import Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

# NUEVO: normalizar todos los espacios y saltos de línea a un solo espacio
def _canon(text: str) -> str:
    return re.sub(r"\s+", " ", text)

# NUEVO: devolver solo los dígitos (p. ej., para recibo)
def _digits(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    parts = re.findall(r"\d+", s)
    return "".join(parts) if parts else None

# NUEVO: helper para capturar valor tras una etiqueta, tolerando saltos de línea
def _find_after(label_pat: str, text: str, value_pat: str, window: int = 160, flags=re.IGNORECASE) -> Optional[str]:
    for m in re.finditer(label_pat, text, flags):
        frag = text[m.end(): m.end() + window]
        vm = re.search(value_pat, frag, flags)
        if vm:
            return vm.group(1).strip()
    return None

def parse_mapfre(text: str) -> Dict[str, str]:
    """
    Parser para PDFs Mapfre (incluye variantes EPS).
    Devuelve un dict que luego se normaliza a la UI en /upload.
    """
    item: Dict[str, str] = {}
    flat = _canon(text)  # texto sin saltos múltiples para patrones sencillos

    # Número de póliza: variantes con acento y sin
    item["numero_poliza"] = (
        _find(r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"P[ÓO]LIZA\s*:?\s*([0-9A-Z\-]+)", text)
        or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", text)
    )

    rec_raw = (
        _find(r"\bRECIBO\W*(\d{5,})", flat)
        or _find(r"\bRecibo\W*(\d{5,})", flat)
        or _find(r"\bRECIBO\W*(\d{5,})", text)
        or _find_after(r"\bRECIBO\b", text, r"([0-9]{5,})", window=300)
        or _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*([0-9]{5,})", text)
    )
    pos = flat.upper().find("RECIBO")
    if pos != -1:
        print("[parse_mapfre] contexto RECIBO:", flat[pos-60:pos+60])
    print("[parse_mapfre] RECIBO raw ->", rec_raw)
    item["recibo"] = _digits(rec_raw)

    item["colectivo_asegurado"] = (
        _find(r"Colectivo\s+Asegurado\s*:\s*(.+)", text)
        or _find(r"CONTRATANTE\s*:\s*(.+)", text)
        or _find(r"Asegurado\s*:\s*(.+)", text)
    )

    item["inicio_vigencia"] = (
        _find(r"Inicio\s+de\s+Vigencia\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    item["vencimiento"] = (
        _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find(r"HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )

    # Moneda: restringida a valores esperados
    item["moneda"] = (
        _find(r"\bMoneda\s*[:\-]?\s*(SOLES|DOLARES|DÓLARES|USD|PEN)", flat)
        or _find(r"\bMONEDA\s*[:\-]?\s*(SOLES|DOLARES|DÓLARES|USD|PEN)", flat)
        or _find_after(r"\bMoneda\b", text, r"(SOLES|DOLARES|DÓLARES|USD|PEN)", window=400)
        or _find_after(r"\bMONEDA\b", text, r"(SOLES|DOLARES|DÓLARES|USD|PEN)", window=400)
    )

    # Forma de Pago: evita capturar moneda
    item["forma_pago"] = (
        _find(r"Forma\s+de\s+Pago\s*[:\-]?\s*(MENSUAL|ANUAL|SEMESTRAL|TRIMESTRAL|BIMESTRAL|QUINCENAL|UNICO|ÚNICO)", flat)
        or _find_after(r"Forma\s+de\s+Pago\b", text, r"(MENSUAL|ANUAL|SEMESTRAL|TRIMESTRAL|BIMESTRAL|QUINCENAL|UNICO|ÚNICO)", window=200)
    )

    # Corrección: si forma_pago contiene moneda, moverla a 'moneda'
    if not item.get("moneda") and item.get("forma_pago") in {"SOLES", "DOLARES", "DÓLARES", "USD", "PEN"}:
        item["moneda"] = item["forma_pago"]
        item["forma_pago"] = None
    

    # Fecha de Emisión
    item["fecha_emision"] = (
        _find(r"Fecha\s+de\s+Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find(r"FECHA\s+EMISION\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )

    # Forma de pago / Último día pago (si aparecen)
    item["forma_pago"] = _find(r"Forma\s+de\s+Pago\s*:\s*(.+)", text)
    item["ultimo_dia_pago"] = _find(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Ramo: puede venir como “Actividad” o en el concepto
    item["ramo"] = (
        _find(r"Actividad\s*:\s*(.+)", text)
        or _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*[0-9]+\.?\s*(.+?)(?:\n|$)", text)
    )

    # Prima: tomar “Prima Comercial” o “Prima Resultante”
    prima_com = (
        _find(r"Prima\s+Comercial\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
        or _find(r"Prima\s+Resultante\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
        or _money(_find(r"Prima\s*Total\s*[:]*\s*([0-9\.,]+)", text))
    )
    item["prima_comercial"] = prima_com

    # Total + IGV (si corresponde)
    igv = _find(r"(?:Impuesto\s+Gral\.?\s+A\s+Las\s+Ventas|IGV)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    total = _find(r"(?:Importe\s+Total|Total)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    item["prima_comercial_igv"] = total

    return {k: _clean(v) for k, v in item.items() if v}