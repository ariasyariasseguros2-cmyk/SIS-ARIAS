import re
from typing import Dict, Optional


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _money_value(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2})?)", s)
    if not m:
        return None
    raw = m.group(1)
    if raw.count(",") == 1 and raw.count(".") == 0:
        raw = raw.replace(",", ".")
    raw = raw.replace(",", "")
    try:
        return f"{float(raw):.2f}"
    except Exception:
        return m.group(1)


def _normalize_moneda(moneda_raw: Optional[str]) -> Optional[str]:
    if not moneda_raw:
        return None
    up = re.sub(r"\s+", "", moneda_raw.replace("\u00A0", " ").upper())
    if not up:
        return None
    if "DOL" in up or "USD" in up or up.startswith("US$") or up == "$":
        return "US$"
    if "SOL" in up or up.startswith("S/") or up.startswith("S/.") or up == "PEN":
        return "S/"
    return moneda_raw.strip()


def _lines_after_marker(text: str, marker: str, max_lines: int = 12) -> list[str]:
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    marker_low = marker.lower()
    for i, ln in enumerate(lines):
        if marker_low in ln.lower():
            return [ln for ln in lines[i + 1:i + 1 + max_lines] if ln]
    return []


def _lines_after_tokens(text: str, tokens: list[str], max_lines: int = 12) -> list[str]:
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    tokens_low = [t.lower() for t in tokens if t]
    for i, ln in enumerate(lines):
        low = ln.lower()
        if all(t in low for t in tokens_low):
            return [ln for ln in lines[i + 1:i + 1 + max_lines] if ln]
    return []


def parse_protecta_pension_condiciones(text: str) -> Dict[str, str]:
    """
    Parser para Condiciones Particulares SCTR Pensiones de Protecta.
    """
    poliza = _find(r"(?:P[o\u00f3]liza|Pliza)\s*No\.?[:]?\s*(\d{6,})", text)
    ramo_raw = _find(r"Ramo:\s*([^\r\n]+)", text) or ""
    moneda = _normalize_moneda(_find(r"Moneda\s+del\s+Contrato:\s*([^\r\n]+)", text))
    fecha_emision = _find(r"Fecha\s+de\s+Emisi[o\u00f3]n:\s*(\d{2}/\d{2}/\d{4})", text)

    inicio_vigencia = _find(
        r"Vigencia\s+de\s+la\s+Cobertura:.*?Desde:\s*(\d{2}/\d{2}/\d{4})",
        text,
    )
    vencimiento = _find(
        r"Vigencia\s+de\s+la\s+Cobertura:.*?Hasta:\s*(\d{2}/\d{2}/\d{4})",
        text,
    )

    contratante = _find(r"Contratante:\s*([^\r\n]+)", text)
    ruc_contratante = _find(r"Contratante:.*?Ruc\s*:\s*(\d{11})", text)

    # Fallback: algunos PDFs traen los datos despues del titulo 'CONDICIONES PARTICULARES'
    if not (poliza and fecha_emision and contratante and ruc_contratante):
        block_lines = _lines_after_tokens(text, ["condiciones", "particulares", "pension"], max_lines=16)
        if not block_lines:
            block_lines = _lines_after_marker(text, "CONDICIONES PARTICULARES", max_lines=16)
        if block_lines:
            if not poliza:
                m_pol = re.search(r"\b(\d{6,})\b", block_lines[0])
                if m_pol:
                    poliza = m_pol.group(1)
            if not fecha_emision:
                dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", "\n".join(block_lines))
                if dates:
                    fecha_emision = dates[0]
            if not contratante and len(block_lines) > 2:
                contratante = block_lines[2]
            if not ruc_contratante:
                if len(block_lines) > 3:
                    m_ruc = re.search(r"\b(\d{8,11})\b", block_lines[3])
                    if m_ruc:
                        ruc_contratante = m_ruc.group(1)
                if not ruc_contratante:
                    m_ruc = re.search(r"\b(\d{8,11})\b", "\n".join(block_lines))
                    if m_ruc and m_ruc.group(1) not in {"20517207331", poliza or ""}:
                        ruc_contratante = m_ruc.group(1)
            if not inicio_vigencia or not vencimiento:
                dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", "\n".join(block_lines))
                if len(dates) > 1 and not inicio_vigencia:
                    inicio_vigencia = dates[1]
                if len(dates) > 2 and not vencimiento:
                    vencimiento = dates[2]

    if not ruc_contratante:
        ruc_contratante = _find(r"Ruc\s*:\s*(\d{11})", text) or _find(r"RUC\s*:\s*(\d{11})", text)
        if ruc_contratante == "20517207331":
            ruc_contratante = None

    asegurados = _find(r"Asegurados:\s*(.*?)(?=\n\s*\n|Coberturas|3\.|Reajuste|$)", text)
    if asegurados:
        asegurados = re.sub(r"\s+", " ", asegurados).strip()

    prima_comercial = _money_value(_find(r"PRIMA\s+COMERCIAL:\s*(?:S/\.?|US\$|USD|\$)?\s*([\d\.,]+)", text))
    igv_val = _money_value(_find(r"I\.?G\.?V\.?\s*:\s*(?:S/\.?|US\$|USD|\$)?\s*([\d\.,]+)", text))
    prima_total = _money_value(_find(r"PRIMA\s+COMERCIAL\s+TOTAL:\s*(?:S/\.?|US\$|USD|\$)?\s*([\d\.,]+)", text))

    if not prima_total and prima_comercial and igv_val:
        try:
            pc = float(prima_comercial.replace(",", "."))
            igv = float(igv_val.replace(",", "."))
            prima_total = f"{(pc + igv):.2f}"
        except Exception:
            pass

    forma_pago = _find(r"Forma\s+de\s+pago\s+de\s+la\s+Prima\s*:\s*([^\r\n]+)", text)
    frecuencia_pago = _find(r"Frecuencia\s+de\s+pago\s+de\s+la\s+Prima\s*:\s*([^\r\n]+)", text)

    ramo_up = ramo_raw.upper()
    ramo_main = "SCTR" if "SCTR" in ramo_up else ""
    ramos_producto = None
    if "PENS" in ramo_up:
        ramos_producto = "PENSIONES"
    elif "SALUD" in ramo_up or "EPS" in ramo_up:
        ramos_producto = "SALUD"

    colectivo = _clean(contratante) or _clean(asegurados)

    return {
        "numero_poliza": _clean(poliza),
        "contrato_nro": _clean(poliza),
        "moneda": _clean(moneda),
        "fecha_emision": _clean(fecha_emision),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),
        "ramo": _clean(ramo_main) or "SCTR",
        "ramos_producto": _clean(ramos_producto),
        "prima_neta": _clean(prima_comercial),
        "prima_comercial": _clean(prima_comercial),
        "prima_total": _clean(prima_total),
        "prima_comercial_igv": _clean(prima_total),
        "forma_pago": _clean(forma_pago),
        "frecuencia_pago": _clean(frecuencia_pago),
        "colectivo_asegurado": _clean(colectivo),
        "numero_documento_extracted": _clean(ruc_contratante),
        "contratante": _clean(contratante),
    }

