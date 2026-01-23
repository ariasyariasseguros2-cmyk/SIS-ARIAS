# NUEVO: parser específico para La Positiva – Vida Ley
import re
from typing import Optional, Dict
from datetime import datetime, timedelta

def _find(pattern: str, text: str, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

def _money(s: Optional[str]) -> Optional[str]:
    if not s: return None
    # Normalizar whitespace y currency, y unificar separadores para no perder decimales
    s2 = re.sub(r"\s+", "", s).replace("S/", "").replace("s/", "")
    if "," in s2 and "." in s2:
        s3 = s2.replace(",", "")
    elif "," in s2 and "." not in s2:
        s3 = s2.replace(".", "").replace(",", ".")
    else:
        s3 = s2
    m = re.search(r"([0-9]+(?:\.[0-9]{2})?)", s3)
    return f"{float(m.group(1)):.2f}" if m else None

# NUEVO: tomar la última coincidencia cuando hay múltiples bloques en el PDF
def _find_last(pattern: str, text: str, flags=re.IGNORECASE):
    ms = list(re.finditer(pattern, text, flags))
    return ms[-1].group(1).strip() if ms else None

def parse_positiva_Salud(text: str) -> Dict[str, str]:
    t_low = text.lower()

    # Encabezados: Proforma / Póliza / Contrato
    numero_proforma = (
        _find(r"N[úu]mero\s+de\s+Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
        or _find(r"\bProforma\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"N[úu]mero\s+de\s+Proforma\s*([0-9A-Z\-]+)", text)
        or _find(r"\bN[úu]mero\s*Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
    )
    poliza_nro = (
        _find(r"P[oó]liza\s*Nro\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"P[oó]liza\s*N°\s*:\s*([0-9A-Z\-]+)", text)
        or _find(r"Poliza\s*:\s*([0-9A-Z\-]+)", text)
    )
    contrato_nro = _find(r"Contrato\s+Nro\s*:\s*([0-9A-Z\-]+)", text)

    # Vigencias: usar la última coincidencia por si hay múltiples bloques
    vig_desde = _find_last(r"Vigencia Desde\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    vig_hasta = _find_last(r"Hasta\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    # Capturar variantes de “Vencimiento”
    pago_venc = (
        _find_last(r"Vencimiento\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Fecha\s+de\s+Vencimiento\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
        or _find_last(r"Vencimiento\s+(?:Proforma|Recibo)\s*[:\n]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    )
    fecha_venc = pago_venc

    moneda = _find(r"Moneda\s*:\s*([A-Za-z]+)", text)
    emision = _find(r"Emisi[oó]n\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)

    # Asegurado / Contratante
    contratante = _find(r"Contratante\s*:\s*(.+)", text)
    asegurado = _find(r"Asegurado\s*:\s*(.+)", text)
    colectivo_asegurado = (asegurado or contratante)

    # Ramo: preferir el campo explícito; si no, inferir por texto
    ramo = _find(r"Ramo\s*:\s*(.+)", text)
    if not ramo:
        has_salud = ("salud" in t_low) or ("eps" in t_low)
        has_pension = ("pensi\u00f3n" in t_low) or ("pension" in t_low)
        if has_salud and has_pension:
            ramo = "SCTR SALUD"
        elif has_salud:
            ramo = "SCTR SALUD"
        elif has_pension:
            ramo = "SCTR PENSION"
        else:
            ramo = "La Positiva"

    # NUEVO: si el PDF contiene SALUD y PENSIÓN, forzar a tomar los encabezados de SALUD (últimas coincidencias)
    has_salud = ("salud" in t_low) or ("eps" in t_low)
    has_pension = ("pensi\u00f3n" in t_low) or ("pension" in t_low)
    if has_salud and has_pension:
        np_last = (
            _find_last(r"N[úu]mero\s+de\s+Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
            or _find_last(r"\bProforma\s*:\s*([0-9A-Z\-]+)", text)
            or _find_last(r"N[úu]mero\s+de\s+Proforma\s*([0-9A-Z\-]+)", text)
            or _find_last(r"\bN[úu]mero\s*Proforma\s*[:\n]\s*([0-9A-Z\-]+)", text)
        )
        if np_last:
            numero_proforma = np_last

        contrato_last = _find_last(r"Contrato\s+Nro\s*:\s*([0-9A-Z\-]+)", text)
        if contrato_last:
            contrato_nro = contrato_last

        poliza_last = (
            _find_last(r"P[oó]liza\s*Nro\s*:\s*([0-9A-Z\-]+)", text)
            or _find_last(r"P[oó]liza\s*N°\s*:\s*([0-9A-Z\-]+)", text)
            or _find_last(r"Poliza\s*:\s*([0-9A-Z\-]+)", text)
        )
        if poliza_last:
            poliza_nro = poliza_last

    # Conceptos: capturas y prioridades (usar última coincidencia del bloque)
    sobrevivencia = _money(_find_last(r"Sobrevivencia[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE))
    costos_emision = _money(_find_last(r"Costos?\s+de\s+Emisi[oó]n[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE)) or \
                     _money(_find_last(r"Costos?\s+Emisi[oó]n[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE))
    prima_comercial_inclusive = _money(_find(r"Prima\s+Comercial[\s\S]*?Incluye[\s\S]*?Emisi[oó]n[\s\S]*?(?:[:=]|\s)?\s*(?:S?\/)?\s*([0-9\., ]+)", text))
    igv_val = _money(_find(r"(?:Impuesto\s+General\s+a\s+las\s+Ventas|IGV)[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text))
    prima_comercial_igv = _money(_find(r"Prima\s+Comercial\s*\+\s*IGV[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text))
    prima_total_alt = _money(_find(r"(?:Importe\s+Total|Total\s+a\s+Pagar|Total|Prima\s+Total)[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text))

    # NUEVO: capturar la fila “SCTR SALUD” como Prima Comercial
    sctr_salud_val = _money(_find_last(r"SCTR\s+SALUD[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE))
    if not sctr_salud_val:
        # Variante cuando 'Descripción' y 'Importes' están separados
        sctr_salud_val = _money(_find_last(r"Descripci[oó]n[\s\S]*?SCTR\s+SALUD[\s\S]*?Importes[\s\S]*?(?:S?\/)?\s*([0-9\., ]+)", text, flags=re.IGNORECASE))

    # NUEVO: captura por filas del cuadro (más robusta frente a saltos de línea/columnas)
    for m in re.finditer(
        r"(Sobrevivencia|Costos?\s+de\s+Emisi[oó]n|Impuesto\s+General\s+a\s+las\s+Ventas|SCTR\s+SALUD)[\s:]*S?\/?\s*([0-9\., ]+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        label = m.group(1).lower()
        amount = _money(m.group(2))
        if "sobrevivencia" in label:
            sobrevivencia = sobrevivencia or amount
        elif "costos" in label:
            costos_emision = costos_emision or amount
        elif "impuesto" in label or "igv" in label:
            igv_val = igv_val or amount
        elif "sctr salud" in label:
            sctr_salud_val = sctr_salud_val or amount

    # Fallbacks calculados
    if not prima_total_alt and prima_comercial_igv and igv_val:
        try:
            prima_total_alt = f"{float(prima_comercial_igv) - float(igv_val):.2f}"
        except Exception:
            pass

    if not costos_emision and prima_total_alt and sobrevivencia:
        try:
            costos_emision = f"{float(prima_total_alt) - float(sobrevivencia):.2f}"
        except Exception:
            pass

    # Prima Neta = Sobrevivencia (si aplica a Vida Ley); en Salud puede no existir
    prima_neta = sobrevivencia

    # NUEVO: Prima Comercial prioriza “SCTR SALUD”; luego lógica existente
    if sctr_salud_val:
        prima_comercial = sctr_salud_val
        # Fijar SALUD si detectamos la fila explícita de SALUD
        ramo = "SCTR SALUD"
    else:
        if prima_neta and costos_emision:
            try:
                prima_comercial = f"{float(prima_neta) + float(costos_emision):.2f}"
            except Exception:
                prima_comercial = prima_comercial_inclusive or prima_total_alt or prima_neta
        else:
            # IMPORTANTE: no usar 'prima_total_alt' como comercial si hay riesgo de que sea +IGV
            prima_comercial = prima_comercial_inclusive or prima_neta or sctr_salud_val or None

    # Prima Comercial + IGV (capturada o calculada)
    if not prima_comercial_igv:
        # Preferir “Prima Total / Total a Pagar” como suma con IGV
        if prima_total_alt:
            prima_comercial_igv = prima_total_alt
        else:
            base = prima_comercial
            if base and igv_val:
                try:
                    prima_comercial_igv = f"{float(base) + float(igv_val):.2f}"
                except Exception:
                    prima_comercial_igv = base
    # Fallback fechas: si falta último día de pago, calcular emision + 15
    def _add_days(date_str: Optional[str], days: int) -> Optional[str]:
        try:
            if not date_str: return None
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return (dt + timedelta(days=days)).strftime("%d/%m/%Y")
        except Exception:
            return None

    # NUEVO: Último día de pago = fin de vigencia + 15; si no hay, emisión + 15; luego el campo capturado
    ultimo_por_vigencia = _add_days(emision, 15) if emision else None
    ultimo_por_emision = _add_days(emision, 15) if emision else None
    pago_venc = ultimo_por_vigencia or ultimo_por_emision or pago_venc

    # Preferir el último día de pago como 'fecha_vencimiento'; si no, usar fin de vigencia
    fecha_venc = pago_venc or vig_hasta

    # Extraer RUC (11 dígitos) o DNI (8 dígitos) asociado al contratante o asegurado
    # Lógica de proximidad: Buscar RUC más cercano a campos clave (Contratante, Proforma, etc.)
    # para evitar capturar el RUC de la aseguradora (cabecera) de forma automática.
    
    ruc_candidato = None
    
    # Encontrar pivotes que indican el inicio de los datos del cliente/póliza
    # El RUC del cliente suele estar cerca o después de estos campos
    pivots_iter = re.finditer(r"(?:Contratante|Asegurado|Proforma|P[oó]liza|Contrato)\s*[:]", text, re.IGNORECASE)
    pivots = [m.start() for m in pivots_iter]
    
    # Prioridad 1: Buscar explícitamente RUC (11 dígitos) con etiqueta "R.U.C."
    rucs_matches = list(re.finditer(r"R\.?U\.?C\.?[\s:\.]*(\d{11})", text, re.IGNORECASE))
    
    if rucs_matches:
        if pivots:
            # Estrategia: Elegir el RUC que está después del primer pivote (inicio del cuerpo)
            # El primer pivote suele ser "Póliza" o "Proforma" en el encabezado del cuerpo.
            # El RUC de la aseguradora suele estar antes (en el membrete).
            first_pivot = pivots[0]
            rucs_after = [m for m in rucs_matches if m.start() >= first_pivot]
            
            if rucs_after:
                # Tomar el primero que aparezca en el cuerpo del documento
                ruc_candidato = rucs_after[0].group(1)
            else:
                # Si no hay RUCs después del pivote (raro), buscar el más cercano al pivote
                # Esto maneja casos donde el layout sea atípico
                best_match = min(rucs_matches, key=lambda m: min(abs(m.start() - p) for p in pivots))
                ruc_candidato = best_match.group(1)
        else:
            # Sin pivotes, usar heurística: si hay varios, evitar el primero si parece cabecera
            if len(rucs_matches) > 1:
                # Asumimos que el primero es la aseguradora (header) y el segundo el cliente
                ruc_candidato = rucs_matches[1].group(1)
            else:
                ruc_candidato = rucs_matches[0].group(1)
    
    # Prioridad 2: Buscar explícitamente DNI (8 dígitos) si no hay RUC
    if not ruc_candidato:
        dnis_matches = list(re.finditer(r"D\.?N\.?I\.?[\s:\.]*(\d{8})", text, re.IGNORECASE))
        if dnis_matches:
            if pivots:
                first_pivot = pivots[0]
                dnis_after = [m for m in dnis_matches if m.start() >= first_pivot]
                if dnis_after:
                    ruc_candidato = dnis_after[0].group(1)
                else:
                    best_match = min(dnis_matches, key=lambda m: min(abs(m.start() - p) for p in pivots))
                    ruc_candidato = best_match.group(1)
            else:
                ruc_candidato = dnis_matches[0].group(1)

    # Prioridad 3: Fallback a búsqueda genérica de RUC (empieza con 10 o 20)
    if not ruc_candidato:
        generic_matches = list(re.finditer(r"\b(10\d{9}|20\d{9})\b", text))
        if generic_matches:
            if pivots:
                first_pivot = pivots[0]
                gen_after = [m for m in generic_matches if m.start() >= first_pivot]
                if gen_after:
                    ruc_candidato = gen_after[0].group(1)
                else:
                     best_match = min(generic_matches, key=lambda m: min(abs(m.start() - p) for p in pivots))
                     ruc_candidato = best_match.group(1)
            else:
                # Si hay varios, preferir el segundo (evitar header)
                if len(generic_matches) > 1:
                    ruc_candidato = generic_matches[1].group(1)
                else:
                    ruc_candidato = generic_matches[0].group(1)

    item = {
        "numero_poliza": (contrato_nro if (ramo and ramo.upper().startswith("SCTR SALUD") and contrato_nro) else (poliza_nro or contrato_nro)),
        "contrato_nro": contrato_nro,
        "recibo": numero_proforma,
        "colectivo_asegurado": colectivo_asegurado,
        "inicio_vigencia": vig_desde,
        "vencimiento": vig_hasta,
        "moneda": moneda,
        "fecha_emision": emision,
        "ultimo_dia_pago": pago_venc,
        "fecha_vencimiento": fecha_venc,
        "prima_neta": prima_neta,
        # Mantener compatibilidad: 'prima_total' representa la comercial sin IGV
        "prima_total": prima_comercial,
        "prima_comercial": prima_comercial,
        "prima_comercial_igv": prima_comercial_igv,
        "ramo": ramo,
        "numero_documento_extracted": ruc_candidato,
    }
    print("item salud", item)
    return {k: v for k, v in item.items() if v}