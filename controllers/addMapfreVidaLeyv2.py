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
    m = re.search(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)", raw)
    tok = (m.group(1).strip() if m else raw)
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

def _canon(text: str) -> str:
    return re.sub(r"\s+", " ", text)

def _find_after(label_pat: str, text: str, value_pat: str, window: int = 2000, flags=re.IGNORECASE) -> Optional[str]:
    for m in re.finditer(label_pat, text, flags):
        frag = text[m.end(): m.end() + window]
        vm = re.search(value_pat, frag, flags)
        if vm:
            return vm.group(1).strip()
    return None

def _between(start_pat: str, end_pat: str, text: str, flags=re.IGNORECASE, window: int = 2000) -> Optional[str]:
    m_start = re.search(start_pat, text, flags)
    if not m_start:
        return None
    frag = text[m_start.end(): m_start.end() + window]
    m_end = re.search(end_pat, frag, flags)
    return _clean(frag[:m_end.start()] if m_end else frag)

def _only_company(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"((?!(?:DE|OTRAS|ACTIVIDADES)\b)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 \.&']{2,}?(?:S\.?A\.?C?|S\.?R\.?L|SRL|SAC|SA|EIRL))\b", s, re.IGNORECASE)
    return m.group(1).strip() if m else s.strip()

def parse_mapfre_vidaley_v2(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    flat = _canon(text)
    date_pat = r"([0-9]{2}/[0-9]{2}/[0-9]{4})"

    def _extract_stream(flat_text: str) -> Dict[str, Optional[str]]:
        out: Dict[str, Optional[str]] = {}
        run = re.search(r"(?:\s*:\s*){10,}", flat_text)
        if not run:
            return out
        values = flat_text[run.end():]
        pos = 0
        def take(pat: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
            nonlocal pos
            mm = re.search(pat, values[pos:], flags)
            if not mm:
                return None
            pos += mm.end()
            return mm.group(1).strip()
        COMPANY  = r"((?!(?:DE|OTRAS|ACTIVIDADES)\b)[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.&']{2,}?(?:S\.?A\.?C?|S\.?R\.?L|SRL|SAC|SA|EIRL))"
        ADDRESS  = r"([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9 \.\-]+?)\s+(?=\d{4,6}\s*-\s)"
        ACTIVITY = r"(\d{4,6}\s*-\s+[A-Z0-9ÁÉÍÓÚÑ \.\-]+?)\s+(?=[A-ZÁÉÍÓÚÑ])"
        DATE     = r"([0-9]{2}/[0-9]{2}/[0-9]{4})"
        CURR     = r"\b(SOLES|USD|PEN|DOLARES|D[ÓO]LARES)\b"
        MONEY    = r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?)"
        poliza      = take(r"\b(\d{8,14})\b")
        recibo      = take(r"\b(\d{6,12})\b")
        contratante = take(COMPANY)
        ruc         = take(r"\b(\d{8,11})\b")
        direccion   = take(ADDRESS)
        actividad   = take(ACTIVITY)
        colectivo   = take(rf"{COMPANY}\s+(?={DATE})")
        iv          = take(DATE)
        v           = take(DATE)
        iva         = take(DATE)
        va          = take(DATE)
        mon         = take(CURR)
        fe          = take(DATE)
        udp         = take(DATE)
        prima_res   = take(MONEY)
        out.update({
            "numero_poliza": poliza,
            "recibo": recibo,
            "contratante": contratante,
            "ruc": ruc,
            "direccion": direccion,
            "actividad": actividad,
            "colectivo_asegurado": colectivo,
            "inicio_vigencia": iv,
            "vencimiento": v,
            "inicio_vigencia_aplicacion": iva,
            "vencimiento_aplicacion": va,
            "moneda": mon,
            "fecha_emision": fe,
            "ultimo_dia_pago": udp,
            "prima_resultante": prima_res,
        })
        return out

    cond = _extract_stream(flat)

    item["numero_poliza"] = (
        _find(r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\s*:\s*([0-9]{6,15})", flat)
        or cond.get("numero_poliza")
        or _find_after(r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\b", flat, r"([0-9]{6,15})", window=4000)
    )

    # RECIBO: no confiar en el stream cuando el OCR dejó "RECIBO :" sin número (termina capturando Monto Base 245064.00)
    rec_raw = _find(r"\bRECIBO\s*:\s*(\d{6,12})\b", flat)
    if not rec_raw:
        # Caso OCR común: el recibo aparece como número suelto inmediatamente después de la póliza (en la cabecera)
        m = re.search(
            r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\s*:\s*([0-9]{6,15})[\s\r\n]+([0-9]{6,12})\b",
            text,
            re.IGNORECASE,
        )
        if m and m.group(2) != m.group(1):
            rec_raw = m.group(2)
    if not rec_raw:
        # Fallback: buscar un número de recibo en la cabecera antes de "CONDICIONES PARTICULARES"
        m_cond = re.search(r"\bCONDICIONES\s+PARTICULARES\b", text, re.IGNORECASE)
        prefix = text[:m_cond.start()] if m_cond else text[:2500]
        pol = item.get("numero_poliza")
        nums = [n for n in re.findall(r"\b(\d{6,12})\b", prefix) if not pol or n != pol]
        if nums:
            rec_raw = nums[-1]
    if not rec_raw:
        # Último recurso: stream (solo si no se detectó el problema de "RECIBO :" vacío)
        rec_raw = cond.get("recibo")
    if rec_raw and item.get("numero_poliza") and rec_raw == item["numero_poliza"]:
        rec_raw = None
    item["recibo"] = rec_raw

    colectivo_label = (
        _between(r"\bColectivo\s+Asegurado\s*:?\b", r"\bInicio\s+de\s+Vigencia\b", flat, window=600)
        or _between(r"\bColectivo\s+Asegurado\s*:?\b", r"\bVencimiento\b", flat, window=600)
        or _find_after(r"\bColectivo\s+Asegurado\b\s*:?\s*", flat, r"([A-ZÁÉÍÓÚÑ0-9 \.&']{3,200})", window=300)
        or _find_after(r"\bColectivo\s+Asegurado\b\s*:?\s*", text, r"([A-ZÁÉÍÓÚÑ0-9 \.&']{3,200})", window=300)
    )
    item["colectivo_asegurado"] = _only_company(colectivo_label or cond.get("contratante") or cond.get("colectivo_asegurado"))

    # Preferir fechas de Aplicación (pedido del usuario)
    iv_app = cond.get("inicio_vigencia_aplicacion") or _find_after(r"Inicio\s+de\s+Vigencia\s+Aplicaci[óo]n\s*:\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=600)
    ve_app = cond.get("vencimiento_aplicacion") or _find_after(r"Vencimiento\s+de\s+Aplicaci[óo]n\s*:\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
    item["inicio_vigencia"] = iv_app or _find_after(r"Inicio\s+de\s+Vigencia\s*:\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=600) or cond.get("inicio_vigencia")
    venc_label = _find_after(r"Vencimiento\s*:\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120) or cond.get("vencimiento")
    # Regla: preferir Vencimiento de Aplicación si es válido; si parece confundido con 'Último día de Pago' o es anterior al inicio, usar Vencimiento:
    def _parse_ddmmyyyy(s: Optional[str]) -> Optional[datetime]:
        try:
            return datetime.strptime(s.strip(), "%d/%m/%Y") if s else None
        except Exception:
            return None
    va_dt = _parse_ddmmyyyy(ve_app)
    iv_dt = _parse_ddmmyyyy(iv_app)
    udp_dt = _parse_ddmmyyyy(_find_after(r"Último\s+d[ií]a\s+de\s+Pago\s*:\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120) or cond.get("ultimo_dia_pago"))
    vnorm_dt = _parse_ddmmyyyy(venc_label)
    use_va = bool(ve_app) and (not iv_dt or (va_dt and va_dt >= iv_dt)) and (not udp_dt or (va_dt and va_dt != udp_dt))
    item["vencimiento"] = (ve_app if use_va else venc_label) or cond.get("vencimiento")
    item["fecha_vecimiento"] = item["vencimiento"] or _find_after(r"\bVencimiento\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=4000)
    item["ultimo_dia_pago"] = _find_after(r"Último\s+d[ií]a\s+de\s+Pago\s*:\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=600) or cond.get("ultimo_dia_pago")
    # Fecha de Emisión: elegir la más cercana al bloque 'Moneda'/'Forma de Pago' (zona de condiciones particulares)
    fe_val = None
    pos_anchor = None
    m_anchor = re.search(r"\bMoneda\b\s*:?\s*", flat, re.IGNORECASE) or re.search(r"\bForma\s+de\s+Pago\b\s*:?\s*", flat, re.IGNORECASE)
    if m_anchor:
        pos_anchor = m_anchor.start()
    candidates = []
    for m in re.finditer(r"Fecha\s+de\s+Emisi[óo]n\b\s*:?\s*", flat, re.IGNORECASE):
        frag = flat[m.end(): m.end() + 220]
        dm = re.search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", frag)
        if dm:
            candidates.append((m.start(), dm.group(1)))
    if candidates:
        if pos_anchor is not None:
            # Preferir la etiqueta posterior al ancla y más cercana
            after = [(abs(c[0] - pos_anchor), c[1], c[0] >= pos_anchor) for c in candidates]
            after_sorted = sorted(after, key=lambda x: (not x[2], x[0]))  # primero las que están después del ancla
            fe_val = after_sorted[0][1]
        else:
            fe_val = candidates[-1][1]
    item["fecha_emision"] = fe_val or _find_after(r"Fecha\s+de\s+Emisi[óo]n\s*:?\s*", flat, date_pat, window=300) or _find(rf"Fecha\s+de\s+Emisi[óo]n\s*:?\s*{date_pat}", flat) or cond.get("fecha_emision")

    # Bloque cercano a "Forma de Pago" puede mezclar moneda y fecha; extraer tokens
    fp_block = _find_after(r"Forma\s+de\s+Pago\s*:\s*", flat, r"(.{1,120})", window=300) or ""
    mon_tok = None
    fp_tok = None
    date_tok = None
    m_mon = re.search(r"\b(SOLES|USD|US\$|PEN|DOLARES|D[ÓO]LARES)\b", fp_block, re.IGNORECASE)
    if m_mon:
        mon_tok = m_mon.group(1).upper()
    m_fp = re.search(r"\b(MENSUAL|ANUAL|SEMESTRAL|TRIMESTRAL|BIMESTRAL|CUATRIMESTRAL)\b", fp_block, re.IGNORECASE)
    if m_fp:
        fp_tok = m_fp.group(1).upper()
    m_dt = re.search(r"\b([0-9]{2}/[0-9]{2}/[0-9]{4})\b", fp_block)
    if m_dt:
        date_tok = m_dt.group(1)

    item["moneda"] = item.get("moneda") or _find_after(r"Moneda\s*:\s*", flat, r"(SOLES|USD|PEN|DOLARES|D[ÓO]LARES)", window=600) or mon_tok or cond.get("moneda")
    item["forma_pago"] = fp_tok or _find_after(r"Forma\s+de\s+Pago\s*:\s*", flat, r"([A-ZÁÉÍÓÚÑ0-9 \.\-]+?)\s+(?=(Moneda|Fecha\s+de\s+Emisi[óo]n|Vencimiento|Inicio|Último|RECIBO)\b)", window=600) or _find(r"Forma\s+de\s+Pago\s*:\s*([A-ZÁÉÍÓÚÑ0-9 \.\-]+)", flat)
    item["inicio_vigencia_aplicacion"] = item.get("inicio_vigencia_aplicacion") or date_tok or cond.get("inicio_vigencia_aplicacion")
    # Forzar que la UI use fechas de Aplicación como Inicio/Fin
    if item.get("inicio_vigencia_aplicacion"):
        item["inicio_vigencia"] = item["inicio_vigencia_aplicacion"]

    # Fallback inteligente de Fecha de Emisión: elegir la fecha válida más cercana anterior a 'inicio_vigencia_aplicacion'
    try:
        iv_app_dt = datetime.strptime((item.get("inicio_vigencia_aplicacion") or item.get("inicio_vigencia")), "%d/%m/%Y")
        fe_cur = item.get("fecha_emision")
        fe_dt = datetime.strptime(fe_cur, "%d/%m/%Y") if fe_cur else None
        # Si no hay emisión o está lejos del inicio de aplicación, buscar/estimar mejor candidata
        need_repick = (fe_dt is None) or (abs((iv_app_dt - fe_dt).days) > 45) or (fe_cur in {item.get("inicio_vigencia"), item.get("vencimiento"), item.get("ultimo_dia_pago")})
        if need_repick:
            all_dates = []
            for dm in re.finditer(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", flat):
                s = dm.group(1)
                try:
                    dt = datetime.strptime(s, "%d/%m/%Y")
                    all_dates.append((dt, s))
                except Exception:
                    pass
            # Filtrar fechas anteriores al inicio de aplicación y dentro de 120 días previos
            candidates = [p for p in all_dates if p[0] <= iv_app_dt and (iv_app_dt - p[0]).days <= 120]
            if candidates:
                candidates.sort(key=lambda x: x[0])
                best = candidates[-1][1]
                item["fecha_emision"] = best
            else:
                # Si no hay candidatas visibles en OCR, estimar como 5 días antes de inicio de aplicación
                est = (iv_app_dt - timedelta(days=5)).strftime("%d/%m/%Y")
                item["fecha_emision"] = est
    except Exception:
        pass

    # Ajuste defensivo: si 'vencimiento' resulta anterior a 'inicio_vigencia', intentar usar el otro candidato (Vencimiento :) cercano
    try:
        def _parse_ddmmyyyy(s: Optional[str]) -> Optional[datetime]:
            if not s: return None
            return datetime.strptime(s.strip(), "%d/%m/%Y")
        iv_dt = _parse_ddmmyyyy(item.get("inicio_vigencia"))
        ve_dt = _parse_ddmmyyyy(item.get("vencimiento"))
        if iv_dt and ve_dt and ve_dt < iv_dt:
            alt_ve = _find_after(r"\bVencimiento\b\s*:?\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=600)
            alt_dt = _parse_ddmmyyyy(alt_ve)
            if alt_dt and alt_dt >= iv_dt:
                item["vencimiento"] = alt_ve
    except Exception:
        pass

    # Fallback final para Fecha de Emisión: elegir la última fecha válida antes del bloque "IMPORTES DE LA DECLARACIÓN"
    try:
        iv_app_dt = datetime.strptime((item.get("inicio_vigencia_aplicacion") or item.get("inicio_vigencia")), "%d/%m/%Y")
        fe_cur = item.get("fecha_emision")
        m_imp = re.search(r"IMP[OÓ]RTES\s+DE\s+LA\s+DECLARACI[ÓO]N", flat, re.IGNORECASE)
        if m_imp:
            prefix = flat[:m_imp.start()]
            dates = []
            for dm in re.finditer(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", prefix):
                s = dm.group(1)
                try:
                    dt = datetime.strptime(s, "%d/%m/%Y")
                    dates.append((dt, s))
                except Exception:
                    pass
            cand = [p for p in dates if p[0] <= iv_app_dt]
            if cand:
                cand.sort(key=lambda x: x[0])
                last_before = cand[-1][1]
                # Si la actual difiere del mejor candidato, reemplazar
                if not fe_cur or fe_cur != last_before:
                    item["fecha_emision"] = last_before
    except Exception:
        pass

    # Heurística para Fecha de Emisión correcta: evitar confundir con 'Inicio de Vigencia'
    # Si fecha_emision coincide con alguna de las otras fechas conocidas, buscar cerca de 'Moneda' o de la propia etiqueta otra fecha distinta
    try:
        known = {x for x in [
            item.get("inicio_vigencia"),
            item.get("vencimiento"),
            item.get("inicio_vigencia_aplicacion"),
            item.get("vencimiento_aplicacion"),
            item.get("ultimo_dia_pago"),
        ] if x}
        fe_cur = item.get("fecha_emision")
        if fe_cur in known:
            # Buscar alrededor de 'Fecha de Emisión' etiqueta
            fe_alt = _find_after(r"Fecha\s+de\s+Emisi[óo]n\b\s*:?\s*", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=200)
            if fe_alt and fe_alt not in known:
                item["fecha_emision"] = fe_alt
            else:
                # Buscar alrededor de 'Moneda' como referencia de bloque
                mon_span = re.search(r"\bMoneda\b\s*:?\s*", flat, re.IGNORECASE)
                if mon_span:
                    start = max(mon_span.start() - 200, 0)
                    end = min(mon_span.end() + 300, len(flat))
                    around = flat[start:end]
                    for m in re.finditer(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", around):
                        cand = m.group(1)
                        if cand not in known:
                            item["fecha_emision"] = cand
                            break
    except Exception:
        pass

    # Selección definitiva: elegir una emisión entre [inicio_vigencia, inicio_vigencia_aplicacion] y distinta de último día de pago/vencimiento
    try:
        iv_dt = datetime.strptime(item.get("fecha_emision"), "%d/%m/%Y") if item.get("fecha_emision") else None
        iv_app_dt = datetime.strptime(item.get("fecha_emision_aplicacion"), "%d/%m/%Y") if item.get("fecha_emision_aplicacion") else None
        udp_dt = datetime.strptime(item.get("fecha_emision_aplicacion"), "%d/%m/%Y") if item.get("fecha_emision_aplicacion") else None
        ve_dt = datetime.strptime(item.get("fecha_vencimiento_aplicacion"), "%d/%m/%Y") if item.get("fecha_vencimiento_aplicacion") else None
        fe_cur = item.get("fecha_emision")
        # Construir rango válido
        lower = iv_dt or iv_app_dt
        upper = iv_app_dt or iv_dt
        if lower and upper:
            # Recoger todas las fechas del texto
            all_dates = []
            for dm in re.finditer(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", flat):
                s = dm.group(1)
                try:
                    dt = datetime.strptime(s, "%d/%m/%Y")
                    all_dates.append((dt, s))
                except Exception:
                    pass
            # Filtrar a ventana y excluir udp/vencimiento exactos
            window = [p for p in all_dates if (p[0] >= lower and p[0] <= upper) and (not udp_dt or p[0] != udp_dt) and (not ve_dt or p[0] != ve_dt)]
            if window:
                window.sort(key=lambda x: x[0])
                chosen = window[-1][1]  # la más cercana a inicio de aplicación por arriba
                if fe_cur != chosen:
                    item["fecha_emision"] = chosen
    except Exception:
        pass

    ramo_main = None
    ramos_producto = None
    t_low = flat.lower()
    if "d.l.688" in t_low or "decreto legislativo 688" in t_low or "vida ley" in t_low:
        ramo_main = "VIDA - LEY"
        if "empleados" in t_low:
            ramos_producto = "EMPLEADOS"
    if ramo_main:
        item["ramo"] = ramo_main
    if ramos_producto:
        item["ramos_producto"] = ramos_producto

        # Prima Comercial: capturar con máxima robustez
    base_pc = None
    total_pc = None
    m_pc = re.search(r"Prima\s+Comercial\s*[:：]?\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)[\s\S]{0,200}?Prima\s+Comercial\s*\+\s*IGV\s*[:：]?\s*S?\/?\s*(\(?\s*(?:[-−–—]\s*)?[0-9\.,]+\s*\)?)", flat, re.IGNORECASE | re.DOTALL)
    if m_pc:
        base_pc = m_pc.group(1)
        total_pc = m_pc.group(2)
    if not base_pc:
        # Limitar estrictamente entre la etiqueta base y la etiqueta de total
        base_area = _between(r"\bPrima\s+Comercial(?!\s*\+)\b", r"\bPrima\s+Comercial\s*\+\s*IGV\b", flat, window=400)
        if base_area:
            nums = re.findall(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?)", base_area)
            if nums:
                try:
                    vals = [float(str(_money(n)).replace(",", ".")) for n in nums]
                    base_pc = nums[vals.index(min(vals))]
                except Exception:
                    base_pc = nums[-1]
    if not total_pc:
        labels_t = list(re.finditer(r"\bPrima\s+Comercial\s*\+\s*IGV\b", flat, re.IGNORECASE))
        if labels_t:
            tm = labels_t[-1]
            frag2 = flat[tm.end(): tm.end() + 150]
            nt = re.search(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?)", frag2)
            if nt:
                total_pc = nt.group(1)
    item["prima_comercial"] = _money(base_pc) or _money(cond.get("prima_resultante"))
    item["prima_comercial_igv"] = _money(total_pc)


    ruc_candidato = cond.get("ruc")
    if not ruc_candidato:
        ruc_candidato = _find(r"RUC\s*:\s*(\d{11})", flat)
    if not ruc_candidato:
        candidates_ruc = re.findall(r"\b(10\d{9}|20\d{9})\b", text)
        if candidates_ruc:
            ruc_candidato = candidates_ruc[0]
    item["numero_documento_extracted"] = ruc_candidato

    try:
        def _as_date2(s: Optional[str]):
            try:
                return datetime.strptime(s.strip(), "%d/%m/%Y").date() if s else None
            except Exception:
                return None

        header_block2 = _between(
            r"\bCONDICIONES\s+PARTICULARES\b",
            r"\bIMP[OÓ]RTES\b",
            flat,
            window=8000,
        ) or flat[:8000]
        dates2 = []
        for d in re.findall(date_pat, header_block2):
            if d not in dates2 and _as_date2(d):
                dates2.append(d)
        if len(dates2) >= 6:
            dates2.sort(key=lambda x: _as_date2(x))
            _inicio_pol = dates2[0]
            _venc = dates2[-1]
            _venc_app = dates2[-2]

            if not item.get("vencimiento_aplicacion"):
                item["vencimiento_aplicacion"] = _venc_app
            item["vencimiento"] = _venc_app
            item["fecha_vecimiento"] = _venc

            iv_app_dt = _as_date2(item.get("inicio_vigencia_aplicacion"))
            if iv_app_dt and not item.get("inicio_vigencia"):
                item["inicio_vigencia"] = item.get("inicio_vigencia_aplicacion")
            if iv_app_dt and item.get("inicio_vigencia") != item.get("inicio_vigencia_aplicacion"):
                item["inicio_vigencia"] = item.get("inicio_vigencia_aplicacion")

            mid = [d for d in dates2 if d not in {_inicio_pol, _venc_app, _venc}]
            if iv_app_dt:
                udp_dt = _as_date2(item.get("ultimo_dia_pago"))
                udp_need = (
                    udp_dt is None
                    or item.get("ultimo_dia_pago") == item.get("fecha_vecimiento")
                    or (_as_date2(_venc_app) and udp_dt and udp_dt > _as_date2(_venc_app))
                    or (udp_dt and udp_dt < iv_app_dt)
                )
                if udp_need:
                    udp_candidates = [d for d in mid if _as_date2(d) and _as_date2(d) >= iv_app_dt and _as_date2(d) <= _as_date2(_venc_app)]
                    if udp_candidates:
                        udp_candidates.sort(key=lambda x: _as_date2(x))
                        item["ultimo_dia_pago"] = udp_candidates[-1]

                fe_dt = _as_date2(item.get("fecha_emision"))
                fe_need = (
                    fe_dt is None
                    or item.get("fecha_emision") == item.get("inicio_vigencia_aplicacion")
                    or item.get("fecha_emision") == _inicio_pol
                    or abs((fe_dt - iv_app_dt).days) > 45
                )
                if fe_need:
                    fe_candidates = [d for d in mid if d != item.get("ultimo_dia_pago") and d != item.get("inicio_vigencia_aplicacion")]
                    if fe_candidates:
                        fe_candidates.sort(key=lambda x: abs((_as_date2(x) - iv_app_dt).days))
                        item["fecha_emision"] = fe_candidates[0]
    except Exception:
        pass

    fe = item.get("fecha_emision")
    try:
        if fe and not item.get("fecha_vecimiento"):
            d = datetime.strptime(fe, "%d/%m/%Y")
            item["fecha_vecimiento"] = (d + timedelta(days=15)).strftime("%d/%m/%Y")
    except Exception:
        pass
    if not item.get("fecha_vecimiento") and item.get("vencimiento"):
        item["fecha_vecimiento"] = item["vencimiento"]

    return {k: _clean(v) for k, v in item.items() if v}
