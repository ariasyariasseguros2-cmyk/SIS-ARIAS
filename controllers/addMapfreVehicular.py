import re
from datetime import datetime, timedelta

def parse_mapfre_vehicular(text: str):
    """
    Parser V3 para 'SUPLEMENTO DE SEGURO VEHICULAR FULL COBERTURA PREMIUM PESADOS' de Mapfre.
    """
    item = {}
    
    # 0. Limpieza básica
    text_norm = re.sub(r'\r\n', '\n', text)
    
    # 1. Póliza
    # PÓLIZA N° 3012500000203
    m_pol = re.search(r'PÓLIZA\s*(?:N[°º])?\s*(\d{8,})', text_norm, re.IGNORECASE)
    if not m_pol:
        m_pol = re.search(r'PÓLIZA.*?\n.*?(\d{8,})', text_norm, re.IGNORECASE)
    if m_pol:
        item['numero_poliza'] = m_pol.group(1)

    # 2. Vigencia
    # VIGENCIA DESDE 30/12/2025 12:00 Hrs.
    # VIGENCIA HASTA 30/12/2026 12:00 Hrs.
    date_pat = r'\d{2}/\d{2}/\d{4}'
    
    m_desde = re.search(rf'VIGENCIA\s+DESDE\s+({date_pat})', text_norm, re.IGNORECASE)
    m_hasta = re.search(rf'VIGENCIA\s+HASTA\s+({date_pat})', text_norm, re.IGNORECASE)
    
    if m_desde:
        item['inicio_vigencia'] = m_desde.group(1)
    
    if m_hasta:
        item['fin_vigencia'] = m_hasta.group(1)
        item['vencimiento'] = m_hasta.group(1)
        item['fecha_vencimiento'] = m_hasta.group(1)

    # 3. Fecha Emisión
    # FECHA DE EMISIÓN:28/10/2025 (Header rojo)
    m_emision = re.search(rf'FECHA\s+DE\s+EMISI[ÓO]N\s*[:\.]?\s*({date_pat})', text_norm, re.IGNORECASE)
    if m_emision:
        item['fecha_emision'] = m_emision.group(1)
        
        # Calcular Ultimo Dia Pago (Fecha Emision + 15 días)
        # Regla estándar si no hay campo explícito
        try:
            fe_obj = datetime.strptime(item['fecha_emision'], '%d/%m/%Y')
            udp_obj = fe_obj + timedelta(days=15)
            item['ultimo_dia_pago'] = udp_obj.strftime('%d/%m/%Y')
        except:
            pass

    # 4. Moneda
    # MONEDA US$
    # Prioridad: Buscar explícitamente debajo o al lado de "MONEDA"
    m_mon = re.search(r'MONEDA\s*[:\.]?\s*(S/|S/\.|SOLES|US\$|USD|DOLARES)', text_norm, re.IGNORECASE | re.DOTALL)
    
    if m_mon:
        val = m_mon.group(1).upper()
        if "US" in val or "DOLAR" in val:
            item['moneda'] = 'US$'
        else:
            item['moneda'] = 'S/'
    else:
        # Fallbacks
        if re.search(r'\bS/\.', text_norm) or "SOLES" in text_norm:
             item['moneda'] = 'S/'
        elif "US$" in text_norm or "DOLARES" in text_norm:
             item['moneda'] = 'US$'

    # 5. Datos Contratante (RUC)
    # RUC 20492680339 (en tabla DATOS DEL CONTRATANTE)
    # Evitar RUC de Mapfre: 20418896915
    rucs = re.findall(r'RUC\s*[:\.]?\s*(\d{11})', text_norm)
    # Buscar también en bloques de tabla donde RUC está en una celda y el número en otra
    if not rucs:
         rucs = re.findall(r'\b20\d{9}\b', text_norm)
         
    for ruc in rucs:
        if ruc != '20418896915':
            item['ruc_contratante'] = ruc
            break

    # 6. Nombre Contratante (Razón Social)
    # Razón social RICARGO SOCIEDAD ANONIMA CERRADA
    m_rs = re.search(r'Raz[óo]n\s+social\s+(.*?)(?:RUC|Direcci[óo]n|$)', text_norm, re.IGNORECASE)
    if m_rs:
        name = m_rs.group(1).strip()
        item['colectivo_asegurado'] = name
        item['asegurado'] = name
    else:
        # Fallback genérico buscando cerca de DATOS DEL CONTRATANTE
        idx = text_norm.find("DATOS DEL CONTRATANTE")
        if idx != -1:
            subtext = text_norm[idx:]
            lines = subtext.splitlines()
            for i, line in enumerate(lines):
                 if "Raz" in line and "social" in line: # Razón social
                     # Intentar extraer de la misma línea
                     clean = re.sub(r'.*Raz[óo]n\s+social\s*', '', line, flags=re.IGNORECASE)
                     clean = re.sub(r'RUC.*', '', clean, flags=re.IGNORECASE).strip()
                     if len(clean) > 3:
                         item['colectivo_asegurado'] = clean
                         item['asegurado'] = clean
                         break

    # 7. Primas
    # Prima Comercial 412.00
    # Prima Comercial + I.G.V. 486.16
    m_pc = re.search(r'Prima\s+Comercial\s+([\d,]+\.\d{2})', text_norm, re.IGNORECASE)
    if m_pc:
        val_pc = m_pc.group(1).replace(',', '')
        item['prima_comercial'] = val_pc
        
        # Prima Neta (Calculada o extraída)
        # Si no está explícita, usamos PC / 1.03
        try:
            pc_float = float(val_pc)
            pn_float = pc_float / 1.03
            item['prima_neta'] = f"{pn_float:.2f}"
        except:
            pass

    m_total = re.search(r'Prima\s+Comercial\s+\+\s+I\.?G\.?V\.?\s+([\d,]+\.\d{2})', text_norm, re.IGNORECASE)
    if m_total:
         item['prima_total'] = m_total.group(1).replace(',', '')
    
    # 8. Recibo / Proforma (Opional, para mantener paridad con parser genérico)
    # Buscar patrones comunes de recibo
    m_rec = re.search(r'(?:RECIBO|PROFORMA)\s*(?:N[°º])?\s*(\d{6,})', text_norm, re.IGNORECASE)
    if m_rec:
        item['recibo'] = m_rec.group(1)

    return item
