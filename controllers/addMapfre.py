import re
from datetime import datetime, timedelta
from typing import Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
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
    cfrag = _find(r"Colectivo\s+Asegurado\s*:?\s*(.+?)\s+Forma\s+de\s+Pago", flat)
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
            _find(r"Colectivo\s+Asegurado\s*:?\s*([A-ZÁÉÍÓÚÑ0-9 \-\.]+)", text)
            or _find_after(r"Colectivo\s+Asegurado\b", text, r"([A-ZÁÉÍÓÚÑ0-9 \-\.]{6,})", window=220)
            or _find_after(r"Actividad\s*:\s*", text, r"([A-ZÁÉÍÓÚÑ0-9 \-\.]{6,})", window=300)
        )
    print("colectivo_asegurado", item["colectivo_asegurado"])

    # ============================================================
    # BLOQUE DE FECHAS: multi-estrategia (del MÁS FIABLE al MENOS)
    # ============================================================
    DATE_RE = re.compile(r"([0-9]{2}/[0-9]{2}/[0-9]{4})")

    # -------- MÉTODO -1: LÍNEA POR LÍNEA (el más fiable para formularios) --------
    # Itera sobre cada línea (o 2 líneas juntas) y busca etiqueta + fecha.
    # El extractor de PDF típico mantiene filas lógicas como líneas individuales.
    LABEL_LINE_PATTERNS = [
        # (campo, regex_etiqueta)  — la regex NO incluye el valor, solo la etiqueta
        ("inicio_vigencia_aplicacion",
         re.compile(r"Inicio\s+de\s+Vigencia\s+Aplicaci[oó]n", re.I)),
        ("vencimiento_aplicacion",
         re.compile(r"Vencimiento\s+de\s+Aplicaci[oó]n", re.I)),
        ("inicio_vigencia",
         re.compile(r"Inicio\s+de\s+Vigencia\b(?!\s+Aplicaci)", re.I)),
        ("vencimiento",
         re.compile(r"\bVencimiento\b(?!\s+de\s+Aplicaci)", re.I)),
        ("ultimo_dia_pago",
         re.compile(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago", re.I)),
        ("fecha_emision",
         re.compile(r"Fecha\s+de\s+Emisi[oó]n", re.I)),
    ]
    _lines = text.splitlines()
    _dates_by_line = {}
    for i, raw_line in enumerate(_lines):
        line = _canon(raw_line)
        if not line:
            continue
        # Probar 1 línea sola, luego línea + siguiente (para valores que saltan)
        fragments = [line]
        if i + 1 < len(_lines):
            fragments.append(line + " " + _canon(_lines[i + 1]))
        for frag in fragments:
            for field_name, label_re in LABEL_LINE_PATTERNS:
                if field_name in _dates_by_line:
                    continue
                if label_re.search(frag):
                    dm = DATE_RE.search(frag)
                    if dm:
                        _dates_by_line[field_name] = dm.group(1)
                        print(f"[debug-m-1] {field_name} = {_dates_by_line[field_name]} (línea {i+1})")
                        break  # ya encontramos este field, no seguir con otros patterns en esta frag
    print("[debug-m-1] resumen método por línea:", _dates_by_line)

    # -------- MÉTODO 0: búsqueda EXPLÍCITA etiqueta : fecha --------
    _explicit_patterns = [
        ("inicio_vigencia_aplicacion",
         [r"Inicio\s+de\s+Vigencia\s+Aplicaci[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"]),
        ("vencimiento_aplicacion",
         [r"Vencimiento\s+de\s+Aplicaci[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"]),
        ("inicio_vigencia",
         [r"Inicio\s+de\s+Vigencia\b(?!\s+Aplicaci)[^:]*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"]),
        ("vencimiento",
         [r"\bVencimiento\b(?!\s+de\s+Aplicaci)[^:]*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"]),
        ("ultimo_dia_pago",
         [r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago[^:]*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"]),
        ("fecha_emision",
         [r"Fecha\s+de\s+Emisi[oó]n[^:]*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})"]),
    ]
    _dates_explicit = {}
    for field_name, pats in _explicit_patterns:
        for pat in pats:
            m = re.search(pat, flat, re.I)
            if not m:
                m = re.search(pat, text, re.I)
            if m:
                _dates_explicit[field_name] = m.group(1).strip()
                print(f"[debug-m0] {field_name} = {_dates_explicit[field_name]} (explícito :)")
                break
    print("[debug-m0] resumen método explícito:", _dates_explicit)

    # -------- MÉTODO 1: extraer TODAS las fechas + TODAS las etiquetas por POSICIÓN --------
    all_dates = [(m.start(), m.group(1)) for m in DATE_RE.finditer(flat)]
    print("[debug-fechas] TODAS las fechas en flat (pos, valor):", all_dates)

    LABELS = [
        ("inicio_vigencia_aplicacion",   re.compile(r"Inicio\s+de\s+Vigencia\s+Aplicaci[oó]n", re.I)),
        ("vencimiento_aplicacion",       re.compile(r"Vencimiento\s+de\s+Aplicaci[oó]n", re.I)),
        ("inicio_vigencia",              re.compile(r"Inicio\s+de\s+Vigencia\b(?!\s+Aplicaci)", re.I)),
        ("vencimiento",                  re.compile(r"\bVencimiento\b(?!\s+de\s+Aplicaci)", re.I)),
        ("ultimo_dia_pago",              re.compile(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago", re.I)),
        ("fecha_emision",                re.compile(r"Fecha\s+de\s+Emisi[oó]n", re.I)),
    ]

    label_occurrences = []
    for field_name, pat in LABELS:
        for m in pat.finditer(flat):
            label_occurrences.append((m.end(), field_name, m.group(0)))
    label_occurrences.sort(key=lambda x: x[0])
    print("[debug-fechas] etiquetas encontradas (pos_fin, campo, match):", label_occurrences)

    used_date_idx = set()
    _dates_by_pos = {}
    for lab_end, field_name, lab_match in label_occurrences:
        ctx = flat[max(0, lab_end - 80): lab_end + 120]
        print(f"[debug-etiqueta] campo={field_name} | pos_fin={lab_end} | contexto: {ctx!r}")
        best_idx = None
        best_dist = None
        for idx, (d_pos, d_val) in enumerate(all_dates):
            if idx in used_date_idx:
                continue
            if d_pos < lab_end:
                continue
            dist = d_pos - lab_end
            if dist <= 600 and (best_dist is None or dist < best_dist):
                best_dist = dist
                best_idx = idx
        if best_idx is not None:
            used_date_idx.add(best_idx)
            _dates_by_pos[field_name] = all_dates[best_idx][1]
            print(f"[debug-fechas]   ✓ asignado a {field_name}: {_dates_by_pos[field_name]} (dist={best_dist})")
        else:
            print(f"[debug-fechas]   ✗ NO se encontró fecha para {field_name}")
    print("[debug-m1] resumen método por posición:", _dates_by_pos)

    # -------- COMBINAR MÉTODOS: MÉTODO -1 > MÉTODO 0 > MÉTODO 1 > fallbacks --------
    _all_fields = ["inicio_vigencia_aplicacion","vencimiento_aplicacion",
                   "inicio_vigencia","vencimiento","ultimo_dia_pago","fecha_emision"]
    _dates_combined = {}
    for fn in _all_fields:
        _dates_combined[fn] = (
            _dates_by_line.get(fn)
            or _dates_explicit.get(fn)
            or _dates_by_pos.get(fn)
        )
    print("[debug-combinado] final pre-fallbacks:", _dates_combined)

    # Aplicar valores combinados
    item["inicio_vigencia_aplicacion"] = _dates_combined["inicio_vigencia_aplicacion"]
    item["vencimiento_aplicacion"]    = _dates_combined["vencimiento_aplicacion"]
    item["inicio_vigencia"]           = _dates_combined["inicio_vigencia"]
    item["vencimiento"]               = _dates_combined["vencimiento"]
    item["ultimo_dia_pago"]           = _dates_combined["ultimo_dia_pago"]
    item["fecha_emision"]             = _dates_combined["fecha_emision"]

    # --- FALLBACKS antiguos si alguno quedó None ---
    if not item.get("inicio_vigencia"):
        item["inicio_vigencia"] = (
            _find_date_near(r"Inicio\s+de\s+Vigencia\b(?!\s+Aplicaci)", text, 160, 160)
            or _find_after(r"Inicio\s+de\s+Vigencia\b(?!\s+Aplicaci)", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=160)
            or _find(r"DESDE\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        )
    print("inicio_vigencia", item["inicio_vigencia"])

    _iva_pat_label = r"Inicio\s+de\s+Vigencia\s+Aplicaci[oó]n"
    if not item.get("inicio_vigencia_aplicacion"):
        item["inicio_vigencia_aplicacion"] = (
            _find_date_near(_iva_pat_label + r"\b", text, 200, 200)
            or _find_after(_iva_pat_label + r"\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=250)
            or _find_after(_iva_pat_label + r"\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=250)
        )
    print("inicio_vigencia_aplicacion", item["inicio_vigencia_aplicacion"])

    if not item.get("vencimiento"):
        item["vencimiento"] = (
            _find_date_near(r"\bVencimiento\b(?!\s+de\s+Aplicaci)", text, 160, 200)
            or _find_after(r"\bVencimiento\b(?!\s+de\s+Aplicaci)", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=200)
            or _find(r"HASTA\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        )
    print("vencimiento", item["vencimiento"])

    _va_pat_label = r"Vencimiento\s+de\s+Aplicaci[oó]n"
    if not item.get("vencimiento_aplicacion"):
        item["vencimiento_aplicacion"] = (
            _find_date_near(_va_pat_label + r"\b", text, 200, 200)
            or _find_after(_va_pat_label + r"\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=250)
            or _find_after(_va_pat_label + r"\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=250)
        )
    print("vencimiento_aplicacion", item["vencimiento_aplicacion"])

    if not item.get("fecha_emision"):
        item["fecha_emision"] = (
            _find_date_near(r"Fecha\s+de\s+Emisi[oó]n\b", text, 160, 160)
            or _find_after(r"Fecha\s+de\s+Emisi[oó]n\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
            or _find(r"FECHA\s+EMISION\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
            or _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        )

    if not item.get("ultimo_dia_pago"):
        item["ultimo_dia_pago"] = (
            _find_after(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago\b", text, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
            or _find(r"[ÚU]ltimo\s+d[ií]a\s+de\s+Pago\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", flat)
        )
    print("ultimo_dia_pago", item["ultimo_dia_pago"])
    print("fecha_emision", item["fecha_emision"])

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
    # Prima:
    # - Algunos PDFs/OCR traen "Prima Comercial + IGV"
    # - Otros solo "Prima Comercial +"
    # - En ciertos casos el OCR invierte los importes entre ambas etiquetas
    prima_com_igv = (
        _find(r"Prima\s+Comercial\s*\+\s*I\s*G\s*V\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", flat)
        or _find(r"Prima\s+Comercial\s*\+\s*IGV\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
        or _find(r"Prima\s+Comercial\s*\+\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
        or _find(r"Prima\s+Comercial\s*\+\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", flat)
    )
    prima_com = (
        _find(r"Prima\s+Comercial(?!\s*\+)\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
        or _find(r"Prima\s+Comercial(?!\s*\+)\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", flat)
        or _find(r"Prima\s+Resultante\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
        or _money(_find(r"Prima\s*Total\s*[:]*\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text))
    )

    try:
        pc_val = float(str(prima_com).replace(',', '.')) if prima_com else None
        pigv_val = float(str(prima_com_igv).replace(',', '.')) if prima_com_igv else None
        if pc_val is not None and pigv_val is not None and pigv_val < pc_val:
            prima_com, prima_com_igv = prima_com_igv, prima_com
    except Exception:
        pass

    item["prima_comercial"] = prima_com

    # Total + IGV
    igv = _find(r"(?:Impuesto\s+Gral\.?\s+A\s+Las\s+Ventas|IGV)\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
    total = _find(r"(?:Importe\s+Total|Total)\s*[:]*\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", text)
    # Guardar "Prima Comercial + IGV" si existe, en 'prima_comercial_igv'
    item["prima_comercial_igv"] = prima_com_igv or total

    # ============================================================
    # HEURÍSTICAS SUAVES: solo corregir inversiones OBVIAS
    # NO reordenar ciegamente por cronología
    # ============================================================
    def _as_date(s: Optional[str]) -> Optional[tuple]:
        if not s: return None
        try:
            d, m, y = s.split('/')
            return (int(y), int(m), int(d))
        except Exception:
            return None

    print("[heurísticas] valores ENTRADA:",
          "iv:", item.get("inicio_vigencia"),
          "iva:", item.get("inicio_vigencia_aplicacion"),
          "v:", item.get("vencimiento"),
          "va:", item.get("vencimiento_aplicacion"),
          "ud:", item.get("ultimo_dia_pago"),
          "fe:", item.get("fecha_emision"))

    # --- 1) IV/FE: Swap solo si inicio_vigencia es ANTES que fecha_emisión y no hay IVA ---
    iv  = _as_date(item.get("inicio_vigencia"))
    fe  = _as_date(item.get("fecha_emision"))
    iva = _as_date(item.get("inicio_vigencia_aplicacion"))
    if (not iva) and iv and fe and iv < fe:
        item["inicio_vigencia"], item["fecha_emision"] = item["fecha_emision"], item["inicio_vigencia"]
        print("[heurísticas] swap iv/fe -> iv:", item["inicio_vigencia"], "fe:", item["fecha_emision"])

    # --- 2) V/UDP: Swap solo si UDP es MAYOR que V y no hay VA que esté en medio ---
    v  = _as_date(item.get("vencimiento"))
    ud = _as_date(item.get("ultimo_dia_pago"))
    va = _as_date(item.get("vencimiento_aplicacion"))
    # Solo intercambiar si no hay vencimiento_aplicacion, ya que si existe:
    # cronológicamente UD < VA < V lo normal
    if (not va) and v and ud and ud > v:
        item["vencimiento"], item["ultimo_dia_pago"] = item["ultimo_dia_pago"], item["vencimiento"]
        v, ud = ud, v
        print("[heurísticas] swap v/ud -> v:", item["vencimiento"], "ud:", item["ultimo_dia_pago"])

    # --- 3) Regla EPS: si UDP >= V y existe VA < V, usar VA como UDP ---
    if v and va and (not ud or ud >= v) and va < v:
        item["ultimo_dia_pago"] = item.get("vencimiento_aplicacion")
        print("[heurísticas] ud <- va:", item["vencimiento_aplicacion"])

    # --- 4) SOBREESCRITURA: solo IV = IVA (el usuario quiere la fecha Aplicación) ---
    #    ¡NO sobreescribir V con VA! para no perder la fecha fin 01/11/2026
    print("[antes-sobreescritura] iv:", item.get("inicio_vigencia"), "iva:", item.get("inicio_vigencia_aplicacion"))
    print("[antes-sobreescritura] v:",  item.get("vencimiento"),       "va:",  item.get("vencimiento_aplicacion"))

    if item.get("inicio_vigencia_aplicacion"):
        item["inicio_vigencia"] = item["inicio_vigencia_aplicacion"]
        print("[sobreescritura] iv = iva ->", item["inicio_vigencia"])
    # V NO se sobreescribe con VA

    print("[heurísticas] valores SALIDA:",
          "iv:", item.get("inicio_vigencia"),
          "iva:", item.get("inicio_vigencia_aplicacion"),
          "v:", item.get("vencimiento"),
          "va:", item.get("vencimiento_aplicacion"),
          "ud:", item.get("ultimo_dia_pago"),
          "fe:", item.get("fecha_emision"))

    # Fecha Vencimiento UI: priorizar Último Día de Pago, luego emisión+15, luego fin vigencia
    item["fecha_vecimiento"] = item.get("ultimo_dia_pago")
    if not item.get("fecha_vecimiento") and item.get("fecha_emision"):
        try:
            d = datetime.strptime(item["fecha_emision"], "%d/%m/%Y").date()
            d2 = d + timedelta(days=15)
            item["fecha_vecimiento"] = d2.strftime("%d/%m/%Y")
        except Exception:
            pass
    if not item.get("fecha_vecimiento"):
        item["fecha_vecimiento"] = item.get("vencimiento")
    # También poblar fecha_vencimiento (mismo propósito, usado por route.py como explícito)
    if item.get("ultimo_dia_pago"):
        item["fecha_vencimiento"] = item["ultimo_dia_pago"]
    elif not item.get("fecha_vencimiento"):
        item["fecha_vencimiento"] = item.get("fecha_vecimiento")

    # Extraer RUC del cliente
    # Prioridad 1: Etiqueta explícita "RUC" seguida de un número
    ruc_candidato = _find(r"RUC\s*[:]?\s*(\d{11})", text)
    
    # Prioridad 2: Buscar cualquier RUC (11 dígitos, empieza con 10 o 20) si no se halló
    if not ruc_candidato:
        candidates_ruc = re.findall(r"\b(10\d{9}|20\d{9})\b", text)
        if candidates_ruc:
            # Mapfre suele poner su propio RUC en el pie de página o encabezado, filtrarlo
            for cand in candidates_ruc: 
                    ruc_candidato = cand
                    break
                    
    item["numero_documento_extracted"] = ruc_candidato

    # Debug final: TODOS los campos relevantes de fechas
    _final = {
        "inicio_vigencia": item.get("inicio_vigencia"),
        "inicio_vigencia_aplicacion": item.get("inicio_vigencia_aplicacion"),
        "vencimiento": item.get("vencimiento"),
        "vencimiento_aplicacion": item.get("vencimiento_aplicacion"),
        "ultimo_dia_pago": item.get("ultimo_dia_pago"),
        "fecha_emision": item.get("fecha_emision"),
        "fecha_vecimiento": item.get("fecha_vecimiento"),
        "fecha_vencimiento": item.get("fecha_vencimiento"),
    }
    print("[FINAL] fechas retornadas:", _final)

    return {k: _clean(v) for k, v in item.items() if v}
