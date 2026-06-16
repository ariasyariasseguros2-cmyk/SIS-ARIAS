import re
import unicodedata

import fitz
import pdfplumber


def addPolizaPacificoGenerales_V4(filepath):
    amount_pattern = r"(\(?\s*[-−–—]?\s*(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{2})?\s*(?:[-−–—])?\s*\)?)"
    soles_pattern = r"(?:S\s*\/\.?|PEN(?:ES)?|\bSOL(?:ES)?\b)"
    dolares_pattern = r"(?:US\s*\$|U\s*\$\s*S|USD(?:\$)?|USS|\bD[OÓ]LAR(?:ES)?\b|DOLAR(?:ES)?)"

    def _strip_accents(value):
        value = value or ""
        return "".join(
            ch for ch in unicodedata.normalize("NFD", value)
            if unicodedata.category(ch) != "Mn"
        )

    def _norm_spaces(value):
        return re.sub(r"[ \t]+", " ", (value or "")).strip()

    def _normalize_for_match(value):
        return _norm_spaces(_strip_accents(value)).lower()

    def _normalize_currency_token(token):
        normalized = re.sub(r"\s+", "", _normalize_for_match(token))
        normalized = normalized.replace("\\", "")
        if re.fullmatch(r"(?:s/\.?|s/|pen|penes|sol|soles)", normalized):
            return "S/."
        if re.fullmatch(r"(?:us\$|u\$s|usd\$?|uss|dolar|dolares)", normalized):
            return "US$"
        return ""

    def _valid_date(value):
        value = (value or "").strip()
        return value if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value) else ""

    def _clean_amount(value):
        raw = (value or "").strip()
        if not raw:
            return 0.0

        raw = raw.replace("−", "-").replace("–", "-").replace("—", "-")
        negative = bool(
            re.search(r"^\s*-\s*", raw)
            or re.search(r"\(\s*.*\s*\)", raw)
            or re.search(r"-\s*$", raw)
            or re.search(rf"(?:{soles_pattern}|{dolares_pattern})\s*-\s*", raw, re.IGNORECASE)
        )

        raw = re.sub(rf"(?:{soles_pattern}|{dolares_pattern})", "", raw, flags=re.IGNORECASE)
        raw = raw.replace("(", "").replace(")", "")
        raw = re.sub(r"^\s*-\s*", "", raw)
        raw = re.sub(r"\s*-\s*$", "", raw)
        raw = raw.replace(" ", "")
        raw = re.sub(r"[^\d,.\-]", "", raw)
        if not raw:
            return 0.0

        raw = raw.lstrip("-").rstrip("-")

        last_dot = raw.rfind(".")
        last_comma = raw.rfind(",")
        last_sep = max(last_dot, last_comma)

        if last_sep >= 0:
            integer_part = re.sub(r"[.,]", "", raw[:last_sep])
            decimal_part = re.sub(r"[^\d]", "", raw[last_sep + 1:])
            normalized = f"{integer_part}.{decimal_part or '00'}"
        else:
            normalized = re.sub(r"[^\d]", "", raw)

        if not normalized or normalized == ".":
            return 0.0

        try:
            number = float(normalized)
            return -abs(number) if negative else number
        except Exception:
            return 0.0

    def _extract_emision(text):
        match = re.search(
            r"emitido\s+el\s+(\d{1,2})\s+de\s+([a-z]+)\s+(?:del\s+)?(\d{4})",
            text,
            re.IGNORECASE,
        )
        if not match:
            return ""

        months = {
            "enero": "01",
            "febrero": "02",
            "marzo": "03",
            "abril": "04",
            "mayo": "05",
            "junio": "06",
            "julio": "07",
            "agosto": "08",
            "setiembre": "09",
            "septiembre": "09",
            "octubre": "10",
            "noviembre": "11",
            "diciembre": "12",
        }
        day = match.group(1).zfill(2)
        month = months.get((match.group(2) or "").lower(), "")
        year = match.group(3)
        return f"{day}/{month}/{year}" if month else ""

    def _extract_pages_with_fitz(path):
        result = []
        try:
            with fitz.open(path) as doc:
                for page in doc:
                    result.append(page.get_text("text") or "")
        except Exception as exc:
            print(f"[PacificoGeneralesV4] fitz extract error: {exc}")
        return result

    def _extract_pages_with_pdfplumber(path):
        result = []
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    result.append(page.extract_text() or "")
        except Exception as exc:
            print(f"[PacificoGeneralesV4] pdfplumber extract error: {exc}")
        return result

    def _extract_labeled_line_value(text, labels):
        for label in labels:
            match = re.search(rf"{label}\s*[:.]?\s*([^\n]+)", text, re.IGNORECASE)
            if match:
                value = _norm_spaces(match.group(1))
                if value:
                    return value
        return ""

    def _extract_concept_amount(text, labels):
        for label in labels:
            match = re.search(
                rf"{label}[\s:.\-]{{0,20}}{amount_pattern}",
                text,
                re.IGNORECASE,
            )
            if match:
                return _clean_amount(match.group(1))
        return 0.0

    def _extract_total_and_currency(text, lines):
        patterns = [
            rf"(US\$|USD|USS|U\$S|S\/\.?|S\/|PEN|SOL(?:ES)?)\s*{amount_pattern}",
            rf"(US\$|USD|USS|U\$S|S\/\.?|S\/|PEN|SOL(?:ES)?)\s*\n\s*{amount_pattern}",
            rf"(?:TOTAL|IMPORTE\s+TOTAL|US\$|S\/\.?)\s*[:.]?\s*(US\$|USD|USS|U\$S|S\/\.?|S\/|PEN|SOL(?:ES)?)?\s*{amount_pattern}",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = [g for g in match.groups() if g]
                if not groups:
                    continue
                if len(groups) == 1:
                    return _clean_amount(groups[0]), ""
                currency = _normalize_currency_token(groups[0])
                amount = _clean_amount(groups[-1])
                if amount:
                    return amount, currency

        candidate_lines = []
        for line in lines:
            normalized = _norm_spaces(line)
            if not normalized:
                continue
            match = re.search(
                rf"^(US\$|USD|USS|U\$S|S\/\.?|S\/|PEN|SOL(?:ES)?)\s+{amount_pattern}$",
                normalized,
                re.IGNORECASE,
            )
            if match:
                currency = _normalize_currency_token(match.group(1))
                amount = _clean_amount(match.group(2))
                if amount:
                    candidate_lines.append((amount, currency))
        if candidate_lines:
            return candidate_lines[-1][0], candidate_lines[-1][1]

        return 0.0, ""

    def _extract_asegurado(text, lines):
        for label in ("Cliente", "Asegurado", "Contratante"):
            value = _extract_labeled_line_value(text, [label])
            if value:
                value = re.sub(r"\s+\d{6,}$", "", value).strip()
                if value:
                    return value.upper()

        for line in lines:
            cleaned = _norm_spaces(line)
            plain = _strip_accents(cleaned).upper()
            if not re.fullmatch(r"[A-Z0-9&.,/\- ]{8,}", plain):
                continue
            if any(
                token in plain
                for token in (
                    "PACIFICO",
                    "AVISO DE COBRANZA",
                    "PRIMA",
                    "CONCEPTOS",
                    "VIGENCIA",
                    "AGENTE",
                    "FORMA DE PAGO",
                    "EMITIDO EL",
                )
            ):
                continue
            if re.search(r"\d{9,}", plain):
                continue
            if len(plain.split()) < 2:
                continue
            if len(plain.split()) > 8:
                continue
            return cleaned.upper()
        return ""

    def _extract_producto(lines, match_idx, full_text):
        skip_exact = {
            "POLIZA",
            "VIGENCIA",
            "CLIENTE",
            "ASEGURADO",
            "TELEFONO",
            "DIRECCION",
            "LOCALIDAD",
            "CONCEPTOS",
            "IMPORTE",
            "FORMA DE PAGO",
        }
        skip_contains = (
            "PACIFICO",
            "SEGUROS",
            "RUC",
            "AGENTE",
            "ARIAS",
            "PRIMA",
            "INTERESES",
            "I.G.V",
            "AVISO DE COBRANZA",
            "CUOTAS",
            "EMITIDO EL",
        )

        candidates = []
        for offset in range(max(0, match_idx - 2), min(len(lines), match_idx + 10)):
            line = _norm_spaces(lines[offset])
            if not line:
                continue
            plain = _strip_accents(line).upper()
            compact = plain.replace(".", "").replace(":", "")
            if compact in skip_exact:
                continue
            if any(token in plain for token in skip_contains):
                continue
            if re.search(r"\d{5,}", plain):
                continue
            if len(plain.split()) < 2:
                continue
            if not re.fullmatch(r"[A-Z0-9/&,\- ]{8,}", plain):
                continue
            candidates.append((offset, line, len(re.findall(r"[A-Z]", plain))))

        if candidates:
            candidates.sort(key=lambda item: (-item[2], abs(item[0] - match_idx)))
            return candidates[0][1].upper()

        low = _normalize_for_match(full_text)
        if "cascos no pesqueros" in low:
            return "CASCOS NO PESQUEROS"
        if "multiriesgo" in low:
            return "MULTIRIESGO"
        if "transporte" in low:
            return "TRANSPORTE"
        return ""

    def _extract_comision_intermediacion(text):
        normalized = _strip_accents(text)
        patterns = [
            rf"Comision\s+por\s+Intermediacion[\s\S]{{0,120}}?(?:{dolares_pattern}|{soles_pattern})\s*{amount_pattern}",
            rf"Comision\s+por\s+Intermediacion[\s\S]{{0,120}}?{amount_pattern}",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                return _clean_amount(match.group(1))
        return 0.0

    data = {
        "aseguradora": "PACIFICO",
        "producto": "",
        "poliza": "",
        "recibo": "",
        "inicio": "",
        "fin": "",
        "fecha_pago": "",
        "emision": "",
        "asegurado": "",
        "prima_neta": 0.0,
        "igv": 0.0,
        "total": 0.0,
        "comision_compania_importe": 0.0,
        "ramo": "",
        "moneda": "S/.",
        "error": None,
    }

    pages_fitz = _extract_pages_with_fitz(filepath)
    pages_pdfplumber = _extract_pages_with_pdfplumber(filepath)

    if any((page or "").strip() for page in pages_pdfplumber):
        pages = [page for page in pages_pdfplumber if (page or "").strip()]
        extraction_source = "pdfplumber"
    else:
        pages = [page for page in pages_fitz if (page or "").strip()]
        extraction_source = "fitz"

    try:
        if not pages:
            raise ValueError("No se pudo extraer texto con fitz ni pdfplumber")
    except Exception as exc:
        data["error"] = f"Error al leer PDF: {exc}"
        print(f"[PacificoGeneralesV4] Error: {exc}")
        return data

    full_text = "\n".join(pages)
    if not full_text.strip():
        data["error"] = "No se pudo extraer texto del PDF."
        return data

    scored_pages = []
    for idx, page_text in enumerate(pages):
        low = _normalize_for_match(page_text)
        score = 0
        if "aviso de cobranza" in low:
            score += 5
        if "poliza" in low:
            score += 3
        if "prima comercial" in low:
            score += 3
        if "i.g.v" in low or "igv" in low:
            score += 2
        if "emitido el" in low:
            score += 1
        if "forma de pago" in low:
            score += 1
        scored_pages.append((score, idx, page_text))

    scored_pages.sort(reverse=True)
    target_text = scored_pages[0][2] if scored_pages and scored_pages[0][0] > 0 else full_text
    target_low = _normalize_for_match(target_text)
    lines = [line for line in target_text.splitlines()]

    print(f"[PacificoGeneralesV4] Source: {extraction_source}")
    print(f"[PacificoGeneralesV4] Pages: {len(pages)}")
    print(f"[PacificoGeneralesV4] Target page score: {scored_pages[0][0] if scored_pages else 0}")

    poliza_match = re.search(
        r"poliza(?:\s*n[°ºo.]*)?\s*[:.]?\s*([0-9][0-9 \-]{5,})",
        _strip_accents(target_text),
        re.IGNORECASE,
    )
    if poliza_match:
        poliza_raw = re.sub(r"\s*-\s*", "-", poliza_match.group(1).strip())
        poliza_raw = re.sub(r"\s+", "", poliza_raw)
        data["poliza"] = poliza_raw.split("-", 1)[0].strip()

    recibo_match = re.search(
        r"aviso\s+de\s+cobranza\s+n[roo0°:. ]*\s*([0-9]{5,})",
        _strip_accents(target_text),
        re.IGNORECASE,
    )
    if recibo_match:
        data["recibo"] = recibo_match.group(1).strip()

    vigencia_match = re.search(
        r"(?:fecha\s+de\s+)?vigencia\s*[:.]?\s*(\d{2}/\d{2}/\d{4})\s*[-a]\s*(\d{2}/\d{2}/\d{4})",
        _strip_accents(target_text),
        re.IGNORECASE,
    )
    if vigencia_match:
        data["inicio"] = vigencia_match.group(1)
        data["fin"] = vigencia_match.group(2)

    data["asegurado"] = _extract_asegurado(target_text, lines)

    policy_line_idx = 0
    for idx, line in enumerate(lines):
        if "poliza" in _normalize_for_match(line):
            policy_line_idx = idx
            break

    data["producto"] = _extract_producto(lines, policy_line_idx, target_text)

    data["prima_neta"] = _extract_concept_amount(
        target_text,
        ["PRIMA\\s+COMERCIAL", "PRIMA\\s+NETA"],
    )
    intereses = _extract_concept_amount(target_text, ["INTERESES?"])
    data["igv"] = _extract_concept_amount(target_text, ["I\\.?\\s*G\\.?\\s*V\\.?"])

    total, currency = _extract_total_and_currency(target_text, lines)
    if total:
        data["total"] = total
    if currency:
        data["moneda"] = currency

    if not data["total"] and data["prima_neta"]:
        data["total"] = round(data["prima_neta"] + data["igv"] + intereses, 2)

    if not data["igv"] and data["prima_neta"]:
        estimated_igv = round(data["prima_neta"] * 0.18, 2)
        if data["total"] and data["total"] >= data["prima_neta"]:
            remainder = round(data["total"] - data["prima_neta"] - intereses, 2)
            data["igv"] = remainder if remainder > 0 else estimated_igv
        else:
            data["igv"] = estimated_igv

    data["comision_compania_importe"] = (
        _extract_comision_intermediacion(full_text)
        or _extract_comision_intermediacion(target_text)
    )

    if not data["moneda"] or data["moneda"] == "S/.":
        if re.search(dolares_pattern, target_text, re.IGNORECASE):
            data["moneda"] = "US$"

    data["emision"] = _extract_emision(full_text) or _extract_emision(target_text)

    prod_low = _normalize_for_match(data["producto"])
    full_low = _normalize_for_match(full_text)
    if "cascos" in prod_low or "cascos" in full_low:
        data["ramo"] = "CASCOS MARITIMOS"
    elif "multiriesgo" in prod_low or "multiriesgo" in full_low:
        data["ramo"] = "MULTIRIESGO"
    elif any(token in prod_low for token in ("vehicular", "automovil", "moto")):
        data["ramo"] = "VEHICULOS"
    elif "transporte" in prod_low or "transporte" in full_low:
        data["ramo"] = "TRANSPORTES"

    data["inicio"] = _valid_date(data["inicio"])
    data["fin"] = _valid_date(data["fin"])
    data["fecha_pago"] = _valid_date(data["fecha_pago"])
    data["emision"] = _valid_date(data["emision"])

    print(f"[PacificoGeneralesV4] Extracted: {data}")
    return data
