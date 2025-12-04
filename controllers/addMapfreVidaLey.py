import re
from typing import Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

def _canon(text: str) -> str:
    return re.sub(r"\s+", " ", text)

def _find_after(label_pat: str, text: str, value_pat: str, window: int = 2000, flags=re.IGNORECASE) -> Optional[str]:
    for m in re.finditer(label_pat, text, flags):
        frag = text[m.end(): m.end() + window]
        vm = re.search(value_pat, frag, flags)
        if vm:
            return vm.group(1).strip()
    return None

def parse_mapfre_vidaley(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    flat = _canon(text)

    # Stream global: valores que vienen después del run de ":" (fuera del bloque)
    def _extract_values_stream_after_colons(flat_text: str) -> Dict[str, Optional[str]]:
        out: Dict[str, Optional[str]] = {}
        run = re.search(r"(?:\s*:\s*){10,}", flat_text)  # aparecen ~13 ':'
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

        COMPANY  = r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.&']{6,})"
        ADDRESS  = r"([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9 \.\-]+?)\s+(?=\d{4,6}\s*-\s)"
        ACTIVITY = r"(\d{4,6}\s*-\s+[A-Z0-9ÁÉÍÓÚÑ \.\-]+?)\s+(?=[A-ZÁÉÍÓÚÑ])"
        DATE     = r"([0-9]{2}/[0-9]{2}/[0-9]{4})"
        CURR     = r"\b(SOLES|USD|PEN|DOLARES|D[ÓO]LARES)\b"
        MONEY    = r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2}))"

        # Condiciones particulares (orden observado en tu flat)
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

        # Fila de importes (Categoría, Nro.Aseg., Monto Base, Tasa, Prima Resultante)
        _categoria  = take(r"([A-ZÁÉÍÓÚÑ0-9<=> \$\.\-]+?)\s+(?=\d+\s)")
        _nroaseg    = take(r"(\d+)")
        _montobase  = take(MONEY)
        _tasa       = take(r"([0-9]+(?:[.,][0-9]+))")
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

    cond = _extract_values_stream_after_colons(flat)

    # Póliza y recibo (solo fallback mínimo con etiquetas si hiciera falta)
    item["numero_poliza"] = cond.get("numero_poliza") or _find_after(r"N[ÚU]MERO\s+DE\s+P[ÓO]LIZA\b", flat, r"([0-9]{6,15})", window=4000)
    rec_raw = cond.get("recibo") or _find_after(r"\bRECIBO\b", flat, r"([0-9]{6,12})", window=4000)
    if rec_raw and item.get("numero_poliza") and rec_raw == item["numero_poliza"]:
        rec_raw = None
    item["recibo"] = rec_raw

    # Condiciones
    item["colectivo_asegurado"] = cond.get("colectivo_asegurado")
    item["inicio_vigencia"] = cond.get("inicio_vigencia")
    item["vencimiento"] = cond.get("vencimiento")
    item["ultimo_dia_pago"] = cond.get("ultimo_dia_pago")
    item["fecha_emision"] = cond.get("fecha_emision")
    item["moneda"] = cond.get("moneda")
    item["ramo"] = cond.get("actividad")
    item["forma_pago"] = _find(r"Forma\s+de\s+Pago\s*:\s*([A-ZÁÉÍÓÚÑ0-9 \.\-]+)", flat)

    # Importes
    item["prima_comercial"] = _money(cond.get("prima_resultante")) or _money(_find(r"Prima\s+Comercial\s*:\s*S?\/?\s*([0-9\.,]+)", flat))
    item["prima_comercial_igv"] = _money(_find(r"Prima\s+Comercial\s*\+\s*IGV\s*:\s*S?\/?\s*([0-9\.,]+)", flat)) or _money(_find(r"(?:Importe\s+Total|Total)\s*:\s*S?\/?\s*([0-9\.,]+)", flat))
    print("item", item)
    return {k: _clean(v) for k, v in item.items() if v}
    

