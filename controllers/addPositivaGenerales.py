import re
from typing import Optional

def _normalize_date_ddmmyyyy(s: str | None) -> Optional[str]:
    if not s:
        return None
    raw = (s or "").strip()
    parts = re.split(r"[\/\-]", raw)
    if len(parts) != 3:
        return raw
    dd, mm, yy = [p.strip() for p in parts]
    if len(yy) == 2:
        yy = f"20{yy}"
    try:
        ddi = int(dd)
        mmi = int(mm)
        yyi = int(yy)
    except Exception:
        return f"{dd}/{mm}/{yy}"
    return f"{ddi:02d}/{mmi:02d}/{yyi:04d}"

def _extract_after_label(text: str, label_pattern: str) -> Optional[str]:
    m = re.search(label_pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    tail = text[m.end():]
    lines = tail.splitlines()
    if not lines:
        return None
    first = lines[0].strip()
    if first:
        first = re.sub(r'^[:：]?\s*', '', first).strip()
        if first:
            return first
    for ln in lines[1:]:
        val = ln.strip()
        if val:
            return val
    return None

def extract_razon_social(text: str) -> Optional[str]:
    patterns = [
        r"Raz[oó]n\s+Social\s*:?",
        r"Nombre\s+o\s+Raz[oó]n\s+Social\s*:?",
        r"Nombres?\s+y\s+Apellidos\s*:?"
    ]
    for pat in patterns:
        val = _extract_after_label(text, pat)
        if val:
            return val
    if val:
        return val
    m = re.search(r"Datos\s+del\s+Contratante(.*?)(?:\n\s*\n|$)", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        blk = m.group(1)
        for pat in patterns:
            v2 = _extract_after_label(blk, pat)
            if v2:
                return v2
    # 2) Carta / encabezado: "Señores\nNOMBRE," o "Señores: NOMBRE"
    # Buscar la línea siguiente o hasta coma
    m2 = re.search(r"Señores?\s*(?:,|:)?\s*(?:\n|\r\n)([^\n\r,]{2,120})", text, flags=re.IGNORECASE)
    if m2:
        name = m2.group(1).strip()
        # Remover coma final si la hay
        name = re.sub(r",\s*$", "", name).strip()
        if name:
            return name

def _normalize_amount(s: str | None) -> Optional[str]:
    if not s:
        return None
    raw = (s or "").strip().replace("−", "-").replace("–", "-").replace("—", "-")
    neg = False
    m_paren = re.match(r'^\((.*)\)$', raw)
    if m_paren:
        neg = True
        raw = (m_paren.group(1) or "").strip()
    v = re.sub(r"[^\d,\.\-]", "", raw)
    if v.startswith("-"):
        neg = True
    v = v.replace("-", "")
    if "," in v and "." in v:
        v = v.replace(",", "")
    elif "," in v and "." not in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        num = float(v)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return v or None

def extract_primas_positiva(text: str) -> dict:
    out = {}
    # Capturar prima comercial y total con IGV, permitiendo prefijos de moneda opcionales
    m_block = re.search(
        r"Prima\s+Comercial[\s\S]{0,120}?(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)[\s\S]{0,240}?Prima\s+Comercial\s*\+\s*IGV[\s\S]{0,120}?(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)",
        text,
        flags=re.IGNORECASE,
    )
    if m_block:
        out['prima_comercial'] = _normalize_amount(m_block.group(1))
        out['prima_comercial_igv'] = _normalize_amount(m_block.group(2))
        return {k: v for k, v in out.items() if v}
    
    m_pc = re.search(
        r"Prima\s+Comercial[\s:]*[\r\n]*[A-Z$S\/\.\s]*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)",
        text,
        flags=re.IGNORECASE,
    )
    m_pigv = re.search(
        r"Prima\s+Comercial\s*\+\s*IGV[\s:]*[\r\n]*[A-Z$S\/\.\s]*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)",
        text,
        flags=re.IGNORECASE,
    )
    if m_pc:
        out['prima_comercial'] = _normalize_amount(m_pc.group(1))
    if m_pigv:
        out['prima_comercial_igv'] = _normalize_amount(m_pigv.group(1))
    return {k: v for k, v in out.items() if v}

def extract_proforma_numero_positiva(text: str) -> Optional[str]:
    if not text:
        return None
    t = (text or "").replace("\u00A0", " ")
    m_head = re.search(
        r"cup[oó]n[\s\|]+n[uú]mero[\s\|]+vencimiento[\s\|]+monto",
        t,
        flags=re.IGNORECASE,
    )
    if m_head:
        window = t[m_head.end(): m_head.end() + 2200]
        m_row = re.search(
            r"(?m)^\s*\d{1,3}\s*(?:\||\s{1,})\s*(\d{6,20})\s*(?:\||\s{1,})\s*\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b",
            window,
            flags=re.IGNORECASE,
        )
        if m_row:
            return m_row.group(1)
        for ln in (window or "").splitlines():
            m_ln = re.search(r"^\s*\d{1,3}\s+(\d{6,20})\b", ln.strip())
            if m_ln:
                return m_ln.group(1)
    m_num = re.search(
        r"N[uú]mero\s+de\s+Proforma\s*[:：]?\s*(?:\r?\n\s*)?([0-9A-Z\-]{5,30})\b",
        t,
        flags=re.IGNORECASE,
    )
    if m_num:
        return m_num.group(1)
    m_prof = re.search(
        r"Proforma\s*N(?:ro\.?|[°º])\s*[:：]?\s*(?:\r?\n\s*)?([0-9]{6,20})\b",
        t,
        flags=re.IGNORECASE,
    )
    if m_prof:
        return m_prof.group(1)
    return None

def extract_numero_poliza_positiva(text: str) -> Optional[str]:
    if not text:
        return None
    t = (text or "").replace("\u00A0", " ")
    m_pol = re.search(
        r"P[oó]liza\s*N(?:ro\.?|[°º]|o)?\s*[:：]?\s*(?:\r?\n\s*)?([0-9]{6,20})\b",
        t,
        flags=re.IGNORECASE,
    )
    if m_pol:
        return m_pol.group(1)
    m_pol2 = re.search(
        r"\bP[oó]liza\b[\s\S]{0,120}?N(?:ro\.?|[°º]|o)\s*[:：]?\s*([0-9]{6,20})\b",
        t,
        flags=re.IGNORECASE,
    )
    if m_pol2:
        return m_pol2.group(1)
    return None

def extract_vigencias_positiva(text: str) -> dict:
    if not text:
        return {}
    t = (text or "").replace("\u00A0", " ")
    out = {}
    m_iv = re.search(
        r"vigencia\s*[-–—]?\s*inicio\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        t,
        flags=re.IGNORECASE,
    )
    m_ve = re.search(
        r"\bt(?:e|é)rmino\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        t,
        flags=re.IGNORECASE,
    )
    if m_iv:
        iv = _normalize_date_ddmmyyyy(m_iv.group(1))
        if iv:
            out["inicio_vigencia"] = iv
    if m_ve:
        ve = _normalize_date_ddmmyyyy(m_ve.group(1))
        if ve:
            out["vencimiento"] = ve
    if out.get("inicio_vigencia") and out.get("vencimiento"):
        return out
    patterns = [
        r"vigencia\s+(?:inicia|empieza|comienza)\s*(?:el\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})[\s\S]{0,200}?\b(?:y\s+)?(?:vence|venc(?:e|imiento)|finaliza|termina)\s*(?:el\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"\bvigencia\s*[:：]?\s*(?:del\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s*(?:al|a\s*al|-\s*)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",
        r"\bdesde\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})[\s\S]{0,120}?\bhasta\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",
    ]
    for pat in patterns:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if not m:
            continue
        iv = _normalize_date_ddmmyyyy(m.group(1))
        ve = _normalize_date_ddmmyyyy(m.group(2))
        if iv and not out.get("inicio_vigencia"):
            out["inicio_vigencia"] = iv
        if ve and not out.get("vencimiento"):
            out["vencimiento"] = ve
        return out
    return out

def _clean_company_name(raw: str | None) -> Optional[str]:
    if not raw:
        return None
    s = (raw or "").strip()
    # Tomar solo la primera línea
    s = s.splitlines()[0].strip()
    # Ventana: si la línea es muy larga, recortar a 180 caracteres
    s = s[:180]
    # Buscar bloque en mayúsculas típico de razón social
    # Permitir coma para casos "APELLIDOS, NOMBRES"
    m = re.search(r"([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9&,\'\.\- /]{2,160})", s)
    if m:
        s = m.group(1).strip()
    # Normalizar espacios múltiples
    s = re.sub(r"\s{2,}", " ", s)
    # Remover inicial suelta al final (p.ej., ' D' de 'Dirección')
    s = re.sub(r"\s+[A-ZÁÉÍÓÚÑ]$", "", s)
    # Si contiene largas frases en minúsculas (probable texto legal), invalidar
    if re.search(r"[a-z]{2,}\s+[a-z]{2,}", s):
        return None
    return s or None

def extract_razon_social_strict(text: str) -> Optional[str]:
    """Versión estricta: busca en una ventana corta después del rótulo para evitar capturar párrafos."""
    """Versión estricta: busca en una ventana corta después del rótulo para evitar capturar párrafos."""
    patterns = [
        r"Raz[oó]n\s+Social\s*:?",
        r"Nombre\s+o\s+Raz[oó]n\s+Social\s*:?",
        r"Nombres?\s+y\s+Apellidos\s*:?",
    ]
    m_nya = re.search(r"Nombres?\s+y\s+Apellidos\s*:\s*", text, flags=re.IGNORECASE)
    if m_nya:
        win = text[m_nya.end(): m_nya.end() + 360]
        lines = (win or "").splitlines()
        head = " ".join([ln.strip() for ln in lines[:3] if ln.strip()])
        seg = head or (lines[0].strip() if lines else "")
        seg = seg.replace("  ", " ").strip()
        comma_idx = seg.find(",")
        if comma_idx != -1:
            left = seg[:comma_idx].strip()
            right = seg[comma_idx + 1:].strip()
            tok = re.findall(r"[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?", left)
            tok2 = re.findall(r"[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?", right)
            if tok and tok2:
                left_two = " ".join(tok[-2:]) if len(tok) >= 2 else " ".join(tok)
                right_two = " ".join(tok2[:2]) if len(tok2) >= 2 else " ".join(tok2)
                res = f"{left_two}, {right_two}".strip()
                return res
    # Caso específico: "Nombre o Razón Social:" → si hay coma, aplicar 2+2; si no, devolver razón social tal cual
    m_nors = re.search(r"Nombre\s+o\s+Raz[oó]n\s+Social\s*:\s*", text, flags=re.IGNORECASE)
    if m_nors:
        win = text[m_nors.end(): m_nors.end() + 360]
        lines = (win or "").splitlines()
        head = " ".join([ln.strip() for ln in lines[:3] if ln.strip()])
        seg = head or (lines[0].strip() if lines else "")
        seg = seg.replace("  ", " ").strip()
        comma_idx = seg.find(",")
        if comma_idx != -1:
            left = seg[:comma_idx].strip()
            right = seg[comma_idx + 1:].strip()
            tok = re.findall(r"[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?", left)
            tok2 = re.findall(r"[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?", right)
            # Filtrar iniciales de 1 carácter
            tok = [t for t in tok if len(t) > 1]
            tok2 = [t for t in tok2 if len(t) > 1]
            if tok and tok2:
                left_two = " ".join(tok[-2:]) if len(tok) >= 2 else " ".join(tok)
                right_two = " ".join(tok2[:2]) if len(tok2) >= 2 else " ".join(tok2)
                return f"{left_two}, {right_two}".strip()
        # Empresa: usar limpieza estándar
        cleaned = _clean_company_name(seg)
        if cleaned:
            return cleaned
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        window = text[m.end(): m.end() + 360]
        # Unir las primeras líneas por si el nombre está dividido por salto de línea (ej. coma al final)
        lines = (window or "").splitlines()
        head = " ".join([ln.strip() for ln in lines[:3] if ln.strip()])
        name = _clean_company_name(head if head else (lines[0].strip() if lines else ""))
        if not name:
            # Buscar en la ventana el bloque en mayúsculas
            mm = re.search(r"([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9&,\'\.\- /]{2,200})", head or window)
            if mm:
                name = _clean_company_name(mm.group(1))
        if name:
            return name

def extract_moneda_positiva(text: str) -> Optional[str]:
    if not text:
        return None
    t = (text or "").replace("\u00A0", " ")

    def _norm(v: str | None) -> str:
        return re.sub(r"\s+", "", (v or "").upper())

    def _pick(v: str | None) -> Optional[str]:
        tok = _norm(v)
        if not tok:
            return None
        if tok in {"$", "USD", "US$", "U$S", "U$"} or tok.startswith("US$") or tok.startswith("U$S") or "DOL" in tok:
            return "US$"
        if tok.startswith("S/") or tok.startswith("S\\") or tok in {"S", "PEN", "MN", "M/N"} or "SOL" in tok:
            return "S/"
        return None

    t_compact = re.sub(r"\s+", "", t).upper()
    m0 = re.search(r"MONEDA[:：]?(US\$|USD|U\$S|U\$|\$|DOLARES|DÓLARES|DÓLARES|S/\.?|S/|S\\|SOLES|PEN|M/N|MN)", t_compact)
    if m0:
        picked = _pick(m0.group(1))
        if picked:
            return picked

    m = re.search(
        r"\bmoneda\b\s*[:：]?\s*(S\s*\/\s*\.?|S\s*\/|S\\|SOLES|PEN|M\/N|MN|US\s*\$|US\$|USD|U\$\s*S|U\$S|U\$|DOLARES|DÓLARES|DÓLARES|\$)",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        picked = _pick(m.group(1))
        if picked:
            return picked

    m2 = re.search(
        r"Prima\s+Comercial[\s\S]{0,200}?(US\s*\$|US\$|USD|U\$\s*S|U\$S|U\$|\$|S\s*\/\s*\.?|S\s*\/|S\\|SOLES|PEN|M\/N|MN)",
        t,
        flags=re.IGNORECASE,
    )
    if m2:
        picked = _pick(m2.group(1))
        if picked:
            return picked

    t_up = t.upper()
    idx_us = t_up.find("US$")
    idx_uus = t_up.find("U$S")
    idx_u = t_up.find("U$")
    idx_usd = re.search(r"\bUSD\b", t_up)
    idx_dol = re.search(r"\bDOL", t_up)
    idx_s = re.search(r"S\/\.?|S\/\b|S\\|\bSOLES\b|\bPEN\b|\bM\/N\b|\bMN\b|\bSOL", t_up)

    dollar_idxs = [i for i in [
        idx_us if idx_us >= 0 else None,
        idx_uus if idx_uus >= 0 else None,
        idx_u if idx_u >= 0 else None,
        idx_usd.start() if idx_usd else None,
        idx_dol.start() if idx_dol else None,
    ] if i is not None]
    sol_idxs = [idx_s.start()] if idx_s else []

    if not dollar_idxs and not sol_idxs:
        return None
    min_dollar = min(dollar_idxs) if dollar_idxs else 10**9
    min_soles = min(sol_idxs) if sol_idxs else 10**9
    if min_dollar <= min_soles:
        return "US$"
    return "S/"

def extract_agenciamiento_positiva(text: str) -> dict:
    if not text:
        return {}
    monto_pat = r"(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)"
    m = re.search(
        r"Cargo\s+de\s+agenciamiento[\s\S]{0,260}?"
        r"Registro\s*[:：]\s*([A-Z0-9]{3,12})"
        r"[\s\S]{0,120}?"
        r"Monto\s*(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)?\s*" + monto_pat,
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r"Registro\s*[:：]\s*([A-Z0-9]{3,12})"
            r"[\s\S]{0,120}?"
            r"Monto\s*(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)?\s*" + monto_pat,
            text,
            flags=re.IGNORECASE,
        )
    if not m:
        return {}
    reg = (m.group(1) or "").strip()
    monto = _normalize_amount(m.group(2))
    out = {}
    if reg:
        out["registro"] = reg
    if monto:
        out["monto"] = monto
    return out
