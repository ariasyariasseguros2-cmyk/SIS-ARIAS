import re
from typing import Dict, Optional


def _extract_poliza(text: str) -> Optional[str]:
    pats = [r"pol[ií]za\s*([0-9]{3,6})\s*-\s*([0-9]{5,12})", r"p[oó]liza\s*([0-9]{3,6})\s*-\s*([0-9]{5,12})"]
    for p in pats:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return f"{m.group(1)} - {m.group(2)}"
    return None

def _extract_recibo_documentos_generados(text: str) -> Optional[str]:
    m = re.search(r"documento(?:s)?\s+generad(?:o|os)", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        window = text[m.end(): m.end() + 1200]
        nums = re.findall(r"\b(\d{6,15})\b", window)
        if nums:
            return nums[0]
    m2 = re.search(r"documentos?\s+generados?\s*[:\-]?\s*(\d{6,15})", text, flags=re.IGNORECASE)
    if m2:
        return m2.group(1)
    m3 = re.search(r"cronograma", text, flags=re.IGNORECASE)
    if m3:
        window = text[m3.end(): m3.end() + 2000]
        nums = re.findall(r"\b(\d{6,15})\b", window)
        if nums:
            return nums[0]
    return None

def _extract_contratante(text: str) -> Optional[str]:
    # 1) Patrón principal: entre "Contratante :" y "Profesión" (tolerante a saltos y espacios)
    m_global = re.search(r"contratante\s*[:：]\s*(.+?)\bprofesi[oó]n\b", text, flags=re.IGNORECASE | re.DOTALL)
    if m_global:
        block = m_global.group(1)
        for piece in block.splitlines():
            s = piece.strip()
            if s and s not in ("/",) and not s.startswith("S/"):
                return re.sub(r"\s+", " ", s).strip(" :\t\r\n")

    # 2) Si no se halló, acotar al bloque "Condiciones Particulares" y repetir
    seg = text
    mcp = re.search(r"condiciones?\s+particulares", text, flags=re.IGNORECASE)
    if mcp:
        seg = text[mcp.start(): mcp.start() + 2000]

    val = None
    m_between = re.search(r"contratante\s*[:：]\s*(.+?)\bprofesi[oó]n\b", seg, flags=re.IGNORECASE | re.DOTALL)
    if m_between:
        cand = m_between.group(1)
        first_line = ""
        for piece in cand.splitlines():
            s = piece.strip()
            if s:
                first_line = s
                break
        if first_line and first_line not in ("/",) and not first_line.startswith("S/"):
            val = re.sub(r"\s+", " ", first_line).strip(" :\t\r\n")

    if not val:
        m1 = re.search(r"contratante\s*[:：]?\s*([^\n\r]+)", seg, flags=re.IGNORECASE)
        if m1:
            val = m1.group(1)
        else:
            m2 = re.search(r"contratante\s*[:：]?\s*([\s\S]{1,120})", seg, flags=re.IGNORECASE)
            val = m2.group(1).splitlines()[0] if m2 else None
    if not val:
        mp = re.search(r"pol[ií]za\s*[0-9]{3,6}\s*-\s*[0-9]{5,12}", text, flags=re.IGNORECASE)
        if mp:
            tail = text[mp.end():]
            for line in tail.splitlines():
                s = line.strip()
                if not s:
                    continue
                if re.fullmatch(r"contratante\.?", s, flags=re.IGNORECASE):
                    break
                if re.fullmatch(r"\d{4,}", s):
                    continue
                if s == "/" or s.startswith("S/"):
                    continue
                if re.search(r"\b(contratante|d\.?n\.?i\.?|r\.?u\.?c\.?|asegurad[oa]|profesi[oó]n)\b", s, flags=re.IGNORECASE):
                    continue
                if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+){1,}", s):
                    val = s
                    break
    if not val:
        lines = [ln.strip() for ln in text.splitlines()]
        for i, ln in enumerate(lines):
            if re.fullmatch(r"contratante\.?", ln, flags=re.IGNORECASE):
                j = i - 1
                while j >= 0 and not lines[j]:
                    j -= 1
                if j >= 0:
                    cand = lines[j]
                    if cand and not re.fullmatch(r"\d{4,}", cand) and not re.search(r"\b(d\.?n\.?i\.?|r\.?u\.?c\.?|asegurad[oa]|profesi[oó]n)\b", cand, flags=re.IGNORECASE):
                        val = cand
                        break
    if val:
        val = re.split(r"\b(profesi[oó]n|d\.?n\.?i\.?|r\.?u\.?c\.?|asegurad[oa])\b", val, flags=re.IGNORECASE)[0]
        val = re.sub(r"\s+", " ", val).strip(" :\t\r\n")
        if val:
            return val
    return None


def parse_rimac_generales(text: str) -> Dict[str, str]: 
    low = text.lower()
    pol = _extract_poliza(text) or ""
    ramo = "VEHICULAR" if "vehicul" in low else ""
    recibo = _extract_recibo_documentos_generados(text) or ""
    contratante = _extract_contratante(text) or ""
    if contratante.strip() in ("/", "S/"):
        contratante = ""

    item = {
        "numero_poliza": pol,
        "recibo": recibo,
        "ramo": ramo,
        "cia": "Rimac",
    }

    if contratante:
        item["contratante"] = contratante
        item["colectivo_asegurado"] = contratante

    try:
        print("[rimac] numero_poliza:", pol)
        print("[rimac] recibo:", recibo)
        print("[rimac] contratante:", contratante if contratante else "(vacio)")
    except Exception:
        pass

    return {k: v for k, v in item.items() if v}
