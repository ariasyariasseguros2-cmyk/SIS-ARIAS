"""
Parser para PDFs combinados de La Positiva con formato "Endoso de Declaración":
  - Bloque 1: La Positiva Vida  → SCTR Pensión  (Proforma de Cobertura / Cobro)
  - Bloque 2: La Positiva EPS   → SCTR Salud    (Proforma de Pago)

Diferencias respecto al parser estándar addLPVPENSION:
  - Póliza etiquetada como "Póliza N° :" (endoso) o "Póliza Nro :" (proforma)
  - Primas en tabla: Sobrevivencia + Costos de Emision + IGV = Prima Comercial + IGV
  - EPS usa "Contrato Nro :" y prima "SCTR SALUD S/ X" + "Prima Total"
  - Ambas secciones viven en el mismo archivo PDF
"""
import re
from typing import Dict, Optional, List
from datetime import datetime, timedelta


def _find(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _money(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    raw = str(s).strip().replace("−", "-").replace("–", "-").replace("—", "-")
    neg = False
    mp = re.match(r"^\((.*)\)$", raw)
    if mp:
        neg = True
        raw = mp.group(1).strip()
    v = re.sub(r"\s+", "", raw).replace("S/", "").replace("s/", "")
    if "," in v and "." in v:
        v = v.replace(",", "")
    elif "," in v and "." not in v:
        v = v.replace(".", "").replace(",", ".")
    m = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", v)
    if not m:
        return None
    try:
        num = float(m.group(1))
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return m.group(1)


def _norm_moneda(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    u = re.sub(r"[\s/\.]", "", s).upper()
    if u in ("SOLES", "SOL", "PEN", "S", "MN"):
        return "S/"
    if u in ("DOLARES", "DÓLARES", "USD", "US", "DOLAR", "DÓLAR"):
        return "US$"
    return s


def _add_days(date_str: Optional[str], days: int) -> Optional[str]:
    try:
        if not date_str:
            return None
        dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
    except Exception:
        return None


def _split_pension_salud(text: str):
    """
    Divide el texto en (bloque_pension, bloque_salud).
    La sección EPS se identifica por el encabezado de La Positiva EPS.
    """
    m_eps = re.search(
        r"La\s+Positiva\s+S\.?A\.?\s+Entidad\s+Prestadora\s+de\s+Salud",
        text,
        re.IGNORECASE,
    )
    if m_eps:
        return text[: m_eps.start()], text[m_eps.start():]

    # Fallback: dividir en el primer "Endoso de Renovación N°"
    m_renov = re.search(
        r"Endoso\s+de\s+Renovaci[oó]n\s+N[°º]", text, re.IGNORECASE
    )
    if m_renov:
        return text[: m_renov.start()], text[m_renov.start():]

    return text, ""


def _parse_pension_vida(block: str) -> Optional[Dict]:
    """Extrae datos del bloque SCTR Pensión (La Positiva Vida)."""
    if not block:
        return None

    # Número de póliza — endoso usa "Póliza N° :", proforma usa "Póliza Nro :"
    numero_poliza = (
        _find(r"P[oó]liza\s+Nro\s*:\s*([0-9A-Z\-]+)", block)
        or _find(r"P[oó]liza\s+N[°º]\s*:\s*([0-9A-Z\-]+)", block)
        or _find(r"P[oó]liza\s*:\s*([0-9]{5,12})\b", block)
    )

    # Número de proforma (solo en la sección "Proforma de Cobertura")
    recibo = _find(r"N[uú]mero\s+de\s+Proforma\s*:\s*([0-9]+)", block)

    # Fechas
    emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)
    vig_desde = _find(r"Vigencia\s+Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)
    # "Hasta :" puede venir junto con "Vigencia desde :" en el mismo renglón de tabla
    vig_hasta = _find(r"\bHasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)

    # fecha_vencimiento = fecha de emisión + 15 días (según las condiciones del convenio)
    fecha_vencimiento = _add_days(emision, 15) or vig_hasta

    # Contratante / asegurado colectivo
    contratante = _find(r"Contratante\s*:\s*([^\n\r]+)", block)

    # Moneda
    moneda_raw = _find(r"Moneda\s*:\s*([A-Za-z]+)", block)
    moneda = _norm_moneda(moneda_raw) or "S/"

    # ── Primas desde "Proforma de Cobertura (Cobro)" ──────────────────────────
    # Tabla: Descripción / Importes
    #   Sobrevivencia              S/  80.00
    #   Costos de Emision          S/   5.00
    #   Impuesto General a las Ventas S/ 15.30
    #   Prima Comercial + IGV      S/ 100.30
    sobrevivencia = _money(_find(r"Sobrevivencia\s+S\/\s*([\d,\.]+)", block))
    costos_emision = _money(
        _find(r"Costos\s+de\s+Emisi[oó]n\s+S\/\s*([\d,\.]+)", block)
    )
    igv_val = _money(
        _find(r"Impuesto\s+General\s+a\s+las\s+Ventas\s+S\/\s*([\d,\.]+)", block)
    )
    prima_comercial_igv = _money(
        _find(r"Prima\s+Comercial\s*\+\s*IGV\s+S\/\s*([\d,\.]+)", block)
    )

    # Fallback desde el endoso: "Prima Comercial (Incluye 3% de Costos de Emisión) : S/ 85.00"
    prima_comercial_endoso = _money(
        _find(r"Prima\s+Comercial\s*\([^)]+\)\s*:\s*S\/\s*([\d,\.]+)", block)
    )
    # Fallback desde el endoso: "Prima Comercial + IGV : S/ 100.30"
    if not prima_comercial_igv:
        prima_comercial_igv = _money(
            _find(r"Prima\s+Comercial\s*\+\s*IGV\s*:\s*S\/\s*([\d,\.]+)", block)
        )

    # prima_neta = Sobrevivencia
    prima_neta = sobrevivencia

    # prima_comercial = Sobrevivencia + Costos de Emisión
    prima_comercial = None
    if prima_neta and costos_emision:
        try:
            prima_comercial = f"{float(prima_neta) + float(costos_emision):.2f}"
        except Exception:
            pass
    prima_comercial = prima_comercial or prima_comercial_endoso

    # prima_comercial_igv calculada si no se encontró
    if not prima_comercial_igv and prima_comercial and igv_val:
        try:
            prima_comercial_igv = f"{float(prima_comercial) + float(igv_val):.2f}"
        except Exception:
            pass

    item = {
        "numero_poliza": numero_poliza,
        "recibo": recibo,
        "inicio_vigencia": vig_desde,
        "vencimiento": vig_hasta,
        "fecha_emision": emision,
        "fecha_vencimiento": fecha_vencimiento,
        "colectivo_asegurado": (contratante or "").strip() or None,
        "moneda": moneda,
        "ramo": "SCTR",
        "ramos_producto": "Pensión",
        "prima_neta": prima_neta,
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": prima_comercial_igv,
        "forma_pago": "CONVENIO DE PAGO",
        "cia": "La Positiva",
        "cia_value": "positiva",
        "issuer": "La Positiva",
    }
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in item.items() if v}


def _parse_salud_eps(block: str) -> Optional[Dict]:
    """Extrae datos del bloque SCTR Salud (La Positiva EPS)."""
    if not block:
        return None

    # EPS usa "Contrato Nro :" o "Contrato No. :" (no Póliza)
    numero_poliza = (
        _find(r"Contrato\s+Nro\s*:\s*([0-9]+)", block)
        or _find(r"Contrato\s+No\.\s*:\s*([0-9]+)", block)
        or _find(r"Contrato\s*:\s*([0-9]{5,12})\b", block)
    )

    recibo = _find(r"N[uú]mero\s+de\s+Proforma\s*:\s*([0-9]+)", block)

    emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)
    vig_desde = _find(r"Vigencia\s+Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)
    # "Hasta:" sin espacio antes de la fecha puede aparecer en el endoso
    vig_hasta = _find(r"\bHasta\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)

    # Vencimiento explícito en la proforma EPS: "Vencimiento: 01/07/2026"
    fecha_vencimiento = (
        _find(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", block)
        or _add_days(emision, 15)
        or vig_hasta
    )

    contratante = _find(r"Contratante\s*:\s*([^\n\r]+)", block)

    moneda_raw = _find(r"Moneda\s*:\s*([A-Za-z]+)", block)
    moneda = _norm_moneda(moneda_raw) or "S/"

    # ── Primas desde "PROFORMA DE PAGO" (EPS) ────────────────────────────────
    # Tabla:
    #   SCTR SALUD                   S/  80.00   ← prima neta
    #   Impuesto General a las Ventas S/  14.40
    #   Prima Total                  S/  94.40
    prima_neta = _money(_find(r"SCTR\s+SALUD\s+S\/\s*([\d,\.]+)", block))
    # Fallback desde el endoso: "Prima Neta : S/ 80.00"
    if not prima_neta:
        prima_neta = _money(_find(r"Prima\s+Neta\s*:\s*S\/\s*([\d,\.]+)", block))

    igv_val = _money(
        _find(r"Impuesto\s+General\s+a\s+las\s+Ventas\s+S\/\s*([\d,\.]+)", block)
    )
    # Fallback desde el endoso: "I.G.V. : S/ 14.40"
    if not igv_val:
        igv_val = _money(_find(r"I\.G\.V\.\s*:\s*S\/\s*([\d,\.]+)", block))

    prima_total = (
        _money(_find(r"Prima\s+Total\s+S\/\s*([\d,\.]+)", block))
        or _money(_find(r"Total\s*:\s*S\/\s*([\d,\.]+)", block))
    )

    # En EPS no hay costos de emisión: prima_comercial = prima_neta
    prima_comercial = prima_neta
    prima_comercial_igv = prima_total
    if not prima_comercial_igv and prima_comercial and igv_val:
        try:
            prima_comercial_igv = f"{float(prima_comercial) + float(igv_val):.2f}"
        except Exception:
            pass

    item = {
        "numero_poliza": numero_poliza,
        "contrato_nro": numero_poliza,
        "recibo": recibo,
        "inicio_vigencia": vig_desde,
        "vencimiento": vig_hasta,
        "fecha_emision": emision,
        "fecha_vencimiento": fecha_vencimiento,
        "colectivo_asegurado": (contratante or "").strip() or None,
        "moneda": moneda,
        "ramo": "SCTR",
        "ramos_producto": "Salud",
        "prima_neta": prima_neta,
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": prima_comercial_igv,
        "forma_pago": "CONVENIO DE PAGO",
        "cia": "La Positiva EPS",
        "cia_value": "lpv-eps",
        "issuer": "La Positiva EPS",
    }
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in item.items() if v}


def parse_lpv_pension_declaracion(text: str) -> List[Dict]:
    """
    Parser principal para el formato combinado 'Endoso de Declaración'.
    Retorna hasta dos ítems: [pensión_item, salud_item].
    """
    pension_block, salud_block = _split_pension_salud(text)

    items: List[Dict] = []

    item_p = _parse_pension_vida(pension_block)
    if item_p and item_p.get("numero_poliza"):
        print("[parser] lpv-pension-declaracion pensión:", item_p)
        items.append(item_p)

    if salud_block:
        item_s = _parse_salud_eps(salud_block)
        if item_s and item_s.get("numero_poliza"):
            print("[parser] lpv-pension-declaracion salud:", item_s)
            items.append(item_s)

    return items
