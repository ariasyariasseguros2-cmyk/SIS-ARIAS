import re
from typing import Dict, Optional

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

def parse_protecta_pension(text: str) -> Dict[str, str]:
    item: Dict[str, str] = {}
    #print("parse_protecta_pension", text)
    print("parse_protecta_pension", text.splitlines())

    # Póliza: por label directo (evitar capturar RUC u otras cifras)
    item["numero_poliza"] = _find(r"P[oó]liza\s*(?:No\.?|N[°º])\s*[:：]?\s*([0-9]{6,12})", text)

    # Fallback fuerte: usar el encabezado "RIESGO - PENSIONES CONDICIONES PARTICULARES" y tomar la siguiente línea numérica
    if not item.get("numero_poliza"):
        m_hdr = re.search(
            r"RIESGO\s*-\s*PENSIONES\s*CONDICIONES\s+PARTICULARES.*?\n\s*([0-9]{6,12})\b",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if m_hdr:
            item["numero_poliza"] = m_hdr.group(1)

    # Fallback genérico: primera línea de 8–12 dígitos que no sea RUC ni esté en contexto de "RUC"
    if not item.get("numero_poliza"):
        for m in re.finditer(r"^\s*([0-9]{8,12})\s*$", text, re.MULTILINE):
            candidate = m.group(1)
            if len(candidate) == 11:
                continue
            prev_ctx = text[max(0, m.start() - 40): m.start()]
            if re.search(r"RUC", prev_ctx, re.IGNORECASE):
                continue
            item["numero_poliza"] = candidate
            break

    # Fecha de Emisión: por label; si no aparece, buscar la primera fecha después del número de póliza
    if not item.get("fecha_emision"):
        item["fecha_emision"] = (
            _find(r"Fecha\s+de\s+Emisi[oó]n\s*[:：]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
            or _find(r"Fecha\s+de\s+Emisi[oó]n[^\d]{0,800}([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        )

    if not item.get("fecha_emision") and item.get("numero_poliza"):
        m_np = re.search(re.escape(item["numero_poliza"]), text)
        if m_np:
            tail = text[m_np.end(): m_np.end() + 300]
            m_date = re.search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", tail)
            if m_date:
                item["fecha_emision"] = m_date.group(1)

    # Vigencia: patrón tolerante que une "Desde ... fecha ... Hasta ... fecha" con saltos grandes
    m_desde_hasta = re.search(
        r"Desde[^\d]{0,1200}([0-9]{2}/[0-9]{2}/[0-9]{4}).*?Hasta[^\d]{0,1200}([0-9]{2}/[0-9]{2}/[0-9]{4})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m_desde_hasta:
        item["inicio_vigencia"] = m_desde_hasta.group(1)
        item["vencimiento"] = m_desde_hasta.group(2)

    # NUEVO: capturar el par de fechas tras "RIESGO - PENSIONES CONDICIONES PARTICULARES"
    if not item.get("inicio_vigencia") or not item.get("vencimiento"):
        m_hdr2 = re.search(r"RIESGO\s*-\s*PENSIONES\s*CONDICIONES\s+PARTICULARES", text, re.IGNORECASE)
        if m_hdr2:
            tail = text[m_hdr2.end(): m_hdr2.end() + 800]
            dates_pair = re.findall(r"\b([0-9]{2}/[0-9]{2}/[0-9]{4})\b", tail)
            if len(dates_pair) >= 2:
                item["inicio_vigencia"] = item.get("inicio_vigencia") or dates_pair[0]
                item["vencimiento"] = item.get("vencimiento") or dates_pair[1]

    # Fallbacks independientes para "Desde" y "Hasta"
    if not item.get("inicio_vigencia"):
        m_desde = re.search(r"Desde", text, re.IGNORECASE)
        if m_desde:
            tail = text[m_desde.end(): m_desde.end() + 1200]
            m_date = re.search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", tail)
            if m_date:
                item["inicio_vigencia"] = m_date.group(1)

    if not item.get("vencimiento"):
        m_hasta = re.search(r"Hasta", text, re.IGNORECASE)
        if m_hasta:
            tail = text[m_hasta.end(): m_hasta.end() + 1600]
            dates = re.findall(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", tail)
            if dates:
                if item.get("inicio_vigencia") and len(dates) > 1 and dates[0] == item["inicio_vigencia"]:
                    item["vencimiento"] = dates[1]
                else:
                    item["vencimiento"] = dates[-1]

    # Ajuste final: si vencimiento == inicio, elegir la siguiente fecha distinta y mayor en la ventana de "Hasta"
    if item.get("inicio_vigencia") and item.get("vencimiento") == item["inicio_vigencia"]:
        m_hasta2 = re.search(r"Hasta", text, re.IGNORECASE)
        if m_hasta2:
            tailh = text[m_hasta2.end(): m_hasta2.end() + 1600]
            ds = re.findall(r"\b([0-9]{2}/[0-9]{2}/[0-9]{4})\b", tailh)
            def _ymd(d: str) -> int:
                dd, mm, yyyy = d.split("/")
                return int(f"{yyyy}{mm}{dd}")
            for d in ds:
                if d != item["inicio_vigencia"] and _ymd(d) >= _ymd(item["inicio_vigencia"]):
                    item["vencimiento"] = d
                    break

    # Asegurados (multilínea)
    m_aseg = re.search(
        r"Asegurados?\s*:\s*(.+?)(?:\nCoberturas|\nRIESGO|\n3\.-|\nVigencia|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m_aseg:
        item["colectivo_asegurado"] = re.sub(r"\s+", " ", m_aseg.group(1)).strip()

    # Ramo y Moneda
    ramo = _find(r"Ramo\s*:\s*([^\n]+)", text)
    if not ramo and "sctr pens" in text.lower():
        ramo = "SCTR PENSIÓN"
    if ramo:
        item["ramo"] = ramo

    moneda = _find(r"Moneda(?:\s+del\s+Contrato)?\s*:\s*([A-Za-z\/\.$]+)", text)
    if moneda:
        m = moneda.strip().upper()
        if re.match(r"^S\s*\/\s*\.?$", m) or m in ("SOLES", "PEN", "SOL", "S/"):
            item["moneda"] = "SOLES"
        elif m in ("USD", "US$", "$", "DOLARES", "DÓLARES"):
            item["moneda"] = "USD"
        else:
            item["moneda"] = moneda

    # Prima Comercial y +IGV (con fallback por terna)
    pc = _money(_find(r"PRIMA\s+COMERCIAL\s*:\s*S?\/?\s*([0-9\.,]+)", text))
    igv = _money(_find(r"I\.?G\.?V\.?\s*:\s*S?\/?\s*([0-9\.,]+)", text))
    total = _money(_find(r"PRIMA\s+COMERCIAL\s+TOTAL\s*:\s*S?\/?\s*([0-9\.,]+)", text))
    item["prima_comercial"] = pc
    if not total and pc and igv:
        try:
            total = f"{float(pc.replace(',', '.')) + float(igv.replace(',', '.')):.2f}"
        except Exception:
            pass
    item["prima_comercial_igv"] = total

    if not item.get("prima_comercial"):
        search_after = text
        m_princ = re.search(r"PRINCIPAL", text, re.IGNORECASE)
        if m_princ:
            search_after = text[m_princ.start(): m_princ.start() + 600]
        triples = re.findall(
            r"\b([0-9]+(?:[.,][0-9]+)?)\b[\s\n]+([0-9]+(?:[.,][0-9]+)?)\b[\s\n]+([0-9]+(?:[.,][0-9]+)?)\b",
            search_after,
        )
        for a, b, c in triples:
            try:
                va, vb, vc = float(a.replace(",", ".")), float(b.replace(",", ".")), float(c.replace(",", "."))
                if 0.17 <= vb / va <= 0.19 and abs((va + vb) - vc) < 0.5:
                    item["prima_comercial"] = f"{va:.2f}".rstrip("0").rstrip(".")
                    item["prima_comercial_igv"] = f"{vc:.2f}".rstrip("0").rstrip(".")
                    break
            except Exception:
                continue

    return {k: _clean(v) for k, v in item.items() if v}