import re
from typing import Dict, Optional, List


class ProtectaParser:
    """Parser específico para PDFs de Protecta"""

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Detecta si el PDF es de Protecta."""
        indicators = [
            r'PROTECTA.*SECURITY',
            r'PROTECTA S\.A\.',
            r'protectasecurity\.pe',
            r'P\s*R\s*O\s*T\s*E\s*C\s*T\s*A', # Spaced out PROTECTA
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """Extrae el nombre del contratante."""
        # 1. Intentar buscar en la sección específica (formato antiguo/estándar)
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:|Vigencia de la Cobertura:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            patterns = [
                r'Contratante\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&-]{4,79}?)(?:\n|Ruc:|RUC:)',
                r'Contratante\s*:\s*([^\n]{5,100}?)(?:\n|$)',
            ]

            for pattern in patterns:
                match = re.search(pattern, seccion_texto, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        # 2. Fallback: Buscar en todo el texto (formato Aviso de Cobranza)
        # Busca "Contratante: NOMBRE" seguido de "DNI/RUC" o nueva línea
        patterns_global = [
            r'Contratante\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&-]{4,79}?)(?:\s+DNI/RUC|\s+RUC|\n)',
            r'Contratante\s*:\s*([^\n]{5,100}?)(?:\s+DNI/RUC|\s+RUC|\n|$)',
        ]
        
        for pattern in patterns_global:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def extract_ruc(self) -> Optional[str]:
        """Extrae el RUC del contratante."""
        # 1. Intentar buscar en la sección específica
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:|Vigencia de la Cobertura:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            match = re.search(r'Ruc\s*:\s*(\d{11})', seccion_texto, re.IGNORECASE)
            if match:
                ruc = match.group(1)
                if ruc != '20517207331':  # Excluir RUC de Protecta
                    return ruc
        
        # 2. Fallback: Buscar patterns globales de RUC asociados al contratante
        # Priorizar RUCs que están cerca de "Contratante" o etiquetados explícitamente como DNI/RUC
        patterns_global = [
            r'DNI/RUC\s*[:]?\s*(\d{11})', # Formato "DNI/RUC: 20..."
            r'RUC\s*[:]?\s*(\d{11})',
        ]
        
        for pattern in patterns_global:
            matches = re.finditer(pattern, self.text, re.IGNORECASE)
            for match in matches:
                ruc = match.group(1)
                if ruc != '20517207331':
                    return ruc

        return None

    def extract_dni(self) -> Optional[str]:
        """Extrae el DNI si es persona natural."""
        patterns = [
            r'DNI/RUC\s*[:]?\s*(\d{8})(?!\d)', # Formato "DNI/RUC: 10..." (si es 8 digitos)
            r'DNI\s*:\s*(\d{8})',
            r'DNI\s*-\s*(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección fiscal del contratante."""
        # 1. Intentar buscar en la sección específica
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:|Vigencia de la Cobertura:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            patterns = [
                r'Direcci[oó]n Fiscal\s*:\s*([^\n]{10,150})',
                r'Direcci[oó]n\s*:\s*([^\n]{10,150})',
            ]

            for pattern in patterns:
                match = re.search(pattern, seccion_texto, re.IGNORECASE)
                if match:
                    direccion = match.group(1).strip()
                    # Excluir direcciones de Protecta
                    if not any(x in direccion for x in ['Domingo Orué', 'Surquillo', 'PROTECTA']):
                        return direccion
        
        # 2. Fallback: Búsqueda global (para formato Aviso de Cobranza)
        patterns_global = [
            r'Direcci[oó]n\s*[:]?\s*([^\n]{10,150})',
        ]
        
        for pattern in patterns_global:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                direccion = match.group(1).strip()
                # Excluir direcciones de Protecta (Av. Domingo Orué 165)
                if not any(x in direccion for x in ['Domingo Orué', 'Surquillo', 'PROTECTA']):
                    return direccion

        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email del contratante."""
        # Buscar en sección de contratante
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            match = re.search(pattern, seccion_texto)
            if match:
                email = match.group(0).lower()
                # Excluir emails de Protecta
                if 'protectasecurity.pe' not in email:
                    return email

        return None

    def extract_telefono(self) -> List[str]:
        """Extrae teléfonos."""
        phones = []
        patterns = [
            r'(?:^|\s)(9\d{8})(?:\s|$)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, self.text, re.MULTILINE)
            for match in matches:
                phone = match.group(1)
                phones.append(phone)

        return list(set(phones))[:2]  # Max 2 teléfonos

    def _parse_location(self, full_address: str) -> Dict[str, str]:
        """
        Intenta separar la dirección en calle y ubicación (Dep/Prov/Dist).
        Retorna un dict con los componentes actualizados.
        """
        result = {
            'direccion': full_address,
            'departamento': '',
            'provincia': '',
            'distrito': ''
        }

        # Buscar separador " - " que divide calle de ubicación
        if ' - ' in full_address:
            parts = full_address.rsplit(' - ', 1)
            address_part = parts[0].strip()
            location_part = parts[1].strip()
            
            # Actualizar dirección limpia
            result['direccion'] = address_part
            
            # Intentar parsear ubicación
            # Lista de departamentos para identificar el inicio
            departamentos = [
                'AMAZONAS', 'ANCASH', 'APURIMAC', 'AREQUIPA', 'AYACUCHO', 'CAJAMARCA', 
                'CALLAO', 'CUSCO', 'HUANCAVELICA', 'HUANUCO', 'ICA', 'JUNIN', 
                'LA LIBERTAD', 'LAMBAYEQUE', 'LIMA', 'LORETO', 'MADRE DE DIOS', 
                'MOQUEGUA', 'PASCO', 'PIURA', 'PUNO', 'SAN MARTIN', 'TACNA', 
                'TUMBES', 'UCAYALI'
            ]
            
            # Detectar departamento
            found_dept = None
            remaining = location_part
            
            for dept in departamentos:
                if location_part.upper().startswith(dept):
                    found_dept = dept
                    remaining = location_part[len(dept):].strip()
                    break
            
            if found_dept:
                result['departamento'] = found_dept
                
                # Heurística para Provincia y Distrito
                # Asumir que lo que queda es "PROVINCIA DISTRITO"
                # Si hay múltiples palabras, el distrito suele ser la última,
                # a menos que empiece con San/Santa/El/La/Los/Las/Nuevo/Villa
                
                words = remaining.split()
                if not words:
                    pass
                elif len(words) == 1:
                    result['provincia'] = words[0] # Solo hay una palabra, asumimos provincia (o distrito?)
                else:
                    # Chequear prefijos de distrito comunes de 2+ palabras
                    dist_prefixes = ['SAN', 'SANTA', 'EL', 'LA', 'LOS', 'LAS', 'NUEVO', 'VILLA', 'PUERTO', 'CERRO']
                    
                    # Intentar determinar cuántas palabras forman el distrito (de atrás hacia adelante)
                    dist_words = 1
                    if len(words) >= 2 and words[-2].upper() in dist_prefixes:
                        dist_words = 2
                    elif len(words) >= 3 and words[-3].upper() in dist_prefixes:
                        dist_words = 3
                        
                    result['distrito'] = ' '.join(words[-dist_words:])
                    result['provincia'] = ' '.join(words[:-dist_words])
            else:
                # Si no detectamos departamento al inicio, poner todo en provincia
                result['provincia'] = location_part

        return result

    def extract_all(self) -> Dict:
        """Extrae toda la información del PDF de Protecta."""
        ruc = self.extract_ruc()
        dni = self.extract_dni()

        if ruc:
            tipo_documento = "RUC"
            numero_documento = ruc
            tipo_persona = "JURIDICA" if ruc.startswith('20') else "NATURAL"
        elif dni:
            tipo_documento = "DNI/CE"
            numero_documento = dni
            tipo_persona = "NATURAL"
        else:
            tipo_documento = "DNI/CE"
            numero_documento = ""
            tipo_persona = "NATURAL"

        nombre = self.extract_contratante()
        telefonos = self.extract_telefono()
        
        # Procesar dirección y ubicación
        raw_direccion = self.extract_direccion() or ""
        location_data = self._parse_location(raw_direccion)

        return {
            'tipoPersona': tipo_persona,
            'razonSocial': nombre or "",
            'tipoDocumento': tipo_documento,
            'numeroDocumento': numero_documento,
            'direccion': location_data['direccion'],
            'distrito': location_data['distrito'],
            'provincia': location_data['provincia'],
            'departamento': location_data['departamento'],
            'email': self.extract_email() or "",
            'telefono1': telefonos[0] if len(telefonos) > 0 else "",
            'telefono2': telefonos[1] if len(telefonos) > 1 else "",
        }
