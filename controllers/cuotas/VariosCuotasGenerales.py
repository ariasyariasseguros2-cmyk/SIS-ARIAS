import re
from typing import Dict, List


def _normalize_importe_text(raw: str | None) -> str:
    txt = (raw or "").strip()
    if not txt:
        return ""
    txt = re.sub(r"[^\d,.\-]", "", txt)
    if not txt:
        return ""
    try:
        if "." in txt and "," in txt:
            if txt.rfind(".") > txt.rfind(","):
                txt = txt.replace(",", "")
            else:
                txt = txt.replace(".", "").replace(",", ".")
        elif txt.count(".") > 1 and "," not in txt:
            parts = txt.split(".")
            txt = "".join(parts[:-1]) + "." + parts[-1]
        elif txt.count(",") > 1 and "." not in txt:
            parts = txt.split(",")
            txt = "".join(parts[:-1]) + "." + parts[-1]
        elif "," in txt:
            txt = txt.replace(".", "").replace(",", ".")
        return f"{float(txt):.2f}"
    except Exception:
        return (raw or "").strip()


def _normalize_date_token(raw: str | None) -> str:
    txt = (raw or "").strip()
    if not txt:
        return ""
    txt = re.sub(r"\s*[/-]\s*", "/", txt)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", txt)
    if not m:
        return txt
    return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"


def extract_cronograma_cuotas_from_text(text: str | None, moneda_default: str | None = None) -> List[Dict[str, object]]:
    if not text:
        return []

    normalized = (text or "").replace("\u00A0", " ").replace("：", ":")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    section_match = re.search(
        r"Cronograma\s+de\s+Pago([\s\S]{0,3500})",
        normalized,
        re.IGNORECASE,
    )
    section = section_match.group(1) if section_match else normalized
    end_match = re.search(
        r"(Monto\s+total\s+a\s+pagar|Tasa\s+de\s+costo\s+efectivo|CUARTO\b)",
        section,
        re.IGNORECASE,
    )
    if end_match:
        section = section[:end_match.start()]

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]

    cuotas: List[Dict[str, object]] = []
    seen = set()
    row_pattern = re.compile(
        r"(?P<orden>\d{1,2}/\d{1,2})\s+"
        r"(?P<fecha>\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(?P<cupon>\d{6,20})\s+"
        r"(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )

    for ln in lines:
        if re.search(r"Orden|Fec\.?\s*Vcto|Cod\.?\s*Cuota|Monto\s+a\s+Pagar", ln, re.IGNORECASE):
            continue
        m = row_pattern.search(ln)
        if not m:
            continue

        cupon = (m.group("cupon") or "").strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)

        orden = (m.group("orden") or "").strip()
        numero_cuota = None
        try:
            numero_cuota = int(orden.split("/")[0])
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
