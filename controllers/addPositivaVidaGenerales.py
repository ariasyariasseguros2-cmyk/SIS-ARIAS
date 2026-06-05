import re
from typing import Optional, Dict
from datetime import datetime

def _find(pattern: str, text: str, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    if not m: return None
    # Si el patrón tiene un grupo, intentar capturarlo
    try:
        val = m.group(1).strip()
        if val: return val
    except:
        pass
    
    # Si no hay grupo o está vacío, buscar en las líneas siguientes (fallback para etiquetas solas)
    tail = text[m.end():]
    for line in tail.splitlines():
        line = re.sub(r'^[:：\s]*', '', line).strip()
        if line: return line
    return None

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    raw0 = str(s)
    raw = raw0.replace("−", "-").replace("–", "-").replace("—", "-")
    m = re.search(r"(\(?\s*(?:-\s*)?[0-9][0-9\.,\s]*\s*\)?)", raw)
    if not m: return None
    
    v = m.group(1).strip()
    neg = False
    mp = re.match(r"^\((.*)\)$", v)
    if mp:
        neg = True
        v = (mp.group(1) or "").strip()
    if re.match(r"^\s*-\s*", v):
        neg = True
    v = re.sub(r"[^\d,\.]", "", v)
    v = v.replace(" ", "")
    if "," in v and "." in v:
        if v.rfind(",") > v.rfind("."): # Caso 1.234,56
            v = v.replace(".", "").replace(",", ".")
        else: # Caso 1,234.56
            v = v.replace(",", "")
    elif "," in v: # Caso 1234,56
        v = v.replace(",", ".")
        
    try:
        num = float(v)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except:
        return v

_MONEY_2DP_RE = re.compile(r"(\(?\s*(?:[-−–—]\s*)?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\s*\)?)")

def _money_candidates_near(label_pattern: str, text: str, window: int = 350) -> list[str]:
    m = re.search(label_pattern, text, re.IGNORECASE)
    if not m:
        return []
    seg = text[m.end(): m.end() + max(0, int(window))]
    out: list[str] = []
    for mm in _MONEY_2DP_RE.finditer(seg):
        val = _money(mm.group(1))
        if val:
            out.append(val)
    return out

def _extract_line(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    line = m.group(0)
    line = re.sub(r"[\r\n]+", " ", line).strip()
    return line or None

def _money_from_line(line: Optional[str]) -> Optional[str]:
    if not line:
        return None
    cands = [mm.group(1) for mm in _MONEY_2DP_RE.finditer(line)]
    if not cands:
        return None
    return _money(cands[-1])

def _to_float(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None

def _looks_like_person_or_company_name(s: Optional[str]) -> bool:
    if not s:
        return False
    v = re.sub(r"\s+", " ", (s or "")).strip()
    if len(v) < 3 or len(v) > 180:
        return False
    low = v.lower()
    if re.search(r"[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}", v):
        return False
    if any(k in low for k in [
        "incumplimiento",
        "obligaciones",
        "procedimientos",
        "proporcionalidad",
        "en caso que",
        "comercializada",
        "banca seguros",
        "cláusula",
        "clausula",
        "ley del contrato de seguro",
        "art.",
        "artículo",
    ]):
        return False
    return True

def _extract_name_strict(text: str) -> Optional[str]:
    try:
        from controllers.addPositivaGenerales import extract_razon_social_strict, extract_razon_social, _clean_company_name
        name = extract_razon_social_strict(text) or extract_razon_social(text)
        cleaned = _clean_company_name(name) if name else None
        return cleaned or (name.strip() if name else None)
    except Exception:
        return None

def parse_positiva_vida_generales(text: str) -> Dict[str, str]:
    item = {}
    
    # Póliza
    poliza = (
        _find(r"P[oó]liza\s*N(?:ro\.?|[°º]|o)?\s*[:：]?\s*([0-9]{6,20})", text)
        or _find(r"\bP[oó]liza\b[\s\S]{0,100}?N(?:ro\.?|[°º]|o)\s*[:：]?\s*([0-9]{6,20})", text)
        or _find(r"RESPONSABILIDAD\s+CIVIL\s+N[°ºo]?\s*([0-9]{6,20})", text)
    )
    item['numero_poliza'] = poliza

    # Proforma / Recibo
    proforma = (
        _find(r"Proforma\s*N(?:ro\.?|[°º]|o)?\s*[:：]?\s*([0-9]{6,20})", text)
        or _find(r"N[uú]mero\s+de\s+Proforma\s*[:：]?\s*([0-9A-Z\-]+)", text)
    )
    item['recibo'] = proforma

    # Ramo
    ramo = (
        _find(r"Ramo\s*[:：]\s*(.+)", text)
        or _find(r"seguro\s+de\s+(RESPONSABILIDAD\s+CIVIL|TRANSPORTES)", text)
    )
    item['ramo'] = ramo

    # Vigencias
    vig_inicio = (
        _find(r"Vigencia-Inicio\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
        or _find(r"vigencia\s+inicia\s*(\d{2}/\d{2}/\d{4})", text)
    )
    vig_fin = (
        _find(r"T[ée]rmino\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
        or _find(r"vence\s+el\s*(\d{2}/\d{2}/\d{4})", text)
    )
    
    if not vig_inicio:
        m_vig = re.search(r"vigencia\s*[:：]?\s*(?:del\s*)?(\d{2}/\d{2}/\d{4})\s*(?:al|a)\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if m_vig:
            vig_inicio = m_vig.group(1)
            vig_fin = m_vig.group(2)
            
    item['inicio_vigencia'] = vig_inicio
    item['vencimiento'] = vig_fin

    # Asegurado / Contratante
    asegurado = _extract_name_strict(text)
    if not asegurado:
        m_blk = re.search(r"Datos\s+del\s+Asegurado\b", text, re.IGNORECASE)
        if m_blk:
            win = text[m_blk.end(): m_blk.end() + 900]
            cand = (
                _find(r"Nombres?\s+y\s+Apellidos\s*[:：]?\s*(.+)", win)
                or _find(r"Nombre\s+o\s+Raz[oó]n\s+Social\s*[:：]?\s*(.+)", win)
            )
            if _looks_like_person_or_company_name(cand):
                asegurado = re.sub(r"\s+", " ", cand).strip()

    hola_name = _find(r"Hola\s+([^:：!\n\r]{2,50})[:：!]", text)
    if hola_name:
        hola_name = re.sub(r"\s+", " ", hola_name).strip()

    contratante = None
    m_blk_c = re.search(r"Datos\s+del\s+Contratante\b", text, re.IGNORECASE)
    if m_blk_c:
        win = text[m_blk_c.end(): m_blk_c.end() + 900]
        cand_c = (
            _find(r"Nombres?\s+y\s+Apellidos\s*[:：]?\s*(.+)", win)
            or _find(r"Nombre\s+o\s+Raz[oó]n\s+Social\s*[:：]?\s*(.+)", win)
        )
        if _looks_like_person_or_company_name(cand_c):
            contratante = re.sub(r"\s+", " ", cand_c).strip()

    if not asegurado:
        cand = _find(r"Asegurado\s*[:：]\s*(.+)", text)
        if _looks_like_person_or_company_name(cand):
            asegurado = re.sub(r"\s+", " ", cand).strip()
    if not contratante:
        cand = _find(r"Contratante\s*[:：]\s*(.+)", text)
        if _looks_like_person_or_company_name(cand):
            contratante = re.sub(r"\s+", " ", cand).strip()

    final_name = asegurado or contratante or (hola_name if _looks_like_person_or_company_name(hola_name) else None)
    item['colectivo_asegurado'] = final_name
    item['contratante'] = contratante or final_name

    # Dirección
    direccion = _find(r"Direcci[oó]n\s*[:：]\s*(.+)", text)
    if direccion:
        item['direccion'] = direccion

    # Moneda
    moneda = None
    # Buscar moneda cerca de las primas
    m_mon = re.search(r"Prima\s+Comercial[\s\S]{0,150}?(US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)", text, re.IGNORECASE)
    if m_mon:
        tok = re.sub(r"\s+", "", m_mon.group(1).upper())
        if "US" in tok or "USD" in tok or tok == "$" or "DOL" in tok:
            moneda = "US$"
        else:
            moneda = "S/"
    
    if not moneda:
        # Buscar "Moneda: ..."
        m_mon2 = re.search(r"Moneda\s*[:：]\s*([^\n]+)", text, re.IGNORECASE)
        if m_mon2:
            tok = m_mon2.group(1).upper()
            if "DOL" in tok or "US" in tok or "$" in tok:
                moneda = "US$"
            else:
                moneda = "S/"
                
    item['moneda'] = moneda

    # Primas
    pc_igv_best: Optional[str] = None
    igv_line = _extract_line(text, r"^\s*Prima\s+Comercial\s*\+\s*IGV\b[^\n\r]*")
    pc_igv_best = _money_from_line(igv_line)
    if not pc_igv_best:
        igv_cands = _money_candidates_near(r"Prima\s+Comercial\s*\+\s*IGV", text)
        if igv_cands:
            pc_igv_best = igv_cands[0]
        else:
            pc_igv = _find(r"Prima\s+Comercial\s*\+\s*IGV[\s\S]{0,50}?(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)", text)
            pc_igv_best = _money(pc_igv)

    pc_best: Optional[str] = None
    pc_line = _extract_line(text, r"^\s*Prima\s+Comercial(?!\s*\+)\b[^\n\r]*")
    pc_best = _money_from_line(pc_line)
    if not pc_best:
        pc_cands = _money_candidates_near(r"Prima\s+Comercial(?!\s*\+)", text)
        if pc_cands:
            if pc_igv_best:
                tot = _to_float(pc_igv_best)
                expected = (tot / 1.18) if tot and tot > 0 else None
                if expected:
                    best = None
                    best_err = None
                    for v in pc_cands:
                        vf = _to_float(v)
                        if vf is None:
                            continue
                        err = abs(vf - expected)
                        if best_err is None or err < best_err:
                            best_err = err
                            best = v
                    pc_best = best or pc_cands[0]
                else:
                    pc_best = pc_cands[0]
            else:
                pc_best = pc_cands[0]
        else:
            pc = _find(r"Prima\s+Comercial(?!\s*\+)[\s\S]{0,50}?(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9\.,]*\s*\)?)", text)
            pc_best = _money(pc)

    pc_num = _to_float(pc_best)
    tot_num = _to_float(pc_igv_best)
    if tot_num and tot_num > 0:
        expected = tot_num / 1.18
        if pc_num is None:
            pc_best = f"{expected:.2f}"
        else:
            rel = abs(pc_num - expected) / expected if expected > 0 else 0
            if rel > 0.02:
                pc_best = f"{expected:.2f}"

    item['prima_comercial'] = pc_best
    item['prima_comercial_igv'] = pc_igv_best

    # Fecha Emisión
    emision = _find(r"Emisi[oó]n\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
    item['fecha_emision'] = emision

    # Fecha Vencimiento (de la proforma/recibo)
    f_venc = _find(r"Fecha\s+de\s+Vencimiento\s*[:：]\s*(\d{2}/\d{2}/\d{4})", text)
    item['fecha_vencimiento'] = f_venc

    m_com = re.search(
        r"Registro\s*[:：]?\s*[A-Z0-9]{3,10}[\s\S]{0,80}?"
        r"Monto\s*(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/|SOLES|PEN)?\s*"
        r"([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})\b",
        text,
        re.IGNORECASE,
    )
    if m_com:
        val = _money(m_com.group(1))
        if val:
            item["comision_compania_importe"] = val

    return {k: v for k, v in item.items() if v}
