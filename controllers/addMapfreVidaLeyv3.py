import re
from typing import Dict, Optional, Tuple

# Formato "carta de bienvenida" de Mapfre Vida Ley: etiquetas sueltas por línea
# (VIGENCIA DESDE / VIGENCIA HASTA / PÓLIZA Nº ...), sin los dos puntos ":" que
# usan los formatos anteriores (addMapfreVidaLey / v2). Ver uploads/nuevoparserpdf/.


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.MULTILINE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    tok = re.sub(r"[^\d,\.]", "", s)
    if "," in tok and "." in tok:
        tok = tok.replace(",", "") if tok.rfind(".") > tok.rfind(",") else tok.replace(".", "").replace(",", ".")
    elif "," in tok:
        tok = tok.replace(".", "").replace(",", ".")
    try:
        return f"{float(tok):.2f}"
    except Exception:
        return None


def _extract_amount_after_label(text: str, label_pat: str, max_lines: int = 4) -> Optional[str]:
    money_pat = r"(\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]+)?\s*\)?)"
    lines = text.splitlines()
    label_re = re.compile(rf"{label_pat}(?:\s*[:：])?(?:\s*S?\/?\.?)?\s*(.*)$", re.IGNORECASE)
    for i, raw_line in enumerate(lines):
        line = _clean(raw_line)
        if not line:
            continue

        same_line = label_re.search(line)
        if same_line:
            suffix = _clean(same_line.group(1))
            if suffix:
                amounts = re.findall(money_pat, suffix, re.IGNORECASE)
                if amounts:
                    return _money(amounts[-1])
        elif not re.fullmatch(rf"{label_pat}\s*:?", line, re.IGNORECASE):
            continue

        for cand_raw in lines[i + 1:i + 1 + max_lines]:
            cand = _clean(cand_raw)
            if not cand or cand == ":":
                continue
            if re.search(r"Prima\s+Comercial", cand, re.IGNORECASE):
                break
            if label_re.search(cand):
                break
            m = re.search(money_pat, cand, re.IGNORECASE)
            if m:
                return _money(m.group(1))
    return None


def _extract_prima_pair(text: str) -> Tuple[Optional[str], Optional[str]]:
    money_pat = r"(\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]+)?\s*\)?)"
    label_re = re.compile(
        rf"^Prima\s+Comercial(\s*\+\s*(?:I\s*G\s*V)?)?\s*:?\s*({money_pat})?$",
        re.IGNORECASE,
    )

    lines = [_clean(line) for line in text.splitlines()]
    label_entries: list[tuple[int, str, Optional[str]]] = []

    for idx, line in enumerate(lines):
        if not line:
            continue
        m = label_re.match(line)
        if not m:
            continue
        label_type = "total" if m.group(1) else "base"
        inline_amount = _money(m.group(2)) if m.group(2) else None
        label_entries.append((idx, label_type, inline_amount))

    if not label_entries:
        return None, None

    relevant = label_entries[-2:] if len(label_entries) >= 2 else label_entries
    label_indexes = {idx for idx, _, _ in label_entries}
    found: dict[str, str] = {}

    for idx, label_type, inline_amount in relevant:
        if inline_amount:
            found[label_type] = inline_amount
            continue

        for j in range(idx + 1, min(len(lines), idx + 6)):
            cand = lines[j]
            if not cand or cand == ":":
                continue
            if j in label_indexes:
                break
            m = re.fullmatch(money_pat, cand, re.IGNORECASE)
            if m:
                found[label_type] = _money(m.group(1))
                break

    if found.get("base") and found.get("total"):
        return found.get("base"), found.get("total")

    start = relevant[0][0]
    end = min(len(lines), relevant[-1][0] + 8)
    region_lines = lines[start:end]
    region_labels = [label_type for _, label_type, _ in relevant]
    region_amounts: list[str] = []

    for line in region_lines:
        if not line or line == ":":
            continue
        if label_re.match(line):
            m_inline = re.search(money_pat, line, re.IGNORECASE)
            if m_inline:
                region_amounts.append(_money(m_inline.group(1)))
            continue
        m = re.fullmatch(money_pat, line, re.IGNORECASE)
        if m:
            region_amounts.append(_money(m.group(1)))

    mapped: dict[str, str] = {}
    for label_type, amount in zip(region_labels, region_amounts):
        mapped[label_type] = amount

    return mapped.get("base") or found.get("base"), mapped.get("total") or found.get("total")


def parse_mapfre_vidaley_v3(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}

    item["numero_poliza"] = _find(r"P[ÓO]LIZA\s*N[°º]\s*(\d{6,15})", text)
    item["inicio_vigencia"] = _find(r"VIGENCIA\s+DESDE\s+(\d{2}/\d{2}/\d{4})", text)
    item["vencimiento"] = _find(r"VIGENCIA\s+HASTA\s+(\d{2}/\d{2}/\d{4})", text)
    item["fecha_vecimiento"] = item.get("vencimiento")
    item["moneda"] = _find(r"MONEDA\s+(SOLES|USD|PEN|D[ÓO]LARES)", text)
    item["colectivo_asegurado"] = _find(r"Colectivo\s+Asegurado\s*:\s*([^\n]+)", text)
    if item.get("colectivo_asegurado"):
        item["asegurado"] = item["colectivo_asegurado"]
    item["numero_documento_extracted"] = _find(r"Doc\s+ID:\s*RUC\s*(\d{8,11})", text)

    # Fecha de emisión: única fecha suelta en su propia línea, antes de "PÓLIZA Nº"
    m_pol = re.search(r"P[ÓO]LIZA\s*N[°º]\s*\d{6,15}", text, re.IGNORECASE)
    header = text[: m_pol.start()] if m_pol else text[:1000]
    item["fecha_emision"] = _find(r"^\s*(\d{2}/\d{2}/\d{4})\s*$", header)

    prima_base = _extract_amount_after_label(text, r"Prima\s+Comercial(?!\s*\+)")
    prima_total = _extract_amount_after_label(text, r"Prima\s+Comercial\s*\+\s*(?:I\s*G\s*V)?")
    item["prima_comercial"] = (
        prima_base
    )
    item["prima_comercial_igv"] = (
        prima_total
    )
    try:
        pc = float(item["prima_comercial"]) if item.get("prima_comercial") else None
        pt = float(item["prima_comercial_igv"]) if item.get("prima_comercial_igv") else None
        if pc is not None and pt is not None and pc > pt:
            item["prima_comercial"], item["prima_comercial_igv"] = item["prima_comercial_igv"], item["prima_comercial"]
    except Exception:
        pass

    item["ramo"] = "VIDA - LEY"
    if re.search(r"\bEMPLEADOS\b", text, re.IGNORECASE):
        item["ramos_producto"] = "EMPLEADOS"

    return {k: _clean(v) for k, v in item.items() if v}


def _demo():
    sample = """15/07/2026
DIRECCIÓN ARMENDÁRIZ N° 345, MIRAFLORES
PÓLIZA Nº 6102600024581
VIGENCIA DESDE 09/06/2026
VIGENCIA HASTA 09/06/2027
TIPO Emisión
MONEDA SOLES
CONDICIONES PARTICULARES
DATOS DEL CONTRATANTE TITULAR
Contratante: N & N TEXTILES E.I.R.L. Doc ID: RUC 20600572939
Colectivo Asegurado: N & N TEXTILES E.I.R.L.
Categoría Tasa
EMPLEADOS SLDO<= US$3825 0.340000000%
PRIMAS IMPORTE
Prima Comercial 209.30
Prima Comercial + IGV 246.97
"""
    item = parse_mapfre_vidaley_v3(sample)
    assert item["numero_poliza"] == "6102600024581", item
    assert item["inicio_vigencia"] == "09/06/2026", item
    assert item["vencimiento"] == "09/06/2027", item
    assert item["moneda"] == "SOLES", item
    assert item["colectivo_asegurado"] == "N & N TEXTILES E.I.R.L.", item
    assert item["numero_documento_extracted"] == "20600572939", item
    assert item["fecha_emision"] == "15/07/2026", item
    assert item["prima_comercial"] == "209.30", item
    assert item["prima_comercial_igv"] == "246.97", item
    assert item["ramo"] == "VIDA - LEY", item
    assert item["ramos_producto"] == "EMPLEADOS", item
    print("OK")


if __name__ == "__main__":
    _demo()
