import re
from typing import Dict, List
from controllers.cuotas.VariosCuotasGenerales import _normalize_date_token, _normalize_importe_text

def extract_cronograma_cuotas_pacifico(text: str | None, moneda_default: str | None = None) -> List[Dict[str, object]]:
    if not text:
        return []

    # Normalización básica
    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    # Buscar sección de cronograma en Pacífico
    section_match = re.search(
        r"(Cronograma\s+de\s+Pagos?|Detalle\s+de\s+Cuotas)([\s\S]{0,3500})",
        normalized,
        re.IGNORECASE,
    )
    section = section_match.group(2) if section_match else normalized

    # El fin suele ser cuando aparecen firmas o cláusulas
    end_match = re.search(
        r"(IMPORTANTE|CLAUSULA|CONDICIONES|EL\s+CONTRATANTE|FIRMA)",
        section,
        re.IGNORECASE,
    )
    if end_match:
        section = section[:end_match.start()]

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]

    cuotas: List[Dict[str, object]] = []
    seen = set()
    
    # Patrón común en Pacífico: 
    # NroCuota (1, 2...) | Fecha (DD/MM/YYYY) | Cupón/Referencia (999999) | Importe (1,234.56)
    row_pattern = re.compile(
        r"(?P<numero_cuota>\d{1,3})\s+"
        r"(?P<fecha>\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(?P<cupon>\d{6,25})\s+"
        r"(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )

    for ln in lines:
        if re.search(r"Cup[oó]n|N[uú]mero|Vencimiento|Monto|Fecha", ln, re.IGNORECASE):
            continue
            
        m = row_pattern.search(ln)
        if not m:
            continue

        cupon = (m.group("cupon") or "").strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)

        numero_cuota = None
        try:
            numero_cuota = int((m.group("numero_cuota") or "").strip())
        except Exception:
            numero_cuota = None

        cuotas.append({
            "numero_cuota": numero_cuota,
            "cupon": cupon,
            "fecha_vencimiento": _normalize_date_token(m.group("fecha")),
            "importe": _normalize_importe_text(m.group("importe")),
            "moneda": moneda_default or "",
            "factura": "",
            "fecha_pago": "",
        })

    return cuotas
