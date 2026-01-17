"""
Parser especializado para PDFs de MAPFRE.
Detecta y extrae información específica del formato de Mapfre.
"""
import re
from typing import Dict, Optional, List


class MapfreParser:
    """Parser específico para PDFs de Mapfre Seguros."""

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Detecta si el PDF es de Mapfre."""
        indicators = [
            r'MAPFRE PERU',
            r'MAPFRE.*COMPA[NÑ][IÍ]A DE SEGUROS',
            r'PÓLIZA DE SEGUROS DE VIDA.*D\.L\.688',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """Extrae el nombre del contratante."""
        patterns = [
            # Para certificados de Vida Ley
            r'CONTRATANTE DEL SEGURO\s*\n\s*([A-ZÁÉÍÓÚÑ][^\n]{5,100}?)(?:\s+RUC|\s+null|\n)',
            # Para condiciones particulares SCTR
            r'Contratante\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&-]{5,100}?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                # Limpiar posibles basuras
                nombre = re.sub(r'\s+RUC.*$', '', nombre)
                nombre = re.sub(r'\s+null.*$', '', nombre)
                return nombre.strip()
        return None

    def extract_ruc(self) -> Optional[str]:
        """Extrae el RUC del contratante."""
        # Buscar RUC después de "CONTRATANTE DEL SEGURO" o "Contratante"
        patterns = [
            r'CONTRATANTE DEL SEGURO.*?RUC\s*-?\s*(\d{11})',
            r'Contratante.*?RUC\s*:?\s*(\d{11})',
            r'(?:^|\n)RUC\s*:?\s*(\d{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                ruc = match.group(1)
                # Excluir RUC de Mapfre
                if ruc != '20418896915':
                    return ruc

        # Fallback: buscar todos los RUC y excluir el de Mapfre
        rucs_encontrados = re.findall(r'RUC\s*-?\s*:?\s*(\d{11})', self.text, re.IGNORECASE)
        rucs_filtrados = [ruc for ruc in rucs_encontrados if ruc != '20418896915']

        return rucs_filtrados[0] if rucs_filtrados else None

    def extract_dni(self) -> Optional[str]:
        """Extrae el DNI del asegurado."""
        patterns = [
            r'DNI\s*-\s*(\d{8})',
            r'DNI\s*:\s*(\d{8})',
            r'DNI\s+(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae direccion del contratante."""
        patterns = [
            # direccion en la misma linea
            r'DIRECCI[OÓ]N\s+PRINCIPAL\s*:\s*([^\n]{8,220})',
            # Dirección principal con salto de linea
            r'DIRECCI[OÓ]N\s+PRINCIPAL\s*:\s*\n\s*([^\n]{8,220})',
            # direccion generica
            r'DIRECCI[OÓ]N\s*:\s*([^\n]{8,220})',
            r'DOMICILIO\s*:\s*([^\n]{8,220})',
            # contenedores de direccion con nro o n
            r'([^\n]{0,60}\bN(?:RO|°|o)\.?\s*\d{1,5}[^\n]{0,60})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                direccion = match.group(1).strip()
                direccion = re.sub(r'\s+', ' ', direccion)
                # saltar no relacionado
                if not any(x in direccion.lower() for x in ['vigencia', 'fin de', 'poliza', 'póliza', 'mapfre', 'ruc']):
                    if len(direccion) >= 8:
                        return direccion
 # prefijos de direcciones
        line_pattern = r'^(?:\s*)(?:AV(?:\.|ENIDA)?|AVENIDA|JR(?:\.|ON)?|JIRON|CALLE|PSJE|PJE|TENIENTE|TEN\.?|MZ(?:\.|A)?|MZA(?:\.)?|LOTE|URB(?:\.|ANIZACION)?|URBANIZACION|PROL|PROLONG|Jr|Av|Teniente)\b[\s\S]{5,200}$'
        for m in re.finditer(line_pattern, self.text, re.IGNORECASE | re.MULTILINE):
            line = m.group(0).strip()
            # Limpiar y validar
            clean = re.sub(r'\s+', ' ', line)
            if not any(x in clean.lower() for x in ['vigencia', 'poliza', 'ruc']):
                if len(clean) >= 8:
                    return clean

        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, self.text)

        # Excluir emails de Mapfre
        for email in matches:
            if 'mapfre' not in email.lower():
                return email.lower()
        return None

    def extract_telefono(self) -> List[str]:
        """Extrae teléfonos."""
        phones = []
        patterns = [
            r'TELF\s*:\s*(\d{9})',
            r'TEL[ÉE]FONO\s*:\s*(\d{9})',
            r'(?:^|\s)(9\d{8})(?:\s|$)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, self.text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                phone = match.group(1).replace('-', '').replace(' ', '')
                if len(phone) == 9 and phone.startswith('9') and phone != 'null':
                    phones.append(phone)

        return list(set(phones))

    def extract_all(self) -> Dict:
        """Extrae toda la información del PDF de Mapfre."""
        # Primero intenta extraer RUC, luego DNI
        ruc = self.extract_ruc()
        dni = self.extract_dni()

        # Determinar tipo de documento y número
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

        # Extraer nombre (contratante o asegurado)
        nombre = self.extract_contratante()
        if not nombre and dni:
            # Si no hay contratante, buscar asegurado (para certificados individuales)
            asegurado_match = re.search(r'ASEGURADO\s*\n\s*([A-ZÁÉÍÓÚÑ\s,]+)', self.text, re.IGNORECASE)
            if asegurado_match:
                nombre = asegurado_match.group(1).strip()

        telefonos = self.extract_telefono()

        return {
            'tipoPersona': tipo_persona,
            'razonSocial': nombre or "",
            'tipoDocumento': tipo_documento,
            'numeroDocumento': numero_documento,
            'direccion': self.extract_direccion() or "",
            'distrito': "",
            'provincia': "",
            'departamento': "",
            'email': self.extract_email() or "",
            'telefono1': telefonos[0] if len(telefonos) > 0 else "",
            'telefono2': telefonos[1] if len(telefonos) > 1 else "",
        }
