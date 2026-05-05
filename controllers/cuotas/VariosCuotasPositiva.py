import re
from typing import Dict, List

from controllers.cuotas.VariosCuotasGenerales import _normalize_date_token, _normalize_importe_text


def extract_cronograma_cuotas_positiva(text: str | None, moneda_default: str | None = None) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    section_match = re.search(
        r"Cronograma\s+de\s+Pagos?([\s\S]{0,2500})",
        normalized,
        re.IGNORECASE,
    )
    section = section_match.group(1) if section_match else normalized

    # Quitar el end_match muy restrictivo o moverlo después
    # En muchos PDF de Positiva, "N° Pagos" o "Total a Pagar" aparecen en el flujo de texto antes de las filas
    # Solo usaremos end_match si encontramos una palabra que indique el FIN real (como "Intermediario:")
    # Pero preferimos procesar todo lo que encontremos después del encabezado
    
    end_match = re.search(
        r"(Intermediario:|T.E.A.:|T.C.E.A.:)",
        section,
        re.IGNORECASE,
    )
    if end_match:
        section = section[:end_match.start()]

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]

    cuotas: List[Dict[str, object]] = []
    seen = set()
    # Regex robusta para La Positiva:
    # 1. numero_cuota opcional o pequeño
    # 2. cupon largo
    # 3. fecha dd/mm/yyyy
    # 4. importe
    row_pattern = re.compile(
        r"(?P<numero_cuota>\d{1,3})[\s\.\-]+(?P<cupon>\d{6,20})\s+(?P<fecha>\d{1,2}/\d{1,2}/\d{4})\s+(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )

    header_re = re.compile(r"Cup[oó]n|N[uú]mero|Vencimiento|Monto", re.IGNORECASE)
    data_lines = [ln for ln in lines if not header_re.search(ln)]
    flat = " ".join(data_lines)

    for m in row_pattern.finditer(flat):
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
