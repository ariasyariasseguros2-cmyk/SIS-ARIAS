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

def parse_crecer_vidaley_pocos_datos(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    
    # Normalización básica: saltos de línea pueden ser \n o \r\n
    # El usuario muestra campos que están en líneas separadas:
    # N° Póliza \n 810200000181629
    
    # 1. N° Póliza
    # Busca "N° Póliza" seguido opcionalmente de saltos de línea y luego el número
    item['numero_poliza'] = _find(r"N°\s*P[óo]liza\s*(?:[\r\n]+)?\s*([0-9]+)", text)
    
    # 2. Ramo
    item['ramo'] = _find(r"Ramo\s*(?:[\r\n]+)?\s*(.+)", text)
    if item['ramo']:
        # Limpiar prefijos numéricos ej "73. Vida Ley..."
        item['ramo'] = re.sub(r"^\d+\.\s*", "", item['ramo'])

    # 3. Moneda
    item['moneda'] = _find(r"Moneda\s*(?:[\r\n]+)?\s*([A-Za-z]+)", text)
    
    # 4. Vigencia (Inicio y Fin)
    # Inicio de Vigencia \n Desde las 00:00 horas del día 19/08/2025.
    item['inicio_vigencia'] = _find(r"Inicio de Vigencia\s*(?:[\r\n]+)?\s*.*?([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    
    # Fin de Vigencia \n Hasta las 24:00 horas del día 19/09/2025.
    item['vencimiento'] = _find(r"Fin de Vigencia\s*(?:[\r\n]+)?\s*.*?([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    
    # 5. Fecha de emisión: 10/10/2025
    item['fecha_emision'] = _find(r"Fecha de emisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    
    # 6. Prima comercial: S/ 100.00
    item['prima_comercial'] = _money(_find(r"Prima comercial\s*:?\s*S?/?\s*([0-9.,]+)", text))
    
    # 7. Prima Comercial + IGV: S/ 118.00
    item['prima_comercial_igv'] = _money(_find(r"Prima Comercial \+ IGV\s*:?\s*S?/?\s*([0-9.,]+)", text))
    
    # 8. Contratante / Razón Social
    # "Razón social \n MOTOINDUSTRIAS S.A.C"
    # Priorizar búsqueda bajo la sección "DATOS DEL CONTRATANTE" para evitar falsos positivos
    item['contratante'] = _find(r"DATOS DEL CONTRATANTE.*?Raz[oó]n social\s*(?:[\r\n]+)?\s*([^\r\n]+)", text, flags=re.IGNORECASE | re.DOTALL)
    
    if not item.get('contratante'):
        item['contratante'] = _find(r"Raz[oó]n social\s*(?:[\r\n]+)?\s*([^\r\n]+)", text)
    
    # Fallbacks / Derivados
    if item.get('contratante'):
        item['colectivo_asegurado'] = item['contratante']

    # Ultimo dia de pago
    # A veces es igual al vencimiento o se calcula
    if item.get('vencimiento') and not item.get('ultimo_dia_pago'):
        item['ultimo_dia_pago'] = item['vencimiento']
    
    print("item vida ley pocos datos", item)
    return {k: _clean(v) for k, v in item.items() if v}
