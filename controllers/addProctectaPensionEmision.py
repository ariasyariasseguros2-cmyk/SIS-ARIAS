import re
from typing import Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def parse_protecta_pension_emision(text: str) -> Dict[str, str]:
    """
    Parsea el texto extraído del PDF de Protecta Pensión Emisión.
    """
    
    # Prima Comercial
    # Ejemplo: PRIMA COMERCIAL: \n S/. 122.04
    prima_comercial = _find(r"PRIMA COMERCIAL:\s*(?:S/\.)?\s*([\d\.,]+)", text)
    
    # Prima Comercial Total
    # Ejemplo: PRIMA COMERCIAL TOTAL: \n S/. 144.01
    prima_total = _find(r"PRIMA COMERCIAL TOTAL:\s*(?:S/\.)?\s*([\d\.,]+)", text)
    
    # Póliza No.
    # Ejemplo: Póliza No.:   4000009113
    poliza = _find(r"Póliza No\.:\s*(\d+)", text)
    
    # Moneda del Contrato
    # Ejemplo: Moneda del Contrato:  Soles
    moneda = _find(r"Moneda del Contrato:\s*(\w+)", text)
    
    # Fecha de Emisión
    # Ejemplo: Fecha de Emisión:    30/08/2025
    # También puede aparecer como "Fecha de Renovación" en renovaciones
    fecha_emision = _find(r"Fecha de Emisi[oó]n:\s*(\d{2}/\d{2}/\d{4})", text)
    if not fecha_emision:
         fecha_emision = _find(r"Fecha de Renovaci[oó]n:\s*(\d{2}/\d{2}/\d{4})", text)
    if not fecha_emision:
         # Fallback: buscar fecha sola si está cerca de "Lugar y Fecha"
         fecha_emision = _find(r"Lugar y Fecha.*?\s(\d{2}/\d{2}/\d{4})", text)
    
    # Vigencia de la Cobertura
    # Ejemplo: Vigencia de la Cobertura:  Desde: 01/09/2025 \n Hasta: 30/09/2025
    inicio_vigencia = _find(r"Vigencia de la Cobertura:.*?Desde:\s*(\d{2}/\d{2}/\d{4})", text)
    vencimiento = _find(r"Hasta:\s*(\d{2}/\d{2}/\d{4})", text)
    
    # Asegurados
    # Ejemplo: Asegurados: Trabajadores del Contratante declarados y \n registrados mensualmente a Protecta Security.
    asegurados = _find(r"Asegurados:\s*(.*?)(?=\n\s*\n|3\.|2\.|DATOS|$)", text)
    if asegurados:
        asegurados = re.sub(r'\s+', ' ', asegurados).strip()

    # Contratante y RUC
    # Buscamos el RUC que aparece después de la etiqueta "Contratante:"
    ruc_contratante = _find(r"Contratante:.*?(?:Ruc|RUC):\s*(\d{11})", text)
    nombre_contratante = _find(r"Contratante:\s*(.*?)\n", text)

    return {
        "prima_comercial": _clean(prima_comercial),
        "prima_total": _clean(prima_total),
        "numero_poliza": _clean(poliza),
        "moneda": _clean(moneda),
        "fecha_emision": _clean(fecha_emision),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),
        "colectivo_asegurado": _clean(asegurados),
        "ramo": "SCTR PENSIÓN",
        "numero_documento_extracted": _clean(ruc_contratante),
        "contratante": _clean(nombre_contratante)
    }

