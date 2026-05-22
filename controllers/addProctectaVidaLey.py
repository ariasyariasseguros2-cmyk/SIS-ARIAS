import re
from datetime import datetime, timedelta
from typing import Dict, Optional


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _slice_between(text: str, start_pat: str, end_pats: list[str]) -> str:
    m = re.search(start_pat, text, re.IGNORECASE)
    if not m:
        return ""
    tail = text[m.end():]
    end_idx = None
    for ep in end_pats:
        me = re.search(ep, tail, re.IGNORECASE)
        if me:
            end_idx = me.start() if end_idx is None else min(end_idx, me.start())
    return tail[:end_idx].strip() if end_idx is not None else tail.strip()


def _date_words_to_ddmmyyyy(text: str) -> Optional[str]:
    m = re.search(
        r"\b(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})\b",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    meses = {
        "enero": "01",
        "febrero": "02",
        "marzo": "03",
        "abril": "04",
        "mayo": "05",
        "junio": "06",
        "julio": "07",
        "agosto": "08",
        "setiembre": "09",
        "septiembre": "09",
        "octubre": "10",
        "noviembre": "11",
        "diciembre": "12",
    }
    dd = f"{int(m.group(1)):02d}"
    mon = meses.get(m.group(2).lower())
    if not mon:
        return None
    return f"{dd}/{mon}/{m.group(3)}"


def _normalize_moneda(moneda_raw: Optional[str]) -> Optional[str]:
    if not moneda_raw:
        return None
    up = re.sub(r"\s+", "", moneda_raw.replace("\u00A0", " ").upper())
    if not up:
        return None
    if "DOL" in up or "USD" in up or up.startswith("US$") or up == "$":
        return "US$"
    if "SOL" in up or up.startswith("S/") or up.startswith("S/.") or up == "PEN":
        return "S/"
    return moneda_raw.strip()


def _normalize_date_ddmmyyyy(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    s = date_str.strip().replace("-", "/")
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", s)
    if not m:
        return None
    dd = f"{int(m.group(1)):02d}"
    mm = f"{int(m.group(2)):02d}"
    return f"{dd}/{mm}/{m.group(3)}"

def _money_value(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2})?)", s)
    if not m:
        return None
    raw = m.group(1)
    if raw.count(",") == 1 and raw.count(".") == 0:
        raw = raw.replace(",", ".")
    raw = raw.replace(",", "")
    try:
        return f"{float(raw):.2f}"
    except Exception:
        return m.group(1)

def _add_days_ddmmyyyy(date_str: Optional[str], days: int) -> Optional[str]:
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
    except Exception:
        return None


def _infer_date_near_label(text: str, label_pattern: str, before: int = 300, after: int = 200) -> Optional[str]:
    matches = list(re.finditer(label_pattern, text or "", re.IGNORECASE))
    if not matches:
        return None
    last = matches[-1]
    start = max(0, last.start() - before)
    end = min(len(text), last.end() + after)
    window = (text or "")[start:end]
    dates = list(re.finditer(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", window))
    if not dates:
        return None
    label_pos = last.start() - start
    best = min(dates, key=lambda d: abs(d.start() - label_pos))
    return best.group(1) if best else None


def _infer_producto_from_asegurados(text: str) -> Optional[str]:
    t = text or ""
    seg = _slice_between(
        t,
        r"\bASEGURADOS\b",
        [
            r"\bBENEFICIARIOS?\b",
            r"\bCOBERTURAS?\b",
            r"\bEXCLUSIONES?\b",
            r"\bCLAUSULAS?\b",
            r"\bCLA\u00c1USULAS?\b",
            r"\bFIRMAS?\b",
        ],
    )
    if not seg:
        m = re.search(r"\bASEGURADOS\b", t, re.IGNORECASE)
        if m:
            seg = t[m.end(): m.end() + 1200]

    if not seg:
        return None

    # Prioridad: Empleado / Obrero explícitos en la tabla
    if re.search(r"\bemplead[oa]s?\b", seg, re.IGNORECASE):
        return "EMPLEADOS"
    if re.search(r"\bobrer[oa]s?\b", seg, re.IGNORECASE) or re.search(r"\bobreros?\b", seg, re.IGNORECASE):
        return "OBRERO"
    if re.search(r"\btrabajador(?:es)?\b", seg, re.IGNORECASE):
        return "TRABAJADORES"

    return None


def parse_protecta_vidaley(text: str) -> Dict[str, str]:
    t = text or ""
    low = t.lower()

    datos_poliza = _slice_between(
        t,
        r"\bDATOS\s+DE\s+LA\s+P[ÓO]LIZA\b",
        [
            r"\bCONTRATANTE\s+DEL\s+SEGURO\b",
            r"\bCONTRATANTE\b",
            r"\bASEGURADOS\b",
        ],
    )

    contratante_section = _slice_between(
        t,
        r"\bCONTRATANTE\s+DEL\s+SEGURO\b",
        [
            r"\bASEGURADOS\b",
            r"\bASEGURADO\b",
            r"\bDATOS\s+DE\s+LOS\s+ASEGURADOS\b",
        ],
    )

    poliza = (
        _find(r"\bP[ÓO]LIZA\b\s*[:：]\s*([0-9]{6,20})\b", datos_poliza)
        or _find(r"\bP[ÓO]LIZA\b\s*[:：]\s*([0-9]{6,20})\b", t)
    )

    moneda_raw = (
        _find(r"\bMONEDA\b\s*[:：]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ$\/\.\s]{1,20})", datos_poliza)
        or _find(r"\bMONEDA\b\s*[:：]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ$\/\.\s]{1,20})", t)
    )
    moneda = _normalize_moneda(moneda_raw)

    inicio_vigencia = None
    vencimiento = None
    m_vig = re.search(
        r"\bVIGENCIA\b[\s:：]{0,6}[\s\S]{0,220}?\b(?:DEL|DESDE)\b[\s\S]{0,80}?(\d{1,2}[/-]\d{1,2}[/-]\d{4})[\s\S]{0,260}?\b(?:AL|HASTA)\b[\s\S]{0,80}?(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        datos_poliza or t,
        re.IGNORECASE | re.DOTALL,
    )
    if m_vig:
        inicio_vigencia = _normalize_date_ddmmyyyy(m_vig.group(1))
        vencimiento = _normalize_date_ddmmyyyy(m_vig.group(2))

    if not (inicio_vigencia and vencimiento):
        m_vig2 = re.search(
            r"\bVIGENCIA\b[\s:：]{0,6}[\s\S]{0,240}?(\d{1,2}[/-]\d{1,2}[/-]\d{4})[\s\S]{0,240}?(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            datos_poliza or t,
            re.IGNORECASE | re.DOTALL,
        )
        if m_vig2:
            d1 = _normalize_date_ddmmyyyy(m_vig2.group(1))
            d2 = _normalize_date_ddmmyyyy(m_vig2.group(2))
            if d1 and d2:
                inicio_vigencia, vencimiento = d1, d2

    contratante = (
        _find(
            r"Denominaci[óo]n\s+o\s+Raz[óo]n\s+Social\s*[:：]\s*([^\r\n]{3,140})",
            contratante_section or t,
        )
        or _find(r"\bCONTRATANTE\b\s*[:：]\s*([^\r\n]{3,140})", contratante_section or t)
    )
    if contratante:
        contratante = re.sub(r"\s{2,}", " ", contratante).strip(" -:·.")

    ruc = None
    rucs = re.findall(r"\bRUC\b\s*[:：]?\s*(\d{11})\b", contratante_section or t, re.IGNORECASE)
    if rucs:
        for cand in rucs:
            if cand != "20517207331":
                ruc = cand
                break
        if not ruc:
            ruc = rucs[0]

    fecha_emision = (
        _find(r"Fecha\s+de\s+Emisi[óo]n\s*[:：]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", t)
        # Caso común en firma: fecha ANTES del texto "Fecha de Emisión"
        or _find(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})[\s\.·_]{0,120}Fecha\s+de\s+Emisi[óo]n\b", t)
        # Caso común en firma: texto "Fecha de Emisión" y luego la fecha en la línea siguiente
        or _find(r"Fecha\s+de\s+Emisi[óo]n\b[\s:：]*\r?\n\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", t)
        # Fallback robusto: buscar la fecha más cercana al ÚLTIMO "Fecha de Emisión"
        or _infer_date_near_label(t, r"Fecha\s+de\s+Emisi[óo]n")
        or _date_words_to_ddmmyyyy(t)
    )
    fecha_emision = _normalize_date_ddmmyyyy(fecha_emision) if fecha_emision else None

    prima_comercial = _money_value(
        _find(
            r"Prima\s+Comercial\s+Total\s*[:：]?\s*(?:S\s*/\s*\.?|S\s*/|S/\.?|US\s*\$|US\$|USD)?\s*([0-9\.,]+)",
            t,
        )
    )
    prima_total_igv = _money_value(
        _find(
            r"Prima\s+Comercial\s+Total\s+m[áa]s\s+IGV\s*[:：]?\s*(?:S\s*/\s*\.?|S\s*/|S/\.?|US\s*\$|US\$|USD)?\s*([0-9\.,]+)",
            t,
        )
    )

    fecha_vencimiento_pago = _add_days_ddmmyyyy(fecha_emision, 30) if fecha_emision else None

    ramo = "VIDA - LEY"
    ramos_producto = _infer_producto_from_asegurados(t)
    if not ramos_producto:
        if re.search(r"\bobrer[oa]s?\b", low):
            ramos_producto = "OBRERO"
        elif re.search(r"\bemplead[oa]s?\b", low):
            ramos_producto = "EMPLEADOS"
        elif "vida ley trabajadores" in low or re.search(r"\btrabajador(?:es)?\b", low):
            ramos_producto = "TRABAJADORES"

    item = {
        "numero_poliza": _clean(poliza),
        "moneda": _clean(moneda),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),
        "fecha_emision": _clean(fecha_emision),
        "fecha_vencimiento": _clean(fecha_vencimiento_pago),
        "fecha_vecimiento": _clean(fecha_vencimiento_pago),
        "ultimo_dia_pago": _clean(fecha_vencimiento_pago),
        "colectivo_asegurado": _clean(contratante),
        "contratante": _clean(contratante),
        "numero_documento_extracted": _clean(ruc),
        "ramo": ramo,
        "ramos_producto": _clean(ramos_producto),
        "prima_neta": _clean(prima_comercial),
        "prima_comercial": _clean(prima_comercial),
        "prima_total": _clean(prima_total_igv),
        "prima_comercial_igv": _clean(prima_total_igv),
    }

    return {k: _clean(v) for k, v in item.items() if v}
