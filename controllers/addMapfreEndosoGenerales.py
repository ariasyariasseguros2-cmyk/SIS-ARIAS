import re
from typing import Dict, Optional


def _money(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return s


def _clean_name(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    out = re.sub(r"\s+(?:RUC\s*)?\d{11}\s*$", "", s, flags=re.IGNORECASE).strip()
    out = re.sub(r"\s+", " ", out)
    return out or None


def _find_after(label_pat: str, text: str, value_pat: str, window: int = 220, flags=re.IGNORECASE) -> Optional[re.Match]:
    for m in re.finditer(label_pat, text, flags):
        frag = text[m.end(): m.end() + window]
        vm = re.search(value_pat, frag, flags)
        if vm:
            return vm
    return None


def _extract_name_from_contratante_block(text_norm: str) -> Optional[str]:
    m_block = re.search(r"DATOS\s+DEL\s+CONTRATANTE", text_norm, re.IGNORECASE)
    if not m_block:
        return None
    subtext = text_norm[m_block.start():]
    lines = [ln.strip() for ln in subtext.splitlines()]
    for i, line in enumerate(lines[:60]):
        if line.upper() == "NOMBRE" or line.upper().startswith("NOMBRE "):
            same_line = re.sub(r"^NOMBRE\s*[:\.]?\s*", "", line, flags=re.IGNORECASE).strip()
            same_line = _clean_name(same_line)
            if same_line and any(c.isalpha() for c in same_line):
                return same_line
            for j in range(i + 1, min(i + 12, len(lines))):
                cand = lines[j].strip()
                if not cand:
                    continue
                cu = cand.upper()
                if cu in {"RUC", "DIRECCIÓN", "DIRECCION", "EMAIL", "TELEFONO", "TELÉFONO", "ACTIVIDAD ECONOMICA", "ACTIVIDAD ECONÓMICA"}:
                    continue
                if "RUC" in cu and len(cu) < 20:
                    continue
                if cand.replace(" ", "").isdigit():
                    continue
                cand = _clean_name(cand)
                if cand and any(c.isalpha() for c in cand):
                    return cand
    return None


def parse_mapfre_endoso_generales(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    text_norm = re.sub(r"\r\n", "\n", text or "")
    low = text_norm.lower()

    m_title = re.search(r"\bSUPLEMENTO\s+DE\s+([A-ZÁÉÍÓÚÑ ]{3,60})", text_norm, re.IGNORECASE)
    if m_title:
        ramo = re.sub(r"\s+", " ", m_title.group(1).strip()).upper()
        item["ramo"] = ramo

    m_pol = re.search(r"\bP[ÓO]LIZA(?!\s+ANTERIOR)\b[\s\S]{0,120}?(\d{8,20})\b", text_norm, re.IGNORECASE)
    if m_pol:
        item["numero_poliza"] = m_pol.group(1)

    m_sup = re.search(r"\bSUPLEMENTO\b\s*(\d{1,6})\b", text_norm, re.IGNORECASE)
    if m_sup:
        item["suplemento"] = m_sup.group(1)

    rucs = re.findall(r"\b(\d{11})\b", text_norm)
    for ruc in rucs:
        if ruc != "20418896915":
            item["ruc_contratante"] = ruc
            break

    name = (
        _extract_name_from_contratante_block(text_norm)
        or _clean_name(re.search(r"\bNOMBRE\b\s*\n\s*([^\n]{3,140})", text_norm, re.IGNORECASE).group(1)) if re.search(r"\bNOMBRE\b\s*\n\s*([^\n]{3,140})", text_norm, re.IGNORECASE) else None
    )
    if name:
        item["colectivo_asegurado"] = name
        item["asegurado"] = name

    date_pat = r"\d{2}/\d{2}/\d{4}"
    money_pat = r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2}))"

    m_vig_pol = _find_after(
        r"VIGENCIA\s+DE\s+P[ÓO]LIZA\b",
        text_norm,
        rf"({date_pat})\s*[-–—]\s*({date_pat})",
        window=260,
    )
    if m_vig_pol:
        item["inicio_vigencia"] = m_vig_pol.group(1)
        item["fin_vigencia"] = m_vig_pol.group(2)
        item["vencimiento"] = m_vig_pol.group(2)
        item["fecha_vencimiento"] = m_vig_pol.group(2)

    m_vig_supl = re.search(
        rf"\bVIGENCIA\b[\s\S]{{0,220}}?({date_pat})[\s\S]{{0,80}}?\bHrs\.[\s\S]{{0,220}}?({date_pat})[\s\S]{{0,80}}?\bHrs\.",
        text_norm,
        re.IGNORECASE,
    )
    if m_vig_supl:
        item["inicio_vigencia_aplicacion"] = m_vig_supl.group(1)
        item["vencimiento_aplicacion"] = m_vig_supl.group(2)

    m_emision = re.search(rf"\bF\.?\s*EMISI[ÓO]N\b[\s\S]{{0,80}}?({date_pat})", text_norm, re.IGNORECASE)
    if not m_emision:
        m_emision = re.search(rf"\bFECHA\s+DE\s+EMISI[ÓO]N\b[\s\S]{{0,80}}?({date_pat})", text_norm, re.IGNORECASE)
    if m_emision:
        item["fecha_emision"] = m_emision.group(1)

    m_mon = _find_after(
        r"\bMONEDA\b",
        text_norm,
        r"\b(US\$|USD|D[ÓO]LARES|SOLES|S\/\.?|PEN)\b",
        window=220,
    )
    if m_mon:
        val = (m_mon.group(1) or "").upper()
        if "US" in val or "DOLAR" in val or "$" in val:
            item["moneda"] = "US$"
        else:
            item["moneda"] = "S/"

    m_pn = re.search(rf"\bPRIMA\s+NETA\b[\s\S]{{0,320}}?{money_pat}", text_norm, re.IGNORECASE)
    if m_pn:
        item["prima_neta"] = _money(m_pn.group(1)) or m_pn.group(1).strip()

    m_pc = re.search(rf"\bPRIMA\s+COMERCIAL\b(?![\s\S]{{0,20}}?\+)[\s\S]{{0,30}}?{money_pat}", text_norm, re.IGNORECASE)
    if m_pc:
        item["prima_comercial"] = _money(m_pc.group(1)) or m_pc.group(1).strip()

    m_pt = re.search(rf"\bPRIMA\s+COMERCIAL\s*\+\s*I\.?\s*G\.?\s*V\.?[\s\S]{{0,30}}?{money_pat}", text_norm, re.IGNORECASE)
    if m_pt:
        total = _money(m_pt.group(1)) or m_pt.group(1).strip()
        item["prima_total"] = total
        item["prima_comercial_igv"] = total
        item["monto"] = total

    try:
        pc = item.get("prima_comercial")
        pt = item.get("prima_total") or item.get("prima_comercial_igv")
        if pc and pt and not item.get("igv"):
            igv_val = float(str(pt).replace(",", "")) - float(str(pc).replace(",", ""))
            if igv_val >= 0:
                item["igv"] = f"{igv_val:.2f}"
    except Exception:
        pass

    if not item.get("ramo"):
        if "embarcacion" in low or "embarcaciones" in low:
            item["ramo"] = "EMBARCACIONES"
        else:
            item["ramo"] = "GENERALES"

    if not item.get("vencimiento") and item.get("fin_vigencia"):
        item["vencimiento"] = item.get("fin_vigencia")
    if not item.get("fecha_vencimiento") and item.get("vencimiento"):
        item["fecha_vencimiento"] = item.get("vencimiento")

    return {k: v for k, v in item.items() if v is not None and str(v).strip() != ""}
