
import re
from typing import Dict, Optional
from controllers.addPositivaGenerales import (
    extract_numero_poliza_positiva,
    extract_proforma_numero_positiva,
    extract_vigencias_positiva,
    extract_razon_social_strict,
    extract_razon_social,
    extract_primas_positiva,
    extract_moneda_positiva,
    _clean_company_name,
    _normalize_date_ddmmyyyy,
    _normalize_amount,
)


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _find(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _extract_fecha_vencimiento(text: str) -> Optional[str]:
    """Extrae la fecha de vencimiento de prima (Fecha de Vencimiento: DD/MM/YYYY)."""
    t = (text or "").replace(" ", " ")
    m = re.search(
        r"Fecha\s+de\s+Vencimiento\s*[:：]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return _normalize_date_ddmmyyyy(m.group(1))
    return None


def _extract_forma_pago_3d(text: str) -> Optional[str]:
    """Detecta forma de pago desde texto 3D."""
    t = (text or "").replace(" ", " ")
    if re.search(r"convenio\s+de\s+pago", t, re.IGNORECASE):
        return "CONVENIO DE PAGO"
    if re.search(r"\bcontado\b", t, re.IGNORECASE):
        return "CONTADO"
    if re.search(r"\bcuotas?\b", t, re.IGNORECASE):
        return "CUOTAS"
    if re.search(r"\bsemestral\b", t, re.IGNORECASE):
        return "SEMESTRAL"
    if re.search(r"\btrimestral\b", t, re.IGNORECASE):
        return "TRIMESTRAL"
    m = re.search(r"Forma\s+de\s+Pago\s*[:：]?\s*([^\n]{3,60})", t, re.IGNORECASE)
    if m:
        return m.group(1).strip().upper()
    return None


def _extract_ramo_3d(text: str) -> str:
    """Extrae el ramo. Para pólizas 3D siempre es '3D'."""
    t = (text or "").replace(" ", " ")
    if re.search(r"deshonestidad[,\s]+desaparici[oó]n\s+y\s+destrucci[oó]n", t, re.IGNORECASE):
        return "3D"
    m = re.search(r"\bRamo\s*[:：]?\s*(3D)\b", t, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    if re.search(r"\b3D\b", t):
        return "3D"
    return "3D"


def parse_poliza_3d_eps(text: str) -> Dict[str, str]:
    t = (text or "").replace(" ", " ")
    item: Dict[str, Optional[str]] = {}

    # Número de póliza
    item["numero_poliza"] = extract_numero_poliza_positiva(t)

    # Recibo / Proforma
    item["recibo"] = extract_proforma_numero_positiva(t)

    # Vigencias (inicio_vigencia + vencimiento)
    vig = extract_vigencias_positiva(t)
    item["inicio_vigencia"] = vig.get("inicio_vigencia")
    item["vencimiento"] = vig.get("vencimiento")

    # Fecha de vencimiento de prima
    item["fecha_vencimiento"] = _extract_fecha_vencimiento(t)

    # Asegurado / colectivo
    name = extract_razon_social_strict(t) or extract_razon_social(t)
    item["colectivo_asegurado"] = _clean_company_name(name) or name

    # Ramo
    item["ramo"] = _extract_ramo_3d(t)

    # Moneda
    item["moneda"] = extract_moneda_positiva(t)

    # Primas
    primas = extract_primas_positiva(t)
    item["prima_comercial"] = primas.get("prima_comercial")
    item["prima_comercial_igv"] = primas.get("prima_comercial_igv")

    # prima_neta = prima_comercial / 1.03 si no se encuentra explícitamente
    prima_neta_raw = _find(
        r"Prima\s+Neta[\s:]*(?:US\s*\$|US\$|USD|\$|S\s*\/\s*\.?|S\s*\/)?\s*([\d,\.]+)",
        t,
    )
    if prima_neta_raw:
        item["prima_neta"] = _normalize_amount(prima_neta_raw)
    elif item.get("prima_comercial"):
        try:
            item["prima_neta"] = f"{float(item['prima_comercial']) / 1.03:.2f}"
        except Exception:
            pass

    # Forma de pago
    item["forma_pago"] = _extract_forma_pago_3d(t)

    # Identificadores de emisor
    item["issuer"] = "La Positiva"
    item["cia"] = "La Positiva"
    item["cia_value"] = "positiva"

    return {k: _clean(v) for k, v in item.items() if v}
