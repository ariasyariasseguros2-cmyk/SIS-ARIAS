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

def _date_if_numeric(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    if re.fullmatch(r"(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4}", s):
        return s
    return None

def parse_crecer_vidaley_pocos_datos(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    
    # Normalización básica: saltos de línea pueden ser \n o \r\n
    # El usuario muestra campos que están en líneas separadas:
    # N° Póliza \n 810200000181629
    
    # 1. N° Póliza / Póliza N°
    poliza_raw = _find(
        r"(?:N[°ºo\.]?\s*P[óo]liza|P[óo]liza\s*N[°ºo\.]?)\s*(?:[\r\n]+)?\s*([0-9]{6,20}(?:-[A-Z0-9]+)*)",
        text,
    )
    if poliza_raw:
        m_base = re.match(r"(\d{6,20})", poliza_raw)
        base = m_base.group(1) if m_base else poliza_raw
        item["numero_poliza"] = base
        if poliza_raw != base:
            item["nro"] = poliza_raw
    
    # 2. Ramo
    item['ramo'] = _find(r"Ramo\s*(?:[\r\n]+)?\s*(.+)", text)
    if item['ramo']:
        # Limpiar prefijos numéricos ej "73. Vida Ley..."
        item['ramo'] = re.sub(r"^\d+\.\s*", "", item['ramo'])

    ramo_main = None
    ramos_producto: Optional[str] = None
    t_low = text.lower()
    if "vida ley" in t_low:
        ramo_main = "VIDA - LEY"
        if "trabajador" in t_low or "trabajadores" in t_low:
            ramos_producto = "OBRERO"
        elif "empleado" in t_low or "empleados" in t_low:
            ramos_producto = "EMPLEADOS"
    if ramo_main:
        item["ramo"] = ramo_main
    if ramos_producto:
        item["ramos_producto"] = ramos_producto

    # 3. Moneda
    item['moneda'] = _find(r"Moneda\s*(?:[\r\n]+)?\s*([A-Za-z]+)", text)
    
    # 4. Vigencia (Inicio y Fin)
    DATE_RE = r"\b([0-9]{2}/[0-9]{2}/[0-9]{4})\b"

    def _parse_ddmmyyyy(date_str: str):
        try:
            from datetime import datetime
            return datetime.strptime(date_str.strip(), "%d/%m/%Y")
        except Exception:
            return None

    candidates = []

    def _push_candidate(d1: str, d2: str, weight: int):
        dt1, dt2 = _parse_ddmmyyyy(d1), _parse_ddmmyyyy(d2)
        if not dt1 or not dt2:
            return
        delta = (dt2 - dt1).days
        if dt2 < dt1:
            return
        if not (0 <= delta <= 370):
            return
        score = weight
        if dt1.year >= 2015:
            score += 10
        if dt2.year >= 2015:
            score += 10
        candidates.append((score, d1, d2))

    pat_strict = rf"\bVigencia\b\s*[:：]?\s*(?:desde|del)\s*{DATE_RE}\s*[–\-]\s*(?:hasta|al)\s*{DATE_RE}"
    pat_loose = rf"\bVigencia\b\s*[:：]?\s*(?:desde|del)\s*{DATE_RE}[\s\S]{{0,40}}?\b(?:hasta|al)\b[\s:：]{{0,6}}{DATE_RE}"

    for m in re.finditer(pat_strict, text, re.IGNORECASE):
        _push_candidate(m.group(1), m.group(2), 40)
    for m in re.finditer(pat_loose, text, re.IGNORECASE | re.DOTALL):
        _push_candidate(m.group(1), m.group(2), 25)

    if not candidates:
        for m in re.finditer(r"\bVigencia\b\s*[:：]", text, re.IGNORECASE):
            frag = text[m.end(): m.end() + 220]
            dates = re.findall(DATE_RE, frag)
            if len(dates) >= 2:
                _push_candidate(dates[0], dates[1], 10)

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        item["inicio_vigencia"], item["vencimiento"] = candidates[0][1], candidates[0][2]
    else:
        item['inicio_vigencia'] = _find(
            r"Inicio de Vigencia\s*(?:[\r\n]+)?\s*.*?([0-9]{2}/[0-9]{2}/[0-9]{4})",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        item['vencimiento'] = _find(
            r"(?:Fin|T[eé]rmino)\s+de\s+Vigencia\s*(?:[\r\n]+)?\s*.*?([0-9]{2}/[0-9]{2}/[0-9]{4})",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    
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

    def _add_days_ddmmyyyy(date_str: Optional[str], days: int) -> Optional[str]:
        try:
            if not date_str:
                return None
            from datetime import datetime, timedelta
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    item['inicio_vigencia'] = _date_if_numeric(item.get('inicio_vigencia'))
    item['vencimiento'] = _date_if_numeric(item.get('vencimiento'))
    item['fecha_emision'] = _date_if_numeric(item.get('fecha_emision'))
    item['ultimo_dia_pago'] = _date_if_numeric(item.get('ultimo_dia_pago'))

    if item.get("fecha_emision"):
        due = _add_days_ddmmyyyy(item.get("fecha_emision"), 30)
        if due:
            if not item.get("fecha_vencimiento"):
                item["fecha_vencimiento"] = due
            if not item.get("ultimo_dia_pago") or item.get("ultimo_dia_pago") == item.get("vencimiento"):
                item["ultimo_dia_pago"] = due
    item["fecha_vencimiento"] = _date_if_numeric(item.get("fecha_vencimiento"))
    
    print("item vida ley pocos datos", item)
    return {k: _clean(v) for k, v in item.items() if v}
