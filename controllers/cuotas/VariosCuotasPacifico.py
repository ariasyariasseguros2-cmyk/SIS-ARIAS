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

    header_re = re.compile(r"Cup[oó]n|N[uú]mero|Vencimiento|Monto|Fecha", re.IGNORECASE)
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

    if cuotas:
        return cuotas

    cron_re = re.compile(r"Cronograma\s+de\s+Pagos?", re.IGNORECASE)
    for sm in cron_re.finditer(normalized):
        idx = sm.start()
        pre_start = max(0, idx - 1800)
        pre = normalized[pre_start:idx]

        date_matches = list(re.finditer(r"\b\d{1,2}/\d{1,2}/\d{4}\b", pre))
        if len(date_matches) < 2:
            continue

        cluster_dates = []
        for m in reversed(date_matches):
            if not cluster_dates:
                cluster_dates.append(m)
                continue
            gap = cluster_dates[-1].start() - m.end()
            if gap <= 40:
                cluster_dates.append(m)
            else:
                break
        cluster_dates.reverse()
        if len(cluster_dates) < 2:
            continue

        n = len(cluster_dates)
        after_dates_pos = cluster_dates[-1].end()
        tail = pre[after_dates_pos:]

        code_matches = list(re.finditer(r"\b\d{8,10}\b", tail))
        if len(code_matches) < n:
            continue

        tail2 = tail[code_matches[n - 1].end():]
        amount_matches = list(re.finditer(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b", tail2))
        if len(amount_matches) < n:
            continue

        cuotas2: List[Dict[str, object]] = []
        seen2 = set()
        for i in range(n):
            cupon = (code_matches[i].group(0) or "").strip()
            if not cupon or cupon in seen2:
                continue
            seen2.add(cupon)
            cuotas2.append({
                "numero_cuota": i + 1,
                "cupon": cupon,
                "fecha_vencimiento": _normalize_date_token(cluster_dates[i].group(0)),
                "importe": _normalize_importe_text(amount_matches[i].group(0)),
                "moneda": moneda_default or "",
                "factura": "",
                "fecha_pago": "",
            })

        if cuotas2:
            return cuotas2

    return []
