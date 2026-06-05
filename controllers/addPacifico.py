import re

def _clean(s: str | None) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: str | None) -> str | None:
    if not s:
        return None
    raw = str(s).strip().replace("−", "-").replace("–", "-").replace("—", "-")
    m = re.search(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)", raw)
    return (m.group(1).strip() if m else raw)

def _valid_date(s: str | None) -> str | None:
    if not s:
        return None
    return s if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s) else None

def _to_float(num_str: str) -> float:
    s0 = (num_str or "").strip()
    if not s0:
        return float("nan")
    s0 = s0.replace("\u00A0", " ").replace("−", "-").replace("–", "-").replace("—", "-")
    neg = False
    mp = re.match(r"^\((.*)\)$", s0)
    if mp:
        neg = True
        s0 = (mp.group(1) or "").strip()
    if re.match(r"^\s*-\s*", s0):
        neg = True
    s = s0.replace(" ", "")
    if not s:
        return float("nan")
    if s.startswith("-"):
        neg = True
        s = s[1:]
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        last_sep_idx = max(s.rfind(","), s.rfind("."))
        dec_sep = s[last_sep_idx]
        thou_sep = "." if dec_sep == "," else ","
        normalized = s.replace(thou_sep, "").replace(dec_sep, ".")
        num = float(normalized)
        return -abs(num) if neg else num
    if has_comma:
        if re.search(r",\d{2}$", s):
            num = float(s.replace(".", "").replace(",", "."))
            return -abs(num) if neg else num
        num = float(s.replace(",", ""))
        return -abs(num) if neg else num
    if has_dot:
        if re.search(r"\.\d{2}$", s):
            num = float(s)
            return -abs(num) if neg else num
        num = float(s.replace(".", ""))
        return -abs(num) if neg else num
    num = float(s)
    return -abs(num) if neg else num

def _monto_total_pagar(text: str) -> str | None:
    m = re.search(
        r"Monto\s+total\s+a\s+pagar\s*:?\s*[^\d\-−–—]{0,40}(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else None

def _capture_block_after(label: str, text: str, end_labels: list[str]) -> str | None:
    m = re.search(label, text, re.IGNORECASE)
    if not m:
        return None
    tail = text[m.end():]
    ends = []
    for el in end_labels:
        em = re.search(el, tail, re.IGNORECASE)
        if em:
            ends.append(em.start())
    cut = min(ends) if ends else 160
    blk = tail[:cut]
    blk = re.sub(r"[\r\n]+", " ", blk)
    blk = re.sub(r"\s{2,}", " ", blk)
    return blk.strip(" :.-")

def parse_pacifico_pension(text: str) -> dict | None:
    def _canon(t: str) -> str:
        flat = re.sub(r"[\r\n]+", " ", t)
        return re.sub(r"\s{2,}", " ", flat)

    money_re = re.compile(
        r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)(?!\d)"
    )

    def _amount_after_label(label_regex: str, raw_text: str, lookahead_lines: int = 2) -> str | None:
        lines = [l.strip() for l in raw_text.splitlines()]
        for i, l in enumerate(lines):
            m = re.search(label_regex, l, re.IGNORECASE)
            if not m:
                continue
            tail = l[m.end() :]
            mm = money_re.search(tail)
            if mm:
                return mm.group(1)
            for j in range(1, lookahead_lines + 1):
                if i + j >= len(lines):
                    break
                mm2 = money_re.search(lines[i + j])
                if mm2:
                    return mm2.group(1)
            return None
        return None

    def _find_after(label_regex: str, t: str, value_regex: str, window: int = 160) -> str | None:
        m = re.search(label_regex, t, re.IGNORECASE)
        if not m:
            return None
        tail = t[m.end(): m.end() + window]
        m2 = re.search(value_regex, tail, re.IGNORECASE | re.DOTALL)
        return m2.group(1).strip() if m2 else None

    def _find_number_near(label_regex: str, t: str, window: int = 200) -> str | None:
        m = re.search(label_regex, t, re.IGNORECASE)
        if not m:
            return None
        start = max(0, m.start() - 20)
        end = min(len(t), m.end() + window)
        segment = t[start:end]
        nm = re.search(r"\b([0-9]{6,12})\b", segment, re.IGNORECASE | re.DOTALL)
        return nm.group(1).strip() if nm else None

    # NUEVOS HELPERS
    def _numbers_after(label_regex: str, t: str, window: int = 500) -> list[str]:
        m = re.search(label_regex, t, re.IGNORECASE)
        if not m:
            return []
        seg = t[m.end(): m.end() + window]
        return re.findall(r"\b([0-9]{6,12})\b", seg, re.IGNORECASE | re.DOTALL)

    def _choose_poliza(candidates: list[str], recibo_val: str | None) -> str | None:
        if not candidates:
            return None
        # descartar el recibo si aparece y preferir longitudes >= 8
        filtered = [n for n in candidates if n != recibo_val]
        for n in filtered:
            if len(n) >= 8:
                return n
        return filtered[0] if filtered else None

    def _find_last(pattern: str, t: str, flags=re.IGNORECASE | re.DOTALL) -> str | None:
        matches = list(re.finditer(pattern, t, flags))
        return matches[-1].group(1).strip() if matches else None

    # Buscar decimales en la(s) línea(s) de la etiqueta, priorizando punto decimal
    def _first_decimal_after(label_regex: str, raw_text: str, lookahead_lines: int = 6, dot_only: bool = True) -> str | None:
        lines = [l.strip() for l in raw_text.splitlines()]
        for i, l in enumerate(lines):
            if re.search(label_regex, l, re.IGNORECASE):
                candidates = [l] + lines[i + 1 : i + 1 + lookahead_lines]
                # cortar en la primera aparición de otra etiqueta (IGV o TOTAL A COBRAR)
                cut = len(candidates)
                for j, c in enumerate(candidates[1:], start=1):
                    if re.search(r"\b(IGV|TOTAL\s+A\s+COBRAR)\b", c, re.IGNORECASE):
                        cut = j
                        break
                search_list = candidates[:cut]
                pattern_dot = r"(?<!\d)(\(?\s*(?:[-−–—]\s*)?[0-9]+\.[0-9]{2}\s*\)?)(?!\d)"
                pattern_any = r"(?<!\d)(\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})\s*\)?)(?!\d)"
                # preferir punto decimal
                for c in search_list:
                    m = re.search(pattern_dot, c)
                    if m:
                        return m.group(1)
                # fallback: aceptar coma solo si se permite
                if not dot_only:
                    for c in search_list:
                        m = re.search(pattern_any, c)
                        if m:
                            return m.group(1)
                return None
        return None

    # Buscar decimales en la(s) línea(s) de la etiqueta, priorizando punto decimal
    def _amounts_near(anchor_regex: str, t: str, window: int = 800) -> list[float]:
        m = re.search(anchor_regex, t, re.IGNORECASE)
        if not m:
            return []
        seg = t[max(0, m.start()-40): m.end() + window]
        # Aceptar punto o coma como separador decimal
        vals = re.findall(r"(?<!\d)(\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})\s*\)?)(?!\d)", seg)
        uniq = []
        for v in vals:
            f = _to_float(v)
            if not (f == f):
                continue
            if all(abs(f - u) > 1e-6 for u in uniq):
                uniq.append(f)
        print("[pacifico] montos cerca del bloque:", uniq)
        return uniq

    # Nuevo fallback: deducción global (total ≈ prima + igv)
    def _deduce_amounts_global(t: str) -> tuple[str | None, str | None, str | None]:
        vals_raw = re.findall(r"(?<!\d)(\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})\s*\)?)(?!\d)", t)
        vals = []
        for v in vals_raw:
            try:
                f = _to_float(v)
                # deduplicar por 2 decimales
                if all(abs(f - u) > 1e-6 for u in vals):
                    vals.append(f)
            except Exception:
                continue
        vals.sort(key=lambda x: abs(x))
        if not vals:
            return None, None, None
        candidates = sorted(vals, key=lambda x: abs(x), reverse=True)
        for c in candidates:
            for a in candidates:
                if a == c:
                    continue
                for b in vals:
                    if b == c or b == a:
                        continue
                    if abs(a) <= 0.01 or abs(b) <= 0.01:
                        continue
                    if abs((a + b) - c) <= 0.01 and abs(a) > abs(b):
                        print("[pacifico] deducción global -> prima:", f"{a:.2f}", "igv:", f"{b:.2f}", "total:", f"{c:.2f}")
                        return f"{a:.2f}", f"{b:.2f}", f"{c:.2f}"
        return None, None, None

    def _label_amount(label_regex: str, raw_text: str, lookahead_lines: int = 6) -> str | None:
        lines = [l.strip() for l in raw_text.splitlines()]
        for i, l in enumerate(lines):
            if re.search(label_regex, l, re.IGNORECASE):
                candidates_lines = [l] + lines[i + 1 : min(len(lines), i + 1 + lookahead_lines)]
                stop_re = re.compile(r"\b(PRIMA\s+COMERCIAL|IGV|TOTAL\s+A\s+COBRAR)\b", re.IGNORECASE)
                vals: list[tuple[float, str]] = []
                for c in candidates_lines:
                    if stop_re.search(c) and c is not l:
                        break
                    for m in re.finditer(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)", c):
                        raw_val = m.group(1)
                        try:
                            f = _to_float(raw_val)
                        except Exception:
                            continue
                        vals.append((f, raw_val))
                if not vals:
                    return None
                vals.sort(key=lambda x: x[0], reverse=True)
                return vals[0][1]
        return None

    def _max_amount(raw_text: str) -> str | None:
        vals = re.findall(r"(\(?\s*(?:[-−–—]\s*)?[0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})\s*\)?|\(?\s*(?:[-−–—]\s*)?[0-9]+(?:[.,][0-9]{2})?\s*\)?)", raw_text)
        best_val = None
        best_raw = None
        for raw in vals:
            try:
                f = _to_float(raw)
            except Exception:
                continue
            if best_val is None or f > best_val:
                best_val, best_raw = f, raw
        return best_raw

    def _find_dates_near(label_regex: str, t: str, window: int = 160) -> tuple[str | None, str | None]:
        m = re.search(label_regex, t, re.IGNORECASE)
        if not m:
            return None, None
        seg = t[m.end(): m.end() + window]
        ds = re.findall(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", seg)
        if not ds:
            return None, None
        # ordenar por fecha para corregir desorden de columnas
        def to_key(d: str):
            dd, mm, yy = map(int, d.split("/"))
            return (yy, mm, dd)
        ds_sorted = sorted(ds, key=to_key)
        if len(ds_sorted) >= 2:
            return ds_sorted[0], ds_sorted[-1]
        return ds_sorted[0], None

    def _poliza_auto_modular(raw: str) -> str | None:
        m = re.search(
            r"Auto\s+Modular\s*[-–]?\s*(?:P\S{1,3}LI?ZA\s*)?(?:N[°ºo\.]?\s*)?([0-9]{6,12})",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        return m.group(1) if m else None

    def _codigo_cuota_first(raw: str) -> str | None:
        header = r"C[ÓO]D\.?\s+CUOTA"
        lines = raw.splitlines()
        for i, l in enumerate(lines):
            if re.search(header, l, re.IGNORECASE):
                for j in range(i + 1, min(i + 8, len(lines))):
                    m = re.search(r"\b([0-9]{6,12})\b", lines[j])
                    if m:
                        return m.group(1).strip()
                break
        m = re.search(header, raw, re.IGNORECASE)
        if not m:
            return None
        seg = raw[m.end() : m.end() + 200]
        m2 = re.search(r"\b([0-9]{6,12})\b", seg, re.IGNORECASE | re.DOTALL)
        return m2.group(1).strip() if m2 else None

    def _asegurado_otra_parte(raw: str) -> str | None:
        m = re.search(
            r"LA\s+COMPAÑ[ÍI]A[^,\n;]*[;:\-]?\s*y\s+de\s+la\s+otra\s+parte,\s*([^\n,;]+)",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            m = re.search(
                r"de\s+la\s+otra\s+parte,\s*([^\n,;]+)",
                raw,
                re.IGNORECASE | re.DOTALL,
            )
        return m.group(1).strip() if m else None

    def _sanitize_entity_name(s: str | None) -> str | None:
        if not s:
            return None
        out = re.sub(r"\bidentificado.*$", "", s, flags=re.IGNORECASE | re.DOTALL)
        out = re.sub(r"\bcon\s+domicilio.*$", "", out, flags=re.IGNORECASE | re.DOTALL)
        out = re.sub(r"[,;:\-]\s*$", "", out).strip()
        out = re.sub(r"\s{2,}", " ", out)
        return out or None

    def _dedupe_repeated_tokens(s: str | None) -> str | None:
        if not s:
            return None
        toks = re.split(r"\s+", s.strip())
        if len(toks) < 2:
            return s.strip()
        up = [t.upper() for t in toks]
        for unit_len in range(1, (len(up) // 2) + 1):
            if len(up) % unit_len != 0:
                continue
            unit = up[:unit_len]
            repeats = len(up) // unit_len
            if repeats >= 2 and unit * repeats == up:
                return " ".join(toks[:unit_len]).strip()
        return " ".join(toks).strip()

    def _extract_razon_social(s: str | None) -> str | None:
        if not s:
            return None
        src = _dedupe_repeated_tokens(s) or s
        src = re.sub(r"\s{2,}", " ", src).strip()
        m = re.search(
            r"\b([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\-& ]{3,180}?(?:S\.A\.C\.?|S\.R\.L\.?|E\.I\.R\.L\.?|S\.A\.A\.?|S\.A\.?))\b",
            src,
            re.IGNORECASE,
        )
        out = m.group(1).strip() if m else src
        out = _sanitize_entity_name(out) or out
        out = _dedupe_repeated_tokens(out) or out
        out = out.strip(" :.-")
        if not out:
            return None
        if re.fullmatch(r"(contratante|asegurado|direcci[oó]n|plan|agente)", out, flags=re.IGNORECASE):
            return None
        return out

    flat = _canon(text)
    head30 = "\n".join(text.splitlines()[:30]).upper()
    flat_up = flat.upper()
    is_convenio = (
        "CONVENIO DE PAGO DE PRIMAS" in head30
        or "CONVENIO DE PAGO DE PRIMAS" in flat_up
        or "MONTO TOTAL A PAGAR" in flat_up
    )
    print("[pacifico] texto extraído (head 600):", text[:600].replace("\n", "\\n"))
    print("[pacifico] flat (head 600):", flat[:600])

    # Recibo primero
    recibo = (
        _find(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\s*N[°º]\s*(?:\n|\r|\s)*([0-9]{6,12})", text)
        or _find_after(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\b", flat, r"N[°º]\s*([0-9]{6,12})", window=220)
        or _find_number_near(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\b", flat, window=320)
    )
    if not recibo:
        recibo = _codigo_cuota_first(text) or _codigo_cuota_first(flat)

    # Póliza: elegir entre candidatos cerca de "POLIZA", descartando el recibo y prefiriendo 8+ dígitos
    auto_poliza = _poliza_auto_modular(text) or _poliza_auto_modular(flat)
    poliza_candidates = (
        _numbers_after(r"\bP[ÓO]LI?ZA\b\s*:", flat, 500)
        or _numbers_after(r"\bP[ÓO]LI?ZA\b", flat, 500)
        or _numbers_after(r"\bPOLI?ZA\b", text, 500)
    )
    print("[pacifico] poliza candidatos:", poliza_candidates)
    numero_poliza = (
        auto_poliza
        or _find(r"P[ÓO]LI?ZA\s*N\D{0,3}\s*([0-9]{6,12})", flat)
        or _find(r"P[ÓO]LI?ZA\s*N\D{0,3}\s*([0-9]{6,12})", text)
        or _choose_poliza(poliza_candidates, recibo)
        or _find(r"P[ÓO]LI?ZA\s*:?\s*(?:\n|\r|\s)*([0-9]{6,12})", text)
        or _find_after(r"\bP[ÓO]LI?ZA\b\s*:?", flat, r"([0-9]{6,12})", window=200)
        or _find_number_near(r"\bP[ÓO]LI?ZA\b", flat, window=400)
        or _find_last(r"P[ÓO]LI?ZA[^0-9]{0,40}([0-9]{6,12})", flat)
        or _find_last(r"P[ÓO]LI?ZA[^0-9]{0,40}([0-9]{6,12})", text)
        or _find_last(r"P\S{1,3}LI?ZA[^0-9]{0,40}([0-9]{6,12})", flat)
        or _find_last(r"P\S{1,3}LI?ZA[^0-9]{0,40}([0-9]{6,12})", text)
    )
    if numero_poliza and not re.match(r"^[0-9]{6,12}$", numero_poliza):
        print("[pacifico] numero_poliza inválido capturado:", numero_poliza)
        numero_poliza = None
    if not numero_poliza:
        numero_poliza = (
            _find(r"\b(20[0-9]{8})\b", flat)
            or _find(r"\b(20[0-9]{8})\b", text)
        )

    def _sanitize_contratante_value(s: str | None) -> str | None:
        if not s:
            return None
        out = s.strip()
        out = re.sub(r"\s+[0-9]+$", "", out)
        out = re.sub(r"\bContratante\b", " ", out, flags=re.IGNORECASE)
        out = re.sub(r"[:\-\.\s]+", " ", out).strip()
        if not out:
            return None
        if re.fullmatch(r"(contratante|asegurado|direcci[oó]n|plan|agente)", out, flags=re.IGNORECASE):
            return None
        return out

    contratante_blk = _capture_block_after(
        r"Contratante\b", text,
        ["Asegurado", "Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA"]
    )
    print("[pacifico] contratante_blk:", contratante_blk)
    contratante = None
    if contratante_blk:
        clean_blk = _sanitize_contratante_value(contratante_blk)
        if clean_blk:
            contratante = _extract_razon_social(clean_blk) or clean_blk
    if not contratante:
        contratante = (
            _find_after(r"Contratante\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120})", window=200)
            or _find(r"Contratante\s*:?\s*(.+)", text)
        )
        contratante = _sanitize_contratante_value(contratante)

    if contratante:
        contratante = re.sub(r"\bHAW\s+K\b", "HAWK", contratante, flags=re.IGNORECASE)
        contratante = _extract_razon_social(contratante) or contratante
        contratante = contratante.upper()
        if contratante in {"CONTRATANTE", "ASEGURADO", "DIRECCION", "DIRECCIÓN", "PLAN", "AGENTE"}:
            contratante = None

    # Asegurado (acotar a razón social vía bloque y patrón de S.A.C.)
    asegurado_blk = _capture_block_after(
        r"Asegurado\b", text,
        ["Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA"]
    )
    print("[pacifico] asegurado_blk:", asegurado_blk)
    asegurado = None
    if asegurado_blk:
        asegurado = _extract_razon_social(asegurado_blk) or asegurado_blk
    else:
        asegurado = _find_after(r"Asegurado\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120})", window=200) \
                    or _find(r"Asegurado\s*:?\s*(.+)", text) \
                    or _find(r"Asegurado\s*\n\s*(.+)", text)
    if not asegurado:
        asegurado = (
            _asegurado_otra_parte(text)
            or _asegurado_otra_parte(flat)
            or _find_last(r"Asegurado\s*[:\s]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120}?S\.A\.C\.?)", text)
            or _find_last(r"Asegurado\s*[:\s]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120}?S\.A\.C\.?)", flat)
            or _find_after(r"Asegurado\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120})", window=220)
            or _capture_block_after(r"Asegurado\b", text, ["Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA"])
        )
    if asegurado:
        asegurado = re.sub(r"\bHAW\s+K\b", "HAWK", asegurado, flags=re.IGNORECASE)
        asegurado = _extract_razon_social(asegurado) or asegurado
        asegurado = asegurado.upper()
    if (not contratante) and asegurado:
        contratante = asegurado

    # Vigencia (tomar ambas fechas y ordenarlas)
    ini_vig, fin_vig = _find_dates_near(r"\bVigencia\b", flat, window=200)
    if not ini_vig or not fin_vig:
        m_vig = re.search(
            r"Vigencia\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4}).{0,80}?al\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
            text, re.IGNORECASE | re.DOTALL
        )
        if m_vig:
            ini_vig, fin_vig = m_vig.group(1), m_vig.group(2)
    inicio_vigencia = ini_vig
    vencimiento = fin_vig

    # Moneda
    moneda = (
        _find(r"\bMoneda\s*:?\s*(SOLES|DOLARES|DÓLARES|USD|PEN)", flat)
        or _find(r"\b(SOLES|DOLARES|DÓLARES|USD|PEN)\b", flat)
    )

    # Fechas
    fecha_emision = (
        _find_last(r"Fecha\s+Emisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_after(r"Fecha\s+Emisi[oó]n\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=160)
        or _find(r"\bEmisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_after(r"\bEmisi[oó]n\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=160)
    )
    ultimo_dia_pago = (
        _find_after(r"Fecha\s+Vencimiento\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
        or _find_last(r"Fecha\s+Vencimiento\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )

    prima_neta = None
    prima_comercial = None
    prima_total = None
    igv_val = None
    total_cobrar = None

    debug_notes = []
    debug_notes.append(f"detect_convenio={'sí' if is_convenio else 'no'}")

    if is_convenio:
        prima_total = (
            _monto_total_pagar(text)
            or _monto_total_pagar(flat)
            or _label_amount(r"Monto\s+total\s+a\s+pagar\s*:", text, lookahead_lines=6)
            or _label_amount(r"Monto\s+total\s+a\s+pagar\s*:", flat, lookahead_lines=6)
            or _label_amount(r"Monto\s+total\s+a\s+pagar\b", text, lookahead_lines=6)
            or _label_amount(r"Monto\s+total\s+a\s+pagar\b", flat, lookahead_lines=6)
            or _max_amount(text)
        )
        debug_notes.append(f"total_source={'regex:Monto total a pagar' if prima_total else 'no_encontrado'}")
        prima_comercial = (
            _find(r"PRIMA\s+COMERCIAL\b\s*:?\s*([0-9][0-9\.,]*)", text)
            or _first_decimal_after(r"\bPRIMA\s+COMERCIAL\b", text, lookahead_lines=4, dot_only=False)
            or _find_after(r"\bPRIMA\s+COMERCIAL\b", flat, r"([0-9]+(?:[.,][0-9]{2}))", window=140)
            or _find_last(r"PRIMA\s+COMERCIAL(?:[^A-Z]|$).*?([0-9]+(?:[.,][0-9]{2}))", text)
        )
        if prima_total:
            try:
                tot_val = _to_float(prima_total)
                prima_total = f"{tot_val:.2f}"
                if prima_comercial:
                    debug_notes.append("prima_comercial=extraída")
                else:
                    prima_comercial = f"{tot_val / 1.18:.2f}"
                    debug_notes.append("prima_comercial=calculada")
            except Exception:
                prima_total = None
                debug_notes.append("total_parse_error")
    else:
        triad_match = re.search(
            r"PRIMA\s+COMERCIAL[^0-9]{0,60}"
            r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)"
            r"[^A-Z]{0,160}I\.?G\.?V\.?[^0-9]{0,60}"
            r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)"
            r"[^A-Z]{0,200}(?:TOTAL\s+A\s+COBRAR|TOTAL\s+A\s+PAGAR)[^0-9]{0,60}"
            r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)",
            text, re.IGNORECASE | re.DOTALL
        ) or re.search(
            r"PRIMA\s+COMERCIAL[^0-9]{0,60}"
            r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)"
            r"[^A-Z]{0,160}IGV[^0-9]{0,60}"
            r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)"
            r"[^A-Z]{0,200}(?:TOTAL\s+A\s+COBRAR|TOTAL\s+A\s+PAGAR)[^0-9]{0,60}"
            r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)",
            text, re.IGNORECASE | re.DOTALL
        )
        if triad_match:
            prima_comercial = triad_match.group(1)
            igv_val = triad_match.group(2)
            total_cobrar = triad_match.group(3)
            debug_notes.append("triada=directa")
        # Montos principales por etiqueta, priorizando valores cercanos a cada rótulo.
        prima_neta = (
            _find(r"PRIMA\s+NETA\s*:?\s*([0-9][0-9\.,]*)", text)
            or _first_decimal_after(r"\bPRIMA\s+NETA\b", text, lookahead_lines=4, dot_only=False)
        )
        prima_comercial = prima_comercial or (
            _amount_after_label(r"\bPRIMA\s+COMERCIAL\b", text, lookahead_lines=2)
            or _first_decimal_after(r"\bPRIMA\s+COMERCIAL\b", text, lookahead_lines=4, dot_only=False)
            or _find_after(r"\bPRIMA\s+COMERCIAL\b", flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)", window=140)
            or _find_last(r"PRIMA\s+COMERCIAL(?:[^A-Z]|$).*?([0-9]+(?:[.,][0-9]{2}))", text)
            or _find(r"PRIMA\s+COMERCIAL\b\s*:?\s*([0-9][0-9\.,]*)", text)
        )
        igv_val = igv_val or (
            _amount_after_label(r"\bIGV\b", text, lookahead_lines=2)
            or _first_decimal_after(r"\bIGV\b", text, lookahead_lines=4, dot_only=False)
            or _find_after(r"\bIGV\b", flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)", window=140)
            or _find_last(r"\bIGV\b(?:[^A-Z]|$).*?([0-9]+(?:[.,][0-9]{2}))", text)
            or _find(r"\bIGV\b\s*:?\s*([0-9][0-9\.,]*)", text)
        )
        total_cobrar = (locals().get("total_cobrar") if "total_cobrar" in locals() else None) or (
            _amount_after_label(r"TOTAL\s+A\s+COBRAR\b", text, lookahead_lines=2)
            or _first_decimal_after(r"TOTAL\s+A\s+COBRAR\b", text, lookahead_lines=4, dot_only=False)
            or _find_after(r"TOTAL\s+A\s+COBRAR\b", flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)", window=140)
            or _find_last(r"TOTAL\s+A\s+COBRAR(?:[^A-Z]|$).*?([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))(?!\d)", text)
            or _find(r"PRIMA\s+COMERCIAL\s*\+\s*IGV\s*:?\s*([0-9][0-9\.,]*)", text)
            or _amount_after_label(r"PRIMA\s+COMERCIAL\s*\+\s*IGV\b", text, lookahead_lines=2)
            or _first_decimal_after(r"PRIMA\s+COMERCIAL\s*\+\s*IGV\b", text, lookahead_lines=4, dot_only=False)
            or _monto_total_pagar(text)
            or _monto_total_pagar(flat)
            or _label_amount(r"Monto\s+total\s+a\s+pagar\b", text, lookahead_lines=6)
            or _label_amount(r"Monto\s+total\s+a\s+pagar\b", flat, lookahead_lines=6)
        )
        debug_notes.append("total_source=normal_labels")

        # Si alguna parte de la triada falta, completarla por identidad contable.
        try:
            if not prima_comercial and total_cobrar and igv_val:
                prima_comercial = f"{_to_float(total_cobrar) - _to_float(igv_val):.2f}"
                debug_notes.append("prima_comercial=total-igv")
            if not igv_val and total_cobrar and prima_comercial:
                igv_val = f"{_to_float(total_cobrar) - _to_float(prima_comercial):.2f}"
                debug_notes.append("igv=total-prima")
            if not total_cobrar and prima_comercial and igv_val:
                total_cobrar = f"{_to_float(prima_comercial) + _to_float(igv_val):.2f}"
                debug_notes.append("total=prima+igv")
        except Exception:
            pass

        # Heurística anti-falsos positivos: si prima == total o los valores son muy pequeños, deducir globalmente
        def _is_small(v: str | None) -> bool:
            try:
                return v is not None and _to_float(v) < 3.0
            except Exception:
                return False
        suspicious = False
        try:
            if prima_comercial and total_cobrar:
                suspicious = abs(_to_float(prima_comercial) - _to_float(total_cobrar)) < 0.01
        except Exception:
            suspicious = False
        if (not prima_comercial or not igv_val or not total_cobrar) or suspicious or _is_small(prima_comercial) or _is_small(total_cobrar):
            a, b, c = _deduce_amounts_global(text)
            if a and b and c:
                prima_comercial, igv_val, total_cobrar = a, b, c
                debug_notes.append("triada=deduccion-global")

    # Ramo: inicializar para evitar NameError
    ramo = None
    ramo = (
        ramo
        or _find(r"(ACCIDENTES\s+DE\s+TRABAJO\s*\([^)]+\))", flat)
        or _find(r"Ramo\s*:?\s*([^\n]+)", text)
    )
    ramo_main = None
    ramos_producto = None
    t_low = flat.lower()
    if "pension" in t_low or "pensiones" in t_low:
        ramo_main = "SCTR"
        ramos_producto = "Pensión"
    elif "salud" in t_low or "eps" in t_low:
        ramo_main = "SCTR"
        ramos_producto = "Salud"

    inicio_vigencia = _valid_date(inicio_vigencia)
    vencimiento = _valid_date(vencimiento)
    fecha_emision = _valid_date(fecha_emision)
    ultimo_dia_pago = _valid_date(ultimo_dia_pago)

    item = {
        "numero_poliza": _clean(numero_poliza),
        "recibo": _clean(recibo),
        "contratante": _clean(contratante),
        "colectivo_asegurado": _clean(asegurado),
        "prima_neta": _clean(_money(prima_neta)),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),
        "moneda": _clean(moneda),
        "fecha_emision": _clean(fecha_emision),
        "ultimo_dia_pago": _clean(ultimo_dia_pago),
        "fecha_vencimiento": _clean(ultimo_dia_pago),
        "prima_comercial": _clean(_money(prima_comercial)),
        "prima_total": _clean(_money(total_cobrar or prima_total)),
        "prima_comercial_igv": _clean(_money(total_cobrar or prima_total)),
        "ramo": _clean(ramo_main) or _clean(ramo),
        "ramos_producto": _clean(ramos_producto),
        "tipo_documento": "convenio" if is_convenio else "normal",
        "debug_info": "; ".join(debug_notes),
    }
    print("[pacifico] numero_poliza:", item.get("numero_poliza"))
    print("[pacifico] recibo:", item.get("recibo"))
    print("[pacifico] contratante:", item.get("contratante"))
    print("[pacifico] asegurado:", item.get("colectivo_asegurado"))
    print("[pacifico] vigencia:", item.get("inicio_vigencia"), "al", item.get("vencimiento"))
    print("[pacifico] moneda:", item.get("moneda"))
    print("[pacifico] fecha_emision:", item.get("fecha_emision"))
    print("[pacifico] ultimo_dia_pago:", item.get("ultimo_dia_pago"))
    print("[pacifico] prima_comercial:", item.get("prima_comercial"))
    print("[pacifico] total (com+igv):", item.get("prima_comercial_igv"))
    print("[pacifico] ramo:", item.get("ramo"))
    print("[pacifico] ramos_producto:", item.get("ramos_producto"))

    item = {k: v for k, v in item.items() if v}
    print("[pacifico] item final pension:", item)
    return item if item else None


def parse_pacifico_convenio(text: str) -> dict | None:
    return parse_pacifico_pension(text)
