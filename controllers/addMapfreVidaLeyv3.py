import re
from typing import Dict, Optional

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


def parse_mapfre_vidaley_v3(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}

    item["numero_poliza"] = _find(r"P[ÓO]LIZA\s*N[°º]\s*(\d{6,15})", text)
    item["inicio_vigencia"] = _find(r"VIGENCIA\s+DESDE\s+(\d{2}/\d{2}/\d{4})", text)
    item["vencimiento"] = _find(r"VIGENCIA\s+HASTA\s+(\d{2}/\d{2}/\d{4})", text)
    item["fecha_vecimiento"] = item.get("vencimiento")
    item["moneda"] = _find(r"MONEDA\s+(SOLES|USD|PEN|D[ÓO]LARES)", text)
    item["colectivo_asegurado"] = _find(r"Colectivo\s+Asegurado\s*:\s*([^\n]+)", text)
    item["numero_documento_extracted"] = _find(r"Doc\s+ID:\s*RUC\s*(\d{8,11})", text)

    # Fecha de emisión: única fecha suelta en su propia línea, antes de "PÓLIZA Nº"
    m_pol = re.search(r"P[ÓO]LIZA\s*N[°º]\s*\d{6,15}", text, re.IGNORECASE)
    header = text[: m_pol.start()] if m_pol else text[:1000]
    item["fecha_emision"] = _find(r"^\s*(\d{2}/\d{2}/\d{4})\s*$", header)

    prima = _find(r"Prima\s+Comercial\s+(?!\+)([\d.,]+)", text)
    prima_igv = _find(r"Prima\s+Comercial\s*\+\s*IGV\s+([\d.,]+)", text)
    item["prima_comercial"] = _money(prima)
    item["prima_comercial_igv"] = _money(prima_igv)

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
