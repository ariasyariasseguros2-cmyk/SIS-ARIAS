import re

def _clean(s: str | None) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> str | None:
    m = re.search(pattern, text, flags)
    if not m:
        return None
    try:
        return m.group(1).strip()
    except IndexError:
        return m.group(0).strip()

def _money(s: str | None) -> str | None:
    if not s:
        return None
    m = re.search(r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+)", s)
    return m.group(1) if m else s

def _valid_date(s: str | None) -> str | None:
    if not s:
        return None
    return s if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s) else None

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

def parse_pacifico_vidaley(text: str) -> dict | None:
    def _to_float_amount(s: str | None) -> float | None:
        if not s:
            return None
        try:
            txt = str(s).strip()
            if not txt:
                return None
            m = re.search(r"[-+]?\d[\d.,]*", txt)
            if not m:
                return None
            raw = (m.group(0) or "").strip()
            if not raw:
                return None
            if raw.startswith("+"):
                raw = raw[1:]
            last_dot = raw.rfind(".")
            last_comma = raw.rfind(",")
            if last_dot == -1 and last_comma == -1:
                return float(raw)
            if last_dot > last_comma:
                cleaned = raw.replace(",", "")
            elif last_comma > last_dot:
                cleaned = raw.replace(".", "").replace(",", ".")
            else:
                sep_idx = max(last_dot, last_comma)
                int_part = "".join(ch for ch in raw[:sep_idx] if (ch.isdigit() or ch == "-"))
                dec_part = "".join(ch for ch in raw[sep_idx + 1 :] if ch.isdigit())
                cleaned = f"{int_part}.{dec_part}" if dec_part else int_part
            if cleaned.count(".") > 1:
                sign = ""
                if cleaned.startswith("-"):
                    sign = "-"
                    cleaned = cleaned[1:]
                parts = cleaned.split(".")
                int_part = "".join(parts[:-1]).replace(".", "").replace(",", "")
                dec_part = parts[-1]
                cleaned = f"{sign}{int_part}.{dec_part}" if dec_part else f"{sign}{int_part}"
            return float(cleaned)
        except Exception:
            return None

    amount_group = r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))"
    amount_pattern = r"\b" + amount_group + r"\b"

    def _canon(t: str) -> str:
        flat = re.sub(r"[\r\n]+", " ", t)
        return re.sub(r"\s{2,}", " ", flat)

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
        # Preferir la PRIMERA aparición cercana a "POLIZA" y descartar el recibo
        filtered = [n for n in candidates if n != recibo_val]
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
                pattern_dot = r"\b([0-9]{1,3}(?:[.,][0-9]{3})*\.[0-9]{2}|[0-9]+\.[0-9]{2})\b"
                pattern_any = amount_pattern
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
        vals = re.findall(amount_pattern, seg, re.IGNORECASE | re.DOTALL)
        uniq = []
        for v in vals:
            f = _to_float_amount(v)
            if f is None:
                continue
            if all(abs(f - u) > 1e-6 for u in uniq):
                uniq.append(f)
        print("[pacifico] montos cerca del bloque:", uniq)
        return uniq

    # Nuevo fallback: deducción global (total ≈ prima + igv)
    def _deduce_amounts_global(t: str) -> tuple[str | None, str | None, str | None]:
        vals_raw = re.findall(amount_pattern, t, re.IGNORECASE | re.DOTALL)
        vals = []
        for v in vals_raw:
            try:
                f = _to_float_amount(v)
                if f is None:
                    continue
                # deduplicar por 2 decimales
                if all(abs(f - u) > 1e-6 for u in vals):
                    vals.append(f)
            except Exception:
                continue
        vals.sort()
        if not vals:
            return None, None, None
        # probar combinaciones buscando c ~ a + b; preferir a > b (prima > igv)
        for c in reversed(vals):
            for a in reversed(vals):
                if a >= c:
                    continue
                for b in vals:
                    if b >= c:
                        continue
                    if a <= 0 or b <= 0:
                        continue
                    if abs((a + b) - c) <= 0.01 and a > b:
                        print("[pacifico] deducción global -> prima:", f"{a:.2f}", "igv:", f"{b:.2f}", "total:", f"{c:.2f}")
                        return f"{a:.2f}", f"{b:.2f}", f"{c:.2f}"
        return None, None, None

    # Nuevo: leer el monto en la misma/primeras líneas tras la etiqueta
    def _label_amount(label_regex: str, raw_text: str, lookahead_lines: int = 6) -> str | None:
        lines = [l.strip() for l in raw_text.splitlines()]
        for i, l in enumerate(lines):
            if re.search(label_regex, l, re.IGNORECASE):
                pattern = r"(?:S\/\s*)?" + amount_group
                found = re.findall(pattern, l)
                if found:
                    return found[-1]
                for j in range(1, lookahead_lines + 1):
                    if i + j >= len(lines):
                        break
                    nxt = lines[i + j]
                    if re.search(r"\b(PRIMA\s+COMERCIAL|IGV|TOTAL\s+A\s+COBRAR)\b", nxt, re.IGNORECASE):
                        break
                    found = re.findall(pattern, nxt)
                    if found:
                        return found[-1]
                return None
        return None

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

    flat = _canon(text)
    print("[pacifico] texto extraído (head 600):", text[:600].replace("\n", "\\n"))
    print("[pacifico] flat (head 600):", flat[:600])

    # Recibo primero
    recibo = (
        _find(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\s*N[°º]\s*(?:\n|\r|\s)*([0-9]{6,12})", text)
        or _find_after(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\b", flat, r"N[°º]\s*([0-9]{6,12})", window=220)
        or _find_number_near(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\b", flat, window=320)
    )

    # Póliza: elegir entre candidatos cerca de "POLIZA", descartando el recibo y prefiriendo 8+ dígitos
    poliza_candidates = (
        _numbers_after(r"\bP[ÓO]LI?ZA\b\s*:", flat, 500)
        or _numbers_after(r"\bP[ÓO]LI?ZA\b", flat, 500)
        or _numbers_after(r"\bPOLI?ZA\b", text, 500)
    )
    print("[pacifico] poliza candidatos:", poliza_candidates)
    numero_poliza = (
        _choose_poliza(poliza_candidates, recibo)
        or _find(r"P[ÓO]LI?ZA\s*:?\s*(?:\n|\r|\s)*([0-9]{6,12})", text)
        or _find_after(r"\bP[ÓO]LI?ZA\b\s*:?", flat, r"([0-9]{6,12})", window=200)
        or _find_number_near(r"\bP[ÓO]LI?ZA\b", flat, window=400)
    )
    if numero_poliza and not re.match(r"^[0-9]{6,12}$", numero_poliza):
        print("[pacifico] numero_poliza inválido capturado:", numero_poliza)
        numero_poliza = None

    # Contratante (Nuevo)
    contratante_blk = _capture_block_after(
        r"Contratante\b", text,
        ["Asegurado", "Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA"]
    )
    print("[pacifico] contratante_blk:", contratante_blk)
    contratante = None
    if contratante_blk:
        # Intentar limpiar código numérico al final si existe (ej: 12377047)
        clean_blk = re.sub(r"\s+[0-9]+$", "", contratante_blk.strip())
        # Buscar patrón de empresa
        m_name = re.search(r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]+(?:S\.A\.C\.?|S\.R\.L\.?|E\.I\.R\.L\.?|S\.A\.?|S\.A\.A\.?))", clean_blk, re.IGNORECASE)
        contratante = m_name.group(1) if m_name else clean_blk
    else:
        contratante = (
            _find_after(r"Contratante\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120})", window=200)
            or _find(r"Contratante\s*:?\s*(.+)", text)
        )
    
    if contratante:
        contratante = re.sub(r"\bHAW\s+K\b", "HAWK", contratante, flags=re.IGNORECASE)

    # Asegurado (acotar a razón social vía bloque y patrón de S.A.C.)
    asegurado_blk = _capture_block_after(
        r"Asegurado\b", text,
        ["Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA"]
    )
    print("[pacifico] asegurado_blk:", asegurado_blk)
    asegurado = None
    if asegurado_blk:
        m_name = re.search(r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]+S\.A\.C\.?)", asegurado_blk)
        asegurado = m_name.group(1) if m_name else asegurado_blk
    else:
        asegurado = _find_after(r"Asegurado\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120})", window=200) \
                    or _find(r"Asegurado\s*:?\s*(.+)", text) \
                    or _find(r"Asegurado\s*\n\s*(.+)", text)
    # Asegurado: usar la ÚLTIMA coincidencia que termine en S.A.C.
    asegurado = (
        _find_last(r"Asegurado\s*[:\s]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120}?S\.A\.C\.?)", text)
        or _find_last(r"Asegurado\s*[:\s]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120}?S\.A\.C\.?)", flat)
        or _find_after(r"Asegurado\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,120})", window=220)
        or _capture_block_after(r"Asegurado\b", text, ["Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA"])
    )
    if asegurado:
        asegurado = re.sub(r"\bHAW\s+K\b", "HAWK", asegurado, flags=re.IGNORECASE)

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
        or _find_after(r"Fecha\s+Emisi[oó]n\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
    )
    ultimo_dia_pago = (
        _find_after(r"Fecha\s+Vencimiento\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
        or _find_last(r"Fecha\s+Vencimiento\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )

    # Montos: extracción por etiqueta y no sobreescribir si ya existen
    prima_comercial = (
        _first_decimal_after(r"\bPRIMA\s+COMERCIAL\b", text, lookahead_lines=4, dot_only=False)
        or _find_after(r"\bPRIMA\s+COMERCIAL\b", flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", window=200)
        or _find_last(r"PRIMA\s+COMERCIAL(?:[^A-Z]|$).*?([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", text)
    )
    igv_label = r"(?:\bIGV\b|I\.?G\.?V\.?|\bIMPSTO\.?\s*GRA(?:L\.?)?(?:\s*A\s*VENTA)?\b|\bIMPUESTO\s+GENERAL\s+A\s+LAS\s+VENTAS\b)"
    igv_val = (
        _first_decimal_after(igv_label, text, lookahead_lines=4, dot_only=False)
        or _find_after(igv_label, flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", window=220)
        or _find_last(igv_label + r"(?:[^A-Z]|$).*?([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", text)
    )
    total_a_cobrar_label = r"TOTAL\s+A\s+(?:COBRAR|PAGAR|CANCELAR)\b"
    total_label = r"(?:TOTAL\s+A\s+(?:COBRAR|PAGAR|CANCELAR)|PRIMA\s+COMERCIAL\s*\+\s*IGV|IMPORTE\s+TOTAL)"
    total_cobrar = (
        _first_decimal_after(total_a_cobrar_label, text, lookahead_lines=6, dot_only=False)
        or _find_after(total_a_cobrar_label, flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", window=320)
        or _find_last(total_a_cobrar_label + r"(?:[^A-Z]|$).*?([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", text)
        or _first_decimal_after(total_label, text, lookahead_lines=5, dot_only=False)
        or _find_after(total_label, flat, r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", window=260)
        or _find_last(total_label + r"(?:[^A-Z]|$).*?([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))", text)
    )
    # Reforzar lectura de línea si alguna quedó vacía
    if not prima_comercial:
        prima_comercial = _label_amount(r"\bPRIMA\s+COMERCIAL\b", text, lookahead_lines=6)
    if not igv_val:
        igv_val = _label_amount(igv_label, text, lookahead_lines=6)
    if not total_cobrar:
        total_cobrar = _label_amount(total_label, text, lookahead_lines=6)

    # Completar triada sin heurística global: usar identidades contables
    pc_num = _to_float_amount(prima_comercial)
    igv_num = _to_float_amount(igv_val)
    tot_num = _to_float_amount(total_cobrar)

    # Sanidad: evitar falsos positivos (ej. TCEA 2.02) cuando la prima es 1,100.31
    if tot_num is not None and pc_num is not None:
        if (tot_num < pc_num) or (pc_num >= 100 and tot_num < 10) or (pc_num >= 50 and tot_num > (pc_num * 5)):
            total_cobrar = None
            tot_num = None
    if igv_num is not None and pc_num is not None:
        if igv_num < 0 or (pc_num >= 100 and igv_num < 1):
            igv_val = None
            igv_num = None

    if tot_num is not None and igv_num is not None and pc_num is None:
        prima_comercial = f"{tot_num - igv_num:.2f}"
        pc_num = _to_float_amount(prima_comercial)
    if pc_num is not None and igv_num is not None and tot_num is None:
        total_cobrar = f"{pc_num + igv_num:.2f}"
        tot_num = _to_float_amount(total_cobrar)
    if pc_num is not None and tot_num is not None and igv_num is None:
        igv_val = f"{tot_num - pc_num:.2f}"
        igv_num = _to_float_amount(igv_val)

    # NO usar deducción global si ya hay montos por etiqueta
    # Solo último recurso si los tres están vacíos
    if pc_num is None and igv_num is None and tot_num is None:
        pc_g, igv_g, tot_g = _deduce_amounts_global(text)
        prima_comercial, igv_val, total_cobrar = pc_g, igv_g, tot_g

    ramo = None
    ramo = (
        ramo
        or (_find(r"\bVida\s+Ley\b", text) and "Vida Ley")
        or _find(r"(ACCIDENTES\s+DE\s+TRABAJO\s*\([^)]+\))", flat)
        or _find(r"Ramo\s*:?\s*([^\n]+)", text)
    )

    ramo_main = None
    ramos_producto = None
    t_low = flat.lower()
    if "vida ley" in t_low:
        ramo_main = "VIDA - LEY"
        if "empleados" in t_low:
            ramos_producto = "EMPLEADOS"

    inicio_vigencia = _valid_date(inicio_vigencia)
    vencimiento = _valid_date(vencimiento)
    fecha_emision = _valid_date(fecha_emision)
    ultimo_dia_pago = _valid_date(ultimo_dia_pago)

    item = {
        "numero_poliza": _clean(numero_poliza),
        "recibo": _clean(recibo),
        "contratante": _clean(contratante),
        "colectivo_asegurado": _clean(asegurado),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),
        "moneda": _clean(moneda),
        "fecha_emision": _clean(fecha_emision),
        "ultimo_dia_pago": _clean(ultimo_dia_pago),
        "fecha_vencimiento": _clean(ultimo_dia_pago),
        "fecha_vecimiento": _clean(ultimo_dia_pago),
        "prima_comercial": _clean(_money(prima_comercial)),
        "prima_comercial_igv": _clean(_money(total_cobrar)) or (
            _clean(prima_comercial) and _clean(igv_val) and
            (
                (lambda a, b: f"{a + b:.2f}" if (a is not None and b is not None) else None)(
                    _to_float_amount(prima_comercial), _to_float_amount(igv_val)
                )
            )
        ) or None,
        "ramo": _clean(ramo_main) or _clean(ramo),
        "ramos_producto": _clean(ramos_producto),
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

    item = {k: v for k, v in item.items() if v}
    print("[pacifico] item final vida ley:", item)
    return item  # FIX: retornar el objeto  
