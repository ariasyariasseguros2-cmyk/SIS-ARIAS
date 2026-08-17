import re
from typing import Dict, Optional


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _canon(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text or "")


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _between(start_pat: str, end_pat: str, text: str, flags=re.IGNORECASE | re.DOTALL, window: int = 4000) -> Optional[str]:
    m_start = re.search(start_pat, text, flags)
    if not m_start:
        return None
    frag = text[m_start.end() : m_start.end() + window]
    m_end = re.search(end_pat, frag, flags)
    return _clean(frag[: m_end.start()] if m_end else frag)


def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    raw0 = str(s).strip()
    raw = raw0.replace("−", "-").replace("–", "-").replace("—", "-")
    m = re.search(r"(\(?\s*(?:[-−–—]\s*)?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d{2})?\s*\)?)", raw)
    if not m:
        return None
    tok = m.group(1).strip()
    neg = False
    mp = re.match(r"^\((.*)\)$", tok)
    if mp:
        neg = True
        tok = (mp.group(1) or "").strip()
    if re.match(r"^\s*[-−–—]\s*", tok):
        neg = True
    tok = re.sub(r"[^\d,\.]", "", tok)
    if not tok:
        return None
    if "." in tok and "," in tok:
        tok = tok.replace(",", "")
    elif "," in tok and "." not in tok:
        tok = tok.replace(",", ".")
    try:
        num = float(tok)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return f"-{tok}" if (neg and tok) else tok


def parse_grandia_eps_v2(text: str) -> Dict[str, str]:
    item: Dict[str, Optional[str]] = {}
    flat = _canon(text)

    def _add_days_ddmmyyyy(date_str: Optional[str], days: int) -> Optional[str]:
        try:
            from datetime import datetime, timedelta
            if not date_str:
                return None
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    def _find_date_range(src: str) -> tuple[Optional[str], Optional[str]]:
        patterns = [
            r"VIGENCIA\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})\s*(?:al|hasta|-|–|—)\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
            r"VIGENCIA\s+DE\s+LA\s+COBERTURA\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})\s*(?:al|hasta|-|–|—)\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
            r"Inicio\s+de\s+Vigencia\s*[:：]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})[\s\S]{0,120}?Vencimiento\s*[:：]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
            r"vigente\s+desde\s+el?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})\s*(?:al|hasta|-|–|—)\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
        ]
        for pat in patterns:
            m = re.search(pat, src, re.IGNORECASE | re.DOTALL)
            if m:
                return m.group(1), m.group(2)
        m_iv = re.search(r"INICIO\s+DE\s+VIGENCIA\s*[:：]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", src, re.IGNORECASE)
        m_fv = re.search(r"FIN\s+DE\s+VIGENCIA\s*[:：]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", src, re.IGNORECASE)
        if m_iv or m_fv:
            return m_iv.group(1) if m_iv else None, m_fv.group(1) if m_fv else None
        return None, None

    def _find_fecha_emision(src: str) -> Optional[str]:
        meses = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "setiembre": "09", "septiembre": "09", "octubre": "10",
            "noviembre": "11", "diciembre": "12",
        }
        m_fe = re.search(r"FECHA\s+DE\s+EMISI[ÓO]N\s*[:：.]?\s*(?:\r?\n\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})", src, re.IGNORECASE)
        if m_fe:
            return m_fe.group(1).replace("-", "/")
        m_words = re.search(r"(?:Suscrito|Emitido|Expedido)[\s\S]{0,100}?(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+de[l]?\s+(\d{4})", src, re.IGNORECASE)
        if m_words:
            mon = m_words.group(2).lower()
            mon_num = meses.get(mon)
            if mon_num:
                dd = f"{int(m_words.group(1)):02d}"
                return f"{dd}/{mon_num}/{m_words.group(3)}"
        m_words2 = re.search(r"(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo)\s*[,，]\s*(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s+de[l]?\s+(\d{4})", src, re.IGNORECASE)
        if m_words2:
            mon = m_words2.group(2).lower()
            mon_num = meses.get(mon)
            if mon_num:
                dd = f"{int(m_words2.group(1)):02d}"
                return f"{dd}/{mon_num}/{m_words2.group(3)}"
        return None

    contrato = (
        _find(r"\bCONTRATO\s*(?:NO\.?|NRO\.?|N°|Nº)\s*[:.]?\s*([0-9]{5,}(?:-[0-9A-Z]+)?)\b", flat)
        or _find(r"\bCONTRATO\s*(?:NO\.?|NRO\.?|N°|Nº)\s*[:.]?\s*([0-9]{5,}(?:-[0-9A-Z]+)?)\b", text)
    )

    inicio_vigencia, vencimiento = _find_date_range(text)
    if not inicio_vigencia and not vencimiento:
        inicio_vigencia, vencimiento = _find_date_range(flat)

    fecha_emision = _find_fecha_emision(text) or _find_fecha_emision(flat)

    datos_block = (
        _between(r"\bDATOS\s+DEL\s+CONTRATANTE\b", r"\bAnexo\b|\bCONSOLIDADO\s+DE\s+PRIMAS\b", text, window=6000)
        or _between(r"\bDATOS\s+DEL\s+CONTRATANTE\b", r"\bAnexo\b|\bCONSOLIDADO\s+DE\s+PRIMAS\b", flat, window=6000)
        or text
    )

    colectivo = (
        _between(r"Denominaci[oó]n\s+social\s*:\s*", r"\bRUC\b", datos_block, window=1200)
        or _find(r"Denominaci[oó]n\s+social\s*:\s*([\s\S]*?)\bRUC\b", datos_block)
    )
    if colectivo:
        colectivo = re.sub(r"\s+", " ", _clean(colectivo)).strip("“”\"' :-")
        colectivo = colectivo.replace("'", "").replace('"', "")

    ruc = _find(r"\bRUC\s*(?:No\.?|Nro\.?|N°|Nº)?\s*[:.]?\s*(\d{11})\b", datos_block) or _find(
        r"\bRUC\s*(?:No\.?|Nro\.?|N°|Nº)?\s*[:.]?\s*(\d{11})\b", flat
    )

    direccion = _between(r"Direcci[oó]n\s*:\s*", r"\bActividad\b", datos_block, window=1200)
    if direccion:
        direccion = re.sub(r"\s+", " ", direccion).strip("“”\"' :-")

    actividad = _between(r"\bActividad\b", r"\bSede\b", datos_block, window=1600)
    if actividad:
        actividad = re.sub(r"\s+", " ", actividad).strip("“”\"' :-")

    sede = _between(r"\bSede\s*:\s*", r"\bUbicaci[oó]n\s+del\s+riesgo\b", datos_block, window=1200)
    if sede:
        sede = re.sub(r"\s+", " ", sede).strip("“”\"' :-")

    ubicacion_riesgo = _between(
        r"\bUbicaci[oó]n\s+del\s+riesgo\b", r"\bAnexo\b|\bCONSOLIDADO\s+DE\s+PRIMAS\b", datos_block, window=900
    )
    if ubicacion_riesgo:
        ubicacion_riesgo = re.sub(r"\s+", " ", ubicacion_riesgo).strip("“”\"' :-")

    block_primas = _between(r"\bCONSOLIDADO\s+DE\s+PRIMAS\b", r"\bPrima\s+Neta\b", text, window=2500) or _between(
        r"\bCONSOLIDADO\s+DE\s+PRIMAS\b", r"\bPrima\s+Neta\b", flat, window=2500
    )
    tipo_riesgo = None
    tasa = None
    numero_trabajadores = None
    importe_total_planilla = None
    if block_primas:
        m_row = re.search(
            r"\b(Alto|Bajo|Mediano|Medio)\s+Riesgo\b[\s:]*([0-9]+(?:[.,][0-9]+)?)\s*%?\s*\+\s*IGV[\s:]*([0-9]{1,5})[\s:]*(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?\d+(?:[.,]\d{2})?\s*\)?)",
            block_primas,
            re.IGNORECASE | re.DOTALL,
        )
        if m_row:
            tipo_riesgo = f"{m_row.group(1).strip()} Riesgo"
            tasa = f"{m_row.group(2).strip()} % + IGV"
            numero_trabajadores = m_row.group(3).strip()
            importe_total_planilla = _money(m_row.group(4))
        else:
            tipo_riesgo = _find(r"\b(Alto|Bajo|Mediano|Medio)\s+Riesgo\b", block_primas)
            tasa_pct = _find(r"\b([0-9]+(?:[.,][0-9]+)?)\s*%?\s*\+\s*IGV\b", block_primas)
            tasa = f"{tasa_pct} % + IGV" if tasa_pct else None
            numero_trabajadores = _find(r"\bTRABAJADORES\b[\s:]*([0-9]{1,5})\b", block_primas)
            importe_total_planilla = _money(_find(r"\bPLANILLA\b[\s:]*([0-9.,]+)", block_primas) or block_primas)

    prima_neta = _money(_find(r"\bPrima\s+Neta\s*:\s*(.+)", text) or _find(r"\bPrima\s+Neta\s*:\s*(.+)", flat))
    igv_val = _money(
        _find(r"\b(?:Impuesto\s+)?IGV(?:\s*\(\s*18%\s*\))?\s*:\s*(.+)", text)
        or _find(r"\b(?:Impuesto\s+)?IGV(?:\s*\(\s*18%\s*\))?\s*:\s*(.+)", flat)
    )
    prima_total = _money(_find(r"\bPrima\s+Total\s*:\s*(.+)", text) or _find(r"\bPrima\s+Total\s*:\s*(.+)", flat))

    prima_comercial = prima_neta
    if not prima_comercial and prima_total and igv_val:
        try:
            prima_comercial = f"{float(prima_total) - float(igv_val):.2f}"
        except Exception:
            prima_comercial = None

    fecha_vecimiento = None
    if fecha_emision:
        fecha_vecimiento = _add_days_ddmmyyyy(fecha_emision, 15)
    if not fecha_vecimiento and inicio_vigencia:
        fecha_vecimiento = _add_days_ddmmyyyy(inicio_vigencia, 15)

    item.update(
        {
            "numero_poliza": contrato,
            "contrato_nro": contrato,
            "colectivo_asegurado": colectivo,
            "inicio_vigencia": inicio_vigencia,
            "vencimiento": vencimiento,
            "fecha_emision": fecha_emision,
            "fecha_vecimiento": fecha_vecimiento,
            "ramo": "SCTR",
            "ramos_producto": "Salud",
            "moneda": "SOLES",
            "prima_comercial": prima_comercial,
            "prima_neta": prima_neta,
            "prima_total": prima_total,
            "prima_comercial_igv": prima_total,
            "numero_documento_extracted": ruc,
            "direccion": direccion,
            "actividad": actividad,
            "sede": sede,
            "ubicacion_riesgo": ubicacion_riesgo,
            "tipo_riesgo": tipo_riesgo,
            "tasa": tasa,
            "numero_trabajadores": numero_trabajadores,
            "importe_total_planilla": importe_total_planilla,
        }
    )
    return {k: _clean(v) for k, v in item.items() if v}
