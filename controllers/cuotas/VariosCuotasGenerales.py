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
        r"(?:Cronograma\s+de\s+Pago|CRONOGRAMA,\s*LUGAR\s+Y\s+FORMA\s+DE\s+PAGO\s+DE\s+LA\s+PRIMA)\s*[:：]?\s*([\s\S]{0,6000})",
        normalized,
        re.IGNORECASE,
    )
    section = section_match.group(1) if section_match else normalized
    end_match = re.search(
        r"(Monto\s+total\s+a\s+pagar|Tasa\s+de\s+costo\s+efectivo|CUARTO\b|TIPO\s+DE\s+CAMBIO|INFORMACI[ÓO]N\s+ADICIONAL)",
        section,
        re.IGNORECASE,
    )
    if end_match:
        section = section[:end_match.start()]

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in section.splitlines() if ln.strip()]

    cuotas: List[Dict[str, object]] = []
    seen = set()
    
    # Patrón 1: Formato "1/12 26/01/2026 123456 1,490.89"
    row_pattern_full = re.compile(
        r"(?P<orden>\d{1,2}/\d{1,2})\s+"
        r"(?P<fecha>\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(?P<cupon>\d{6,20})\s+"
        r"(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )
    
    # Patrón 2: Formato simple "1 26/01/2026 123456 1,490.89" (como La Positiva)
    row_pattern_simple = re.compile(
        r"(?P<numero_cuota>\d{1,3})\s+"
        r"(?P<cupon>\d{6,20})\s+"
        r"(?P<fecha>\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(?P<importe>\d[\d\.,]*)",
        re.IGNORECASE,
    )

    for ln in lines:
        if re.search(r"Orden|Fec\.?\s*Vcto|Cod\.?\s*Cuota|Monto\s+a\s+Pagar|Cup[oó]n|Número", ln, re.IGNORECASE):
            continue
            
        m = row_pattern_full.search(ln) or row_pattern_simple.search(ln)
        if not m:
            continue

        cupon = (m.group("cupon") or "").strip()
        if not cupon or cupon in seen:
            continue
        seen.add(cupon)

        numero_cuota = None
        try:
            # Si es patrón 1 (1/12), sacamos el primer número
            # Si es patrón 2 (1), lo usamos directamente
            if "orden" in m.groupdict() and m.group("orden"):
                numero_cuota = int(m.group("orden").split("/")[0])
            else:
                numero_cuota = int(m.group("numero_cuota"))
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

    def _read_compact_date(tokens: List[str], idx: int) -> tuple[str, int]:
        for take in (1, 2, 3):
            if idx + take > len(tokens):
                break
            cand = "".join(tokens[idx : idx + take])
            cand = re.sub(r"\s+", "", cand).replace("-", "/")
            m = re.search(r"\d{1,2}/\d{1,2}/\d{4}", cand)
            if m:
                return _normalize_date_token(m.group(0)), idx + take
        return "", idx

    def _read_digits(tokens: List[str], idx: int) -> tuple[str, int]:
        for take in (1, 2, 3):
            if idx + take > len(tokens):
                break
            cand = "".join(tokens[idx : idx + take])
            cand = re.sub(r"\s+", "", cand)
            if re.fullmatch(r"\d{6,25}", cand):
                return cand, idx + take
        return "", idx

    rimac_header_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("documento"):
            rimac_header_idx = i
            break

    if rimac_header_idx is None:
        return []

    tokens = lines[rimac_header_idx + 1 :]
    i = 0
    while i < len(tokens):
        if not re.fullmatch(r"\d{1,3}", tokens[i] or ""):
            i += 1
            continue
        numero_cuota = None
        try:
            numero_cuota = int(tokens[i])
        except Exception:
            numero_cuota = None
        i += 1
        if i >= len(tokens):
            break
        if re.fullmatch(r"[A-Za-z]{1,5}", tokens[i] or ""):
            i += 1
        if i >= len(tokens):
            break
        importe_raw = tokens[i]
        if not re.search(r"\d", importe_raw or ""):
            i += 1
            continue
        importe = _normalize_importe_text(importe_raw)
        i += 1
        inicio, i2 = _read_compact_date(tokens, i)
        if not inicio:
            i += 1
            continue
        i = i2
        fin, i2 = _read_compact_date(tokens, i)
        if not fin:
            i += 1
            continue
        i = i2
        fecha_venc, i2 = _read_compact_date(tokens, i)
        if not fecha_venc:
            i += 1
            continue
        i = i2
        cupon, i2 = _read_digits(tokens, i)
        if not cupon:
            i += 1
            continue
        i = i2
        if cupon in seen:
            continue
        seen.add(cupon)
        cuotas.append({
            "numero_cuota": numero_cuota,
            "cupon": cupon,
            "fecha_vencimiento": fecha_venc,
            "importe": importe,
            "moneda": moneda_default or "",
            "factura": "",
            "fecha_pago": "",
        })

    return cuotas
