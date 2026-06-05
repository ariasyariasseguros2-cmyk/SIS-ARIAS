import re
import pdfplumber

def addPacificoGenerales_V2(filepath):
    def _valid_date(s: str | None) -> str:
        return s if s and re.fullmatch(r"\d{2}/\d{2}/\d{4}", s) else ""

    data = {
        "aseguradora": "PACIFICO",
        "producto": "MULTISALUD",
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
        "moneda": "S/.", 
        "error": None
    }
    
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        
        # Debug: print partial text to help diagnosis if needed (visible in server logs)
        print(f"[PacificoGeneralesV2] Extracted text length: {len(text)}")
        
    except Exception as e:
        data["error"] = f"Error al leer PDF: {str(e)}"
        print(f"[PacificoGeneralesV2] Error: {e}")
        return data
    
    try:
        # Detect currency near the total or by majority/priority labels
        # We look for symbols near the amounts first, or specific labels
        # For Pacifico, we look for the block containing PRIMA COMERCIAL and IGV
        # The total is usually preceded by S/. or US$
        
        # Look for S/. or US$ specifically near the "TOTAL" label
        total_block = re.search(r'(?:TOTAL|IMPORTE\s*TOTAL|IMPORTETOTAL)[^\d\n]{0,30}(S\/\.?|US\$|USD|SOLES|PEN)[^\d\n]*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})', text, re.IGNORECASE)
        if total_block:
            curr = total_block.group(1).upper()
            if 'US$' in curr or 'USD' in curr:
                data["moneda"] = "US$"
            else:
                data["moneda"] = "S/."
        else:
            # Fallback: search for any S/. or US$ followed by a number that looks like a total (high amount)
            # or just look at the most common currency symbol in the document
            compact = re.sub(r"\s+", "", (text or "").upper())
            has_usd = ("US$" in compact) or ("USD" in compact) or ("DOLAR" in compact) or ("DÓLAR" in compact)
            has_sol = ("S/" in compact) or ("SOLES" in compact) or ("PEN" in compact)

            if has_usd and not has_sol:
                data["moneda"] = "US$"
            elif has_sol and not has_usd:
                data["moneda"] = "S/."
            elif has_usd and has_sol:
                near_amount = re.findall(r"(S\/\.?|US\$|USD)\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2}", text, re.IGNORECASE)
                if near_amount:
                    counts = {"US$": 0, "S/.": 0}
                    for tok in near_amount:
                        up = re.sub(r"\s+", "", (tok or "").upper())
                        if up.startswith("S/") or "PEN" in up or "SOL" in up:
                            counts["S/."] += 1
                        elif up.startswith("US$") or "USD" in up or "$" == up or "DOL" in up:
                            counts["US$"] += 1
                    data["moneda"] = "US$" if counts["US$"] > counts["S/."] else "S/."
                else:
                    data["moneda"] = "S/."
            else:
                data["moneda"] = "S/."
    except Exception:
        pass

    # 1. Póliza
    # Matches: Póliza : 13404419, Póliza N°: 13404419, Póliza No 13404419-65874107
    # We capture the first sequence of digits
    m_pol = re.search(r'P[óo]liza(?:.*?)[:.]?\s*(\d+)', text, re.IGNORECASE)
    if m_pol:
        data["poliza"] = m_pol.group(1)
        print(f"[PacificoGeneralesV2] Poliza found: {data['poliza']}")

    # 1.1 Recibo (Aviso de Cobranza)
    # Matches: AVISO DE COBRANZA N° 93140094
    m_rec = re.search(r'AVISO\s+DE\s+COBRANZA\s+N[°ºo.]?\s*(\d+)', text, re.IGNORECASE)
    if m_rec:
        data["recibo"] = m_rec.group(1)
        print(f"[PacificoGeneralesV2] Recibo found: {data['recibo']}")

    # 2. Vigencia
    # Vigencia : 18/01/2026 - 18/01/2027
    m_vig = re.search(
        r'Vigencia\s*[:.]?\s*(\d{2}/\d{2}/\d{4})(?:\s*-\s*(\d{2}/\d{2}/\d{4}))?',
        text,
        re.IGNORECASE,
    )
    if not m_vig:
        m_vig = re.search(r'Vigencia\s*\n\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if not m_vig:
        m_vig = re.search(r'(\d{2}/\d{2}/\d{4})\s*\n\s*Vigencia\b', text, re.IGNORECASE)
    if m_vig:
        data["inicio"] = m_vig.group(1)
        if len(m_vig.groups()) > 1 and m_vig.group(2):
            data["fin"] = m_vig.group(2)

    # 2.2 Fecha de Pago (Cronograma - Vencimiento Cuota)
    # Buscamos la primera fecha en el cronograma: 1/04 01/02/2026
    # OJO: La fecha de vencimiento que pide el usuario es la del primer pago (01/02/2026)
    # Pattern: X/Y  DD/MM/YYYY
    m_pago = re.search(r'(?:Cronograma|Cuota).+?(\d{1,2}/\d{1,2})\s+(\d{2}/\d{2}/\d{4})', text, re.DOTALL | re.IGNORECASE)
    if not m_pago:
        # Fallback: simple search for pattern like "1/04 01/02/2026" anywhere
        m_pago = re.search(r'\b\d{1,2}/\d{1,2}\s+(\d{2}/\d{2}/\d{4})', text)

    if m_pago:
        data["fecha_pago"] = m_pago.group(2) if len(m_pago.groups()) > 1 else m_pago.group(1)
        # Verify group index. In regex 1: (\d{1,2}/\d{1,2}) is group 1. (\d{2}/\d{2}/\d{4}) is group 2.
        # So we want group 2.
        print(f"[PacificoGeneralesV2] Fecha Pago found: {data['fecha_pago']}")

    # 2.1 Emisión
    # Try "Emisión : 05/11/2025"
    m_emision = re.search(r'Emisi[óo]n\s*[:.]?\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if m_emision:
        data["emision"] = m_emision.group(1)
    else:
        # Try "Emitido el 05 de Noviembre del 2025"
        m_emitido = re.search(r'Emitido\s+el\s+(\d{1,2})\s+de\s+([A-Za-z]+)\s+(?:del\s+)?(\d{4})', text, re.IGNORECASE)
        if m_emitido:
            day = m_emitido.group(1).zfill(2)
            month_str = m_emitido.group(2).lower()
            year = m_emitido.group(3)
            
            months = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
                'julio': '07', 'agosto': '08', 'setiembre': '09', 'septiembre': '09', 'octubre': '10', 
                'noviembre': '11', 'diciembre': '12'
            }
            
            if month_str in months:
                data["emision"] = f"{day}/{months[month_str]}/{year}"


    # 3. Asegurado / Cliente
    # Priority: Cliente > Asegurado > Señor(a) > Contexto RUC
    candidates = []
    
    def is_valid_name(s):
        s = s.strip()
        # Remove trailing numbers (DNI/Code) if they exist (e.g. "NAME 12345678")
        s = re.sub(r'\s+\d+$', '', s)
        s = s.strip()
        
        if len(s) < 4: return False
        
        # Names in these documents are typically 2-5 words. 
        # Sentences in the policy text are usually much longer.
        words = s.split()
        if len(words) > 6:
            return False

        # If it has multiple lowercase words (excluding "de", "la"), it's likely a sentence
        lowercase_words = [w for w in words if w.islower() and w not in ['de', 'la', 'y']]
        if len(lowercase_words) > 1:
            return False

        # Extended list of invalid terms to exclude common footer/info strings and legal phrases
        invalid_terms = ['afiliados', 'todos los', 'trabajadores', 'resumen', 'multisalud', 
                         'condiciones', 'clausula', 's, afiliados', 'estimado(a)',
                         'pág', 'pag', 'fecha', 'representante legal', 'artículo', 'articulo', 'convenio de pago',
                         'www.', 'http', 'teléfono', 'telefono', 'dirección', 'direccion', 'calle', 'avenida', 'jr.', 'av.',
                         'defensoría', 'defensoria', 'correo electrónico', 'email', 'probabilidad', 'enfermedades',
                         'titular', 'dependientes', 'residan', 'perú', 'derecho', 'solicitud', 'cobertura']
        
        lower_s = s.lower()
        if any(term in lower_s for term in invalid_terms):
            return False
        if lower_s.startswith('ruc'):
            return False
        # Must start with Uppercase or Digit
        if s and not s[0].isupper() and not s[0].isdigit():
            return False
        # Reject if it looks like a URL or has too many symbols
        if 'www.' in lower_s or '.com' in lower_s or '@' in lower_s:
            return False
        return True

    # 1. Extract from "Cliente :"
    matches_cliente = re.findall(r'^\s*Cliente\s*[:.]?\s*([^\n]+)', text, re.IGNORECASE | re.MULTILINE)
    for m in matches_cliente:
        raw = re.sub(r'\s+\d+$', '', m).strip()
        if is_valid_name(raw):
            candidates.append(raw)
            
    # 2. Extract from "Asegurado :"
    matches_aseg = re.findall(r'^\s*Asegurado\s*[:.]?\s*([^\n]+)', text, re.IGNORECASE | re.MULTILINE)
    for m in matches_aseg:
        raw = re.sub(r'\s+\d+$', '', m).strip()
        if is_valid_name(raw):
            candidates.append(raw)

    # 3. Extract from "Señor(a).-"
    m_senor = re.search(r'Señor\(a\)\.-\s*\n([^\n]+)', text)
    if m_senor:
        raw = m_senor.group(1).strip()
        if is_valid_name(raw):
            candidates.append(raw)
            
    # 4. Extract uppercase line before RUC (Strong signal for company/person name)
    m_ruc_before = re.search(r'([A-ZÑ\s]{10,})\n\s*R\.?U\.?C', text)
    if m_ruc_before:
        raw = m_ruc_before.group(1).strip()
        if is_valid_name(raw):
             candidates.append(raw)

    # Decision Logic
    # Collect all valid candidates and pick the most frequent/appropriate one
    valid_candidates = [c for c in candidates if is_valid_name(c)]
    
    if valid_candidates:
        # Count occurrences of each valid candidate to find the most frequent (likely the name)
        from collections import Counter
        counts = Counter(valid_candidates)
        # Prioritize ALL UPPERCASE names among the most frequent
        most_common = counts.most_common()
        best_candidate = most_common[0][0]
        
        # If there's a tie or close second, prefer the one in all caps
        highest_count = most_common[0][1]
        for cand, count in most_common:
            if count == highest_count and cand.isupper():
                best_candidate = cand
                break
        
        data["asegurado"] = best_candidate
            
    print(f"[PacificoGeneralesV2] Valid candidates found: {valid_candidates}")
    print(f"[PacificoGeneralesV2] Selected Asegurado: {data['asegurado']}")

    # 4. Importes
    def clean_amount(s):
        try:
            raw = (s or '').strip()
            if not raw:
                return 0.0
            raw = raw.replace('−', '-').replace('–', '-').replace('—', '-')
            neg = False
            m_paren = re.match(r'^\((.*)\)$', raw)
            if m_paren:
                neg = True
                raw = (m_paren.group(1) or '').strip()
            if re.match(r'^\s*-\s*', raw):
                neg = True
            raw = re.sub(r'[^\d.,]', '', raw)
            if not raw:
                return 0.0
            
            # Robust parsing for mixed separators (e.g. 15.451.45 or 15,451.45)
            # Find the last separator (either . or ,)
            last_dot = raw.rfind('.')
            last_comma = raw.rfind(',')
            last_sep = max(last_dot, last_comma)
            
            if last_sep == -1:
                # No separator, assume integer
                num = float(raw)
                return -abs(num) if neg else num
            
            # Check if it's a thousands separator or decimal
            # If there are multiple separators, or the last one is followed by 2 digits (standard currency), treat as decimal
            # We assume the last separator is the decimal separator
            
            integer_part = raw[:last_sep].replace('.', '').replace(',', '')
            decimal_part = raw[last_sep+1:]
            
            num = float(f"{integer_part}.{decimal_part}")
            return -abs(num) if neg else num
        except:
            return 0.0

    # Estrategia: Buscar el bloque de Conceptos -> Importe
    # PRIMA COMERCIAL   15.451.45
    # ...
    # I.G.V.            2.781.28
    
    # Prima Neta / Comercial
    # Buscamos específicamente "PRIMA COMERCIAL" seguido de un monto
    # Usamos search para encontrar la primera coincidencia válida en el bloque principal
    m_prima = re.search(r'PRIMA\s+(?:COMERCIAL|NETA)[^\d\n\-−–—]{0,60}(\(?\s*[-−–—]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\s*\)?)', text, re.IGNORECASE)
    if m_prima:
        data["prima_neta"] = clean_amount(m_prima.group(1))

    # IGV
    # Buscamos IGV cercano
    m_igv = re.search(r'I\.?G\.?V\.?[^\d\n\-−–—]{0,60}(\(?\s*[-−–—]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\s*\)?)', text, re.IGNORECASE)
    if m_igv:
        val = clean_amount(m_igv.group(1))
        # Validación simple para no confundir con otros montos
        if val != data["prima_neta"]:
             data["igv"] = val

    # Total Calculation
    # Si tenemos ambos, sumamos
    if data["prima_neta"] != 0:
        if data["igv"] == 0:
             # Try to calculate 18%
             data["igv"] = round(data["prima_neta"] * 0.18, 2)
        
        data["total"] = round(data["prima_neta"] + data["igv"], 2)
    else:
        # Fallback: search for Total label (S/.)
        # S/. 18.232.73
        m_total = re.search(r'(?:TOTAL|S/\.)[^\d\n\-−–—]{0,60}(\(?\s*[-−–—]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\s*\)?)', text, re.IGNORECASE)
        if m_total:
             data["total"] = clean_amount(m_total.group(1))
             # Back-calculate net
             data["prima_neta"] = round(data["total"] / 1.18, 2)
             data["igv"] = round(data["total"] - data["prima_neta"], 2)

    data["inicio"] = _valid_date(data.get("inicio"))
    data["fin"] = _valid_date(data.get("fin"))
    data["fecha_pago"] = _valid_date(data.get("fecha_pago"))
    data["emision"] = _valid_date(data.get("emision"))

    print(f"[PacificoGeneralesV2] Extracted: {data}")
    return data
