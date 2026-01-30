import re
from typing import Dict, Optional, List


class CrecerParser:

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Detecta si el PDF es de Crecer Seguros."""
        indicators = [
            r'CRECER SEGUROS',
            r'R\.U\.C\.\s*',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """Extrae el nombre del contratante."""
        patterns = [

            r'SE[ÑN]OR\s*\(ES\)\s*:\s*([A-ZÁÉÍÓÚÑ][^\n:]{5,100}?)(?:\s*FECHA|\s*RUC|\s*DNI|\s*:|$)',

            r'CONTRATANTE\s*:\s*([A-ZÁÉÍÓÚÑ][^\n:]{5,100}?)(?:\s*RUC|\s*DNI|\s*DIRECCI[OÓ]?[NI]N?|\s*:|$)',

            r':{10,}.*?\b(\d{8,})\s+(\d{6,})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.,&\']{10,80}?)\s+\d{8,11}\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                if match.lastindex == 3:
                    nombre = match.group(3).strip()
                else:
                    nombre = match.group(1).strip()
                nombre = re.sub(r'\s*:?\s*$', '', nombre)
                nombre = re.sub(r'\s+', ' ', nombre)
                return nombre
        return None

    def extract_ruc(self) -> Optional[str]:
        """RUC CONTRATANTE"""
        # Priorizar patrones que vinculan explícitamente el RUC al contratante
        patterns = [
            r'DNI/RUC\s*[:\s]\s*(\d{11})',
            r'SEÑOR.*?RUC\s*:\s*(\d{11})',
            r'CONTRATANTE.*?RUC\s*:\s*(\d{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)

        # Búsqueda general con exclusión contextual (evitar RUC de la aseguradora)
        # Se asume que el RUC de la aseguradora está cerca de 'CRECER' o 'SEGUROS'
        for match in re.finditer(r'\b(20\d{9})\b', self.text):
            ruc = match.group(1)
            start = match.start()
            
            # Contexto anterior (hasta 100 caracteres)
            context_before = self.text[max(0, start-100):start].upper()
            
            # Si aparece el nombre de la aseguradora cerca
            if ('CRECER' in context_before or 'SEGUROS' in context_before):
                if not any(x in context_before for x in ['SEÑOR', 'CONTRATANTE', 'ASEGURADO', 'CLIENTE', 'DNI']):
                    continue # Es probable que sea el RUC de la aseguradora
            
            return ruc

        return None

    def extract_dni(self) -> Optional[str]:
        patterns = [
            r'DNI\s*[:\-]\s*(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección del contratante."""
        # Prefijos de dirección extendidos
        prefixes = r'AV|JR|CA|CALLE|JIRON|AVENIDA|MZ|MZA|LOTE|PASAJE|PSJE|PJ|CARRETERA|KM'
        
        patterns = [
            # Patrón específico con prefijo conocido
            rf'DIRECCI[OÓ]?[NI]N?\s*[:.]?\s*((?:{prefixes}).*?)(?:\s*TEL[ÉE]FONO|\n|$)',
            rf'DIRECCI[OÓ]?[NI]N?\s*:\s*((?:{prefixes}).*?)(?:\s*ORDEN\s+COMPRA|\s*FORMA\s+DE\s+PAGO|\s*C[OÓ]DIGO)',
            
            # Patrones genéricos (sin prefijo obligatorio, pero después de DIRECCIÓN)
            r'DIRECCI[OÓ]?[NI]N?\s*[:.]?\s*([A-ZÁÉÍÓÚÑ0-9][^\n]*?)(?:\s*TEL[ÉE]FONO|\n|$)',

            # Patrones antiguos
            rf'((?:{prefixes})[^\n]{{5,150}}(?:\n[^\n]{{1,100}})?)\s*DIRECCI[OÓ]?[NI]N?\s*:',
            
            # Fallback genérico
            r'DIRECCI[OÓ]?[NI]N?\s*:\s*([A-ZÁÉÍÓÚÑ0-9][^\n]{10,150}?)(?:\s+\d{4,6}\s*-|\s*RUC|\s*ACTIVIDAD)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                direccion = match.group(1).strip()

                if not any(x in direccion for x in ['Jorge Basadre', 'SAN ISIDRO']):
                    direccion = re.sub(r'\s+', ' ', direccion)

                    direccion = re.sub(r'\(\s*\.\s*[A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+', '', direccion, flags=re.IGNORECASE)
                    direccion = re.sub(r'\(\s*\.\s*[A-ZÁÉÍÓÚÑ\s]+-?\s*$', '', direccion, flags=re.IGNORECASE)
                    direccion = re.sub(r'\s*(FORMA\s+DE\s+PAGO|ORDEN\s+COMPRA|C[OÓ]DIGO).*$', '', direccion, flags=re.IGNORECASE)
                    direccion = re.sub(r'\s+\d{4,6}\s*-\s*[A-Z].*$', '', direccion, flags=re.IGNORECASE)
                    
                    # Eliminar ubicación geográfica al final si existe (separada por guión)
                    # Ej: "... - UCAYALI CORONEL PORTILLO MANANTAY"
                    location_match = re.search(r'\s+-\s*([A-ZÁÉÍÓÚÑ\s]+)$', direccion)
                    if location_match:
                         departments = ['AMAZONAS', 'ANCASH', 'APURIMAC', 'AREQUIPA', 'AYACUCHO', 'CAJAMARCA', 'CALLAO', 'CUSCO', 'HUANCAVELICA', 'HUANUCO', 'ICA', 'JUNIN', 'LA LIBERTAD', 'LAMBAYEQUE', 'LIMA', 'LORETO', 'MADRE DE DIOS', 'MOQUEGUA', 'PASCO', 'PIURA', 'PUNO', 'SAN MARTIN', 'TACNA', 'TUMBES', 'UCAYALI']
                         loc_part = location_match.group(1).upper()
                         if any(dep in loc_part for dep in departments):
                             direccion = direccion[:location_match.start()].strip()

                    return direccion.strip()
        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, self.text)

        for email in matches:
            if 'crecer' not in email.lower():
                return email.lower()
        return None

    def extract_ubicacion_geografica(self) -> Dict[str, str]:
        """Extrae distrito, provincia y departamento de la dirección."""
        # Patterns for (DISTRITO - PROVINCIA - DEPARTAMENTO)
        patterns = [
            # Con punto despues del paréntesis, permite saltos de línea (ANTES de DIRECCIÓN)
            r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*\n?\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+)',
            #  Con punto, captura hasta ORDEN, FORMA, etc.
            r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s+ORDEN|\s+FORMA|\s*$)',
            #Sin punto
            r'\(\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*\)',
            #  despues de DIRECCIÓN (cuando pdfplumber invierte el orden)
            r'DIRECCI[OÓ]?[NI]N?\s*:.*?\n\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)',
            #  Distrito truncado en dirección + resto después
            r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*$',  # Distrito truncado
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                if match.lastindex == 2 and pattern == patterns[3]:
                    distrito_match = re.search(r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*\n?\s*DIRECCI', self.text, re.IGNORECASE | re.DOTALL)
                    distrito = distrito_match.group(1).strip() if distrito_match else ""
                    provincia = match.group(1).strip()
                    departamento = match.group(2).strip()
                else:
                    distrito = match.group(1).strip()
                    provincia = match.group(2).strip() if match.lastindex >= 2 else ""
                    departamento = match.group(3).strip() if match.lastindex >= 3 else ""

                # Limpiar texto extra del departamento
                departamento = re.sub(r'\s*(ORDEN|COMPRA|FORMA|DE|PAGO).*$', '', departamento, flags=re.IGNORECASE).strip()

                if 'LIMA' not in distrito.upper() and 'ISIDRO' not in distrito.upper():
                    if provincia and departamento:
                        return {
                            'distrito': distrito.title() if distrito else '',
                            'provincia': provincia.title(),
                            'departamento': departamento.title()
                        }
        
        # Try to find location in Address line: "... - DEPARTAMENTO PROVINCIA DISTRITO"
        inline_pattern = r'DIRECCI[OÓ]?[NI]N?\s*[:.]?.*?\s-\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s*TEL[ÉE]FONO|\n|$)'
        match = re.search(inline_pattern, self.text, re.IGNORECASE | re.DOTALL)
        if match:
             location_str = match.group(1).strip()
             departments = ['AMAZONAS', 'ANCASH', 'APURIMAC', 'AREQUIPA', 'AYACUCHO', 'CAJAMARCA', 'CALLAO', 'CUSCO', 'HUANCAVELICA', 'HUANUCO', 'ICA', 'JUNIN', 'LA LIBERTAD', 'LAMBAYEQUE', 'LIMA', 'LORETO', 'MADRE DE DIOS', 'MOQUEGUA', 'PASCO', 'PIURA', 'PUNO', 'SAN MARTIN', 'TACNA', 'TUMBES', 'UCAYALI']
             
             found_dep = None
             for dep in departments:
                 if location_str.upper().startswith(dep):
                     found_dep = dep
                     break
            
             if found_dep:
                 remaining = location_str[len(found_dep):].strip()
                 parts = remaining.split()
                 distrito = ""
                 provincia = ""
                 
                 if len(parts) >= 1:
                     # Check for multi-word district
                     if len(parts) >= 2 and parts[-2].upper() in ['SAN', 'SANTA', 'LA', 'EL', 'LOS', 'LAS', 'VILLA', 'PUENTE', 'CERRO', 'NUEVO', 'BAJO', 'ALTO']:
                         distrito = " ".join(parts[-2:])
                         provincia = " ".join(parts[:-2])
                     else:
                         distrito = parts[-1]
                         provincia = " ".join(parts[:-1])
                 
                 return {
                     'distrito': distrito.title(),
                     'provincia': provincia.title(),
                     'departamento': found_dep.title()
                 }

        return {'distrito': '', 'provincia': '', 'departamento': ''}

    def extract_telefono(self) -> List[str]:
        """Extrae telefono."""
        phones = []
        pattern = r'(?:^|\s)(9\d{8})(?:\s|$)'
        matches = re.finditer(pattern, self.text, re.MULTILINE)

        for match in matches:
            phones.append(match.group(1))

        return list(set(phones))[:2]

    def extract_all(self) -> Dict:
        """Extrae toda la información del PDF de Crecer."""
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
        ubicacion = self.extract_ubicacion_geografica()

        return {
            'tipoPersona': tipo_persona,
            'razonSocial': nombre or "",
            'tipoDocumento': tipo_documento,
            'numeroDocumento': numero_documento,
            'direccion': self.extract_direccion() or "",
            'distrito': ubicacion['distrito'],
            'provincia': ubicacion['provincia'],
            'departamento': ubicacion['departamento'],
            'email': self.extract_email() or "",
            'telefono1': telefonos[0] if len(telefonos) > 0 else "",
            'telefono2': telefonos[1] if len(telefonos) > 1 else "",
        }
