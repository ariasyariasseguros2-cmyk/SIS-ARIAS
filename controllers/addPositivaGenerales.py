import re
from typing import Optional

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
    v = re.sub(r"[^\d,\.]", "", s)
    if "," in v and "." in v:
        v = v.replace(",", "")
    elif "," in v and "." not in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return f"{float(v):.2f}"
    except Exception:
        return v or None

def extract_primas_positiva(text: str) -> dict:
    out = {}
    m_block = re.search(
        r"Prima\s+Comercial[\s\S]{0,120}?([0-9][0-9\.,]*)[\s\S]{0,240}?Prima\s+Comercial\s*\+\s*IGV[\s\S]{0,120}?([0-9][0-9\.,]*)",
        text,
        flags=re.IGNORECASE,
    )
    if m_block:
        out['prima_comercial'] = _normalize_amount(m_block.group(1))
        out['prima_comercial_igv'] = _normalize_amount(m_block.group(2))
        return {k: v for k, v in out.items() if v}
    m_pc = re.search(
        r"Prima\s+Comercial[\s:]*[\r\n]*[A-Z$S\/\.\s]*([0-9][0-9\.,]*)",
        text,
        flags=re.IGNORECASE,
    )
    m_pigv = re.search(
        r"Prima\s+Comercial\s*\+\s*IGV[\s:]*[\r\n]*[A-Z$S\/\.\s]*([0-9][0-9\.,]*)",
        text,
        flags=re.IGNORECASE,
    )
    if m_pc:
        out['prima_comercial'] = _normalize_amount(m_pc.group(1))
    if m_pigv:
        out['prima_comercial_igv'] = _normalize_amount(m_pigv.group(1))
    return {k: v for k, v in out.items() if v}

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
