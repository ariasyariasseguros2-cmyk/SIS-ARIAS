import re
from datetime import datetime, timedelta

def parse_mapfre_equipo_contratistas_2(text: str):
    """
    Parser V2 para 'POLIZA DE SEGURO DE EQUIPO DE CONTRATISTAS' de Mapfre.
    Lógica más robusta y flexible para variantes de formato.
    """
    item = {}
    
    # 0. Limpieza básica
    # Unificar saltos de línea para facilitar regex multilínea
    text_norm = re.sub(r'\r\n', '\n', text)
    
    # 1. Póliza
    # PÓLIZA
    # 2322510103330
    # Caso 1: Póliza seguida de salto de línea y luego número (con posible basura en medio si es tabla)
    m_pol = re.search(r'PÓLIZA.*?\n.*?(\d{8,})', text_norm, re.IGNORECASE)
    if not m_pol:
        # Caso 2: Póliza en la misma línea
        m_pol = re.search(r'PÓLIZA\s*[:\.]?\s*(\d{8,})', text_norm, re.IGNORECASE)
    if not m_pol:
        # Caso 3: Póliza con espacio y número largo (ej: PÓLIZA 2402510107210)
        m_pol = re.search(r'PÓLIZA\s+(\d{10,})', text_norm, re.IGNORECASE)
    if not m_pol:
        # Caso 4: Búsqueda flexible multilínea (backup)
        m_pol = re.search(r'PÓLIZA.*?(\d{10,})', text_norm, re.IGNORECASE | re.DOTALL)
    if m_pol:
        item['numero_poliza'] = m_pol.group(1)

    # 2. Vigencia
    # VIGENCIA DESDE HASTA
    # 27/11/2025 12:00 Hrs. 28/11/2026 12:00 Hrs.
    # O formato: VIGENCIA DE PÓLIZA 05/10/2025 - 05/10/2026
    date_pat = r'\d{2}/\d{2}/\d{4}'
    
    # Patrón 1: Completo con Hrs (permitiendo texto intermedio como HASTA)
    # Usamos DOTALL para permitir que HASTA esté en nueva línea
    m_vig = re.search(rf'({date_pat})\s+\d{{2}}:\d{{2}}\s+Hrs\..*?({date_pat})', text_norm, re.IGNORECASE | re.DOTALL)
    if not m_vig:
        # Patrón 2: Específico VIGENCIA DE PÓLIZA fecha - fecha
        m_vig = re.search(rf'VIGENCIA\s+DE\s+PÓLIZA\s*({date_pat})\s*-\s*({date_pat})', text_norm, re.IGNORECASE)
    if not m_vig:
        # Patrón 3: Simple con guión (más genérico)
        m_vig = re.search(rf'VIGENCIA.*?({date_pat})\s*-\s*({date_pat})', text_norm, re.IGNORECASE | re.DOTALL)
        
    if m_vig:
        item['inicio_vigencia'] = m_vig.group(1)
        item['fin_vigencia'] = m_vig.group(2)
        item['vencimiento'] = m_vig.group(2)
        item['fecha_vencimiento'] = m_vig.group(2)

    # 3. Fecha Emisión
    # F.EMISIÓN  ...  27/11/2025
    # Puede estar lejos si es formato tabla, usamos DOTALL
    # Hacemos F.EMISION más flexible (F\s*\.?\s*EMISI)
    # También soportar F.EMISIÓN en la misma línea
    m_emision = re.search(rf'F\s*\.?\s*EMISI[ÓO]N\s*[:\.]?\s*({date_pat})', text_norm, re.IGNORECASE)
    if not m_emision:
        m_emision = re.search(rf'F\s*\.?\s*EMISI[ÓO]N.*?({date_pat})', text_norm, re.IGNORECASE | re.DOTALL)
        
    if m_emision:
        item['fecha_emision'] = m_emision.group(1)
        
        # Calcular Ultimo Dia Pago (Fecha Emision + 15 días)
        try:
            fe_obj = datetime.strptime(item['fecha_emision'], '%d/%m/%Y')
            udp_obj = fe_obj + timedelta(days=15)
            item['ultimo_dia_pago'] = udp_obj.strftime('%d/%m/%Y')
        except:
            pass
        
    # 4. Moneda
    # MONEDA US$ o DOLARES
    # Prioridad: Buscar explícitamente debajo o al lado de "MONEDA"
    # Usamos DOTALL para permitir salto de línea (ej: MONEDA\nS/)
    m_mon = re.search(r'MONEDA\s*[:\.]?\s*(S/|S/\.|SOLES|US\$|USD|DOLARES)', text_norm, re.IGNORECASE | re.DOTALL)
    
    if m_mon:
        val = m_mon.group(1).upper()
        if "US" in val or "DOLAR" in val:
            item['moneda'] = 'US$'
        else:
            item['moneda'] = 'S/'
    else:
        # Fallbacks más seguros (evitar "US$" suelto si hay S/ cerca)
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
    
    # 6. Nombre Contratante (Colectivo Asegurado) - LÓGICA ROBUSTA V2
    # - Búsqueda parcial de "NOMBRE"
    # - Búsqueda case-insensitive de "DATOS DEL CONTRATANTE" (permitiendo espacios extra)
    # - Tolerancia a puntos y formatos variados
    
    # Usamos regex para encontrar el bloque "DATOS DEL CONTRATANTE" tolerando espacios
    m_block = re.search(r'DATOS\s+DEL\s+CONTRATANTE', text_norm, re.IGNORECASE)
    
    if m_block:
        # Cortamos el texto desde esa posición
        start_idx = m_block.start()
        subtext = text_norm[start_idx:]
        lines = subtext.splitlines()
        
        found_name = False
        for i, line in enumerate(lines):
            # Limitamos a las primeras 20 líneas del bloque
            if i > 20: 
                break
                
            if "NOMBRE" in line.upper():
                # Check 1: Ver si el nombre está en la misma línea
                # Eliminar la palabra NOMBRE y posibles dos puntos
                same_line_content = re.sub(r'^.*?NOMBRE\s*[:\.]?\s*', '', line, flags=re.IGNORECASE).strip()
                
                # Limpiar si tiene RUC al final
                clean_same_line = re.sub(r'\s+(?:RUC\s*)?\d{11}\s*$', '', same_line_content, flags=re.IGNORECASE).strip()
                
                # Verificar si lo que queda es válido (tiene letras y longitud mínima)
                check_sl = clean_same_line.replace(" ", "").replace("-", "").replace(".", "")
                if len(check_sl) > 2 and any(c.isalpha() for c in check_sl):
                     item['colectivo_asegurado'] = clean_same_line
                     item['asegurado'] = clean_same_line
                     found_name = True
                     break

                # Check 2: Buscar hacia abajo el nombre real si no estaba en la misma línea
                for j in range(i + 1, len(lines)):
                    # Limite de búsqueda hacia abajo
                    if j > i + 10:
                        break
                        
                    candidate = lines[j].strip()
                    
                    # Saltar líneas vacías
                    if not candidate:
                        continue
                        
                    # Saltar etiquetas conocidas
                    cand_upper = candidate.upper()
                    invalid_keywords = ["RUC", "DIRECCIÓN", "DIRECCION", "EMAIL", "TELEFONO", "ACTIVIDAD ECONOMICA", "COD."]
                    
                    is_label = False
                    for kw in invalid_keywords:
                        if cand_upper == kw or cand_upper.startswith(kw + ":") or cand_upper.startswith(kw + " "):
                            is_label = True
                            break
                    
                    if is_label:
                        continue
                        
                    # Validación específica para RUC suelto como etiqueta
                    if "RUC" in cand_upper and len(cand_upper) < 20: 
                         continue
                    
                    # Si la línea contiene RUC al final (ej: NOMBRE EMPRESA RUC 20...)
                    # Intentamos limpiarlo
                    # Regex para quitar RUC al final de la línea: \s+(RUC\s*)?\d{11}\s*$
                    clean_cand = re.sub(r'\s+(?:RUC\s*)?\d{11}\s*$', '', candidate, flags=re.IGNORECASE).strip()
                    
                    # Chequeo final de validez sobre clean_cand
                    # Si queda vacío o solo números/simbolos
                    check_cand = clean_cand.replace(" ", "").replace("-", "").replace(".", "")
                    has_letters = any(c.isalpha() for c in check_cand)
                    
                    if not has_letters:
                        continue
                        
                    # Si pasa los filtros -> es el nombre correcto
                    item['colectivo_asegurado'] = clean_cand
                    item['asegurado'] = clean_cand
                    found_name = True
                    break
                
                if found_name:
                    break # Detener búsqueda principal tras encontrar el bloque NOMBRE
    
    # 7. Primas
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

    # 8. Comisión
    # IMPORTE DE LA COMISION 475.61
    m_com = re.search(r'IMPORTE DE LA COMISION\s+([\d,]+\.\d{2})', text_norm, re.IGNORECASE)
    if m_com:
        item['comision_compania_importe'] = m_com.group(1).replace(',', '')
    
    # 9. Recibo / Proforma
    # NRO. RECIBO
    # 166713608
    m_recibo = re.search(r'NRO\.?\s*RECIBO.*?(\d{7,})', text_norm, re.IGNORECASE | re.DOTALL)
    if m_recibo:
        item['recibo'] = m_recibo.group(1)

    # 10. Producto
    # Si no se encuentra explícito, usar el mismo del ramo o "EQUIPO DE CONTRATISTAS"
    #m_prod = re.search(r'PRODUCTO\s*[:\.]?\s*(.*)', text_norm, re.IGNORECASE)
    #if m_prod:
        #item['producto'] = m_prod.group(1).strip()
    #else:
        #item['producto'] = 'EQUIPO DE CONTRATISTAS'

    # Ramo
    item['ramo'] = 'EQUIPO DE CONTRATISTAS'
    print("intem addMapfre Equipo Contratiste_2 ", item)

    return item
