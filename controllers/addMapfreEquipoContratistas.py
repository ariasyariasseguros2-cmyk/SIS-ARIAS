import re

def parse_mapfre_equipo_contratistas(text: str):
    """
    Parser para 'POLIZA DE SEGURO DE EQUIPO DE CONTRATISTAS' de Mapfre.
    """
    item = {}
    
    # 0. Limpieza básica
    # Unificar saltos de línea para facilitar regex multilínea
    text_norm = re.sub(r'\r\n', '\n', text)
    
    # 1. Póliza
    # PÓLIZA
    # 2322510103330
    m_pol = re.search(r'PÓLIZA\s*\n\s*(\d{8,})', text_norm, re.IGNORECASE)
    if not m_pol:
        m_pol = re.search(r'PÓLIZA\s*[:\.]?\s*(\d{8,})', text_norm, re.IGNORECASE)
    if not m_pol:
        # En caso esté en la misma línea o con texto intermedio breve
        m_pol = re.search(r'PÓLIZA.*?(\d{10,})', text_norm, re.IGNORECASE | re.DOTALL)
    if m_pol:
        item['numero_poliza'] = m_pol.group(1)

    # 2. Vigencia
    # VIGENCIA DESDE HASTA
    # 27/11/2025 12:00 Hrs. 28/11/2026 12:00 Hrs.
    date_pat = r'\d{2}/\d{2}/\d{4}'
    m_vig = re.search(rf'({date_pat})\s+\d{{2}}:\d{{2}}\s+Hrs\.\s+({date_pat})', text_norm)
    if m_vig:
        item['inicio_vigencia'] = m_vig.group(1)
        item['fin_vigencia'] = m_vig.group(2)
        item['vencimiento'] = m_vig.group(2)
        item['fecha_vencimiento'] = m_vig.group(2)

    # 3. Fecha Emisión
    # F.EMISIÓN  ...  27/11/2025
    # Puede estar lejos si es formato tabla, usamos DOTALL
    m_emision = re.search(rf'F\.EMISIÓ?N.*?({date_pat})', text_norm, re.IGNORECASE | re.DOTALL)
    if m_emision:
        item['fecha_emision'] = m_emision.group(1)
        
    # 4. Moneda
    # MONEDA US$ o DOLARES
    # Prioridad: Buscar explícitamente debajo o al lado de "MONEDA"
    m_mon = re.search(r'MONEDA\s*[:\.]?\s*(S/|S/\.|SOLES|US\$|USD|DOLARES)', text_norm, re.IGNORECASE | re.DOTALL)
    
    if m_mon:
        val = m_mon.group(1).upper()
        if "US" in val or "DOLAR" in val:
            item['moneda'] = 'US$'
        else:
            item['moneda'] = 'S/'
    else:
        # Fallbacks más seguros
        if re.search(r'\bS/\.', text_norm) or "SOLES" in text_norm:
             item['moneda'] = 'S/'
        elif "US$" in text_norm or "DOLARES" in text_norm:
             item['moneda'] = 'US$'

    # 5. Datos Contratante (RUC)
    # Buscamos todos los RUCs y descartamos el de Mapfre (20418896915)
    rucs = re.findall(r'RUC\s*:?\s*(\d{11})', text_norm)
    # También buscar números de 11 dígitos sueltos cerca de "RUC" si el formato es tabla
    if not rucs:
        rucs = re.findall(r'\b20\d{9}\b', text_norm)
        
    for ruc in rucs:
        if ruc != '20418896915':
            item['ruc_contratante'] = ruc
            break
    
    # 6. Nombre Contratante (Colectivo Asegurado)
    # Solicitud de usuario (Lógica estricta mejorada con salto de líneas inválidas):
    # 1. Buscar primera aparición exacta de "DATOS DEL CONTRATANTE"
    # 2. Dividir en líneas
    # 3. Buscar línea exacta "NOMBRE"
    # 4. Iterar hacia abajo saltando vacíos, etiquetas y números hasta encontrar valor
    
    idx = text_norm.find("DATOS DEL CONTRATANTE")
    if idx != -1:
        # Cortamos el texto desde esa posición
        subtext = text_norm[idx:]
        lines = subtext.splitlines()
        
        for i, line in enumerate(lines):
            # Comparación exacta requerida
            if line.strip().upper() == "NOMBRE":
                
                # Buscar hacia abajo el nombre real
                for j in range(i + 1, len(lines)):
                    candidate = lines[j].strip()
                    
                    # Saltar líneas vacías
                    if not candidate:
                        continue
                        
                    # Saltar etiquetas conocidas que podrían aparecer si el campo está vacío
                    # (aunque el usuario dice que hay nombre, esto previene tomar "RUC" como nombre)
                    candidate_upper = candidate.upper()
                    if candidate_upper in ["RUC", "DIRECCIÓN", "DIRECCION", "EMAIL", "TELEFONO", "ACTIVIDAD ECONOMICA"]:
                        continue
                        
                    if "RUC" in candidate_upper and len(candidate_upper) < 15: # "RUC" o "RUC:" suelto
                         continue
                    
                    # Saltar líneas que sean solo números (ej: el valor del RUC si se coló)
                    if candidate.replace(" ", "").isdigit():
                        continue
                        
                    # Si pasa los filtros -> es el nombre correcto
                    item['colectivo_asegurado'] = candidate
                    item['asegurado'] = candidate
                    break
                
                break # Detener búsqueda principal tras encontrar el bloque NOMBRE
    
    # 6. Primas
    # Prima Comercial 4,259.77
    m_pc = re.search(r'Prima Comercial\s+([\d,]+\.\d{2})', text_norm)
    if m_pc:
        # Limpiar comas para evitar error de cálculo en JS/Backend
        val_pc = m_pc.group(1).replace(',', '')
        item['prima_comercial'] = val_pc
        
        # Calcular Prima Neta (asumiendo DE=3%: PC = PN * 1.03)
        try:
            pc_float = float(val_pc)
            pn_float = pc_float / 1.03
            item['prima_neta'] = f"{pn_float:.2f}"
        except:
            pass
        
    # Prima Comercial + I.G.V.
    m_pigv = re.search(r'Prima Comercial\s+\+\s+I\.G\.V\.\s+([\d,]+\.\d{2})', text_norm)
    if m_pigv:
        val_pigv = m_pigv.group(1).replace(',', '')
        item['prima_comercial_igv'] = val_pigv
        item['prima_total'] = val_pigv
        item['monto'] = val_pigv

    # 7. Comisión
    # IMPORTE DE LA COMISION 475.61
    m_com = re.search(r'IMPORTE DE LA COMISION\s+([\d,]+\.\d{2})', text_norm, re.IGNORECASE)
    if m_com:
        item['comision_compania_importe'] = m_com.group(1).replace(',', '')
        # Calcular porcentaje si tenemos prima neta (o comercial ajustada)
        # Pero mejor dejar que la UI lo calcule o enviarlo si aparece explícito
    
    # 8. Recibo / Proforma
    # NRO. RECIBO
    # 166713608
    m_recibo = re.search(r'NRO\.?\s*RECIBO.*?(\d{7,})', text_norm, re.IGNORECASE | re.DOTALL)
    if m_recibo:
        item['recibo'] = m_recibo.group(1)


    # Ramo
    item['ramo'] = 'EQUIPO DE CONTRATISTAS'

    return item
