import re

def _clean(s: str | None) -> str:
    return (s or "").strip()

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.DOTALL) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

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

def parse_pacifico_salud(text: str) -> dict | None:
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
        # descartar el recibo si aparece y preferir longitudes >= 8
        filtered = [n for n in candidates if n != recibo_val]
        for n in filtered:
            if len(n) >= 8:
                return n
        return filtered[0] if filtered else None

    def _find_last(pattern: str, t: str, flags=re.IGNORECASE | re.DOTALL) -> str | None:
        matches = list(re.finditer(pattern, t, flags))
        return matches[-1].group(1).strip() if matches else None

    # Nuevo helper: empresa en mayúsculas justo debajo del título
    def _company_after(label_regex: str, t: str, window: int = 260) -> str | None:
        m = re.search(label_regex, t, re.IGNORECASE)
        if not m:
            return None
        seg = t[m.end(): m.end() + window]
        m2 = re.search(r"([A-ZÁÉÍÓÚÑ& ]+S\.?A\.?C\.?)", seg)
        if m2:
            val = m2.group(1).strip()
            if not re.search(r"CORREDOR(?:ES)?|SEGUROS|PACIFICO", val, re.IGNORECASE):
                return val
        return None

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
                pattern_dot = r"\b([0-9]+\.[0-9]{2})\b"
                pattern_any = r"\b([0-9]+(?:[.,][0-9]{2}))\b"
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
        vals = re.findall(r"\b([0-9]+(?:[.,][0-9]{2}))\b", seg)
        uniq = []
        for v in vals:
            f = float(v.replace(",", "."))
            if all(abs(f - u) > 1e-6 for u in uniq):
                uniq.append(f)
        print("[pacifico] montos cerca del bloque:", uniq)
        return uniq

    # Nuevo fallback: deducción global (total ≈ prima + igv)
    def _deduce_amounts_global(t: str) -> tuple[str | None, str | None, str | None]:
        vals_raw = re.findall(r"\b([0-9]+(?:[.,][0-9]{2}))\b", t)
        vals = []
        for v in vals_raw:
            try:
                f = float(v.replace(",", "."))
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
                pattern = r"(?:S\/\s*)?([0-9]+(?:[.,][0-9]{2}))"
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

    # Helper: toma el valor en líneas siguientes pero saltando etiquetas (incluye las sin ":")
    def _is_label_line(v: str) -> bool:
        return bool(re.match(
            r"^(Cliente|Direcci[oó]n|Localidad|R\.U\.C\.|Fecha\s+de\s+Emisi[oó]n|Asegurado|Asesor|Moneda|N[°º]\s*Relaci[oó]n|Prima|Producto|Documento|P[oó]liza/Contrato|Vigencia)\s*:?\s*$",
            v,
            re.IGNORECASE
        ))

    def _next_line_value(t: str, label_regex: str, lookahead: int = 8) -> str | None:
        lines = [l.strip() for l in t.splitlines()]
        for i, l in enumerate(lines):
            if re.search(label_regex, l, re.IGNORECASE):
                for j in range(1, lookahead + 1):
                    if i + j >= len(lines):
                        break
                    v = lines[i + j].strip()
                    # Saltar líneas vacías, etiquetas con o sin ":" al final
                    if not v or _is_label_line(v) or re.search(r":[\s]*$", v):
                        continue
                    return v
        return None

    def _acob_number(t: str) -> str | None:
        lines = [l.strip() for l in t.splitlines()]
        for i, l in enumerate(lines):
            if re.search(r"\bA\s*/\s*COB\b", l, re.IGNORECASE):
                chunk = " ".join([l] + lines[i + 1 : i + 1 + 3])
                m = re.search(r"\b([0-9]{6,12})\b", chunk)
                return m.group(1) if m else None
        m2 = re.search(r"\bA\s*/\s*COB\b[\s\S]{0,160}?\b([0-9]{6,12})\b", t, re.IGNORECASE)
        return m2.group(1) if m2 else None

    acob = _acob_number(text)
    recibo_doc = (
        _find(r"Documento\s*:\s*(?:\r?\n\s*)?(?:SCTR\s*)?(R-[0-9]{4,})\b", text)
        or _find(r"\b(R-[0-9]{4,})\b", _capture_block_after(r"Documento\b", text, ["Póliza/Contrato", "Vigencia", "Producto", "Prima", "Moneda"]) or "")
    )
    recibo_fact = (
        _find(r"FACTURA\s+ELECTR[ÓO]NICA(?:\s|\r?\n)+([A-Z0-9\-]+)", text)
        or _next_line_value(text, r"FACTURA\s+ELECTR[ÓO]NICA")
    )
    recibo = (
        acob
        or recibo_doc
        or recibo_fact
        or _find(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\s*N[°º]\s*(?:\n|\r|\s)*([0-9]{6,12})", text)
        or _find_after(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\b", flat, r"N[°º]\s*([0-9]{6,12})", window=220)
        or _find_number_near(r"LIQUIDACI[oó]N\s+DE\s+PRIMA\b", flat, window=320)
        or _find(r"\bF[0-9]{3}-[0-9]{5,8}\b", flat)
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
        or _next_line_value(text, r"P[ÓO]liza/Contrato\s*:")
    )
    if numero_poliza and not re.match(r"^[0-9]{6,12}$", numero_poliza):
        print("[pacifico] numero_poliza inválido capturado:", numero_poliza)
        numero_poliza = None

    # Asegurado: priorizar 'Cliente:' y luego 'Asegurado:', evitando tomar “Asesor”
    client_factura = _company_after(r"FACTURA\s+ELECTR[ÓO]NICA\b", text, window=180)
    cliente_vertical = _next_line_value(text, r"Cliente\s*:")
    asegurado_vertical = _next_line_value(text, r"Asegurado\s*:")

    if client_factura and not re.search(r"CORREDOR(?:ES)?|SEGUROS|PACIFICO", client_factura, re.IGNORECASE):
        asegurado = client_factura
    elif cliente_vertical and not re.search(r"CORREDOR(?:ES)?|SEGUROS|PACIFICO", cliente_vertical, re.IGNORECASE):
        asegurado = cliente_vertical
    elif asegurado_vertical and not re.search(r"CORREDOR(?:ES)?|SEGUROS|ARIAS", asegurado_vertical, re.IGNORECASE):
        asegurado = asegurado_vertical
    else:
        asegurado_blk = _capture_block_after(
            r"Asegurado\b", text,
            ["Dirección", "Plan", "Agente", "REG. PROD.", "CODIGO", "Moneda", "DOCUMENTO", "LIQUIDACION", "Vigencia", "POLIZA", "Producto"]
        )
        print("[pacifico] asegurado_blk:", asegurado_blk)
        asegurado = None
        if asegurado_blk:
            m_name = re.search(r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]+S\.A\.C\.?)", asegurado_blk)
            asegurado = m_name.group(1) if m_name else None

        if not asegurado:
            asegurado = (
                _find_last(r"Asegurado\s*[:\s]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]{6,160}?S\.A\.C\.?)", text)
                or _find_last(r"Asegurado\s*[:\s]*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\.\- ]{6,160}?S\.A\.C\.?)", flat)
                or _find_after(r"Asegurado\b\s*:?", flat, r"([A-ZÁÉÍÓÚÑ0-9\.\- ]{6,160}?S\.A\.C\.?)", window=220)
            )

    # Corrección visual del OCR: HAW K -> HAWK
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
    vencimiento = fin_vig  # Mantener el fin de vigencia tal cual

    # Moneda: buscar token dentro de una ventana luego de la etiqueta; si es SOL -> SOLES
    moneda = (
        _find_after(r"\bMoneda\b", flat, r"(SOLES|DOLARES|D[ÓO]LARES|USD|PEN|SOL)", window=300)
        or _find(r"\b(SOLES|DOLARES|D[ÓO]LARES|USD|PEN|SOL)\b", flat)
        or _next_line_value(text, r"Moneda\s*:")
    )
    if moneda:
        moneda = moneda.strip()
        if moneda.upper() == "SOL":
            moneda = "SOLES"

    # Fechas: calcular último día de pago = emisión + 15 días, y usarlo también como fecha_vencimiento (UI)
    from datetime import datetime, timedelta
    def _sumar_dias(fecha_str: str, dias: int) -> str | None:
        try:
            d = datetime.strptime(fecha_str, "%d/%m/%Y")
            d2 = d + timedelta(days=dias)
            return d2.strftime("%d/%m/%Y")
        except Exception:
            return None

    fecha_emision = (
        _find_last(r"Fecha\s+de\s+Emisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Fecha\s+Emisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _next_line_value(text, r"Fecha\s+de\s+Emisi[oó]n\s*:?")
    )
    ultimo_dia_pago = (
        _find_after(r"Fecha\s+Vencimiento\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
        or _find_last(r"Fecha\s+Vencimiento\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    fecha_vencimiento = None
    if fecha_emision:
        calc_ultimo = _sumar_dias(fecha_emision, 15)
        if calc_ultimo:
            ultimo_dia_pago = calc_ultimo
            fecha_vencimiento = calc_ultimo  # para la columna “Fecha Vencimiento” del frontend
    # Nota: NO tocar 'vencimiento' (fin de vigencia)

    # Moneda: buscar token dentro de una ventana luego de la etiqueta; si es SOL -> SOLES
    moneda = (
        _find_after(r"\bMoneda\b", flat, r"(SOLES|DOLARES|D[ÓO]LARES|USD|PEN|SOL)", window=300)
        or _find(r"\b(SOLES|DOLARES|D[ÓO]LARES|USD|PEN|SOL)\b", flat)
        or _next_line_value(text, r"Moneda\s*:")
    )
    if moneda:
        moneda = moneda.strip()
        if moneda.upper() == "SOL":
            moneda = "SOLES"

    # Fechas
    from datetime import datetime, timedelta
    def _sumar_dias(fecha_str: str, dias: int) -> str | None:
        try:
            d = datetime.strptime(fecha_str, "%d/%m/%Y")
            d2 = d + timedelta(days=dias)
            return d2.strftime("%d/%m/%Y")
        except Exception:
            return None
    fecha_emision = (
        _find_last(r"Fecha\s+de\s+Emisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Fecha\s+Emisi[oó]n\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _next_line_value(text, r"Fecha\s+de\s+Emisi[oó]n\s*:?")
    )
    ultimo_dia_pago = (
        _find_after(r"Fecha\s+Vencimiento\b", flat, r"([0-9]{2}/[0-9]{2}/[0-9]{4})", window=120)
        or _find_last(r"Fecha\s+Vencimiento\s*:?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )

    # Regla solicitada: último día de pago = emisión + 15 días; vencimiento = último día de pago
    if fecha_emision:
        calc_ultimo = _sumar_dias(fecha_emision, 15)
        if calc_ultimo:
            ultimo_dia_pago = calc_ultimo
            fecha_vencimiento = calc_ultimo  # para la columna “Fecha Vencimiento” del frontend
    # Montos: sin cambios
    prima_label = _label_amount(r"\bPrima\b(?!\s+Comercial)", text, lookahead_lines=3)
    prima_comercial = (
        _first_decimal_after(r"\bPRIMA\s+COMERCIAL\b", text, lookahead_lines=4, dot_only=False)
        or _find_after(r"\bPRIMA\s+COMERCIAL\b", flat, r"([0-9]+(?:[.,][0-9]{2}))", window=140)
        or _find_last(r"PRIMA\s+COMERCIAL(?:[^A-Z]|$).*?([0-9]+(?:[.,][0-9]{2}))", text)
    )
    if not prima_comercial and prima_label:
        prima_comercial = prima_label
    igv_val = (
        _first_decimal_after(r"\bIGV\b", text, lookahead_lines=4, dot_only=False)
        or _find_after(r"\bIGV\b", flat, r"([0-9]+(?:[.,][0-9]{2}))", window=140)
        or _find_last(r"\bIGV\b(?:[^A-Z]|$).*?([0-9]+(?:[.,][0-9]{2}))", text)
    )
    total_cobrar = (
        _first_decimal_after(r"(TOTAL\s+A\s+COBRAR|IMPORTE\s+TOTAL|V\.?\s*VENTA)\b", text, lookahead_lines=4, dot_only=False)
        or _find_after(r"(TOTAL\s+A\s+COBRAR|IMPORTE\s+TOTAL|V\.?\s*VENTA)\b", flat, r"([0-9]+(?:[.,][0-9]{2}))", window=140)
        or _find_last(r"(TOTAL\s+A\s+COBRAR|IMPORTE\s+TOTAL|V\.?\s*VENTA)(?:[^A-Z]|$).*?([0-9]+(?:[.,][0-9]{2}))", text)
    )

    # Normalizar y corregir usando la deducción por bloque si hay confusión
    def _to_float(s: str | None) -> float | None:
        if not s:
            return None
        try:
            return float(s.replace(",", "."))
        except Exception:
            return None

    pc_num = _to_float(prima_comercial)
    igv_num = _to_float(igv_val)
    tot_num = _to_float(total_cobrar)

    # Si hay total e IGV, fijar prima = total - igv (salvo que ya se leyó "Prima" explícita)
    if igv_num is not None and tot_num is not None and not (prima_label and pc_num is not None):
        prima_comercial = f"{tot_num - igv_num:.2f}"
        pc_num = _to_float(prima_comercial)

    # Si falta alguno o hay coincidencias sospechosas, deducir por bloque; si no hay bloque, usar deducción global
    if (pc_num is None or igv_num is None or tot_num is None or
        (pc_num is not None and igv_num is not None and abs(pc_num - igv_num) < 1e-6) or
        (pc_num is not None and tot_num is not None and abs(pc_num - tot_num) < 1e-6) or
        (igv_num is not None and tot_num is not None and abs(igv_num - tot_num) < 1e-6)):
        amts = _amounts_near(r"(PRIMA\s+COMERCIAL|IGV|TOTAL\s+A\s+COBRAR)", text, window=800)
        amts = [a for a in amts if a > 0.01]
        if len(amts) >= 2:
            tot_calc = max(amts)
            igv_calc = min(amts)
            prima_calc = round(tot_calc - igv_calc, 2)
            if not (prima_label and pc_num is not None):
                prima_comercial = f"{prima_calc:.2f}"
            igv_val = f"{igv_calc:.2f}"
            total_cobrar = f"{tot_calc:.2f}"
            print("[pacifico] montos deducidos -> prima:", prima_comercial, "igv:", igv_val, "total:", total_cobrar)
        else:
            pc_g, igv_g, tot_g = _deduce_amounts_global(text)
            if tot_g and igv_g:
                if not (prima_label and pc_num is not None):
                    prima_comercial = pc_g
                igv_val, total_cobrar = igv_g, tot_g
                print("[pacifico] deducción global aplicada -> prima:", prima_comercial, "igv:", igv_val, "total:", total_cobrar)

    # Si aún prima coincide con IGV/TOTAL, corregir por identidad contable
    pc_num = _to_float(prima_comercial)
    igv_num = _to_float(igv_val)
    tot_num = _to_float(total_cobrar)
    if pc_num is not None and igv_num is not None and tot_num is not None:
        if (abs(pc_num - igv_num) < 1e-6 or abs(pc_num - tot_num) < 1e-6) and not (prima_label and pc_num is not None):
            prima_comercial = f"{tot_num - igv_num:.2f}"
            print("[pacifico] prima_comercial recalculada como total - igv:", prima_comercial)

    ramo_main = "SCTR"
    ramos_producto = "Salud"

    # Extraer RUC del cliente
    ruc_candidato = None
    
    # 1. Buscar todos los candidatos RUC asociados a etiquetas explícitas (estricto)
    candidates_labeled = re.findall(r"(?:R\.?U\.?C\.?)\s*[:]?\s*(\d{11})", text, re.IGNORECASE)
    for cand in candidates_labeled:
        if cand != "20431115825": 
            ruc_candidato = cand
            break
    
    # 2. Fallback: Buscar cualquier número de 11 dígitos que empiece con 10 o 20 en todo el texto (si no se halló antes)
    if not ruc_candidato:
        all_candidates = re.findall(r"\b(10\d{9}|20\d{9})\b", text)
        for cand in all_candidates:
            if cand != "20431115825":
                ruc_candidato = cand
                break
            
    # Fallback: Si no encuentra etiqueta explícita ni candidatos válidos, buscar DNI (8 dígitos)
    if not ruc_candidato:
        candidates_dni = re.findall(r"(?:D\.?N\.?I\.?)\s*[:]?\s*(\d{8})", text, re.IGNORECASE)
        if candidates_dni:
            ruc_candidato = candidates_dni[0]

    inicio_vigencia = _valid_date(inicio_vigencia)
    vencimiento = _valid_date(vencimiento)
    fecha_emision = _valid_date(fecha_emision)
    ultimo_dia_pago = _valid_date(ultimo_dia_pago)
    fecha_vencimiento = _valid_date(fecha_vencimiento)

    item = {
        "numero_poliza": _clean(numero_poliza),
        "recibo": _clean(recibo),
        "colectivo_asegurado": _clean(asegurado),
        "inicio_vigencia": _clean(inicio_vigencia),
        "vencimiento": _clean(vencimiento),                  # Fin de Vigencia
        "fecha_vencimiento": _clean(fecha_vencimiento) or _clean(ultimo_dia_pago),  # Vencimiento (pago)
        "moneda": _clean(moneda),
        "fecha_emision": _clean(fecha_emision),
        "ultimo_dia_pago": _clean(ultimo_dia_pago),
        "prima_comercial": _clean(_money(prima_comercial)),
        "prima_comercial_igv": _clean(_money(total_cobrar)) or (
            _clean(prima_comercial) and _clean(igv_val) and
            f"{float(prima_comercial.replace(',', '.')) + float(igv_val.replace(',', '.')):.2f}"
        ) or None,
        "ramo": _clean(ramo_main),
        "ramos_producto": _clean(ramos_producto),
        "numero_documento_extracted": ruc_candidato,
    }
    print("[pacifico salud] numero_poliza:", item.get("numero_poliza"))
    print("[pacifico salud] recibo:", item.get("recibo"))
    print("[pacifico salud] asegurado:", item.get("colectivo_asegurado"))
    print("[pacifico salud] vigencia:", item.get("inicio_vigencia"), "al", item.get("vencimiento"))
    print("[pacifico salud] moneda:", item.get("moneda"))
    print("[pacifico salud] fecha_emision:", item.get("fecha_emision"))
    print("[pacifico salud] ultimo_dia_pago:", item.get("ultimo_dia_pago"))
    print("[pacifico salud] prima_comercial:", item.get("prima_comercial"))
    print("[pacifico salud] total (com+igv):", item.get("prima_comercial_igv"))
    print("[pacifico salud] ramo:", item.get("ramo"))
    print("[pacifico salud] ruc:", item.get("numero_documento_extracted"))

    item = {k: v for k, v in item.items() if v}
    print("[pacifico] item final salud:", item)
    return item if item else None
