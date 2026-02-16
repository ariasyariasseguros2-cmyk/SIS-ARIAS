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

# NUEVO: fecha cercana a una etiqueta (busca después y antes)
def _find_date_near(label_pat: str, text: str, window_left: int = 160, window_right: int = 160, flags=re.IGNORECASE) -> Optional[str]:
    date_pat = r"([0-9]{2}/[0-9]{2}/[0-9]{4})"
    for m in re.finditer(label_pat, text, flags):
        right = text[m.end(): m.end() + window_right]
        rm = re.search(date_pat, right, flags)
        if rm:
            return rm.group(1).strip()
        left = text[max(0, m.start() - window_left): m.start()]
        lm = None
        # tomar la última fecha antes de la etiqueta
        for mm in re.finditer(date_pat, left, flags):
            lm = mm
        if lm:
            return lm.group(1).strip()
    return None

def parse_mapfre(text: str) -> Dict[str, str]:
    """
    Parser para PDFs Mapfre (incluye variantes EPS).
    Devuelve un dict que luego se normaliza a la UI en /upload.
    """
    item: Dict[str, str] = {}
    flat = _canon(text)  # texto sin saltos múltiples para patrones sencillos
    print("[parse_mapfre] texto normalizado:", flat)
    print("item", item)
    # Número de póliza: variantes con acento y sin
    # Regex ajustado para requerir al menos un dígito y evitar capturar palabras como "DE"
    item["numero_poliza"] = (
        _find(r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\s*:\s*([0-9A-Z\-]*\d[0-9A-Z\-]*)", text)
        or _find(r"P[ÓO]LIZA\s*:?\s*([0-9A-Z\-]*\d[0-9A-Z\-]*)", text)
        or _find(r"Poliza\s*:\s*([0-9A-Z\-]*\d[0-9A-Z\-]*)", text)
    )
    print("numero_poliza", item["numero_poliza"])

    # Fallback: algunos PDFs ponen el recibo en la misma línea que la póliza
    rec_from_header = _find(
        r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\s*:\s*[0-9A-Z\-]+\s+([0-9]{6,12})",
        flat,
    )

    rec_raw = (
        _find(r"\bRECIBO\W*(\d{5,})", flat)
        or _find(r"\bRecibo\W*(\d{5,})", flat)
        or _find(r"\bRECIBO\W*(\d{5,})", text)
        or _find_after(r"\bRECIBO\b", text, r"([0-9]{5,})", window=600)
        or _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*([0-9]{5,})", text)
        or rec_from_header
    )
    pos = flat.upper().find("RECIBO")
    if not rec_raw and pos != -1:
        # Buscar dígitos cerca de la palabra RECIBO por si el número queda "a la izquierda"
        window = flat[max(0, pos - 500): pos + 500]
        m = re.search(r"\b(\d{6,12})\b", window)
        if m:
            rec_raw = m.group(1)
    if rec_raw and item.get("numero_poliza") and rec_raw == item["numero_poliza"]:
        rec_raw = None
    if pos != -1:
        print("[parse_mapfre] contexto RECIBO:", flat[pos-60:pos+60])
    print("[parse_mapfre] RECIBO raw ->", rec_raw)
    item["recibo"] = _digits(rec_raw)

    # Colectivo Asegurado: tomar el texto entre la etiqueta y "Forma de Pago", 
    # luego elegir la última frase en MAYÚSCULAS sin dígitos (evita CONTRATANTE).
    cfrag = _find(r"Colectivo\s+Asegurado\s*:\s*(.+?)\s+Forma\s+de\s+Pago", flat)
    item["colectivo_asegurado"] = None
    if cfrag:
        caps = re.findall(r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]{4,}", cfrag)
        for cand in reversed(caps):
            if not re.search(r"\d", cand):
                item["colectivo_asegurado"] = cand.strip()
                break
    # Fallbacks si el bloque anterior no funciona
    if not item.get("colectivo_asegurado"):
        item["colectivo_asegurado"] = (
            _find(r"Colectivo\s+Asegurado\s*:\s*([A-ZÁÉÍÓÚÑ0-9 \-\.]+)", text)
            or _find_after(r"Actividad\s*:\s*", text, r"([A-ZÁÉÍÓÚÑ0-9 \-\.]{6,})", window=300)
        )
    print("colectivo_asegurado", item["colectivo_asegurado"])

    # Fechas: buscar cerca de cada etiqueta
    item["inicio_vigencia"] = (
        _find_date_near(r"Inicio\s+de\s+Vigencia\b", text, 160, 160)
        or _find_after(r"Inicio\s+de\s+Vigencia\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=160)
        or _find(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    print("inicio_vigencia", item["inicio_vigencia"])
    item["vencimiento"] = (
        _find_date_near(r"\bVencimiento\b", text, 160, 200)
        or _find_after(r"\bVencimiento\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=200)
        or _find(r"HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    item["vencimiento_aplicacion"] = (
        _find_date_near(r"Vencimiento\s+de\s+Aplicaci[oó]n\b", text, 160, 200)
        or _find_after(r"Vencimiento\s+de\s+Aplicaci[oó]n\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=200)
        or _find(r"Vencimiento\s+de\s+Aplicaci[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find(r"Vencimiento\s+de\s+Aplicaci[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", flat)
    )

    # Moneda
    item["moneda"] = (
        _find(r"\bMoneda\s*[:\-]?\s*(SOLES|DOLARES|DÓLARES|USD|PEN)", flat)
        or _find(r"\bMONEDA\s*[:\-]?\s*(SOLES|DOLARES|DÓLARES|USD|PEN)", flat)
        or _find_after(r"\bMoneda\b", text, r"(SOLES|DOLARES|DÓLARES|USD|PEN)", window=400)
        or _find_after(r"\bMONEDA\b", text, r"(SOLES|DOLARES|DÓLARES|USD|PEN)", window=400)
        or _find(r"\b(SOLES|DOLARES|DÓLARES|USD|PEN)\b", flat)
    )

    # Forma de Pago: solo valores válidos
    item["forma_pago"] = (
        _find(r"Forma\s+de\s+Pago\s*[:\-]?\s*(MENSUAL|ANUAL|SEMESTRAL|TRIMESTRAL|BIMESTRAL|QUINCENAL|UNICO|ÚNICO)", flat)
        or _find_after(r"Forma\s+de\s+Pago\b", text, r"(MENSUAL|ANUAL|SEMESTRAL|TRIMESTRAL|BIMESTRAL|QUINCENAL|UNICO|ÚNICO)", window=200)
    )
    if not item.get("moneda") and item.get("forma_pago") in {"SOLES", "DOLARES", "DÓLARES", "USD", "PEN"}:
        item["moneda"] = item["forma_pago"]
        item["forma_pago"] = None

    # Fecha de Emisión
    item["fecha_emision"] = (
        _find_date_near(r"Fecha\s+de\s+Emisi[oó]n\b", text, 160, 160)
        or _find_after(r"Fecha\s+de\s+Emisi[oó]n\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
        or _find(r"FECHA\s+EMISION\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )

    # Último día de pago: SOLO fecha a la derecha de la etiqueta (evitar tomar la izquierda)
    item["ultimo_dia_pago"] = (
        _find_after(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
        or _find(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", flat)
    )
    print("ultimo_dia_pago", item["ultimo_dia_pago"])

    # Ramo: código + descripción aunque el valor quede lejos de la etiqueta
    item["ramo"] = (
        _find_after(r"Actividad\s*:\s*", text, r"([0-9]{4,6}\s*-\s*[A-Z0-9\.\- ,]+)", window=400)
        or _find(r"Actividad\s*:\s*([0-9]{4,6}\s*-\s*[A-Z0-9\.\- ,]+)", flat)
        or _find(r"(?:Ct\s*)?Cancelaci[oó]n\s+Recibo\s*[0-9]+\.?\s*(.+?)(?:\n|$)", text)
    )

    # Normalizar ramo/producto para SCTR (Pensión/Salud)
    ramo_main = None
    ramos_producto = None
    t_low = flat.lower()
    if "seguro complementario de trabajo de riesgo" in t_low or "sctr" in t_low:
        ramo_main = "SCTR"
        if "pension" in t_low or "pensiones" in t_low:
            ramos_producto = "Pensión"
        elif "salud" in t_low or "eps" in t_low:
            ramos_producto = "Salud"
    if ramo_main:
        item["ramo"] = ramo_main
    if ramos_producto:
        item["ramos_producto"] = ramos_producto

    # Prima
    # NUEVO: primero intentar "Prima Comercial + IGV"
    prima_com_igv = _find(r"Prima\s+Comercial\s*\+\s*IGV\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    prima_com = (
        prima_com_igv
        or _find(r"Prima\s+Comercial\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
        or _find(r"Prima\s+Resultante\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
        or _money(_find(r"Prima\s*Total\s*[:]*\s*([0-9\.,]+)", text))
    )
    item["prima_comercial"] = prima_com

    # Total + IGV
    igv = _find(r"(?:Impuesto\s+Gral\.?\s+A\s+Las\s+Ventas|IGV)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    total = _find(r"(?:Importe\s+Total|Total)\s*[:]*\s*S?\/?\s*([0-9\.,]+)", text)
    # NUEVO: guardar "Prima Comercial + IGV" si existe, en 'prima_comercial_igv'
    item["prima_comercial_igv"] = prima_com_igv or total

    # Heurísticas para corregir inversiones de fechas
    def _as_date(s: Optional[str]) -> Optional[tuple]:
        if not s: return None
        try:
            d, m, y = s.split('/')
            return (int(y), int(m), int(d))
        except Exception:
            return None

    # Normalizar las tres fechas de la columna derecha (UDP, VA, V) por orden cronológico
    _right_dates = {
        "ultimo_dia_pago": item.get("ultimo_dia_pago"),
        "vencimiento_aplicacion": item.get("vencimiento_aplicacion"),
        "vencimiento": item.get("vencimiento"),
    }
    _valid = [(k, v, _as_date(v)) for k, v in _right_dates.items() if _as_date(v)]
    # Nota: se mantiene la normalización original, sin forzar 'vencimiento' a la última fecha
    if len({v for _, v, _ in _valid}) >= 2:
        _ordered = sorted(_valid, key=lambda t: t[2])  # ascendente
        item["ultimo_dia_pago"] = _ordered[0][1]
        if len(_ordered) == 2:
            item["vencimiento"] = _ordered[1][1]
        else:
            item["vencimiento_aplicacion"] = _ordered[1][1]
            item["vencimiento"] = _ordered[2][1]
        print("[parse_mapfre] fechas normalizadas ->",
              "UD:", item["ultimo_dia_pago"],
              "VA:", item.get("vencimiento_aplicacion"),
              "V:", item["vencimiento"])

    # Mantener corrección emisión/vigencia si vienen cruzadas
    iv = _as_date(item.get("inicio_vigencia"))
    fe = _as_date(item.get("fecha_emision"))
    if iv and fe and fe < iv:
        item["inicio_vigencia"], item["fecha_emision"] = item["fecha_emision"], item["inicio_vigencia"]

    v  = _as_date(item.get("vencimiento"))
    ud = _as_date(item.get("ultimo_dia_pago"))
    va = _as_date(item.get("vencimiento_aplicacion"))
    if v and ud and ud > v:
        # intercambiar si quedaron cruzados
        item["vencimiento"], item["ultimo_dia_pago"] = item["ultimo_dia_pago"], item["vencimiento"]
        print("vencimiento", item["vencimiento"],"ultimo_dia_pago", item["ultimo_dia_pago"], "vencimiento_aplicacion", item["vencimiento_aplicacion"])
        v, ud = ud, v
    # Regla Mapfre EPS: si Último Día >= Vencimiento (o igual) y hay Venc. de Aplicación menor, usarlo
    if v and va and (not ud or ud >= v or ud == v) and va < v:
        item["ultimo_dia_pago"] = item.get("vencimiento_aplicacion")
        print("ultimo_dia_pago", item["vencimiento_aplicacion"])
    # NUEVO: duplicar 'vencimiento' como 'fecha_vecimiento' para la UI
    item["fecha_vecimiento"] = item.get("vencimiento")

    # Extraer RUC del cliente
    # Prioridad 1: Etiqueta explícita "RUC" seguida de un número
    ruc_candidato = _find(r"RUC\s*[:]?\s*(\d{11})", text)
    
    # Prioridad 2: Buscar cualquier RUC (11 dígitos, empieza con 10 o 20) si no se halló
    if not ruc_candidato:
        candidates_ruc = re.findall(r"\b(10\d{9}|20\d{9})\b", text)
        if candidates_ruc:
            # Mapfre suele poner su propio RUC (20202380621) en el pie de página o encabezado, filtrarlo
            for cand in candidates_ruc: 
                    ruc_candidato = cand
                    break
                    
    item["numero_documento_extracted"] = ruc_candidato

    return {k: _clean(v) for k, v in item.items() if v}
